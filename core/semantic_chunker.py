"""
core/semantic_chunker.py
PRISM Phase 0.3.4 P2.4 - 최종 완성 (GPT 제안 100% 반영)

✅ 변경사항:
1. 경계 정밀도 강화 (조문 참조 오탐 방지)
2. 파편 병합 (200자 미만 청크 자동 병합)
3. 숫자 변종 확대 (제28조제2항 오탐 방지)
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.3.4 P2.4 의미 기반 청킹 (최종 완성)"""
    
    # 유연한 숫자 패턴
    NUM = r'(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)'
    
    # GPT 제안: 조 뒤에 숫자 금지 (제28조제2항 오탐 방지)
    AFTER_JO_NOT_NUM = r'(?!\s*제?\s*[0-9一二三四五六七八九十Ⅰ-Ⅻ０-９])'
    
    # 규정 전용 패턴 (정밀)
    PATTERNS = {
        'basic': re.compile(r'기\s*본\s*정\s*신', re.IGNORECASE),
        'chapter': re.compile(rf'제\s*{NUM}\s*장', re.IGNORECASE),
        'article': re.compile(rf'^(제\s*{NUM}\s*조){AFTER_JO_NOT_NUM}(?=\s|\()', re.MULTILINE | re.IGNORECASE),
        'supplement': re.compile(r'부\s*칙', re.IGNORECASE),
        'roman': re.compile(r'[Ⅰ-Ⅸ]+\.', re.IGNORECASE)
    }
    
    PRIORITY = {
        'basic': 1,
        'chapter': 2,
        'supplement': 3,
        'article': 4,
        'roman': 5
    }
    
    def __init__(self):
        logger.info("✅ SemanticChunker Phase 0.3.4 P2.4 초기화")
        logger.info("   🎯 패턴: 5개 (최종 완성)")
        logger.info("   🔧 경계 정밀도 강화")
        logger.info("   🧩 파편 자동 병합")
    
    def _pre_normalize(self, text: str) -> str:
        """라인 브레이크 전처리"""
        # 장 앞에 줄바꿈
        text = re.sub(rf'(제\s*{self.NUM}\s*장)', r'\n\1', text)
        
        # 조 앞에 줄바꿈
        text = re.sub(rf'(제\s*{self.NUM}\s*조)', r'\n\1', text)
        
        # 부칙 앞에 줄바꿈
        text = re.sub(r'(부\s*칙)', r'\n\1', text)
        
        # 불규칙 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text
    
    def _post_merge_small_fragments(self, chunks: List[Dict], min_len: int = 200) -> List[Dict]:
        """
        GPT 제안: 파편 병합
        
        200자 미만 청크를 앞 청크에 병합
        """
        if not chunks:
            return chunks
        
        merged = []
        fragment_count = 0
        
        for chunk in chunks:
            char_count = chunk['metadata']['char_count']
            
            # 200자 미만 + article 타입 → 병합 후보
            if merged and char_count < min_len and chunk['metadata']['type'] == 'article':
                # 앞 청크에 병합
                merged[-1]['content'] += '\n' + chunk['content']
                merged[-1]['metadata']['char_count'] += char_count
                fragment_count += 1
                logger.debug(f"   🧩 파편 병합: {chunk['metadata']['boundary']} ({char_count}자)")
            else:
                merged.append(chunk)
        
        if fragment_count > 0:
            logger.info(f"   🧩 파편 병합: {fragment_count}개")
        
        # 인덱스 재정렬
        for i, chunk in enumerate(merged, 1):
            chunk['metadata']['chunk_index'] = i
        
        return merged
    
    def chunk(self, text: str, target_size: int = 800, min_size: int = 50, max_size: int = 1500) -> List[Dict[str, Any]]:
        """청킹 실행"""
        if not text or len(text) < min_size:
            raise ValueError(f"입력 텍스트가 너무 짧음 ({len(text)}자)")
        
        logger.info(f"✂️ 청킹 시작: {len(text)}자")
        
        # 라인 브레이크 전처리
        text = self._pre_normalize(text)
        logger.info("   🔧 라인 브레이크 전처리 완료")
        
        # 1. 모든 경계 탐지
        boundaries = []
        
        for pattern_name, pattern in self.PATTERNS.items():
            matches = list(pattern.finditer(text))
            if matches:
                logger.info(f"   🔍 {pattern_name}: {len(matches)}개 매칭")
            
            for match in matches:
                boundaries.append({
                    'type': pattern_name,
                    'priority': self.PRIORITY[pattern_name],
                    'start': match.start(),
                    'text': match.group(0).strip()
                })
        
        if not boundaries:
            logger.warning("   ⚠️ 패턴 미검출 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        # 2. 위치 기준 정렬
        boundaries.sort(key=lambda x: (x['start'], x['priority']))
        
        # 3. 중복 제거
        unique_boundaries = []
        last_start = -1
        for b in boundaries:
            if b['start'] != last_start:
                unique_boundaries.append(b)
                last_start = b['start']
        
        logger.info(f"   📋 유효 경계: {len(unique_boundaries)}개")
        
        # 4. 청크 생성
        chunks = []
        for i, boundary in enumerate(unique_boundaries):
            start = boundary['start']
            end = unique_boundaries[i + 1]['start'] if i + 1 < len(unique_boundaries) else len(text)
            
            content = text[start:end].strip()
            
            if len(content) < min_size:
                continue
            
            # 제목 추출
            title_match = re.match(rf'제\s*{self.NUM}\s*조\s*\(([^)]+)\)', content)
            title = title_match.group(1) if title_match else None
            
            chunks.append({
                'content': content,
                'metadata': {
                    'type': boundary['type'],
                    'boundary': boundary['text'],
                    'title': title,
                    'char_count': len(content),
                    'chunk_index': len(chunks) + 1
                }
            })
        
        if not chunks:
            logger.warning("   ⚠️ 빈 결과 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        # GPT 제안: 파편 병합
        chunks = self._post_merge_small_fragments(chunks, min_len=200)
        
        logger.info(f"✅ 청킹 완료: {len(chunks)}개")
        
        return chunks
    
    def _fallback_chunk(self, text: str, target: int, min_len: int, max_len: int) -> List[Dict[str, Any]]:
        """길이 기반 페일세이프 청킹"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + target, len(text))
            
            # 문장 경계 찾기
            if end < len(text):
                for sep in ['\n\n', '\n', '. ', '。']:
                    boundary = text.rfind(sep, start + min_len, end)
                    if boundary != -1:
                        end = boundary + len(sep)
                        break
            
            content = text[start:end].strip()
            
            if len(content) >= min_len:
                chunks.append({
                    'content': content,
                    'metadata': {
                        'type': 'fallback',
                        'char_count': len(content),
                        'chunk_index': len(chunks) + 1
                    }
                })
            
            start = end
        
        logger.info(f"   ✅ Fallback 청킹: {len(chunks)}개")
        return chunks if chunks else [{'content': text, 'metadata': {'type': 'emergency', 'char_count': len(text), 'chunk_index': 1}}]
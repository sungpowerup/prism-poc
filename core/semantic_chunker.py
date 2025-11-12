"""
core/semantic_chunker.py
PRISM Phase 0.3.4 P2.1 - 긴급 패턴 수정

✅ 변경사항:
1. 줄 시작 패턴 수정 (^로 강제)
2. 디버그 로그 추가
3. 최소 크기 완화 (10자 → 50자)
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.3.4 P2.1 의미 기반 청킹 (패턴 긴급 수정)"""
    
    # 긴급 수정: 줄 시작만 매칭, 공백 허용
    PATTERNS = {
        'basic': re.compile(r'^기\s*본\s*정\s*신', re.MULTILINE),
        'chapter': re.compile(r'^제\s*\d+\s*장', re.MULTILINE),
        'article': re.compile(r'^제\s*\d+\s*조', re.MULTILINE),
        'supplement': re.compile(r'^부\s*칙', re.MULTILINE)
    }
    
    PRIORITY = {
        'basic': 1,
        'chapter': 2,
        'article': 3,
        'supplement': 4
    }
    
    def __init__(self):
        logger.info("✅ SemanticChunker Phase 0.3.4 P2.1 초기화")
        logger.info(f"   🎯 패턴: {len(self.PATTERNS)}개 (순수 본문 형태 지원)")
    
    def chunk(self, text: str, target_size: int = 800, min_size: int = 50, max_size: int = 1500) -> List[Dict[str, Any]]:
        """청킹 실행"""
        if not text or len(text) < min_size:
            raise ValueError(f"입력 텍스트가 너무 짧음 ({len(text)}자)")
        
        logger.info(f"✂️ 청킹 시작: {len(text)}자")
        
        # 디버그: 샘플 출력
        sample = text[:200].replace('\n', '\\n')
        logger.debug(f"   📝 텍스트 샘플: {sample}")
        
        # 1. 모든 경계 탐지
        boundaries = []
        
        for pattern_name, pattern in self.PATTERNS.items():
            matches = list(pattern.finditer(text))
            logger.debug(f"   🔍 {pattern_name}: {len(matches)}개 매칭")
            
            for match in matches:
                boundaries.append({
                    'type': pattern_name,
                    'priority': self.PRIORITY[pattern_name],
                    'start': match.start(),
                    'text': match.group(0).strip()
                })
                logger.debug(f"      → {match.group(0).strip()[:30]} @ {match.start()}")
        
        if not boundaries:
            logger.warning("   ⚠️ 패턴 미검출 → Fallback")
            logger.warning(f"   📝 첫 100자: {text[:100]}")
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
        
        logger.info(f"   📋 경계 {len(unique_boundaries)}개 감지 (중복 제거 후)")
        
        # 4. 청크 생성
        chunks = []
        for i, boundary in enumerate(unique_boundaries):
            start = boundary['start']
            end = unique_boundaries[i + 1]['start'] if i + 1 < len(unique_boundaries) else len(text)
            
            content = text[start:end].strip()
            
            # 최소 크기 완화 (10 → 50)
            if len(content) < min_size:
                logger.debug(f"   건너뜀: {boundary['text'][:20]} ({len(content)}자 < {min_size}자)")
                continue
            
            if len(content) > max_size:
                logger.warning(f"   크기 초과: {boundary['text'][:20]} ({len(content)}자 > {max_size}자)")
            
            # 제목 추출 (제N조(제목))
            title_match = re.match(r'^제\s*\d+\s*조\s*\(([^)]+)\)', content)
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
        
        logger.info(f"✅ 청킹 완료: {len(chunks)}개")
        
        if not chunks:
            logger.warning("   ⚠️ 빈 결과 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
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
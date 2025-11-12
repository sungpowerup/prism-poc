"""
core/semantic_chunker.py
PRISM Phase 0.3.4 P2.5.1 - Dual-Rail Hotfix

✅ 변경사항 (마창수산팀 주도 설계):
1. 듀얼 패턴 (Strict + Loose)
2. 강화된 라인브레이크 (모든 케이스 커버)
3. 적응형 병합 (헤더 절대 보호)
4. 상세 로깅 (디버깅 용이)

목표: 청크 10~14개, 조문 감지 15~20개
Author: 마창수산팀 (박준호 AI/ML Lead)
Date: 2025-11-12
Version: Phase 0.3.4 P2.5.1
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.3.4 P2.5.1 의미 기반 청킹 (Dual-Rail Hotfix)"""
    
    # 유연한 숫자 패턴 (raw string)
    NUM = r'(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)'
    
    # ✅ Dual-Rail 패턴
    ARTICLE_STRICT = re.compile(
        r'(?m)^(?:#{0,6}\s*)제\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)\s*조'
        r'(?:\s*의\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+))?\s*\(',
        re.IGNORECASE
    )
    
    ARTICLE_LOOSE = re.compile(
        r'(?m)^(?:#{0,6}\s*)제\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)\s*조'
        r'(?:\s*의\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+))?'
        r'(?!\s*\d)',  # 뒤에 숫자 금지 (제28조제2항 제외)
        re.IGNORECASE
    )
    
    CHAPTER = re.compile(
        r'(?m)^(?:#{0,6}\s*)제\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)\s*장',
        re.IGNORECASE
    )
    
    BASIC = re.compile(
        r'(?m)^(?:#{0,6}\s*)기\s*본\s*정\s*신|^기본정신',
        re.IGNORECASE
    )
    
    SUPPLEMENT = re.compile(
        r'(?m)^(?:#{0,6}\s*)부\s*칙',
        re.IGNORECASE
    )
    
    ROMAN = re.compile(r'(?m)^[Ⅰ-Ⅸ]+\.', re.IGNORECASE)
    
    PRIORITY = {
        'basic': 1,
        'chapter': 2,
        'supplement': 3,
        'article': 4,
        'article_loose': 4,  # 같은 우선순위
        'roman': 5
    }
    
    def __init__(self):
        logger.info("✅ SemanticChunker Phase 0.3.4 P2.5.1 초기화 (Dual-Rail)")
        logger.info("   🎯 듀얼 패턴: Strict + Loose")
        logger.info("   🔧 강화된 라인브레이크 + 적응형 병합")
    
    def _pre_normalize(self, text: str) -> str:
        """
        ✅ 강화된 라인브레이크 전처리 (정규식 오류 수정)
        
        처리 순서:
        1. 한 줄에 붙은 장+조 분리
        2. 조 헤더 앞에 강제 개행
        3. 볼드/헤딩 형태 처리
        4. 부칙 처리
        """
        # 1. 한 줄에 붙은 장+조 분리
        # "제1장 총칙 제1조(목적)" → "제1장 총칙\n제1조(목적)"
        # ✅ look-behind 대신 look-ahead 사용
        text = re.sub(
            r'(장[^\n]{1,40})\s+(제\s*\d+\s*조)',
            r'\1\n\2',
            text
        )
        
        # 2. 조 헤더 앞에 강제 개행 (괄호 있는 경우)
        # "...한다. 제1조(목적) 이 규정은" → "...한다.\n제1조(목적) 이 규정은"
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])(\s*제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\()',
            r'\1\n\2',
            text
        )
        
        # 3. 조 헤더 앞에 강제 개행 (괄호 없는 경우도)
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])(\s*제\s*\d+\s*조(?:\s*의\s*\d+)?(?!\d))',
            r'\1\n\2',
            text
        )
        
        # 4. 헤딩 마크다운 처리
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])\s*(#{1,6}\s*제\s*\d+\s*[장조][^\n]*)',
            r'\1\n\2',
            text
        )
        
        # 5. 볼드 텍스트 처리
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])\s*(\*\*\s*제\s*\d+\s*조[^*]*\*\*)',
            r'\1\n\2',
            text
        )
        
        # 6. 장 앞에 줄바꿈
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])\s*(제\s*\d+\s*장)',
            r'\1\n\2',
            text
        )
        
        # 7. 부칙 앞에 줄바꿈
        # ✅ look-behind 제거
        text = re.sub(
            r'([^\n])\s*(부\s*칙)',
            r'\1\n\2',
            text
        )
        
        # 8. 불규칙 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 9. 연속 개행 정리 (최대 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _find_boundaries(self, text: str) -> List[Tuple[int, str, str]]:
        """
        ✅ Dual-Rail 경계 탐지
        
        1단계: Strict 패턴 (괄호 필수)
        2단계: 조문 < 12개면 Loose 보강
        
        Returns:
            List of (position, type, matched_text)
        """
        boundaries = []
        
        # 1단계: 기본정신, 장, 조(Strict), 부칙
        for pattern, pattern_type in [
            (self.BASIC, 'basic'),
            (self.CHAPTER, 'chapter'),
            (self.ARTICLE_STRICT, 'article'),
            (self.SUPPLEMENT, 'supplement'),
            (self.ROMAN, 'roman')
        ]:
            for match in pattern.finditer(text):
                boundaries.append((
                    match.start(),
                    pattern_type,
                    match.group(0).strip()
                ))
        
        # 조문 개수 확인
        article_count = sum(1 for _, t, _ in boundaries if t == 'article')
        
        logger.info(f"   🔍 1단계 (Strict): 조문 {article_count}개")
        
        # 2단계: 조문 < 12개면 Loose 보강
        if article_count < 12:
            logger.info(f"   🔁 조문 부족 → Loose 패턴 보강")
            
            for match in self.ARTICLE_LOOSE.finditer(text):
                pos = match.start()
                matched = match.group(0).strip()
                
                # 중복 체크 (같은 위치에 이미 있으면 스킵)
                if not any(b[0] == pos for b in boundaries):
                    boundaries.append((pos, 'article_loose', matched))
            
            article_count = sum(1 for _, t, _ in boundaries if t in ('article', 'article_loose'))
            logger.info(f"   ✅ 2단계 (Loose): 조문 {article_count}개")
        
        # 위치 기준 정렬
        boundaries.sort(key=lambda x: (x[0], self.PRIORITY[x[1]]))
        
        # 중복 제거 (같은 위치는 우선순위 높은 것만)
        unique_boundaries = []
        last_pos = -1
        for b in boundaries:
            if b[0] != last_pos:
                unique_boundaries.append(b)
                last_pos = b[0]
        
        return unique_boundaries
    
    def _log_boundary_preview(self, text: str, boundaries: List[Tuple[int, str, str]], window: int = 30):
        """경계 미리보기 로깅 (디버깅용)"""
        if not boundaries:
            return
        
        previews = []
        for i, (pos, btype, matched) in enumerate(boundaries[:20], 1):  # 최대 20개
            start = max(0, pos - window)
            end = min(len(text), pos + window)
            
            before = text[start:pos].replace('\n', '↵')
            after = text[pos:end].replace('\n', '↵')
            
            previews.append(f"   [{i:02d}:{btype:8s}] ...{before}⟨{matched}⟩{after}...")
        
        logger.info("   🔎 경계 미리보기:")
        for preview in previews:
            logger.info(preview)
    
    def _post_merge_small_fragments(
        self,
        chunks: List[Dict],
        target_size: int = 800,
        min_len: int = 150
    ) -> List[Dict]:
        """
        ✅ 적응형 병합 (헤더 절대 보호)
        
        규칙:
        1. 헤더 청크는 절대 병합 안 함
        2. 연속 1회까지만 병합
        3. 합산 크기 제한 (target_size * 1.2)
        """
        if not chunks:
            return chunks
        
        merged = []
        fragment_count = 0
        
        for chunk in chunks:
            char_count = chunk['metadata']['char_count']
            content = chunk['content'].lstrip()
            
            # 헤더 판정 (더 넓은 범위)
            is_header = (
                content.startswith(('제', '부칙', 'Ⅰ', 'Ⅱ', 'Ⅲ', '#', '**', '기본정신'))
                or chunk['metadata']['type'] in ('basic', 'chapter', 'supplement')
            )
            
            # 병합 조건 체크
            should_merge = (
                merged  # 앞 청크 존재
                and char_count < min_len  # 짧은 청크
                and not is_header  # 헤더 아님
                and not merged[-1]['content'].lstrip().startswith(('제', '부칙', 'Ⅰ', 'Ⅱ', 'Ⅲ', '#', '**', '기본정신'))  # 앞도 헤더 아님
                and (merged[-1]['metadata']['char_count'] + char_count <= int(target_size * 1.2))  # 크기 제한
                and (merged[-1]['metadata'].get('merged_count', 0) < 1)  # 연속 1회까지
            )
            
            if should_merge:
                # 앞 청크에 병합
                merged[-1]['content'] += '\n' + chunk['content']
                merged[-1]['metadata']['char_count'] += char_count
                merged[-1]['metadata']['merged_count'] = merged[-1]['metadata'].get('merged_count', 0) + 1
                fragment_count += 1
                logger.debug(f"      🧩 파편 병합: {chunk['metadata']['boundary']} ({char_count}자)")
            else:
                merged.append(chunk)
        
        if fragment_count > 0:
            logger.info(f"   🧩 파편 병합: {fragment_count}개")
        
        # 인덱스 재정렬
        for i, chunk in enumerate(merged, 1):
            chunk['metadata']['chunk_index'] = i
        
        return merged
    
    def chunk(
        self,
        text: str,
        target_size: int = 800,
        min_size: int = 50,
        max_size: int = 1500
    ) -> List[Dict[str, Any]]:
        """청킹 실행"""
        if not text or len(text) < min_size:
            raise ValueError(f"입력 텍스트가 너무 짧음 ({len(text)}자)")
        
        logger.info(f"✂️ 청킹 시작: {len(text)}자")
        
        # 1. 라인 브레이크 전처리
        text = self._pre_normalize(text)
        logger.info("   🔧 라인 브레이크 전처리 완료")
        
        # 2. Dual-Rail 경계 탐지
        boundaries = self._find_boundaries(text)
        
        if not boundaries:
            logger.warning("   ⚠️ 패턴 미검출 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        logger.info(f"   📋 유효 경계: {len(boundaries)}개")
        
        # 디버깅: 경계 미리보기 (첫 20개)
        if logger.level <= logging.INFO:
            self._log_boundary_preview(text, boundaries)
        
        # 3. 청크 생성
        chunks = []
        for i, (start, btype, matched) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            
            content = text[start:end].strip()
            
            if len(content) < min_size:
                continue
            
            # 제목 추출
            title_match = re.search(r'제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\(([^)]+)\)', content)
            title = title_match.group(1) if title_match else None
            
            chunks.append({
                'content': content,
                'metadata': {
                    'type': btype,
                    'boundary': matched,
                    'title': title,
                    'char_count': len(content),
                    'chunk_index': len(chunks) + 1
                }
            })
        
        if not chunks:
            logger.warning("   ⚠️ 빈 결과 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        # 4. 적응형 병합
        chunks = self._post_merge_small_fragments(chunks, target_size=target_size, min_len=150)
        
        logger.info(f"✅ 청킹 완료: {len(chunks)}개")
        
        # 타입별 분포 로깅
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk['metadata']['type']
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        logger.info(f"   📊 타입 분포: {dict(type_counts)}")
        
        return chunks
    
    def _fallback_chunk(
        self,
        text: str,
        target: int,
        min_len: int,
        max_len: int
    ) -> List[Dict[str, Any]]:
        """길이 기반 페일세이프 청킹"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + target, len(text))
            
            # 문장 경계 찾기
            if end < len(text):
                for sep in ['\n\n', '\n', '. ', '。']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break
            
            content = text[start:end].strip()
            
            if len(content) >= min_len:
                chunks.append({
                    'content': content,
                    'metadata': {
                        'type': 'fallback',
                        'boundary': 'length-based',
                        'title': None,
                        'char_count': len(content),
                        'chunk_index': len(chunks) + 1
                    }
                })
            
            start = end
        
        logger.info(f"   ⚠️ Fallback 청킹: {len(chunks)}개")
        return chunks
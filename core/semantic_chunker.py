"""
core/semantic_chunker.py
PRISM Phase 0.4.0 P0-2 긴급 패치 (기본정신 헤더 인식)

✅ 핵심 개선:
1. 기본정신 헤더 우선 탐지 (priority=1)
2. JSON/리뷰용 모두에서 첫 청크로 보존
3. 타입 분포에서 basic 타입 정상 표시

Author: 마창수산팀 (박준호 AI/ML Lead) + GPT 보정
Date: 2025-11-13
Version: Phase 0.4.0 P0-2 (Emergency Patch)
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.4.0 P0-2 의미 기반 청킹 (기본정신 보존)"""
    
    # 유연한 숫자 패턴
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
        r'(?!\s*\d)',
        re.IGNORECASE
    )
    
    INLINE_REF = re.compile(r'^.{0,30}제\s*\d+\s*조\s*제\s*\d+\s*(?:항|호)', re.MULTILINE)
    
    CHAPTER = re.compile(
        r'(?m)^(?:#{0,6}\s*)제\s*(?:\d+|[一二三四五六七八九十百千]+|[Ⅰ-Ⅻ]+|[０-９]+)\s*장',
        re.IGNORECASE
    )
    
    # ✅ P0-2: 기본정신 헤더 패턴 강화
    BASIC = re.compile(
        r'(?m)^(?:#{0,6}\s*)?기\s*본\s*정\s*신|^기본정신|^기본\s*정신',
        re.IGNORECASE
    )
    
    SUPPLEMENT = re.compile(
        r'(?m)^(?:#{0,6}\s*)부\s*칙',
        re.IGNORECASE
    )
    
    ROMAN = re.compile(r'(?m)^[Ⅰ-Ⅸ]+\.', re.IGNORECASE)
    
    # ✅ P0-2: 우선순위 조정 (basic이 최우선)
    PRIORITY = {
        'basic': 1,        # 최우선
        'chapter': 2,
        'supplement': 3,
        'article': 4,
        'article_loose': 4,
        'roman': 5
    }
    
    def __init__(self):
        logger.info("✅ SemanticChunker Phase 0.4.0 P0-2 초기화 (기본정신 보존)")
        logger.info("   🎯 제4조 누락 방지 + 기본정신 헤더 인식")
        logger.info("   🔧 강화된 라인브레이크 + 적응형 병합 + 자동 QA")
    
    def _pre_normalize(self, text: str) -> str:
        """강화된 라인브레이크 전처리"""
        # 1. 한 줄에 붙은 장+조 분리
        text = re.sub(r'(장[^\n]{1,40})\s+(제\s*\d+\s*조)', r'\1\n\2', text)
        
        # 2. 조 헤더 앞에 강제 개행 (괄호 있는 경우)
        text = re.sub(r'([^\n])(\s*제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\()', r'\1\n\2', text)
        
        # 3. 조 헤더 앞에 강제 개행 (괄호 없는 경우)
        text = re.sub(r'([^\n])(\s*제\s*\d+\s*조(?:\s*의\s*\d+)?(?!\d))', r'\1\n\2', text)
        
        # 4. 헤딩 마크다운 처리
        text = re.sub(r'([^\n])\s*(#{1,6}\s*제\s*\d+\s*[장조][^\n]*)', r'\1\n\2', text)
        
        # 5. 볼드 텍스트 처리
        text = re.sub(r'([^\n])\s*(\*\*\s*제\s*\d+\s*조[^*]*\*\*)', r'\1\n\2', text)
        
        # 6. 장 앞에 줄바꿈
        text = re.sub(r'([^\n])\s*(제\s*\d+\s*장)', r'\1\n\2', text)
        
        # 7. 부칙 앞에 줄바꿈
        text = re.sub(r'([^\n])\s*(부\s*칙)', r'\1\n\2', text)
        
        # ✅ P0-2: 기본정신 앞에 줄바꿈
        text = re.sub(r'([^\n])\s*(기\s*본\s*정\s*신)', r'\1\n\2', text)
        
        # 8. 불규칙 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 9. 연속 개행 정리 (최대 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _is_inline_reference(self, pos: int, matched: str, text: str) -> bool:
        """인라인 참조 판정 (같은 줄만 검사)"""
        # 1. 경계가 속한 줄 추출
        line_start = text.rfind('\n', 0, pos) + 1
        line_end = text.find('\n', pos)
        if line_end == -1:
            line_end = len(text)
        
        line = text[line_start:line_end]
        
        # 2. 같은 줄에서 인라인 참조 패턴 체크
        if self.INLINE_REF.match(line):
            logger.debug(f"      🔍 인라인 참조 감지 (같은 줄): {matched}")
            return True
        
        # 3. 괄호+제목 체크
        if '(' not in matched and ')' not in matched:
            logger.debug(f"      🔍 괄호 없음: {matched}")
            return True
        
        return False
    
    def _filter_inline_references(
        self,
        boundaries: List[Tuple[int, str, str]],
        text: str
    ) -> List[Tuple[int, str, str]]:
        """article_loose 사후 필터링 (정교화)"""
        filtered = []
        removed_count = 0
        
        for pos, btype, matched in boundaries:
            if btype == 'article_loose':
                if self._is_inline_reference(pos, matched, text):
                    removed_count += 1
                    continue
            
            filtered.append((pos, btype, matched))
        
        if removed_count > 0:
            logger.info(f"   🗑️ 인라인 참조 제거: {removed_count}개")
        
        return filtered
    
    def _find_boundaries(self, text: str) -> List[Tuple[int, str, str]]:
        """
        ✅ Dual-Rail 경계 탐지 + 기본정신 우선 탐지
        
        우선순위:
        1. 기본정신 (최우선)
        2. 장
        3. 조(Strict)
        4. 부칙
        5. 조(Loose, 필요시)
        """
        boundaries = []
        
        # ✅ P0-2: 1단계 - 기본정신 우선 탐지
        for match in self.BASIC.finditer(text):
            boundaries.append((
                match.start(),
                'basic',
                match.group(0).strip()
            ))
            logger.info(f"   📖 기본정신 감지: {match.group(0).strip()}")
        
        # 2단계: 장, 조(Strict), 부칙
        for pattern, pattern_type in [
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
        
        # 3단계: 조문 < 12개면 Loose 보강
        if article_count < 12:
            logger.info(f"   🔁 조문 부족 → Loose 패턴 보강")
            
            for match in self.ARTICLE_LOOSE.finditer(text):
                pos = match.start()
                matched = match.group(0).strip()
                
                # 중복 체크
                if not any(b[0] == pos for b in boundaries):
                    boundaries.append((pos, 'article_loose', matched))
            
            article_count = sum(1 for _, t, _ in boundaries if t in ('article', 'article_loose'))
            logger.info(f"   ✅ 2단계 (Loose): 조문 {article_count}개")
        
        # 위치 기준 정렬
        boundaries.sort(key=lambda x: (x[0], self.PRIORITY[x[1]]))
        
        # 중복 제거
        unique_boundaries = []
        last_pos = -1
        for b in boundaries:
            if b[0] != last_pos:
                unique_boundaries.append(b)
                last_pos = b[0]
        
        # 4단계: 인라인 참조 필터링
        unique_boundaries = self._filter_inline_references(unique_boundaries, text)
        
        return unique_boundaries
    
    def _log_boundary_preview(self, text: str, boundaries: List[Tuple[int, str, str]], window: int = 30):
        """경계 미리보기 로깅"""
        if not boundaries:
            return
        
        previews = []
        for i, (pos, btype, matched) in enumerate(boundaries[:20], 1):
            start = max(0, pos - window)
            end = min(len(text), pos + window)
            
            before = text[start:pos].replace('\n', '↵')
            after = text[pos:end].replace('\n', '↵')
            
            previews.append(f"   [{i:02d}:{btype:8s}] ...{before}⟨{matched}⟩{after}...")
        
        logger.info("   🔎 경계 미리보기:")
        for preview in previews:
            logger.info(preview)
    
    def _is_header_chunk(self, content: str, btype: str) -> bool:
        """헤더 청크 판정 강화"""
        # ✅ P0-2: basic 타입 헤더 인식
        if btype in ('basic', 'chapter', 'supplement'):
            return True
        
        s = content.lstrip()
        if s.startswith(('제', '부칙', 'Ⅰ', 'Ⅱ', 'Ⅲ', '#', '**', '기본정신', '기본 정신')):
            return True
        
        if len(content) < 50 and btype == 'article':
            return True
        
        return False
    
    def _post_merge_small_fragments(
        self,
        chunks: List[Dict],
        target_size: int = 800,
        min_len: int = 150
    ) -> List[Dict]:
        """적응형 병합 (헤더 절대 보호)"""
        if not chunks:
            return chunks
        
        merged = []
        fragment_count = 0
        
        for chunk in chunks:
            char_count = chunk['metadata']['char_count']
            content = chunk['content']
            btype = chunk['metadata']['type']
            
            is_curr_header = self._is_header_chunk(content, btype)
            
            should_merge = False
            if merged:
                prev_content = merged[-1]['content']
                prev_btype = merged[-1]['metadata']['type']
                is_prev_header = self._is_header_chunk(prev_content, prev_btype)
                
                should_merge = (
                    char_count < min_len
                    and not is_curr_header
                    and not is_prev_header
                    and (merged[-1]['metadata']['char_count'] + char_count <= int(target_size * 1.2))
                    and (merged[-1]['metadata'].get('merged_count', 0) < 1)
                )
            
            if should_merge:
                merged[-1]['content'] += '\n' + chunk['content']
                merged[-1]['metadata']['char_count'] += char_count
                merged[-1]['metadata']['merged_count'] = merged[-1]['metadata'].get('merged_count', 0) + 1
                fragment_count += 1
                logger.debug(f"      🧩 파편 병합: {chunk['metadata']['boundary']} ({char_count}자)")
            else:
                merged.append(chunk)
        
        if fragment_count > 0:
            logger.info(f"   🧩 파편 병합: {fragment_count}개")
        
        for i, chunk in enumerate(merged, 1):
            chunk['metadata']['chunk_index'] = i
        
        return merged
    
    def _extract_headers_from_md(self, text: str) -> Set[str]:
        """Markdown에서 조문 헤더 추출"""
        headers = set()
        
        patterns = [
            re.compile(r'제\s*\d+\s*조(?:\s*의\s*\d+)?'),
            re.compile(r'제\s*\d+\s*장'),
            # ✅ P0-2: 기본정신도 헤더로 인식
            re.compile(r'기본정신|기본\s*정신'),
        ]
        
        for pattern in patterns:
            for match in pattern.finditer(text):
                headers.add(match.group(0).strip())
        
        return headers
    
    def _qa_check_missing_headers(self, text: str, chunks: List[Dict]) -> None:
        """자동 QA 게이트 - 누락 조문 감지"""
        md_headers = self._extract_headers_from_md(text)
        
        chunk_headers = set()
        for chunk in chunks:
            boundary = chunk['metadata'].get('boundary', '')
            btype = chunk['metadata'].get('type', '')
            
            # ✅ P0-2: basic 타입도 헤더로 추가
            if btype == 'basic':
                chunk_headers.add('기본정신')
            
            if boundary:
                match = re.match(r'(제\s*\d+\s*조(?:\s*의\s*\d+)?)', boundary)
                if match:
                    chunk_headers.add(match.group(1).strip())
                
                match = re.match(r'(제\s*\d+\s*장)', boundary)
                if match:
                    chunk_headers.add(match.group(1).strip())
        
        missing = md_headers - chunk_headers
        
        if missing:
            logger.warning(f"   ⚠️ 누락된 조문 감지: {sorted(missing)}")
            logger.warning(f"   → JSON 청크에서 다음 조문이 빠졌습니다!")
        else:
            logger.info(f"   ✅ QA 통과: 모든 조문이 JSON에 포함됨")
    
    def chunk(
        self,
        text: str,
        target_size: int = 800,
        min_size: int = 50,
        max_size: int = 1500
    ) -> List[Dict[str, Any]]:
        """청킹 실행 + 자동 QA"""
        if not text or len(text) < min_size:
            raise ValueError(f"입력 텍스트가 너무 짧음 ({len(text)}자)")
        
        logger.info(f"✂️ 청킹 시작: {len(text)}자")
        
        # 1. 라인 브레이크 전처리
        text = self._pre_normalize(text)
        logger.info("   🔧 라인 브레이크 전처리 완료")
        
        # 2. Dual-Rail 경계 탐지 + 기본정신 우선
        boundaries = self._find_boundaries(text)
        
        if not boundaries:
            logger.warning("   ⚠️ 패턴 미검출 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        logger.info(f"   📋 유효 경계: {len(boundaries)}개")
        
        if logger.level <= logging.INFO:
            self._log_boundary_preview(text, boundaries)
        
        # 3. 청크 생성
        chunks = []
        for i, (start, btype, matched) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            
            content = text[start:end].strip()
            
            if len(content) < min_size and not self._is_header_chunk(content, btype):
                continue
            
            # 제목 추출
            if btype == 'basic':
                title = '기본정신'
            else:
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
        
        # 타입별 분포
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk['metadata']['type']
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        logger.info(f"   📊 타입 분포: {dict(type_counts)}")
        
        # ✅ P0-2: basic 타입 존재 여부 확인
        if 'basic' in type_counts:
            logger.info(f"   ✅ 기본정신 청크 보존: {type_counts['basic']}개")
        else:
            logger.warning(f"   ⚠️ 기본정신 청크 없음 (MD에 없거나 인식 실패)")
        
        loose_count = type_counts.get('article_loose', 0)
        loose_ratio = loose_count / len(chunks) if chunks else 0
        
        if loose_ratio > 0.3:
            logger.warning(f"   ⚠️ article_loose 비율 높음: {loose_ratio:.1%}")
        else:
            logger.info(f"   ✅ article_loose 비율 양호: {loose_ratio:.1%}")
        
        # 5. 자동 QA
        self._qa_check_missing_headers(text, chunks)
        
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
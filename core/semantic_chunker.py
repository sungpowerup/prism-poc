"""
core/semantic_chunker.py
PRISM Phase 0.4.0 P0-3a - QA 헤더 추출 정교화

✅ GPT 피드백 반영:
1. 인라인 참조 노이즈 완전 제거
2. 청킹 경계 패턴과 QA 헤더 추출 통합
3. "진짜 헤더"만 QA 대상으로

Author: 정수아 (QA Lead) + GPT 보정
Date: 2025-11-13
Version: Phase 0.4.0 P0-3a
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.4.0 P0-3a 의미 기반 청킹 (QA 정교화)"""
    
    # ============================================
    # 조문 헤더 패턴 (청킹 + QA 공통 사용)
    # ============================================
    NUM = r'\d+(?:의\d+)?'
    AFTER_JO_NOT_NUM = r'(?!\s*제?\s*\d)'
    
    # Strict: 제N조( 형식 (실제 헤더)
    ARTICLE_STRICT = re.compile(
        rf'^(제\s*{NUM}\s*조){AFTER_JO_NOT_NUM}(?=\s*\()',
        re.MULTILINE
    )
    
    # Loose: 제N조 단독 (백업)
    ARTICLE_LOOSE = re.compile(
        rf'^(제\s*{NUM}\s*조){AFTER_JO_NOT_NUM}(?=\s|$)',
        re.MULTILINE
    )
    
    # 장 패턴
    CHAPTER = re.compile(r'^(제\s*\d+\s*장)', re.MULTILINE)
    
    # ✅ GPT 핵심: 기본정신 우선 탐지
    BASIC_SPIRIT = re.compile(r'(?:^|\n)(기본\s*정신)(?:\s|$)', re.MULTILINE)
    
    def __init__(self, target_size: int = 512, min_size: int = 100, max_size: int = 2048):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        
        logger.info("✅ SemanticChunker Phase 0.4.0 P0-3a 초기화 (QA 정교화)")
        logger.info("   🎯 인라인 참조 노이즈 제거 + 헤더 추출 정교화")
    
    def chunk(self, text: str, target_size: int = None, min_size: int = None, max_size: int = None) -> List[Dict[str, Any]]:
        """의미 기반 청킹 실행"""
        if not text or not text.strip():
            return []
        
        target_size = target_size or self.target_size
        min_size = min_size or self.min_size
        max_size = max_size or self.max_size
        
        logger.info(f"✂️ 청킹 시작: {len(text)}자")
        
        # 라인 브레이크 전처리
        text = self._preprocess_linebreaks(text)
        logger.info("   🔧 라인 브레이크 전처리 완료")
        
        # ✅ 기본정신 우선 감지
        has_basic_spirit = bool(self.BASIC_SPIRIT.search(text))
        if has_basic_spirit:
            logger.info(f"   📖 기본정신 감지: 기본정신")
        
        # 경계 찾기
        boundaries = self._find_boundaries(text)
        
        if not boundaries:
            logger.warning("   ⚠️ 빈 결과 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        # 청크 생성
        chunks = []
        for i, (pos, btype, matched, title) in enumerate(boundaries):
            if i == len(boundaries) - 1:
                content = text[pos:].strip()
            else:
                next_pos = boundaries[i + 1][0]
                content = text[pos:next_pos].strip()
            
            if not content:
                continue
            
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
        
        # 작은 청크 병합
        chunks = self._post_merge_small_fragments(chunks, target_size=target_size, min_len=150)
        
        logger.info(f"✅ 청킹 완료: {len(chunks)}개")
        
        # 타입 분포
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk['metadata']['type']
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        logger.info(f"   📊 타입 분포: {dict(type_counts)}")
        
        # 기본정신 보존 확인
        if has_basic_spirit:
            basic_count = type_counts.get('basic', 0)
            logger.info(f"   ✅ 기본정신 청크 보존: {basic_count}개")
        
        # article_loose 비율 모니터링
        loose_count = type_counts.get('article_loose', 0)
        loose_ratio = loose_count / len(chunks) if chunks else 0
        
        if loose_ratio > 0.3:
            logger.warning(f"   ⚠️ article_loose 비율 높음: {loose_ratio:.1%}")
        else:
            logger.info(f"   ✅ article_loose 비율 양호: {loose_ratio:.1%}")
        
        # ✅ GPT 핵심: QA 검증 (정교화된 헤더 추출)
        self._validate_chunks(text, chunks)
        
        return chunks
    
    def _preprocess_linebreaks(self, text: str) -> str:
        """라인 브레이크 전처리"""
        # 조문 헤더 앞에 줄바꿈 확보
        text = re.sub(
            r'([。\.])(\s*)(제\s*\d+조)',
            r'\1\n\n\3',
            text
        )
        
        # 장 앞에 줄바꿈
        text = re.sub(
            r'([。\.])(\s*)(제\s*\d+\s*장)',
            r'\1\n\n\3',
            text
        )
        
        return text
    
    def _find_boundaries(self, text: str) -> List[tuple]:
        """청킹 경계 찾기"""
        boundaries = []
        
        # 1. 기본정신 (최우선)
        for m in self.BASIC_SPIRIT.finditer(text):
            boundaries.append((m.start(), 'basic', m.group(1), '기본정신'))
        
        # 2. Strict 조문
        strict_articles = set()
        for m in self.ARTICLE_STRICT.finditer(text):
            pos = m.start()
            matched = m.group(1).strip()
            
            # 제목 추출
            title_match = re.search(rf'{re.escape(matched)}\s*\(([^)]+)\)', text[pos:pos+50])
            title = title_match.group(1) if title_match else None
            
            boundaries.append((pos, 'article', matched, title))
            strict_articles.add(matched)
        
        logger.info(f"   🔍 1단계 (Strict): 조문 {len(strict_articles)}개")
        
        # 3. Loose 조문 보강 (Strict에 없는 것만)
        if len(strict_articles) < 5:
            logger.info("   🔁 조문 부족 → Loose 패턴 보강")
            
            loose_candidates = []
            for m in self.ARTICLE_LOOSE.finditer(text):
                matched = m.group(1).strip()
                if matched not in strict_articles:
                    loose_candidates.append((m.start(), matched))
            
            # ✅ GPT 핵심: 인라인 참조 필터링
            loose_candidates = self._filter_inline_references(text, loose_candidates)
            
            for pos, matched in loose_candidates:
                boundaries.append((pos, 'article', matched, None))
            
            logger.info(f"   ✅ 2단계 (Loose): 조문 {len(strict_articles) + len(loose_candidates)}개")
            logger.info(f"   🗑️ 인라인 참조 제거: {len(list(self.ARTICLE_LOOSE.finditer(text))) - len(loose_candidates)}개")
        
        # 4. 장
        for m in self.CHAPTER.finditer(text):
            boundaries.append((m.start(), 'chapter', m.group(1).strip(), None))
        
        # 정렬
        boundaries.sort(key=lambda x: x[0])
        
        # 유효성 검증
        boundaries = [b for b in boundaries if b[0] < len(text)]
        
        logger.info(f"   📋 유효 경계: {len(boundaries)}개")
        
        # 경계 미리보기
        if boundaries:
            logger.info("   🔎 경계 미리보기:")
            for i, (pos, btype, matched, title) in enumerate(boundaries[:10]):
                preview = text[max(0, pos-20):pos+80].replace('\n', '↵')
                logger.info(f"   [{i+1:02d}:{btype:8s}] ...{preview}...")
        
        return boundaries
    
    def _filter_inline_references(self, text: str, candidates: List[tuple]) -> List[tuple]:
        """
        ✅ GPT 핵심: 인라인 참조 필터링
        
        제28조, 제34조 같은 본문 내 참조를 제거
        진짜 헤더만 남김
        """
        filtered = []
        
        for pos, matched in candidates:
            # 전후 50자 컨텍스트
            start = max(0, pos - 50)
            end = min(len(text), pos + 100)
            context = text[start:end]
            
            # 인라인 참조 패턴
            inline_patterns = [
                rf'{re.escape(matched)}\s*제\s*\d+항',      # 제73조제1항
                rf'{re.escape(matched)}\s*에\s*따른',       # 제34조에 따른
                rf'{re.escape(matched)}\s*및',              # 제41조 및
                rf'{re.escape(matched)}\s*또는',            # 제28조 또는
                rf'{re.escape(matched)}\s*의\s*규정',       # 제35조의 규정
            ]
            
            is_inline = any(re.search(p, context) for p in inline_patterns)
            
            if not is_inline:
                filtered.append((pos, matched))
        
        return filtered
    
    def _post_merge_small_fragments(self, chunks: List[Dict], target_size: int = 512, min_len: int = 150) -> List[Dict]:
        """작은 파편 병합"""
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        merge_count = 0
        
        while i < len(chunks):
            current = chunks[i]
            current_len = len(current['content'])
            
            # min_len 이상이면 그대로 추가
            if current_len >= min_len:
                merged.append(current)
                i += 1
                continue
            
            # 마지막 청크면 이전과 병합
            if i == len(chunks) - 1:
                if merged:
                    merged[-1]['content'] += '\n\n' + current['content']
                    merged[-1]['metadata']['char_count'] = len(merged[-1]['content'])
                    merge_count += 1
                else:
                    merged.append(current)
                i += 1
                continue
            
            # 다음 청크와 병합
            next_chunk = chunks[i + 1]
            if current_len + len(next_chunk['content']) <= target_size * 1.5:
                next_chunk['content'] = current['content'] + '\n\n' + next_chunk['content']
                next_chunk['metadata']['char_count'] = len(next_chunk['content'])
                merge_count += 1
                i += 1
            else:
                merged.append(current)
                i += 1
        
        if merge_count > 0:
            logger.info(f"   🧩 파편 병합: {merge_count}개")
        
        return merged
    
    def _validate_chunks(self, markdown: str, chunks: List[Dict]) -> None:
        """
        ✅ GPT 핵심: QA 검증 (정교화된 헤더 추출)
        
        청킹 경계 패턴과 동일한 정규식 사용
        인라인 참조는 QA 대상에서 제외
        """
        # ✅ 개선: Strict 패턴으로만 헤더 추출 (인라인 참조 제외)
        md_headers = set()
        
        # Strict 조문 헤더만 추출
        for m in self.ARTICLE_STRICT.finditer(markdown):
            header = m.group(1).strip()
            header = re.sub(r'\s+', '', header)  # 공백 제거
            md_headers.add(header)
        
        # Loose 조문도 추출 (인라인 참조 필터링)
        loose_matches = []
        for m in self.ARTICLE_LOOSE.finditer(markdown):
            pos = m.start()
            header = m.group(1).strip()
            header = re.sub(r'\s+', '', header)
            
            if header not in md_headers:
                loose_matches.append((pos, header))
        
        # 인라인 참조 필터링
        loose_matches = self._filter_inline_references(markdown, loose_matches)
        for _, header in loose_matches:
            md_headers.add(header)
        
        # JSON 청크 헤더 추출
        json_headers = set()
        for chunk in chunks:
            if chunk['metadata']['type'] in ['article', 'article_loose']:
                header = chunk['metadata']['boundary']
                header = re.sub(r'\s+', '', header)
                json_headers.add(header)
        
        # 누락 검증
        missing = md_headers - json_headers
        
        if missing:
            logger.warning(f"   ⚠️ 누락된 조문 감지: {sorted(missing)}")
            logger.warning(f"   → JSON 청크에서 다음 조문이 빠졌습니다!")
        
        # 통계
        logger.info(f"   📊 QA 검증:")
        logger.info(f"      MD 헤더: {len(md_headers)}개")
        logger.info(f"      JSON 헤더: {len(json_headers)}개")
        logger.info(f"      누락: {len(missing)}개")
    
    def _fallback_chunk(self, text: str, target: int, min_len: int, max_len: int) -> List[Dict[str, Any]]:
        """길이 기반 페일세이프"""
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
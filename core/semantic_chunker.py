"""
core/semantic_chunker.py
PRISM Phase 0.4.0 P0-3.1 - Hotfix (헤더 패턴 통합 + 기본정신 강화)

✅ P0-3.1 긴급 수정:
1. DualQA와 동일한 헤더 패턴 사용 (9개 조문 → 9개 청크)
2. 기본정신 패턴 강화 (모든 변형 커버)
3. 인라인 참조 필터링 유지

Author: 마창수산팀 + GPT 피드백 반영
Date: 2025-11-13
Version: Phase 0.4.0 P0-3.1
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Phase 0.4.0 P0-3.1 의미 기반 청킹 (DualQA 패턴 통합)"""
    
    # ============================================
    # ✅ P0-3.1: DualQA와 완전히 동일한 패턴 사용
    # ============================================
    NUM = r'\d+(?:의\d+)?'
    
    # Strict: 제N조( 형식 (실제 헤더)
    # ✅ DualQA와 동일: 앞에 공백/특수문자 허용
    ARTICLE_STRICT = re.compile(
        rf'^[\s⟨<\[]*(제\s*{NUM}\s*조)\s*\(',
        re.MULTILINE
    )
    
    # Loose: 제N조 단독 (백업)
    # ✅ DualQA와 동일: 앞에 공백/특수문자 허용
    ARTICLE_LOOSE = re.compile(
        rf'^[\s⟨<\[]*(제\s*{NUM}\s*조)(?=\s|$)',
        re.MULTILINE
    )
    
    # 장 패턴
    CHAPTER = re.compile(r'^[\s⟨<\[]*(제\s*\d+\s*장)', re.MULTILINE)
    
    # ✅ P0-3.1: 기본정신 패턴 대폭 강화
    # "기본정신", "기 본 정 신", "⟨기본정신⟩", "⟨기 본 정 신⟩" 모두 커버
    BASIC_SPIRIT = re.compile(
        r'[\s⟨<\[]*(기\s*본\s*정\s*신)[\s⟩>\]]*',
        re.MULTILINE | re.IGNORECASE
    )
    
    def __init__(self, target_size: int = 512, min_size: int = 100, max_size: int = 2048):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        
        logger.info("✅ SemanticChunker Phase 0.4.0 P0-3.1 초기화 (Hotfix)")
        logger.info("   🎯 DualQA 패턴 통합 + 기본정신 강화")
    
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
        
        # ✅ P0-3.1: 기본정신 우선 감지 (강화된 패턴)
        basic_match = self.BASIC_SPIRIT.search(text)
        if basic_match:
            logger.info(f"   📖 기본정신 감지: {basic_match.group(1)}")
        else:
            logger.warning("   ⚠️ 기본정신 미감지 (VLM 추출 실패 가능성)")
        
        # 경계 찾기
        boundaries = self._find_boundaries(text)
        
        if not boundaries:
            logger.warning("   ⚠️ 경계 미발견 → Fallback")
            return self._fallback_chunk(text, target_size, min_size, max_size)
        
        # ✅ P0-3.1: 기본정신 경계 추가 (최우선)
        if basic_match:
            basic_pos = basic_match.start()
            # 기본정신이 경계 목록에 없으면 추가
            if not any(b[0] == basic_pos for b in boundaries):
                boundaries.insert(0, (basic_pos, 'basic', '기본정신', None))
                logger.info("   ✅ 기본정신 경계 추가")
        
        # 경계 기반 청킹
        chunks = []
        for i, (pos, btype, matched, title) in enumerate(boundaries):
            next_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            content = text[pos:next_pos].strip()
            
            if len(content) >= min_size:
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
        
        # 파편 병합 (200자 미만)
        chunks = self._post_merge_small_fragments(chunks, target_size=target_size, min_len=200)
        
        logger.info(f"✅ 청킹 완료: {len(chunks)}개")
        
        # 타입 분포
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk['metadata']['type']
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        logger.info(f"   📊 타입 분포: {dict(type_counts)}")
        
        # ✅ P0-3.1: 기본정신 청크 검증
        if basic_match and type_counts.get('basic', 0) == 0:
            logger.error("   ❌ 기본정신 감지했으나 청크 생성 실패!")
        elif type_counts.get('basic', 0) > 0:
            logger.info(f"   ✅ 기본정신 청크 보존: {type_counts['basic']}개")
        
        # article_loose 비율 모니터링
        loose_count = type_counts.get('article_loose', 0)
        loose_ratio = loose_count / len(chunks) if chunks else 0
        
        if loose_ratio > 0.3:
            logger.warning(f"   ⚠️ article_loose 비율 높음: {loose_ratio:.1%}")
        else:
            logger.info(f"   ✅ article_loose 비율 양호: {loose_ratio:.1%}")
        
        # ✅ P0-3.1: QA 검증 (MD vs JSON)
        md_headers = self._extract_headers_for_qa(text)
        json_headers = [c['metadata']['boundary'] for c in chunks if c['metadata']['type'] in ['article', 'article_loose']]
        
        missing_headers = set(md_headers) - set(json_headers)
        
        logger.info(f"   📊 QA 검증:")
        logger.info(f"      MD 헤더: {len(md_headers)}개")
        logger.info(f"      JSON 헤더: {len(json_headers)}개")
        
        if missing_headers:
            logger.error(f"      ❌ 누락: {len(missing_headers)}개 - {list(missing_headers)[:5]}")
        else:
            logger.info(f"      ✅ 누락: 0개")
        
        return chunks
    
    def _preprocess_linebreaks(self, text: str) -> str:
        """라인 브레이크 전처리"""
        # 연속 공백 정리
        text = re.sub(r' {2,}', ' ', text)
        # 연속 줄바꿈 정리 (3개 이상 → 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
    
    def _find_boundaries(self, text: str) -> List[tuple]:
        """경계 찾기 (DualQA 패턴 통합)"""
        boundaries = []
        
        # 1. 기본정신 (최우선)
        basic_match = self.BASIC_SPIRIT.search(text)
        if basic_match:
            boundaries.append((basic_match.start(), 'basic', '기본정신', None))
        
        # 2. Strict 조문 (제N조( 형식)
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
            
            # ✅ 인라인 참조 필터링
            loose_candidates = self._filter_inline_references(text, loose_candidates)
            
            for pos, matched in loose_candidates:
                boundaries.append((pos, 'article_loose', matched, None))
            
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
        """인라인 참조 필터링"""
        filtered = []
        
        for pos, matched in candidates:
            # 앞뒤 50자 컨텍스트
            start = max(0, pos - 50)
            end = min(len(text), pos + len(matched) + 50)
            context = text[start:end]
            
            # 인라인 참조 패턴 감지
            is_inline = False
            
            # 패턴 1: "제N조제M항" (조문 참조)
            if re.search(r'제\d+조제\d+[항호]', context):
                is_inline = True
            
            # 패턴 2: "제N조 및 제M조" (나열)
            if re.search(r'제\d+조\s*[및과]\s*제\d+조', context):
                is_inline = True
            
            # 패턴 3: 문장 중간 (앞에 한글이 바로 붙음)
            if pos > 0 and re.match(r'[가-힣]', text[pos-1]):
                is_inline = True
            
            if not is_inline:
                filtered.append((pos, matched))
        
        return filtered
    
    def _extract_headers_for_qa(self, text: str) -> List[str]:
        """QA용 조문 헤더 추출 (DualQA와 동일)"""
        headers = set()
        
        # Strict 패턴
        for m in self.ARTICLE_STRICT.finditer(text):
            headers.add(m.group(1).strip())
        
        # Loose 패턴
        for m in self.ARTICLE_LOOSE.finditer(text):
            matched = m.group(1).strip()
            # 인라인 참조 제외
            pos = m.start()
            if pos == 0 or text[pos-1] in ['\n', ' ', '⟨', '<', '[']:
                headers.add(matched)
        
        return sorted(headers)
    
    def _post_merge_small_fragments(self, chunks: List[Dict], target_size: int = 512, min_len: int = 200) -> List[Dict]:
        """200자 미만 파편 병합"""
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # 200자 이상이면 그대로 추가
            if len(current['content']) >= min_len:
                merged.append(current)
                i += 1
                continue
            
            # 200자 미만이면 앞 청크에 병합
            if merged:
                merged[-1]['content'] += '\n\n' + current['content']
                merged[-1]['metadata']['char_count'] = len(merged[-1]['content'])
                logger.info(f"   🧩 파편 병합: {len(current['content'])}자 → 앞 청크")
            else:
                # 첫 청크면 그대로 추가
                merged.append(current)
            
            i += 1
        
        return merged
    
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
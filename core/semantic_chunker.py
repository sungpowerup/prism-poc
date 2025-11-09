"""
core/semantic_chunker.py
PRISM Phase 0.3.4 P2 - Semantic Chunker (조문 패턴 강화)

✅ Phase 0.3.4 P2 긴급 수정:
1. 조문 패턴 강화 (제1~200조 모두 매칭)
2. 다양한 헤딩 레벨 지원 (# ## ### ####)
3. 조문 누락 방지 로직
4. 청크=0 하드 실패 유지
⚠️ GPT 피드백 핵심:
"제1~6조, 제8조 통째로 청크 누락 → 조문 패턴 미스매치"

Author: 박준호 (AI/ML Lead) + 마창수산 팀
Date: 2025-11-08
Version: Phase 0.3.4 P2
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 0.3.4 P2 의미 기반 청킹 엔진
    
    ✅ Phase 0.3.4 P2 개선:
    - 조문 패턴 강화 (누락 방지)
    - 청크=0 하드 실패 유지
    - Fallback 길이 기반 청킹 의무화
    """
    
    VERSION = "Phase 0.3.4 P2"
    
    # ✅ P2: 강화된 조문 패턴
    ARTICLE_PATTERNS = [
        # 패턴 1: ### 제1조(목적)
        r'(#{1,4}\s*제\d+조[^#]*?)(?=#{1,4}\s*제\d+조|$)',
        # 패턴 2: **제1조(목적)**
        r'(\*\*제\d+조[^*]*?\*\*[^*]*?)(?=\*\*제\d+조|$)',
        # 패턴 3: 제1조(목적) (헤딩 없음)
        r'(^제\d+조[^\n]*?\n[\s\S]*?)(?=^제\d+조|\Z)',
    ]
    
    # 한국어 문장 종결 패턴
    KOREAN_SENTENCE_ENDINGS = [
        r'다\.',  # ~하다.
        r'다\)',  # ~한다)
        r'다\s*$',  # ~한다
        r'함\.',  # ~함.
        r'됨\.',  # ~됨.
        r'임\.',  # ~임.
        r'<\d{4}\.\s*\d{1,2}\.\s*\d{1,2}>',  # <2024.1.1>
        r'\d+\.\)',  # 1.)
        r'호\s*$',  # ~호
        r'한다\.',  # ~한다.
    ]
    
    # 불완전 종결 패턴
    INCOMPLETE_ENDINGS = [
        r'의\s*$', r'를\s*$', r'을\s*$', r'가\s*$',
        r'에\s*$', r'와\s*$', r'로\s*$', r'채\s*$',
    ]
    
    def __init__(self, target_size: int = 800, min_size: int = 300):
        """초기화"""
        self.target_size = target_size
        self.min_size = min_size
        
        self.sentence_patterns = [re.compile(p) for p in self.KOREAN_SENTENCE_ENDINGS]
        self.incomplete_patterns = [re.compile(p) for p in self.INCOMPLETE_ENDINGS]
        
        # ✅ P2: 조문 패턴 컴파일
        self.article_patterns = [
            re.compile(p, re.MULTILINE | re.DOTALL) 
            for p in self.ARTICLE_PATTERNS
        ]
        
        logger.info(f"✅ SemanticChunker {self.VERSION} 초기화")
        logger.info(f"   🎯 목표: {target_size}자, 최소: {min_size}자")
        logger.info(f"   📋 조문 패턴: {len(self.article_patterns)}개")
        logger.info(f"   🚫 청크=0 → 예외 발생 (하드 실패)")
    
    def chunk(self, text: str, doc_type: str = 'statute') -> List[Dict[str, Any]]:
        """
        ✅ P2: 텍스트를 의미 단위로 청킹
        
        Args:
            text: 입력 텍스트
            doc_type: 문서 타입
        
        Returns:
            청크 리스트
        
        Raises:
            RuntimeError: 청크=0인 경우
        """
        logger.info(f"   ✂️ SemanticChunker {self.VERSION} 시작")
        
        # 입력 검증
        if not text or len(text.strip()) < 10:
            error_msg = f"❌ 청킹 실패: 입력 텍스트가 너무 짧음 ({len(text)}자)"
            logger.error(f"      {error_msg}")
            raise RuntimeError(error_msg)
        
        # 1. 기본 청킹
        chunks = self._basic_chunk(text, doc_type)
        logger.info(f"      기본 청킹: {len(chunks)}개")
        
        # ✅ P2: 청크=0 Fallback
        if not chunks:
            logger.warning(f"      ⚠️ 기본 청킹 실패 → Fallback 길이 기반 청킹")
            chunks = self._fallback_length_based_chunk(text)
            logger.info(f"      Fallback 청킹: {len(chunks)}개")
        
        # 2. 경계 검증 + 병합
        validated = self._validate_boundaries(chunks)
        logger.info(f"      경계 검증: {len(validated)}개")
        
        # 3. 조문 정렬 (statute만)
        if doc_type == 'statute' and validated:
            sorted_chunks = self._sort_by_article(validated)
        else:
            sorted_chunks = validated
        
        # ✅ P2: 최종 청크=0 하드 실패
        if not sorted_chunks:
            error_msg = "❌ 청킹 하드 실패: 0개 청크 생성 (Fallback도 실패)"
            logger.error(f"      {error_msg}")
            logger.error(f"      입력 길이: {len(text)}자")
            logger.error(f"      문서 타입: {doc_type}")
            raise RuntimeError(error_msg)
        
        logger.info(f"   ✅ 청킹 완료: {len(sorted_chunks)}개")
        
        return sorted_chunks
    
    def _basic_chunk(self, text: str, doc_type: str) -> List[Dict[str, Any]]:
        """
        ✅ P2: 기본 청킹 (강화된 조문 패턴)
        """
        chunks = []
        
        if doc_type == 'statute':
            # ✅ P2: 여러 패턴 시도
            matches = []
            
            for pattern in self.article_patterns:
                found = pattern.findall(text)
                if found:
                    matches.extend(found)
                    logger.info(f"      📋 패턴 매칭: {len(found)}개")
            
            # 중복 제거 (같은 조문을 여러 패턴이 잡을 수 있음)
            seen_articles = set()
            unique_matches = []
            
            for match in matches:
                # 조문 번호 추출
                article_match = re.search(r'제(\d+)조', match)
                if article_match:
                    article_num = article_match.group(1)
                    
                    if article_num not in seen_articles:
                        seen_articles.add(article_num)
                        unique_matches.append(match)
            
            logger.info(f"      📋 고유 조문: {len(unique_matches)}개")
            
            # 청크 생성
            for match in unique_matches:
                article_match = re.search(r'제(\d+)조(?:의(\d+))?', match)
                article_no = article_match.group(0) if article_match else ''
                
                title_match = re.search(r'제\d+조(?:의\d+)?\s*\(([^)]+)\)', match)
                article_title = title_match.group(1) if title_match else ''
                
                # 정리
                content = match.strip()
                
                # 헤딩 마커 제거 (중복 방지)
                content = re.sub(r'^#{1,4}\s*', '', content, flags=re.MULTILINE)
                content = re.sub(r'\*\*', '', content)
                
                chunks.append({
                    'content': content,
                    'metadata': {
                        'article_no': article_no,
                        'article_title': article_title,
                        'char_count': len(content),
                        'chunk_index': len(chunks) + 1
                    }
                })
        
        else:
            # 일반 문서: 문장 단위
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current_chunk = []
            current_size = 0
            
            for sentence in sentences:
                if current_size + len(sentence) > self.target_size and current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'content': chunk_text,
                        'metadata': {
                            'article_no': '',
                            'article_title': '',
                            'char_count': len(chunk_text),
                            'chunk_index': len(chunks) + 1
                        }
                    })
                    current_chunk = []
                    current_size = 0
                
                current_chunk.append(sentence)
                current_size += len(sentence)
            
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'article_no': '',
                        'article_title': '',
                        'char_count': len(chunk_text),
                        'chunk_index': len(chunks) + 1
                    }
                })
        
        return chunks
    
    def _fallback_length_based_chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        ✅ P2: Fallback 길이 기반 청킹 (의무)
        """
        logger.warning("      🔧 Fallback 길이 기반 청킹 시작")
        
        chunks = []
        text_length = len(text)
        
        start = 0
        chunk_index = 1
        
        while start < text_length:
            end = min(start + self.target_size, text_length)
            
            # 문장 중간이면 다음 마침표까지 확장
            if end < text_length:
                search_end = min(end + 200, text_length)
                text_segment = text[end:search_end]
                
                period_match = re.search(r'[.!?]\s', text_segment)
                if period_match:
                    end += period_match.end()
            
            chunk_text = text[start:end].strip()
            
            # 최소 크기 체크
            if len(chunk_text) >= self.min_size or start == 0:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'article_no': '',
                        'article_title': '',
                        'char_count': len(chunk_text),
                        'chunk_index': chunk_index,
                        'fallback': True
                    }
                })
                chunk_index += 1
            
            start = end
        
        logger.info(f"      ✅ Fallback 청킹: {len(chunks)}개 생성")
        
        return chunks
    
    def _validate_boundaries(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """경계 검증 + 자동 병합"""
        validated = []
        i = 0
        
        while i < len(chunks):
            chunk = chunks[i]
            content = chunk['content']
            
            is_complete = self._is_sentence_boundary(content)
            
            if not is_complete and i + 1 < len(chunks):
                # 불완전 → 병합
                logger.warning(f"      ⚠️ 불완전 청크: '{content[-50:]}'")
                next_chunk = chunks[i + 1]
                
                merged_content = content + '\n\n' + next_chunk['content']
                merged_chunk = {
                    'content': merged_content,
                    'metadata': {
                        'article_no': chunk['metadata']['article_no'] or next_chunk['metadata']['article_no'],
                        'article_title': chunk['metadata']['article_title'] or next_chunk['metadata']['article_title'],
                        'char_count': len(merged_content),
                        'chunk_index': len(validated) + 1,
                        'merged': True
                    }
                }
                
                validated.append(merged_chunk)
                logger.info(f"      ✅ 자동 병합: Chunk {i+1} + {i+2}")
                i += 2
            else:
                validated.append(chunk)
                i += 1
        
        return validated
    
    def _is_sentence_boundary(self, text: str) -> bool:
        """문장 경계 검사"""
        text_end = text.strip()[-100:]
        
        # 완전한 종결 확인
        for pattern in self.sentence_patterns:
            if pattern.search(text_end):
                return True
        
        # 불완전 종결 확인
        for pattern in self.incomplete_patterns:
            if pattern.search(text_end):
                return False
        
        return True
    
    def _sort_by_article(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """조문 번호 기준 정렬"""
        def extract_article_number(chunk: Dict[str, Any]) -> Tuple[int, int]:
            article_no = chunk['metadata'].get('article_no', '')
            
            if not article_no:
                return (999, 0)
            
            main_match = re.search(r'제(\d+)조', article_no)
            sub_match = re.search(r'제\d+조의(\d+)', article_no)
            
            main_num = int(main_match.group(1)) if main_match else 999
            sub_num = int(sub_match.group(1)) if sub_match else 0
            
            return (main_num, sub_num)
        
        sorted_chunks = sorted(chunks, key=extract_article_number)
        
        # chunk_index 재부여
        for i, chunk in enumerate(sorted_chunks, 1):
            chunk['metadata']['chunk_index'] = i
        
        return sorted_chunks
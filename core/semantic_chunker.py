"""
core/semantic_chunker.py
PRISM Phase 0.3.2 - Semantic Chunker (문장 경계 보존)

✅ Phase 0.3.2 개선:
1. 문장 경계 보존 분할 추가
2. 최소 청크 크기 가드 (300자)
3. 한국어 문장 경계 패턴

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-07
Version: Phase 0.3.2
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 0.3.2 의미 기반 청킹 엔진 (문장 경계 보존)
    
    ✅ Phase 0.3.2 개선:
    - 문장 경계 보존 분할
    - 최소 청크 크기 가드
    - 한국어 문장 패턴
    """
    
    VERSION = "Phase 0.3.2"
    
    # 청크 크기 설정
    MIN_SIZE = 300      # ✅ Phase 0.3.2: 최소 크기 가드
    TARGET_SIZE = 900
    MAX_SIZE = 1200
    
    # 조문 패턴
    ARTICLE_PATTERN = re.compile(
        r'#{1,6}\s*제\d+조(?:의\d+)?(?:\([^)]+\))?',
        re.MULTILINE
    )
    
    # ✅ Phase 0.3.2: 한국어 문장 경계 패턴 (GPT 제안)
    SENTENCE_PATTERN = re.compile(
        r'(?<=[다|요|임|함|음])\s+',  # 한국어 문장 끝
        re.MULTILINE
    )
    
    # Fallback: 영어식 문장 경계
    SENTENCE_PATTERN_EN = re.compile(
        r'(?<=[.!?])\s+',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info(f"✅ SemanticChunker {self.VERSION} 초기화")
        logger.info(f"   청크 크기: {self.MIN_SIZE}-{self.MAX_SIZE} (목표: {self.TARGET_SIZE})")
        logger.info(f"   최소 가드: {self.MIN_SIZE}자")
        logger.info(f"   하드 가드: {self.MAX_SIZE}자 강제 flush")
        logger.info(f"   Fail-safe: 조문 < 2개 시 길이 분할")
        logger.info(f"   조문 패턴: ### 헤더 지원")
        logger.info(f"   ✅ 문장 경계 보존: 한국어 패턴")
    
    def chunk(
        self,
        text: str,
        doc_type: str = 'statute',
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        텍스트를 의미 단위로 청킹
        
        Args:
            text: 원본 텍스트
            doc_type: 문서 타입
            metadata: 메타데이터
        
        Returns:
            청크 리스트
        """
        logger.info(f"🔗 SemanticChunking {self.VERSION} 시작: {len(text)} 글자")
        
        # ✅ 1단계: 조문 경계 탐지
        boundaries = self._find_article_boundaries(text)
        
        if len(boundaries) < 2:
            logger.warning(f"  ⚠️ 조문 경계 부족 ({len(boundaries)}개) - Fail-safe 길이 분할")
            return self._fallback_chunk(text, metadata)
        
        logger.info(f"   조문 감지: {len(boundaries)}개")
        
        # ✅ 2단계: 조문 기반 초기 분할
        sections = self._split_by_articles(text, boundaries)
        
        # ✅ Phase 0.3.2: 3단계: 문장 경계 보존 분할
        adjusted_sections = []
        for section in sections:
            if len(section) > self.MAX_SIZE:
                # 문장 경계 기반 분할
                split_sections = self._split_with_sentence_boundary(section, self.MAX_SIZE)
                adjusted_sections.extend(split_sections)
            else:
                adjusted_sections.append(section)
        
        logger.info(f"   길이 조정 후: {len(adjusted_sections)}개 섹션")
        
        # ✅ Phase 0.3.2: 4단계: 최소 크기 가드
        adjusted_sections = self._merge_short_chunks(adjusted_sections, self.MIN_SIZE)
        
        # ✅ 5단계: 청크 생성
        chunks = self._create_chunks(adjusted_sections, metadata)
        
        logger.info(f"   ✅ {len(chunks)}개 청크 생성")
        
        return chunks
    
    def _find_article_boundaries(self, text: str) -> List[Tuple[int, str]]:
        """
        조문 경계 탐지
        
        Args:
            text: 원본 텍스트
        
        Returns:
            [(위치, 조문 헤더), ...]
        """
        boundaries = []
        
        for match in self.ARTICLE_PATTERN.finditer(text):
            boundaries.append((match.start(), match.group()))
        
        return boundaries
    
    def _split_by_articles(
        self,
        text: str,
        boundaries: List[Tuple[int, str]]
    ) -> List[str]:
        """
        조문 경계 기반 분할
        
        Args:
            text: 원본 텍스트
            boundaries: 조문 경계
        
        Returns:
            분할된 섹션 리스트
        """
        sections = []
        
        for i in range(len(boundaries)):
            start = boundaries[i][0]
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            
            section = text[start:end].strip()
            if section:
                sections.append(section)
        
        return sections
    
    def _split_with_sentence_boundary(
        self,
        text: str,
        max_size: int
    ) -> List[str]:
        """
        ✅ Phase 0.3.2: 문장 경계 보존 분할 (GPT 제안)
        
        Args:
            text: 원본 텍스트
            max_size: 최대 크기
        
        Returns:
            분할된 섹션 리스트
        """
        # 한국어 문장 분할 시도
        sentences = self.SENTENCE_PATTERN.split(text)
        
        # 한국어 패턴 실패 시 영어 패턴 사용
        if len(sentences) == 1:
            sentences = self.SENTENCE_PATTERN_EN.split(text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_len = len(sentence)
            
            # 하드 가드 도달 시 문장 단위로 분할
            if current_size + sentence_len > max_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_len
            else:
                current_chunk.append(sentence)
                current_size += sentence_len
        
        # 마지막 청크
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _merge_short_chunks(
        self,
        chunks: List[str],
        min_size: int
    ) -> List[str]:
        """
        ✅ Phase 0.3.2: 짧은 청크 병합 (GPT 제안)
        
        Args:
            chunks: 청크 리스트
            min_size: 최소 크기
        
        Returns:
            병합된 청크 리스트
        """
        merged = []
        i = 0
        
        while i < len(chunks):
            chunk = chunks[i]
            
            # 마지막 청크거나 충분히 긴 경우
            if i == len(chunks) - 1 or len(chunk) >= min_size:
                merged.append(chunk)
                i += 1
            # 다음 청크와 병합
            else:
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    merged.append(chunk + '\n\n' + next_chunk)
                    i += 2
                else:
                    merged.append(chunk)
                    i += 1
        
        return merged
    
    def _create_chunks(
        self,
        sections: List[str],
        base_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        청크 객체 생성
        
        Args:
            sections: 섹션 리스트
            base_metadata: 기본 메타데이터
        
        Returns:
            청크 리스트
        """
        chunks = []
        
        for i, section in enumerate(sections, 1):
            # 조문 번호 추출
            article_match = self.ARTICLE_PATTERN.search(section)
            article_no = article_match.group() if article_match else f"섹션{i}"
            
            # 조문 제목 추출
            article_title = ""
            if article_match:
                title_match = re.search(r'\(([^)]+)\)', article_match.group())
                if title_match:
                    article_title = title_match.group(1)
            
            metadata = {
                'article_no': article_no.replace('#', '').strip(),
                'article_title': article_title,
                'char_count': len(section),
                'chunk_index': i
            }
            
            if base_metadata:
                metadata.update(base_metadata)
            
            chunks.append({
                'id': f'chunk_{i}',
                'content': section,
                'metadata': metadata
            })
        
        return chunks
    
    def _fallback_chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Fail-safe 길이 기반 분할
        
        Args:
            text: 원본 텍스트
            metadata: 메타데이터
        
        Returns:
            청크 리스트
        """
        chunks = []
        start = 0
        chunk_index = 1
        
        while start < len(text):
            end = min(start + self.TARGET_SIZE, len(text))
            
            # 문장 경계 찾기
            if end < len(text):
                # 한국어 문장 끝 찾기
                for pattern in [r'[다|요|임|함|음]\s', r'[.!?]\s']:
                    match = re.search(pattern, text[end:end+100])
                    if match:
                        end += match.end()
                        break
            
            section = text[start:end].strip()
            
            if section:
                chunk = {
                    'id': f'chunk_{chunk_index}',
                    'content': section,
                    'metadata': {
                        'article_no': f'섹션{chunk_index}',
                        'article_title': '',
                        'char_count': len(section),
                        'chunk_index': chunk_index
                    }
                }
                
                if metadata:
                    chunk['metadata'].update(metadata)
                
                chunks.append(chunk)
                chunk_index += 1
            
            start = end
        
        return chunks
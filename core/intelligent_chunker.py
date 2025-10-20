"""
PRISM Phase 2.7 - Intelligent Chunker
의미 기반 청킹 + 고유 ID 생성

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
Update: 청크 ID 고유화 (RAG 최적화)
"""

import re
import hashlib
from typing import List, Dict
from dataclasses import dataclass, asdict


@dataclass
class Chunk:
    """청크 데이터"""
    chunk_id: str          # 고유 ID (해시 기반)
    page_num: int
    content: str
    type: str              # 'text', 'chart', 'table', 'image'
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return asdict(self)


class IntelligentChunker:
    """
    의미 기반 청킹
    
    전략:
    - TEXT: 문장 단위 (100-500 토큰)
    - CHART: 단일 차트 = 1 청크
    - TABLE: 단일 표 = 1 청크  
    - IMAGE: 단일 이미지 = 1 청크
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap: int = 50
    ):
        """
        초기화
        
        Args:
            min_chunk_size: 최소 청크 크기 (토큰)
            max_chunk_size: 최대 청크 크기 (토큰)
            overlap: 청크 간 중복 (토큰)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        print("✅ IntelligentChunker initialized")
        print(f"   Chunk size: {min_chunk_size}-{max_chunk_size} tokens")
        print(f"   Overlap: {overlap} tokens")
    
    def chunk_region(
        self,
        content: str,
        region_type: str,
        page_num: int,
        section_path: str,
        source: str
    ) -> List[Chunk]:
        """
        영역별 청킹
        
        Args:
            content: 추출된 컨텐츠
            region_type: 'text', 'chart', 'table', 'image'
            page_num: 페이지 번호
            section_path: 섹션 경로
            source: 'ocr', 'vlm'
            
        Returns:
            청크 리스트
        """
        
        if region_type in ['chart', 'table', 'image']:
            # 비텍스트는 분할하지 않음
            return self._create_single_chunk(
                content, region_type, page_num, section_path, source
            )
        
        elif region_type == 'text':
            # 텍스트는 의미 단위로 분할
            return self._chunk_text(
                content, page_num, section_path, source
            )
        
        else:
            # 기타 타입도 단일 청크
            return self._create_single_chunk(
                content, region_type, page_num, section_path, source
            )
    
    def _create_single_chunk(
        self,
        content: str,
        chunk_type: str,
        page_num: int,
        section_path: str,
        source: str
    ) -> List[Chunk]:
        """단일 청크 생성 (차트/표/이미지)"""
        
        # 고유 ID 생성 (해시 기반)
        chunk_id = self._generate_unique_id(
            page_num=page_num,
            chunk_type=chunk_type,
            content=content,
            section_path=section_path
        )
        
        chunk = Chunk(
            chunk_id=chunk_id,
            page_num=page_num,
            content=content,
            type=chunk_type,
            metadata={
                'section_path': section_path,
                'token_count': self._estimate_tokens(content),
                'source': source
            }
        )
        
        return [chunk]
    
    def _chunk_text(
        self,
        text: str,
        page_num: int,
        section_path: str,
        source: str
    ) -> List[Chunk]:
        """텍스트 청킹 (의미 단위)"""
        
        if not text or len(text.strip()) == 0:
            return []
        
        # 문장 분리
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            # 청크 크기 체크
            if current_tokens + sentence_tokens > self.max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = ' '.join(current_chunk)
                chunk_id = self._generate_unique_id(
                    page_num=page_num,
                    chunk_type='text',
                    content=chunk_text,
                    section_path=section_path,
                    index=len(chunks)  # 인덱스 추가
                )
                
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    page_num=page_num,
                    content=chunk_text,
                    type='text',
                    metadata={
                        'section_path': section_path,
                        'token_count': current_tokens,
                        'source': source
                    }
                ))
                
                # 오버랩을 위해 마지막 문장 유지
                if self.overlap > 0:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
            
            # 문장 추가
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # 마지막 청크
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk_id = self._generate_unique_id(
                page_num=page_num,
                chunk_type='text',
                content=chunk_text,
                section_path=section_path,
                index=len(chunks)
            )
            
            chunks.append(Chunk(
                chunk_id=chunk_id,
                page_num=page_num,
                content=chunk_text,
                type='text',
                metadata={
                    'section_path': section_path,
                    'token_count': current_tokens,
                    'source': source
                }
            ))
        
        return chunks
    
    def _generate_unique_id(
        self,
        page_num: int,
        chunk_type: str,
        content: str,
        section_path: str,
        index: int = 0
    ) -> str:
        """
        고유 청크 ID 생성 (RAG 최적화)
        
        전략: page + type + 컨텐츠 해시 + 인덱스
        
        예시:
        - p001_text_a3f2b9c1_000
        - p002_chart_7d4e8f23
        - p003_table_9c1a5b6e
        
        장점:
        - 완전 고유 (중복 불가)
        - 정렬 가능 (페이지순)
        - 추적 가능 (타입 확인)
        - 재현 가능 (같은 컨텐츠 = 같은 ID)
        """
        
        # 컨텐츠 해시 (짧게)
        content_hash = hashlib.md5(
            (content + section_path).encode('utf-8')
        ).hexdigest()[:8]
        
        # ID 생성
        if chunk_type == 'text' and index > 0:
            # 텍스트 청크는 인덱스 포함
            chunk_id = f"p{page_num:03d}_{chunk_type}_{content_hash}_{index:03d}"
        else:
            # 비텍스트는 인덱스 없음
            chunk_id = f"p{page_num:03d}_{chunk_type}_{content_hash}"
        
        return chunk_id
    
    def _split_sentences(self, text: str) -> List[str]:
        """문장 분리"""
        
        # 한글/영어 문장 종결 패턴
        sentence_endings = r'[.!?。！？]\s+'
        
        sentences = re.split(sentence_endings, text)
        
        # 빈 문장 제거
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (간단)"""
        
        # 한글: 2글자 = 1토큰
        # 영어: 4글자 = 1토큰
        
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        numbers = len(re.findall(r'\d+', text))
        
        tokens = (korean_chars // 2) + (english_words // 4) + numbers
        
        return max(tokens, 1)
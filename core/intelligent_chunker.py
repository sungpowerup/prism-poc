"""
core/intelligent_chunker.py
지능형 청킹 (문장 단위)

개선 사항:
- 문장 경계에서만 분할
- 의미 단위 보존
- 오버랩 지원
"""

import re
from typing import List


class IntelligentChunker:
    """
    문장 단위 지능형 청킹
    
    특징:
    - 문장 경계 존중 (온점, 느낌표, 물음표)
    - 문맥 보존을 위한 오버랩
    - 최소/최대 길이 제약
    """
    
    def __init__(
        self, 
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap: int = 50
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기 (글자)
            max_chunk_size: 최대 청크 크기 (글자)
            overlap: 오버랩 크기 (글자)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        # 문장 종결 패턴
        self.sentence_endings = re.compile(r'[.!?]\s+|[.!?]$')
    
    def chunk_text(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 청킹
        
        Args:
            text: 원본 텍스트
        
        Returns:
            청크 리스트
        """
        if len(text) <= self.max_chunk_size:
            # 짧은 텍스트는 그대로 반환
            return [text]
        
        # 1. 문장 분리
        sentences = self._split_sentences(text)
        
        # 2. 청크 생성
        chunks = self._create_chunks(sentences)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장으로 분리
        
        한국어 특성 고려:
        - 온점(.), 느낌표(!), 물음표(?)
        - 줄바꿈(\n) 존중
        """
        # 줄바꿈 기준으로 1차 분리
        paragraphs = text.split('\n')
        
        sentences = []
        for para in paragraphs:
            if not para.strip():
                continue
            
            # 문장 종결 기준으로 분리
            parts = self.sentence_endings.split(para)
            
            for i, part in enumerate(parts):
                if not part.strip():
                    continue
                
                # 종결부호 복원
                if i < len(parts) - 1:
                    sentences.append(part.strip() + '.')
                else:
                    sentences.append(part.strip())
        
        return sentences
    
    def _create_chunks(self, sentences: List[str]) -> List[str]:
        """
        문장들을 청크로 묶기
        
        전략:
        1. 최대 길이를 넘지 않는 선에서 문장들을 묶음
        2. 최소 길이보다 짧으면 다음 문장과 합침
        3. 오버랩을 위해 이전 청크의 마지막 문장 포함
        """
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, sent in enumerate(sentences):
            sent_length = len(sent)
            
            # 현재 청크에 추가했을 때 최대 길이 초과?
            if current_length + sent_length > self.max_chunk_size:
                if current_chunk:
                    # 현재 청크 저장
                    chunks.append(' '.join(current_chunk))
                    
                    # 오버랩: 마지막 문장을 다음 청크 시작에 포함
                    if self.overlap > 0 and len(current_chunk) > 0:
                        overlap_sentences = self._get_overlap_sentences(current_chunk)
                        current_chunk = overlap_sentences
                        current_length = sum(len(s) for s in current_chunk)
                    else:
                        current_chunk = []
                        current_length = 0
            
            # 문장 추가
            current_chunk.append(sent)
            current_length += sent_length
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # 최소 길이 체크 및 병합
        chunks = self._merge_small_chunks(chunks)
        
        return chunks
    
    def _get_overlap_sentences(self, chunk: List[str]) -> List[str]:
        """
        오버랩을 위한 문장들 추출
        
        마지막 문장부터 역순으로 오버랩 크기만큼 추출
        """
        overlap_sentences = []
        overlap_length = 0
        
        for sent in reversed(chunk):
            if overlap_length + len(sent) > self.overlap:
                break
            overlap_sentences.insert(0, sent)
            overlap_length += len(sent)
        
        return overlap_sentences
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        너무 짧은 청크를 이전/다음 청크와 병합
        """
        if not chunks:
            return []
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # 최소 길이보다 짧고, 다음 청크가 있으면 병합
            if len(current) < self.min_chunk_size and i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                merged_chunk = current + ' ' + next_chunk
                
                # 병합해도 최대 길이 이내면 병합
                if len(merged_chunk) <= self.max_chunk_size:
                    merged.append(merged_chunk)
                    i += 2  # 2개 건너뛰기
                    continue
            
            merged.append(current)
            i += 1
        
        return merged


class SemanticChunker(IntelligentChunker):
    """
    의미 기반 청킹 (추후 확장)
    
    TODO:
    - Sentence Transformer 기반 유사도 계산
    - 의미적으로 유사한 문장끼리 묶기
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def chunk_by_similarity(self, text: str, threshold: float = 0.7) -> List[str]:
        """
        의미 유사도 기반 청킹
        
        Args:
            text: 원본 텍스트
            threshold: 유사도 임계값 (0~1)
        
        Returns:
            청크 리스트
        """
        # TODO: 구현
        # 1. 문장 임베딩
        # 2. 유사도 계산
        # 3. 유사한 문장끼리 그룹화
        
        # 현재는 기본 청킹 사용
        return self.chunk_text(text)
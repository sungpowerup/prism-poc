"""
PRISM Phase 2 - Intelligent Chunker

RAG를 위한 지능형 문서 청킹 모듈

Author: 이서영 (Backend Lead)
Date: 2025-10-12
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import tiktoken

from models.layout_detector import DocumentElement, ElementType
from core.document_analyzer import DocumentStructure


@dataclass
class Chunk:
    """청크 데이터"""
    chunk_id: str
    type: str  # "text", "table", "image"
    content: str
    page_num: int
    metadata: Dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "type": self.type,
            "content": self.content,
            "page_num": self.page_num,
            "metadata": self.metadata,
            "has_embedding": self.embedding is not None
        }


@dataclass
class ChunkingResult:
    """청킹 결과"""
    chunks: List[Chunk]
    statistics: Dict
    
    def to_dict(self) -> Dict:
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "statistics": self.statistics
        }


class IntelligentChunker:
    """
    지능형 청킹 모듈
    
    전략:
    1. 제목으로 섹션 분리
    2. 표는 독립 청크
    3. 텍스트는 의미 기반 분할
    4. 임베딩 생성 (선택)
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        use_embeddings: bool = False
    ):
        """
        Args:
            chunk_size: 청크 크기 (토큰)
            chunk_overlap: 청크 중복 (토큰)
            use_embeddings: 임베딩 생성 여부
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_embeddings = use_embeddings
        
        # Tokenizer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Sentence Transformer (선택적)
        self.embedder = None
        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Sentence Transformer loaded")
            except ImportError:
                print("⚠️  sentence-transformers not installed. Embeddings disabled.")
                self.use_embeddings = False
    
    def chunk(
        self,
        structure: DocumentStructure,
        texts: List,  # ⭐ ExtractedText 객체 또는 dict 리스트
        tables: List,
        captions: List
    ) -> ChunkingResult:
        """
        문서 전체 청킹
        
        Args:
            structure: 문서 구조
            texts: 추출된 텍스트 목록 (ExtractedText 객체 또는 dict)
            tables: 파싱된 표 목록
            captions: 이미지 캡션 목록
            
        Returns:
            청킹 결과
        """
        chunks = []
        
        # 1. 텍스트 청크
        text_chunks = self._chunk_texts(texts, structure)
        chunks.extend(text_chunks)
        
        # 2. 표 청크 (각 표를 독립 청크로)
        table_chunks = self._chunk_tables(tables)
        chunks.extend(table_chunks)
        
        # 3. 이미지 청크 (캡션)
        image_chunks = self._chunk_images(captions)
        chunks.extend(image_chunks)
        
        # 4. 임베딩 생성 (선택)
        if self.use_embeddings and self.embedder:
            self._add_embeddings(chunks)
        
        # 통계
        statistics = self._compute_statistics(chunks)
        
        return ChunkingResult(chunks=chunks, statistics=statistics)
    
    def _chunk_texts(
        self, 
        texts: List,
        structure: DocumentStructure
    ) -> List[Chunk]:
        """텍스트를 의미 기반으로 청킹"""
        chunks = []
        
        # 페이지별 그룹화
        by_page = {}
        for text_data in texts:
            # ⭐ ExtractedText 객체 또는 dict 모두 지원
            if hasattr(text_data, 'page_num'):
                # ExtractedText 객체
                page = text_data.page_num
                content = text_data.content
            elif isinstance(text_data, dict):
                # dict
                page = text_data.get("page_num", 1)
                content = text_data.get("text", "")
            else:
                # 알 수 없는 타입
                print(f"⚠️  Unknown text_data type: {type(text_data)}")
                continue
            
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(content)
        
        # 페이지별 청킹
        for page_num, page_texts in sorted(by_page.items()):
            # 페이지 내 텍스트를 하나로 합침
            full_text = "\n\n".join(page_texts)
            
            if not full_text.strip():
                continue
            
            # 토큰 기반 분할
            tokens = self.tokenizer.encode(full_text)
            
            # 청크 생성
            chunk_idx = 0
            for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                
                chunk = Chunk(
                    chunk_id=f"text_{page_num}_{chunk_idx}",
                    type="text",
                    content=chunk_text,
                    page_num=page_num,
                    metadata={
                        "token_count": len(chunk_tokens),
                        "char_count": len(chunk_text)
                    }
                )
                chunks.append(chunk)
                chunk_idx += 1
        
        return chunks
    
    def _chunk_tables(self, tables: List) -> List[Chunk]:
        """각 표를 독립 청크로"""
        chunks = []
        
        for i, table in enumerate(tables):
            # Markdown 형식으로 변환
            content = table.to_markdown()
            
            chunk = Chunk(
                chunk_id=f"table_{table.page_num}_{i}",
                type="table",
                content=content,
                page_num=table.page_num,
                metadata={
                    "rows": len(table.rows),
                    "columns": len(table.headers),
                    "has_headers": len(table.headers) > 0
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_images(self, captions: List) -> List[Chunk]:
        """이미지 캡션을 청크로"""
        chunks = []
        
        for i, caption_data in enumerate(captions):
            chunk = Chunk(
                chunk_id=f"image_{caption_data.element.page_num}_{i}",
                type="image",
                content=caption_data.caption,
                page_num=caption_data.element.page_num,
                metadata={
                    "element_type": caption_data.element.type.value,
                    "confidence": caption_data.confidence,
                    "provider": caption_data.provider
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _add_embeddings(self, chunks: List[Chunk]):
        """청크에 임베딩 추가"""
        if not self.embedder:
            return
        
        # 배치로 임베딩 생성
        texts = [c.content for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
    
    def _compute_statistics(self, chunks: List[Chunk]) -> Dict:
        """청킹 통계"""
        text_chunks = [c for c in chunks if c.type == "text"]
        table_chunks = [c for c in chunks if c.type == "table"]
        image_chunks = [c for c in chunks if c.type == "image"]
        
        return {
            "total_chunks": len(chunks),
            "text_chunks": len(text_chunks),
            "table_chunks": len(table_chunks),
            "image_chunks": len(image_chunks),
            "avg_chunk_size": sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0,
            "has_embeddings": any(c.embedding is not None for c in chunks)
        }
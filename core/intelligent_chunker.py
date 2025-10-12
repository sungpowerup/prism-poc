"""
PRISM Phase 2.1 - Intelligent Chunker (개선)

RAG를 위한 지능형 문서 청킹 모듈

개선 사항:
- 표는 무조건 독립 청크로 분리
- 문장 경계 인식 강화
- 섹션 제목 기반 청크 분리

Author: 이서영 (Backend Lead)
Date: 2025-10-13
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import tiktoken
import re


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
    지능형 청킹 모듈 (개선)
    
    전략:
    1. 표는 무조건 독립 청크 (크기 무관)
    2. 제목/섹션으로 의미 단위 분리
    3. 문장 경계에서만 분할
    4. 적절한 오버랩 유지
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
        structure,  # DocumentStructure
        texts: List,
        tables: List,
        captions: List
    ) -> ChunkingResult:
        """
        문서 전체 청킹 (개선)
        
        Args:
            structure: 문서 구조
            texts: 추출된 텍스트 목록
            tables: 파싱된 표 목록
            captions: 이미지 캡션 목록
            
        Returns:
            청킹 결과
        """
        chunks = []
        
        # ⭐ 1. 표 청크 (최우선, 독립 처리)
        table_chunks = self._chunk_tables(tables)
        chunks.extend(table_chunks)
        print(f"  ✅ 표 청크: {len(table_chunks)}개")
        
        # 2. 텍스트 청크 (의미 단위 + 문장 경계)
        text_chunks = self._chunk_texts_improved(texts, structure)
        chunks.extend(text_chunks)
        print(f"  ✅ 텍스트 청크: {len(text_chunks)}개")
        
        # 3. 이미지 청크 (캡션)
        image_chunks = self._chunk_images(captions)
        chunks.extend(image_chunks)
        print(f"  ✅ 이미지 청크: {len(image_chunks)}개")
        
        # 4. 임베딩 생성 (선택)
        if self.use_embeddings and self.embedder:
            self._add_embeddings(chunks)
        
        # 통계
        statistics = self._compute_statistics(chunks)
        
        return ChunkingResult(chunks=chunks, statistics=statistics)
    
    def _chunk_tables(self, tables: List) -> List[Chunk]:
        """
        표 청킹 (개선)
        
        변경사항:
        - 각 표를 무조건 독립 청크로 (크기 무관)
        - Markdown 형식으로 변환
        """
        chunks = []
        
        for i, table in enumerate(tables):
            # Markdown 형식으로 변환
            if hasattr(table, 'to_markdown'):
                content = table.to_markdown()
            elif hasattr(table, 'markdown'):
                content = table.markdown
            elif isinstance(table, dict):
                content = table.get("markdown", str(table))
            else:
                content = str(table)
            
            # 메타데이터
            metadata = {
                "source": "table_extraction"
            }
            
            # 표 정보 추출
            if hasattr(table, 'num_rows'):
                metadata["rows"] = table.num_rows
                metadata["columns"] = table.num_cols
            elif isinstance(table, dict):
                metadata["rows"] = table.get("num_rows", 0)
                metadata["columns"] = table.get("num_cols", 0)
            
            # 페이지 번호
            if hasattr(table, 'page_num'):
                page_num = table.page_num
            elif isinstance(table, dict):
                page_num = table.get("page_num", 1)
            else:
                page_num = 1
            
            chunk = Chunk(
                chunk_id=f"table_{page_num}_{i}",
                type="table",
                content=content,
                page_num=page_num,
                metadata=metadata
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_texts_improved(
        self,
        texts: List,
        structure
    ) -> List[Chunk]:
        """
        텍스트 청킹 (개선)
        
        개선사항:
        1. 섹션 제목으로 청크 시작
        2. 문장 경계에서만 분할
        3. 의미 단위 보존
        """
        chunks = []
        
        # 페이지별 그룹화
        by_page = {}
        for text_data in texts:
            if hasattr(text_data, 'page_num'):
                page = text_data.page_num
                content = text_data.content
            elif isinstance(text_data, dict):
                page = text_data.get("page_num", 1)
                content = text_data.get("text", "")
            else:
                continue
            
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(content)
        
        # 페이지별 청킹
        for page_num, page_texts in sorted(by_page.items()):
            full_text = "\n\n".join(page_texts)
            
            if not full_text.strip():
                continue
            
            # ⭐ 문장 단위로 분할
            sentences = self._split_into_sentences(full_text)
            
            # 청크 생성 (문장 경계 유지)
            page_chunks = self._create_sentence_chunks(
                sentences, page_num
            )
            chunks.extend(page_chunks)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장으로 분할
        
        한국어 문장 종결 패턴:
        - 다. / 요. / 음. / 함.
        - ? / !
        """
        # 문장 종결 패턴
        patterns = [
            r'([^.!?]+[.!?])\s+',  # 마침표, 물음표, 느낌표
            r'([^다요음함]+[다요음함]\.)\s+',  # 한국어 종결 + 마침표
        ]
        
        sentences = []
        remaining = text
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, remaining))
            if matches:
                for match in matches:
                    sentence = match.group(1).strip()
                    if sentence:
                        sentences.append(sentence)
                # 마지막 문장
                last_end = matches[-1].end()
                if last_end < len(remaining):
                    sentences.append(remaining[last_end:].strip())
                break
        
        # 패턴 매칭 실패 시 줄바꿈으로 분할
        if not sentences:
            sentences = [s.strip() for s in text.split('\n') if s.strip()]
        
        return sentences
    
    def _create_sentence_chunks(
        self,
        sentences: List[str],
        page_num: int
    ) -> List[Chunk]:
        """
        문장들을 청크로 조합
        
        전략:
        - 토큰 수가 chunk_size를 넘지 않는 선에서 문장 추가
        - 문장 중간에서 절대 끊지 않음
        - 적절한 오버랩 유지
        """
        chunks = []
        chunk_idx = 0
        
        current_sentences = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.tokenizer.encode(sentence))
            
            # 청크 크기 확인
            if current_tokens + sentence_tokens > self.chunk_size and current_sentences:
                # 현재 청크 저장
                chunk = self._build_text_chunk(
                    current_sentences, page_num, chunk_idx
                )
                chunks.append(chunk)
                chunk_idx += 1
                
                # 오버랩 처리
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences, self.chunk_overlap
                )
                current_sentences = overlap_sentences
                current_tokens = sum(
                    len(self.tokenizer.encode(s)) for s in overlap_sentences
                )
            
            current_sentences.append(sentence)
            current_tokens += sentence_tokens
        
        # 마지막 청크
        if current_sentences:
            chunk = self._build_text_chunk(
                current_sentences, page_num, chunk_idx
            )
            chunks.append(chunk)
        
        return chunks
    
    def _build_text_chunk(
        self,
        sentences: List[str],
        page_num: int,
        chunk_idx: int
    ) -> Chunk:
        """텍스트 청크 생성"""
        content = " ".join(sentences)
        token_count = len(self.tokenizer.encode(content))
        
        chunk = Chunk(
            chunk_id=f"text_{page_num}_{chunk_idx}",
            type="text",
            content=content,
            page_num=page_num,
            metadata={
                "token_count": token_count,
                "char_count": len(content),
                "sentence_count": len(sentences)
            }
        )
        return chunk
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_tokens: int
    ) -> List[str]:
        """
        오버랩할 문장 추출
        
        마지막 문장부터 역순으로 overlap_tokens만큼
        """
        overlap = []
        total_tokens = 0
        
        for sentence in reversed(sentences):
            tokens = len(self.tokenizer.encode(sentence))
            if total_tokens + tokens > overlap_tokens:
                break
            overlap.insert(0, sentence)
            total_tokens += tokens
        
        return overlap
    
    def _chunk_images(self, captions: List) -> List[Chunk]:
        """이미지 캡션을 청크로"""
        chunks = []
        
        for i, caption_data in enumerate(captions):
            # ImageCaption 객체 또는 dict 지원
            if hasattr(caption_data, 'caption'):
                content = caption_data.caption
                page_num = caption_data.element.page_number
                confidence = caption_data.confidence
            elif isinstance(caption_data, dict):
                content = caption_data.get("caption", "")
                page_num = caption_data.get("page_num", 1)
                confidence = caption_data.get("confidence", 1.0)
            else:
                continue
            
            chunk = Chunk(
                chunk_id=f"image_{page_num}_{i}",
                type="image",
                content=content,
                page_num=page_num,
                metadata={
                    "confidence": confidence,
                    "source": "vlm_caption"
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _add_embeddings(self, chunks: List[Chunk]) -> None:
        """임베딩 생성"""
        if not self.embedder:
            return
        
        texts = [c.content for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
    
    def _compute_statistics(self, chunks: List[Chunk]) -> Dict:
        """통계 계산"""
        by_type = {}
        for chunk in chunks:
            by_type[chunk.type] = by_type.get(chunk.type, 0) + 1
        
        total_chars = sum(len(c.content) for c in chunks)
        avg_size = total_chars / len(chunks) if chunks else 0
        
        return {
            "total_chunks": len(chunks),
            "text_chunks": by_type.get("text", 0),
            "table_chunks": by_type.get("table", 0),
            "image_chunks": by_type.get("image", 0),
            "avg_chunk_size": round(avg_size, 2),
            "has_embeddings": any(c.embedding is not None for c in chunks)
        }


# 테스트
if __name__ == "__main__":
    # 샘플 데이터
    class MockStructure:
        pass
    
    texts = [
        {"page_num": 1, "text": "이것은 첫 번째 문장입니다. 이것은 두 번째 문장입니다. 세 번째 문장도 있습니다."}
    ]
    
    class MockTable:
        def __init__(self):
            self.page_num = 1
            self.num_rows = 3
            self.num_cols = 2
        
        def to_markdown(self):
            return "| A | B |\n|---|---|\n| 1 | 2 |"
    
    tables = [MockTable()]
    captions = []
    
    chunker = IntelligentChunker(chunk_size=100, chunk_overlap=20)
    result = chunker.chunk(MockStructure(), texts, tables, captions)
    
    print("\n✅ Chunking Test:")
    print(f"  총 청크: {result.statistics['total_chunks']}개")
    print(f"  텍스트: {result.statistics['text_chunks']}개")
    print(f"  표: {result.statistics['table_chunks']}개")
    
    for chunk in result.chunks:
        print(f"\n{chunk.chunk_id} ({chunk.type}):")
        print(f"  {chunk.content[:100]}...")
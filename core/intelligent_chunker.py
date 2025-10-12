"""
PRISM Phase 2.3 - Intelligent Chunker (Phase 2.3 호환)

RAG를 위한 지능형 문서 청킹 모듈

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


class IntelligentChunker:
    """
    지능형 청킹 모듈 (Phase 2.3 호환)
    
    전략:
    1. DocumentElement 리스트를 받아서 처리
    2. 표는 무조건 독립 청크 (크기 무관)
    3. 제목/섹션으로 의미 단위 분리
    4. 문장 경계에서만 분할
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
    
    def create_chunks(self, elements: List) -> List[Chunk]:
        """
        ⭐ Phase 2.3용 create_chunks 메서드
        
        DocumentElement 리스트를 받아서 Chunk 리스트로 변환
        
        Args:
            elements: DocumentElement 리스트
            
        Returns:
            Chunk 리스트
        """
        from models.layout_detector import ElementType
        
        chunks = []
        
        # 페이지별로 그룹화
        by_page = {}
        for element in elements:
            page_num = element.metadata.get('page_num', 1)
            if page_num not in by_page:
                by_page[page_num] = {'text': [], 'table': []}
            
            if element.type == ElementType.TABLE:
                by_page[page_num]['table'].append(element)
            else:
                by_page[page_num]['text'].append(element)
        
        # 페이지별 처리
        for page_num in sorted(by_page.keys()):
            page_data = by_page[page_num]
            
            # 1. 표 청크 (독립 처리)
            for i, table_element in enumerate(page_data['table']):
                chunk = Chunk(
                    chunk_id=f"table_{page_num}_{i}",
                    type="table",
                    content=table_element.text or "",
                    page_num=page_num,
                    metadata={
                        "confidence": table_element.confidence,
                        "source": "claude_vision"
                    }
                )
                chunks.append(chunk)
            
            # 2. 텍스트 청크
            text_elements = page_data['text']
            if text_elements:
                # 모든 텍스트를 하나로 합침
                full_text = "\n\n".join(
                    element.text for element in text_elements if element.text
                )
                
                if full_text.strip():
                    # 문장으로 분할
                    sentences = self._split_into_sentences(full_text)
                    
                    # 청크 생성
                    text_chunks = self._create_sentence_chunks(sentences, page_num)
                    chunks.extend(text_chunks)
        
        # 임베딩 생성 (선택)
        if self.use_embeddings and self.embedder:
            self._add_embeddings(chunks)
        
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
            r'([^다요음함]+[다요음함]\.)' # 한국어 종결
        ]
        
        sentences = []
        remaining = text
        
        for pattern in patterns:
            matches = re.finditer(pattern, remaining)
            for match in matches:
                sentence = match.group(1).strip()
                if sentence:
                    sentences.append(sentence)
        
        # 패턴에 매칭되지 않은 나머지 텍스트
        if remaining.strip() and not sentences:
            # 패턴이 없으면 그냥 \n\n으로 분할
            sentences = [s.strip() for s in remaining.split('\n\n') if s.strip()]
        
        return sentences if sentences else [text]
    
    def _create_sentence_chunks(
        self,
        sentences: List[str],
        page_num: int
    ) -> List[Chunk]:
        """
        문장 리스트를 청크로 변환
        
        전략:
        - chunk_size 이하로 문장을 모음
        - 문장 경계에서만 분할
        - 오버랩 유지
        """
        chunks = []
        
        current_sentences = []
        current_tokens = 0
        chunk_idx = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.tokenizer.encode(sentence))
            
            # 현재 청크에 추가하면 chunk_size 초과하는 경우
            if current_tokens + sentence_tokens > self.chunk_size and current_sentences:
                # 현재 청크 완성
                chunk = self._build_text_chunk(
                    current_sentences, page_num, chunk_idx
                )
                chunks.append(chunk)
                chunk_idx += 1
                
                # 오버랩 문장 가져오기
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences, self.chunk_overlap
                )
                
                # 새 청크 시작 (오버랩 포함)
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
    
    def _add_embeddings(self, chunks: List[Chunk]) -> None:
        """임베딩 생성"""
        if not self.embedder:
            return
        
        texts = [c.content for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()


# 테스트
if __name__ == "__main__":
    from models.layout_detector import DocumentElement, ElementType
    
    # 샘플 데이터
    elements = [
        DocumentElement(
            type=ElementType.TEXT,
            bbox=(0, 0, 100, 100),
            confidence=0.95,
            text="이것은 첫 번째 문장입니다. 이것은 두 번째 문장입니다.",
            metadata={'page_num': 1}
        ),
        DocumentElement(
            type=ElementType.TABLE,
            bbox=(0, 0, 100, 100),
            confidence=0.95,
            text="| A | B |\n|---|---|\n| 1 | 2 |",
            metadata={'page_num': 1}
        ),
        DocumentElement(
            type=ElementType.SECTION,
            bbox=(0, 0, 100, 100),
            confidence=0.95,
            text="섹션 제목입니다. 섹션 내용이 여기에 있습니다.",
            metadata={'page_num': 2, 'title': 'Section 1'}
        )
    ]
    
    chunker = IntelligentChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.create_chunks(elements)
    
    print("\n✅ Chunking Test:")
    print(f"  총 청크: {len(chunks)}개")
    
    for chunk in chunks:
        print(f"\n{chunk.chunk_id} ({chunk.type}, page {chunk.page_num}):")
        print(f"  {chunk.content[:100]}...")
"""
PRISM Phase 2 - Intelligent Chunker

문서 구조를 이해하고 의미 기반으로 청킹합니다.

Author: 이서영 (Backend Lead)
Date: 2025-10-11
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
import numpy as np

from core.document_analyzer import DocumentStructure, PageLayout
from core.text_extractor import ExtractedText
from core.table_parser import StructuredTable
from core.image_captioner import ImageCaption
from models.layout_detector import ElementType


@dataclass
class Chunk:
    """RAG용 청크"""
    chunk_id: str
    type: str  # "text", "table", "image"
    content: str
    metadata: Dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        result = {
            "chunk_id": self.chunk_id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }
        
        if self.embedding:
            result["embedding"] = self.embedding
        
        return result


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
    1. 제목 기반 섹션 분리
    2. 표는 독립 청크로 유지
    3. 긴 텍스트는 의미 기반 분할
    4. 문맥 정보(앞뒤 섹션) 메타데이터로 첨부
    """
    
    def __init__(
        self, 
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Args:
            chunk_size: 목표 청크 크기 (토큰)
            chunk_overlap: 청크 간 중복 (토큰)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(
        self,
        structure: DocumentStructure,
        texts: List[ExtractedText],
        tables: List[StructuredTable],
        captions: List[ImageCaption]
    ) -> ChunkingResult:
        """
        문서 전체를 청킹
        
        Args:
            structure: 문서 구조
            texts: 추출된 텍스트
            tables: 파싱된 표
            captions: 이미지 캡션
            
        Returns:
            청킹 결과
        """
        chunks = []
        
        # 페이지별로 처리
        for page in structure.pages:
            page_chunks = self._chunk_page(
                page, texts, tables, captions
            )
            chunks.extend(page_chunks)
        
        # 통계 계산
        statistics = self._calculate_statistics(chunks)
        
        return ChunkingResult(chunks=chunks, statistics=statistics)
    
    def _chunk_page(
        self,
        page: PageLayout,
        texts: List[ExtractedText],
        tables: List[StructuredTable],
        captions: List[ImageCaption]
    ) -> List[Chunk]:
        """페이지 단위 청킹"""
        chunks = []
        
        # 1. 텍스트 청크
        page_texts = [t for t in texts if t.page_num == page.page_num]
        text_chunks = self._chunk_texts(page_texts, page)
        chunks.extend(text_chunks)
        
        # 2. 표 청크 (독립)
        page_tables = [t for t in tables if t.page_num == page.page_num]
        table_chunks = self._chunk_tables(page_tables, page)
        chunks.extend(table_chunks)
        
        # 3. 이미지 청크
        page_captions = [c for c in captions if c.element.page_num == page.page_num]
        image_chunks = self._chunk_images(page_captions, page)
        chunks.extend(image_chunks)
        
        return chunks
    
    def _chunk_texts(
        self, 
        texts: List[ExtractedText], 
        page: PageLayout
    ) -> List[Chunk]:
        """텍스트 청킹"""
        if not texts:
            return []
        
        # 제목 요소 찾기
        titles = [e for e in page.elements if e.type == ElementType.TITLE]
        
        chunks = []
        current_section = None
        accumulated_text = []
        
        for text in sorted(texts, key=lambda t: (t.bbox.y, t.bbox.x)):
            # 제목인지 체크
            is_title = any(
                self._bbox_overlaps(text.bbox, t.bbox) 
                for t in titles
            )
            
            if is_title:
                # 이전 섹션 청크 생성
                if accumulated_text:
                    chunks.extend(self._split_text_by_size(
                        "\n\n".join(accumulated_text),
                        current_section,
                        page.page_num
                    ))
                    accumulated_text = []
                
                # 새 섹션 시작
                current_section = text.content
            
            accumulated_text.append(text.content)
        
        # 마지막 섹션 처리
        if accumulated_text:
            chunks.extend(self._split_text_by_size(
                "\n\n".join(accumulated_text),
                current_section,
                page.page_num
            ))
        
        return chunks
    
    def _split_text_by_size(
        self, 
        text: str, 
        section: Optional[str],
        page_num: int
    ) -> List[Chunk]:
        """텍스트를 크기 기반으로 분할"""
        # 간단한 토큰 추정 (대략 1단어 = 1.3토큰)
        words = text.split()
        estimated_tokens = len(words) * 1.3
        
        if estimated_tokens <= self.chunk_size:
            # 한 청크에 들어감
            return [Chunk(
                chunk_id=f"page{page_num}_text_1",
                type="text",
                content=text,
                metadata={
                    "page": page_num,
                    "section": section,
                    "tokens": int(estimated_tokens)
                }
            )]
        
        # 여러 청크로 분할
        chunks = []
        sentences = text.split('. ')
        
        current_chunk = []
        current_tokens = 0
        chunk_idx = 1
        
        for sentence in sentences:
            sentence_tokens = len(sentence.split()) * 1.3
            
            if current_tokens + sentence_tokens > self.chunk_size:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(Chunk(
                        chunk_id=f"page{page_num}_text_{chunk_idx}",
                        type="text",
                        content='. '.join(current_chunk) + '.',
                        metadata={
                            "page": page_num,
                            "section": section,
                            "chunk_index": chunk_idx,
                            "tokens": int(current_tokens)
                        }
                    ))
                    chunk_idx += 1
                
                # 오버랩 처리 (마지막 문장 일부 포함)
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_sentences = current_chunk[-1:]
                    current_chunk = overlap_sentences + [sentence]
                    current_tokens = sum(len(s.split()) * 1.3 for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # 마지막 청크
        if current_chunk:
            chunks.append(Chunk(
                chunk_id=f"page{page_num}_text_{chunk_idx}",
                type="text",
                content='. '.join(current_chunk) + '.',
                metadata={
                    "page": page_num,
                    "section": section,
                    "chunk_index": chunk_idx,
                    "tokens": int(current_tokens)
                }
            ))
        
        return chunks
    
    def _chunk_tables(
        self, 
        tables: List[StructuredTable], 
        page: PageLayout
    ) -> List[Chunk]:
        """표 청킹 (각 표는 독립 청크)"""
        chunks = []
        
        for idx, table in enumerate(tables):
            chunk = Chunk(
                chunk_id=f"page{page.page_num}_table_{idx+1}",
                type="table",
                content=table.to_markdown(),
                metadata={
                    "page": page.page_num,
                    "caption": table.caption,
                    "headers": table.headers,
                    "row_count": len(table.rows),
                    "col_count": len(table.headers) if table.headers else 0,
                    "bbox": table.bbox.to_dict(),
                    "structured_data": table.to_json()
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_images(
        self, 
        captions: List[ImageCaption], 
        page: PageLayout
    ) -> List[Chunk]:
        """이미지 청킹"""
        chunks = []
        
        for idx, caption in enumerate(captions):
            chunk = Chunk(
                chunk_id=f"page{page.page_num}_image_{idx+1}",
                type="image",
                content=caption.caption,
                metadata={
                    "page": page.page_num,
                    "element_type": caption.element.type.value,
                    "confidence": caption.confidence,
                    "provider": caption.provider,
                    "bbox": caption.element.bbox.to_dict()
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _bbox_overlaps(self, bbox1, bbox2) -> bool:
        """두 BBox가 겹치는지 확인"""
        x1_overlap = bbox1.x < bbox2.x + bbox2.width and bbox1.x + bbox1.width > bbox2.x
        y1_overlap = bbox1.y < bbox2.y + bbox2.height and bbox1.y + bbox1.height > bbox2.y
        return x1_overlap and y1_overlap
    
    def _calculate_statistics(self, chunks: List[Chunk]) -> Dict:
        """청킹 통계 계산"""
        by_type = {}
        for chunk in chunks:
            by_type[chunk.type] = by_type.get(chunk.type, 0) + 1
        
        total_tokens = sum(
            chunk.metadata.get("tokens", 0) 
            for chunk in chunks if chunk.type == "text"
        )
        
        return {
            "total_chunks": len(chunks),
            "by_type": by_type,
            "total_tokens": total_tokens,
            "avg_chunk_size": total_tokens / max(by_type.get("text", 1), 1)
        }


# 테스트 코드
if __name__ == "__main__":
    from core.document_analyzer import DocumentAnalyzer
    from core.text_extractor import TextExtractor
    from core.table_parser import TableParser
    from core.image_captioner import ImageCaptioner
    from models.layout_detector import ElementType
    import json
    
    pdf_path = "data/uploads/test_document.pdf"
    
    # 1. 문서 분석
    print("=== Step 1: Document Analysis ===")
    analyzer = DocumentAnalyzer()
    structure = analyzer.analyze(pdf_path, max_pages=3)
    
    # 2. 텍스트 추출
    print("\n=== Step 2: Text Extraction ===")
    text_elements = structure.get_all_elements_by_type(ElementType.TEXT)
    extractor = TextExtractor()
    texts = extractor.extract_all_text(pdf_path, text_elements)
    print(f"Extracted {len(texts)} text blocks")
    
    # 3. 표 파싱
    print("\n=== Step 3: Table Parsing ===")
    table_elements = structure.get_all_elements_by_type(ElementType.TABLE)
    parser = TableParser()
    tables = parser.parse_all_tables(pdf_path, table_elements)
    print(f"Parsed {len(tables)} tables")
    
    # 4. 이미지 캡션
    print("\n=== Step 4: Image Captioning ===")
    image_elements = structure.get_all_elements_by_type(ElementType.IMAGE)
    chart_elements = structure.get_all_elements_by_type(ElementType.CHART)
    captioner = ImageCaptioner(provider="claude")
    captions = captioner.generate_captions_batch(
        pdf_path, 
        image_elements + chart_elements, 
        analyzer
    )
    print(f"Generated {len(captions)} captions")
    
    # 5. 지능형 청킹
    print("\n=== Step 5: Intelligent Chunking ===")
    chunker = IntelligentChunker(
        chunk_size=512,
        chunk_overlap=50
    )
    result = chunker.chunk(structure, texts, tables, captions)
    
    # 6. 결과 출력
    print("\n=== Chunking Results ===")
    print(f"Total chunks: {result.statistics['total_chunks']}")
    print(f"By type: {result.statistics['by_type']}")
    print(f"Total tokens: {result.statistics['total_tokens']}")
    print(f"Avg chunk size: {result.statistics['avg_chunk_size']:.1f} tokens")
    
    # 7. 결과 저장
    with open("data/processed/chunks.json", "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    print("\n✅ Chunking complete! Results saved to data/processed/chunks.json")
    
    # 8. 샘플 출력
    print("\n=== Sample Chunks ===")
    for i, chunk in enumerate(result.chunks[:5]):
        print(f"\n[Chunk {i+1}] {chunk.type} ({chunk.chunk_id})")
        print(f"Metadata: {chunk.metadata}")
        content_preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
        print(f"Content: {content_preview}")
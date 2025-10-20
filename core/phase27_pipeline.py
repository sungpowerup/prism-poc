"""
PRISM Phase 2.7 - Main Processing Pipeline
2-Stage Pipeline + Intelligent Chunking

Stage 1: Layout Detection
Stage 2: Hybrid Extraction
Stage 3: Intelligent Chunking

Author: 이서영 (Backend Lead)
Date: 2025-10-20
"""

import time
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import fitz  # PyMuPDF

from core.layout_detector import LayoutDetector, Region
from core.hybrid_extractor import HybridExtractor, ExtractedContent
from core.intelligent_chunker import IntelligentChunker, Chunk


class Phase27Pipeline:
    """
    PRISM Phase 2.7 메인 파이프라인
    
    특징:
    - 2-Stage 처리 (Layout → Extraction)
    - 하이브리드 추출 (OCR + VLM)
    - 의미 기반 청킹
    - RAG 최적화
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap_size: int = 50
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기 (토큰)
            max_chunk_size: 최대 청크 크기 (토큰)
            overlap_size: 청크 간 오버랩 (토큰)
        """
        print("\n" + "="*60)
        print("PRISM Phase 2.7 Pipeline Initialization")
        print("="*60 + "\n")
        
        # Stage 1: Layout Detection
        self.layout_detector = LayoutDetector()
        
        # Stage 2: Hybrid Extraction
        self.extractor = HybridExtractor()
        
        # Stage 3: Intelligent Chunking
        self.chunker = IntelligentChunker(
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            overlap_size=overlap_size
        )
        
        print("\n✅ Pipeline ready!\n")
    
    def process_pdf(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 문서 전체 처리
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        
        print(f"📄 Processing PDF: {pdf_path}")
        print(f"⏱️  Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # PDF 열기
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"📖 Total pages: {total_pages}\n")
        
        # 페이지별 처리
        all_chunks = []
        
        for page_num in range(total_pages):
            print(f"{'='*60}")
            print(f"📄 Processing Page {page_num + 1}/{total_pages}")
            print(f"{'='*60}\n")
            
            page_chunks = self._process_page(doc, page_num)
            all_chunks.extend(page_chunks)
            
            print(f"\n✅ Page {page_num + 1} completed: {len(page_chunks)} chunks generated\n")
        
        doc.close()
        
        # 결과 통계
        elapsed_time = time.time() - start_time
        
        result = {
            'metadata': {
                'processed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'total_pages': total_pages,
                'total_chunks': len(all_chunks),
                'processing_time_seconds': round(elapsed_time, 2),
                'chunk_types': self._count_chunk_types(all_chunks)
            },
            'chunks': [chunk.to_dict() for chunk in all_chunks]
        }
        
        print(f"\n{'='*60}")
        print(f"🎉 Processing Complete!")
        print(f"{'='*60}")
        print(f"⏱️  Total time: {elapsed_time:.1f}s")
        print(f"📊 Total chunks: {len(all_chunks)}")
        print(f"📈 Chunk types: {result['metadata']['chunk_types']}")
        print()
        
        return result
    
    def _process_page(self, doc: fitz.Document, page_num: int) -> List[Chunk]:
        """
        단일 페이지 처리
        
        Args:
            doc: PDF 문서 객체
            page_num: 페이지 번호 (0-based)
            
        Returns:
            Chunk 리스트
        """
        page = doc[page_num]
        
        # 1. 페이지를 이미지로 변환
        print("🖼️  Step 1: Converting page to image...")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
        img_data = pix.tobytes("png")
        
        from io import BytesIO
        page_image = Image.open(BytesIO(img_data))
        print(f"   Image size: {page_image.size[0]}x{page_image.size[1]}\n")
        
        # 2. Stage 1: Layout Detection
        print("🔍 Step 2: Detecting layout regions...")
        regions = self.layout_detector.detect(page_image)
        
        if not regions:
            print("   ⚠️  No regions detected, treating whole page as text\n")
            # 전체 페이지를 하나의 텍스트 영역으로
            regions = [Region(
                type='text',
                bbox=(0, 0, page_image.size[0], page_image.size[1]),
                confidence=0.5,
                description='Full page'
            )]
        
        print(f"   Found {len(regions)} regions\n")
        
        # 3. Stage 2: Hybrid Extraction
        print("📝 Step 3: Extracting content from regions...")
        extracted_contents = []
        
        for i, region in enumerate(regions, 1):
            print(f"   Region {i}/{len(regions)}: {region.type} - {region.description}")
            
            # 영역 이미지 crop
            region_image = self.layout_detector.crop_region(page_image, region)
            
            # 하이브리드 추출
            content = self.extractor.extract(
                region_image=region_image,
                region_type=region.type,
                description=region.description
            )
            
            extracted_contents.append(content)
            print(f"      ✓ Extracted {len(content.content)} characters (confidence: {content.confidence:.2f})")
        
        print()
        
        # 4. Stage 3: Intelligent Chunking
        print("✂️  Step 4: Creating intelligent chunks...")
        all_chunks = []
        
        for i, content in enumerate(extracted_contents, 1):
            region_desc = regions[i-1].description if i <= len(regions) else "Region"
            
            chunks = self.chunker.chunk_content(
                content=content.content,
                content_type=content.type,
                page_num=page_num + 1,  # 1-based page number
                base_section=region_desc,
                metadata=content.metadata
            )
            
            all_chunks.extend(chunks)
            print(f"   Region {i}: {len(chunks)} chunk(s) created")
        
        return all_chunks
    
    def _count_chunk_types(self, chunks: List[Chunk]) -> Dict[str, int]:
        """청크 타입별 개수 세기"""
        counts = {}
        for chunk in chunks:
            counts[chunk.type] = counts.get(chunk.type, 0) + 1
        return counts


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Pipeline Test")
    print("="*60 + "\n")
    
    pipeline = Phase27Pipeline()
    
    # 테스트 PDF 경로 확인
    test_pdf = Path("input/test_document.pdf")
    
    if test_pdf.exists():
        print(f"✅ Test PDF found: {test_pdf}\n")
        
        # 처리 실행
        result = pipeline.process_pdf(str(test_pdf), max_pages=3)
        
        print("\n📊 Result Summary:")
        print(f"   Chunks: {result['metadata']['total_chunks']}")
        print(f"   Types: {result['metadata']['chunk_types']}")
        print(f"   Time: {result['metadata']['processing_time_seconds']}s")
    else:
        print(f"⚠️  Test PDF not found: {test_pdf}")
        print(f"   Please place a PDF file at: {test_pdf.absolute()}")
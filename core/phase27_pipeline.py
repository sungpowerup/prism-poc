"""
PRISM Phase 2.7 - Main Processing Pipeline
2-Stage Pipeline + Intelligent Chunking

Stage 1: Layout Detection
Stage 2: Hybrid Extraction
Stage 3: Intelligent Chunking

Author: 이서영 (Backend Lead)
Date: 2025-10-20
Fixed: bbox tuple access issue + Anthropic initialization
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
        vlm_provider: str = 'claude',
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap_size: int = 50
    ):
        """
        Args:
            vlm_provider: VLM 프로바이더 ('claude', 'azure_openai', 'ollama')
            min_chunk_size: 최소 청크 크기 (토큰)
            max_chunk_size: 최대 청크 크기 (토큰)
            overlap_size: 청크 간 오버랩 (토큰)
        """
        print("\n" + "="*60)
        print("PRISM Phase 2.7 Pipeline Initialization")
        print("="*60 + "\n")
        
        self.vlm_provider = vlm_provider
        print(f"🤖 VLM Provider: {vlm_provider.upper()}")
        
        # Stage 1: Layout Detection
        self.layout_detector = LayoutDetector(vlm_provider=vlm_provider)
        
        # Stage 2: Hybrid Extraction
        self.extractor = HybridExtractor(vlm_provider=vlm_provider)
        
        # Stage 3: Intelligent Chunking
        self.chunker = IntelligentChunker(
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            overlap_size=overlap_size
        )
        
        print("\n✅ Pipeline ready!\n")
    
    def process(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 문서 전체 처리 (메인 엔트리포인트)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과 딕셔너리
        """
        return self.process_pdf(pdf_path, max_pages)
    
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
        print(f"⏱️  Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # PDF 열기
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"📖 Total pages: {total_pages}\n")
        
        # 각 페이지 처리
        all_chunks = []
        
        for page_num in range(total_pages):
            print("="*60)
            print(f"📄 Processing Page {page_num + 1}/{total_pages}")
            print("="*60 + "\n")
            
            # 페이지별 청크 생성
            page_chunks = self._process_page(doc, page_num)
            all_chunks.extend(page_chunks)
            
            print(f"\n✅ Page {page_num + 1} completed: {len(page_chunks)} chunks generated\n")
        
        # 문서 닫기
        doc.close()
        
        # 처리 완료
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 메타데이터
        metadata = {
            'processed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'total_pages': total_pages,
            'total_chunks': len(all_chunks),
            'processing_time_seconds': round(processing_time, 2),
            'chunk_types': self._count_chunk_types(all_chunks),
            'vlm_provider': self.vlm_provider
        }
        
        # 결과 딕셔너리
        result = {
            'metadata': metadata,
            'chunks': [chunk.to_dict() for chunk in all_chunks]
        }
        
        print("="*60)
        print("🎉 Processing Complete!")
        print("="*60)
        print(f"⏱️  Total time: {processing_time:.1f}s")
        print(f"📊 Total chunks: {len(all_chunks)}")
        print(f"📈 Chunk types: {metadata['chunk_types']}\n")
        
        return result
    
    def _process_page(self, doc: fitz.Document, page_num: int) -> List[Chunk]:
        """
        단일 페이지 처리
        
        Args:
            doc: PyMuPDF 문서 객체
            page_num: 페이지 번호 (0-based)
            
        Returns:
            청크 리스트
        """
        page = doc[page_num]
        
        # Stage 1: Page → Image
        print("🖼️  Step 1: Converting page to image...")
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        print(f"   Image size: {img.width}x{img.height}")
        
        # Stage 2: Layout Detection
        print("🔍 Step 2: Detecting layout regions...")
        regions = self.layout_detector.detect_regions(img)
        print(f"   Found {len(regions)} regions")
        
        # Stage 3: Hybrid Extraction
        print("📝 Step 3: Extracting content from regions...")
        extracted_contents = []
        
        for i, region in enumerate(regions, 1):
            print(f"   Region {i}/{len(regions)}: {region.type} - {region.description}")
            
            # ✅ 수정: bbox는 튜플 (x, y, width, height)
            # 튜플 언팩으로 각 값 추출
            x, y, width, height = region.bbox
            
            # 영역 이미지 추출
            region_img = img.crop((
                x,
                y,
                x + width,
                y + height
            ))
            
            # 컨텐츠 추출
            content = self.extractor.extract_content(
                image=region_img,
                region_type=region.type,
                page_text=page.get_text()
            )
            
            extracted_contents.append(content)
            
            # 추출 결과 출력
            char_count = len(content.content)
            confidence = content.confidence
            print(f"      ✓ Extracted {char_count} characters (confidence: {confidence:.2f})")
        
        # Stage 4: Intelligent Chunking
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
    
    # VLM Provider 선택
    import sys
    vlm_provider = sys.argv[1] if len(sys.argv) > 1 else 'claude'
    
    pipeline = Phase27Pipeline(vlm_provider=vlm_provider)
    
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
        print(f"   Provider: {result['metadata']['vlm_provider']}")
    else:
        print(f"⚠️  Test PDF not found: {test_pdf}")
        print(f"   Please place a PDF file at: {test_pdf.absolute()}")
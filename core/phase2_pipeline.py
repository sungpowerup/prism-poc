"""
PRISM Phase 2.1 - Enhanced Pipeline

개선 사항:
- Fallback Table Extractor 통합
- 개선된 Intelligent Chunker 통합
- 표 추출 품질 향상

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import fitz  # PyMuPDF

from models.layout_detector import LayoutDetector, DocumentElement, ElementType
from core.text_extractor import PaddleOCRExtractor
from core.table_extractor_fallback import FallbackTableExtractor, ExtractedTable
from core.image_captioner import ImageCaptioner
from core.intelligent_chunker import IntelligentChunker
from core.document_analyzer import DocumentAnalyzer


class Phase2Pipeline:
    """
    PRISM Phase 2.1 파이프라인 (개선)
    
    처리 단계:
    1. Layout Detection (Detectron2 또는 Mock)
    2. Text Extraction (PaddleOCR)
    3. ⭐ Table Parsing (Detectron2 + Fallback)
    4. Image Captioning (VLM - 선택)
    5. ⭐ Intelligent Chunking (개선)
    """
    
    def __init__(
        self,
        use_vlm: bool = False,
        vlm_provider: str = "claude",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Args:
            use_vlm: VLM 사용 여부
            vlm_provider: VLM 제공자 (claude/azure/ollama)
            chunk_size: 청크 크기
            chunk_overlap: 청크 오버랩
        """
        print("Initializing PRISM Phase 2.1 Pipeline...")
        
        # 1. Layout Detector
        self.layout_detector = LayoutDetector()
        
        # 2. Text Extractor
        self.text_extractor = PaddleOCRExtractor()
        
        # 3. ⭐ Fallback Table Extractor (신규)
        self.fallback_table_extractor = FallbackTableExtractor(
            min_cols=3,
            min_rows=2,
            alignment_threshold=10.0
        )
        print("✅ Fallback Table Extractor loaded")
        
        # 4. Image Captioner (선택)
        self.use_vlm = use_vlm
        if use_vlm:
            self.image_captioner = ImageCaptioner(
                provider=vlm_provider,
                require_key=False
            )
        else:
            self.image_captioner = None
        
        # 5. ⭐ Intelligent Chunker (개선)
        self.chunker = IntelligentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # 6. Document Analyzer
        self.analyzer = DocumentAnalyzer()
        
        print("✅ Pipeline initialized successfully\n")
    
    def process(
        self,
        pdf_path: str,
        output_dir: str = "data/processed",
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 처리
        
        Args:
            pdf_path: PDF 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 페이지 수
            
        Returns:
            처리 결과
        """
        start_time = time.time()
        
        print("=" * 60)
        print("PRISM Phase 2.1 - Document Processing")
        print("=" * 60)
        print(f"Input: {pdf_path}")
        print(f"Max pages: {max_pages or 'All'}")
        print("=" * 60)
        print()
        
        # 출력 디렉토리 생성
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # PDF 로드
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        # Step 1: Layout Detection
        print(f"📄 Step 1/5: Analyzing document structure...")
        elements = []
        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            print(f"Analyzing page {page_num + 1}/{total_pages}...")
            page_elements = self.layout_detector.detect(img, page_num + 1)
            elements.extend(page_elements)
        
        print(f"✓ Found {len(elements)} elements")
        print()
        
        # Step 2: Text Extraction
        print(f"📝 Step 2/5: Extracting text...")
        texts = []
        ocr_results = []  # ⭐ OCR 결과 저장 (표 추출용)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # OCR 추출
            extracted, ocr_result = self.text_extractor.extract(img, page_num + 1)
            texts.extend(extracted)
            ocr_results.append((page_num + 1, ocr_result))
        
        print(f"✓ Extracted {len(texts)} text blocks")
        print()
        
        # Step 3: ⭐ Table Parsing (개선)
        print(f"📊 Step 3/5: Parsing tables...")
        tables = self._parse_tables_enhanced(elements, ocr_results)
        print(f"✓ Parsed {len(tables)} tables")
        print()
        
        # Step 4: Image Captioning
        print(f"🖼️  Step 4/5: Generating image captions...")
        captions = []
        if self.use_vlm and self.image_captioner:
            captions = self._generate_captions(elements, doc)
        else:
            print("⚠️  VLM disabled, skipping captions")
        print(f"✓ Generated {len(captions)} captions")
        print()
        
        # Step 5: ⭐ Intelligent Chunking (개선)
        print(f"🧩 Step 5/5: Intelligent chunking...")
        structure = self.analyzer.analyze_structure(elements)
        result = self.chunker.chunk(structure, texts, tables, captions)
        print(f"✓ Created {len(result.chunks)} chunks")
        print()
        
        # 결과 저장
        self._save_results(pdf_path, result, output_dir)
        
        elapsed = time.time() - start_time
        print("=" * 60)
        print("✅ Processing complete!")
        print(f"Time: {elapsed:.1f}s")
        print(f"Output: {output_dir}")
        print("=" * 60)
        print()
        
        return {
            "elements": len(elements),
            "texts": len(texts),
            "tables": len(tables),
            "captions": len(captions),
            "chunks": len(result.chunks),
            "statistics": result.statistics,
            "elapsed_time": elapsed
        }
    
    def _parse_tables_enhanced(
        self,
        elements: List[DocumentElement],
        ocr_results: List[tuple]
    ) -> List[ExtractedTable]:
        """
        표 파싱 (개선)
        
        전략:
        1. Detectron2가 TABLE을 탐지하면 우선 사용
        2. 탐지 실패 시 Fallback Extractor 사용
        """
        tables = []
        
        # 1. Detectron2 탐지 표
        detectron_tables = [e for e in elements if e.type == ElementType.TABLE]
        
        if detectron_tables:
            print(f"  ✅ Detectron2 found {len(detectron_tables)} tables")
            for table_element in detectron_tables:
                # TODO: Detectron2 표를 구조화
                # 현재는 placeholder
                pass
        
        # 2. ⭐ Fallback Extractor (OCR 기반)
        for page_num, ocr_result in ocr_results:
            # OCR 결과를 dict 리스트로 변환
            ocr_dicts = []
            for item in ocr_result:
                if isinstance(item, dict):
                    ocr_dicts.append(item)
                elif isinstance(item, tuple) and len(item) >= 2:
                    # (bbox, (text, confidence)) 형식
                    bbox, text_data = item[0], item[1]
                    text = text_data[0] if isinstance(text_data, tuple) else str(text_data)
                    ocr_dicts.append({
                        "text": text,
                        "bbox": bbox
                    })
            
            # Fallback Extractor로 표 추출
            page_tables = self.fallback_table_extractor.extract_tables(
                ocr_dicts, page_num
            )
            
            if page_tables:
                print(f"  ✅ Fallback found {len(page_tables)} tables on page {page_num}")
            
            tables.extend(page_tables)
        
        return tables
    
    def _generate_captions(
        self,
        elements: List[DocumentElement],
        doc
    ) -> List:
        """이미지 캡션 생성"""
        captions = []
        
        for element in elements:
            if not self.image_captioner.should_caption(element):
                continue
            
            # 페이지 이미지 로드
            page = doc[element.page_number - 1]
            pix = page.get_pixmap(dpi=150)
            page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 캡션 생성
            caption = self.image_captioner.generate_caption(
                page_img, element
            )
            if caption:
                captions.append(caption)
        
        return captions
    
    def _save_results(
        self,
        pdf_path: str,
        result,
        output_dir: str
    ) -> None:
        """결과 저장"""
        import json
        
        pdf_name = Path(pdf_path).stem
        output_path = Path(output_dir) / f"{pdf_name}_chunks.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"📝 Saved: {output_path}")


# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python phase2_pipeline.py <pdf_path> [max_pages]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    pipeline = Phase2Pipeline(
        use_vlm=False,  # VLM 비활성화 (테스트용)
        chunk_size=512,
        chunk_overlap=50
    )
    
    result = pipeline.process(pdf_path, max_pages=max_pages)
    
    print("\n📊 Summary:")
    print(f"  Elements: {result['elements']}")
    print(f"  Texts: {result['texts']}")
    print(f"  Tables: {result['tables']}")
    print(f"  Chunks: {result['chunks']}")
    print(f"\n  Statistics:")
    for k, v in result['statistics'].items():
        print(f"    {k}: {v}")
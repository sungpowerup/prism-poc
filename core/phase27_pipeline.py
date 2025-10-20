"""
PRISM Phase 2.7 Pipeline - 간단한 OCR 기반 버전

Author: 이서영 (Backend Lead)
Date: 2025-10-20
Fix: OCR 기반 간단한 구현 (LayoutDetector, HybridExtractor, IntelligentChunker 단순화)
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from PIL import Image

# 간단한 모듈들 import
from core.layout_detector import LayoutDetector, Region
from core.hybrid_extractor import HybridExtractor, ExtractedContent
from core.intelligent_chunker import IntelligentChunker, Chunk


class Phase27Pipeline:
    """
    PRISM Phase 2.7 파이프라인 (간단 버전)
    
    Features:
    - PyMuPDF 기반 PDF → 이미지 변환
    - 전체 페이지를 TEXT 영역으로 처리
    - OCR (Tesseract/PaddleOCR) 텍스트 추출
    - 길이 기반 청킹
    """
    
    def __init__(self, vlm_provider: str = "claude"):
        """
        Args:
            vlm_provider: VLM 제공자 (현재 미사용, OCR만 사용)
        """
        self.vlm_provider = vlm_provider
        
        # 서브 모듈 초기화
        print("\n" + "="*60)
        print("PRISM Phase 2.7 Pipeline Initialization")
        print("="*60)
        
        self.layout_detector = LayoutDetector(vlm_provider=vlm_provider)
        self.extractor = HybridExtractor(vlm_provider=vlm_provider, ocr_engine='tesseract')
        self.chunker = IntelligentChunker(
            min_chunk_size=100,
            max_chunk_size=500,
            overlap=50
        )
        
        print("="*60 + "\n")
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        PDF 문서 처리
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리 (선택)
            
        Returns:
            처리 결과 딕셔너리
        """
        
        start_time = time.time()
        
        print("\n" + "="*60)
        print(f"🔷 PRISM Phase 2.7 - PDF Processing")
        print("="*60)
        print(f"📄 Input: {pdf_path}")
        print(f"🤖 VLM Provider: {self.vlm_provider} (OCR mode)")
        print("="*60 + "\n")
        
        # Step 1: PDF → 이미지 변환
        print("🖼️  Step 1: Converting PDF to images...")
        page_images = self._pdf_to_images(pdf_path)
        total_pages = len(page_images)
        print(f"   ✓ Converted {total_pages} page(s)\n")
        
        # Step 2: 페이지별 처리
        all_chunks = []
        all_stats = []
        
        for page_num, page_image in enumerate(page_images, start=1):
            print(f"\n{'─'*60}")
            print(f"📄 Processing Page {page_num}/{total_pages}")
            print(f"{'─'*60}")
            
            # 페이지 처리
            page_chunks, stats = self._process_page(page_image, page_num)
            
            all_chunks.extend(page_chunks)
            all_stats.append(stats)
            
            print(f"✓ Page {page_num} completed: {len(page_chunks)} chunk(s)")
        
        # Step 3: 결과 생성
        elapsed_time = time.time() - start_time
        
        result = {
            'metadata': {
                'filename': Path(pdf_path).name,
                'total_pages': total_pages,
                'total_chunks': len(all_chunks),
                'processing_time_sec': elapsed_time,
                'vlm_provider': self.vlm_provider,
                'processed_at': datetime.now().isoformat(),
                'chunk_types': self._count_chunk_types(all_chunks)
            },
            'stage1_elements': self._extract_stage1_from_stats(all_stats),
            'stage2_chunks': [self._chunk_to_dict(chunk) for chunk in all_chunks]
        }
        
        # Step 4: 파일 저장 (선택)
        if output_dir:
            self._save_results(result, output_dir)
        
        # 완료 메시지
        print("\n" + "="*60)
        print("✅ Processing Complete!")
        print("="*60)
        print(f"⏱️  Total time: {elapsed_time:.1f}s")
        print(f"📊 Total chunks: {len(all_chunks)}")
        print(f"📈 Chunk types: {result['metadata']['chunk_types']}")
        
        return result
    
    def _process_page(
        self,
        page_image: Image.Image,
        page_num: int
    ) -> Tuple[List[Chunk], Dict]:
        """
        페이지 처리
        
        Args:
            page_image: PIL Image
            page_num: 페이지 번호
            
        Returns:
            (청크 리스트, 통계)
        """
        
        # Step 1: 이미지 확인
        print("🖼️  Step 1: Converting page to image...")
        print(f"   Image size: {page_image.width}x{page_image.height}")
        
        # Step 2: 레이아웃 감지 (전체 페이지 = 1개 region)
        print("🔍 Step 2: Detecting layout regions...")
        regions = self.layout_detector.detect_regions(page_image)
        print(f"   Found {len(regions)} region(s)")
        
        # Step 3: 영역별 컨텐츠 추출
        print("📝 Step 3: Extracting content from regions...")
        page_chunks = []
        
        for i, region in enumerate(regions, start=1):
            # Bbox 검증
            valid_bbox = self._validate_and_fix_bbox(
                region.bbox, 
                page_image.width, 
                page_image.height
            )
            
            if valid_bbox is None:
                print(f"   ⚠️  Region {i}: Invalid bbox, skipping...")
                continue
            
            # 영역 이미지 잘라내기
            try:
                region_image = page_image.crop(valid_bbox)
            except Exception as e:
                print(f"   ❌ Region {i}: Crop failed - {e}")
                continue
            
            # 컨텐츠 추출 (OCR)
            print(f"   Region {i}/{len(regions)}: {region.type} - {region.description}")
            
            try:
                extracted = self.extractor.extract(
                    image=region_image,
                    region_type=region.type,
                    description=region.description
                )
                
                content_len = len(extracted.content)
                print(f"      ✓ Extracted {content_len} characters (confidence: {extracted.confidence:.2f})")
                
                # 내용이 있으면 청킹
                if content_len > 0:
                    print(f"      🔄 Chunking {content_len} characters...")
                    
                    region_chunks = self.chunker.chunk_region(
                        content=extracted.content,
                        region_type=extracted.type,
                        page_num=page_num,
                        section_path=region.description,
                        source=extracted.metadata.get('source', 'unknown')
                    )
                    
                    page_chunks.extend(region_chunks)
                    print(f"      ✓ Created {len(region_chunks)} chunk(s)")
                else:
                    print(f"      ⚠️  No content extracted")
                
            except Exception as e:
                print(f"      ❌ Extraction failed: {e}")
                continue
        
        # Step 4: 청킹 완료
        print("✂️  Step 4: Creating intelligent chunks...")
        print(f"   Total: {len(page_chunks)} chunk(s) created")
        
        # 통계
        stats = {
            'page_num': page_num,
            'regions': len(regions),
            'chunks': len(page_chunks),
            'region_types': self._count_region_types(regions)
        }
        
        return page_chunks, stats
    
    def _validate_and_fix_bbox(
        self,
        bbox: Tuple[int, int, int, int],
        img_width: int,
        img_height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """Bbox 좌표 검증 및 수정"""
        
        left, top, right, bottom = bbox
        
        # 1. 좌표 순서 확인
        if left > right:
            left, right = right, left
        if top > bottom:
            top, bottom = bottom, top
        
        # 2. 좌표가 동일하면 무효
        if left == right or top == bottom:
            return None
        
        # 3. 이미지 범위 내로 제한
        left = max(0, min(left, img_width - 1))
        top = max(0, min(top, img_height - 1))
        right = max(left + 1, min(right, img_width))
        bottom = max(top + 1, min(bottom, img_height))
        
        # 4. 최소 크기 확인
        if (right - left) < 1 or (bottom - top) < 1:
            return None
        
        return (left, top, right, bottom)
    
    def _pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """PDF → 이미지 변환 (PyMuPDF)"""
        
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 고해상도 렌더링 (300 DPI)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Image로 변환
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        
        doc.close()
        
        return images
    
    def _count_region_types(self, regions: List[Region]) -> Dict[str, int]:
        """Region 타입 집계"""
        counts = {}
        for region in regions:
            counts[region.type] = counts.get(region.type, 0) + 1
        return counts
    
    def _count_chunk_types(self, chunks: List[Chunk]) -> Dict[str, int]:
        """Chunk 타입 집계"""
        counts = {}
        for chunk in chunks:
            counts[chunk.type] = counts.get(chunk.type, 0) + 1
        return counts
    
    def _extract_stage1_from_stats(self, all_stats: List[Dict]) -> List[Dict]:
        """통계에서 Stage 1 정보 추출"""
        elements = []
        for stats in all_stats:
            for region_type, count in stats.get('region_types', {}).items():
                elements.append({
                    'page_number': stats['page_num'],
                    'type': region_type,
                    'count': count
                })
        return elements
    
    def _chunk_to_dict(self, chunk: Chunk) -> Dict:
        """Chunk 객체를 딕셔너리로 변환"""
        return {
            'chunk_id': f"chunk_{chunk.page_num}_{id(chunk)}",
            'page_number': chunk.page_num,
            'element_type': chunk.type,
            'content': chunk.content,
            'metadata': chunk.metadata,
            'model_used': self.vlm_provider,
            'processing_time_sec': 0  # 현재 미측정
        }
    
    def _save_results(self, result: Dict, output_dir: str):
        """결과를 파일로 저장"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 저장
        json_path = output_path / f"result_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Results saved to: {json_path}")


# CLI 실행
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python phase27_pipeline.py <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    
    pipeline = Phase27Pipeline()
    result = pipeline.process_pdf(pdf_path, output_dir)
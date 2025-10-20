"""
PRISM Phase 2.7 - Complete Pipeline
레이아웃 감지 → 하이브리드 추출 → 지능형 청킹

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-20
Fix: IntelligentChunker 파라미터 수정 (overlap_size → overlap)
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from PIL import Image
import json

from core.layout_detector import LayoutDetector, Region
from core.hybrid_extractor import HybridExtractor
from core.intelligent_chunker import IntelligentChunker, Chunk


class Phase27Pipeline:
    """
    Phase 2.7 완전 자동 파이프라인
    
    단계:
    1. PDF → 이미지 변환
    2. 레이아웃 감지 (LayoutDetector)
    3. 영역별 컨텐츠 추출 (HybridExtractor)
    4. 지능형 청킹 (IntelligentChunker)
    """
    
    def __init__(
        self,
        vlm_provider: str = 'claude',
        chunk_min_size: int = 100,
        chunk_max_size: int = 500,
        chunk_overlap: int = 50  # ✅ 수정: overlap_size → chunk_overlap
    ):
        """
        초기화
        
        Args:
            vlm_provider: VLM 프로바이더
            chunk_min_size: 최소 청크 크기
            chunk_max_size: 최대 청크 크기
            chunk_overlap: 청크 간 중복  # ✅ 수정
        """
        
        print("\n" + "="*60)
        print("PRISM Phase 2.7 Pipeline Initialization")
        print("="*60)
        print()
        print(f"🤖 VLM Provider: {vlm_provider.upper()}")
        
        # 컴포넌트 초기화
        self.layout_detector = LayoutDetector(vlm_provider=vlm_provider)
        self.extractor = HybridExtractor(vlm_provider=vlm_provider)
        
        # ✅ 수정: 파라미터 이름 변경
        self.chunker = IntelligentChunker(
            min_chunk_size=chunk_min_size,
            max_chunk_size=chunk_max_size,
            overlap=chunk_overlap  # ✅ 수정: overlap_size → overlap
        )
        
        print()
        print("✅ Pipeline ready!")
        print()
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        PDF 처리 (전체 파이프라인)
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 결과 저장 경로 (None이면 자동 생성)
            
        Returns:
            처리 결과 딕셔너리
        """
        
        start_time = time.time()
        
        # PDF → 이미지 변환
        print(f"📄 Processing PDF: {pdf_path}")
        print(f"⏱️  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        page_images = self._pdf_to_images(pdf_path)
        print(f"📖 Total pages: {len(page_images)}")
        print()
        
        # 페이지별 처리
        all_chunks = []
        page_stats = []
        
        for page_num, page_image in enumerate(page_images, start=1):
            print("="*60)
            print(f"📄 Processing Page {page_num}/{len(page_images)}")
            print("="*60)
            print()
            
            page_chunks, stats = self._process_page(page_image, page_num)
            
            all_chunks.extend(page_chunks)
            page_stats.append(stats)
            
            print(f"\n✅ Page {page_num} completed: {len(page_chunks)} chunks generated")
            print()
        
        # 결과 정리
        elapsed_time = time.time() - start_time
        
        result = {
            'metadata': {
                'processed_at': datetime.now().isoformat(),
                'total_pages': len(page_images),
                'total_chunks': len(all_chunks),
                'processing_time_seconds': round(elapsed_time, 2),
                'chunk_types': self._count_chunk_types(all_chunks),
                'vlm_provider': os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
            },
            'chunks': [chunk.to_dict() for chunk in all_chunks],
            'page_stats': page_stats
        }
        
        # 결과 저장
        if output_dir:
            self._save_results(result, output_dir, pdf_path)
        
        # 완료 메시지
        print("="*60)
        print("🎉 Processing Complete!")
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
        
        # Step 1: 이미지 변환 확인
        print("🖼️  Step 1: Converting page to image...")
        print(f"   Image size: {page_image.width}x{page_image.height}")
        
        # Step 2: 레이아웃 감지
        print("🔍 Step 2: Detecting layout regions...")
        regions = self.layout_detector.detect_regions(page_image)
        print(f"   Found {len(regions)} regions")
        
        # Step 3: 영역별 컨텐츠 추출
        print("📝 Step 3: Extracting content from regions...")
        page_chunks = []
        
        for i, region in enumerate(regions, start=1):
            # 영역 이미지 잘라내기
            region_image = page_image.crop(region.bbox)
            
            # 컨텐츠 추출
            print(f"   Region {i}/{len(regions)}: {region.type} - {region.description}")
            extracted = self.extractor.extract(
                image=region_image,
                region_type=region.type,
                description=region.description
            )
            
            print(f"      ✓ Extracted {len(extracted.content)} characters (confidence: {extracted.confidence:.2f})")
            
            # 청킹
            region_chunks = self.chunker.chunk_region(
                content=extracted.content,
                region_type=extracted.type,
                page_num=page_num,
                section_path=region.description,
                source=extracted.metadata.get('source', 'unknown')
            )
            
            page_chunks.extend(region_chunks)
        
        # Step 4: 청킹 완료
        print("✂️  Step 4: Creating intelligent chunks...")
        for i, region in enumerate(regions, start=1):
            region_chunk_count = sum(
                1 for chunk in page_chunks
                if chunk.metadata['section_path'] == region.description
            )
            print(f"   Region {i}: {region_chunk_count} chunk(s) created")
        
        # 통계
        stats = {
            'page_num': page_num,
            'regions': len(regions),
            'chunks': len(page_chunks),
            'region_types': self._count_region_types(regions)
        }
        
        return page_chunks, stats
    
    def _pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """PDF → 이미지 변환"""
        
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
    
    def _count_chunk_types(self, chunks: List[Chunk]) -> Dict[str, int]:
        """청크 타입별 카운트"""
        counts = {}
        for chunk in chunks:
            counts[chunk.type] = counts.get(chunk.type, 0) + 1
        return counts
    
    def _count_region_types(self, regions: List[Region]) -> Dict[str, int]:
        """영역 타입별 카운트"""
        counts = {}
        for region in regions:
            counts[region.type] = counts.get(region.type, 0) + 1
        return counts
    
    def _save_results(self, result: Dict, output_dir: str, pdf_path: str):
        """결과 저장"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        pdf_name = Path(pdf_path).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 저장
        json_path = output_path / f"prism_result_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Results saved to: {json_path}")
        
        # Markdown 저장
        md_path = output_path / f"prism_result_{timestamp}.md"
        self._save_markdown(result, md_path)
        print(f"💾 Markdown saved to: {md_path}")
    
    def _save_markdown(self, result: Dict, md_path: Path):
        """Markdown 형식으로 저장"""
        
        with open(md_path, 'w', encoding='utf-8') as f:
            # 헤더
            f.write("# PRISM Phase 2.7 - 처리 결과\n\n")
            
            meta = result['metadata']
            f.write(f"**처리 일시:** {meta['processed_at']}\n")
            f.write(f"**총 페이지:** {meta['total_pages']}\n")
            f.write(f"**총 청크:** {meta['total_chunks']}\n")
            f.write(f"**처리 시간:** {meta['processing_time_seconds']:.2f}초\n\n")
            
            # 청크 타입 통계
            f.write("## 청크 타입별 통계\n\n")
            for chunk_type, count in meta['chunk_types'].items():
                f.write(f"- **{chunk_type}**: {count}개\n")
            f.write("\n---\n\n")
            
            # 청크별 내용
            for chunk in result['chunks']:
                f.write(f"## 📝 {chunk['chunk_id']}\n\n")
                f.write(f"**페이지:** {chunk['page_num']} | ")
                f.write(f"**타입:** {chunk['type']} | ")
                f.write(f"**토큰:** {chunk['metadata']['token_count']}\n")
                f.write(f"**경로:** {chunk['metadata']['section_path']}\n\n")
                f.write("### 내용\n\n")
                f.write(f"{chunk['content']}\n\n")
                f.write("---\n\n")


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
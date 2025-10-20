"""
PRISM Phase 2.8 Pipeline - VLM 통합 완성
Element 분류 + VLM 변환 + Intelligent Chunking

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-21
Version: 2.8
"""

import os
import json
import time
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from PIL import Image
import io
import logging

# Core 모듈
from core.element_classifier import ElementClassifier
from core.vlm_service import VLMService
from core.intelligent_chunker import IntelligentChunker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase28Pipeline:
    """
    PRISM Phase 2.8 파이프라인
    
    Features:
    ✅ Element 자동 분류 (Chart/Table/Diagram/Text/Image)
    ✅ VLM 기반 자연어 변환 (경쟁사 수준)
    ✅ Intelligent Chunking (의미 기반)
    ✅ 품질 자동 평가
    """
    
    def __init__(self, vlm_provider: str = "claude"):
        """
        Args:
            vlm_provider: VLM 제공자 ('claude', 'azure_openai', 'ollama')
        """
        self.vlm_provider = vlm_provider
        
        print("\n" + "="*60)
        print("🔷 PRISM Phase 2.8 Pipeline Initialization")
        print("="*60)
        
        # 서브 모듈 초기화
        print("📊 Element Classifier 초기화...")
        self.classifier = ElementClassifier(use_vlm=True, vlm_threshold=0.7)
        
        print("🤖 VLM Service 초기화...")
        self.vlm_service = VLMService()
        
        print("🧩 Intelligent Chunker 초기화...")
        self.chunker = IntelligentChunker(
            min_chunk_size=100,
            max_chunk_size=500,
            overlap=50
        )
        
        print("="*60 + "\n")
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 문서 처리 (VLM 통합)
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 처리 페이지 (None=전체)
            
        Returns:
            처리 결과 딕셔너리
        """
        
        start_time = time.time()
        
        print("\n" + "="*60)
        print(f"🔷 PRISM Phase 2.8 - PDF Processing")
        print("="*60)
        print(f"📄 Input: {pdf_path}")
        print(f"🤖 VLM Provider: {self.vlm_provider}")
        print(f"🎯 Max Pages: {max_pages or 'All'}")
        print("="*60 + "\n")
        
        # Step 1: PDF → 이미지 변환
        print("📄 Step 1: Converting PDF to images...")
        page_images = self._pdf_to_images(pdf_path, max_pages)
        total_pages = len(page_images)
        print(f"   ✓ Converted {total_pages} page(s)\n")
        
        # Step 2: 페이지별 처리
        all_chunks = []
        stage1_stats = []
        
        for page_num, page_image in enumerate(page_images, start=1):
            print(f"\n{'─'*60}")
            print(f"📄 Processing Page {page_num}/{total_pages}")
            print(f"{'─'*60}")
            
            # 페이지 처리
            page_chunks, stats = self._process_page_vlm(page_image, page_num)
            
            all_chunks.extend(page_chunks)
            stage1_stats.append(stats)
            
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
                'chunk_types': self._count_chunk_types(all_chunks),
                'phase': '2.8'
            },
            'stage1_elements': stage1_stats,
            'stage2_chunks': all_chunks
        }
        
        # Step 4: 파일 저장
        if output_dir:
            self._save_results(result, output_dir)
        
        # 완료 메시지
        print("\n" + "="*60)
        print("✅ Processing Complete!")
        print("="*60)
        print(f"⏱️  Total time: {elapsed_time:.1f}s")
        print(f"📊 Total chunks: {len(all_chunks)}")
        print(f"📈 Chunk types: {result['metadata']['chunk_types']}")
        print("="*60)
        
        return result
    
    def _pdf_to_images(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> List[Image.Image]:
        """PDF → 이미지 변환 (PyMuPDF)"""
        
        doc = fitz.open(pdf_path)
        images = []
        
        total_pages = len(doc) if max_pages is None else min(max_pages, len(doc))
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # 고해상도 렌더링 (DPI 300)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Image로 변환
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            images.append(image)
        
        doc.close()
        
        return images
    
    def _process_page_vlm(
        self,
        page_image: Image.Image,
        page_num: int
    ) -> tuple:
        """
        페이지 처리 (VLM 통합)
        
        Args:
            page_image: PIL Image
            page_num: 페이지 번호
            
        Returns:
            (chunks, stats)
        """
        
        print("🔍 Step 1: Element Classification...")
        
        # Element 분류
        classification = self.classifier.classify(page_image)
        
        element_type = classification.element_type
        confidence = classification.confidence
        
        print(f"   ✓ Type: {element_type} (confidence: {confidence:.2f})")
        
        # VLM 변환
        print("🤖 Step 2: VLM Transformation...")
        
        try:
            # 이미지 → bytes
            img_buffer = io.BytesIO()
            page_image.save(img_buffer, format='PNG')
            image_bytes = img_buffer.getvalue()
            
            # VLM 호출
            vlm_result = self.vlm_service.generate_caption(
                image_data=image_bytes,
                element_type=element_type
            )
            
            content = vlm_result['caption']
            tokens_used = vlm_result.get('tokens_used', 0)
            processing_time = vlm_result.get('processing_time_ms', 0) / 1000
            
            print(f"   ✓ Generated: {len(content)} chars")
            print(f"   ✓ Tokens: {tokens_used}, Time: {processing_time:.2f}s")
        
        except Exception as e:
            logger.error(f"❌ VLM 변환 실패: {e}")
            content = f"[Element 처리 실패: {str(e)}]"
            tokens_used = 0
            processing_time = 0
        
        # 청킹
        print("🧩 Step 3: Intelligent Chunking...")
        
        chunks = self.chunker.chunk_text(
            text=content,
            metadata={
                'page_number': page_num,
                'element_type': element_type,
                'confidence': confidence,
                'source': 'vlm'
            }
        )
        
        print(f"   ✓ Created {len(chunks)} chunk(s)")
        
        # 통계
        stats = {
            'page_number': page_num,
            'element_type': element_type,
            'confidence': confidence,
            'chunks_count': len(chunks),
            'tokens_used': tokens_used,
            'processing_time_sec': processing_time
        }
        
        return chunks, stats
    
    def _count_chunk_types(self, chunks: List[Dict]) -> Dict[str, int]:
        """청크 타입별 개수"""
        
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.get('element_type', 'unknown')
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        return type_counts
    
    def _save_results(self, result: Dict, output_dir: str):
        """결과 저장"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 저장
        json_path = output_path / f"result_phase28_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Markdown 저장
        md_path = output_path / f"result_phase28_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown(result))
        
        print(f"\n💾 Results saved:")
        print(f"   - JSON: {json_path}")
        print(f"   - MD: {md_path}")
    
    def _generate_markdown(self, result: Dict) -> str:
        """Markdown 생성"""
        
        md = []
        
        # 헤더
        md.append("# PRISM Phase 2.8 - 문서 추출 결과\n")
        md.append(f"**생성일시**: {result['metadata']['processed_at'][:19].replace('T', ' ')}\n")
        md.append("---\n\n")
        
        # 메타데이터
        meta = result['metadata']
        md.append("## 📄 문서 정보\n\n")
        md.append(f"- **파일명**: {meta['filename']}\n")
        md.append(f"- **총 페이지**: {meta['total_pages']}\n")
        md.append(f"- **처리 시간**: {meta['processing_time_sec']:.2f}초\n")
        md.append(f"- **총 청크**: {meta['total_chunks']}\n")
        md.append(f"- **VLM 프로바이더**: {meta['vlm_provider']}\n")
        md.append(f"- **Phase**: {meta['phase']}\n")
        md.append("\n---\n\n")
        
        # Stage 1 통계
        md.append("## 📊 Stage 1: Element 분류 통계\n\n")
        
        for stat in result.get('stage1_elements', []):
            md.append(f"### 페이지 {stat['page_number']}\n")
            md.append(f"- **타입**: {stat['element_type']}\n")
            md.append(f"- **신뢰도**: {stat['confidence']:.2f}\n")
            md.append(f"- **청크 수**: {stat['chunks_count']}\n")
            md.append(f"- **토큰 사용**: {stat['tokens_used']}\n")
            md.append(f"- **처리 시간**: {stat['processing_time_sec']:.2f}s\n\n")
        
        md.append("---\n\n")
        
        # Stage 2 청크
        md.append("## 🧩 Stage 2: 지능형 청크\n\n")
        
        for i, chunk in enumerate(result.get('stage2_chunks', []), 1):
            md.append(f"### 청크 #{i}\n\n")
            md.append(f"**페이지**: {chunk['page_number']}\n")
            md.append(f"**타입**: {chunk['element_type']}\n")
            md.append(f"**모델**: {chunk['model_used']}\n\n")
            md.append("**내용**:\n\n")
            md.append("```\n")
            md.append(chunk['content'])
            md.append("\n```\n\n")
            md.append("---\n\n")
        
        return ''.join(md)


# ========== CLI 실행 ==========

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python phase28_pipeline.py <pdf_path> [output_dir] [max_pages]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    pipeline = Phase28Pipeline()
    result = pipeline.process_pdf(pdf_path, output_dir, max_pages)
    
    print("\n✅ Done!")
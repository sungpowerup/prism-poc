"""
core/phase30_pipeline.py
PRISM Phase 3.0 파이프라인

Stage 1: PDF → Page Images
Stage 2: Layout Detection (페이지당 여러 영역)
Stage 3: Region-based VLM Analysis
Stage 4: Section-aware Chunking
"""

import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging
import cv2
import numpy as np
from dotenv import load_dotenv
from PIL import Image

# 환경 변수 로드
load_dotenv()

from .pdf_processor import PDFProcessor
from .layout_detector import LayoutDetector, Region
from .vlm_service import VLMService
from .section_chunker import SectionAwareChunker

logger = logging.getLogger(__name__)


class Phase30Pipeline:
    """
    PRISM Phase 3.0 파이프라인
    
    주요 개선사항:
    - Layout Detection으로 개별 영역 분리
    - Region-based VLM Analysis
    - Section-aware Chunking
    """
    
    def __init__(self, vlm_provider='azure_openai'):
        """
        Args:
            vlm_provider: 'azure_openai', 'claude', 'ollama'
        """
        logger.info("="*60)
        logger.info("PRISM Phase 3.0 Pipeline 초기화")
        logger.info("="*60)
        
        self.vlm_provider = vlm_provider
        
        # 컴포넌트 초기화
        self.pdf_processor = PDFProcessor()
        logger.info("✅ PDF Processor")
        
        self.vlm_service = VLMService(provider=vlm_provider)
        logger.info(f"✅ VLM Service ({vlm_provider})")
        
        self.layout_detector = LayoutDetector(
            vlm_service=self.vlm_service,
            use_vlm_validation=True
        )
        logger.info("✅ Layout Detector")
        
        self.chunker = SectionAwareChunker(
            min_size=100,
            max_size=500,
            preserve_structure=True
        )
        logger.info("✅ Section-aware Chunker")
        
        logger.info("="*60 + "\n")
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir='output',
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        PDF 처리
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 처리 페이지 수
            
        Returns:
            {
                'metadata': {...},
                'regions': [...],
                'chunks': [...]
            }
        """
        start_time = time.time()
        
        logger.info("\n" + "="*60)
        logger.info(f"📄 PRISM Phase 3.0 문서 처리")
        logger.info(f"   파일: {Path(pdf_path).name}")
        logger.info("="*60)
        
        # Stage 1: PDF → Images
        logger.info("\n--- Stage 1: PDF → Page Images ---")
        page_images_raw = self.pdf_processor.pdf_to_images(pdf_path)
        
        if max_pages:
            page_images_raw = page_images_raw[:max_pages]
        
        # PIL Image → numpy array 변환
        page_images = []
        for i, img in enumerate(page_images_raw, 1):
            if isinstance(img, str):
                # Base64 문자열인 경우
                import base64
                from io import BytesIO
                
                # data URL 제거
                if img.startswith('data:image'):
                    img = img.split(',')[1]
                
                img_bytes = base64.b64decode(img)
                pil_img = Image.open(BytesIO(img_bytes))
                np_img = np.array(pil_img)
            elif hasattr(img, 'convert'):
                # PIL Image인 경우
                np_img = np.array(img.convert('RGB'))
            else:
                # 이미 numpy array인 경우
                np_img = img
            
            # BGR → RGB 변환 확인 (OpenCV는 BGR 사용)
            if len(np_img.shape) == 3 and np_img.shape[2] == 3:
                # RGB 그대로 사용 (PIL은 RGB)
                page_images.append(np_img)
            else:
                page_images.append(np_img)
        
        logger.info(f"✅ {len(page_images)}개 페이지 변환 완료 (numpy array)\n")
        
        all_regions = []
        all_extractions = []
        
        # Stage 2 & 3: 페이지별 처리
        for page_num, page_img in enumerate(page_images, 1):
            logger.info("\n" + "="*60)
            logger.info(f"페이지 {page_num}/{len(page_images)} 처리")
            logger.info("="*60)
            
            # Stage 2: Layout Detection
            logger.info("\n--- Stage 2: Layout Detection ---")
            regions = self.layout_detector.detect_regions(page_img, page_num)
            
            # Stage 3: Region-based Extraction
            logger.info("\n--- Stage 3: Region-based Extraction ---")
            for region_num, region in enumerate(regions, 1):
                logger.info(f"\n[Region {region_num}/{len(regions)}] {region.type}")
                
                # 영역 크롭
                x, y, w, h = region.bbox
                crop = page_img[y:y+h, x:x+w]
                
                # 타입별 추출
                content = self._extract_content(crop, region)
                
                extraction = {
                    'page_number': page_num,
                    'region_number': region_num,
                    'region_type': region.type,
                    'bbox': region.bbox,
                    'content': content,
                    'metadata': region.metadata
                }
                
                all_regions.append(region)
                all_extractions.append(extraction)
                
                logger.info(f"   추출 완료: {len(content)}자")
        
        # Stage 4: Section-aware Chunking
        logger.info("\n" + "="*60)
        logger.info("--- Stage 4: Section-aware Chunking ---")
        logger.info("="*60)
        
        chunks = self.chunker.chunk_extractions(all_extractions)
        
        logger.info(f"\n✅ {len(chunks)}개 청크 생성 완료")
        
        # 결과 통합
        result = {
            'metadata': {
                'filename': Path(pdf_path).name,
                'phase': '3.0',
                'vlm_provider': self.vlm_provider,
                'processed_at': datetime.now().isoformat(),
                'total_pages': len(page_images),
                'total_regions': len(all_regions),
                'total_chunks': len(chunks),
                'processing_time_sec': round(time.time() - start_time, 2)
            },
            'regions': [r.to_dict() for r in all_regions],
            'extractions': all_extractions,
            'chunks': [c.to_dict() for c in chunks]
        }
        
        # 저장
        self._save_results(result, output_dir)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Phase 3.0 처리 완료")
        logger.info(f"   총 처리 시간: {result['metadata']['processing_time_sec']}초")
        logger.info(f"   감지된 영역: {len(all_regions)}개")
        logger.info(f"   생성된 청크: {len(chunks)}개")
        logger.info("="*60 + "\n")
        
        return result
    
    def _extract_content(self, crop_image: np.ndarray, region: Region) -> str:
        """
        영역 타입별 콘텐츠 추출
        
        Args:
            crop_image: 크롭된 영역 이미지
            region: 영역 정보
            
        Returns:
            추출된 텍스트
        """
        region_type = region.type
        
        if region_type == 'header':
            return self._extract_header(crop_image, region)
        elif region_type == 'chart':
            return self._extract_chart(crop_image, region)
        elif region_type == 'table':
            return self._extract_table(crop_image, region)
        elif region_type == 'map':
            return self._extract_map(crop_image, region)
        else:
            return self._extract_text(crop_image, region)
    
    def _extract_header(self, crop_image: np.ndarray, region: Region) -> str:
        """헤더 추출 (VLM)"""
        from prompts.layout_prompt import HEADER_EXTRACTION_PROMPT
        
        try:
            result = self.vlm_service.analyze_image(crop_image, HEADER_EXTRACTION_PROMPT)
            
            # JSON 파싱
            if isinstance(result, str):
                result = json.loads(result)
            
            header_text = result.get('text', '')
            
            logger.info(f"   헤더: {header_text}")
            
            return header_text
            
        except Exception as e:
            logger.error(f"   헤더 추출 실패: {e}")
            return "[헤더 추출 실패]"
    
    def _extract_chart(self, crop_image: np.ndarray, region: Region) -> str:
        """차트 데이터 추출 (VLM)"""
        from prompts.chart_prompt import CHART_EXTRACTION_PROMPT
        
        # 차트 타입 힌트
        chart_type = region.metadata.get('chart_type', 'unknown')
        
        prompt = CHART_EXTRACTION_PROMPT
        
        if chart_type == 'pie':
            prompt += "\n\n**힌트**: 이 차트는 원그래프(파이 차트)입니다."
        elif chart_type == 'bar':
            prompt += "\n\n**힌트**: 이 차트는 막대그래프입니다."
        
        try:
            caption = self.vlm_service.analyze_image(crop_image, prompt)
            
            logger.info(f"   차트 분석 완료: {len(caption)}자")
            
            return caption
            
        except Exception as e:
            logger.error(f"   차트 추출 실패: {e}")
            return "[차트 추출 실패]"
    
    def _extract_table(self, crop_image: np.ndarray, region: Region) -> str:
        """표 구조화 (VLM)"""
        from prompts.table_prompt import TABLE_EXTRACTION_PROMPT
        
        try:
            table_data = self.vlm_service.analyze_image(crop_image, TABLE_EXTRACTION_PROMPT)
            
            logger.info(f"   표 추출 완료: {len(table_data)}자")
            
            return table_data
            
        except Exception as e:
            logger.error(f"   표 추출 실패: {e}")
            return "[표 추출 실패]"
    
    def _extract_map(self, crop_image: np.ndarray, region: Region) -> str:
        """지도 데이터 추출 (VLM + 검증)"""
        from prompts.layout_prompt import MAP_REGION_PROMPT
        
        try:
            result = self.vlm_service.analyze_image(crop_image, MAP_REGION_PROMPT)
            
            # JSON 파싱 및 검증
            if isinstance(result, str):
                result = json.loads(result)
            
            regions_data = result.get('regions', [])
            
            # 검증: 지역 개수
            expected_regions = 6  # 한국 지도 기준
            if len(regions_data) < expected_regions:
                logger.warning(f"   ⚠️ 지역 개수 부족: {len(regions_data)}/{expected_regions}")
            
            # 텍스트 포맷
            lines = ["[지역별 분포]"]
            for r in regions_data:
                lines.append(f"- {r['name']}: {r['value']}%")
            
            map_text = "\n".join(lines)
            
            logger.info(f"   지도 추출 완료: {len(regions_data)}개 지역")
            
            return map_text
            
        except Exception as e:
            logger.error(f"   지도 추출 실패: {e}")
            return "[지도 추출 실패]"
    
    def _extract_text(self, crop_image: np.ndarray, region: Region) -> str:
        """일반 텍스트 추출 (OCR 또는 VLM)"""
        # TODO: PaddleOCR 통합
        
        from prompts.image_prompt import IMAGE_CAPTION_PROMPT
        
        try:
            text = self.vlm_service.analyze_image(crop_image, IMAGE_CAPTION_PROMPT)
            
            logger.info(f"   텍스트 추출 완료: {len(text)}자")
            
            return text
            
        except Exception as e:
            logger.error(f"   텍스트 추출 실패: {e}")
            return "[텍스트 추출 실패]"
    
    def _save_results(self, result: Dict, output_dir: str):
        """결과 저장 (JSON + MD)"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(result['metadata']['filename']).stem
        
        # JSON 저장
        json_path = output_path / f"prism_phase30_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 결과 저장: {json_path}")
        
        # Markdown 저장
        md_path = output_path / f"prism_phase30_{timestamp}.md"
        self._write_markdown(result, md_path)
        
        logger.info(f"💾 마크다운: {md_path}")
    
    def _write_markdown(self, result: Dict, md_path: Path):
        """Markdown 파일 생성"""
        lines = []
        
        lines.append(f"# PRISM Phase 3.0 - 구조화된 문서 추출\n")
        lines.append(f"**생성일시**: {result['metadata']['processed_at']}\n")
        lines.append("---\n")
        
        lines.append("## 📄 문서 정보\n")
        lines.append(f"- **파일명**: {result['metadata']['filename']}")
        lines.append(f"- **총 페이지**: {result['metadata']['total_pages']}개")
        lines.append(f"- **총 영역**: {result['metadata']['total_regions']}개")
        lines.append(f"- **총 청크**: {result['metadata']['total_chunks']}개")
        lines.append(f"- **처리 시간**: {result['metadata']['processing_time_sec']}초")
        lines.append(f"- **Phase**: 3.0\n")
        
        lines.append("## 🧩 청크\n")
        
        for i, chunk in enumerate(result['chunks'], 1):
            lines.append(f"### 청크 #{i}\n")
            lines.append(f"- **ID**: {chunk['chunk_id']}")
            lines.append(f"- **타입**: {chunk['metadata']['chunk_type']}")
            lines.append(f"- **섹션**: {chunk['metadata'].get('section_path', 'N/A')}")
            lines.append(f"- **페이지**: {chunk['metadata']['page_number']}\n")
            lines.append("```")
            lines.append(chunk['content'])
            lines.append("```\n")
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


# CLI 실행
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m core.phase30_pipeline <pdf_path> [output_dir] [vlm_provider]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    vlm_provider = sys.argv[3] if len(sys.argv) > 3 else 'azure_openai'
    
    pipeline = Phase30Pipeline(vlm_provider=vlm_provider)
    result = pipeline.process_pdf(pdf_path, output_dir)
    
    print(f"\n✅ 처리 완료!")
    print(f"   청크: {result['metadata']['total_chunks']}개")
    print(f"   시간: {result['metadata']['processing_time_sec']}초")
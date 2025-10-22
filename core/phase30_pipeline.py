"""
core/phase30_pipeline.py
PRISM Phase 3.0 - Main Pipeline

✅ 최종 완벽 수정:
1. VLM analyze_image() 파라미터: image_data (not image_base64)
2. SectionChunker 메소드: chunk_extractions() (not chunk)
3. region_id 자동 생성
4. all_extractions 데이터 구조 수정 (region_type 추가)

실행: Phase30Pipeline(vlm_provider).process_document(pdf_path)
"""

import os
import json
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging
import io
import numpy as np
from PIL import Image

from core.pdf_processor import PDFProcessor
from core.layout_detector import LayoutDetector
from core.vlm_service import VLMService
from core.section_chunker import SectionChunker
from prompts.chart_prompt import ChartPrompts

logger = logging.getLogger(__name__)


class Phase30Pipeline:
    """
    PRISM Phase 3.0 파이프라인
    - Layout Detection (CV 기반)
    - Region-based VLM Analysis
    - Section-aware Chunking
    """
    
    def __init__(self, vlm_provider: str = "azure_openai"):
        """
        Phase 3.0 파이프라인 초기화
        
        Args:
            vlm_provider: VLM 프로바이더 ('azure_openai', 'claude', 'ollama')
        """
        logger.info("="*60)
        logger.info("PRISM Phase 3.0 Pipeline 초기화")
        logger.info("="*60)
        
        # 컴포넌트 초기화
        self.pdf_processor = PDFProcessor()
        logger.info("✅ PDF Processor")
        
        self.vlm_service = VLMService(provider=vlm_provider)
        logger.info(f"✅ VLM Service ({vlm_provider})")
        
        self.layout_detector = LayoutDetector()
        logger.info("✅ Layout Detector")
        
        self.chunker = SectionChunker()
        logger.info("✅ Section-aware Chunker")
        
        logger.info("="*60 + "\n")
    
    def process_document(
        self,
        pdf_path: str,
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        문서 처리 (전체 파이프라인)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과
        """
        start_time = time.time()
        
        filename = Path(pdf_path).name
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 PRISM Phase 3.0 문서 처리")
        logger.info(f"   파일: {filename}")
        logger.info(f"{'='*60}")
        
        # Stage 1: PDF → Base64 Images
        logger.info(f"\n--- Stage 1: PDF → Base64 Images ---")
        base64_images = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages)
        
        logger.info(f"✅ {len(base64_images)}개 페이지 변환 완료")
        
        # Base64 문자열 → numpy array 변환
        page_images = []
        
        for idx, base64_str in enumerate(base64_images, 1):
            try:
                # Base64 디코딩
                if base64_str.startswith('data:image'):
                    base64_str = base64_str.split(',', 1)[1]
                
                img_bytes = base64.b64decode(base64_str)
                pil_img = Image.open(io.BytesIO(img_bytes))
                np_img = np.array(pil_img.convert('RGB'))
                
                page_images.append(np_img)
                
                logger.info(f"  페이지 {idx}: Base64 → numpy array 변환 완료 {np_img.shape}")
                
            except Exception as e:
                logger.error(f"  페이지 {idx} 변환 실패: {e}")
                raise
        
        logger.info(f"✅ {len(page_images)}개 페이지 numpy 변환 완료\n")
        
        # Stage 2~3: 페이지별 처리
        all_regions = []
        all_extractions = []
        region_id_counter = 0
        
        for page_num, page_image in enumerate(page_images, 1):
            logger.info(f"{'='*60}")
            logger.info(f"페이지 {page_num}/{len(page_images)} 처리")
            logger.info(f"{'='*60}")
            
            # Stage 2: Layout Detection
            logger.info(f"\n--- Stage 2: Layout Detection ---")
            
            try:
                regions = self.layout_detector.detect_regions(page_image, page_num)
                
                # region_id 및 page_number 추가
                for region in regions:
                    region_id_counter += 1
                    region['region_id'] = f"region_{region_id_counter:04d}"
                    region['page_number'] = page_num
                
                all_regions.extend(regions)
                
                logger.info(f"✅ {len(regions)}개 영역 감지 완료")
                
            except Exception as e:
                logger.error(f"❌ Layout Detection 실패: {e}")
                continue
            
            # Stage 3: Region-based Extraction
            logger.info(f"\n--- Stage 3: Region-based Extraction ---")
            
            for i, region in enumerate(regions, 1):
                logger.info(f"\n[Region {i}/{len(regions)}] {region['type']}")
                
                try:
                    # 영역 크롭
                    x, y, w, h = region['bbox']
                    
                    # 경계 체크
                    h_img, w_img = page_image.shape[:2]
                    x = max(0, min(x, w_img))
                    y = max(0, min(y, h_img))
                    w = max(1, min(w, w_img - x))
                    h = max(1, min(h, h_img - y))
                    
                    roi = page_image[y:y+h, x:x+w]
                    
                    # numpy array → PIL Image → Base64
                    pil_roi = Image.fromarray(roi)
                    buffer = io.BytesIO()
                    pil_roi.save(buffer, format='PNG')
                    buffer.seek(0)
                    roi_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                    
                    # VLM 분석
                    element_type = region['type']
                    prompt = ChartPrompts.get_prompt_for_type(element_type)
                    
                    # ✅ 수정: VLM 호출 파라미터 (image_data)
                    content = self.vlm_service.analyze_image(
                        image_data=roi_base64,
                        prompt=prompt
                    )
                    
                    # UTF-8 인코딩 확인
                    if content:
                        try:
                            content.encode('utf-8')
                        except UnicodeEncodeError:
                            logger.warning(f"  ⚠️ UTF-8 인코딩 오류 감지, 재인코딩 시도")
                            content = content.encode('latin1').decode('utf-8', errors='ignore')
                    
                    # ✅ 수정: extraction 데이터 구조 (region_type 추가)
                    extraction = {
                        'region_id': region['region_id'],
                        'page_number': page_num,
                        'region_type': element_type,  # SectionChunker가 요구하는 키
                        'type': element_type,  # 호환성 유지
                        'bbox': region['bbox'],
                        'confidence': region['confidence'],
                        'content': content or '',
                        'metadata': region.get('metadata', {})
                    }
                    
                    all_extractions.append(extraction)
                    
                    logger.info(f"  ✅ VLM 분석 완료 ({len(content or '')}자)")
                    
                except Exception as e:
                    logger.error(f"  ❌ Region 처리 실패: {e}")
                    continue
        
        # Stage 4: Section-aware Chunking
        logger.info(f"\n{'='*60}")
        logger.info("--- Stage 4: Section-aware Chunking ---")
        logger.info(f"{'='*60}")
        
        try:
            # ✅ 수정: chunk_extractions() 메소드 호출
            chunks = self.chunker.chunk_extractions(all_extractions)
            logger.info(f"✅ {len(chunks)}개 청크 생성 완료\n")
        except Exception as e:
            logger.error(f"❌ Chunking 실패: {e}")
            logger.exception(e)
            chunks = []
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # 결과 조합
        result = {
            'metadata': {
                'filename': filename,
                'total_pages': len(page_images),
                'total_regions': len(all_regions),
                'total_chunks': len(chunks),
                'processing_time_sec': round(processing_time, 2),
                'vlm_provider': self.vlm_service.provider,
                'processed_at': datetime.now().isoformat()
            },
            'regions': all_regions,
            'extractions': all_extractions,
            'chunks': chunks
        }
        
        logger.info(f"{'='*60}")
        logger.info("✅ Phase 3.0 처리 완료!")
        logger.info(f"   총 페이지: {len(page_images)}개")
        logger.info(f"   감지된 영역: {len(all_regions)}개")
        logger.info(f"   생성된 청크: {len(chunks)}개")
        logger.info(f"   처리 시간: {processing_time:.2f}초")
        logger.info(f"{'='*60}\n")
        
        return result


# 테스트
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python -m core.phase30_pipeline <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # 환경 변수 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    # 파이프라인 실행
    pipeline = Phase30Pipeline(vlm_provider='azure_openai')
    result = pipeline.process_document(pdf_path, max_pages=3)
    
    # 결과 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))
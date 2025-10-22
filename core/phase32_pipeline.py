"""
core/phase32_pipeline.py
PRISM Phase 3.2 - Ultra Filtering Pipeline (Fixed)

✅ 수정사항:
- layout_detector.detect() → layout_detector.detect_regions()

Author: 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.2.1 (Method Name Fix)
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid
import base64
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)


class Phase32Pipeline:
    """
    Phase 3.2 처리 파이프라인
    
    특징:
    - Layout Detector v3.2 (Ultra Filtering)
    - Region 수 대폭 감소 (목표: 20-30개)
    - VLM API 호출 최소화
    """
    
    def __init__(self, pdf_processor, layout_detector, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            layout_detector: LayoutDetectorV32 인스턴스
            vlm_service: VLMService 인스턴스
            storage: Storage 인스턴스
        """
        self.pdf_processor = pdf_processor
        self.layout_detector = layout_detector
        self.vlm_service = vlm_service
        self.storage = storage
    
    def process_pdf(
        self, 
        pdf_path: str, 
        max_pages: int = 20
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Phase 3.2 처리 시작: {pdf_path}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"{'='*60}")
        
        # ==========================================
        # Stage 1: PDF → 이미지 변환
        # ==========================================
        logger.info("📄 Stage 1: PDF → 이미지 변환")
        
        pages = self.pdf_processor.pdf_to_images(pdf_path, max_pages)
        
        logger.info(f"  ✅ {len(pages)}개 페이지 변환 완료\n")
        
        # ==========================================
        # Stage 2: Layout Detection (Ultra Filtering)
        # ==========================================
        logger.info("🔍 Stage 2: Layout Detection (v3.2)")
        
        all_regions = []
        
        for page_num, page_data in enumerate(pages, start=1):
            logger.info(f"  📃 Page {page_num}/{len(pages)} 분석 중...")
            
            # PIL Image 또는 base64 처리
            if isinstance(page_data, str):
                # ✅ Data URL 형식 처리 (data:image/png;base64,...)
                if page_data.startswith('data:image'):
                    # "data:image/png;base64," 부분 제거
                    page_data = page_data.split(',', 1)[1]
                
                # ✅ Base64 padding 수정 (길이를 4의 배수로)
                missing_padding = len(page_data) % 4
                if missing_padding:
                    page_data += '=' * (4 - missing_padding)
                
                # base64 → numpy array
                image_bytes = base64.b64decode(page_data)
                pil_image = Image.open(io.BytesIO(image_bytes))
                page_array = np.array(pil_image)
            elif isinstance(page_data, Image.Image):
                # PIL Image → numpy array
                page_array = np.array(page_data)
            else:
                # 이미 numpy array
                page_array = page_data
            
            # ✅ 수정: detect() → detect_regions()
            regions = self.layout_detector.detect_regions(page_array, page_num - 1)
            
            logger.info(f"    ✅ {len(regions)}개 Region 감지")
            
            # 각 Region에 페이지 번호 및 ID 추가
            for i, region in enumerate(regions):
                region['page'] = page_num
                region['region_id'] = f"p{page_num}_r{i+1}"
                
                # 이미지 데이터 추출 (bbox 기반)
                bbox = region['bbox']
                x, y, w, h = bbox
                
                # ROI 추출
                roi = page_array[y:y+h, x:x+w]
                
                # base64 인코딩
                pil_roi = Image.fromarray(roi)
                buffer = io.BytesIO()
                pil_roi.save(buffer, format='PNG')
                region['image_data'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            all_regions.extend(regions)
        
        logger.info(f"\n  ✅ 총 {len(all_regions)}개 Region 감지 완료\n")
        
        # ==========================================
        # Stage 3: VLM 변환
        # ==========================================
        logger.info("🧠 Stage 3: VLM 변환")
        
        results = []
        vlm_calls = 0
        success_count = 0
        
        for i, region in enumerate(all_regions, start=1):
            logger.info(f"  🔄 Region {i}/{len(all_regions)} 처리 중...")
            
            try:
                # VLM 호출
                result = self.vlm_service.analyze_image(
                    image_data=region['image_data'],
                    element_type=region['type']
                )
                
                vlm_calls += 1
                success_count += 1
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region['type'],
                    'bbox': region['bbox'],
                    'confidence': region.get('confidence', 0.0),
                    'content': result.get('content', ''),
                    'metadata': region.get('metadata', {}),
                    'status': 'success'
                })
                
                logger.info(f"    ✅ 변환 완료")
            
            except Exception as e:
                logger.error(f"    ❌ VLM 변환 실패: {e}")
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region['type'],
                    'bbox': region['bbox'],
                    'confidence': 0.0,
                    'content': '',
                    'error': str(e),
                    'status': 'failed'
                })
        
        # ==========================================
        # 결과 요약
        # ==========================================
        total_time = time.time() - start_time
        
        # 평균 신뢰도 계산
        confidences = [r['confidence'] for r in results if r['status'] == 'success']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Phase 3.2 처리 완료!")
        logger.info(f"{'='*60}")
        logger.info(f"  📊 감지된 Region: {len(all_regions)}개")
        logger.info(f"  ✅ 성공: {success_count}개")
        logger.info(f"  ❌ 실패: {len(results) - success_count}개")
        logger.info(f"  🔥 VLM API 호출: {vlm_calls}회")
        logger.info(f"  ⏱️  총 처리 시간: {total_time:.2f}초")
        logger.info(f"  🎯 평균 신뢰도: {avg_confidence:.2%}")
        logger.info(f"{'='*60}\n")
        
        return {
            'session_id': session_id,
            'total_pages': len(pages),
            'total_regions': len(all_regions),
            'results': results,
            'success_count': success_count,
            'failed_count': len(results) - success_count,
            'vlm_calls': vlm_calls,
            'total_time_sec': total_time,
            'avg_confidence': avg_confidence
        }


# 테스트
if __name__ == '__main__':
    import sys
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 임포트
    from core.pdf_processor import PDFProcessor
    from core.layout_detector_v3 import LayoutDetectorV32
    from core.vlm_service import VLMService
    from core.storage import Storage
    
    # 초기화
    pdf_processor = PDFProcessor()
    layout_detector = LayoutDetectorV32()
    vlm_service = VLMService(provider='azure_openai')
    storage = Storage('data/prism_poc.db')
    
    # 파이프라인
    pipeline = Phase32Pipeline(
        pdf_processor,
        layout_detector,
        vlm_service,
        storage
    )
    
    # 테스트
    if len(sys.argv) < 2:
        print("사용법: python -m core.phase32_pipeline <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = pipeline.process_pdf(pdf_path, max_pages=3)
    
    print(f"\n✅ 처리 완료!")
    print(f"Session ID: {result['session_id']}")
    print(f"총 Region: {result['total_regions']}개")
    print(f"성공: {result['success_count']}개")
    print(f"실패: {result['failed_count']}개")
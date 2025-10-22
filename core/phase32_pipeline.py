"""
core/phase32_pipeline.py

PRISM Phase 3.2 - Ultra Filtering Pipeline (Final)

✅ 최종 수정 사항:
1. VLMService.analyze_image() 메서드 사용 (실제 구현과 일치)
2. 파라미터: image_data, element_type, prompt
3. 결과는 문자열로 직접 반환됨

Author: PRISM 개발팀
Date: 2025-10-22
Version: 3.2.3 (Final - analyze_image)
"""

import logging
import time
import base64
import io
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase32Pipeline:
    """
    PRISM Phase 3.2 파이프라인
    
    단계:
    1. PDF → 이미지 (PyMuPDF)
    2. Layout Detection V3.2 (Ultra Filtering)
    3. VLM 변환 (Region → Caption)
    4. 결과 구조화 및 저장
    """
    
    def __init__(
        self,
        pdf_processor,
        layout_detector,
        vlm_service,
        storage
    ):
        """
        초기화
        
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
        
        logger.info("✅ Phase32Pipeline 초기화 완료")
    
    def process_pdf(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        PDF 문서 처리 (app_phase32.py 호환 메서드)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 (None=전체)
        
        Returns:
            처리 결과 딕셔너리
        """
        # 자동으로 session_id 생성
        session_id = str(uuid.uuid4())[:8]
        return self.process(session_id, pdf_path, max_pages)
    
    def process(
        self,
        session_id: str,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        PDF 문서 전체 처리
        
        Args:
            session_id: 세션 ID
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 (None=전체)
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("🚀 PRISM Phase 3.2 처리 시작")
        logger.info(f"📄 파일: {pdf_path}")
        logger.info(f"🆔 세션: {session_id}")
        logger.info("="*60)
        
        # ==========================================
        # Stage 1: PDF → Images
        # ==========================================
        logger.info("\n📖 Stage 1: PDF → 이미지 변환")
        
        try:
            pages_data = self.pdf_processor.pdf_to_images(
                pdf_path=pdf_path,
                max_pages=max_pages
            )
            logger.info(f"  ✅ {len(pages_data)}개 페이지 변환 완료")
        except Exception as e:
            logger.error(f"  ❌ PDF 변환 실패: {e}")
            raise
        
        # ==========================================
        # Stage 2: Layout Detection V3.2
        # ==========================================
        logger.info("\n🔍 Stage 2: Layout Detection V3.2 (Ultra Filtering)")
        
        all_regions = []
        
        for page_num, page_data in enumerate(pages_data, start=1):
            logger.info(f"\n  📄 Page {page_num}/{len(pages_data)} 처리 중...")
            
            # Base64 → numpy array
            if isinstance(page_data, str):
                # ✅ Data URL 형식 처리 (data:image/png;base64,...)
                if page_data.startswith('data:image'):
                    # "data:image/png;base64," 부분 제거
                    page_data = page_data.split(',', 1)[1]
                
                # Base64 padding 추가
                missing_padding = len(page_data) % 4
                if missing_padding:
                    page_data += '=' * (4 - missing_padding)
                
                # 디코딩
                image_bytes = base64.b64decode(page_data)
                image = Image.open(io.BytesIO(image_bytes))
                page_array = np.array(image)
            else:
                page_array = page_data
            
            # Layout Detection
            regions = self.layout_detector.detect_regions(page_array, page_num - 1)
            
            logger.info(f"    ✅ {len(regions)}개 Region 감지")
            
            # 각 Region에 페이지 번호 및 ID 추가
            for i, region in enumerate(regions):
                region['page'] = page_num
                region['region_id'] = f"p{page_num}_r{i+1}"
                
                # 이미지 데이터 추출 (bbox 기반)
                bbox = region['bbox']
                x, y, w, h = bbox
                
                # 경계 체크
                h_img, w_img = page_array.shape[:2]
                x = max(0, min(x, w_img))
                y = max(0, min(y, h_img))
                w = max(1, min(w, w_img - x))
                h = max(1, min(h, h_img - y))
                
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
                # ✅ VLMService.analyze_image() 호출
                region_type = region.get('region_type', 'unknown')
                prompt = f"Describe this {region_type} in detail."
                
                content = self.vlm_service.analyze_image(
                    image_data=region['image_data'],
                    element_type=region_type,
                    prompt=prompt
                )
                
                # 신뢰도 추정 (VLM 응답 길이 기반)
                confidence = min(0.7 + len(content) / 1000, 0.95) if content else 0.0
                
                vlm_calls += 1
                success_count += 1
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region_type,
                    'bbox': region['bbox'],
                    'confidence': confidence,
                    'content': content,
                    'status': 'success'
                })
                
                logger.info(f"    ✅ 변환 성공 (신뢰도: {confidence:.2f})")
                
            except Exception as e:
                logger.error(f"    ❌ VLM 변환 실패: {e}")
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region.get('region_type', 'unknown'),
                    'bbox': region['bbox'],
                    'confidence': 0.0,
                    'content': '',
                    'error': str(e),
                    'status': 'failed'
                })
        
        # ==========================================
        # Stage 4: 결과 집계
        # ==========================================
        logger.info("\n📊 Stage 4: 결과 집계")
        
        total_time = time.time() - start_time
        failed_count = len(results) - success_count
        avg_confidence = (
            sum(r['confidence'] for r in results if r['status'] == 'success') / success_count
            if success_count > 0 else 0.0
        )
        
        result_summary = {
            'session_id': session_id,
            'total_pages': len(pages_data),
            'total_regions': len(all_regions),
            'results': results,
            'success_count': success_count,
            'failed_count': failed_count,
            'vlm_calls': vlm_calls,
            'total_time_sec': total_time,
            'avg_confidence': avg_confidence
        }
        
        logger.info(f"  ✅ 성공: {success_count}개")
        logger.info(f"  ❌ 실패: {failed_count}개")
        logger.info(f"  🔗 VLM 호출: {vlm_calls}회")
        logger.info(f"  ⏱️ 처리 시간: {total_time:.1f}초")
        logger.info(f"  📈 평균 신뢰도: {avg_confidence:.2%}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Phase 3.2 처리 완료!")
        logger.info("="*60 + "\n")
        
        return result_summary
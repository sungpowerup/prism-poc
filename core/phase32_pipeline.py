"""
core/phase32_pipeline.py
PRISM Phase 3.2 - Ultra Filtering Pipeline

Layout Detector v3.2 통합
"""

import logging
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)


class Phase32Pipeline:
    """
    Phase 3.2 처리 파이프라인
    
    특징:
    - Layout Detector v3.2 (Ultra Filtering)
    - Region 수 대폭 감소 (목표: 6-8개)
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
        
        logger.info(f"🚀 Phase 3.2 처리 시작: {pdf_path}")
        
        # ==========================================
        # Stage 1: PDF → 이미지 변환
        # ==========================================
        logger.info("📄 Stage 1: PDF → 이미지 변환")
        
        # ✅ 수정: extract_pages_as_base64 → pdf_to_images
        pages = self.pdf_processor.pdf_to_images(pdf_path, max_pages)
        
        logger.info(f"  ✅ {len(pages)}개 페이지 변환 완료")
        
        # ==========================================
        # Stage 2: Layout Detection (Ultra Filtering)
        # ==========================================
        logger.info("🔍 Stage 2: Layout Detection (v3.2)")
        
        all_regions = []
        
        for page_num, page_image in enumerate(pages, start=1):
            logger.info(f"  📃 Page {page_num} 분석 중...")
            
            # Layout Detector v3.2 실행
            regions = self.layout_detector.detect(page_image, page_num)
            
            logger.info(f"    ✅ {len(regions)}개 Region 감지")
            
            # 각 Region에 페이지 번호 추가
            for region in regions:
                region['page'] = page_num
            
            all_regions.extend(regions)
        
        logger.info(f"  ✅ 총 {len(all_regions)}개 Region 감지 완료")
        
        # ==========================================
        # Stage 3: VLM 변환
        # ==========================================
        logger.info("🧠 Stage 3: VLM 변환")
        
        results = []
        vlm_calls = 0
        
        for i, region in enumerate(all_regions, start=1):
            logger.info(f"  🔄 Region {i}/{len(all_regions)} 처리 중...")
            
            try:
                # VLM 호출
                caption = self.vlm_service.generate_caption(
                    image_data=region['image_data'],
                    element_type=region['region_type']
                )
                
                vlm_calls += 1
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region['region_type'],
                    'bbox': region['bbox'],
                    'confidence': region.get('confidence', 0.0),
                    'caption': caption,
                    'status': 'success'
                })
                
                logger.info(f"    ✅ 변환 완료 (신뢰도: {region.get('confidence', 0.0):.2f})")
            
            except Exception as e:
                logger.error(f"    ❌ VLM 변환 실패: {e}")
                
                results.append({
                    'region_id': region['region_id'],
                    'page': region['page'],
                    'region_type': region['region_type'],
                    'bbox': region['bbox'],
                    'confidence': 0.0,
                    'caption': None,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # ==========================================
        # Stage 4: 결과 저장
        # ==========================================
        logger.info("💾 Stage 4: 결과 저장")
        
        # Session 생성
        import uuid
        session_id = str(uuid.uuid4())
        
        self.storage.create_session(
            session_id=session_id,
            filename=pdf_path
        )
        
        # Element 저장
        for result in results:
            self.storage.save_element({
                'id': result['region_id'],
                'session_id': session_id,
                'page_number': result['page'],
                'type': result['region_type'],
                'original': None,  # 이미지는 별도 저장 가능
                'caption': result['caption'],
                'confidence': result['confidence']
            })
        
        # 메트릭 저장
        success_count = sum(1 for r in results if r['status'] == 'success')
        avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0.0
        
        total_time = time.time() - start_time
        
        self.storage.update_metrics(
            session_id=session_id,
            total_elements=len(all_regions),
            processed_elements=len(results),
            avg_confidence=avg_confidence,
            total_time_sec=total_time
        )
        
        logger.info(f"  ✅ Session {session_id} 저장 완료")
        
        # ==========================================
        # 최종 결과
        # ==========================================
        logger.info("="*60)
        logger.info("🎉 Phase 3.2 처리 완료!")
        logger.info(f"  📊 감지된 Region: {len(all_regions)}개")
        logger.info(f"  ✅ 성공: {success_count}개")
        logger.info(f"  ❌ 실패: {len(results) - success_count}개")
        logger.info(f"  🔥 VLM API 호출: {vlm_calls}회")
        logger.info(f"  ⏱️  총 처리 시간: {total_time:.2f}초")
        logger.info(f"  🎯 평균 신뢰도: {avg_confidence:.2%}")
        logger.info("="*60)
        
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
    vlm_service = VLMService(
        provider='azure',
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
        endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
    )
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
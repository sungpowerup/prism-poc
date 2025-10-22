"""
core/phase35_pipeline.py
PRISM Phase 3.5 - Pipeline (VLM 프롬프트 전면 개선)

Author: 이서영 (Backend Lead)
Date: 2025-10-23
Version: 3.5
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


class Phase35Pipeline:
    """
    Phase 3.5 처리 파이프라인
    
    특징:
    - Layout Detector v3.5 (표/막대/원그래프 개선)
    - VLM 프롬프트 전면 개선 (데이터 누락 방지)
    - JSON 직렬화 안정화
    """
    
    def __init__(self, pdf_processor, layout_detector, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            layout_detector: LayoutDetectorV35 인스턴스
            vlm_service: VLMService 인스턴스
            storage: Storage 인스턴스
        """
        self.pdf_processor = pdf_processor
        self.layout_detector = layout_detector
        self.vlm_service = vlm_service
        self.storage = storage
        
        # Phase 3.5 프롬프트 (전면 개선)
        self.prompts = {
            'header': """이 이미지는 문서의 헤더 영역입니다.

**CRITICAL**: 이미지에 보이는 **모든 텍스트**를 정확히 추출하세요.

다음 정보를 추출:
- 제목 (있는 경우)
- 날짜 (있는 경우)
- 페이지 번호 (있는 경우)
- 섹션명 (있는 경우)
- 기타 메타데이터

JSON 형식으로 반환:
{
  "title": "...",
  "date": "...",
  "page_number": "...",
  "section": "...",
  "metadata": {...}
}

**주의**: 텍스트가 없다고 판단하지 말고, OCR을 최대한 활용하세요.""",
            
            'pie_chart': """이 이미지는 원그래프입니다.

**CRITICAL**: 다음 정보를 **간결하게** 추출하세요 (RAG 최적화):

1. 제목 (있는 경우)
2. 각 섹터의 레이블과 값 (%)
3. 합계 확인

JSON 형식으로 반환:
{
  "title": "...",
  "data": [
    {"label": "...", "value": "...", "percentage": "..."},
    ...
  ],
  "total": "..."
}

**주의**: 
- 설명문 없이 데이터만 추출하세요
- "이 원그래프는..." 같은 서술 금지
- 모든 섹터를 빠짐없이 추출하세요""",
            
            'bar_chart': """이 이미지는 막대그래프입니다.

**CRITICAL**: 다음 정보를 **간결하게** 추출하세요 (RAG 최적화):

1. 제목 (있는 경우)
2. X축 레이블
3. Y축 레이블
4. **모든 막대의 레이블과 값** (빠짐없이)

JSON 형식으로 반환:
{
  "title": "...",
  "x_label": "...",
  "y_label": "...",
  "data": [
    {"label": "...", "value": "..."},
    ...
  ]
}

**IMPORTANT**: 
- data 배열을 비워두지 마세요! 반드시 모든 막대의 값을 추출하세요
- 막대가 10개면 data에 10개 항목이 있어야 합니다
- 설명문 없이 데이터만 추출하세요""",
            
            'table': """이 이미지는 표입니다.

**CRITICAL**: 다음 정보를 **간결하게** 추출하세요 (RAG 최적화):

1. 제목 (있는 경우)
2. 헤더 행 (열 이름)
3. **모든 데이터 행** (빠짐없이)

JSON 형식으로 반환:
{
  "title": "...",
  "headers": ["...", "...", ...],
  "rows": [
    ["...", "...", ...],
    ...
  ]
}

**IMPORTANT**:
- rows 배열을 비워두지 마세요! 모든 행을 추출하세요
- 표에 10행이 있으면 rows에 10개 항목이 있어야 합니다
- 설명문 없이 데이터만 추출하세요""",
            
            'text': """이 이미지는 일반 텍스트 영역입니다.

**CRITICAL**: 다음 정보를 **간결하게** 추출하세요 (RAG 최적화):

1. 섹션 제목 (있는 경우)
2. 주요 내용 (키워드 중심)
3. 숫자 데이터 (있는 경우)

JSON 형식으로 반환:
{
  "section_title": "...",
  "key_points": ["...", "...", ...],
  "numbers": {...}
}

**주의**: 장황한 설명 금지. 핵심만 추출하세요.""",
            
            'map': """이 이미지는 지도 또는 공간 데이터입니다.

**CRITICAL**: 다음 정보를 추출하세요:

1. **지역명** (모든 지역을 빠짐없이)
2. 각 지역의 데이터 값 (있는 경우)

JSON 형식으로 반환:
{
  "regions": ["지역1", "지역2", ...],
  "data": {
    "지역1": "값1",
    "지역2": "값2",
    ...
  }
}

**IMPORTANT**:
- regions 배열을 비워두지 마세요! 지도에 표시된 모든 지역명을 추출하세요
- 지역명이 "수도권", "경남권", "충청권" 등으로 표시되어 있으면 정확히 추출하세요
- 백분율(%) 값이 있으면 함께 추출하세요"""
        }
    
    def process_pdf(
        self, 
        pdf_path: str, 
        max_pages: int = 20,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            progress_callback: 진행 상황 콜백 함수
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Phase 3.5 처리 시작: {pdf_path}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"{'='*60}")
        
        # ========================================
        # Stage 1: PDF → 이미지 변환
        # ========================================
        if progress_callback:
            progress_callback("📄 PDF 변환 중...", 0)
        
        logger.info("\n[Stage 1] PDF → 이미지 변환")
        images = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages)
        logger.info(f"✅ {len(images)}개 페이지 변환 완료")
        
        if not images:
            logger.error("❌ PDF 변환 실패")
            return {
                'status': 'error',
                'error': 'PDF 변환 실패',
                'session_id': session_id
            }
        
        # ========================================
        # Stage 2: Layout Detection v3.5
        # ========================================
        all_regions = []
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int((page_num / len(images)) * 50)
                progress_callback(f"🔍 페이지 {page_num + 1}/{len(images)} 분석 중...", progress)
            
            logger.info(f"\n[Stage 2] 페이지 {page_num + 1} - Layout Detection v3.5")
            
            try:
                # Base64 디코딩
                if isinstance(img_data, str):
                    if ',' in img_data:
                        img_data = img_data.split(',', 1)[1]
                    
                    missing_padding = len(img_data) % 4
                    if missing_padding:
                        img_data += '=' * (4 - missing_padding)
                    
                    img_bytes = base64.b64decode(img_data)
                    img = Image.open(io.BytesIO(img_bytes))
                else:
                    img = Image.open(io.BytesIO(img_data))
                
                # NumPy 배열로 변환
                img_array = np.array(img)
                
                # BGR 변환
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    import cv2
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Layout Detection v3.5
                regions = self.layout_detector.detect_regions(img_array, page_num=page_num)
                
                # Region ID 및 이미지 데이터 추가
                for i, region in enumerate(regions):
                    region['region_id'] = f"page{page_num + 1}_region{i + 1}"
                    region['page_num'] = page_num + 1
                    
                    # Region 이미지 추출
                    bbox = region['bbox']
                    x, y, w, h = bbox
                    region_img = img_array[y:y+h, x:x+w]
                    
                    # PIL 이미지로 변환
                    if len(region_img.shape) == 3 and region_img.shape[2] == 3:
                        import cv2
                        region_img = cv2.cvtColor(region_img, cv2.COLOR_BGR2RGB)
                    
                    region_pil = Image.fromarray(region_img)
                    
                    # Base64 인코딩
                    buffer = io.BytesIO()
                    region_pil.save(buffer, format='PNG')
                    region['image_data'] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                all_regions.extend(regions)
                logger.info(f"✅ 페이지 {page_num + 1}: {len(regions)}개 영역 감지")
                
            except Exception as e:
                logger.error(f"❌ 페이지 {page_num + 1} 처리 실패: {e}")
                continue
        
        logger.info(f"\n✅ 총 {len(all_regions)}개 영역 감지 완료")
        
        # ========================================
        # Stage 3: VLM 변환
        # ========================================
        if progress_callback:
            progress_callback("🤖 VLM 변환 중...", 50)
        
        logger.info(f"\n[Stage 3] VLM 변환 시작 (총 {len(all_regions)}개)")
        
        results = []
        success_count = 0
        error_count = 0
        
        for i, region in enumerate(all_regions):
            if progress_callback:
                progress = 50 + int((i / len(all_regions)) * 50)
                progress_callback(f"🤖 VLM 변환 중... ({i+1}/{len(all_regions)})", progress)
            
            try:
                # 프롬프트 선택
                region_type = region['type']
                prompt = self.prompts.get(region_type, self.prompts['text'])
                
                # VLM 호출
                logger.info(f"   Region {region['region_id']} ({region_type}) 변환 중...")
                
                vlm_result = self.vlm_service.analyze_image(
                    image_data=region['image_data'],
                    element_type=region_type,
                    prompt=prompt
                )
                
                if vlm_result:
                    success_count += 1
                    logger.info(f"   ✅ 성공 ({len(vlm_result)} 글자)")
                    
                    # NumPy 타입 변환
                    bbox = region['bbox']
                    bbox_list = [int(x) for x in bbox]
                    
                    confidence = float(region['confidence'])
                    
                    # metadata 변환
                    metadata = region.get('metadata', {})
                    clean_metadata = {}
                    for key, value in metadata.items():
                        if isinstance(value, (np.integer, np.floating)):
                            clean_metadata[key] = float(value)
                        elif isinstance(value, np.ndarray):
                            clean_metadata[key] = value.tolist()
                        elif isinstance(value, tuple):
                            clean_metadata[key] = [int(x) if isinstance(x, np.integer) else float(x) if isinstance(x, np.floating) else x for x in value]
                        else:
                            clean_metadata[key] = value
                    
                    results.append({
                        'region_id': region['region_id'],
                        'page_num': int(region['page_num']),
                        'type': region_type,
                        'bbox': bbox_list,
                        'confidence': confidence,
                        'vlm_result': vlm_result,
                        'metadata': clean_metadata
                    })
                else:
                    error_count += 1
                    logger.warning(f"   ⚠️ VLM 결과 없음")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"   ❌ 실패: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"\n✅ VLM 변환 완료: 성공 {success_count}개, 실패 {error_count}개")
        
        # ========================================
        # Stage 4: 결과 저장
        # ========================================
        if progress_callback:
            progress_callback("💾 저장 중...", 95)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result = {
            'status': 'success',
            'session_id': session_id,
            'processing_time': processing_time,
            'pages_processed': len(images),
            'regions_detected': len(all_regions),
            'vlm_success': success_count,
            'vlm_errors': error_count,
            'results': results
        }
        
        # DB 저장
        try:
            self.storage.save_session(result)
            logger.info("✅ DB 저장 완료")
        except Exception as e:
            logger.error(f"⚠️ DB 저장 실패: {e}")
        
        if progress_callback:
            progress_callback("✅ 완료!", 100)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Phase 3.5 처리 완료")
        logger.info(f"   - 처리 시간: {processing_time:.1f}초")
        logger.info(f"   - Region 감지: {len(all_regions)}개")
        if len(all_regions) > 0:
            logger.info(f"   - VLM 성공: {success_count}개 ({success_count/len(all_regions)*100:.1f}%)")
        logger.info(f"{'='*60}\n")
        
        return result

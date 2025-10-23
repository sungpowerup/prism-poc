"""
core/pdf_processor_v40.py
PRISM Phase 4.0 - PDF Processor (고해상도 지원)

✅ Phase 4.0 개선사항:
1. 고해상도 변환 지원 (300 DPI)
2. DPI 파라미터 추가

Author: 이서영 (Backend Lead)
Date: 2025-10-23
Version: 4.0
"""

import fitz  # PyMuPDF
import base64
import logging
from typing import List
from PIL import Image
import io

logger = logging.getLogger(__name__)


class PDFProcessorV40:
    """
    PDF 처리기 v4.0
    
    Phase 4.0 특징:
    - 고해상도 변환 (300 DPI)
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PDFProcessorV40 초기화 완료")
    
    def pdf_to_images(
        self, 
        pdf_path: str, 
        max_pages: int = 20,
        dpi: int = 300  # ✅ Phase 4.0: 고해상도
    ) -> List[str]:
        """
        PDF를 고해상도 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 변환 페이지 수
            dpi: 해상도 (기본 300 DPI)
        
        Returns:
            Base64 인코딩된 이미지 리스트
        """
        logger.info(f"PDF → 이미지 변환 시작: {pdf_path} (DPI: {dpi})")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), max_pages)
            logger.info(f"총 {total_pages}페이지 변환")
            
            images = []
            
            # DPI → 확대 배율 계산
            zoom = dpi / 72.0  # 기본 72 DPI 대비 배율
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # 고해상도 이미지 렌더링
                pix = page.get_pixmap(matrix=mat)
                
                # PIL Image로 변환
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Base64 인코딩
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                images.append(img_base64)
                
                logger.info(f"  Page {page_num + 1}/{total_pages} 변환 완료 ({pix.width}x{pix.height})")
            
            doc.close()
            
            logger.info(f"✅ {len(images)}개 이미지 변환 완료 (DPI: {dpi})")
            return images
            
        except Exception as e:
            logger.error(f"❌ PDF 변환 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

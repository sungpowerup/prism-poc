"""
core/pdf_processor.py
PRISM Phase 5.0 - PDF Processor

Author: 박준호 (AI/ML Lead)
Date: 2025-10-24
Version: 5.0
"""

import base64
import logging
from typing import List
from pdf2image import convert_from_path
from PIL import Image
import io

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF 처리 클래스
    
    특징:
    - PDF → 고해상도 이미지 변환
    - Base64 인코딩
    """
    
    def __init__(self):
        """PDF 프로세서 초기화"""
        logger.info("✅ PDFProcessor 초기화 완료")
    
    def pdf_to_images(
        self,
        pdf_path: str,
        max_pages: int = 20,
        dpi: int = 300
    ) -> List[str]:
        """
        PDF → Base64 인코딩된 이미지 리스트
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 페이지 수
            dpi: 해상도 (기본 300)
        
        Returns:
            Base64 인코딩된 이미지 리스트
        """
        logger.info(f"📄 PDF 변환 시작: {pdf_path}")
        logger.info(f"   - 최대 페이지: {max_pages}")
        logger.info(f"   - DPI: {dpi}")
        
        try:
            # PDF → PIL Image 변환
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=1,
                last_page=max_pages
            )
            
            logger.info(f"✅ {len(images)}개 페이지 변환 완료")
            
            # Base64 인코딩
            encoded_images = []
            for i, img in enumerate(images):
                # PNG로 변환
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                img_bytes = buffer.getvalue()
                
                # Base64 인코딩
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                encoded_images.append(img_base64)
                
                logger.info(f"   페이지 {i+1}: {len(img_base64)} 글자")
            
            return encoded_images
        
        except Exception as e:
            logger.error(f"❌ PDF 변환 실패: {e}")
            raise
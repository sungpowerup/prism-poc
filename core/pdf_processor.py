"""
core/pdf_processor.py
PRISM Phase 2.8 - PDF Processor

PyMuPDF 기반 PDF → 이미지 변환
"""

import io
import base64
import logging
from typing import List, Optional
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF 문서 처리기
    
    기능:
    - PDF → 페이지별 이미지 변환 (PyMuPDF)
    - 고해상도 렌더링 (DPI 300)
    - Base64 인코딩
    """
    
    def __init__(self, vlm_service=None):
        """
        Args:
            vlm_service: VLM 서비스 (선택적, 향후 확장용)
        """
        self.vlm_service = vlm_service
        self.dpi = 300  # 고해상도
    
    def pdf_to_images(
        self, 
        pdf_path: str, 
        max_pages: Optional[int] = None
    ) -> List[str]:
        """
        PDF → Base64 인코딩된 이미지 리스트
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 페이지 수 (None이면 전체)
        
        Returns:
            Base64 인코딩된 이미지 문자열 리스트
        """
        logger.info(f"PDF → 이미지 변환 시작: {pdf_path}")
        
        images = []
        
        try:
            # PDF 열기
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # 최대 페이지 제한
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            logger.info(f"총 {total_pages}페이지 변환")
            
            # 페이지별 이미지 변환
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # PIL Image로 변환
                image = self._page_to_image(page)
                
                # Base64 인코딩
                image_base64 = self._image_to_base64(image)
                
                images.append(image_base64)
                logger.info(f"  Page {page_num + 1}/{total_pages} 변환 완료")
            
            doc.close()
            
            logger.info(f"✅ {len(images)}개 이미지 변환 완료")
            return images
        
        except Exception as e:
            logger.error(f"❌ PDF 변환 실패: {e}")
            raise
    
    def _page_to_image(self, page) -> Image.Image:
        """
        PyMuPDF Page → PIL Image 변환
        
        Args:
            page: fitz.Page 객체
        
        Returns:
            PIL Image
        """
        # 고해상도 렌더링 매트릭스
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        
        # Pixmap 생성
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # PNG 바이트로 변환
        img_data = pix.tobytes("png")
        
        # PIL Image로 변환
        image = Image.open(io.BytesIO(img_data))
        
        return image
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        PIL Image → Base64 문자열
        
        Args:
            image: PIL Image
        
        Returns:
            Base64 인코딩된 문자열 (data URL 형식)
        """
        # PNG로 저장
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Base64 인코딩
        img_bytes = buffer.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Data URL 형식
        return f"data:image/png;base64,{img_base64}"


# 테스트
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python -m core.pdf_processor <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    processor = PDFProcessor()
    images = processor.pdf_to_images(pdf_path, max_pages=3)
    
    print(f"\n✅ 변환 완료: {len(images)}개 이미지")
    print(f"첫 번째 이미지 크기: {len(images[0])} bytes")
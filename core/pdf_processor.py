"""
core/pdf_processor.py
PRISM POC - PDF 처리기 (PyMuPDF 버전)
"""

from pathlib import Path
from typing import List, Dict
import io
from PIL import Image
import fitz  # PyMuPDF
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF → 이미지 변환 및 Element 추출"""
    
    def __init__(self):
        self.dpi = 200  # 이미지 품질
    
    def process_pdf(self, pdf_bytes: bytes, session_id: str) -> List[Dict]:
        """
        PDF → 페이지별 이미지 변환 (PyMuPDF 사용)
        
        Args:
            pdf_bytes: PDF 파일 바이트
            session_id: 세션 ID
            
        Returns:
            List[Dict]: Element 목록
        """
        elements = []
        
        try:
            # PyMuPDF로 PDF 열기
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            logger.info(f"PDF 문서 로드 완료: {len(doc)} 페이지")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 페이지를 이미지로 변환
                # zoom factor 계산 (DPI 200 기준)
                zoom = self.dpi / 72  # 기본 DPI는 72
                mat = fitz.Matrix(zoom, zoom)
                
                # 픽스맵 생성 (고품질)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                
                # PIL Image로 변환
                image = Image.open(io.BytesIO(img_bytes))
                
                # Element 생성
                element = {
                    'id': str(uuid.uuid4()),
                    'session_id': session_id,
                    'page_number': page_num + 1,
                    'element_type': 'image',  # 기본값
                    'bbox': None,
                    'image': image,
                    'status': 'pending'
                }
                
                elements.append(element)
                logger.info(f"페이지 {page_num + 1}/{len(doc)} 변환 완료")
            
            doc.close()
            logger.info(f"총 {len(elements)}개 Element 추출 완료")
            
        except Exception as e:
            logger.error(f"PDF 처리 오류: {e}")
            raise
        
        return elements
    
    def image_to_bytes(self, image: Image.Image, format: str = 'PNG') -> bytes:
        """PIL Image → bytes 변환"""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()


# 테스트 코드
if __name__ == '__main__':
    # 간단한 테스트
    processor = PDFProcessor()
    
    # 샘플 PDF 읽기
    with open('test.pdf', 'rb') as f:
        pdf_bytes = f.read()
    
    elements = processor.process_pdf(pdf_bytes, 'test_session')
    print(f"추출된 Element 수: {len(elements)}")
    
    for elem in elements:
        print(f"  - 페이지 {elem['page_number']}: {elem['image'].size}")
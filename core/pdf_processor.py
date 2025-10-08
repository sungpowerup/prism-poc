"""
core/pdf_processor.py
PRISM POC - PDF 처리기
"""

from pathlib import Path
from typing import List, Dict
import io
from PIL import Image
from pdf2image import convert_from_bytes
import uuid

class PDFProcessor:
    """PDF → 이미지 변환 및 Element 추출"""
    
    def __init__(self):
        self.dpi = 200  # 이미지 품질
    
    def process_pdf(self, pdf_bytes: bytes, session_id: str) -> List[Dict]:
        """
        PDF → 페이지별 이미지 변환
        
        Returns:
            List[Dict]: Element 목록
        """
        elements = []
        
        try:
            # PDF → 이미지 변환
            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt='png'
            )
            
            for page_num, image in enumerate(images, start=1):
                # 페이지를 하나의 Element로 취급
                element = {
                    'id': str(uuid.uuid4()),
                    'session_id': session_id,
                    'page_number': page_num,
                    'element_type': 'image',  # 기본값
                    'bbox': None,
                    'image': image,
                    'status': 'pending'
                }
                
                elements.append(element)
        
        except Exception as e:
            print(f"PDF 처리 오류: {e}")
            raise
        
        return elements
    
    def image_to_bytes(self, image: Image.Image, format: str = 'PNG') -> bytes:
        """PIL Image → bytes 변환"""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
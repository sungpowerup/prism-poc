"""
PDF Processor - OCR 및 이미지 추출 개선
"""

import io
import base64
import logging
from typing import List, Dict, Optional
from pdf2image import convert_from_bytes
from PIL import Image

logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF 처리 클래스"""
    
    def __init__(self):
        """초기화"""
        logger.info("PDFProcessor 초기화 중...")
        
        # PaddleOCR 초기화
        try:
            from paddleocr import PaddleOCR
            logger.info("PaddleOCR 초기화 중...")
            
            # PaddleOCR 3.3.0+에서는 use_gpu, show_log 파라미터가 제거됨
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean'
            )
            
            logger.info("[OK] PaddleOCR 초기화 완료")
        except Exception as e:
            logger.error(f"PaddleOCR 초기화 실패: {e}")
            self.ocr = None
    
    def process_pdf(self, pdf_data: bytes, dpi: int = 200) -> List[Dict]:
        """
        PDF 처리 (이미지 변환 + OCR)
        
        Args:
            pdf_data: PDF 바이너리 데이터
            dpi: 이미지 변환 해상도
        
        Returns:
            Element 리스트
        """
        elements = []
        
        try:
            # PDF -> 이미지 변환
            logger.info(f"PDF를 이미지로 변환 중... (DPI: {dpi})")
            images = convert_from_bytes(pdf_data, dpi=dpi)
            logger.info(f"{len(images)}개 페이지 변환 완료")
            
            # 페이지별 처리
            for page_num, image in enumerate(images, 1):
                logger.info(f"페이지 {page_num} 처리 중...")
                
                # 이미지 -> Base64
                image_base64 = self._image_to_base64(image)
                
                # OCR 텍스트 추출
                ocr_text = self._extract_ocr_text(image)
                
                element = {
                    'page_num': page_num,
                    'image_base64': image_base64,
                    'ocr_text': ocr_text,
                    'ocr_available': bool(ocr_text)
                }
                
                elements.append(element)
                
                logger.info(f"페이지 {page_num} 완료 (OCR: {len(ocr_text)}자)")
            
            return elements
        
        except Exception as e:
            logger.error(f"PDF 처리 오류: {e}", exc_info=True)
            raise
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        PIL Image -> Base64 문자열
        """
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"이미지 변환 오류: {e}")
            return ""
    
    def _extract_ocr_text(self, image: Image.Image) -> str:
        """
        이미지에서 OCR 텍스트 추출
        
        Args:
            image: PIL Image 객체
        
        Returns:
            추출된 텍스트
        """
        if not self.ocr:
            logger.warning("OCR 엔진이 초기화되지 않았습니다.")
            return ""
        
        try:
            # PIL Image -> numpy array
            import numpy as np
            img_array = np.array(image)
            
            # OCR 실행 (PaddleOCR 3.3.0+ 방식)
            result = self.ocr.predict(img_array)
            
            if not result or not result.get('dt_polys'):
                return ""
            
            # 텍스트 추출
            texts = []
            rec_text = result.get('rec_text', [])
            rec_score = result.get('rec_score', [])
            
            for text, score in zip(rec_text, rec_score):
                # 신뢰도 0.5 이상만
                if score >= 0.5:
                    texts.append(text)
            
            # 텍스트 결합
            full_text = '\n'.join(texts)
            
            return full_text
        
        except Exception as e:
            logger.error(f"OCR 추출 오류: {e}")
            return ""
    
    def extract_text_blocks(self, ocr_text: str) -> List[Dict]:
        """
        OCR 텍스트를 블록 단위로 분할
        
        Args:
            ocr_text: 전체 OCR 텍스트
        
        Returns:
            텍스트 블록 리스트
        """
        blocks = []
        
        # 빈 줄 기준으로 블록 분리
        paragraphs = [p.strip() for p in ocr_text.split('\n\n') if p.strip()]
        
        for idx, para in enumerate(paragraphs, 1):
            block = {
                'block_id': f"block_{idx:03d}",
                'text': para,
                'length': len(para),
                'lines': len(para.split('\n'))
            }
            blocks.append(block)
        
        return blocks
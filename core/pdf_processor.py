"""
PDF Processor with Fixed OCR Call
"""

import fitz  # PyMuPDF
import io
import base64
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서 처리기 (바이트 데이터 지원)"""
    
    def __init__(self):
        """초기화"""
        logger.info("PDFProcessor 초기화 중...")
        self.ocr = None
        
        # PaddleOCR 초기화 (선택적)
        try:
            logger.info("PaddleOCR 초기화 중...")
            from paddleocr import PaddleOCR
            
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean'
            )
            logger.info("OCR 초기화 완료")
        except Exception as e:
            logger.warning(f"OCR 초기화 실패: {e}")
            logger.info("OCR 없이 계속 진행합니다 (이미지만 추출)")
            self.ocr = None
    
    def process_pdf(self, pdf_data: bytes) -> List[Dict[str, Any]]:
        """
        PDF 바이트 데이터 처리
        
        Args:
            pdf_data: PDF 바이트 데이터
            
        Returns:
            Element 리스트
        """
        elements = []
        
        try:
            # 바이트 데이터를 직접 열기
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            logger.info(f"PDF 열기 성공: {len(doc)} 페이지")
            
            for page_num in range(len(doc)):
                try:
                    logger.info(f"Page {page_num + 1} 처리 시작...")
                    
                    page = doc[page_num]
                    
                    # 페이지를 이미지로 변환
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")
                    
                    # Base64 인코딩
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # OCR 텍스트 추출
                    ocr_text = ""
                    if self.ocr:
                        try:
                            # ✅ cls 파라미터 제거
                            result = self.ocr.ocr(img_bytes)
                            if result and result[0]:
                                ocr_text = "\n".join([
                                    line[1][0] 
                                    for line in result[0] 
                                    if line and len(line) > 1
                                ])
                        except Exception as e:
                            logger.warning(f"OCR 실패 (Page {page_num + 1}): {e}")
                    
                    # Element 생성
                    element = {
                        'page': page_num + 1,
                        'type': 'image',
                        'confidence': 0.5,
                        'image_base64': img_base64,
                        'ocr_text': ocr_text,
                        'bbox': {
                            'x': 0,
                            'y': 0,
                            'width': pix.width,
                            'height': pix.height
                        }
                    }
                    
                    elements.append(element)
                    logger.info(f"Page {page_num + 1} 처리 완료 ({len(ocr_text)}자 OCR)")
                    
                except Exception as e:
                    logger.error(f"Page {page_num + 1} 처리 실패: {e}")
                    continue
            
            doc.close()
            
        except Exception as e:
            logger.error(f"PDF 처리 실패: {e}", exc_info=True)
            raise
        
        return elements
    
    def get_page_count(self, pdf_data: bytes) -> int:
        """PDF 페이지 수 반환"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"페이지 수 확인 실패: {e}")
            return 0
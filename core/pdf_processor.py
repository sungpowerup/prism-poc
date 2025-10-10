"""
core/pdf_processor.py
PRISM POC - PDF 처리 (수정: OCR use_gpu 제거)
"""

import io
import time
from pathlib import Path
from typing import Dict, List, Optional
import base64

from pdf2image import convert_from_path
from PIL import Image
import fitz  # PyMuPDF

# OCR (선택적)
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

from utils.logger import setup_logger

logger = setup_logger(__name__)

class PDFProcessor:
    """PDF 문서 처리 클래스"""
    
    def __init__(self):
        """초기화"""
        logger.info("PDFProcessor 초기화 중...")
        self.ocr = None
        self._init_ocr()
    
    def _init_ocr(self):
        """PaddleOCR 초기화 (선택적)"""
        if not PADDLEOCR_AVAILABLE:
            logger.warning("PaddleOCR 미설치 - OCR 기능 비활성화")
            return
        
        try:
            logger.info("PaddleOCR 초기화 중...")
            
            # ✅ use_gpu 파라미터 제거 (기본값 사용)
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean',
                show_log=False  # 로그 줄이기
            )
            
            logger.info("PaddleOCR 초기화 완료")
            
        except Exception as e:
            logger.warning(f"OCR 초기화 실패: {e}")
            self.ocr = None
    
    def get_page_count(self, pdf_path: Path) -> int:
        """PDF 페이지 수 확인"""
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"PDF 열기 실패: {e}")
            raise
    
    def extract_text_ocr(self, image: Image.Image) -> str:
        """
        OCR로 텍스트 추출
        
        Args:
            image: PIL Image
        
        Returns:
            추출된 텍스트
        """
        if self.ocr is None:
            logger.warning("OCR 사용 불가 - 빈 문자열 반환")
            return ""
        
        try:
            # PIL → numpy array
            import numpy as np
            img_array = np.array(image)
            
            # OCR 실행
            result = self.ocr.ocr(img_array, cls=True)
            
            if not result or not result[0]:
                return ""
            
            # 텍스트 추출
            texts = []
            for line in result[0]:
                try:
                    if len(line) >= 2 and len(line[1]) >= 2:
                        text = line[1][0]
                        if text and text.strip():
                            texts.append(text)
                except (IndexError, TypeError) as e:
                    logger.debug(f"OCR 라인 파싱 실패: {e}")
                    continue
            
            extracted_text = ' '.join(texts)
            logger.info(f"OCR 추출 완료: {len(extracted_text)}자")
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"OCR 처리 오류: {e}")
            return ""
    
    def classify_image_type(self, image: Image.Image) -> Dict:
        """
        이미지 타입 간단 분류
        
        Returns:
            {
                'element_type': 'chart' | 'table' | 'image' | 'diagram',
                'confidence': float,
                'reasoning': str
            }
        """
        # 간단한 기본 분류 (실제로는 ElementClassifier 사용)
        width, height = image.size
        aspect_ratio = width / height
        
        # 일단 모두 'image'로 분류
        return {
            'element_type': 'image',
            'confidence': 0.5,
            'reasoning': f'Default classification (size: {width}x{height}, ratio: {aspect_ratio:.2f})'
        }
    
    def process_page(
        self, 
        pdf_path: Path, 
        page_num: int,
        use_ocr: bool = True
    ) -> Dict:
        """
        페이지 처리 (이미지 변환 + OCR)
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호 (1-based)
            use_ocr: OCR 사용 여부
        
        Returns:
            {
                'page_num': int,
                'image': PIL.Image,
                'image_base64': str,
                'ocr_text': str,
                'element_type': Dict,
                'processing_time': float
            }
        """
        start_time = time.time()
        
        logger.info(f"Page {page_num} 처리 시작...")
        
        try:
            # 1) PDF → 이미지 변환
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=200  # 적절한 해상도
            )
            
            if not images:
                raise ValueError(f"페이지 {page_num} 변환 실패")
            
            page_image = images[0]
            
            # 2) Base64 인코딩
            buffered = io.BytesIO()
            page_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # 3) OCR 텍스트 추출
            ocr_text = ""
            if use_ocr and self.ocr:
                ocr_text = self.extract_text_ocr(page_image)
            
            # 4) Element 타입 분류
            element_type = self.classify_image_type(page_image)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Page {page_num} 처리 완료 ({processing_time:.2f}초)")
            
            return {
                'page_num': page_num,
                'image': page_image,
                'image_base64': image_base64,
                'ocr_text': ocr_text,
                'element_type': element_type,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 실패: {e}")
            raise
    
    def process_pdf(
        self, 
        pdf_path: Path,
        use_ocr: bool = True,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        전체 PDF 처리
        
        Args:
            pdf_path: PDF 파일 경로
            use_ocr: OCR 사용 여부
            max_pages: 최대 처리 페이지 (None이면 전체)
        
        Returns:
            페이지 데이터 리스트
        """
        page_count = self.get_page_count(pdf_path)
        
        if max_pages:
            page_count = min(page_count, max_pages)
        
        logger.info(f"총 {page_count}페이지 처리 시작")
        
        results = []
        
        for page_num in range(1, page_count + 1):
            try:
                page_data = self.process_page(pdf_path, page_num, use_ocr)
                results.append(page_data)
            except Exception as e:
                logger.error(f"페이지 {page_num} 처리 실패: {e}")
                # 실패해도 계속 진행
                results.append({
                    'page_num': page_num,
                    'error': str(e)
                })
        
        logger.info(f"PDF 처리 완료: {len(results)}페이지")
        
        return results


# 테스트용
if __name__ == '__main__':
    processor = PDFProcessor()
    
    # 샘플 PDF 처리
    pdf_path = Path('sample.pdf')
    
    if pdf_path.exists():
        results = processor.process_pdf(pdf_path, max_pages=3)
        
        for result in results:
            if 'error' not in result:
                print(f"Page {result['page_num']}: {len(result['ocr_text'])}자 추출")
                print(f"  Element: {result['element_type']['element_type']}")
            else:
                print(f"Page {result['page_num']}: 실패 - {result['error']}")
    else:
        print(f"파일 없음: {pdf_path}")
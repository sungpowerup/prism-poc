"""
PDF Processor with OCR Integration
PDF 파싱, Element 추출 및 OCR 텍스트 추출
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import io
import base64

from PIL import Image
import numpy as np
from pypdf import PdfReader
from pdf2image import convert_from_path
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서 처리기 (OCR 통합)"""
    
    def __init__(self):
        """초기화"""
        logger.info("PDFProcessor 초기화 중...")
        
        # OCR 엔진 초기화
        try:
            logger.info("PaddleOCR 초기화 중...")
            self.ocr = PaddleOCR(
                lang='korean',
                use_gpu=False,  # RTX 3050 4GB는 부족하므로 CPU 사용
                use_angle_cls=True,
                det_db_thresh=0.3
                # show_log는 PaddleOCR 3.2.0에서 제거됨
            )
            logger.info("PaddleOCR 초기화 완료 (CPU 모드)")
        except Exception as e:
            logger.warning(f"OCR 초기화 실패: {e}")
            self.ocr = None
    
    def _extract_text_with_ocr(self, image: Image.Image) -> str:
        """
        OCR로 텍스트 추출
        
        Args:
            image: PIL Image 객체
            
        Returns:
            추출된 텍스트
        """
        if self.ocr is None:
            logger.warning("⚠️ OCR 엔진이 초기화되지 않음")
            return ""
        
        try:
            # PIL Image를 numpy array로 변환
            img_array = np.array(image)
            
            # OCR 실행
            result = self.ocr.ocr(img_array)
            
            if not result or not result[0]:
                return ""
            
            # 텍스트 추출 (신뢰도 50% 이상만)
            texts = []
            for line in result[0]:
                if len(line) >= 2:
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    if confidence > 0.5:
                        texts.append(text)
            
            # 연속된 빈 줄 제거
            extracted = "\n".join(texts)
            import re
            extracted = re.sub(r'\n{3,}', '\n\n', extracted)
            
            logger.debug(f"📝 OCR 추출: {len(texts)}줄, {len(extracted)}자")
            
            return extracted.strip()
            
        except Exception as e:
            logger.error(f"❌ OCR 처리 오류: {e}")
            return ""
    
    def _calculate_ocr_confidence(self, image: Image.Image) -> float:
        """
        OCR 신뢰도 계산
        
        Args:
            image: PIL Image 객체
            
        Returns:
            평균 신뢰도 (0.0 ~ 1.0)
        """
        if self.ocr is None:
            return 0.0
        
        try:
            img_array = np.array(image)
            result = self.ocr.ocr(img_array)
            
            if not result or not result[0]:
                return 0.0
            
            confidences = []
            for line in result[0]:
                if len(line) >= 2:
                    conf = line[1][1]
                    confidences.append(conf)
            
            if not confidences:
                return 0.0
            
            return sum(confidences) / len(confidences)
            
        except Exception as e:
            logger.error(f"❌ 신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_page_count(self, pdf_path: Path) -> int:
        """
        PDF 페이지 수 확인
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            페이지 수
        """
        try:
            reader = PdfReader(str(pdf_path))
            return len(reader.pages)
        except Exception as e:
            logger.error(f"❌ PDF 페이지 수 확인 실패: {e}")
            raise
    
    def extract_page_as_image(self, pdf_path: Path, page_num: int) -> Image.Image:
        """
        PDF 페이지를 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호 (1-based)
            
        Returns:
            PIL Image 객체
        """
        try:
            # pdf2image로 변환 (300 DPI)
            images = convert_from_path(
                str(pdf_path),
                first_page=page_num,
                last_page=page_num,
                dpi=300
            )
            
            if not images:
                raise ValueError(f"페이지 {page_num} 변환 실패")
            
            return images[0]
            
        except Exception as e:
            logger.error(f"❌ 페이지 {page_num} 이미지 변환 실패: {e}")
            raise
    
    def process_page(
        self, 
        pdf_path: Path, 
        page_num: int,
        use_ocr: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 페이지 처리 (이미지 + OCR)
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호 (1-based)
            use_ocr: OCR 사용 여부
            
        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"📄 Page {page_num} 처리 시작...")
        
        try:
            # 1) 페이지를 이미지로 변환
            image = self.extract_page_as_image(pdf_path, page_num)
            
            # 2) OCR 텍스트 추출
            extracted_text = ""
            ocr_confidence = 0.0
            
            if use_ocr and self.ocr:
                logger.info(f"📝 Page {page_num}: OCR 텍스트 추출 중...")
                extracted_text = self._extract_text_with_ocr(image)
                ocr_confidence = self._calculate_ocr_confidence(image)
                logger.info(f"✅ Page {page_num}: OCR 완료 ({len(extracted_text)} chars, conf: {ocr_confidence:.2f})")
            
            # 3) 이미지를 Base64로 인코딩 (VLM 전송용)
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            result = {
                'page_number': page_num,
                'image': image,
                'image_base64': image_base64,
                'extracted_text': extracted_text,
                'ocr_confidence': ocr_confidence,
                'width': image.width,
                'height': image.height,
                'format': image.format or 'PNG'
            }
            
            logger.info(f"✅ Page {page_num} 처리 완료")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Page {page_num} 처리 실패: {e}")
            raise
    
    def process_document(
        self, 
        pdf_path: Path,
        use_ocr: bool = True
    ) -> List[Dict[str, Any]]:
        """
        전체 PDF 문서 처리
        
        Args:
            pdf_path: PDF 파일 경로
            use_ocr: OCR 사용 여부
            
        Returns:
            페이지별 처리 결과 리스트
        """
        try:
            # 페이지 수 확인
            page_count = self.get_page_count(pdf_path)
            logger.info(f"📄 총 {page_count}페이지 처리 시작")
            
            results = []
            
            for page_num in range(1, page_count + 1):
                try:
                    result = self.process_page(pdf_path, page_num, use_ocr)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Page {page_num} 처리 실패: {e}")
                    # 실패한 페이지는 건너뛰고 계속 진행
                    results.append({
                        'page_number': page_num,
                        'error': str(e),
                        'extracted_text': '',
                        'ocr_confidence': 0.0
                    })
            
            logger.info(f"✅ 문서 처리 완료: {len(results)}/{page_count} 페이지")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 문서 처리 실패: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """프로세서 통계 정보"""
        return {
            'processor': 'PDFProcessor',
            'ocr_engine': 'PaddleOCR' if self.ocr else 'None',
            'ocr_language': 'korean',
            'ocr_mode': 'CPU',
            'supported_formats': ['PDF']
        }
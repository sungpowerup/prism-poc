"""
PRISM Phase 3.1 - OCR Text Extractor

✅ 기능:
1. 전체 페이지 텍스트 추출 (pytesseract)
2. 섹션 헤더 자동 감지
3. 텍스트 영역 Layout 분석
4. VLM과 통합 가능한 구조

Author: 박준호 (AI/ML Lead)
Date: 2025-10-22
Version: 3.1
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging
import re

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("⚠️  pytesseract not installed. OCR 기능 제한됨.")

logger = logging.getLogger(__name__)


class OCRTextExtractor:
    """
    OCR 기반 텍스트 추출기
    
    기능:
    - 전체 페이지 텍스트 추출
    - 섹션 헤더 감지
    - 텍스트 영역 레이아웃 분석
    """
    
    def __init__(self, lang: str = 'kor+eng'):
        """
        초기화
        
        Args:
            lang: OCR 언어 (기본: 한국어+영어)
        """
        self.lang = lang
        self.available = PYTESSERACT_AVAILABLE
        
        # 섹션 헤더 패턴
        self.section_patterns = [
            r'^\d{1,2}\s+.+',  # "06 응답자 특성"
            r'^[☉○◎●◉⊙]\s+.+',  # "☉ 응답자 성별"
            r'^[가-힣]{2,10}\s*특성',  # "응답자 특성"
            r'^Chapter\s+\d+',  # "Chapter 1"
            r'^제\s*\d+\s*[장절]',  # "제 1 장"
        ]
        
        # 텍스트 영역 파라미터
        self.text_region_params = {
            'min_height': 30,
            'max_height': 200,
            'min_width': 200,
            'text_density_threshold': 0.01
        }
        
        if self.available:
            logger.info("✅ OCRTextExtractor 초기화 완료")
        else:
            logger.warning("⚠️ OCRTextExtractor 제한 모드 (pytesseract 없음)")
    
    def extract_full_text(self, image: np.ndarray) -> Dict:
        """
        전체 페이지 텍스트 추출
        
        Args:
            image: 페이지 이미지 (numpy array)
            
        Returns:
            {
                'full_text': str,
                'lines': List[str],
                'blocks': List[Dict],
                'confidence': float
            }
        """
        if not self.available:
            return self._mock_extraction(image)
        
        # 전처리
        processed = self._preprocess_for_ocr(image)
        
        # OCR 실행 (상세 정보 포함)
        data = pytesseract.image_to_data(
            processed,
            lang=self.lang,
            output_type=pytesseract.Output.DICT
        )
        
        # 텍스트 블록 구성
        blocks = []
        current_block = []
        current_block_num = -1
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            if conf < 30 or not text:  # 신뢰도 낮은 것 제외
                continue
            
            block_num = data['block_num'][i]
            
            if block_num != current_block_num:
                if current_block:
                    blocks.append({
                        'text': ' '.join(current_block),
                        'bbox': self._get_block_bbox(data, current_block_num),
                        'type': 'text_block'
                    })
                current_block = [text]
                current_block_num = block_num
            else:
                current_block.append(text)
        
        # 마지막 블록 추가
        if current_block:
            blocks.append({
                'text': ' '.join(current_block),
                'bbox': self._get_block_bbox(data, current_block_num),
                'type': 'text_block'
            })
        
        # 전체 텍스트
        full_text = '\n'.join([block['text'] for block in blocks])
        
        # 라인별 분리
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # 평균 신뢰도
        confidences = [int(c) for c in data['conf'] if int(c) >= 0]
        avg_confidence = np.mean(confidences) if confidences else 0
        
        return {
            'full_text': full_text,
            'lines': lines,
            'blocks': blocks,
            'confidence': float(avg_confidence)
        }
    
    def extract_section_titles(self, image: np.ndarray) -> List[Dict]:
        """
        섹션 헤더 자동 감지
        
        Args:
            image: 페이지 이미지
            
        Returns:
            [
                {
                    'title': '06 응답자 특성',
                    'bbox': [x, y, w, h],
                    'level': 1,
                    'confidence': 0.95
                },
                ...
            ]
        """
        if not self.available:
            return []
        
        # 전체 텍스트 추출
        ocr_result = self.extract_full_text(image)
        
        section_titles = []
        
        for i, line in enumerate(ocr_result['lines']):
            # 섹션 패턴 매칭
            for pattern in self.section_patterns:
                if re.match(pattern, line):
                    # 레벨 추정
                    level = self._estimate_section_level(line)
                    
                    section_titles.append({
                        'title': line,
                        'bbox': self._estimate_line_bbox(ocr_result['blocks'], i),
                        'level': level,
                        'confidence': 0.85,
                        'type': 'section_header'
                    })
                    break
        
        return section_titles
    
    def extract_text_regions(self, image: np.ndarray) -> List[Dict]:
        """
        텍스트 영역 레이아웃 분석
        
        Args:
            image: 페이지 이미지
            
        Returns:
            텍스트 영역 리스트 (bbox 포함)
        """
        if not self.available:
            return []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 이진화
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 수평 확장 (텍스트 라인 연결)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 크기 필터링
            if h < self.text_region_params['min_height'] or \
               h > self.text_region_params['max_height'] or \
               w < self.text_region_params['min_width']:
                continue
            
            # 텍스트 밀도 체크
            roi = binary[y:y+h, x:x+w]
            text_density = np.sum(roi) / (w * h * 255)
            
            if text_density < self.text_region_params['text_density_threshold']:
                continue
            
            # OCR 실행
            roi_image = image[y:y+h, x:x+w]
            text = pytesseract.image_to_string(roi_image, lang=self.lang).strip()
            
            if len(text) > 5:  # 최소 5자 이상
                text_regions.append({
                    'type': 'text_region',
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'text': text,
                    'confidence': 0.80
                })
        
        return text_regions
    
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """OCR 전처리"""
        # Grayscale 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 노이즈 제거
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 이진화
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _get_block_bbox(self, data: Dict, block_num: int) -> List[int]:
        """OCR 블록의 Bounding Box 계산"""
        xs, ys, ws, hs = [], [], [], []
        
        for i in range(len(data['block_num'])):
            if data['block_num'][i] == block_num:
                xs.append(data['left'][i])
                ys.append(data['top'][i])
                ws.append(data['width'][i])
                hs.append(data['height'][i])
        
        if not xs:
            return [0, 0, 0, 0]
        
        min_x = min(xs)
        min_y = min(ys)
        max_x = max([x + w for x, w in zip(xs, ws)])
        max_y = max([y + h for y, h in zip(ys, hs)])
        
        return [min_x, min_y, max_x - min_x, max_y - min_y]
    
    def _estimate_section_level(self, line: str) -> int:
        """섹션 레벨 추정"""
        # 숫자로 시작하면 Level 1
        if re.match(r'^\d{1,2}\s+', line):
            return 1
        
        # 특수 기호로 시작하면 Level 2
        if re.match(r'^[☉○◎●◉⊙]\s+', line):
            return 2
        
        # 기타는 Level 3
        return 3
    
    def _estimate_line_bbox(self, blocks: List[Dict], line_idx: int) -> List[int]:
        """라인의 Bounding Box 추정"""
        if line_idx < len(blocks):
            return blocks[line_idx].get('bbox', [0, 0, 0, 0])
        return [0, 0, 0, 0]
    
    def _mock_extraction(self, image: np.ndarray) -> Dict:
        """pytesseract 없을 때 Mock 결과"""
        logger.warning("⚠️ pytesseract 없음. Mock 모드 실행.")
        
        return {
            'full_text': '[OCR 불가 - pytesseract 설치 필요]',
            'lines': [],
            'blocks': [],
            'confidence': 0.0
        }


# ⭐ Phase 3.1 통합 클래스
class Phase31LayoutDetector:
    """
    Phase 3.1 통합 Layout Detector
    
    CV + OCR 하이브리드
    """
    
    def __init__(self):
        """초기화"""
        from layout_detector_phase31 import LayoutDetector as CVLayoutDetector
        
        self.cv_detector = CVLayoutDetector()
        self.ocr_extractor = OCRTextExtractor()
        
        logger.info("✅ Phase 3.1 통합 초기화 완료 (CV + OCR)")
    
    def detect_all_regions(self, image: np.ndarray, page_num: int = 0) -> Dict:
        """
        모든 영역 감지 (CV + OCR)
        
        Returns:
            {
                'cv_regions': List[Dict],  # CV 감지 (차트, 표, 지도)
                'text_regions': List[Dict],  # OCR 텍스트 영역
                'section_titles': List[Dict],  # 섹션 헤더
                'full_text': str  # 전체 텍스트
            }
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Phase 3.1 통합 감지 (페이지 {page_num + 1})")
        logger.info(f"{'='*60}\n")
        
        # 1. CV 기반 영역 감지
        logger.info("Stage 1: CV 기반 Layout Detection")
        cv_regions = self.cv_detector.detect_regions(image, page_num)
        logger.info(f"   → {len(cv_regions)}개 CV 영역 감지\n")
        
        # 2. OCR 텍스트 추출
        logger.info("Stage 2: OCR 텍스트 추출")
        ocr_result = self.ocr_extractor.extract_full_text(image)
        logger.info(f"   → {len(ocr_result['lines'])}줄 텍스트 추출")
        logger.info(f"   → 신뢰도: {ocr_result['confidence']:.1f}%\n")
        
        # 3. 섹션 헤더 감지
        logger.info("Stage 3: 섹션 헤더 감지")
        section_titles = self.ocr_extractor.extract_section_titles(image)
        logger.info(f"   → {len(section_titles)}개 섹션 헤더 감지\n")
        
        # 4. 텍스트 영역 레이아웃
        logger.info("Stage 4: 텍스트 영역 레이아웃")
        text_regions = self.ocr_extractor.extract_text_regions(image)
        logger.info(f"   → {len(text_regions)}개 텍스트 영역 감지\n")
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ 총 감지: CV {len(cv_regions)}개 + OCR {len(text_regions)}개")
        logger.info(f"{'='*60}\n")
        
        return {
            'cv_regions': cv_regions,
            'text_regions': text_regions,
            'section_titles': section_titles,
            'full_text': ocr_result['full_text'],
            'ocr_lines': ocr_result['lines'],
            'ocr_confidence': ocr_result['confidence']
        }
"""
core/quick_layout_analyzer.py
PRISM Phase 5.5.0 - Quick Layout Analyzer

✅ Phase 5.5.0 핵심 개선 (GPT 보강 반영):
- OCR 텍스트 반환 (ocr_text)
- 조항 토큰 비율 계산 (article_token_ratio)
- 번호 목록 밀도 계산 (numbered_list_density)
- 격자 밀도 계산 (h_v_line_density)
- 교차점 개수 반환 (grid_intersections)

(Phase 5.4.0 기능 유지)
- 버스 키워드 검출
- 지도 검출 민감도 강화
- 표 검출 2단 검증

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.5.0
"""

import cv2
import numpy as np
import logging
import base64
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Tesseract 선택적 import
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("⚠️ pytesseract 없음 - OCR 기능 비활성화")


class QuickLayoutAnalyzer:
    """
    Phase 5.5.0 OpenCV + OCR 기반 빠른 레이아웃 분석기
    
    목적:
    - VLM 호출 전 0.5초 이내 구조 힌트 생성
    - 프롬프트 최적화 및 검증 기준 제공
    - 표 과검출 방지 (가감형 confidence)
    
    힌트:
    - has_text: 텍스트 영역 존재
    - has_map: 지도/노선도 존재
    - has_table: 표 존재
    - has_numbers: 숫자 데이터 존재
    - diagram_count: 다이어그램 개수
    - grid_intersections: 교차점 개수 (표 신뢰도)
    - h_v_line_density: 가로/세로선 밀도 (표 신뢰도)
    - ocr_text: OCR 추출 텍스트 (짧게)
    - article_token_ratio: 조항 토큰 비율 (규정 모드 감지)
    - numbered_list_density: 번호 목록 밀도 (규정 모드 감지)
    - bus_keywords: 버스 키워드 리스트
    """
    
    def __init__(self):
        """초기화"""
        self.tesseract_available = TESSERACT_AVAILABLE
        logger.info("✅ QuickLayoutAnalyzer v5.5.0 초기화 완료")
        if self.tesseract_available:
            logger.info("   📊 Tesseract OCR 활성화 (표 + 버스 + 규정 키워드)")
        else:
            logger.warning("   ⚠️ Tesseract OCR 비활성화 (일부 기능 제한)")
    
    def analyze(self, image_data: str) -> Dict[str, Any]:
        """
        이미지 구조 분석 (0.5초 이내)
        
        Args:
            image_data: Base64 인코딩된 이미지
        
        Returns:
            {
                'has_text': bool,
                'has_map': bool,
                'has_table': bool,
                'has_numbers': bool,
                'diagram_count': int,
                'grid_intersections': int,
                'h_v_line_density': float,
                'ocr_text': str,
                'article_token_ratio': float,
                'numbered_list_density': float,
                'bus_keywords': List[str]
            }
        """
        logger.info("   🔍 QuickLayoutAnalyzer v5.5.0 시작")
        
        # Base64 → OpenCV 이미지
        image = self._base64_to_cv2(image_data)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # OCR 텍스트 추출 (핵심!)
        ocr_text = self._extract_ocr_text(gray) if self.tesseract_available else ""
        
        # 구조 감지
        hints = {
            'has_text': self._detect_text(image),
            'has_map': self._detect_map(image),
            'has_table': self._detect_tables(image, image_data),
            'has_numbers': self._detect_numbers(image),
            'diagram_count': self._count_diagrams(image),
            
            # ✅ Phase 5.5.0: 표 신뢰도 계산용 필드
            'grid_intersections': self._count_grid_intersections(gray),
            'h_v_line_density': self._calculate_line_density(gray),
            
            # ✅ Phase 5.5.0: OCR 기반 필드
            'ocr_text': ocr_text[:500],  # 짧게 (500자)
            'article_token_ratio': self._calculate_article_ratio(ocr_text),
            'numbered_list_density': self._calculate_numbered_density(ocr_text),
            
            # ✅ Phase 5.4.0: 버스 키워드
            'bus_keywords': self._detect_bus_keywords(ocr_text)
        }
        
        logger.info(f"   ✅ 힌트 생성 완료:")
        logger.info(f"      - 텍스트: {hints['has_text']}, 지도: {hints['has_map']}, 표: {hints['has_table']}")
        logger.info(f"      - 교차점: {hints['grid_intersections']}, 선밀도: {hints['h_v_line_density']:.4f}")
        logger.info(f"      - 조항비율: {hints['article_token_ratio']:.2f}, 번호밀도: {hints['numbered_list_density']:.2f}")
        if hints['bus_keywords']:
            logger.info(f"      - 버스 키워드: {hints['bus_keywords']}")
        
        return hints
    
    def _base64_to_cv2(self, image_data: str) -> np.ndarray:
        """Base64 → OpenCV 이미지 변환"""
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image
    
    def _extract_ocr_text(self, gray: np.ndarray) -> str:
        """
        ✅ Phase 5.5.0: OCR 텍스트 추출
        
        Args:
            gray: Grayscale 이미지
        
        Returns:
            OCR 추출 텍스트 (최대 1000자)
        """
        if not self.tesseract_available:
            return ""
        
        try:
            # Tesseract 실행 (한글 + 영어)
            text = pytesseract.image_to_string(gray, lang='kor+eng')
            
            # 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            
            logger.debug(f"      OCR 텍스트: {len(text)}자 추출")
            return text[:1000]  # 최대 1000자
        
        except Exception as e:
            logger.debug(f"      OCR 실패: {e}")
            return ""
    
    def _calculate_article_ratio(self, ocr_text: str) -> float:
        """
        ✅ Phase 5.5.0: 조항 토큰 비율 계산
        
        목적: 규정/법령 문서 감지 + 표 과검출 방지
        
        Args:
            ocr_text: OCR 텍스트
        
        Returns:
            조항 토큰 비율 (0.0 ~ 1.0)
        """
        if not ocr_text:
            return 0.0
        
        # 조항 패턴 검색
        patterns = [
            r'제\s?\d+조',
            r'제\s?\d+항',
            r'제\s?\d+호',
            r'\(\d+\)',
            r'①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩',
            r'^\d+\.',
        ]
        
        # 매칭된 토큰 개수
        matches = sum(len(re.findall(p, ocr_text, re.MULTILINE)) for p in patterns)
        
        # 전체 토큰 개수 (공백 기준)
        total_tokens = len(ocr_text.split())
        
        if total_tokens == 0:
            return 0.0
        
        # 비율 계산 (0.0 ~ 1.0)
        ratio = min(1.0, matches / max(1, total_tokens))
        
        logger.debug(f"      조항 토큰: {matches}/{total_tokens} = {ratio:.2f}")
        return ratio
    
    def _calculate_numbered_density(self, ocr_text: str) -> float:
        """
        ✅ Phase 5.5.0: 번호 목록 밀도 계산
        
        목적: 규정/법령 문서 감지 + 표 과검출 방지
        
        Args:
            ocr_text: OCR 텍스트
        
        Returns:
            번호 목록 밀도 (0.0 ~ 1.0)
        """
        if not ocr_text:
            return 0.0
        
        lines = ocr_text.split('\n')
        if len(lines) == 0:
            return 0.0
        
        # 번호 목록 패턴 (줄 시작)
        patterns = [
            r'^\s*\d+\.',
            r'^\s*\d+\)',
            r'^\s*[①-⑳]',
            r'^\s*\(\d+\)',
        ]
        
        # 매칭된 줄 개수
        numbered_lines = sum(
            1 for line in lines
            if any(re.match(p, line) for p in patterns)
        )
        
        # 밀도 계산
        density = numbered_lines / max(1, len(lines))
        
        logger.debug(f"      번호 목록: {numbered_lines}/{len(lines)} 줄 = {density:.2f}")
        return density
    
    def _count_grid_intersections(self, gray: np.ndarray) -> int:
        """
        ✅ Phase 5.5.0: 격자 교차점 개수 계산
        
        Args:
            gray: Grayscale 이미지
        
        Returns:
            교차점 개수
        """
        # Canny 엣지 검출
        edges = cv2.Canny(gray, 30, 100)
        
        # 가로선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 세로선 검출
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # 교차점 검출
        intersections = cv2.bitwise_and(horizontal_lines, vertical_lines)
        intersections_count = np.sum(intersections > 0)
        
        logger.debug(f"      격자 교차점: {intersections_count}개")
        return int(intersections_count)
    
    def _calculate_line_density(self, gray: np.ndarray) -> float:
        """
        ✅ Phase 5.5.0: 가로/세로선 밀도 계산
        
        Args:
            gray: Grayscale 이미지
        
        Returns:
            선 밀도 (0.0 ~ 1.0)
        """
        # Canny 엣지 검출
        edges = cv2.Canny(gray, 30, 100)
        
        # 가로선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 세로선 검출
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # 선 픽셀 합계
        h_pixels = np.sum(horizontal_lines > 0)
        v_pixels = np.sum(vertical_lines > 0)
        
        # 전체 픽셀
        total_pixels = gray.shape[0] * gray.shape[1]
        
        # 밀도 계산
        density = (h_pixels + v_pixels) / max(1, total_pixels)
        
        logger.debug(f"      선 밀도: {density:.6f}")
        return float(density)
    
    def _detect_text(self, image: np.ndarray) -> bool:
        """텍스트 영역 검출"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        h_ratio = np.sum(horizontal_lines > 0) / horizontal_lines.size
        has_text = h_ratio > 0.01
        logger.debug(f"      텍스트 영역: {has_text} (가로선 비율: {h_ratio:.4f})")
        return has_text
    
    def _detect_map(self, image: np.ndarray) -> bool:
        """지도/노선도 검출"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray)
        
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        large_contours = sum(1 for c in contours if cv2.contourArea(c) > 1000)
        
        total_area = image.shape[0] * image.shape[1]
        contour_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 1000)
        area_ratio = contour_area / total_area if total_area > 0 else 0
        
        has_map = std_dev > 60 and large_contours > 10 and area_ratio > 0.3
        
        logger.debug(
            f"      지도/노선도: {has_map} "
            f"(편차: {std_dev:.1f}, 컨투어: {large_contours}, 면적비: {area_ratio:.2%})"
        )
        return has_map
    
    def _detect_tables(self, image: np.ndarray, image_data: str = None) -> bool:
        """표 검출"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        intersections = cv2.bitwise_and(horizontal_lines, vertical_lines)
        intersections_sum = np.sum(intersections > 0)
        
        has_table_cv = intersections_sum > 50
        
        has_table_text = False
        if self.tesseract_available and image_data:
            try:
                text = pytesseract.image_to_string(gray, lang='kor+eng')
                table_keywords = ['단위', '사례수', '비율', '합계', '%', '명', '원', '개']
                for keyword in table_keywords:
                    if keyword in text:
                        has_table_text = True
                        logger.debug(f"      Tesseract 표 키워드 감지: '{keyword}'")
                        break
            except Exception as e:
                logger.debug(f"      Tesseract OCR 실패: {e}")
        
        has_table = has_table_cv or has_table_text
        
        logger.debug(
            f"      표 검출: {has_table} "
            f"(CV 교차점: {intersections_sum}, Tesseract 키워드: {has_table_text})"
        )
        return has_table
    
    def _detect_numbers(self, image: np.ndarray) -> bool:
        """숫자 데이터 검출"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        small_boxes = sum(1 for c in contours if 10 < cv2.contourArea(c) < 500)
        has_numbers = small_boxes > 20
        logger.debug(f"      숫자 데이터: {has_numbers} (작은 박스: {small_boxes})")
        return has_numbers
    
    def _count_diagrams(self, image: np.ndarray) -> int:
        """다이어그램 개수 추정"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_regions = sum(1 for c in contours if cv2.contourArea(c) > 5000)
        diagram_count = min(5, large_regions)
        logger.debug(f"      다이어그램: {diagram_count}개 (큰 영역: {large_regions})")
        return diagram_count
    
    def _detect_bus_keywords(self, ocr_text: str) -> List[str]:
        """버스 키워드 검출"""
        if not ocr_text:
            return []
        BUS_KEYWORDS = ['노선', '배차', '정류장', '첫차', '막차', '차고지', '버스']
        detected = [kw for kw in BUS_KEYWORDS if kw in ocr_text]
        return detected
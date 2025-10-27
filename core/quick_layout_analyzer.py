"""
core/quick_layout_analyzer.py
PRISM Phase 5.3.1 - Quick Layout Analyzer (긴급 패치)

✅ Phase 5.3.1 수정:
1. Canny threshold 완화 (50/150 → 30/100)
2. Tesseract 표 키워드 검출 추가 (2단 검증)
3. 표 검출 민감도 향상

Author: 박준호 (AI/ML Lead) + GPT 제안 반영
Date: 2025-10-27
Version: 5.3.1
"""

import cv2
import numpy as np
import logging
import base64
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Tesseract 선택적 import
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("⚠️ pytesseract 없음 - 표 키워드 검출 비활성화")


class QuickLayoutAnalyzer:
    """
    Phase 5.3.1 OpenCV 기반 빠른 레이아웃 분석기
    
    GPT 제안 반영:
    - Canny threshold 완화로 흐릿한 선 검출
    - Tesseract로 표 키워드 보조 검출 (2단 검증)
    
    목적:
    - VLM 호출 전 0.5초 이내 구조 힌트 생성
    - 프롬프트 최적화 및 검증 기준 제공
    
    힌트:
    - has_text: 텍스트 영역 존재
    - has_map: 지도/노선도 존재
    - has_table: 표 존재
    - has_numbers: 숫자 데이터 존재
    - diagram_count: 다이어그램 개수
    """
    
    def __init__(self):
        """초기화"""
        self.tesseract_available = TESSERACT_AVAILABLE
        logger.info("✅ QuickLayoutAnalyzer v5.3.1 초기화 완료")
        if self.tesseract_available:
            logger.info("   📊 Tesseract 표 키워드 검출 활성화")
    
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
                'diagram_count': int
            }
        """
        logger.info("   🔍 QuickLayoutAnalyzer 시작")
        
        # Base64 → OpenCV 이미지
        image = self._base64_to_cv2(image_data)
        
        # 구조 감지
        hints = {
            'has_text': self._detect_text(image),
            'has_map': self._detect_map(image),
            'has_table': self._detect_tables(image, image_data),  # ✅ image_data 추가
            'has_numbers': self._detect_numbers(image),
            'diagram_count': self._count_diagrams(image)
        }
        
        logger.info(f"   ✅ 힌트: {hints}")
        return hints
    
    def _base64_to_cv2(self, image_data: str) -> np.ndarray:
        """Base64 → OpenCV 이미지 변환"""
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image
    
    def _detect_text(self, image: np.ndarray) -> bool:
        """
        텍스트 영역 검출
        
        전략: 가로 선이 많으면 텍스트
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 가로 선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 가로 선 픽셀 비율
        h_ratio = np.sum(horizontal_lines > 0) / horizontal_lines.size
        
        has_text = h_ratio > 0.01
        logger.debug(f"      텍스트 영역: {has_text} (가로선 비율: {h_ratio:.4f})")
        return has_text
    
    def _detect_map(self, image: np.ndarray) -> bool:
        """
        지도/노선도 검출
        
        전략: 색상 다양성 + 곡선
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 색상 다양성 (표준편차)
        std_dev = np.std(gray)
        
        # 곡선 검출 (Canny + Contour)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 큰 컨투어 개수
        large_contours = sum(1 for c in contours if cv2.contourArea(c) > 1000)
        
        has_map = std_dev > 40 and large_contours > 5
        logger.debug(f"      지도/노선도: {has_map} (편차: {std_dev:.1f}, 컨투어: {large_contours})")
        return has_map
    
    def _detect_tables(self, image: np.ndarray, image_data: str = None) -> bool:
        """
        ✅ Phase 5.3.1: 표 검출 강화 (GPT 제안)
        
        전략:
        1. OpenCV Canny threshold 완화 (30/100)
        2. Tesseract 표 키워드 보조 검출 (2단 검증)
        
        Args:
            image: OpenCV 이미지
            image_data: Base64 이미지 (Tesseract용, 선택)
        
        Returns:
            표 존재 여부
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ✅ 1. Canny threshold 완화 (흐릿한 선 검출)
        edges = cv2.Canny(gray, 30, 100)  # 기존: 50, 150
        
        # 가로선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 세로선 검출
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # 교차점 검출
        intersections = cv2.bitwise_and(horizontal_lines, vertical_lines)
        intersections_sum = np.sum(intersections > 0)
        
        # OpenCV 기반 표 검출
        has_table_cv = intersections_sum > 50
        
        # ✅ 2. Tesseract 표 키워드 검출 (보조)
        has_table_text = False
        if self.tesseract_available and image_data:
            try:
                # OCR 실행
                text = pytesseract.image_to_string(gray, lang='kor+eng')
                
                # 표 키워드 검사
                table_keywords = ['단위', '사례수', '비율', '합계', '%', '명', '원', '개']
                for keyword in table_keywords:
                    if keyword in text:
                        has_table_text = True
                        logger.debug(f"      Tesseract 표 키워드 감지: '{keyword}'")
                        break
            
            except Exception as e:
                logger.debug(f"      Tesseract OCR 실패: {e}")
        
        # 2단 검증: OpenCV 또는 Tesseract 중 하나라도 통과
        has_table = has_table_cv or has_table_text
        
        logger.debug(
            f"      표 검출: {has_table} "
            f"(CV 교차점: {intersections_sum}, "
            f"Tesseract 키워드: {has_table_text})"
        )
        return has_table
    
    def _detect_numbers(self, image: np.ndarray) -> bool:
        """
        숫자 데이터 검출
        
        전략: 작은 텍스트 박스가 많으면 숫자
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 이진화
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 컨투어 검출
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 작은 박스 (숫자) 개수
        small_boxes = sum(1 for c in contours if 10 < cv2.contourArea(c) < 500)
        
        has_numbers = small_boxes > 20
        logger.debug(f"      숫자 데이터: {has_numbers} (작은 박스: {small_boxes})")
        return has_numbers
    
    def _count_diagrams(self, image: np.ndarray) -> int:
        """
        다이어그램 개수 추정
        
        전략: 큰 연결 영역 개수
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 컨투어 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 큰 영역만 카운트 (면적 > 5000)
        large_regions = sum(1 for c in contours if cv2.contourArea(c) > 5000)
        
        # 다이어그램 개수 추정 (최대 5개)
        diagram_count = min(5, large_regions)
        
        logger.debug(f"      다이어그램: {diagram_count}개 (큰 영역: {large_regions})")
        return diagram_count


# 테스트 코드
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python quick_layout_analyzer.py <base64_image>")
        sys.exit(1)
    
    analyzer = QuickLayoutAnalyzer()
    image_data = sys.argv[1]
    
    hints = analyzer.analyze(image_data)
    
    print("=== QuickLayoutAnalyzer 결과 ===")
    for key, value in hints.items():
        print(f"{key}: {value}")
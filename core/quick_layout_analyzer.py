"""
core/quick_layout_analyzer.py
PRISM Phase 5.3.0 - Quick Layout Analyzer

목적: OpenCV로 0.5초 이내에 문서 구조 힌트 제공
GPT 제안 반영: MVP 버전 - has_numbers와 diagram_count 우선 구현
"""

import cv2
import numpy as np
from PIL import Image
import base64
import io
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QuickLayoutAnalyzer:
    """
    경량 CV 기반 레이아웃 힌트 생성기
    
    Phase 5.3.0 MVP 전략:
    - has_numbers와 diagram_count 우선 정확도 (GPT 제안)
    - 나머지는 보수적 추정 (False Positive 최소화)
    - 0.5초 이내 처리 목표
    """
    
    def __init__(self):
        self.min_text_area = 1000
        self.min_diagram_area = 5000
        self.max_diagram_area = 100000
        
        # Tesseract 사용 가능 여부 체크
        self.tesseract_available = self._check_tesseract()
        
        logger.info(f"✅ QuickLayoutAnalyzer 초기화 (Tesseract: {'사용 가능' if self.tesseract_available else '미설치'})")
    
    def _check_tesseract(self) -> bool:
        """Tesseract 사용 가능 여부 확인"""
        try:
            import pytesseract
            # 간단한 테스트
            pytesseract.get_tesseract_version()
            return True
        except:
            logger.warning("⚠️ Tesseract 미설치 - 숫자 검출 기능 제한")
            return False
    
    def analyze(self, image_data: str) -> Dict:
        """
        빠른 레이아웃 분석
        
        Args:
            image_data: Base64 인코딩된 이미지
            
        Returns:
            hints: {
                'has_text': bool,
                'has_table': bool,
                'has_map': bool,
                'diagram_count': int,  # MVP 우선
                'has_numbers': bool,   # MVP 우선
                'layout_complexity': str
            }
        """
        logger.info("🔍 Quick CV 분석 시작 (Phase 5.3.0 MVP)")
        
        try:
            # Base64 → numpy array
            image = self._decode_image(image_data)
            
            # MVP 우선: has_numbers와 diagram_count
            hints = {
                'has_numbers': self._detect_numbers(image),
                'diagram_count': self._count_diagrams(image),
                'has_text': self._detect_text_regions(image),
                'has_table': self._detect_tables(image),
                'has_map': self._detect_map(image),
                'layout_complexity': self._assess_complexity(image)
            }
            
            logger.info(f"✅ CV 분석 완료: numbers={hints['has_numbers']}, diagrams={hints['diagram_count']}")
            return hints
            
        except Exception as e:
            logger.error(f"❌ CV 분석 실패: {e}")
            # Fallback: 안전한 기본값
            return {
                'has_text': True,
                'has_table': False,
                'has_map': False,
                'diagram_count': 0,
                'has_numbers': True,  # 보수적으로 True
                'layout_complexity': 'medium'
            }
    
    def _decode_image(self, image_data: str) -> np.ndarray:
        """Base64 → OpenCV 이미지"""
        try:
            # Base64 디코딩
            img_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(img_bytes))
            
            # PIL → OpenCV (RGB → BGR)
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"이미지 디코딩 실패: {e}")
            raise
    
    def _detect_numbers(self, image: np.ndarray) -> bool:
        """
        숫자 밀집 영역 검출 (MVP 우선 - GPT 제안)
        
        원리:
        1. Tesseract로 숫자 스캔 (가능 시)
        2. 패턴 매칭 (시간, 금액 등)
        """
        if not self.tesseract_available:
            # Tesseract 없으면 보수적으로 True (VLM이 판단)
            logger.debug("   Tesseract 없음 → 숫자 검출 True (기본값)")
            return True
        
        try:
            import pytesseract
            
            # 이미지 전처리 (숫자 인식 향상)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # 숫자 + 콜론 + 단위만 인식 (GPT 제안: kor+eng)
            try:
                text = pytesseract.image_to_string(
                    binary,
                    lang='kor+eng',  # 한글 + 영문
                    config='--psm 6 -c tessedit_char_whitelist=0123456789:분원%명대초시간'
                )
            except Exception as e:
                # kor+eng 실패 시 eng로 Fallback
                logger.warning(f"   Tesseract kor+eng 실패, eng로 Fallback: {e}")
                text = pytesseract.image_to_string(
                    binary,
                    lang='eng',
                    config='--psm 6 -c tessedit_char_whitelist=0123456789:분원%명대초시간'
                )
            
            # 시간 패턴 (XX:XX)
            colon_count = text.count(':')
            
            # 단위 패턴
            units = ['분', '원', '%', '명', '대', '초']
            unit_count = sum(text.count(u) for u in units)
            
            has_numbers = colon_count >= 2 or unit_count >= 3
            
            logger.debug(f"   숫자 검출: {has_numbers} (콜론: {colon_count}, 단위: {unit_count})")
            return has_numbers
            
        except Exception as e:
            logger.warning(f"   Tesseract 실패: {e}")
            return True  # 실패 시 보수적으로 True
    
    def _count_diagrams(self, image: np.ndarray) -> int:
        """
        다이어그램 개수 추정 (MVP 우선 - GPT 제안)
        
        원리: 닫힌 중간 크기 영역 카운트
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge 검출
        edges = cv2.Canny(gray, 50, 150)
        
        # 닫힌 영역 강조
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Contour 찾기
        contours, _ = cv2.findContours(
            closed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 적절한 크기 영역 카운트
        diagram_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if self.min_diagram_area < area < self.max_diagram_area:
                # 종횡비 체크 (너무 길쭉하면 제외)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                if 0.3 < aspect_ratio < 3.0:
                    diagram_count += 1
        
        # 최대 5개로 제한 (과다 검출 방지 - GPT 제안)
        diagram_count = min(diagram_count, 5)
        
        logger.debug(f"   다이어그램 검출: {diagram_count}개")
        return diagram_count
    
    def _detect_text_regions(self, image: np.ndarray) -> bool:
        """
        텍스트 영역 검출
        
        원리: 텍스트는 수평선이 많음
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 수평선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(
            gray,
            cv2.MORPH_OPEN,
            horizontal_kernel,
            iterations=2
        )
        
        # 흰색 픽셀 비율
        white_ratio = np.sum(detect_horizontal > 200) / detect_horizontal.size
        
        has_text = white_ratio > 0.01
        logger.debug(f"   텍스트 검출: {has_text} (비율: {white_ratio:.3f})")
        return has_text
    
    def _detect_tables(self, image: np.ndarray) -> bool:
        """
        표 검출 (격자 패턴)
        
        원리: 표는 수평선 + 수직선 교차
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 수평선 검출
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 수직선 검출
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # 교차점 = 표
        intersections = cv2.bitwise_and(h_lines, v_lines)
        intersection_count = np.sum(intersections > 0)
        
        has_table = intersection_count > 50
        logger.debug(f"   표 검출: {has_table} (교차점: {intersection_count})")
        return has_table
    
    def _detect_map(self, image: np.ndarray) -> bool:
        """
        지도 검출
        
        원리: 복잡한 곡선 + 색상 다양성
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Contour 검출
        edges = cv2.Canny(gray, 30, 100)
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 복잡한 곡선 contour 개수
        curved_contours = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area > 1000:  # 충분히 큰 영역
                arc_length = cv2.arcLength(contour, True)
                epsilon = 0.01 * arc_length
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # 복잡한 형상 (10개 이상 꼭지점)
                if len(approx) > 10:
                    curved_contours += 1
        
        # 색상 다양성 체크
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        unique_hues = len(np.unique(hsv[:, :, 0]))
        
        # GPT 제안: 보수적 기준 (False Positive 최소화)
        has_map = curved_contours > 5 and unique_hues > 30
        
        logger.debug(f"   지도 검출: {has_map} (곡선: {curved_contours}, 색상: {unique_hues})")
        return has_map
    
    def _assess_complexity(self, image: np.ndarray) -> str:
        """
        레이아웃 복잡도 평가
        
        Returns:
            'simple': 텍스트만 또는 단순 표
            'medium': 텍스트 + 표/차트
            'complex': 지도 + 다이어그램 + 텍스트
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Edge 밀도
        edge_density = np.sum(edges > 0) / edges.size
        
        # Contour 복잡도
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if edge_density < 0.05 and len(contours) < 100:
            complexity = 'simple'
        elif edge_density < 0.15 and len(contours) < 500:
            complexity = 'medium'
        else:
            complexity = 'complex'
        
        logger.debug(f"   복잡도: {complexity} (edge: {edge_density:.3f}, contours: {len(contours)})")
        return complexity

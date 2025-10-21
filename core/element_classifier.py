"""
core/element_classifier.py
Element 자동 분류 (세부 분류 추가)

개선 사항:
- 원그래프, 막대그래프, 선그래프 등 세부 분류
- 복합 차트 감지 (원그래프 + 막대그래프)
- 신뢰도 향상
"""

import cv2
import numpy as np
from typing import Dict, List
import base64
from io import BytesIO
from PIL import Image


class ElementClassifier:
    """
    CV 기반 Element 분류기
    
    분류:
    - chart: 차트 (원그래프, 막대그래프, 선그래프 등)
    - table: 표
    - diagram: 복합 다이어그램
    - text: 텍스트
    - image: 일반 이미지
    """
    
    def __init__(self, use_vlm: bool = False):
        self.use_vlm = use_vlm
        
        # 임계값
        self.CHART_AXIS_THRESHOLD = 100  # 축 선 개수
        self.TABLE_LINE_THRESHOLD = 20   # 표 선 개수
        self.CIRCLE_THRESHOLD = 3        # 원 개수 (파이 차트)
        self.BAR_THRESHOLD = 5           # 막대 개수
    
    def classify(self, image_data: str) -> Dict:
        """
        이미지 분류 (세부 타입 포함)
        
        Args:
            image_data: Base64 인코딩된 이미지
        
        Returns:
            {
                'element_type': 'chart' | 'table' | 'diagram' | 'text' | 'image',
                'subtypes': ['pie', 'bar'],  # 세부 분류
                'confidence': 0.9,
                'reasoning': '...'
            }
        """
        # Base64 → OpenCV
        img_array = self._base64_to_cv2(image_data)
        
        # 특징 추출
        features = self._extract_features(img_array)
        
        # 규칙 기반 분류
        classification = self._classify_by_rules(features)
        
        # 세부 타입 감지
        subtypes = self._detect_subtypes(img_array, classification['element_type'], features)
        classification['subtypes'] = subtypes
        
        return classification
    
    def _base64_to_cv2(self, base64_str: str) -> np.ndarray:
        """Base64 → OpenCV 이미지"""
        # data:image/png;base64, 제거
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        img_bytes = base64.b64decode(base64_str)
        img_pil = Image.open(BytesIO(img_bytes))
        img_array = np.array(img_pil)
        
        # RGB → BGR (OpenCV)
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    def _extract_features(self, img: np.ndarray) -> Dict:
        """
        이미지 특징 추출
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # 1. 선 검출 (Canny + HoughLines)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
        
        horizontal_lines = 0
        vertical_lines = 0
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                
                if angle < 10 or angle > 170:  # 수평선
                    horizontal_lines += 1
                elif 80 < angle < 100:  # 수직선
                    vertical_lines += 1
        
        # 2. 원 검출 (HoughCircles)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            dp=1, 
            minDist=50,
            param1=50, 
            param2=30, 
            minRadius=10, 
            maxRadius=200
        )
        circle_count = len(circles[0]) if circles is not None else 0
        
        # 3. 텍스트 밀도 (흑백 비율)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        text_density = np.sum(binary == 0) / binary.size
        
        # 4. 색상 다양성
        if len(img.shape) == 3:
            colors = img.reshape(-1, 3)
            unique_colors = len(np.unique(colors, axis=0))
        else:
            unique_colors = len(np.unique(gray))
        
        return {
            'horizontal_lines': horizontal_lines,
            'vertical_lines': vertical_lines,
            'circle_count': circle_count,
            'text_density': text_density,
            'unique_colors': unique_colors,
            'total_lines': horizontal_lines + vertical_lines
        }
    
    def _classify_by_rules(self, features: Dict) -> Dict:
        """
        규칙 기반 분류
        """
        h_lines = features['horizontal_lines']
        v_lines = features['vertical_lines']
        circles = features['circle_count']
        total_lines = features['total_lines']
        text_density = features['text_density']
        
        # 우선순위: table > chart > diagram > text > image
        
        # 1. 표 (Table)
        if h_lines > self.TABLE_LINE_THRESHOLD and v_lines > self.TABLE_LINE_THRESHOLD:
            return {
                'element_type': 'table',
                'confidence': 0.9,
                'reasoning': f'격자 구조 감지 (H:{h_lines}, V:{v_lines})'
            }
        
        # 2. 차트 (Chart)
        if circles >= self.CIRCLE_THRESHOLD or total_lines > self.CHART_AXIS_THRESHOLD:
            return {
                'element_type': 'chart',
                'confidence': 0.85,
                'reasoning': f'차트 요소 감지 (원:{circles}, 선:{total_lines})'
            }
        
        # 3. 다이어그램 (Diagram) - 선과 원이 적당히 있음
        if total_lines > 10 and circles > 0:
            return {
                'element_type': 'diagram',
                'confidence': 0.8,
                'reasoning': f'복합 다이어그램 (원:{circles}, 선:{total_lines})'
            }
        
        # 4. 텍스트 (Text)
        if text_density > 0.3:
            return {
                'element_type': 'text',
                'confidence': 0.85,
                'reasoning': f'텍스트 밀도 높음 ({text_density:.2f})'
            }
        
        # 5. 일반 이미지 (Image)
        return {
            'element_type': 'image',
            'confidence': 0.7,
            'reasoning': '특정 구조 없음'
        }
    
    def _detect_subtypes(self, img: np.ndarray, element_type: str, features: Dict) -> List[str]:
        """
        세부 타입 감지
        
        Returns:
            ['pie', 'bar', 'line', 'map', etc.]
        """
        subtypes = []
        
        if element_type == 'chart':
            # 원그래프 (Pie Chart)
            if features['circle_count'] >= self.CIRCLE_THRESHOLD:
                subtypes.append('pie')
            
            # 막대그래프 (Bar Chart)
            if self._detect_bars(img):
                subtypes.append('bar')
            
            # 선그래프 (Line Chart)
            if self._detect_lines(img):
                subtypes.append('line')
        
        elif element_type == 'diagram':
            # 지도
            if self._detect_map(img):
                subtypes.append('map')
            
            # 복합 다이어그램
            if features['circle_count'] > 0 and features['total_lines'] > 20:
                subtypes.append('complex')
        
        return subtypes if subtypes else ['unknown']
    
    def _detect_bars(self, img: np.ndarray) -> bool:
        """
        막대그래프 감지
        
        방법: 수직 또는 수평 사각형 패턴
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rect_count = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = h / w if w > 0 else 0
            
            # 수직 막대 (h > w * 2)
            if aspect_ratio > 2 and h > 50:
                rect_count += 1
            
            # 수평 막대 (w > h * 2)
            elif aspect_ratio < 0.5 and w > 50:
                rect_count += 1
        
        return rect_count >= self.BAR_THRESHOLD
    
    def _detect_lines(self, img: np.ndarray) -> bool:
        """
        선그래프 감지
        
        방법: 대각선 패턴 (축 제외)
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return False
        
        diagonal_count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            # 대각선 (10도 < angle < 170도, 수평/수직 제외)
            if 10 < angle < 80 or 100 < angle < 170:
                diagonal_count += 1
        
        return diagonal_count >= 3
    
    def _detect_map(self, img: np.ndarray) -> bool:
        """
        지도 감지
        
        방법: 복잡한 윤곽선 + 색상 영역
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 복잡한 윤곽선 개수
        complex_contours = 0
        for cnt in contours:
            perimeter = cv2.arcLength(cnt, True)
            area = cv2.contourArea(cnt)
            
            if area > 500 and perimeter > 200:
                complex_contours += 1
        
        return complex_contours >= 5


class BatchElementClassifier:
    """
    배치 처리 분류기
    """
    
    def __init__(self):
        self.classifier = ElementClassifier()
    
    def classify_batch(self, elements: List[Dict]) -> List[Dict]:
        """
        여러 Element를 배치로 분류
        
        Args:
            elements: [{'image_data': '...', 'bbox': {...}}, ...]
        
        Returns:
            [{'element_type': 'chart', 'subtypes': ['pie'], ...}, ...]
        """
        results = []
        for elem in elements:
            result = self.classifier.classify(elem['image_data'])
            result['bbox'] = elem.get('bbox')
            results.append(result)
        
        return results
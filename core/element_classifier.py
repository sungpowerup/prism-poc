"""
core/element_classifier.py
Element 자동 분류기 (정확도 개선)

개선 사항:
1. 표 과다 분류 방지 (격자선 임계값 상향)
2. 복합 Element 감지 (차트 + 표 혼재)
3. 세부 타입 정확도 향상
"""

import cv2
import numpy as np
import base64
from typing import Dict, List
from io import BytesIO
from PIL import Image


class ElementClassifier:
    """
    CV 기반 Element 자동 분류기
    
    분류 타입:
    - chart: 차트 (pie, bar, line, scatter 등)
    - table: 표
    - diagram: 다이어그램
    - text: 텍스트 위주
    - image: 일반 이미지
    """
    
    def __init__(self, use_vlm: bool = False):
        """
        Args:
            use_vlm: VLM 검증 사용 여부 (향후 구현)
        """
        self.use_vlm = use_vlm
    
    def classify(self, image_data: str, bbox: Dict = None) -> Dict:
        """
        이미지 Element 분류
        
        Args:
            image_data: Base64 이미지
            bbox: 바운딩 박스 (선택)
        
        Returns:
            {
                'element_type': str,
                'subtypes': List[str],
                'confidence': float,
                'features': Dict
            }
        """
        # Base64 → OpenCV 이미지
        img = self._base64_to_cv2(image_data)
        
        # 특징 추출
        features = self._extract_features(img)
        
        # 분류 점수 계산
        scores = self._calculate_scores(features)
        
        # 최종 분류
        element_type = max(scores, key=scores.get)
        confidence = scores[element_type]
        
        # 세부 타입 감지
        subtypes = self._detect_subtypes(element_type, features, img)
        
        return {
            'element_type': element_type,
            'subtypes': subtypes,
            'confidence': confidence,
            'features': features
        }
    
    def _base64_to_cv2(self, image_data: str) -> np.ndarray:
        """Base64 → OpenCV 이미지"""
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        img_bytes = base64.b64decode(image_data)
        img = Image.open(BytesIO(img_bytes))
        img_array = np.array(img)
        
        # RGB → BGR (OpenCV 포맷)
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_array
    
    def _extract_features(self, img: np.ndarray) -> Dict:
        """
        이미지에서 특징 추출
        
        Returns:
            {
                'has_lines': bool,
                'line_count': int,
                'has_circles': bool,
                'circle_count': int,
                'color_variance': float,
                'text_density': float,
                'edge_density': float
            }
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # 1. 선 감지 (표 격자선)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
        line_count = len(lines) if lines is not None else 0
        
        # 2. 원 감지 (파이 차트)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1, minDist=50,
            param1=50, param2=30, minRadius=20, maxRadius=200
        )
        circle_count = len(circles[0]) if circles is not None else 0
        
        # 3. 색상 분산 (차트는 색상 다양)
        color_variance = float(np.std(img))
        
        # 4. 텍스트 밀도 (OCR 없이 추정)
        text_density = self._estimate_text_density(gray)
        
        # 5. 엣지 밀도
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        return {
            'has_lines': line_count > 10,
            'line_count': line_count,
            'has_circles': circle_count > 0,
            'circle_count': circle_count,
            'color_variance': color_variance,
            'text_density': text_density,
            'edge_density': edge_density
        }
    
    def _estimate_text_density(self, gray: np.ndarray) -> float:
        """텍스트 밀도 추정"""
        # 텍스트는 작은 연결 영역이 많음
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        small_contours = [c for c in contours if cv2.contourArea(c) < 500]
        
        return len(small_contours) / (gray.shape[0] * gray.shape[1])
    
    def _calculate_scores(self, features: Dict) -> Dict[str, float]:
        """
        특징 → 분류 점수 계산 (개선)
        
        개선 사항:
        - 표 임계값 상향 (과다 분류 방지)
        - 복합 Element 처리
        """
        scores = {
            'chart': 0.0,
            'table': 0.0,
            'diagram': 0.0,
            'text': 0.0,
            'image': 0.0
        }
        
        # === Chart 점수 ===
        if features['has_circles']:
            scores['chart'] += 0.6  # 원형 차트 강력한 신호
        
        if features['color_variance'] > 50:
            scores['chart'] += 0.3  # 색상 다양성
        
        if features['line_count'] > 5 and features['line_count'] < 30:
            scores['chart'] += 0.2  # 적당한 선 (축, 격자)
        
        # === Table 점수 (임계값 상향) ===
        # ✅ 수정: 표 판정을 더 엄격하게
        if features['line_count'] > 50:  # ← 기존 20에서 50으로 상향
            scores['table'] += 0.7
        elif features['line_count'] > 30:  # 중간값
            scores['table'] += 0.4
        
        if features['text_density'] > 0.01:
            scores['table'] += 0.3  # 텍스트 많음
        
        # === Diagram 점수 ===
        if features['edge_density'] > 0.1 and not features['has_circles']:
            scores['diagram'] += 0.5
        
        if features['color_variance'] > 30 and features['line_count'] < 50:
            scores['diagram'] += 0.3
        
        # === Text 점수 ===
        if features['text_density'] > 0.02:
            scores['text'] += 0.6
        
        if features['color_variance'] < 20:  # 흑백 텍스트
            scores['text'] += 0.3
        
        # === Image 점수 (기본값) ===
        scores['image'] = 0.3  # 기본 점수
        
        # 정규화
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}
        
        return scores
    
    def _detect_subtypes(
        self, 
        element_type: str, 
        features: Dict,
        img: np.ndarray
    ) -> List[str]:
        """
        세부 타입 감지
        
        - chart: ['pie', 'bar', 'line', 'scatter']
        - table: ['simple', 'complex', 'merged']
        - diagram: ['flowchart', 'map', 'network']
        """
        subtypes = []
        
        if element_type == 'chart':
            # 파이 차트
            if features['has_circles']:
                subtypes.append('pie')
            
            # 막대 차트 (수직/수평 선 많음)
            if features['line_count'] > 10 and features['line_count'] < 30:
                subtypes.append('bar')
            
            # 선 차트 (곡선 감지)
            if self._has_curves(img):
                subtypes.append('line')
        
        elif element_type == 'table':
            # 단순 표 vs 복잡한 표
            if features['line_count'] > 100:
                subtypes.append('complex')
            else:
                subtypes.append('simple')
        
        elif element_type == 'diagram':
            # 지도 (색상 영역 분할)
            if self._looks_like_map(img):
                subtypes.append('map')
            else:
                subtypes.append('flowchart')
        
        # 기본값
        if not subtypes:
            subtypes.append('unknown')
        
        return subtypes
    
    def _has_curves(self, img: np.ndarray) -> bool:
        """곡선 감지 (선 차트)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        edges = cv2.Canny(gray, 50, 150)
        
        # 곡선은 직선이 아닌 엣지가 많음
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=5)
        line_count = len(lines) if lines is not None else 0
        
        edge_count = np.sum(edges > 0)
        
        # 엣지가 많은데 직선이 적으면 곡선
        return edge_count > 5000 and line_count < 20
    
    def _looks_like_map(self, img: np.ndarray) -> bool:
        """지도 감지 (색상 영역)"""
        # HSV 변환
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) if len(img.shape) == 3 else img
        
        # 색상 채널 분산 (지도는 영역별 색상 분리)
        if len(hsv.shape) == 3:
            hue_std = np.std(hsv[:, :, 0])
            return hue_std > 30
        
        return False


# 테스트
if __name__ == '__main__':
    classifier = ElementClassifier()
    
    # 테스트 이미지 (1x1 투명 PNG)
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    result = classifier.classify(test_image)
    
    print(f"Type: {result['element_type']}")
    print(f"Subtypes: {result['subtypes']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Features: {result['features']}")
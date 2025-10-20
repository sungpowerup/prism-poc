"""
PRISM Phase 2.8 - Element Classifier
CV 기반 휴리스틱 + VLM 검증 하이브리드 방식

Author: 박준호 (AI/ML Lead)
Date: 2025-10-21
Version: 2.0
"""

import cv2
import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """분류 결과"""
    element_type: str  # 'chart', 'table', 'text', 'diagram', 'image'
    confidence: float  # 0.0 ~ 1.0
    features: Dict[str, float]  # 특징 점수
    method: str  # 'cv_heuristic', 'vlm', 'hybrid'


class ElementClassifier:
    """
    Element 자동 분류기 (CV + VLM 하이브리드)
    
    단계:
    1. CV 기반 휴리스틱 분류 (빠름, 80% 정확도)
    2. 신뢰도 낮으면 VLM 검증 (느림, 95% 정확도)
    3. 최종 결정
    """
    
    def __init__(self, use_vlm: bool = True, vlm_threshold: float = 0.7):
        """
        Args:
            use_vlm: VLM 검증 사용 여부
            vlm_threshold: VLM 검증 트리거 임계값 (이하면 VLM 호출)
        """
        self.use_vlm = use_vlm
        self.vlm_threshold = vlm_threshold
        
        # VLM 서비스 (lazy loading)
        self._vlm_service = None
    
    @property
    def vlm_service(self):
        """VLM 서비스 lazy loading"""
        if self._vlm_service is None and self.use_vlm:
            try:
                from core.vlm_service import VLMService
                self._vlm_service = VLMService()
                logger.info("✅ VLM 서비스 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ VLM 서비스 초기화 실패: {e}")
                self.use_vlm = False
        
        return self._vlm_service
    
    def classify(
        self,
        image: Image.Image,
        use_vlm_fallback: bool = True
    ) -> ClassificationResult:
        """
        Element 분류
        
        Args:
            image: PIL Image
            use_vlm_fallback: 신뢰도 낮을 때 VLM 사용 여부
            
        Returns:
            ClassificationResult
        """
        
        # Step 1: CV 기반 휴리스틱 분류
        cv_result = self._classify_cv(image)
        
        logger.info(
            f"🔍 CV 분류: {cv_result.element_type} "
            f"(신뢰도: {cv_result.confidence:.2f})"
        )
        
        # Step 2: 신뢰도가 낮으면 VLM 검증
        if (self.use_vlm and 
            use_vlm_fallback and 
            cv_result.confidence < self.vlm_threshold):
            
            logger.info("🤖 신뢰도 낮음 → VLM 검증 시작...")
            
            try:
                vlm_result = self._classify_vlm(image)
                
                logger.info(
                    f"✅ VLM 분류: {vlm_result.element_type} "
                    f"(신뢰도: {vlm_result.confidence:.2f})"
                )
                
                # VLM 결과 우선 (더 정확함)
                return vlm_result
            
            except Exception as e:
                logger.warning(f"⚠️ VLM 분류 실패: {e}, CV 결과 사용")
        
        # Step 3: CV 결과 반환
        return cv_result
    
    def _classify_cv(self, image: Image.Image) -> ClassificationResult:
        """CV 기반 휴리스틱 분류"""
        
        # PIL → OpenCV
        img_array = np.array(image)
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_cv = img_array
        
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY) if len(img_cv.shape) == 3 else img_cv
        
        # 특징 추출
        features = {
            'has_axes': self._detect_axes(gray),
            'has_grid': self._detect_grid_lines(gray),
            'has_legend': self._detect_legend(img_cv),
            'has_table_lines': self._detect_table_lines(gray),
            'has_boxes': self._detect_boxes(gray),
            'has_arrows': self._detect_arrows(gray),
            'text_density': self._estimate_text_density(gray),
            'color_variance': self._calculate_color_variance(img_cv),
            'edge_density': self._calculate_edge_density(gray)
        }
        
        # 분류 로직
        element_type, confidence = self._classify_from_features(features)
        
        return ClassificationResult(
            element_type=element_type,
            confidence=confidence,
            features=features,
            method='cv_heuristic'
        )
    
    def _classify_from_features(
        self,
        features: Dict[str, float]
    ) -> Tuple[str, float]:
        """특징 기반 분류"""
        
        scores = {
            'chart': 0.0,
            'table': 0.0,
            'diagram': 0.0,
            'text': 0.0,
            'image': 0.0
        }
        
        # 차트 점수
        if features['has_axes'] > 0.5:
            scores['chart'] += 0.4
        if features['has_grid'] > 0.3:
            scores['chart'] += 0.3
        if features['has_legend'] > 0.3:
            scores['chart'] += 0.3
        if features['color_variance'] > 0.4:
            scores['chart'] += 0.2
        
        # 표 점수
        if features['has_table_lines'] > 0.6:
            scores['table'] += 0.7
        if features['text_density'] > 0.5:
            scores['table'] += 0.2
        if features['edge_density'] > 0.5:
            scores['table'] += 0.1
        
        # 다이어그램 점수
        if features['has_boxes'] > 0.5:
            scores['diagram'] += 0.4
        if features['has_arrows'] > 0.4:
            scores['diagram'] += 0.4
        if 0.2 < features['text_density'] < 0.5:
            scores['diagram'] += 0.2
        
        # 텍스트 점수
        if features['text_density'] > 0.7:
            scores['text'] += 0.6
        if features['edge_density'] < 0.3:
            scores['text'] += 0.2
        if features['color_variance'] < 0.2:
            scores['text'] += 0.2
        
        # 이미지 점수 (기본값)
        if features['color_variance'] > 0.6:
            scores['image'] += 0.4
        if features['edge_density'] > 0.6:
            scores['image'] += 0.3
        if features['text_density'] < 0.2:
            scores['image'] += 0.3
        
        # 최고 점수 선택
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type], 1.0)
        
        # 최소 신뢰도 보장
        if confidence < 0.3:
            confidence = 0.3
        
        return best_type, confidence
    
    def _detect_axes(self, gray: np.ndarray) -> float:
        """축 감지 (차트 특징)"""
        
        # Hough Line Transform
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=50,
            minLineLength=gray.shape[1] * 0.3,
            maxLineGap=10
        )
        
        if lines is None:
            return 0.0
        
        # 수평/수직선 비율
        h_lines = 0
        v_lines = 0
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            if angle < 10 or angle > 170:
                h_lines += 1
            elif 80 < angle < 100:
                v_lines += 1
        
        # 축이 있으면 수평+수직선이 많음
        axis_score = min((h_lines + v_lines) / 10, 1.0)
        
        return axis_score
    
    def _detect_grid_lines(self, gray: np.ndarray) -> float:
        """격자선 감지 (차트 특징)"""
        
        # 얇은 선 감지
        edges = cv2.Canny(gray, 30, 100)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=30,
            minLineLength=gray.shape[1] * 0.2,
            maxLineGap=20
        )
        
        if lines is None or len(lines) < 5:
            return 0.0
        
        # 평행선 개수
        grid_score = min(len(lines) / 15, 1.0)
        
        return grid_score
    
    def _detect_legend(self, img: np.ndarray) -> float:
        """범례 감지 (차트 특징)"""
        
        # 색상 블록 + 텍스트 패턴 감지
        # 간단한 휴리스틱: 작은 색상 영역이 텍스트 옆에 있음
        
        # HSV 변환
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 다양한 색상 존재 여부
        unique_colors = len(np.unique(hsv[:, :, 0])) / 180
        
        legend_score = min(unique_colors, 1.0) * 0.5
        
        return legend_score
    
    def _detect_table_lines(self, gray: np.ndarray) -> float:
        """표 선 감지"""
        
        # 수평/수직 선 감지
        edges = cv2.Canny(gray, 50, 150)
        
        # 수평선 커널
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel)
        
        # 수직선 커널
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        v_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kernel)
        
        # 교차점 개수
        intersections = cv2.bitwise_and(h_lines, v_lines)
        intersection_count = np.sum(intersections > 0)
        
        # 정규화
        table_score = min(intersection_count / 100, 1.0)
        
        return table_score
    
    def _detect_boxes(self, gray: np.ndarray) -> float:
        """박스 감지 (다이어그램 특징)"""
        
        # 컨투어 감지
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 사각형 비율
        rectangles = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:  # 너무 작은 것 제외
                continue
            
            # 근사 다각형
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            
            if len(approx) == 4:  # 사각형
                rectangles += 1
        
        box_score = min(rectangles / 10, 1.0)
        
        return box_score
    
    def _detect_arrows(self, gray: np.ndarray) -> float:
        """화살표 감지 (다이어그램 특징)"""
        
        # 간단한 휴리스틱: 삼각형 + 선
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        triangles = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 50 or area > 500:
                continue
            
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            
            if len(approx) == 3:  # 삼각형
                triangles += 1
        
        arrow_score = min(triangles / 5, 1.0)
        
        return arrow_score
    
    def _estimate_text_density(self, gray: np.ndarray) -> float:
        """텍스트 밀도 추정"""
        
        # 적응형 임계값
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 작은 컴포넌트 비율 (텍스트는 작은 요소가 많음)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        
        small_components = np.sum(stats[:, cv2.CC_STAT_AREA] < 200)
        text_density = min(small_components / 100, 1.0)
        
        return text_density
    
    def _calculate_color_variance(self, img: np.ndarray) -> float:
        """색상 분산 계산"""
        
        if len(img.shape) == 2:
            return 0.0
        
        # HSV 색상 채널의 표준편차
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_std = np.std(hsv[:, :, 0])
        
        # 정규화 (0-180 범위)
        color_variance = min(h_std / 90, 1.0)
        
        return color_variance
    
    def _calculate_edge_density(self, gray: np.ndarray) -> float:
        """엣지 밀도 계산"""
        
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size
        
        return min(edge_ratio * 10, 1.0)
    
    def _classify_vlm(self, image: Image.Image) -> ClassificationResult:
        """VLM 기반 분류 (높은 정확도)"""
        
        import io
        
        # PIL → bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        image_bytes = img_buffer.getvalue()
        
        # VLM 프롬프트
        prompt = """이 이미지를 다음 중 하나로 분류하세요:

1. chart - 차트, 그래프 (막대, 선, 파이, 산점도 등. 축과 데이터 포인트가 있음)
2. table - 표 (행과 열로 구성된 데이터)
3. diagram - 다이어그램 (플로우차트, 아키텍처, 네트워크 등. 박스와 화살표)
4. text - 텍스트 블록 (주로 문자로 구성)
5. image - 일반 이미지 (사진, 스크린샷, 일러스트)

한 단어로만 대답하세요 (chart, table, diagram, text, image 중 하나):"""
        
        # VLM API 호출
        result = self.vlm_service.generate_caption(
            image_data=image_bytes,
            element_type='image',
            custom_prompt=prompt
        )
        
        # 응답 파싱
        element_type = result['caption'].strip().lower()
        
        # 유효성 검증
        valid_types = ['chart', 'table', 'diagram', 'text', 'image']
        if element_type not in valid_types:
            logger.warning(f"⚠️ VLM 응답 이상: '{element_type}', 기본값 'image' 사용")
            element_type = 'image'
        
        return ClassificationResult(
            element_type=element_type,
            confidence=0.95,  # VLM은 일반적으로 높은 신뢰도
            features={},
            method='vlm'
        )


# ========== 테스트 코드 ==========

if __name__ == '__main__':
    
    # 테스트
    classifier = ElementClassifier(use_vlm=True)
    
    test_image = Image.open('input/test_chart.png')
    result = classifier.classify(test_image)
    
    print(f"\n분류 결과:")
    print(f"  타입: {result.element_type}")
    print(f"  신뢰도: {result.confidence:.2f}")
    print(f"  방법: {result.method}")
    print(f"\n특징:")
    for key, value in result.features.items():
        print(f"  {key}: {value:.2f}")
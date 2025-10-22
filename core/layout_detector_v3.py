"""
PRISM Phase 3.2 - Layout Detector v3.2 (Ultra Filtering)

✅ 주요 특징:
1. Region 감지 대폭 감소 (188개 → 20-30개 목표)
2. 초강력 필터링 파라미터 (min_size 20,000px)
3. 5-Stage 색상 검증 시스템
4. Map 오분류 완전 차단

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.2 (Ultra Filtering)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LayoutDetectorV32:
    """
    Layout Detector v3.2 - Ultra Filtering
    
    Phase 3.2 핵심 개선:
    - ✅ min_region_size: 20,000px (20배 강화)
    - ✅ pie_min_radius: 100px (3.3배 강화)
    - ✅ 5-Stage 색상 검증
    - ✅ Map 오분류 완전 차단
    """
    
    def __init__(self):
        """초기화"""
        # ⭐ 기본 파라미터 (Ultra Filtering)
        self.min_region_size = 20000  # 1,000 → 20,000 (20배)
        self.confidence_threshold = 0.75
        
        # ⭐ 원그래프 파라미터 (강화)
        self.pie_chart_params = {
            'dp': 1,
            'minDist': 300,      # 250 → 300
            'param1': 100,
            'param2': 80,        # 50 → 80 (엄격)
            'minRadius': 100,    # 30 → 100 (3.3배)
            'maxRadius': 500
        }
        
        # ⭐ 색상 검증 파라미터 (5-Stage)
        self.color_params = {
            'min_sectors': 2,           # Stage 1: 최소 섹터 수
            'min_hsv_range': 40,        # Stage 2: HSV 범위 (30 → 40)
            'min_saturation': 30,       # Stage 3: 평균 채도
            'min_value_variance': 500,  # Stage 4: 명도 분산
            'min_circularity': 0.7      # Stage 5: 원형도
        }
        
        # 표 파라미터
        self.table_params = {
            'max_width': 800,
            'max_height': 1000,
            'min_h_lines': 3,
            'min_v_lines': 3
        }
        
        # 막대그래프 파라미터
        self.bar_chart_params = {
            'min_bars': 3,
            'max_y_diff': 50,
            'min_bar_area': 1000  # 500 → 1000
        }
        
        # ⭐ Map 파라미터 (완전 차단)
        self.map_params = {
            'min_area': 100000,       # 50,000 → 100,000 (초강력)
            'min_complexity': 30,     # 20 → 30
            'max_circularity': 0.6,   # 0.7 → 0.6
            'aspect_ratio_min': 0.5,
            'aspect_ratio_max': 2.0
        }
        
        logger.info("🚀 LayoutDetectorV32 초기화 완료 (Ultra Filtering)")
        logger.info(f"   - min_region_size: {self.min_region_size:,}px")
        logger.info(f"   - pie_min_radius: {self.pie_chart_params['minRadius']}px")
        logger.info(f"   - 5-Stage 색상 검증: ON")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        레이아웃 영역 감지 (Ultra Filtering)
        
        Args:
            image: 입력 이미지 (numpy array, BGR)
            page_num: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        regions = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} - Layout Detection v3.2")
        logger.info(f"{'='*60}")
        
        # 1. 헤더 감지
        logger.info("Stage 1: 헤더 감지")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지 (Ultra Filtering + 5-Stage 검증)
        logger.info("Stage 2: 원그래프 감지 (5-Stage 검증)")
        pie_charts = self._detect_pie_charts_v32(image)
        logger.info(f"   → {len(pie_charts)}개 감지")
        regions.extend(pie_charts)
        
        # 3. 막대그래프 감지
        logger.info("Stage 3: 막대그래프 감지")
        bar_charts = self._detect_bar_charts(image)
        logger.info(f"   → {len(bar_charts)}개 감지")
        regions.extend(bar_charts)
        
        # 4. 표 감지
        logger.info("Stage 4: 표 감지")
        tables = self._detect_tables(image)
        logger.info(f"   → {len(tables)}개 감지")
        regions.extend(tables)
        
        # 5. Map 감지 (초강력 필터)
        logger.info("Stage 5: Map 감지 (Ultra Filter)")
        maps = self._detect_maps_ultra(image)
        logger.info(f"   → {len(maps)}개 감지")
        regions.extend(maps)
        
        logger.info(f"\n✅ 총 {len(regions)}개 영역 감지 완료")
        logger.info(f"{'='*60}\n")
        
        return regions
    
    def _detect_headers(self, image: np.ndarray) -> List[Dict]:
        """헤더 영역 감지"""
        headers = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        
        # 상단 10% 영역
        header_region = gray[:int(h * 0.1), :]
        
        # 텍스트 밀도 체크
        _, binary = cv2.threshold(header_region, 200, 255, cv2.THRESH_BINARY_INV)
        text_density = np.sum(binary) / (header_region.shape[0] * header_region.shape[1])
        
        if text_density > 0.02:
            headers.append({
                'type': 'header',
                'bbox': [0, 0, int(w), int(h * 0.1)],
                'confidence': 0.8,
                'metadata': {'text_density': float(text_density)}
            })
        
        return headers
    
    def _detect_pie_charts_v32(self, image: np.ndarray) -> List[Dict]:
        """
        원그래프 감지 v3.2 (Ultra Filtering + 5-Stage 검증)
        
        5-Stage 검증:
        1. Sector Counting (최소 2개 섹터)
        2. HSV Range Analysis (색상 다양성)
        3. Saturation Check (평균 채도 > 30)
        4. Value Variance (명도 분산 > 500)
        5. Circularity (원형도 > 0.7)
        """
        pie_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Hough Circle Transform (Ultra Filtering 파라미터)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            **self.pie_chart_params
        )
        
        if circles is None:
            return pie_charts
        
        circles = np.uint16(np.around(circles))
        
        for circle in circles[0, :]:
            x, y, r = circle
            
            # ROI 추출
            y1, y2 = max(0, y-r), min(image.shape[0], y+r)
            x1, x2 = max(0, x-r), min(image.shape[1], x+r)
            roi = image[y1:y2, x1:x2]
            
            if roi.size == 0:
                continue
            
            # ⭐ 크기 필터링 (Ultra)
            area = np.pi * r * r
            if area < self.min_region_size:
                logger.debug(f"   ❌ Circle 제외 (크기 부족: {area:.0f}px)")
                continue
            
            # ⭐ 5-Stage 색상 검증
            if not self._verify_pie_chart_5stage(roi):
                logger.debug(f"   ❌ Circle 제외 (5-Stage 검증 실패)")
                continue
            
            # ✅ 통과
            pie_charts.append({
                'type': 'pie_chart',
                'bbox': [int(x-r), int(y-r), int(2*r), int(2*r)],
                'confidence': 0.90,
                'metadata': {
                    'radius': int(r),
                    'area': int(area),
                    '5stage_verified': True
                }
            })
        
        return pie_charts
    
    def _verify_pie_chart_5stage(self, roi: np.ndarray) -> bool:
        """
        5-Stage 원그래프 검증
        
        Returns:
            True if 원그래프, False otherwise
        """
        if roi.size == 0:
            return False
        
        # Stage 1: Sector Counting
        sectors = self._count_sectors(roi)
        if sectors < self.color_params['min_sectors']:
            logger.debug(f"      Stage 1 실패: sectors={sectors}")
            return False
        
        # Stage 2: HSV Range Analysis
        hsv_range = self._calculate_hsv_range(roi)
        if hsv_range < self.color_params['min_hsv_range']:
            logger.debug(f"      Stage 2 실패: hsv_range={hsv_range:.1f}")
            return False
        
        # Stage 3: Saturation Check
        avg_saturation = self._calculate_avg_saturation(roi)
        if avg_saturation < self.color_params['min_saturation']:
            logger.debug(f"      Stage 3 실패: saturation={avg_saturation:.1f}")
            return False
        
        # Stage 4: Value Variance
        value_variance = self._calculate_value_variance(roi)
        if value_variance < self.color_params['min_value_variance']:
            logger.debug(f"      Stage 4 실패: variance={value_variance:.1f}")
            return False
        
        # Stage 5: Circularity
        circularity = self._calculate_circularity(roi)
        if circularity < self.color_params['min_circularity']:
            logger.debug(f"      Stage 5 실패: circularity={circularity:.2f}")
            return False
        
        logger.debug(f"      ✅ 5-Stage 검증 통과")
        return True
    
    def _count_sectors(self, roi: np.ndarray) -> int:
        """Stage 1: 섹터 개수 세기"""
        if roi.size == 0:
            return 0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        edges = cv2.Canny(gray, 50, 150)
        
        # 직선 검출 (섹터 경계)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30, minLineLength=20, maxLineGap=10)
        
        if lines is None:
            return 0
        
        # 중심에서 시작하는 직선 수 (대략적)
        return min(len(lines), 10)  # 최대 10개로 제한
    
    def _calculate_hsv_range(self, roi: np.ndarray) -> float:
        """Stage 2: HSV 색상 범위 계산"""
        if roi.size == 0:
            return 0.0
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        
        # Hue 범위 (0-179)
        h_range = float(np.max(h_channel) - np.min(h_channel))
        return h_range
    
    def _calculate_avg_saturation(self, roi: np.ndarray) -> float:
        """Stage 3: 평균 채도 계산"""
        if roi.size == 0:
            return 0.0
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        s_channel = hsv[:, :, 1]
        
        return float(np.mean(s_channel))
    
    def _calculate_value_variance(self, roi: np.ndarray) -> float:
        """Stage 4: 명도 분산 계산"""
        if roi.size == 0:
            return 0.0
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        
        return float(np.var(v_channel))
    
    def _calculate_circularity(self, roi: np.ndarray) -> float:
        """Stage 5: 원형도 계산"""
        if roi.size == 0:
            return 0.0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        # 가장 큰 윤곽선
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        perimeter = cv2.arcLength(largest_contour, True)
        
        if perimeter == 0:
            return 0.0
        
        # Circularity = 4π × Area / Perimeter²
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        return float(circularity)
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """막대그래프 감지"""
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 사각형 필터링
        rectangles = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # 크기 필터링
            if area < self.bar_chart_params['min_bar_area']:
                continue
            
            # 종횡비 (세로 막대: h > w)
            if h > w * 1.5:
                rectangles.append((x, y, w, h))
        
        # 그룹화 (수평 정렬 막대 3개 이상)
        if len(rectangles) >= self.bar_chart_params['min_bars']:
            rectangles_sorted = sorted(rectangles, key=lambda r: r[0])
            
            for i in range(len(rectangles_sorted) - 2):
                r1, r2, r3 = rectangles_sorted[i:i+3]
                
                # Y축 정렬 체크
                y_align = (abs(r1[1] - r2[1]) < self.bar_chart_params['max_y_diff'] and
                          abs(r2[1] - r3[1]) < self.bar_chart_params['max_y_diff'])
                
                if y_align:
                    # Bounding box
                    min_x = min(r1[0], r2[0], r3[0])
                    min_y = min(r1[1], r2[1], r3[1])
                    max_x = max(r1[0] + r1[2], r2[0] + r2[2], r3[0] + r3[2])
                    max_y = max(r1[1] + r1[3], r2[1] + r2[3], r3[1] + r3[3])
                    
                    w = max_x - min_x
                    h = max_y - min_y
                    
                    if w * h >= self.min_region_size:
                        bar_charts.append({
                            'type': 'bar_chart',
                            'bbox': [int(min_x), int(min_y), int(w), int(h)],
                            'confidence': 0.85,
                            'metadata': {'bars': 3, 'y_aligned': True}
                        })
                        break
        
        return bar_charts
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """표 감지"""
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 선 검출
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is not None:
            # 수평선/수직선 분리
            h_lines = []
            v_lines = []
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                if abs(y1 - y2) < 10:
                    h_lines.append(line)
                elif abs(x1 - x2) < 10:
                    v_lines.append(line)
            
            # 표 조건
            if len(h_lines) >= self.table_params['min_h_lines'] and \
               len(v_lines) >= self.table_params['min_v_lines']:
                
                # Bounding box
                all_x = [p for line in lines for p in [line[0][0], line[0][2]]]
                all_y = [p for line in lines for p in [line[0][1], line[0][3]]]
                
                x, y = int(min(all_x)), int(min(all_y))
                w, h = int(max(all_x) - x), int(max(all_y) - y)
                
                # 크기 제한
                if w > self.table_params['max_width'] or h > self.table_params['max_height']:
                    logger.warning(f"   ⚠️ Table 제외 (크기 초과: {w}x{h})")
                    return tables
                
                area = w * h
                if area >= self.min_region_size:
                    tables.append({
                        'type': 'table',
                        'bbox': [x, y, w, h],
                        'confidence': 0.85,
                        'metadata': {
                            'h_lines': len(h_lines),
                            'v_lines': len(v_lines)
                        }
                    })
        
        return tables
    
    def _detect_maps_ultra(self, image: np.ndarray) -> List[Dict]:
        """
        Map 감지 (Ultra Filter - 완전 차단)
        
        Phase 3.2:
        - min_area: 100,000px (초강력)
        - complexity: 30 (매우 복잡한 형태만)
        - circularity < 0.6 (비원형만)
        """
        maps = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 1. 크기 필터링 (Ultra)
            area = w * h
            if area < self.map_params['min_area']:
                continue
            
            # 2. 정사각형 제외
            aspect_ratio = w / h if h > 0 else 0
            if not (self.map_params['aspect_ratio_min'] <= aspect_ratio <= self.map_params['aspect_ratio_max']):
                continue
            
            # 3. 원형도 체크
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
            
            circularity = (4 * np.pi * area) / (perimeter ** 2)
            if circularity > self.map_params['max_circularity']:
                continue
            
            # 4. 복잡도 체크
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue
            
            complexity = (1 - area / hull_area) * 100
            if complexity < self.map_params['min_complexity']:
                continue
            
            # ✅ 통과 (매우 드묾)
            maps.append({
                'type': 'map',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': 0.80,
                'metadata': {
                    'area': int(area),
                    'complexity': float(complexity),
                    'circularity': float(circularity)
                }
            })
        
        return maps


# 테스트 코드
if __name__ == '__main__':
    import sys
    from PIL import Image
    
    if len(sys.argv) < 2:
        print("사용법: python layout_detector_v3.py <image_path>")
        sys.exit(1)
    
    # 이미지 로드
    img_path = sys.argv[1]
    pil_img = Image.open(img_path)
    img_array = np.array(pil_img)
    
    # BGR 변환
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 감지
    detector = LayoutDetectorV32()
    regions = detector.detect_regions(img_array, page_num=0)
    
    print(f"\n✅ 총 {len(regions)}개 영역 감지:")
    for i, region in enumerate(regions):
        print(f"{i+1}. {region['type']}: bbox={region['bbox']}, conf={region['confidence']:.2f}")

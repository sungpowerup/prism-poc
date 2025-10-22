"""
PRISM Phase 3.1 - Layout Detector (Map 오분류 차단 + 개선)

✅ 주요 개선:
1. Map 오분류 완전 차단 (크기/형태 강화)
2. 막대그래프 감지 추가
3. Table 과잉 통합 방지
4. 정사각형/원형 요소 Map 제외

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.1
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class LayoutDetector:
    """
    레이아웃 감지기 (Phase 3.1)
    
    개선 사항:
    - ✅ Map 오분류 완전 차단 (크기 50,000px 이상, 정사각형 제외)
    - ✅ 막대그래프 감지 추가
    - ✅ Table 크기 제한 (800x1000px)
    - ✅ 원그래프 감지 강화
    """
    
    def __init__(self):
        """초기화"""
        # 기본 파라미터
        self.min_region_size = 20000
        self.confidence_threshold = 0.70
        
        # ⭐ Map 파라미터 (강화)
        self.map_params = {
            'min_area': 50000,  # 20,000 → 50,000 (작은 차트 제외)
            'min_complexity': 20,  # 12 → 20 (단순 형태 제외)
            'max_circularity': 0.7,  # 0.8 → 0.7 (원형 제외)
            'aspect_ratio_min': 0.6,  # 0.7 → 0.6
            'aspect_ratio_max': 1.8,  # 1.5 → 1.8
            'exclude_square': True,  # ⭐ 정사각형 완전 제외
            'square_threshold': 0.15  # ±15% 이내는 정사각형
        }
        
        # 원그래프 파라미터
        self.pie_chart_params = {
            'dp': 1,
            'minDist': 250,
            'param1': 100,
            'param2': 80,
            'minRadius': 100,
            'maxRadius': 500
        }
        
        # 컬러 검증 파라미터
        self.color_params = {
            'min_color_std': 20,
            'min_hsv_range': 30,
            'min_sectors': 2,
            'max_circularity': 4.0
        }
        
        # ⭐ Table 파라미터 (개선)
        self.table_params = {
            'max_width': 800,   # 최대 가로 (과잉 통합 방지)
            'max_height': 1000, # 최대 세로
            'min_h_lines': 3,
            'min_v_lines': 3
        }
        
        # ⭐ 막대그래프 파라미터 (신규)
        self.bar_chart_params = {
            'min_bars': 3,
            'max_y_diff': 50,
            'min_bar_area': 500
        }
        
        logger.info("🔍 LayoutDetector 초기화 완료 (Phase 3.1)")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        레이아웃 영역 감지
        
        Args:
            image: 입력 이미지 (numpy array)
            page_num: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        regions = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} 레이아웃 감지 (Phase 3.1)")
        logger.info(f"{'='*60}")
        
        # 1. 헤더 감지
        logger.info("1. 헤더 감지 중...")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 헤더 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지
        logger.info("2. 원그래프 감지 중...")
        pie_charts = self._detect_pie_charts(image)
        logger.info(f"   → {len(pie_charts)}개 원그래프 감지")
        regions.extend(pie_charts)
        
        # 3. ⭐ 막대그래프 감지 (신규)
        logger.info("3. 막대그래프 감지 중...")
        bar_charts = self._detect_bar_charts(image)
        logger.info(f"   → {len(bar_charts)}개 막대그래프 감지")
        regions.extend(bar_charts)
        
        # 4. 표 감지
        logger.info("4. 표 감지 중...")
        tables = self._detect_tables(image)
        logger.info(f"   → {len(tables)}개 표 감지")
        regions.extend(tables)
        
        # 5. ⭐ 지도 감지 (강화된 필터)
        logger.info("5. 지도 감지 중 (강화 필터)...")
        maps = self._detect_maps_strict(image)
        logger.info(f"   → {len(maps)}개 지도 감지")
        regions.extend(maps)
        
        # 필터링 및 병합
        logger.info(f"\n총 {len(regions)}개 영역 감지 완료")
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
                'metadata': {
                    'text_density': float(text_density)
                }
            })
        
        return headers
    
    def _detect_pie_charts(self, image: np.ndarray) -> List[Dict]:
        """원그래프 감지"""
        pie_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Hough Circle Transform
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            **self.pie_chart_params
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                x, y, r = circle
                
                # ROI 추출
                roi = image[max(0, y-r):min(image.shape[0], y+r),
                           max(0, x-r):min(image.shape[1], x+r)]
                
                if roi.size == 0:
                    continue
                
                # 크기 필터링
                area = np.pi * r * r
                if area < self.min_region_size:
                    continue
                
                # 컬러 다양성 체크
                color_std = 0.0
                if len(roi.shape) == 3:
                    color_std = np.std(roi, axis=(0, 1)).mean()
                    if color_std < self.color_params['min_color_std']:
                        continue
                
                # 섹터 수 확인
                num_sectors = self._count_sectors(roi)
                if num_sectors < self.color_params['min_sectors']:
                    continue
                
                pie_charts.append({
                    'type': 'pie_chart',
                    'bbox': [int(x - r), int(y - r), int(2 * r), int(2 * r)],
                    'confidence': 0.90,
                    'metadata': {
                        'radius': int(r),
                        'center': [int(x), int(y)],
                        'area': int(area),
                        'sectors': int(num_sectors),
                        'color_std': float(color_std)
                    }
                })
        
        return pie_charts
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ 막대그래프 감지 (신규)
        
        특징:
        - 3개 이상의 직사각형이 수평으로 정렬
        - Y축 위치가 유사 (±50px)
        """
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 직사각형 후보 수집
        rectangles = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # 크기 필터링
            if area < self.bar_chart_params['min_bar_area']:
                continue
            
            # 종횡비 체크 (막대 형태)
            aspect_ratio = h / w if w > 0 else 0
            if 0.3 < aspect_ratio < 3.0:
                rectangles.append((x, y, w, h))
        
        # 그룹화 (수평 정렬)
        if len(rectangles) >= self.bar_chart_params['min_bars']:
            rectangles_sorted = sorted(rectangles, key=lambda r: r[0])  # X축 기준 정렬
            
            for i in range(len(rectangles_sorted) - 2):
                r1, r2, r3 = rectangles_sorted[i:i+3]
                
                # Y축 정렬 체크
                y_align = (abs(r1[1] - r2[1]) < self.bar_chart_params['max_y_diff'] and 
                          abs(r2[1] - r3[1]) < self.bar_chart_params['max_y_diff'])
                
                if y_align:
                    # Bounding box 계산
                    min_x = min(r1[0], r2[0], r3[0])
                    min_y = min(r1[1], r2[1], r3[1])
                    max_x = max(r1[0] + r1[2], r2[0] + r2[2], r3[0] + r3[2])
                    max_y = max(r1[1] + r1[3], r2[1] + r2[3], r3[1] + r3[3])
                    
                    w = max_x - min_x
                    h = max_y - min_y
                    
                    # 크기 체크
                    if w * h >= self.min_region_size:
                        bar_charts.append({
                            'type': 'bar_chart',
                            'bbox': [int(min_x), int(min_y), int(w), int(h)],
                            'confidence': 0.85,
                            'metadata': {
                                'bars': 3,
                                'y_aligned': True
                            }
                        })
                        break  # 하나만 감지 (중복 방지)
        
        return bar_charts
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """
        표 감지 (개선)
        
        ⭐ 과잉 통합 방지:
        - 최대 크기 800x1000px
        """
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 선 검출
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            100,
            minLineLength=100,
            maxLineGap=10
        )
        
        if lines is not None:
            # 수평선과 수직선 분리
            h_lines = []
            v_lines = []
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # 수평선
                if abs(y1 - y2) < 10:
                    h_lines.append(line)
                # 수직선
                elif abs(x1 - x2) < 10:
                    v_lines.append(line)
            
            # 표 조건: 수평선 3개 이상, 수직선 3개 이상
            if len(h_lines) >= self.table_params['min_h_lines'] and \
               len(v_lines) >= self.table_params['min_v_lines']:
                
                # Bounding box 계산
                all_x = [p for line in lines for p in [line[0][0], line[0][2]]]
                all_y = [p for line in lines for p in [line[0][1], line[0][3]]]
                
                x, y = int(min(all_x)), int(min(all_y))
                w, h = int(max(all_x) - x), int(max(all_y) - y)
                
                # ⭐ 크기 제한 (과잉 통합 방지)
                if w > self.table_params['max_width'] or h > self.table_params['max_height']:
                    logger.warning(f"   ⚠️ Table 너무 큼 ({w}x{h}), 건너뜀")
                    return tables
                
                # 크기 필터링
                area = w * h
                if area >= self.min_region_size:
                    tables.append({
                        'type': 'table',
                        'bbox': [x, y, w, h],
                        'confidence': 0.85,
                        'metadata': {
                            'h_lines': int(len(h_lines)),
                            'v_lines': int(len(v_lines))
                        }
                    })
        
        return tables
    
    def _detect_maps_strict(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ 지도 감지 (강화된 필터)
        
        개선:
        1. 최소 크기 50,000px (작은 차트 제외)
        2. 정사각형 완전 제외 (aspect_ratio 0.85~1.15)
        3. 복잡도 20 이상 (단순 형태 제외)
        4. 원형도 0.7 이하 (원형 제외)
        """
        maps = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 엣지 검출
        edges = cv2.Canny(gray, 50, 150)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # ⭐ 1. 크기 필터링 (강화)
            area = w * h
            if area < self.map_params['min_area']:  # 50,000px 이상
                continue
            
            # ⭐ 2. 정사각형 완전 제외
            aspect_ratio = w / h if h > 0 else 0
            if self.map_params['exclude_square']:
                lower = 1.0 - self.map_params['square_threshold']  # 0.85
                upper = 1.0 + self.map_params['square_threshold']  # 1.15
                
                if lower <= aspect_ratio <= upper:
                    logger.debug(f"   ⚠️ 정사각형 제외 (ratio={aspect_ratio:.2f})")
                    continue
            
            # 종횡비 범위 체크
            if not (self.map_params['aspect_ratio_min'] < aspect_ratio < self.map_params['aspect_ratio_max']):
                continue
            
            # ⭐ 3. 복잡도 체크 (강화)
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            if len(approx) <= self.map_params['min_complexity']:  # 20 이상
                logger.debug(f"   ⚠️ 복잡도 낮음 (points={len(approx)})")
                continue
            
            # ⭐ 4. 원형도 체크 (강화)
            circularity = (4 * np.pi * cv2.contourArea(contour)) / (perimeter ** 2) if perimeter > 0 else 0
            if circularity > self.map_params['max_circularity']:  # 0.7 이하
                logger.debug(f"   ⚠️ 원형 제외 (circularity={circularity:.2f})")
                continue
            
            # ⭐ 모든 필터 통과!
            maps.append({
                'type': 'map',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': 0.70,
                'metadata': {
                    'complexity': int(len(approx)),
                    'aspect_ratio': float(aspect_ratio),
                    'circularity': float(circularity),
                    'area': int(area)
                }
            })
        
        return maps
    
    def _count_sectors(self, roi: np.ndarray) -> int:
        """섹터 수 추정 (K-means)"""
        if len(roi.shape) != 3:
            return 0
        
        # 픽셀을 1D 배열로 변환
        pixels = roi.reshape(-1, 3).astype(np.float32)
        
        # K-means 클러스터링 (최대 8개)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 8, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        
        # 유의미한 컬러 개수 (5% 이상)
        unique, counts = np.unique(labels, return_counts=True)
        total_pixels = len(labels)
        significant_colors = np.sum(counts > total_pixels * 0.05)
        
        return int(significant_colors)
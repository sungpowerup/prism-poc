"""
PRISM Phase 3.0 - Layout Detector (수정)
차트 타입별 정확한 감지
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class LayoutDetector:
    """
    문서 레이아웃 감지기 (차트 타입 구분 개선)
    """
    
    def __init__(self):
        self.min_region_size = 1000  # 최소 영역 크기 (픽셀)
        self.confidence_threshold = 0.6
        
    def detect_regions(self, image: np.ndarray, page_number: int) -> List[Dict]:
        """
        페이지 내 모든 영역 감지 (타입별 구분)
        
        Args:
            image: 페이지 이미지 (numpy array)
            page_number: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"페이지 {page_number} 레이아웃 감지 시작")
        logger.info(f"{'='*60}")
        
        regions = []
        
        # 1. 헤더 감지 (텍스트 영역)
        logger.info("1. 헤더 감지 중...")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 헤더 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지
        logger.info("2. 원그래프 감지 중...")
        pie_charts = self._detect_pie_charts(image)
        logger.info(f"   → {len(pie_charts)}개 원그래프 감지")
        regions.extend(pie_charts)
        
        # 3. 막대그래프 감지
        logger.info("3. 막대그래프 감지 중...")
        bar_charts = self._detect_bar_charts(image)
        logger.info(f"   → {len(bar_charts)}개 막대그래프 감지")
        regions.extend(bar_charts)
        
        # 4. 표 감지
        logger.info("4. 표 감지 중...")
        tables = self._detect_tables(image)
        logger.info(f"   → {len(tables)}개 표 감지")
        regions.extend(tables)
        
        # 5. 지도 감지 (한국 지도)
        logger.info("5. 지도 감지 중...")
        maps = self._detect_maps(image)
        logger.info(f"   → {len(maps)}개 지도 감지")
        regions.extend(maps)
        
        # 6. 중첩 제거 및 우선순위 정렬
        logger.info("6. 영역 중첩 제거 중...")
        regions = self._remove_overlaps(regions)
        
        # 7. VLM 검증 (선택)
        logger.info("7. VLM 검증 중...")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"총 {len(regions)}개 영역 감지 완료")
        for i, region in enumerate(regions, 1):
            logger.info(
                f"   Region {i}: {region['type']:<10} at "
                f"({region['bbox'][0]}, {region['bbox'][1]}, "
                f"{region['bbox'][2]}, {region['bbox'][3]}) "
                f"(신뢰도: {region['confidence']:.2f})"
            )
        logger.info(f"{'='*60}\n")
        
        return regions
    
    def _detect_headers(self, image: np.ndarray) -> List[Dict]:
        """
        헤더(텍스트 영역) 감지
        
        Args:
            image: 이미지
            
        Returns:
            헤더 영역 리스트
        """
        headers = []
        
        # OCR 기반 텍스트 영역 감지 (간단한 버전)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 텍스트가 있는 영역은 상단 10% 영역에서 찾기
        h, w = gray.shape[:2]
        header_region = gray[:int(h * 0.1), :]
        
        # 텍스트 밀도가 높은 영역 찾기
        _, binary = cv2.threshold(header_region, 200, 255, cv2.THRESH_BINARY_INV)
        text_density = np.sum(binary) / (header_region.shape[0] * header_region.shape[1])
        
        if text_density > 0.01:  # 1% 이상 텍스트 밀도
            headers.append({
                'type': 'header',
                'bbox': [0, 0, w, int(h * 0.1)],
                'confidence': 0.8,
                'metadata': {'text_density': text_density}
            })
        
        return headers
    
    def _detect_pie_charts(self, image: np.ndarray) -> List[Dict]:
        """
        원그래프 감지
        
        Args:
            image: 이미지
            
        Returns:
            원그래프 영역 리스트
        """
        pie_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Hough Circle Transform으로 원 감지
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=100,
            param1=50,
            param2=30,
            minRadius=30,
            maxRadius=200
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                x, y, r = circle
                
                # 원 영역 크롭
                x1, y1 = max(0, x - r), max(0, y - r)
                x2, y2 = min(image.shape[1], x + r), min(image.shape[0], y + r)
                
                roi = image[y1:y2, x1:x2]
                
                # 색상 다양성 확인 (파이 차트는 여러 색상)
                if self._has_multiple_colors(roi):
                    pie_charts.append({
                        'type': 'pie_chart',
                        'bbox': [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                        'confidence': 0.85,
                        'metadata': {
                            'center': (int(x), int(y)),
                            'radius': int(r)
                        }
                    })
        
        return pie_charts
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """
        막대그래프 감지
        
        Args:
            image: 이미지
            
        Returns:
            막대그래프 영역 리스트
        """
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Canny Edge Detection
        edges = cv2.Canny(gray, 50, 150)
        
        # 직사각형 찾기
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 정렬된 직사각형 그룹 찾기
        rectangles = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 막대 모양 필터링 (세로 막대 또는 가로 막대)
            aspect_ratio = w / h if h > 0 else 0
            
            if (aspect_ratio > 0.2 and aspect_ratio < 5) and (w * h > self.min_region_size):
                rectangles.append({
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'aspect_ratio': aspect_ratio
                })
        
        # 정렬된 직사각형 그룹화 (막대그래프 후보)
        if len(rectangles) >= 3:  # 최소 3개 막대
            # Y 좌표 기준 그룹화 (가로 막대) 또는 X 좌표 기준 그룹화 (세로 막대)
            rectangles.sort(key=lambda r: r['y'])
            
            groups = self._group_aligned_rectangles(rectangles)
            
            for group in groups:
                if len(group) >= 3:  # 3개 이상 막대
                    x_min = min(r['x'] for r in group)
                    y_min = min(r['y'] for r in group)
                    x_max = max(r['x'] + r['w'] for r in group)
                    y_max = max(r['y'] + r['h'] for r in group)
                    
                    bar_charts.append({
                        'type': 'bar_chart',
                        'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
                        'confidence': 0.80,
                        'metadata': {
                            'bar_count': len(group),
                            'orientation': 'horizontal' if group[0]['w'] > group[0]['h'] else 'vertical'
                        }
                    })
        
        return bar_charts
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """
        표 감지
        
        Args:
            image: 이미지
            
        Returns:
            표 영역 리스트
        """
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 수평/수직 라인 감지
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # 이진화
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 수평선 감지
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        
        # 수직선 감지
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        
        # 교차점 찾기 (표의 특징)
        table_structure = cv2.add(horizontal_lines, vertical_lines)
        
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 표 크기 필터링
            if w * h > self.min_region_size * 2:
                tables.append({
                    'type': 'table',
                    'bbox': [x, y, w, h],
                    'confidence': 0.75,
                    'metadata': {}
                })
        
        return tables
    
    def _detect_maps(self, image: np.ndarray) -> List[Dict]:
        """
        지도 감지 (한국 지도 한정)
        
        Args:
            image: 이미지
            
        Returns:
            지도 영역 리스트
        """
        maps = []
        
        # 색상 기반 영역 감지
        colorful_regions = self._find_colorful_regions(image)
        
        for region in colorful_regions:
            x, y, w, h = region['bbox']
            
            # 한국 지도 특징: 세로로 긴 형태
            aspect_ratio = h / w if w > 0 else 0
            
            # 한국 지도는 대략 1.2~1.8 비율
            if 1.0 < aspect_ratio < 2.0:
                # 추가 검증: 복잡도가 높은지 (지도는 복잡함)
                complexity = self._calculate_complexity(image[y:y+h, x:x+w])
                
                if complexity > 5.0:  # 복잡도 기준
                    maps.append({
                        'type': 'map',
                        'bbox': [x, y, w, h],
                        'confidence': 0.70,
                        'metadata': {
                            'complexity': complexity
                        }
                    })
        
        return maps
    
    def _find_colorful_regions(self, image: np.ndarray) -> List[Dict]:
        """
        컬러풀한 영역 찾기
        
        Args:
            image: 이미지
            
        Returns:
            영역 리스트
        """
        regions = []
        
        if len(image.shape) == 2:
            return regions  # 그레이스케일은 스킵
        
        # HSV 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 채도(Saturation) 기반 마스크
        _, saturation, _ = cv2.split(hsv)
        _, mask = cv2.threshold(saturation, 30, 255, cv2.THRESH_BINARY)
        
        # 컨투어 찾기
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w * h > self.min_region_size:
                regions.append({
                    'bbox': [x, y, w, h]
                })
        
        return regions
    
    def _has_multiple_colors(self, roi: np.ndarray, threshold: int = 3) -> bool:
        """
        영역에 여러 색상이 있는지 확인 (파이 차트 검증)
        
        Args:
            roi: 관심 영역
            threshold: 최소 색상 개수
            
        Returns:
            True if 여러 색상 존재
        """
        if len(roi.shape) == 2:
            return False
        
        # 색상 히스토그램
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        
        # 피크 개수 세기
        peaks = 0
        for i in range(len(hist) - 1):
            if hist[i] > 100:  # 임계값
                peaks += 1
        
        return peaks >= threshold
    
    def _calculate_complexity(self, roi: np.ndarray) -> float:
        """
        영역의 복잡도 계산
        
        Args:
            roi: 관심 영역
            
        Returns:
            복잡도 점수
        """
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # Laplacian으로 엣지 강도 계산
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        complexity = np.var(laplacian)
        
        return complexity
    
    def _group_aligned_rectangles(self, rectangles: List[Dict]) -> List[List[Dict]]:
        """
        정렬된 직사각형 그룹화 (막대그래프 감지용)
        
        Args:
            rectangles: 직사각형 리스트
            
        Returns:
            그룹화된 리스트
        """
        if not rectangles:
            return []
        
        groups = []
        current_group = [rectangles[0]]
        
        for i in range(1, len(rectangles)):
            prev = rectangles[i - 1]
            curr = rectangles[i]
            
            # Y 좌표 차이가 작으면 같은 그룹 (가로 막대)
            if abs(curr['y'] - prev['y']) < 50:
                current_group.append(curr)
            else:
                if len(current_group) >= 3:
                    groups.append(current_group)
                current_group = [curr]
        
        if len(current_group) >= 3:
            groups.append(current_group)
        
        return groups
    
    def _remove_overlaps(self, regions: List[Dict]) -> List[Dict]:
        """
        중첩된 영역 제거 (IoU 기반)
        
        Args:
            regions: 영역 리스트
            
        Returns:
            중복 제거된 리스트
        """
        if len(regions) <= 1:
            return regions
        
        # 신뢰도 기준 정렬 (높은 것 우선)
        regions.sort(key=lambda r: r['confidence'], reverse=True)
        
        filtered = []
        
        for region in regions:
            overlaps = False
            
            for existing in filtered:
                iou = self._calculate_iou(region['bbox'], existing['bbox'])
                
                if iou > 0.5:  # 50% 이상 겹치면 중복
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(region)
        
        # 위치 기준 정렬 (위 → 아래, 왼쪽 → 오른쪽)
        filtered.sort(key=lambda r: (r['bbox'][1], r['bbox'][0]))
        
        return filtered
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """
        IoU (Intersection over Union) 계산
        
        Args:
            bbox1: [x, y, w, h]
            bbox2: [x, y, w, h]
            
        Returns:
            IoU 값 (0~1)
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # 교집합 영역
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # 합집합 영역
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
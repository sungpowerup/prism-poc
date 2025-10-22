"""
PRISM Phase 3.2 - Ultra Filtering Layout Detector
초강력 필터링 + 컬러 검증 강화

✨ Phase 3.1 → 3.2 개선:
1. 초강력 파라미터
   - min_region_size: 5,000 → 20,000 (4배)
   - minRadius: 60 → 100 (작은 원 완전 배제)
   - param2: 50 → 80 (매우 엄격)
   - minDist: 150 → 250 (넓은 간격)

2. 컬러 검증 강화
   - 섹터 수 확인 (최소 2개)
   - 면적 대비 둘레 비율 체크
   - HSV 컬러 다양성 검증
   - 그레이스케일 영역 제외

3. 지능형 필터링 강화
   - 크기 필터 실제 적용
   - 종횡비 검증
   - 컬러 복잡도 임계값

예상 효과:
- 영역 감지: 36개 → 6~8개
- 원그래프: 40개 → 3~5개
- 정확도: 95%+
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class UltraLayoutDetector:
    """
    초강력 레이아웃 감지기 (Phase 3.2)
    - 초강력 파라미터
    - 컬러 검증 강화
    """
    
    def __init__(self):
        # ⭐ 초강력 파라미터
        self.min_region_size = 20000  # 5,000 → 20,000 (4배)
        self.confidence_threshold = 0.75  # 0.7 → 0.75
        
        # 원그래프 파라미터 (초강력)
        self.pie_chart_params = {
            'minRadius': 100,     # 60 → 100 (작은 원 완전 배제)
            'maxRadius': 500,
            'param1': 50,
            'param2': 80,         # 50 → 80 (매우 엄격)
            'minDist': 250        # 150 → 250 (넓은 간격)
        }
        
        # 컬러 검증 파라미터
        self.color_params = {
            'min_color_std': 20,      # 최소 컬러 표준편차 (단색 제외)
            'min_sectors': 2,         # 최소 섹터 수
            'max_circularity': 4.0,   # 최대 원형도 (불규칙 제외)
            'min_hsv_range': 30       # 최소 HSV 범위
        }
        
        # IoU 임계값 (중복 제거)
        self.iou_threshold = 0.6  # 0.5 → 0.6 (더 엄격)
        
    def detect_regions(self, image: np.ndarray, page_number: int) -> List[Dict]:
        """
        페이지 내 모든 영역 감지 (초강력 필터링)
        
        Args:
            image: 페이지 이미지 (numpy array)
            page_number: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"페이지 {page_number} 레이아웃 감지 시작 (Phase 3.2 Ultra)")
        logger.info(f"{'='*60}")
        
        # ✨ Stage 0: 사전 이미지 분석
        logger.info("0. 사전 이미지 분석 중...")
        image_quality = self._analyze_image_quality(image)
        logger.info(f"   → 이미지 품질: {image_quality['score']:.2f}")
        logger.info(f"   → 텍스트 밀도: {image_quality['text_density']:.3f}")
        logger.info(f"   → 컬러 복잡도: {image_quality['color_complexity']:.2f}")
        
        regions = []
        
        # 1. 헤더 감지
        logger.info("1. 헤더 감지 중...")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 헤더 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지 (초강력 + 컬러 검증)
        logger.info("2. 원그래프 감지 중 (Ultra 필터링)...")
        pie_charts = self._detect_pie_charts_ultra(image)
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
        
        # 5. 지도 감지
        logger.info("5. 지도 감지 중...")
        maps = self._detect_maps(image)
        logger.info(f"   → {len(maps)}개 지도 감지")
        regions.extend(maps)
        
        # ⭐ Stage 6: 초강력 필터링
        logger.info("6. 초강력 필터링 중...")
        regions_before = len(regions)
        regions = self._ultra_filter(regions, image)
        logger.info(f"   → 필터링: {regions_before}개 → {len(regions)}개")
        
        # ⭐ Stage 7: 지능형 병합
        logger.info("7. 지능형 병합 중...")
        regions_before = len(regions)
        regions = self._smart_merge(regions)
        logger.info(f"   → 병합: {regions_before}개 → {len(regions)}개")
        
        # 8. 중첩 제거 (강화)
        logger.info("8. 중첩 제거 중 (IoU=0.6)...")
        regions_before = len(regions)
        regions = self._remove_overlaps_ultra(regions)
        logger.info(f"   → 최종: {regions_before}개 → {len(regions)}개")
        
        # 최종 결과 로깅
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 총 {len(regions)}개 영역 감지 완료")
        for i, region in enumerate(regions, 1):
            logger.info(
                f"   Region {i}: {region['type']:<12} at "
                f"({region['bbox'][0]:4d}, {region['bbox'][1]:4d}, "
                f"{region['bbox'][2]:4d}, {region['bbox'][3]:4d}) "
                f"[신뢰도: {region['confidence']:.2f}]"
            )
        logger.info(f"{'='*60}\n")
        
        return regions
    
    def _analyze_image_quality(self, image: np.ndarray) -> Dict:
        """사전 이미지 품질 분석"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape
        
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        text_density = np.sum(binary) / (h * w)
        
        color_complexity = np.std(gray) / 255.0
        
        score = (text_density * 0.4 + color_complexity * 0.6)
        
        return {
            'score': score,
            'text_density': text_density,
            'color_complexity': color_complexity,
            'is_valid': score > 0.05
        }
    
    def _detect_headers(self, image: np.ndarray) -> List[Dict]:
        """헤더 감지"""
        headers = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        
        header_region = gray[:int(h * 0.1), :]
        
        _, binary = cv2.threshold(header_region, 200, 255, cv2.THRESH_BINARY_INV)
        text_density = np.sum(binary) / (header_region.shape[0] * header_region.shape[1])
        
        if text_density > 0.01:
            headers.append({
                'type': 'header',
                'bbox': [0, 0, w, int(h * 0.1)],
                'confidence': 0.8,
                'metadata': {'text_density': text_density}
            })
        
        return headers
    
    def _detect_pie_charts_ultra(self, image: np.ndarray) -> List[Dict]:
        """
        원그래프 감지 (초강력 + 컬러 검증)
        """
        pie_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # ⭐ 초강력 파라미터로 원 감지
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.pie_chart_params['minDist'],      # 250
            param1=self.pie_chart_params['param1'],
            param2=self.pie_chart_params['param2'],        # 80 (매우 엄격)
            minRadius=self.pie_chart_params['minRadius'],  # 100 (큰 원만)
            maxRadius=self.pie_chart_params['maxRadius']
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
                
                # ⭐ 1. 크기 필터링 (20,000 픽셀 이상)
                area = np.pi * r * r
                if area < self.min_region_size:
                    continue
                
                # ⭐ 2. 컬러 다양성 체크
                if len(roi.shape) == 3:
                    color_std = np.std(roi, axis=(0, 1)).mean()
                    if color_std < self.color_params['min_color_std']:  # 20 이상
                        continue
                    
                    # ⭐ 3. HSV 컬러 범위 체크
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    h_range = np.ptp(hsv[:, :, 0])  # Hue 범위
                    if h_range < self.color_params['min_hsv_range']:  # 30 이상
                        continue
                
                # ⭐ 4. 섹터 수 확인 (파이 차트는 최소 2개 섹터)
                num_sectors = self._count_sectors(roi)
                if num_sectors < self.color_params['min_sectors']:
                    continue
                
                # ⭐ 5. 원형도 체크 (면적 대비 둘레)
                contours, _ = cv2.findContours(
                    cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi, 50, 150),
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    perimeter = cv2.arcLength(largest_contour, True)
                    circularity = perimeter / np.sqrt(area)
                    
                    if circularity > self.color_params['max_circularity']:  # 4.0 이하
                        continue
                
                pie_charts.append({
                    'type': 'pie_chart',
                    'bbox': [int(x - r), int(y - r), int(2 * r), int(2 * r)],
                    'confidence': 0.90,  # 0.85 → 0.90 (높은 신뢰도)
                    'metadata': {
                        'radius': int(r),
                        'center': (int(x), int(y)),
                        'area': int(area),
                        'sectors': num_sectors,
                        'color_std': float(color_std) if len(roi.shape) == 3 else 0,
                        'circularity': float(circularity) if contours else 0
                    }
                })
        
        return pie_charts
    
    def _count_sectors(self, roi: np.ndarray) -> int:
        """
        원그래프 섹터 수 카운트
        """
        if len(roi.shape) != 3:
            return 0
        
        # HSV 변환
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Hue 히스토그램
        hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        
        # 피크 찾기 (섹터 수 추정)
        peaks = []
        threshold = np.max(hist) * 0.1
        
        for i in range(len(hist)):
            if hist[i] > threshold:
                if not peaks or i - peaks[-1] > 10:
                    peaks.append(i)
        
        return len(peaks)
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """막대그래프 감지"""
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rectangles = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            if area < 500 or area > image.shape[0] * image.shape[1] * 0.5:
                continue
            
            aspect_ratio = h / w if w > 0 else 0
            if 0.3 < aspect_ratio < 3.0:
                rectangles.append((x, y, w, h))
        
        if len(rectangles) >= 3:
            rectangles_sorted = sorted(rectangles, key=lambda r: r[0])
            
            for i in range(len(rectangles_sorted) - 2):
                r1, r2, r3 = rectangles_sorted[i:i+3]
                
                y_align = abs(r1[1] - r2[1]) < 50 and abs(r2[1] - r3[1]) < 50
                
                if y_align:
                    min_x = min(r1[0], r2[0], r3[0])
                    min_y = min(r1[1], r2[1], r3[1])
                    max_x = max(r1[0] + r1[2], r2[0] + r2[2], r3[0] + r3[2])
                    max_y = max(r1[1] + r1[3], r2[1] + r2[3], r3[1] + r3[3])
                    
                    w = max_x - min_x
                    h = max_y - min_y
                    
                    if w * h >= self.min_region_size:
                        bar_charts.append({
                            'type': 'bar_chart',
                            'bbox': [min_x, min_y, w, h],
                            'confidence': 0.80,
                            'metadata': {'num_bars': 3}
                        })
                    break
        
        return bar_charts
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """표 감지"""
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
        
        if lines is not None:
            h_lines = []
            v_lines = []
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                if abs(y2 - y1) < 10:
                    h_lines.append((min(x1, x2), max(x1, x2), y1))
                elif abs(x2 - x1) < 10:
                    v_lines.append((min(y1, y2), max(y1, y2), x1))
            
            if len(h_lines) >= 3 and len(v_lines) >= 3:
                min_x = min(line[2] for line in v_lines)
                max_x = max(line[2] for line in v_lines)
                min_y = min(line[2] for line in h_lines)
                max_y = max(line[2] for line in h_lines)
                
                w = max_x - min_x
                h = max_y - min_y
                
                if w * h >= self.min_region_size:
                    tables.append({
                        'type': 'table',
                        'bbox': [min_x, min_y, w, h],
                        'confidence': 0.75,
                        'metadata': {'rows': len(h_lines), 'cols': len(v_lines)}
                    })
        
        return tables
    
    def _detect_maps(self, image: np.ndarray) -> List[Dict]:
        """지도 감지"""
        maps = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            if area < self.min_region_size or area > image.shape[0] * image.shape[1] * 0.3:
                continue
            
            aspect_ratio = h / w if w > 0 else 0
            if 0.8 < aspect_ratio < 1.5:
                perimeter = cv2.arcLength(contour, True)
                complexity = perimeter / (2 * (w + h)) if (w + h) > 0 else 0
                
                if complexity > 1.2:
                    maps.append({
                        'type': 'map',
                        'bbox': [x, y, w, h],
                        'confidence': 0.70,
                        'metadata': {'complexity': complexity, 'area': area}
                    })
        
        return maps
    
    def _ultra_filter(self, regions: List[Dict], image: np.ndarray) -> List[Dict]:
        """
        초강력 필터링
        """
        filtered = []
        h, w = image.shape[:2]
        
        for region in regions:
            x, y, rw, rh = region['bbox']
            area = rw * rh
            
            # ⭐ 1. 크기 필터 (20,000 픽셀)
            if region['type'] != 'header' and area < self.min_region_size:
                continue
            
            # ⭐ 2. 경계 필터
            if x < 10 or y < 10 or x + rw > w - 10 or y + rh > h - 10:
                if region['type'] != 'header':
                    continue
            
            # ⭐ 3. 신뢰도 필터
            if region['confidence'] < self.confidence_threshold:
                continue
            
            # ⭐ 4. 종횡비 필터 (너무 긴 직사각형 제외)
            aspect_ratio = rh / rw if rw > 0 else 0
            if aspect_ratio > 5.0 or aspect_ratio < 0.2:
                if region['type'] not in ['header', 'bar_chart']:
                    continue
            
            filtered.append(region)
        
        return filtered
    
    def _smart_merge(self, regions: List[Dict]) -> List[Dict]:
        """지능형 병합"""
        if len(regions) <= 1:
            return regions
        
        merged = []
        used = set()
        
        for i, r1 in enumerate(regions):
            if i in used:
                continue
            
            candidates = [r1]
            
            for j, r2 in enumerate(regions):
                if j <= i or j in used:
                    continue
                
                if r1['type'] == r2['type']:
                    iou = self._calculate_iou(r1['bbox'], r2['bbox'])
                    distance = self._calculate_distance(r1['bbox'], r2['bbox'])
                    
                    if iou > 0.3 or distance < 50:
                        candidates.append(r2)
                        used.add(j)
            
            if len(candidates) > 1:
                merged_region = self._merge_regions(candidates)
                merged.append(merged_region)
            else:
                merged.append(r1)
            
            used.add(i)
        
        return merged
    
    def _merge_regions(self, regions: List[Dict]) -> Dict:
        """영역 병합"""
        min_x = min(r['bbox'][0] for r in regions)
        min_y = min(r['bbox'][1] for r in regions)
        max_x = max(r['bbox'][0] + r['bbox'][2] for r in regions)
        max_y = max(r['bbox'][1] + r['bbox'][3] for r in regions)
        
        avg_confidence = sum(r['confidence'] for r in regions) / len(regions)
        
        return {
            'type': regions[0]['type'],
            'bbox': [min_x, min_y, max_x - min_x, max_y - min_y],
            'confidence': avg_confidence,
            'metadata': {'merged_count': len(regions)}
        }
    
    def _remove_overlaps_ultra(self, regions: List[Dict]) -> List[Dict]:
        """중첩 제거 (IoU=0.6)"""
        if len(regions) <= 1:
            return regions
        
        sorted_regions = sorted(regions, key=lambda r: r['confidence'], reverse=True)
        
        keep = []
        
        for region in sorted_regions:
            overlap = False
            
            for kept_region in keep:
                iou = self._calculate_iou(region['bbox'], kept_region['bbox'])
                
                if iou > self.iou_threshold:  # 0.6
                    overlap = True
                    break
            
            if not overlap:
                keep.append(region)
        
        return keep
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """IoU 계산"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_distance(self, bbox1: List[int], bbox2: List[int]) -> float:
        """중심점 거리"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2
        
        return np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)


# 기존 클래스 교체
LayoutDetector = UltraLayoutDetector
SmartLayoutDetector = UltraLayoutDetector
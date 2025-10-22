"""
PRISM Phase 3.3 - Layout Detector v3.3 (Balanced Filtering)

✅ 핵심 개선:
1. Ultra Filtering 완화 (min_region_size: 20,000 → 5,000)
2. 큰 표 감지 허용 (max_table_size 대폭 증가)
3. 원그래프 감지 기준 완화
4. 일반 텍스트 영역 감지 추가
5. 경쟁사 수준 데이터 추출 목표

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.3 (Balanced Filtering)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LayoutDetectorV33:
    """
    Layout Detector v3.3 - Balanced Filtering
    
    Phase 3.3 핵심 밸런스:
    - ✅ min_region_size: 5,000px (20,000 → 5,000, 적절한 크기)
    - ✅ max_table_size: 10,000,000px (큰 표도 허용)
    - ✅ pie_min_radius: 50px (100 → 50, 작은 차트 감지)
    - ✅ 일반 텍스트 영역 감지 추가
    - ✅ 3-Stage 색상 검증 (5-Stage → 3-Stage, 적절한 검증)
    """
    
    def __init__(self):
        """초기화"""
        # ⭐ 기본 파라미터 (Balanced)
        self.min_region_size = 5000  # 20,000 → 5,000 (4배 완화)
        self.confidence_threshold = 0.70
        
        # ⭐ 원그래프 파라미터 (완화)
        self.pie_chart_params = {
            'dp': 1,
            'minDist': 200,      # 300 → 200
            'param1': 100,
            'param2': 60,        # 80 → 60 (완화)
            'minRadius': 50,     # 100 → 50 (작은 차트 감지)
            'maxRadius': 500
        }
        
        # ⭐ 색상 검증 파라미터 (3-Stage로 간소화)
        self.color_params = {
            'min_sectors': 2,           # Stage 1: 최소 섹터 수
            'min_hsv_range': 25,        # Stage 2: HSV 범위 (40 → 25)
            'min_saturation': 20,       # Stage 3: 평균 채도 (30 → 20)
        }
        
        # ⭐ 표 파라미터 (대폭 완화)
        self.table_params = {
            'min_width': 100,
            'max_width': 5000,      # 800 → 5000 (큰 표 허용)
            'min_height': 100,
            'max_height': 10000,    # 1000 → 10000 (큰 표 허용)
            'min_h_lines': 2,       # 3 → 2
            'min_v_lines': 2        # 3 → 2
        }
        
        # 막대그래프 파라미터
        self.bar_chart_params = {
            'min_bars': 2,          # 3 → 2
            'max_y_diff': 50,
            'min_bar_area': 500     # 1000 → 500
        }
        
        # ⭐ Map 파라미터 (적절한 수준)
        self.map_params = {
            'min_area': 30000,       # 100,000 → 30,000
            'min_complexity': 15,    # 30 → 15
            'max_circularity': 0.7,
            'aspect_ratio_min': 0.5,
            'aspect_ratio_max': 2.0
        }
        
        # ⭐ 일반 텍스트 영역 파라미터 (신규)
        self.text_region_params = {
            'min_text_density': 0.02,
            'max_text_density': 0.30,
            'min_area': 5000,
            'max_aspect_ratio': 5.0
        }
        
        logger.info("🚀 LayoutDetectorV33 초기화 완료 (Balanced Filtering)")
        logger.info(f"   - min_region_size: {self.min_region_size:,}px (완화)")
        logger.info(f"   - pie_min_radius: {self.pie_chart_params['minRadius']}px (작은 차트 감지)")
        logger.info(f"   - max_table_height: {self.table_params['max_height']:,}px (큰 표 허용)")
        logger.info(f"   - 3-Stage 색상 검증: ON (간소화)")
        logger.info(f"   - 일반 텍스트 영역 감지: ON (신규)")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        레이아웃 영역 감지 (Balanced Filtering)
        
        Args:
            image: 입력 이미지 (numpy array, BGR)
            page_num: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        regions = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} - Layout Detection v3.3 (Balanced)")
        logger.info(f"{'='*60}")
        
        # 1. 헤더 감지
        logger.info("Stage 1: 헤더 감지")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지 (Balanced + 3-Stage 검증)
        logger.info("Stage 2: 원그래프 감지 (3-Stage 검증)")
        pie_charts = self._detect_pie_charts_v33(image)
        logger.info(f"   → {len(pie_charts)}개 감지")
        regions.extend(pie_charts)
        
        # 3. 막대그래프 감지
        logger.info("Stage 3: 막대그래프 감지")
        bar_charts = self._detect_bar_charts(image)
        logger.info(f"   → {len(bar_charts)}개 감지")
        regions.extend(bar_charts)
        
        # 4. 표 감지 (큰 표 허용)
        logger.info("Stage 4: 표 감지 (큰 표 허용)")
        tables = self._detect_tables_v33(image)
        logger.info(f"   → {len(tables)}개 감지")
        regions.extend(tables)
        
        # 5. Map 감지 (적절한 필터)
        logger.info("Stage 5: Map 감지")
        maps = self._detect_maps(image)
        logger.info(f"   → {len(maps)}개 감지")
        regions.extend(maps)
        
        # ⭐ 6. 일반 텍스트 영역 감지 (신규)
        logger.info("Stage 6: 일반 텍스트 영역 감지 (신규)")
        text_regions = self._detect_text_regions(image)
        logger.info(f"   → {len(text_regions)}개 감지")
        regions.extend(text_regions)
        
        # 7. 중복 제거 및 병합
        logger.info("Stage 7: 중복 제거 및 병합")
        regions = self._merge_overlapping_regions(regions)
        logger.info(f"   → 최종 {len(regions)}개 영역")
        
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
    
    def _detect_pie_charts_v33(self, image: np.ndarray) -> List[Dict]:
        """
        원그래프 감지 v3.3 (Balanced + 3-Stage 검증)
        
        3-Stage 검증 (간소화):
        1. Sector Counting (최소 2개 섹터)
        2. HSV Range Analysis (색상 다양성, 완화)
        3. Saturation Check (평균 채도 > 20, 완화)
        """
        pie_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Hough Circle 감지
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            **self.pie_chart_params
        )
        
        if circles is None:
            return pie_charts
        
        circles = np.uint16(np.around(circles))
        
        for circle in circles[0, :]:
            x, y, r = int(circle[0]), int(circle[1]), int(circle[2])
            
            # Bbox 계산
            x1, y1 = max(0, x - r), max(0, y - r)
            x2, y2 = min(image.shape[1], x + r), min(image.shape[0], y + r)
            
            # 영역 크기 체크
            area = (x2 - x1) * (y2 - y1)
            if area < self.min_region_size:
                continue
            
            # ROI 추출
            roi = image[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            
            # ⭐ 3-Stage 색상 검증 (간소화)
            stage1_pass = self._check_sectors(roi)
            if not stage1_pass:
                continue
            
            stage2_pass = self._check_hsv_range(roi)
            if not stage2_pass:
                continue
            
            stage3_pass = self._check_saturation(roi)
            if not stage3_pass:
                continue
            
            # ✅ 모든 검증 통과
            pie_charts.append({
                'type': 'pie_chart',
                'bbox': [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                'confidence': 0.85,
                'metadata': {
                    'radius': int(r),
                    'center': [int(x), int(y)],
                    'area': int(area)
                }
            })
        
        return pie_charts
    
    def _check_sectors(self, roi: np.ndarray) -> bool:
        """Stage 1: 섹터 개수 체크"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        unique_hues = len(np.unique(hsv[:, :, 0]))
        return unique_hues >= self.color_params['min_sectors']
    
    def _check_hsv_range(self, roi: np.ndarray) -> bool:
        """Stage 2: HSV 범위 체크 (완화)"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_range = np.ptp(hsv[:, :, 0])
        return h_range >= self.color_params['min_hsv_range']
    
    def _check_saturation(self, roi: np.ndarray) -> bool:
        """Stage 3: 채도 체크 (완화)"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        avg_saturation = np.mean(hsv[:, :, 1])
        return avg_saturation >= self.color_params['min_saturation']
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """막대그래프 감지"""
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 막대 후보 찾기
        bars = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            if area < self.bar_chart_params['min_bar_area']:
                continue
            
            # 세로로 긴 형태 (막대)
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio > 1.5:
                bars.append({'x': x, 'y': y, 'w': w, 'h': h})
        
        # 막대들을 그룹화
        if len(bars) >= self.bar_chart_params['min_bars']:
            bars.sort(key=lambda b: b['y'])
            
            # Y 좌표 비슷한 막대들 그룹화
            groups = []
            current_group = [bars[0]]
            
            for bar in bars[1:]:
                if abs(bar['y'] - current_group[-1]['y']) <= self.bar_chart_params['max_y_diff']:
                    current_group.append(bar)
                else:
                    if len(current_group) >= self.bar_chart_params['min_bars']:
                        groups.append(current_group)
                    current_group = [bar]
            
            if len(current_group) >= self.bar_chart_params['min_bars']:
                groups.append(current_group)
            
            # 그룹을 막대그래프로 변환
            for group in groups:
                min_x = min(b['x'] for b in group)
                min_y = min(b['y'] for b in group)
                max_x = max(b['x'] + b['w'] for b in group)
                max_y = max(b['y'] + b['h'] for b in group)
                
                area = (max_x - min_x) * (max_y - min_y)
                if area >= self.min_region_size:
                    bar_charts.append({
                        'type': 'bar_chart',
                        'bbox': [int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)],
                        'confidence': 0.75,
                        'metadata': {'bar_count': len(group)}
                    })
        
        return bar_charts
    
    def _detect_tables_v33(self, image: np.ndarray) -> List[Dict]:
        """
        표 감지 v3.3 (큰 표 허용)
        
        개선사항:
        - max_width: 5000px (큰 표 허용)
        - max_height: 10000px (큰 표 허용)
        - min_lines: 2 (완화)
        """
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough Line 감지
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return tables
        
        # 수평/수직선 분류
        h_lines = []
        v_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 수평선
            if abs(y2 - y1) < 10:
                h_lines.append((x1, y1, x2, y2))
            
            # 수직선
            if abs(x2 - x1) < 10:
                v_lines.append((x1, y1, x2, y2))
        
        # 표 영역 찾기
        if len(h_lines) >= self.table_params['min_h_lines'] and len(v_lines) >= self.table_params['min_v_lines']:
            # Bounding box 계산
            all_x = [x for line in h_lines + v_lines for x in [line[0], line[2]]]
            all_y = [y for line in h_lines + v_lines for y in [line[1], line[3]]]
            
            x1, y1 = min(all_x), min(all_y)
            x2, y2 = max(all_x), max(all_y)
            w, h = x2 - x1, y2 - y1
            
            # ⭐ 크기 체크 (큰 표 허용)
            if (self.table_params['min_width'] <= w <= self.table_params['max_width'] and
                self.table_params['min_height'] <= h <= self.table_params['max_height']):
                
                area = w * h
                if area >= self.min_region_size:
                    tables.append({
                        'type': 'table',
                        'bbox': [int(x1), int(y1), int(w), int(h)],
                        'confidence': 0.80,
                        'metadata': {
                            'h_lines': len(h_lines),
                            'v_lines': len(v_lines),
                            'size': f'{w}x{h}'
                        }
                    })
                    logger.info(f"   ✅ 표 감지 성공: {w}x{h}px (큰 표 허용)")
        
        return tables
    
    def _detect_maps(self, image: np.ndarray) -> List[Dict]:
        """Map 감지 (적절한 필터링)"""
        maps = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 1. 최소 면적 체크
            if area < self.map_params['min_area']:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
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
            
            # ✅ 통과
            maps.append({
                'type': 'map',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': 0.75,
                'metadata': {
                    'area': int(area),
                    'complexity': float(complexity),
                    'circularity': float(circularity)
                }
            })
        
        return maps
    
    def _detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """
        일반 텍스트 영역 감지 (신규)
        
        차트/표가 아닌 일반 텍스트 블록을 감지합니다.
        """
        text_regions = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        
        # 헤더 제외 영역
        content_region = gray[int(h * 0.1):, :]
        
        # 텍스트 밀도 맵 생성 (100x100 픽셀 블록 단위)
        block_size = 100
        rows = content_region.shape[0] // block_size
        cols = content_region.shape[1] // block_size
        
        for i in range(rows):
            for j in range(cols):
                y1 = i * block_size
                y2 = (i + 1) * block_size
                x1 = j * block_size
                x2 = (j + 1) * block_size
                
                block = content_region[y1:y2, x1:x2]
                
                # 텍스트 밀도 계산
                _, binary = cv2.threshold(block, 200, 255, cv2.THRESH_BINARY_INV)
                text_density = np.sum(binary) / (block_size * block_size)
                
                # 적절한 텍스트 밀도 체크
                if (self.text_region_params['min_text_density'] <= text_density <= 
                    self.text_region_params['max_text_density']):
                    
                    # 절대 좌표로 변환
                    abs_y1 = y1 + int(h * 0.1)
                    area = block_size * block_size
                    
                    if area >= self.text_region_params['min_area']:
                        text_regions.append({
                            'type': 'text',
                            'bbox': [int(x1), int(abs_y1), block_size, block_size],
                            'confidence': 0.70,
                            'metadata': {'text_density': float(text_density)}
                        })
        
        return text_regions
    
    def _merge_overlapping_regions(self, regions: List[Dict]) -> List[Dict]:
        """
        중복되는 영역 병합
        
        IoU > 0.5인 영역들을 병합합니다.
        """
        if len(regions) <= 1:
            return regions
        
        merged = []
        used = set()
        
        for i, region1 in enumerate(regions):
            if i in used:
                continue
            
            bbox1 = region1['bbox']
            group = [region1]
            
            for j, region2 in enumerate(regions[i+1:], start=i+1):
                if j in used:
                    continue
                
                bbox2 = region2['bbox']
                iou = self._calculate_iou(bbox1, bbox2)
                
                if iou > 0.5:
                    group.append(region2)
                    used.add(j)
            
            # 그룹을 하나로 병합
            if len(group) == 1:
                merged.append(region1)
            else:
                merged_bbox = self._merge_bboxes([r['bbox'] for r in group])
                merged_type = max(set(r['type'] for r in group), 
                                key=lambda t: sum(1 for r in group if r['type'] == t))
                
                merged.append({
                    'type': merged_type,
                    'bbox': merged_bbox,
                    'confidence': max(r['confidence'] for r in group),
                    'metadata': {'merged_count': len(group)}
                })
        
        return merged
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """IoU 계산"""
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        
        x1_2, y1_2, w2, h2 = bbox2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        # 교집합
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # 합집합
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _merge_bboxes(self, bboxes: List[List[int]]) -> List[int]:
        """여러 bbox를 하나로 병합"""
        x1 = min(bbox[0] for bbox in bboxes)
        y1 = min(bbox[1] for bbox in bboxes)
        x2 = max(bbox[0] + bbox[2] for bbox in bboxes)
        y2 = max(bbox[1] + bbox[3] for bbox in bboxes)
        
        return [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]


# 테스트 코드
if __name__ == '__main__':
    import sys
    from PIL import Image
    
    if len(sys.argv) < 2:
        print("사용법: python core_layout_detector_v33_BALANCED.py <image_path>")
        sys.exit(1)
    
    # 이미지 로드
    img_path = sys.argv[1]
    pil_img = Image.open(img_path)
    img_array = np.array(pil_img)
    
    # BGR 변환
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 감지
    detector = LayoutDetectorV33()
    regions = detector.detect_regions(img_array, page_num=0)
    
    print(f"\n✅ 총 {len(regions)}개 영역 감지:")
    for i, region in enumerate(regions):
        print(f"{i+1}. {region['type']}: bbox={region['bbox']}, conf={region['confidence']:.2f}")
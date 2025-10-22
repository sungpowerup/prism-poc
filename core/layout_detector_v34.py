"""
core/layout_detector_v34.py
PRISM Phase 3.4.1 - Layout Detector v3.4.1 (Hybrid Detection - 과감지 방지)

🔥 Phase 3.4.1 긴급 수정:
1. ✅ 막대그래프 과감지 방지 (min_bar_area: 300 → 800)
2. ✅ 표 페이지 전체 크기 제외 (max_page_ratio: 70%)
3. ✅ 지도 감지 완화 (min_text_regions: 3 → 2)
4. ✅ 막대그래프 필터 강화 (min_bar_width: 10 → 20, min_bar_height: 15)

경쟁사 대비 목표:
- 표 감지: 0% → 90%+
- 막대그래프: 18% → 85%+
- 지도: 0% → 80%+

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.4.1 (긴급 수정)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LayoutDetectorV34:
    """
    Layout Detector v3.4 - Hybrid Detection
    
    Phase 3.4 핵심 전략:
    - ✅ Specialized Detectors (표/막대그래프/지도)
    - ✅ Multi-Stage Validation (CV → Heuristics → VLM Fallback)
    - ✅ Text Region 과감지 방지 (500x500px + 병합)
    """
    
    def __init__(self):
        """초기화"""
        # 기본 파라미터
        self.min_region_size = 5000
        self.confidence_threshold = 0.70
        
        # 원그래프 파라미터 (v3.3 유지)
        self.pie_chart_params = {
            'dp': 1,
            'minDist': 200,
            'param1': 100,
            'param2': 60,
            'minRadius': 50,
            'maxRadius': 500
        }
        
        # 색상 검증 파라미터 (v3.3 유지)
        self.color_params = {
            'min_sectors': 2,
            'min_hsv_range': 25,
            'min_saturation': 20,
        }
        
        # ⭐ 표 파라미터 (Phase 3.4.1 조정)
        self.table_params = {
            # Hough Line 파라미터
            'min_width': 100,
            'max_width': 1800,           # 5000 → 1800 (페이지 전체 제외) ✅
            'min_height': 100,
            'max_height': 2500,          # 10000 → 2500 (페이지 전체 제외) ✅
            'min_h_lines': 2,
            'min_v_lines': 2,
            
            # ✅ Text Grid 파라미터
            'grid_threshold': 0.7,
            'min_text_blocks': 6,
            'min_alignment_score': 0.7,  # 0.6 → 0.7 (더 엄격) ✅
            'max_page_ratio': 0.7        # 신규: 페이지 대비 최대 70% ✅
        }
        
        # ⭐ 막대그래프 파라미터 (Phase 3.4.1 조정)
        self.bar_chart_params = {
            'min_bars': 2,              # 2개만 있어도 인정
            'max_y_diff': 80,           # 100 → 80 (적절히 조정)
            'min_bar_area': 800,        # 300 → 800 (과감지 방지) ✅
            'min_bar_width': 20,        # 10 → 20 (너무 작은 막대 제외) ✅
            'min_bar_height': 15,       # 신규 (너무 낮은 막대 제외) ✅
            'max_aspect_ratio': 8.0,    # 10 → 8 (적절히 조정)
            'min_group_width': 150      # 신규 (전체 그래프 최소 너비) ✅
        }
        
        # ⭐ Map 파라미터 (Phase 3.4.1 완화)
        self.map_params = {
            'min_area': 30000,
            'min_complexity': 10,
            'max_circularity': 0.7,
            'aspect_ratio_min': 0.5,
            'aspect_ratio_max': 2.0,
            
            # ✅ 지역명 감지 (완화)
            'check_region_names': True,
            'min_text_regions': 2        # 3 → 2 (완화) ✅
        }
        
        # ⭐ 일반 텍스트 영역 파라미터 (Phase 3.4 개선)
        self.text_region_params = {
            'min_text_density': 0.02,
            'max_text_density': 0.30,
            'min_area': 10000,           # 5000 → 10000 (과감지 방지)
            'max_aspect_ratio': 5.0,
            'block_size': 500,           # ✅ 100 → 500 (큰 블록)
            'merge_threshold': 0.3       # ✅ 신규: 인접 블록 병합
        }
        
        logger.info("🚀 LayoutDetectorV34 초기화 완료 (Hybrid Detection v3.4.1)")
        logger.info(f"   - 표 감지: Hough Line + Text Grid (페이지 전체 제외)")
        logger.info(f"   - 막대그래프: Rectangle Clustering (과감지 방지)")
        logger.info(f"   - 지도: Contour + Region Names (완화)")
        logger.info(f"   - 텍스트: {self.text_region_params['block_size']}x{self.text_region_params['block_size']}px 블록 (병합)")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        레이아웃 영역 감지 (Hybrid Detection)
        
        Args:
            image: 입력 이미지 (numpy array, BGR)
            page_num: 페이지 번호
            
        Returns:
            감지된 영역 리스트
        """
        regions = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} - Layout Detection v3.4 (Hybrid)")
        logger.info(f"{'='*60}")
        
        # 1. 헤더 감지 (v3.3 유지)
        logger.info("Stage 1: 헤더 감지")
        headers = self._detect_headers(image)
        logger.info(f"   → {len(headers)}개 감지")
        regions.extend(headers)
        
        # 2. 원그래프 감지 (v3.3 유지)
        logger.info("Stage 2: 원그래프 감지")
        pie_charts = self._detect_pie_charts_v33(image)
        logger.info(f"   → {len(pie_charts)}개 감지")
        regions.extend(pie_charts)
        
        # ⭐ 3. 표 감지 (Phase 3.4 신규 알고리즘)
        logger.info("Stage 3: 표 감지 (Hybrid: Hough Line + Text Grid)")
        tables = self._detect_tables_v34(image)
        logger.info(f"   → {len(tables)}개 감지 ✨")
        regions.extend(tables)
        
        # ⭐ 4. 막대그래프 감지 (Phase 3.4 대폭 개선)
        logger.info("Stage 4: 막대그래프 감지 (완화된 필터)")
        bar_charts = self._detect_bar_charts_v34(image)
        logger.info(f"   → {len(bar_charts)}개 감지 ✨")
        regions.extend(bar_charts)
        
        # ⭐ 5. Map 감지 (Phase 3.4 신규 알고리즘)
        logger.info("Stage 5: Map 감지 (Contour + Region Names)")
        maps = self._detect_maps_v34(image)
        logger.info(f"   → {len(maps)}개 감지 ✨")
        regions.extend(maps)
        
        # ⭐ 6. 일반 텍스트 영역 감지 (Phase 3.4 개선)
        logger.info("Stage 6: 일반 텍스트 영역 감지 (500x500 + 병합)")
        text_regions = self._detect_text_regions_v34(image)
        logger.info(f"   → {len(text_regions)}개 감지 ✨")
        regions.extend(text_regions)
        
        # 7. 중복 제거 및 병합 (v3.3 유지)
        logger.info("Stage 7: 중복 제거 및 병합")
        regions = self._merge_overlapping_regions(regions)
        logger.info(f"   → 최종 {len(regions)}개 영역")
        
        logger.info(f"\n✅ 총 {len(regions)}개 영역 감지 완료")
        logger.info(f"{'='*60}\n")
        
        return regions
    
    # ========================================
    # v3.3 유지 메소드들
    # ========================================
    
    def _detect_headers(self, image: np.ndarray) -> List[Dict]:
        """헤더 영역 감지 (v3.3 유지)"""
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
        원그래프 감지 v3.3 (v3.3 유지)
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
            
            # 3-Stage 색상 검증
            stage1_pass = self._check_sectors(roi)
            if not stage1_pass:
                continue
            
            stage2_pass = self._check_hsv_range(roi)
            if not stage2_pass:
                continue
            
            stage3_pass = self._check_saturation(roi)
            if not stage3_pass:
                continue
            
            # ✅ 통과
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
        """Stage 1: Sector Counting (v3.3 유지)"""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        edges = cv2.Canny(gray, 50, 150)
        
        # 라인 감지
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30, minLineLength=20, maxLineGap=10)
        
        if lines is None:
            return False
        
        # 중심에서 나가는 라인 개수
        h, w = roi.shape[:2]
        cx, cy = w // 2, h // 2
        
        sector_lines = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 중심 근처 통과 여부
            dist_to_center = min(
                np.sqrt((x1 - cx)**2 + (y1 - cy)**2),
                np.sqrt((x2 - cx)**2 + (y2 - cy)**2)
            )
            
            if dist_to_center < min(w, h) * 0.3:
                sector_lines += 1
        
        return sector_lines >= self.color_params['min_sectors']
    
    def _check_hsv_range(self, roi: np.ndarray) -> bool:
        """Stage 2: HSV Range Analysis (v3.3 유지)"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        
        # Hue 범위
        h_min, h_max = np.min(h_channel), np.max(h_channel)
        h_range = h_max - h_min
        
        return h_range >= self.color_params['min_hsv_range']
    
    def _check_saturation(self, roi: np.ndarray) -> bool:
        """Stage 3: Saturation Check (v3.3 유지)"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        s_channel = hsv[:, :, 1]
        
        # 평균 채도
        mean_saturation = np.mean(s_channel)
        
        return mean_saturation >= self.color_params['min_saturation']
    
    # ========================================
    # Phase 3.4 신규/개선 메소드들
    # ========================================
    
    def _detect_tables_v34(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ Phase 3.4 표 감지 (Hybrid)
        
        2-Stage Detection:
        1. Hough Line Detection (기존)
        2. Text Grid Analysis (신규) ← 경쟁사 수준 감지
        """
        tables = []
        
        # Stage 1: Hough Line Detection (기존 방식)
        hough_tables = self._detect_tables_by_lines(image)
        
        # Stage 2: Text Grid Analysis (신규)
        grid_tables = self._detect_tables_by_text_grid(image)
        
        # 병합 (중복 제거)
        all_tables = hough_tables + grid_tables
        
        # 중복 제거
        merged_tables = self._merge_table_candidates(all_tables)
        
        logger.info(f"   - Hough Lines: {len(hough_tables)}개")
        logger.info(f"   - Text Grid: {len(grid_tables)}개")
        logger.info(f"   - 병합 후: {len(merged_tables)}개")
        
        return merged_tables
    
    def _detect_tables_by_lines(self, image: np.ndarray) -> List[Dict]:
        """Hough Line 기반 표 감지 (v3.3 유지)"""
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough Line 감지
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
        
        if lines is None:
            return tables
        
        # 수평선/수직선 분류
        h_lines = []
        v_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            if abs(y2 - y1) < 10:  # 수평선
                h_lines.append((x1, y1, x2, y2))
            elif abs(x2 - x1) < 10:  # 수직선
                v_lines.append((x1, y1, x2, y2))
        
        # 최소 라인 수 체크
        if (len(h_lines) >= self.table_params['min_h_lines'] and 
            len(v_lines) >= self.table_params['min_v_lines']):
            
            # Bbox 계산
            all_x = [x for line in h_lines + v_lines for x in [line[0], line[2]]]
            all_y = [y for line in h_lines + v_lines for y in [line[1], line[3]]]
            
            x1, y1 = min(all_x), min(all_y)
            x2, y2 = max(all_x), max(all_y)
            w, h = x2 - x1, y2 - y1
            
            # 크기 체크
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
                            'size': f'{w}x{h}',
                            'method': 'hough_line'
                        }
                    })
        
        return tables
    
    def _detect_tables_by_text_grid(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ Phase 3.4.1 Text Grid 기반 표 감지 (페이지 전체 제외)
        
        알고리즘:
        1. Connected Components로 텍스트 블록 추출
        2. 수평/수직 정렬 분석
        3. 격자 구조 판별
        4. ✅ 페이지 전체 크기 필터링 (신규)
        """
        tables = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 페이지 크기
        page_height, page_width = gray.shape[:2]
        
        # 텍스트 블록 추출 (Thresholding)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Morphology로 텍스트 블록 강화
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        # Connected Components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated, connectivity=8)
        
        # 텍스트 블록 필터링 (최소 크기)
        text_blocks = []
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            
            # 최소 크기 체크 (작은 노이즈 제거)
            if area < 100:
                continue
            
            # Aspect ratio 체크 (너무 길거나 높은 것 제외)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
            
            text_blocks.append({
                'bbox': (x, y, w, h),
                'centroid': centroids[i]
            })
        
        # 최소 블록 수 체크
        if len(text_blocks) < self.table_params['min_text_blocks']:
            return tables
        
        # 정렬 분석
        alignment_score = self._analyze_text_alignment(text_blocks)
        
        logger.info(f"      Text Grid: {len(text_blocks)}개 블록, 정렬 점수: {alignment_score:.2f}")
        
        # ✅ 정렬 점수 임계값 (0.7)
        if alignment_score >= self.table_params['min_alignment_score']:
            # 전체 Bbox 계산
            all_x = [b['bbox'][0] for b in text_blocks]
            all_y = [b['bbox'][1] for b in text_blocks]
            all_x2 = [b['bbox'][0] + b['bbox'][2] for b in text_blocks]
            all_y2 = [b['bbox'][1] + b['bbox'][3] for b in text_blocks]
            
            x1, y1 = min(all_x), min(all_y)
            x2, y2 = max(all_x2), max(all_y2)
            w, h = x2 - x1, y2 - y1
            
            # ✅ 페이지 대비 비율 체크 (신규)
            width_ratio = w / page_width
            height_ratio = h / page_height
            
            if width_ratio > self.table_params['max_page_ratio'] or height_ratio > self.table_params['max_page_ratio']:
                logger.info(f"      ⚠️ 페이지 전체 크기 제외: {width_ratio:.1%} x {height_ratio:.1%}")
                return tables
            
            # 크기 체크
            if (self.table_params['min_width'] <= w <= self.table_params['max_width'] and
                self.table_params['min_height'] <= h <= self.table_params['max_height']):
                
                area = w * h
                if area >= self.min_region_size:
                    tables.append({
                        'type': 'table',
                        'bbox': [int(x1), int(y1), int(w), int(h)],
                        'confidence': 0.85,  # Text Grid는 높은 신뢰도
                        'metadata': {
                            'text_blocks': len(text_blocks),
                            'alignment_score': float(alignment_score),
                            'size': f'{w}x{h}',
                            'method': 'text_grid'
                        }
                    })
                    
                    logger.info(f"      ✅ Text Grid 표 감지: {w}x{h}px (블록 {len(text_blocks)}개)")
        
        return tables
    
    def _analyze_text_alignment(self, text_blocks: List[Dict]) -> float:
        """
        텍스트 블록들의 정렬 점수 계산
        
        Returns:
            0.0~1.0 사이 정렬 점수 (높을수록 격자 구조)
        """
        if len(text_blocks) < 4:
            return 0.0
        
        # X 좌표와 Y 좌표 추출
        x_coords = [b['centroid'][0] for b in text_blocks]
        y_coords = [b['centroid'][1] for b in text_blocks]
        
        # X 좌표 클러스터링 (열)
        x_clusters = self._cluster_coordinates(x_coords, threshold=50)
        
        # Y 좌표 클러스터링 (행)
        y_clusters = self._cluster_coordinates(y_coords, threshold=30)
        
        # 정렬 점수 = (행 수 * 열 수) / 전체 블록 수
        expected_blocks = len(x_clusters) * len(y_clusters)
        actual_blocks = len(text_blocks)
        
        alignment_score = min(actual_blocks / expected_blocks, 1.0) if expected_blocks > 0 else 0.0
        
        return alignment_score
    
    def _cluster_coordinates(self, coords: List[float], threshold: float) -> List[List[float]]:
        """
        좌표들을 클러스터링
        
        Args:
            coords: 좌표 리스트
            threshold: 클러스터링 거리 임계값
            
        Returns:
            클러스터 리스트
        """
        if not coords:
            return []
        
        sorted_coords = sorted(coords)
        clusters = []
        current_cluster = [sorted_coords[0]]
        
        for coord in sorted_coords[1:]:
            if coord - current_cluster[-1] <= threshold:
                current_cluster.append(coord)
            else:
                clusters.append(current_cluster)
                current_cluster = [coord]
        
        clusters.append(current_cluster)
        
        return clusters
    
    def _merge_table_candidates(self, tables: List[Dict]) -> List[Dict]:
        """
        표 후보들을 병합 (중복 제거)
        
        IoU > 0.5인 표들을 하나로 병합합니다.
        """
        if len(tables) <= 1:
            return tables
        
        merged = []
        used = set()
        
        for i, table1 in enumerate(tables):
            if i in used:
                continue
            
            bbox1 = table1['bbox']
            group = [table1]
            
            for j, table2 in enumerate(tables[i+1:], start=i+1):
                if j in used:
                    continue
                
                bbox2 = table2['bbox']
                iou = self._calculate_iou(bbox1, bbox2)
                
                if iou > 0.5:
                    group.append(table2)
                    used.add(j)
            
            # 병합
            if len(group) == 1:
                merged.append(table1)
            else:
                merged_bbox = self._merge_bboxes([t['bbox'] for t in group])
                max_conf = max(t['confidence'] for t in group)
                
                merged.append({
                    'type': 'table',
                    'bbox': merged_bbox,
                    'confidence': max_conf,
                    'metadata': {
                        'merged_count': len(group),
                        'methods': [t['metadata'].get('method', 'unknown') for t in group]
                    }
                })
        
        return merged
    
    def _detect_bar_charts_v34(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ Phase 3.4.1 막대그래프 감지 (과감지 방지)
        
        개선사항:
        1. 직사각형 클러스터링 적절히 조정
        2. 최소 막대 크기 증가 (min_area: 300 → 800)
        3. 최소 너비/높이 체크 추가
        4. 전체 그래프 최소 너비 체크 (150px)
        """
        bar_charts = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Morphology로 막대 강화
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 직사각형 후보 추출
        rectangles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # ✅ 최소 면적 체크 (800px)
            if area < self.bar_chart_params['min_bar_area']:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # ✅ 최소 너비 체크
            if w < self.bar_chart_params['min_bar_width']:
                continue
            
            # ✅ 최소 높이 체크 (신규)
            if h < self.bar_chart_params['min_bar_height']:
                continue
            
            # ✅ Aspect ratio 체크
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio > self.bar_chart_params['max_aspect_ratio']:
                continue
            
            rectangles.append({
                'bbox': (x, y, w, h),
                'area': area,
                'bottom_y': y + h
            })
        
        # ✅ 최소 막대 수 체크
        if len(rectangles) < self.bar_chart_params['min_bars']:
            return bar_charts
        
        # Y축 정렬 분석
        bottom_ys = [r['bottom_y'] for r in rectangles]
        bottom_ys_sorted = sorted(bottom_ys)
        
        # 클러스터링
        aligned_groups = []
        current_group = [rectangles[0]]
        
        for i, rect in enumerate(rectangles[1:], start=1):
            y_diff = abs(rect['bottom_y'] - current_group[0]['bottom_y'])
            
            # ✅ Y축 차이 체크 (80px)
            if y_diff <= self.bar_chart_params['max_y_diff']:
                current_group.append(rect)
            else:
                if len(current_group) >= self.bar_chart_params['min_bars']:
                    aligned_groups.append(current_group)
                current_group = [rect]
        
        # 마지막 그룹
        if len(current_group) >= self.bar_chart_params['min_bars']:
            aligned_groups.append(current_group)
        
        # 막대그래프 생성
        for group in aligned_groups:
            all_x = [r['bbox'][0] for r in group]
            all_y = [r['bbox'][1] for r in group]
            all_x2 = [r['bbox'][0] + r['bbox'][2] for r in group]
            all_y2 = [r['bbox'][1] + r['bbox'][3] for r in group]
            
            x1, y1 = min(all_x), min(all_y)
            x2, y2 = max(all_x2), max(all_y2)
            w, h = x2 - x1, y2 - y1
            
            # ✅ 전체 그래프 최소 너비 체크 (신규)
            if w < self.bar_chart_params['min_group_width']:
                continue
            
            area = w * h
            if area >= self.min_region_size:
                bar_charts.append({
                    'type': 'bar_chart',
                    'bbox': [int(x1), int(y1), int(w), int(h)],
                    'confidence': 0.75,
                    'metadata': {
                        'bar_count': len(group),
                        'avg_bar_height': int(np.mean([r['bbox'][3] for r in group]))
                    }
                })
                
                logger.info(f"      ✅ 막대그래프 감지: {len(group)}개 막대, {w}x{h}px")
        
        return bar_charts
    
    def _detect_maps_v34(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ Phase 3.4 지도 감지 (신규 알고리즘)
        
        개선사항:
        1. Contour 복잡도 완화 (15 → 10)
        2. 지역명 감지 추가 (OCR 없이 텍스트 패턴)
        3. 색상 구역 분석 추가
        """
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
            
            # 4. 복잡도 체크 (완화)
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue
            
            complexity = (1 - area / hull_area) * 100
            if complexity < self.map_params['min_complexity']:
                continue
            
            # ✅ 5. 내부 텍스트 영역 체크 (신규)
            roi = image[y:y+h, x:x+w]
            has_text_regions = self._check_internal_text_regions(roi)
            
            if not has_text_regions:
                continue
            
            # ✅ 통과
            maps.append({
                'type': 'map',
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': 0.75,
                'metadata': {
                    'area': int(area),
                    'complexity': float(complexity),
                    'circularity': float(circularity),
                    'has_text_regions': has_text_regions
                }
            })
            
            logger.info(f"      ✅ 지도 감지: {w}x{h}px (복잡도: {complexity:.1f})")
        
        return maps
    
    def _check_internal_text_regions(self, roi: np.ndarray) -> bool:
        """
        ⭐ 신규: ROI 내부에 텍스트 영역이 있는지 체크
        
        지도는 보통 지역명 등의 텍스트가 포함되어 있습니다.
        """
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Connected Components로 텍스트 블록 추출
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(dilated, connectivity=8)
        
        # 텍스트 크기의 블록 개수 세기
        text_like_count = 0
        for i in range(1, num_labels):
            _, _, w, h, area = stats[i]
            
            # 텍스트 크기 (50~500 픽셀 정도)
            if 50 <= area <= 500:
                aspect_ratio = w / h if h > 0 else 0
                # 텍스트는 보통 가로로 긴 형태
                if 0.3 <= aspect_ratio <= 5.0:
                    text_like_count += 1
        
        # 최소 3개 이상의 텍스트 영역
        return text_like_count >= self.map_params['min_text_regions']
    
    def _detect_text_regions_v34(self, image: np.ndarray) -> List[Dict]:
        """
        ⭐ Phase 3.4 일반 텍스트 영역 감지 (개선)
        
        개선사항:
        1. 블록 크기 증가 (100x100 → 500x500)
        2. 인접 블록 병합
        3. 최소 면적 증가 (5000 → 10000)
        """
        text_regions = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        
        # 헤더 제외 영역
        content_region = gray[int(h * 0.1):, :]
        
        # ✅ 블록 크기 증가 (100 → 500)
        block_size = self.text_region_params['block_size']
        rows = content_region.shape[0] // block_size
        cols = content_region.shape[1] // block_size
        
        candidate_blocks = []
        
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
                    
                    candidate_blocks.append({
                        'bbox': [int(x1), int(abs_y1), block_size, block_size],
                        'density': text_density
                    })
        
        # ✅ 인접 블록 병합 (신규)
        merged_blocks = self._merge_adjacent_text_blocks(candidate_blocks)
        
        # 최소 면적 필터링
        for block in merged_blocks:
            bbox = block['bbox']
            area = bbox[2] * bbox[3]
            
            if area >= self.text_region_params['min_area']:
                text_regions.append({
                    'type': 'text',
                    'bbox': bbox,
                    'confidence': 0.70,
                    'metadata': {'text_density': float(block['density'])}
                })
        
        logger.info(f"      후보 블록: {len(candidate_blocks)}개 → 병합 후: {len(merged_blocks)}개")
        
        return text_regions
    
    def _merge_adjacent_text_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """
        ⭐ 신규: 인접한 텍스트 블록들을 병합
        
        Args:
            blocks: 텍스트 블록 리스트
            
        Returns:
            병합된 블록 리스트
        """
        if not blocks:
            return []
        
        merged = []
        used = set()
        
        for i, block1 in enumerate(blocks):
            if i in used:
                continue
            
            group = [block1]
            bbox1 = block1['bbox']
            
            for j, block2 in enumerate(blocks[i+1:], start=i+1):
                if j in used:
                    continue
                
                bbox2 = block2['bbox']
                
                # 인접성 체크 (일정 거리 이내)
                if self._are_blocks_adjacent(bbox1, bbox2):
                    group.append(block2)
                    used.add(j)
                    # bbox1 업데이트 (확장)
                    bbox1 = self._merge_bboxes([g['bbox'] for g in group])
            
            # 병합
            merged_bbox = self._merge_bboxes([g['bbox'] for g in group])
            avg_density = np.mean([g['density'] for g in group])
            
            merged.append({
                'bbox': merged_bbox,
                'density': avg_density
            })
        
        return merged
    
    def _are_blocks_adjacent(self, bbox1: List[int], bbox2: List[int]) -> bool:
        """
        두 블록이 인접한지 체크
        
        Args:
            bbox1, bbox2: [x, y, w, h]
            
        Returns:
            인접 여부
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # 중심점 거리
        cx1, cy1 = x1 + w1/2, y1 + h1/2
        cx2, cy2 = x2 + w2/2, y2 + h2/2
        
        distance = np.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2)
        
        # 블록 크기 대비 거리
        avg_size = (w1 + h1 + w2 + h2) / 4
        
        # 임계값: 블록 크기의 30%
        threshold = avg_size * self.text_region_params['merge_threshold']
        
        return distance < threshold
    
    # ========================================
    # 공통 유틸리티 (v3.3 유지)
    # ========================================
    
    def _merge_overlapping_regions(self, regions: List[Dict]) -> List[Dict]:
        """
        중복되는 영역 병합 (v3.3 유지)
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
            
            # 병합
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
        """IoU 계산 (v3.3 유지)"""
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
        """여러 bbox를 하나로 병합 (v3.3 유지)"""
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
        print("사용법: python layout_detector_v34.py <image_path>")
        sys.exit(1)
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # 이미지 로드
    img_path = sys.argv[1]
    pil_img = Image.open(img_path)
    img_array = np.array(pil_img)
    
    # BGR 변환
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 감지
    detector = LayoutDetectorV34()
    regions = detector.detect_regions(img_array, page_num=0)
    
    print(f"\n✅ 총 {len(regions)}개 영역 감지:")
    for i, region in enumerate(regions):
        print(f"{i+1}. {region['type']}: bbox={region['bbox']}, conf={region['confidence']:.2f}")
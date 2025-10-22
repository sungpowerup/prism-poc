"""
core/layout_detector_v35.py
PRISM Phase 3.5 - Layout Detector v3.5 (대규모 개선)

🔥 Phase 3.5 핵심 개선:
1. ✅ 표 감지 재설계 (Text Grid 단독 허용, 병합 로직 완화)
2. ✅ 원그래프 과감지 방지 강화 (minRadius: 120, 섹터 검증 강화)
3. ✅ 막대그래프 필터 완화 (min_bars: 2, min_group: 250×60)
4. ✅ 페이지별 하드코딩 제거 (동적 파라미터)

목표: 경쟁사 대비 85% 품질 달성

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-23
Version: 3.5
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LayoutDetectorV35:
    """
    Layout Detector v3.5 - 대규모 개선
    
    Phase 3.5 핵심 전략:
    - ✅ 표: Text Grid 단독 허용, 크기만 검증
    - ✅ 원그래프: minRadius 120, 섹터 3개 이상
    - ✅ 막대그래프: min_bars 2, 더 작은 그룹 허용
    - ✅ 동적 파라미터 (페이지 하드코딩 제거)
    """
    
    def __init__(self):
        """초기화"""
        # 기본 파라미터
        self.min_region_size = 5000
        self.confidence_threshold = 0.70
        
        # 원그래프 파라미터 (Phase 3.5 강화)
        self.pie_chart_params = {
            'dp': 1,
            'minDist': 200,
            'param1': 100,
            'param2': 70,        # 60 → 70 (강화)
            'minRadius': 120,    # 50 → 120 (작은 원 완전 제외) ✅
            'maxRadius': 500
        }
        
        # 색상 검증 파라미터 (Phase 3.5 강화)
        self.color_params = {
            'min_sectors': 3,       # 2 → 3 (최소 3개 섹터) ✅
            'min_hsv_range': 30,    # 25 → 30 (색상 다양성 강화)
            'min_saturation': 25,   # 20 → 25 (채도 강화)
        }
        
        # 표 파라미터 (Phase 3.5 재설계)
        self.table_params = {
            # Text Grid만으로도 표 인정 ✅
            'text_grid_only': True,
            
            # Text Grid 파라미터
            'grid_threshold': 0.7,
            'min_text_blocks': 6,
            'min_alignment_score': 0.7,
            
            # 크기 검증만 수행
            'min_page_ratio': 0.08,  # 0.10 → 0.08 (더 작은 표 허용) ✅
            'max_page_ratio': 0.70,  # 0.65 → 0.70 (더 큰 표 허용) ✅
            
            # Hough Line은 보조 (optional)
            'min_width': 100,
            'max_width': 1800,
            'min_height': 100,
            'max_height': 2500,
            'min_h_lines': 1,
            'min_v_lines': 1,
        }
        
        # 막대그래프 파라미터 (Phase 3.5 완화)
        self.bar_chart_params = {
            'min_bars': 2,              # 3 → 2 (2개 막대 허용) ✅
            'max_y_diff': 100,          # 80 → 100 (Y축 정렬 완화) ✅
            'min_bar_area': 1000,       # 1200 → 1000 (더 작은 막대 허용)
            'min_bar_width': 25,        # 30 → 25
            'min_bar_height': 20,       # 25 → 20
            'max_aspect_ratio': 8.0,
            'min_group_width': 250,     # 350 → 250 (더 작은 그룹 허용) ✅
            'min_group_height': 60      # 80 → 60 ✅
        }
        
        # 지도 파라미터
        self.map_params = {
            'min_complexity': 5.0,
            'max_circularity': 0.1,
            'min_aspect_ratio': 0.5,
            'max_aspect_ratio': 2.0,
            'min_text_regions': 3
        }
        
        logger.info("🚀 LayoutDetectorV35 초기화 완료 (Phase 3.5 대규모 개선)")
        logger.info("   - 표 감지: Text Grid 단독 허용, 크기만 검증 (8~70%)")
        logger.info("   - 막대그래프: 2개 이상, 그룹 250×60 이상")
        logger.info("   - 원그래프: minRadius 120, 섹터 3개 이상")
        logger.info("   - 지도: Contour + Region Names")
        logger.info("   - 텍스트: 비활성화")
        logger.info("   - 중복 제거: Overlap Ratio 80% 기준")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        이미지에서 모든 영역 감지 (Hybrid Detection)
        
        Args:
            image: 입력 이미지 (BGR)
            page_num: 페이지 번호 (0-based)
        
        Returns:
            감지된 영역 리스트
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} - Layout Detection v3.5 (Phase 3.5)")
        logger.info(f"{'='*60}")
        
        regions = []
        
        # Stage 1: 헤더 감지
        logger.info("Stage 1: 헤더 감지")
        headers = self._detect_headers(image)
        regions.extend(headers)
        logger.info(f"   → {len(headers)}개 감지")
        
        # Stage 2: 원그래프 감지 (Phase 3.5 강화)
        logger.info("Stage 2: 원그래프 감지 (Phase 3.5 강화)")
        pie_charts = self._detect_pie_charts(image, page_num)
        regions.extend(pie_charts)
        logger.info(f"   → {len(pie_charts)}개 감지")
        
        # Stage 3: 표 감지 (Phase 3.5 재설계)
        logger.info("Stage 3: 표 감지 (Phase 3.5 재설계: Text Grid 단독)")
        tables = self._detect_tables(image)
        regions.extend(tables)
        logger.info(f"   → {len(tables)}개 감지 ✨")
        
        # Stage 4: 막대그래프 감지 (Phase 3.5 완화)
        logger.info("Stage 4: 막대그래프 감지 (Phase 3.5 완화: 2개 이상)")
        bar_charts = self._detect_bar_charts(image)
        regions.extend(bar_charts)
        logger.info(f"   → {len(bar_charts)}개 감지 ✨")
        
        # Stage 5: Map 감지
        logger.info("Stage 5: Map 감지 (Contour + Region Names)")
        maps = self._detect_maps(image)
        regions.extend(maps)
        logger.info(f"   → {len(maps)}개 감지 ✨")
        
        # Stage 6: 일반 텍스트 영역 (비활성화)
        logger.info("Stage 6: 일반 텍스트 영역 감지 (비활성화)")
        logger.info(f"   → 0개 감지 (비활성화) ✨")
        
        # Stage 7: 중복 제거 및 병합
        logger.info("Stage 7: 중복 제거 및 병합 (표 내부 요소 제외)")
        regions = self._remove_duplicates(regions)
        logger.info(f"   → 최종 {len(regions)}개 영역")
        
        logger.info(f"\n✅ 총 {len(regions)}개 영역 감지 완료")
        logger.info(f"{'='*60}\n")
        
        return regions
    
    def _detect_headers(self, image: np.ndarray) -> List[Dict]:
        """헤더 감지 (상단 고정 영역)"""
        h, w = image.shape[:2]
        
        # 상단 8% 영역을 헤더로 간주
        header_height = int(h * 0.08)
        
        return [{
            'type': 'header',
            'bbox': [0, 0, w, header_height],
            'confidence': 0.95,
            'metadata': {'method': 'fixed_position'}
        }]
    
    def _detect_pie_charts(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        원그래프 감지 (Phase 3.5 강화)
        - minRadius: 120 (작은 원 완전 제외)
        - 섹터 3개 이상 필수
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        # Hough Circle Transform (Phase 3.5 강화 파라미터)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=self.pie_chart_params['dp'],
            minDist=self.pie_chart_params['minDist'],
            param1=self.pie_chart_params['param1'],
            param2=self.pie_chart_params['param2'],
            minRadius=self.pie_chart_params['minRadius'],  # 120
            maxRadius=self.pie_chart_params['maxRadius']
        )
        
        pie_charts = []
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                x, y, r = circle
                
                # ROI 추출
                x1 = max(0, x - r)
                y1 = max(0, y - r)
                x2 = min(image.shape[1], x + r)
                y2 = min(image.shape[0], y + r)
                
                roi = image[y1:y2, x1:x2]
                
                # 색상 검증 (Phase 3.5 강화)
                if self._verify_pie_chart_colors(roi):
                    pie_charts.append({
                        'type': 'pie_chart',
                        'bbox': [int(x - r), int(y - r), int(2 * r), int(2 * r)],
                        'confidence': 0.85,
                        'metadata': {
                            'center': (int(x), int(y)),
                            'radius': int(r),
                            'method': 'hough_circles'
                        }
                    })
        
        return pie_charts
    
    def _verify_pie_chart_colors(self, roi: np.ndarray) -> bool:
        """
        원그래프 색상 검증 (Phase 3.5 강화)
        - 최소 3개 섹터 필수
        """
        if roi.size == 0:
            return False
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        # 채도 검증 (Phase 3.5 강화)
        mask = s > self.color_params['min_saturation']  # 25
        
        if np.sum(mask) < roi.size * 0.3:
            return False
        
        # HSV 범위 검증
        hue_range = np.max(h[mask]) - np.min(h[mask]) if np.sum(mask) > 0 else 0
        
        if hue_range < self.color_params['min_hsv_range']:  # 30
            return False
        
        # 섹터 개수 검증 (Phase 3.5 강화)
        unique_hues = len(np.unique(h[mask] // 15))  # 15도 단위
        
        if unique_hues < self.color_params['min_sectors']:  # 3개 이상
            return False
        
        return True
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """
        표 감지 (Phase 3.5 재설계)
        
        핵심 개선:
        1. Text Grid만으로도 표 인정
        2. 크기 검증만 수행 (8~70%)
        3. 병합 로직 단순화
        """
        h, w = image.shape[:2]
        page_area = h * w
        
        tables = []
        
        # Text Grid 분석
        text_grid_tables = self._detect_tables_text_grid(image)
        
        logger.info(f"   - Text Grid: {len(text_grid_tables)}개")
        
        # Phase 3.5: Text Grid 결과를 크기만 검증하고 바로 사용
        for table in text_grid_tables:
            x, y, w_box, h_box = table['bbox']
            table_area = w_box * h_box
            ratio = table_area / page_area
            
            # 크기 검증
            if (self.table_params['min_page_ratio'] <= ratio <= 
                self.table_params['max_page_ratio']):
                tables.append(table)
        
        logger.info(f"   - 크기 필터 후: {len(tables)}개")
        logger.info(f"   → 최종 {len(tables)}개 감지 ✨")
        
        return tables
    
    def _detect_tables_text_grid(self, image: np.ndarray) -> List[Dict]:
        """
        Text Grid 기반 표 감지
        
        Returns:
            감지된 표 리스트
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # MSER로 텍스트 블록 감지
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        # 텍스트 블록 좌표
        text_blocks = []
        for region in regions:
            if len(region) < 10:
                continue
            
            x, y, w, h = cv2.boundingRect(region)
            
            # 너무 작거나 큰 블록 제외
            if w < 10 or h < 10 or w > 500 or h > 100:
                continue
            
            text_blocks.append((x, y, w, h))
        
        if len(text_blocks) < self.table_params['min_text_blocks']:
            return []
        
        logger.info(f"       Text Grid: {len(text_blocks)}개 블록, 정렬 점수: {self._calculate_alignment_score(text_blocks):.2f}")
        
        # 정렬 점수 계산
        alignment_score = self._calculate_alignment_score(text_blocks)
        
        if alignment_score < self.table_params['min_alignment_score']:
            return []
        
        # 전체 영역 계산
        if not text_blocks:
            return []
        
        min_x = min(x for x, y, w, h in text_blocks)
        min_y = min(y for x, y, w, h in text_blocks)
        max_x = max(x + w for x, y, w, h in text_blocks)
        max_y = max(y + h for x, y, w, h in text_blocks)
        
        return [{
            'type': 'table',
            'bbox': [min_x, min_y, max_x - min_x, max_y - min_y],
            'confidence': 0.80,
            'metadata': {
                'method': 'text_grid',
                'alignment_score': alignment_score,
                'text_blocks': len(text_blocks)
            }
        }]
    
    def _calculate_alignment_score(self, blocks: List[Tuple[int, int, int, int]]) -> float:
        """텍스트 블록 정렬 점수 계산"""
        if len(blocks) < 2:
            return 0.0
        
        # Y좌표 그룹화 (행 감지)
        y_coords = sorted([y for x, y, w, h in blocks])
        y_groups = []
        current_group = [y_coords[0]]
        
        for y in y_coords[1:]:
            if abs(y - current_group[-1]) < 20:
                current_group.append(y)
            else:
                y_groups.append(current_group)
                current_group = [y]
        
        if current_group:
            y_groups.append(current_group)
        
        # X좌표 그룹화 (열 감지)
        x_coords = sorted([x for x, y, w, h in blocks])
        x_groups = []
        current_group = [x_coords[0]]
        
        for x in x_coords[1:]:
            if abs(x - current_group[-1]) < 20:
                current_group.append(x)
            else:
                x_groups.append(current_group)
                current_group = [x]
        
        if current_group:
            x_groups.append(current_group)
        
        # 정렬 점수 = (행 수 + 열 수) / 블록 수
        score = (len(y_groups) + len(x_groups)) / len(blocks)
        
        return min(score, 1.0)
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """
        막대그래프 감지 (Phase 3.5 완화)
        - min_bars: 2 (2개 막대 허용)
        - min_group: (250, 60)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 사각형 후보
        rectangles = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # 막대 필터 (Phase 3.5 완화)
            if (area < self.bar_chart_params['min_bar_area'] or
                w < self.bar_chart_params['min_bar_width'] or
                h < self.bar_chart_params['min_bar_height']):
                continue
            
            aspect_ratio = float(w) / h if h > 0 else 0
            if aspect_ratio > self.bar_chart_params['max_aspect_ratio']:
                continue
            
            rectangles.append((x, y, w, h))
        
        # Y좌표 기준 클러스터링
        bar_groups = self._cluster_rectangles_by_y(rectangles)
        
        bar_charts = []
        
        for group in bar_groups:
            if len(group) < self.bar_chart_params['min_bars']:  # 2개 이상
                continue
            
            # 그룹 영역 계산
            min_x = min(x for x, y, w, h in group)
            min_y = min(y for x, y, w, h in group)
            max_x = max(x + w for x, y, w, h in group)
            max_y = max(y + h for x, y, w, h in group)
            
            group_w = max_x - min_x
            group_h = max_y - min_y
            
            # 그룹 크기 검증 (Phase 3.5 완화)
            if (group_w < self.bar_chart_params['min_group_width'] or  # 250
                group_h < self.bar_chart_params['min_group_height']):  # 60
                continue
            
            logger.info(f"       ✅ 막대그래프 감지: {len(group)}개 막대, {group_w}x{group_h}px")
            
            bar_charts.append({
                'type': 'bar_chart',
                'bbox': [min_x, min_y, group_w, group_h],
                'confidence': 0.75,
                'metadata': {
                    'num_bars': len(group),
                    'method': 'rectangle_clustering'
                }
            })
        
        return bar_charts
    
    def _cluster_rectangles_by_y(self, rectangles: List[Tuple[int, int, int, int]]) -> List[List[Tuple[int, int, int, int]]]:
        """Y좌표 기준으로 사각형 클러스터링 (Phase 3.5 완화)"""
        if not rectangles:
            return []
        
        # Y좌표 중심 기준 정렬
        sorted_rects = sorted(rectangles, key=lambda r: r[1] + r[3] // 2)
        
        clusters = []
        current_cluster = [sorted_rects[0]]
        
        for rect in sorted_rects[1:]:
            y_center = rect[1] + rect[3] // 2
            prev_y_center = current_cluster[-1][1] + current_cluster[-1][3] // 2
            
            # Y축 정렬 허용 오차 (Phase 3.5 완화: 100)
            if abs(y_center - prev_y_center) < self.bar_chart_params['max_y_diff']:
                current_cluster.append(rect)
            else:
                clusters.append(current_cluster)
                current_cluster = [rect]
        
        if current_cluster:
            clusters.append(current_cluster)
        
        return clusters
    
    def _detect_maps(self, image: np.ndarray) -> List[Dict]:
        """지도 감지 (Contour 기반)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        maps = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            if area < 50000:
                continue
            
            # 복잡도 계산
            perimeter = cv2.arcLength(cnt, True)
            complexity = perimeter ** 2 / area if area > 0 else 0
            
            if complexity < self.map_params['min_complexity']:
                continue
            
            # 원형도 계산
            circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
            
            if circularity > self.map_params['max_circularity']:
                continue
            
            # BBox 계산
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            if not (self.map_params['min_aspect_ratio'] <= 
                   aspect_ratio <= 
                   self.map_params['max_aspect_ratio']):
                continue
            
            # 내부 텍스트 영역 검출
            roi = image[y:y+h, x:x+w]
            text_regions = self._count_text_regions(roi)
            
            if text_regions < self.map_params['min_text_regions']:
                continue
            
            maps.append({
                'type': 'map',
                'bbox': [x, y, w, h],
                'confidence': 0.70,
                'metadata': {
                    'complexity': complexity,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio,
                    'text_regions': text_regions
                }
            })
        
        return maps
    
    def _count_text_regions(self, roi: np.ndarray) -> int:
        """ROI 내부의 텍스트 영역 개수 추정"""
        if roi.size == 0:
            return 0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # MSER로 텍스트 영역 감지
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        return len(regions)
    
    def _remove_duplicates(self, regions: List[Dict]) -> List[Dict]:
        """중복 영역 제거 (IoU 기반)"""
        if len(regions) <= 1:
            return regions
        
        # 신뢰도 기준 정렬
        sorted_regions = sorted(regions, key=lambda r: r['confidence'], reverse=True)
        
        final_regions = []
        
        for region in sorted_regions:
            # 기존 영역과 겹침 확인
            is_duplicate = False
            
            for existing in final_regions:
                overlap = self._calculate_overlap(region['bbox'], existing['bbox'])
                
                # 80% 이상 겹치면 중복
                if overlap > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final_regions.append(region)
        
        return final_regions
    
    def _calculate_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
        """두 BBox의 겹침 비율 계산 (IoU)"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # 교집합 계산
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # 합집합 계산
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

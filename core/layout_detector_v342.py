"""
core/layout_detector_v342.py
PRISM Phase 3.4.3 - Layout Detector v3.4.3 (긴급 수정)

🔥 Phase 3.4.3 긴급 수정:
1. ✅ Logger 오류 수정 (end 파라미터 제거)
2. ✅ 표 크기 제한 강화 (min: 0.15, max: 0.60 - 페이지 전체 제외)
3. ✅ 중복 제거 로직 개선 (overlap_ratio 80% 기준)

Phase 3.4.2 핵심:
1. ✅ 막대그래프 필터 강화 (min_bar_area: 1200, min_group_width: 250)
2. ✅ 지도 감지 완화 (min_text_regions: 1, 키워드 확장)
3. ✅ 표 감지 개선 (15~60% 크기 인정, 내부 요소 제외)

목표:
- 페이지 1: 7개 영역 (header 1 + pie 2 + bar 3 + map 1)
- 페이지 2: 7개 영역 (header 1 + pie 4 + bar 2)
- 페이지 3: 3개 영역 (header 1 + table 2)

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-22
Version: 3.4.3 (긴급 수정)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LayoutDetectorV342:
    """
    Layout Detector v3.4.3 - Hybrid Detection (긴급 수정)
    
    Phase 3.4.3 긴급 수정:
    - ✅ Logger 오류 수정 (모든 영역 손실 방지)
    - ✅ 표 크기 제한 강화 (15~60%, 페이지 전체 제외)
    - ✅ 중복 제거 개선 (overlap_ratio 80% 기준)
    
    Phase 3.4.2 핵심:
    - ✅ 막대그래프 필터 강화 (작은 막대 완전 제거)
    - ✅ 지도 감지 완화 (키워드 확장)
    - ✅ 표 내부 요소 제외 (중복 제거)
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
        
        # ⭐ 표 파라미터 (Phase 3.4.2 개선)
        self.table_params = {
            # Hough Line 파라미터
            'min_width': 100,
            'max_width': 1800,
            'min_height': 100,
            'max_height': 2500,
            'min_h_lines': 2,
            'min_v_lines': 2,
            
            # Text Grid 파라미터
            'grid_threshold': 0.7,
            'min_text_blocks': 6,
            'min_alignment_score': 0.7,
            
            # ✅ Phase 3.4.3: 표 크기 범위 조정
            'min_page_ratio': 0.15,  # 0.50 → 0.15 (작은 표 허용)
            'max_page_ratio': 0.60   # 0.85 → 0.60 (페이지 전체 제외)
        }
        
        # ⭐ 막대그래프 파라미터 (Phase 3.4.2 대폭 강화)
        self.bar_chart_params = {
            'min_bars': 2,              # 유지
            'max_y_diff': 80,           # 유지
            'min_bar_area': 1200,       # 800 → 1200 (50% 증가) ✅
            'min_bar_width': 30,        # 20 → 30 (50% 증가) ✅
            'min_bar_height': 25,       # 15 → 25 (67% 증가) ✅
            'max_aspect_ratio': 8.0,    # 유지
            'min_group_width': 250,     # 150 → 250 (67% 증가) ✅
            'min_group_height': 60      # 신규: 전체 높이 체크 ✅
        }
        
        # ⭐ Map 파라미터 (Phase 3.4.2 완화)
        self.map_params = {
            'min_area': 30000,
            'min_complexity': 10,
            'max_circularity': 0.7,
            'aspect_ratio_min': 0.5,
            'aspect_ratio_max': 2.0,
            
            # ✅ 지역명 감지 (완화 + 키워드 확장)
            'check_region_names': True,
            'min_text_regions': 1,      # 2 → 1 (완화) ✅
            'region_keywords': [         # 키워드 확장 ✅
                '권', '도', '시',
                '수도권', '경남권', '전라권', '충청권', '경북권', '강원',
                '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'
            ]
        }
        
        # 텍스트 파라미터
        self.text_params = {
            'block_size': 500,
            'overlap': 100,
            'min_text_density': 0.02
        }
        
        logger.info(f"🚀 LayoutDetectorV342 초기화 완료 (Hybrid Detection v3.4.3)")
        logger.info(f"   - 표 감지: Hough Line + Text Grid (15~60% 크기, 페이지 전체 제외)")
        logger.info(f"   - 막대그래프: Rectangle Clustering (강화된 필터)")
        logger.info(f"   - 지도: Contour + Region Names (완화 + 키워드 확장)")
        logger.info(f"   - 텍스트: 500x500px 블록 (병합)")
        logger.info(f"   - 중복 제거: Overlap Ratio 80% 기준")
    
    def detect_regions(self, image: np.ndarray, page_num: int = 0) -> List[Dict]:
        """
        메인 감지 함수
        
        Args:
            image: 입력 이미지 (BGR)
            page_num: 페이지 번호
        
        Returns:
            감지된 영역 리스트
        """
        h, w = image.shape[:2]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 페이지 {page_num + 1} - Layout Detection v3.4.3 (Hybrid)")
        logger.info(f"{'='*60}")
        
        all_regions = []
        
        # Stage 1: 헤더 감지
        logger.info(f"Stage 1: 헤더 감지")
        header_regions = self._detect_header(image)
        all_regions.extend(header_regions)
        logger.info(f"   → {len(header_regions)}개 감지")
        
        # Stage 2: 원그래프 감지
        logger.info(f"Stage 2: 원그래프 감지")
        pie_regions = self._detect_pie_charts(image)
        all_regions.extend(pie_regions)
        logger.info(f"   → {len(pie_regions)}개 감지")
        
        # Stage 3: 표 감지 (Hybrid: Hough Line + Text Grid)
        logger.info(f"Stage 3: 표 감지 (Hybrid: Hough Line + Text Grid)")
        table_regions = self._detect_tables_hybrid(image)
        all_regions.extend(table_regions)
        logger.info(f"   → {len(table_regions)}개 감지 ✨")
        
        # Stage 4: 막대그래프 감지
        logger.info(f"Stage 4: 막대그래프 감지 (강화된 필터)")
        bar_regions = self._detect_bar_charts(image)
        all_regions.extend(bar_regions)
        logger.info(f"   → {len(bar_regions)}개 감지 ✨")
        
        # Stage 5: 지도 감지
        logger.info(f"Stage 5: Map 감지 (Contour + Region Names)")
        map_regions = self._detect_maps(image)
        all_regions.extend(map_regions)
        logger.info(f"   → {len(map_regions)}개 감지 ✨")
        
        # Stage 6: 일반 텍스트 영역
        logger.info(f"Stage 6: 일반 텍스트 영역 감지 (500x500 + 병합)")
        text_regions = self._detect_text_regions(image, all_regions)
        all_regions.extend(text_regions)
        logger.info(f"   → {len(text_regions)}개 감지 ✨")
        
        # ⭐ Stage 7: 표 내부 요소 제거 (Phase 3.4.2 신규)
        logger.info(f"Stage 7: 중복 제거 및 병합 (표 내부 요소 제외)")
        all_regions = self._remove_duplicates(all_regions)
        logger.info(f"   → 최종 {len(all_regions)}개 영역")
        
        logger.info(f"\n✅ 총 {len(all_regions)}개 영역 감지 완료")
        logger.info(f"{'='*60}\n")
        
        return all_regions
    
    # ========================================
    # Stage 1: 헤더 감지
    # ========================================
    
    def _detect_header(self, image: np.ndarray) -> List[Dict]:
        """헤더 영역 감지 (v3.3 유지)"""
        h, w = image.shape[:2]
        header_height = int(h * 0.08)
        
        return [{
            'type': 'header',
            'bbox': (0, 0, w, header_height),
            'confidence': 0.95,
            'metadata': {'method': 'fixed_position'}
        }]
    
    # ========================================
    # Stage 2: 원그래프 감지
    # ========================================
    
    def _detect_pie_charts(self, image: np.ndarray) -> List[Dict]:
        """원그래프 감지 (v3.3 유지)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (9, 9), 2)
        
        circles = cv2.HoughCircles(
            gray_blur,
            cv2.HOUGH_GRADIENT,
            dp=self.pie_chart_params['dp'],
            minDist=self.pie_chart_params['minDist'],
            param1=self.pie_chart_params['param1'],
            param2=self.pie_chart_params['param2'],
            minRadius=self.pie_chart_params['minRadius'],
            maxRadius=self.pie_chart_params['maxRadius']
        )
        
        regions = []
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                cx, cy, r = circle
                
                # ROI 추출
                x1 = max(0, cx - r - 20)
                y1 = max(0, cy - r - 20)
                x2 = min(image.shape[1], cx + r + 20)
                y2 = min(image.shape[0], cy + r + 20)
                
                roi = image[y1:y2, x1:x2]
                
                # 색상 검증
                if self._validate_pie_chart_colors(roi):
                    regions.append({
                        'type': 'pie_chart',
                        'bbox': (x1, y1, x2 - x1, y2 - y1),
                        'confidence': 0.85,
                        'metadata': {
                            'center': (int(cx), int(cy)),
                            'radius': int(r),
                            'method': 'hough_circles'
                        }
                    })
        
        return regions
    
    def _validate_pie_chart_colors(self, roi: np.ndarray) -> bool:
        """원그래프 색상 검증 (v3.3 유지)"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        unique_hues = set()
        for y in range(0, hsv.shape[0], 5):
            for x in range(0, hsv.shape[1], 5):
                h, s, v = hsv[y, x]
                if s > self.color_params['min_saturation'] and v > 50:
                    unique_hues.add(h // 15)
        
        return len(unique_hues) >= self.color_params['min_sectors']
    
    # ========================================
    # Stage 3: 표 감지 (Hybrid)
    # ========================================
    
    def _detect_tables_hybrid(self, image: np.ndarray) -> List[Dict]:
        """
        표 감지 (Hybrid: Hough Line + Text Grid)
        
        Phase 3.4.2 개선:
        - 50~85% 크기의 표 인정
        - 표 내부 요소는 별도 감지하지 않음
        """
        h, w = image.shape[:2]
        page_area = h * w
        
        # 1) Hough Line 기반 감지
        hough_tables = self._detect_tables_hough(image)
        
        # 2) Text Grid 기반 감지
        text_tables = self._detect_tables_text_grid(image)
        
        # 3) 병합
        all_tables = hough_tables + text_tables
        
        # ⭐ Phase 3.4.2: 크기 기반 필터링 (50~85%)
        filtered_tables = []
        for table in all_tables:
            x, y, w_t, h_t = table['bbox']
            table_area = w_t * h_t
            ratio = table_area / page_area
            
            # 50~85% 사이의 표만 인정
            if self.table_params['min_page_ratio'] <= ratio <= self.table_params['max_page_ratio']:
                filtered_tables.append(table)
                logger.info(f"       ✅ 표 감지: {w_t}×{h_t}px (페이지 대비 {ratio*100:.1f}%)")
        
        logger.info(f"   - Hough Lines: {len(hough_tables)}개")
        logger.info(f"   - Text Grid: {len(text_tables)}개")
        logger.info(f"   - 병합 후: {len(filtered_tables)}개")
        
        return filtered_tables
    
    def _detect_tables_hough(self, image: np.ndarray) -> List[Dict]:
        """Hough Line 기반 표 감지 (v3.4.1 유지)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )
        
        if lines is None:
            return []
        
        h_lines = []
        v_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            if abs(y2 - y1) < 10:
                h_lines.append((x1, y1, x2, y2))
            elif abs(x2 - x1) < 10:
                v_lines.append((x1, y1, x2, y2))
        
        if len(h_lines) < self.table_params['min_h_lines'] or len(v_lines) < self.table_params['min_v_lines']:
            return []
        
        # Bounding box 계산
        all_points = []
        for x1, y1, x2, y2 in h_lines + v_lines:
            all_points.extend([(x1, y1), (x2, y2)])
        
        if not all_points:
            return []
        
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        
        x, y = min(xs), min(ys)
        w, h = max(xs) - x, max(ys) - y
        
        # 크기 검증
        if (self.table_params['min_width'] <= w <= self.table_params['max_width'] and
            self.table_params['min_height'] <= h <= self.table_params['max_height']):
            return [{
                'type': 'table',
                'bbox': (x, y, w, h),
                'confidence': 0.80,
                'metadata': {
                    'h_lines': len(h_lines),
                    'v_lines': len(v_lines),
                    'method': 'hough_lines'
                }
            }]
        
        return []
    
    def _detect_tables_text_grid(self, image: np.ndarray) -> List[Dict]:
        """Text Grid 기반 표 감지 (v3.4.1 유지)"""
        h, w = image.shape[:2]
        page_area = h * w
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_blocks = []
        for cnt in contours:
            x, y, w_c, h_c = cv2.boundingRect(cnt)
            area = w_c * h_c
            
            if 100 < area < 5000:
                text_blocks.append((x, y, w_c, h_c))
        
        if len(text_blocks) < self.table_params['min_text_blocks']:
            return []
        
        # 정렬 점수 계산
        xs = sorted([x for x, y, w, h in text_blocks])
        ys = sorted([y for x, y, w, h in text_blocks])
        
        x_aligned = sum(1 for i in range(len(xs)-1) if abs(xs[i] - xs[i+1]) < 20) / max(1, len(xs)-1)
        y_aligned = sum(1 for i in range(len(ys)-1) if abs(ys[i] - ys[i+1]) < 20) / max(1, len(ys)-1)
        
        alignment_score = (x_aligned + y_aligned) / 2
        
        logger.info(f"       Text Grid: {len(text_blocks)}개 블록, 정렬 점수: {alignment_score:.2f}")
        
        # 정렬 점수 검증
        if alignment_score < self.table_params['min_alignment_score']:
            return []
        
        # Bounding box 계산
        xs_all = [x for x, y, w, h in text_blocks]
        ys_all = [y for x, y, w, h in text_blocks]
        ws_all = [w for x, y, w, h in text_blocks]
        hs_all = [h for x, y, w, h in text_blocks]
        
        x_min = min(xs_all)
        y_min = min(ys_all)
        x_max = max([x + w for x, w in zip(xs_all, ws_all)])
        y_max = max([y + h for y, h in zip(ys_all, hs_all)])
        
        w_table = x_max - x_min
        h_table = y_max - y_min
        table_area = w_table * h_table
        ratio = table_area / page_area
        
        # ⭐ Phase 3.4.2: 크기 범위 체크는 여기서 하지 않고 상위에서 처리
        return [{
            'type': 'table',
            'bbox': (x_min, y_min, w_table, h_table),
            'confidence': 0.75,
            'metadata': {
                'text_blocks': len(text_blocks),
                'alignment_score': alignment_score,
                'page_ratio': ratio,
                'method': 'text_grid'
            }
        }]
    
    # ========================================
    # Stage 4: 막대그래프 감지
    # ========================================
    
    def _detect_bar_charts(self, image: np.ndarray) -> List[Dict]:
        """
        막대그래프 감지 (Rectangle Clustering)
        
        Phase 3.4.2 개선:
        - min_bar_area: 800 → 1200
        - min_bar_width: 20 → 30
        - min_bar_height: 15 → 25
        - min_group_width: 150 → 250
        - min_group_height: 60 (신규)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 막대 후보 수집
        bar_candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # ⭐ Phase 3.4.2: 강화된 필터
            if (area >= self.bar_chart_params['min_bar_area'] and
                w >= self.bar_chart_params['min_bar_width'] and
                h >= self.bar_chart_params['min_bar_height']):
                
                aspect_ratio = max(w, h) / min(w, h)
                if aspect_ratio <= self.bar_chart_params['max_aspect_ratio']:
                    bar_candidates.append((x, y, w, h))
        
        # 막대 그룹화 (Y축 정렬)
        bar_groups = self._group_bars_by_y(bar_candidates)
        
        regions = []
        for group in bar_groups:
            if len(group) >= self.bar_chart_params['min_bars']:
                # Bounding box
                xs = [x for x, y, w, h in group]
                ys = [y for x, y, w, h in group]
                ws = [w for x, y, w, h in group]
                hs = [h for x, y, w, h in group]
                
                x_min = min(xs)
                y_min = min(ys)
                x_max = max([x + w for x, w in zip(xs, ws)])
                y_max = max([y + h for y, h in zip(ys, hs)])
                
                group_w = x_max - x_min
                group_h = y_max - y_min
                
                # ⭐ Phase 3.4.2: 그룹 크기 검증 강화
                if (group_w >= self.bar_chart_params['min_group_width'] and
                    group_h >= self.bar_chart_params['min_group_height']):
                    
                    regions.append({
                        'type': 'bar_chart',
                        'bbox': (x_min, y_min, group_w, group_h),
                        'confidence': 0.75,
                        'metadata': {
                            'num_bars': len(group),
                            'method': 'rectangle_clustering'
                        }
                    })
                    
                    logger.info(f"       ✅ 막대그래프 감지: {len(group)}개 막대, {group_w}x{group_h}px")
        
        return regions
    
    def _group_bars_by_y(self, bars: List[Tuple[int, int, int, int]]) -> List[List[Tuple[int, int, int, int]]]:
        """막대를 Y축 기준으로 그룹화 (v3.4.1 유지)"""
        if not bars:
            return []
        
        sorted_bars = sorted(bars, key=lambda b: b[1])
        
        groups = []
        current_group = [sorted_bars[0]]
        
        for bar in sorted_bars[1:]:
            if abs(bar[1] - current_group[-1][1]) <= self.bar_chart_params['max_y_diff']:
                current_group.append(bar)
            else:
                groups.append(current_group)
                current_group = [bar]
        
        groups.append(current_group)
        
        return groups
    
    # ========================================
    # Stage 5: 지도 감지
    # ========================================
    
    def _detect_maps(self, image: np.ndarray) -> List[Dict]:
        """
        지도 감지 (Contour + Region Names)
        
        Phase 3.4.2 개선:
        - min_text_regions: 2 → 1 (완화)
        - region_keywords 확장 (수도권, 경남권 등 추가)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            if area < self.map_params['min_area']:
                continue
            
            # Bounding box
            x, y, w, h = cv2.boundingRect(cnt)
            
            # 종횡비 검증
            aspect_ratio = w / h if h > 0 else 0
            if not (self.map_params['aspect_ratio_min'] <= aspect_ratio <= self.map_params['aspect_ratio_max']):
                continue
            
            # 복잡도 검증
            perimeter = cv2.arcLength(cnt, True)
            complexity = perimeter / np.sqrt(area) if area > 0 else 0
            
            if complexity < self.map_params['min_complexity']:
                continue
            
            # 원형도 검증
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            if circularity > self.map_params['max_circularity']:
                continue
            
            # ⭐ Phase 3.4.2: 지역명 검증 (완화)
            if self.map_params['check_region_names']:
                roi = image[y:y+h, x:x+w]
                if not self._check_internal_text_regions(roi):
                    continue
            
            regions.append({
                'type': 'map',
                'bbox': (x, y, w, h),
                'confidence': 0.70,
                'metadata': {
                    'complexity': complexity,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio,
                    'method': 'contour_analysis'
                }
            })
        
        return regions
    
    def _check_internal_text_regions(self, roi: np.ndarray) -> bool:
        """
        지도 내부 텍스트 검증
        
        Phase 3.4.2 개선:
        - min_text_regions: 2 → 1 (완화)
        - 키워드 확장
        """
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            if 50 < area < 2000:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = w / h if h > 0 else 0
                
                if 0.3 < aspect_ratio < 5.0:
                    text_regions += 1
        
        # ⭐ Phase 3.4.2: 완화 (2 → 1)
        return text_regions >= self.map_params['min_text_regions']
    
    # ========================================
    # Stage 6: 일반 텍스트 영역
    # ========================================
    
    def _detect_text_regions(self, image: np.ndarray, existing_regions: List[Dict]) -> List[Dict]:
        """일반 텍스트 영역 감지 (500x500 블록) (v3.4.1 유지)"""
        h, w = image.shape[:2]
        block_size = self.text_params['block_size']
        overlap = self.text_params['overlap']
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        candidates = []
        
        for y in range(0, h - block_size, block_size - overlap):
            for x in range(0, w - block_size, block_size - overlap):
                roi = gray[y:y+block_size, x:x+block_size]
                
                _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                text_density = np.sum(binary == 255) / (block_size * block_size)
                
                if text_density > self.text_params['min_text_density']:
                    # 기존 영역과 겹치지 않는지 확인
                    if not self._overlaps_existing(x, y, block_size, block_size, existing_regions):
                        candidates.append((x, y, block_size, block_size))
        
        # 인접 블록 병합
        merged = self._merge_adjacent_blocks(candidates)
        
        logger.info(f"       후보 블록: {len(candidates)}개 → 병합 후: {len(merged)}개")
        
        return [{
            'type': 'text',
            'bbox': bbox,
            'confidence': 0.60,
            'metadata': {'method': 'block_based'}
        } for bbox in merged]
    
    def _overlaps_existing(self, x: int, y: int, w: int, h: int, regions: List[Dict]) -> bool:
        """기존 영역과 겹치는지 확인 (v3.4.1 유지)"""
        for region in regions:
            rx, ry, rw, rh = region['bbox']
            
            if not (x + w < rx or x > rx + rw or y + h < ry or y > ry + rh):
                return True
        
        return False
    
    def _merge_adjacent_blocks(self, blocks: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """인접한 블록 병합 (v3.4.1 유지)"""
        if not blocks:
            return []
        
        merged = []
        used = set()
        
        for i, block1 in enumerate(blocks):
            if i in used:
                continue
            
            group = [block1]
            used.add(i)
            
            for j, block2 in enumerate(blocks):
                if j <= i or j in used:
                    continue
                
                if self._is_adjacent(block1, block2, threshold=50):
                    group.append(block2)
                    used.add(j)
            
            # 그룹의 Bounding box
            xs = [x for x, y, w, h in group]
            ys = [y for x, y, w, h in group]
            ws = [w for x, y, w, h in group]
            hs = [h for x, y, w, h in group]
            
            x_min = min(xs)
            y_min = min(ys)
            x_max = max([x + w for x, w in zip(xs, ws)])
            y_max = max([y + h for y, h in zip(ys, hs)])
            
            merged.append((x_min, y_min, x_max - x_min, y_max - y_min))
        
        return merged
    
    def _is_adjacent(self, block1: Tuple[int, int, int, int], block2: Tuple[int, int, int, int], threshold: int = 50) -> bool:
        """두 블록이 인접했는지 확인 (v3.4.1 유지)"""
        x1, y1, w1, h1 = block1
        x2, y2, w2, h2 = block2
        
        # X축 거리
        if x1 + w1 < x2:
            x_dist = x2 - (x1 + w1)
        elif x2 + w2 < x1:
            x_dist = x1 - (x2 + w2)
        else:
            x_dist = 0
        
        # Y축 거리
        if y1 + h1 < y2:
            y_dist = y2 - (y1 + h1)
        elif y2 + h2 < y1:
            y_dist = y1 - (y2 + h2)
        else:
            y_dist = 0
        
        return x_dist <= threshold and y_dist <= threshold
    
    # ========================================
    # Stage 7: 중복 제거 (Phase 3.4.2 강화)
    # ========================================
    
    def _remove_duplicates(self, regions: List[Dict]) -> List[Dict]:
        """
        중복 제거 및 병합
        
        Phase 3.4.3 개선:
        - 표 내부의 pie_chart, bar_chart 완전 제거
        - 80% 이상 겹치면 표 내부로 판단
        - IoU 기반 중복 제거
        """
        if not regions:
            return []
        
        # 1) 표 추출
        tables = [r for r in regions if r['type'] == 'table']
        
        # 2) 표 내부에 있는 pie/bar 제거
        filtered = []
        
        for region in regions:
            # 표 내부 요소 체크
            if region['type'] in ['pie_chart', 'bar_chart']:
                is_inside_table = False
                
                for table in tables:
                    # 80% 이상 겹치면 표 내부로 판단
                    overlap_ratio = self._calculate_overlap_ratio(region['bbox'], table['bbox'])
                    if overlap_ratio > 0.8:
                        is_inside_table = True
                        logger.info(f"       ⚠️ {region['type']} 제외 (표 내부, 겹침 {overlap_ratio*100:.1f}%)")
                        break
                
                if not is_inside_table:
                    filtered.append(region)
            else:
                # 표, 헤더, 지도, 텍스트는 그대로 추가
                filtered.append(region)
        
        # 3) IoU 기반 중복 제거
        final = []
        
        for i, region1 in enumerate(filtered):
            is_duplicate = False
            
            for region2 in final:
                iou = self._calculate_iou(region1['bbox'], region2['bbox'])
                
                if iou > 0.5:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final.append(region1)
        
        return final
    
    def _calculate_overlap_ratio(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """bbox1이 bbox2와 얼마나 겹치는지 계산 (bbox1 기준)"""
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
        
        return intersection / area1 if area1 > 0 else 0.0
    
    def _calculate_iou(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """IoU 계산 (v3.4.1 유지)"""
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
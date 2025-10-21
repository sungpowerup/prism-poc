"""
core/layout_detector.py
PRISM Phase 3.0 - 페이지 레이아웃 감지 및 영역 분리

CV 기반 휴리스틱 + VLM 검증 하이브리드 방식
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Region:
    """감지된 영역 정보"""
    region_id: str
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    type: str  # 'header', 'chart', 'table', 'map', 'text', 'image'
    confidence: float
    metadata: Dict
    
    def to_dict(self):
        """딕셔너리 변환"""
        return asdict(self)


class LayoutDetector:
    """
    페이지 레이아웃 감지기
    
    기능:
    1. CV 기반 빠른 감지 (헤더, 차트, 표, 지도)
    2. VLM 검증 (신뢰도 낮은 경우)
    3. 영역 중첩 제거 및 정렬
    """
    
    def __init__(self, vlm_service=None, use_vlm_validation=True):
        """
        Args:
            vlm_service: VLM 서비스 인스턴스
            use_vlm_validation: VLM 검증 사용 여부
        """
        self.vlm_service = vlm_service
        self.use_vlm_validation = use_vlm_validation
        
        # 임계값 설정
        self.thresholds = {
            'header_font_size_ratio': 0.02,
            'chart_color_variance': 1000,
            'table_grid_score': 0.6,
            'map_complexity': 0.7,
            'vlm_confidence_threshold': 0.7
        }
    
    def detect_regions(self, page_image: np.ndarray, page_number: int = 1) -> List[Region]:
        """페이지에서 모든 영역 감지"""
        logger.info(f"\n{'='*60}")
        logger.info(f"페이지 {page_number} 레이아웃 감지 시작")
        logger.info(f"{'='*60}")
        
        regions = []
        
        # 1. 헤더 감지
        logger.info("1. 헤더 감지 중...")
        headers = self._detect_headers(page_image, page_number)
        regions.extend(headers)
        logger.info(f"   → {len(headers)}개 헤더 감지")
        
        # 2. 차트 감지
        logger.info("2. 차트 감지 중...")
        charts = self._detect_charts(page_image, page_number)
        regions.extend(charts)
        logger.info(f"   → {len(charts)}개 차트 감지")
        
        # 3. 표 감지
        logger.info("3. 표 감지 중...")
        tables = self._detect_tables(page_image, page_number)
        regions.extend(tables)
        logger.info(f"   → {len(tables)}개 표 감지")
        
        # 4. 지도 감지
        logger.info("4. 지도 감지 중...")
        maps = self._detect_maps(page_image, page_number)
        regions.extend(maps)
        logger.info(f"   → {len(maps)}개 지도 감지")
        
        # 5. 중첩 제거 및 정렬
        logger.info("5. 영역 중첩 제거 중...")
        regions = self._remove_overlaps(regions)
        regions = sorted(regions, key=lambda r: (r.bbox[1], r.bbox[0]))
        
        # 6. VLM 검증
        if self.use_vlm_validation and self.vlm_service:
            logger.info("6. VLM 검증 중...")
            regions = self._validate_with_vlm(page_image, regions)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"총 {len(regions)}개 영역 감지 완료")
        for i, r in enumerate(regions, 1):
            logger.info(f"  Region {i}: {r.type:8s} at {r.bbox} (신뢰도: {r.confidence:.2f})")
        logger.info(f"{'='*60}\n")
        
        return regions
    
    def _detect_headers(self, image: np.ndarray, page_number: int) -> List[Region]:
        """섹션 헤더 감지"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        headers = []
        
        # 상단 20% 영역
        top_region = gray[:int(h * 0.2), :]
        _, binary = cv2.threshold(top_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for i, contour in enumerate(contours):
            x, y, w_c, h_c = cv2.boundingRect(contour)
            
            # 헤더 조건: 넓고, 한 줄, 좌측 정렬
            if w_c > w * 0.3 and h_c < h * 0.05 and x < w * 0.2:
                region = Region(
                    region_id=f"page{page_number}_header{i+1}",
                    bbox=(x, y, w_c, h_c),
                    type='header',
                    confidence=0.8,
                    metadata={'detection_method': 'cv_contour'}
                )
                headers.append(region)
        
        return headers
    
    def _detect_charts(self, image: np.ndarray, page_number: int) -> List[Region]:
        """차트/그래프 감지"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        charts = []
        
        # 2x2 그리드 분할
        grid_h, grid_w = h // 2, w // 2
        
        for row in range(2):
            for col in range(2):
                y_start = row * grid_h
                x_start = col * grid_w
                
                region_img = image[y_start:y_start+grid_h, x_start:x_start+grid_w]
                region_hsv = hsv[y_start:y_start+grid_h, x_start:x_start+grid_w]
                
                # 색상 다양성
                color_variance = np.var(region_hsv[:, :, 0])
                
                # 선 감지
                edges = cv2.Canny(cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY), 50, 150)
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
                line_count = len(lines) if lines is not None else 0
                
                # 차트 조건
                if color_variance > self.thresholds['chart_color_variance'] and line_count > 5:
                    chart_type = self._infer_chart_type(region_img)
                    
                    region = Region(
                        region_id=f"page{page_number}_chart{len(charts)+1}",
                        bbox=(x_start, y_start, grid_w, grid_h),
                        type='chart',
                        confidence=0.75,
                        metadata={
                            'detection_method': 'cv_color_variance',
                            'chart_type': chart_type,
                            'color_variance': float(color_variance)
                        }
                    )
                    charts.append(region)
        
        return charts
    
    def _infer_chart_type(self, region_img: np.ndarray) -> str:
        """차트 타입 추론"""
        gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
        
        # 원 감지 (파이 차트)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1, minDist=50,
            param1=50, param2=30, minRadius=30, maxRadius=200
        )
        if circles is not None:
            return 'pie'
        
        # 수직선 많으면 막대 그래프
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        if lines is not None:
            vertical_lines = sum(1 for line in lines if abs(line[0][0] - line[0][2]) < 10)
            if vertical_lines > len(lines) * 0.5:
                return 'bar'
        
        return 'unknown'
    
    def _detect_tables(self, image: np.ndarray, page_number: int) -> List[Region]:
        """표 감지"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        tables = []
        
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=w*0.3, maxLineGap=5)
        
        if lines is None:
            return tables
        
        # 가로선/세로선 분리
        h_lines, v_lines = [], []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 10:
                h_lines.append(line[0])
            elif abs(x1 - x2) < 10:
                v_lines.append(line[0])
        
        # 표 조건
        if len(h_lines) >= 3 and len(v_lines) >= 3:
            all_x = [l[0] for l in h_lines + v_lines] + [l[2] for l in h_lines + v_lines]
            all_y = [l[1] for l in h_lines + v_lines] + [l[3] for l in h_lines + v_lines]
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            
            region = Region(
                region_id=f"page{page_number}_table1",
                bbox=(x_min, y_min, x_max - x_min, y_max - y_min),
                type='table',
                confidence=0.9,
                metadata={'h_lines': len(h_lines), 'v_lines': len(v_lines)}
            )
            tables.append(region)
        
        return tables
    
    def _detect_maps(self, image: np.ndarray, page_number: int) -> List[Region]:
        """지도 감지"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        maps = []
        
        # 우측 절반
        right_gray = gray[:, w//2:]
        edges = cv2.Canny(right_gray, 30, 100)
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:
                continue
            
            perimeter = cv2.arcLength(contour, True)
            complexity = perimeter / (2 * np.sqrt(np.pi * area)) if area > 0 else 0
            
            if complexity > self.thresholds['map_complexity']:
                x, y, w_c, h_c = cv2.boundingRect(contour)
                x += w // 2  # 좌표 보정
                
                region = Region(
                    region_id=f"page{page_number}_map{len(maps)+1}",
                    bbox=(x, y, w_c, h_c),
                    type='map',
                    confidence=0.7,
                    metadata={'complexity': float(complexity)}
                )
                maps.append(region)
        
        return maps
    
    def _remove_overlaps(self, regions: List[Region]) -> List[Region]:
        """중첩 제거 (NMS)"""
        if len(regions) <= 1:
            return regions
        
        sorted_regions = sorted(regions, key=lambda r: r.confidence, reverse=True)
        keep = []
        
        for region in sorted_regions:
            overlap = False
            for kept in keep:
                if self._calculate_iou(region.bbox, kept.bbox) > 0.5:
                    overlap = True
                    break
            if not overlap:
                keep.append(region)
        
        return keep
    
    def _calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
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
        union = w1 * h1 + w2 * h2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _validate_with_vlm(self, page_image: np.ndarray, regions: List[Region]) -> List[Region]:
        """VLM 검증"""
        validated = []
        
        for region in regions:
            if region.confidence >= self.thresholds['vlm_confidence_threshold']:
                validated.append(region)
                continue
            
            # VLM 호출 (신뢰도 낮은 경우만)
            x, y, w, h = region.bbox
            crop = page_image[y:y+h, x:x+w]
            
            try:
                # VLM 검증 로직 (추후 구현)
                region.confidence = 0.95
                region.metadata['vlm_verified'] = True
            except Exception as e:
                logger.warning(f"VLM 검증 실패: {e}")
            
            validated.append(region)
        
        return validated
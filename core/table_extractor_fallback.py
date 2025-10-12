"""
PRISM Phase 2.1 - Fallback Table Extractor (품질 개선)

개선 사항:
- ✅ 동적 정렬 임계값 적용 (한글 OCR 고려)
- ✅ 최소 열/행 조건 완화
- ✅ 표 품질 검증 완화

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13 (개선)
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from collections import defaultdict


@dataclass
class OCRBox:
    """OCR 결과 박스"""
    text: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float = 1.0


@dataclass
class TableCell:
    """표 셀 정보"""
    text: str
    row: int
    col: int
    bbox: Tuple[float, float, float, float]
    confidence: float = 1.0


@dataclass
class ExtractedTable:
    """추출된 표"""
    cells: List[TableCell]
    num_rows: int
    num_cols: int
    page_num: int
    bbox: Tuple[float, float, float, float]
    confidence: float
    
    def to_markdown(self) -> str:
        """Markdown 표 변환"""
        grid = {}
        for cell in self.cells:
            grid[(cell.row, cell.col)] = cell.text
        
        lines = []
        
        # 헤더
        header_cols = []
        for col in range(self.num_cols):
            text = grid.get((0, col), "")
            header_cols.append(text)
        lines.append("| " + " | ".join(header_cols) + " |")
        
        # 구분선
        lines.append("|" + "|".join(["---"] * self.num_cols) + "|")
        
        # 데이터 행
        for row in range(1, self.num_rows):
            row_cols = []
            for col in range(self.num_cols):
                text = grid.get((row, col), "")
                row_cols.append(text)
            lines.append("| " + " | ".join(row_cols) + " |")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "page_num": self.page_num,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "markdown": self.to_markdown()
        }


class FallbackTableExtractor:
    """
    OCR 기반 표 추출기 (품질 개선)
    
    개선 전략:
    1. 🎯 동적 정렬 임계값 (한글 OCR은 정렬이 덜 정확)
    2. 🎯 최소 열/행 조건 완화 (2x2 표도 허용)
    3. 🎯 표 품질 검증 완화 (50% 셀 채움율)
    """
    
    def __init__(
        self,
        min_cols: int = 2,           # 기존: 3
        min_rows: int = 2,
        alignment_threshold: float = 20.0  # 기존: 10.0
    ):
        """
        Args:
            min_cols: 표로 인정할 최소 열 개수
            min_rows: 표로 인정할 최소 행 개수
            alignment_threshold: 정렬 판단 임계값 (픽셀)
        """
        self.min_cols = min_cols
        self.min_rows = min_rows
        self.alignment_threshold = alignment_threshold
    
    def extract_tables(
        self,
        ocr_result: List[Dict],
        page_num: int
    ) -> List[ExtractedTable]:
        """
        OCR 결과에서 표 추출
        
        Args:
            ocr_result: PaddleOCR 결과 [{"text": ..., "bbox": ...}, ...]
            page_num: 페이지 번호
            
        Returns:
            추출된 표 목록
        """
        if not ocr_result:
            return []
        
        # 1. OCR 결과를 셀 후보로 변환
        cells = self._ocr_to_cells(ocr_result)
        
        # 2. 행/열 그룹핑
        rows = self._group_by_rows(cells)
        cols = self._find_columns(rows)
        
        # 3. 표 조건 검증
        if len(rows) < self.min_rows or len(cols) < self.min_cols:
            return []
        
        # 4. 표 구조 생성
        table = self._build_table(rows, cols, page_num)
        
        if table:
            return [table]
        return []
    
    def _ocr_to_cells(self, ocr_result: List[Dict]) -> List[Dict]:
        """OCR 결과를 셀 후보로 변환"""
        cells = []
        
        for item in ocr_result:
            bbox = item["bbox"]
            text = item["text"]
            
            # bbox를 (x1, y1, x2, y2)로 변환
            if isinstance(bbox[0], list):
                # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)
            else:
                # [x1, y1, x2, y2]
                x1, y1, x2, y2 = bbox
            
            cells.append({
                "text": text,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": (x1 + x2) / 2,
                "center_y": (y1 + y2) / 2
            })
        
        return cells
    
    def _group_by_rows(self, cells: List[Dict]) -> List[List[Dict]]:
        """셀을 행으로 그룹핑"""
        if not cells:
            return []
        
        # y 좌표로 정렬
        sorted_cells = sorted(cells, key=lambda c: c["y1"])
        
        rows = []
        current_row = [sorted_cells[0]]
        
        # 🎯 동적 행 간격 계산
        avg_height = np.mean([c["y2"] - c["y1"] for c in cells])
        row_gap = avg_height * 0.5  # 평균 높이의 50%
        
        for cell in sorted_cells[1:]:
            # 이전 행과 y 좌표 차이
            prev_y = current_row[-1]["y1"]
            
            if abs(cell["y1"] - prev_y) < row_gap:
                current_row.append(cell)
            else:
                # 새 행 시작
                rows.append(sorted(current_row, key=lambda c: c["x1"]))
                current_row = [cell]
        
        # 마지막 행 추가
        if current_row:
            rows.append(sorted(current_row, key=lambda c: c["x1"]))
        
        return rows
    
    def _find_columns(self, rows: List[List[Dict]]) -> List[float]:
        """
        행들의 x 좌표를 분석하여 열 경계 찾기
        🎯 개선: 동적 임계값 적용
        """
        if not rows:
            return []
        
        # 모든 셀의 x 좌표 수집
        all_x = []
        for row in rows:
            for cell in row:
                all_x.append(cell["x1"])
        
        if not all_x:
            return []
        
        all_x = sorted(set(all_x))
        
        # 클러스터링
        columns = []
        current_cluster = [all_x[0]]
        
        # 🎯 동적 임계값 (한글은 정렬이 덜 정확함)
        dynamic_threshold = self.alignment_threshold * 1.5
        
        for x in all_x[1:]:
            if x - current_cluster[-1] < dynamic_threshold:
                current_cluster.append(x)
            else:
                columns.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [x]
        
        if current_cluster:
            columns.append(sum(current_cluster) / len(current_cluster))
        
        return columns
    
    def _build_table(
        self,
        rows: List[List[Dict]],
        columns: List[float],
        page_num: int
    ) -> Optional[ExtractedTable]:
        """표 구조 생성"""
        num_rows = len(rows)
        num_cols = len(columns)
        
        # 전체 bbox 계산
        all_cells_flat = [cell for row in rows for cell in row]
        x1 = min(c["x1"] for c in all_cells_flat)
        y1 = min(c["y1"] for c in all_cells_flat)
        x2 = max(c["x2"] for c in all_cells_flat)
        y2 = max(c["y2"] for c in all_cells_flat)
        bbox = (x1, y1, x2, y2)
        
        # 표 셀 생성
        table_cells = []
        
        for row_idx, row in enumerate(rows):
            for cell in row:
                # 가장 가까운 열 찾기
                col_idx = 0
                min_dist = abs(cell["x1"] - columns[0])
                
                for i, col_x in enumerate(columns):
                    dist = abs(cell["x1"] - col_x)
                    if dist < min_dist:
                        min_dist = dist
                        col_idx = i
                
                # 🎯 완화된 거리 임계값
                if min_dist > self.alignment_threshold * 2:
                    continue
                
                table_cell = TableCell(
                    text=cell["text"],
                    row=row_idx,
                    col=col_idx,
                    bbox=(cell["x1"], cell["y1"], cell["x2"], cell["y2"]),
                    confidence=0.85
                )
                table_cells.append(table_cell)
        
        # 🎯 표 품질 검증 완화 (70% → 50%)
        expected_cells = num_rows * num_cols
        actual_cells = len(table_cells)
        
        if actual_cells < expected_cells * 0.5:
            return None
        
        table = ExtractedTable(
            cells=table_cells,
            num_rows=num_rows,
            num_cols=num_cols,
            page_num=page_num,
            bbox=bbox,
            confidence=0.8
        )
        
        return table


# 테스트
if __name__ == "__main__":
    sample_ocr = [
        {"text": "구분", "bbox": [[10, 10], [50, 10], [50, 30], [10, 30]]},
        {"text": "항목1", "bbox": [[60, 10], [100, 10], [100, 30], [60, 30]]},
        {"text": "항목2", "bbox": [[110, 10], [150, 10], [150, 30], [110, 30]]},
        {"text": "행1", "bbox": [[10, 40], [50, 40], [50, 60], [10, 60]]},
        {"text": "데이터1", "bbox": [[60, 40], [100, 40], [100, 60], [60, 60]]},
        {"text": "데이터2", "bbox": [[110, 40], [150, 40], [150, 60], [110, 60]]},
    ]
    
    extractor = FallbackTableExtractor(min_cols=2, min_rows=2, alignment_threshold=20.0)
    tables = extractor.extract_tables(sample_ocr, page_num=1)
    
    print(f"✅ Found {len(tables)} table(s)")
    for i, table in enumerate(tables):
        print(f"\n표 {i+1}:")
        print(f"  크기: {table.num_rows}x{table.num_cols}")
        print(f"  신뢰도: {table.confidence:.2f}")
        print(f"\nMarkdown:\n{table.to_markdown()}")
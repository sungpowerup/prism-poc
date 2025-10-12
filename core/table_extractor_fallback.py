"""
PRISM Phase 2.1 - Fallback Table Extractor

Detectron2 없이도 OCR 기반으로 표를 추출합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from collections import defaultdict


@dataclass
class TableCell:
    """표 셀 정보"""
    text: str
    row: int
    col: int
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
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
        # 행/열 구조 생성
        grid = {}
        for cell in self.cells:
            grid[(cell.row, cell.col)] = cell.text
        
        # Markdown 생성
        lines = []
        
        # 헤더 (첫 행)
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
    OCR 기반 표 추출기
    
    전략:
    1. OCR bbox들의 정렬 패턴 분석
    2. 수평/수직으로 정렬된 텍스트 그룹 탐지
    3. 행/열 구조 추론
    4. 표 경계 확정
    """
    
    def __init__(
        self,
        min_cols: int = 3,
        min_rows: int = 2,
        alignment_threshold: float = 10.0
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
        
        # 2. 수평/수직 정렬 분석
        row_groups = self._group_by_rows(cells)
        col_groups = self._group_by_cols(cells)
        
        # 3. 표 후보 탐지
        table_candidates = self._detect_table_regions(
            cells, row_groups, col_groups
        )
        
        # 4. 표 검증 및 구조화
        tables = []
        for candidate in table_candidates:
            table = self._build_table(candidate, page_num)
            if table:
                tables.append(table)
        
        return tables
    
    def _ocr_to_cells(self, ocr_result: List[Dict]) -> List[Dict]:
        """OCR 결과를 셀 후보로 변환"""
        cells = []
        
        for item in ocr_result:
            bbox = item.get("bbox", [])
            text = item.get("text", "").strip()
            
            if not text or len(bbox) != 4:
                continue
            
            # bbox: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            
            cell = {
                "text": text,
                "x1": min(x_coords),
                "y1": min(y_coords),
                "x2": max(x_coords),
                "y2": max(y_coords),
                "cx": (min(x_coords) + max(x_coords)) / 2,
                "cy": (min(y_coords) + max(y_coords)) / 2,
            }
            cells.append(cell)
        
        return cells
    
    def _group_by_rows(self, cells: List[Dict]) -> List[List[Dict]]:
        """Y 좌표 기준으로 행 그룹화"""
        if not cells:
            return []
        
        # Y 중심 좌표로 정렬
        sorted_cells = sorted(cells, key=lambda c: c["cy"])
        
        rows = []
        current_row = [sorted_cells[0]]
        
        for cell in sorted_cells[1:]:
            # 이전 셀과 Y 좌표 차이
            prev_cy = current_row[-1]["cy"]
            diff = abs(cell["cy"] - prev_cy)
            
            if diff < self.alignment_threshold:
                # 같은 행
                current_row.append(cell)
            else:
                # 새 행
                rows.append(current_row)
                current_row = [cell]
        
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _group_by_cols(self, cells: List[Dict]) -> List[List[Dict]]:
        """X 좌표 기준으로 열 그룹화"""
        if not cells:
            return []
        
        # X 중심 좌표로 정렬
        sorted_cells = sorted(cells, key=lambda c: c["cx"])
        
        cols = []
        current_col = [sorted_cells[0]]
        
        for cell in sorted_cells[1:]:
            # 이전 셀과 X 좌표 차이
            prev_cx = current_col[-1]["cx"]
            diff = abs(cell["cx"] - prev_cx)
            
            if diff < self.alignment_threshold:
                # 같은 열
                current_col.append(cell)
            else:
                # 새 열
                cols.append(current_col)
                current_col = [cell]
        
        if current_col:
            cols.append(current_col)
        
        return cols
    
    def _detect_table_regions(
        self,
        cells: List[Dict],
        row_groups: List[List[Dict]],
        col_groups: List[List[Dict]]
    ) -> List[Dict]:
        """표 후보 영역 탐지"""
        candidates = []
        
        # 연속된 행/열이 많은 영역 찾기
        for i, row_group in enumerate(row_groups):
            if len(row_group) < self.min_cols:
                continue
            
            # 연속된 행 찾기
            consecutive_rows = [row_group]
            for j in range(i + 1, len(row_groups)):
                next_row = row_groups[j]
                
                # 열 개수가 비슷하고 정렬되어 있으면 연속된 행
                if abs(len(next_row) - len(row_group)) <= 1:
                    consecutive_rows.append(next_row)
                else:
                    break
            
            # 표 조건 확인
            if len(consecutive_rows) >= self.min_rows:
                # 모든 셀 수집
                table_cells = []
                for row in consecutive_rows:
                    table_cells.extend(row)
                
                # 표 경계 계산
                x1 = min(c["x1"] for c in table_cells)
                y1 = min(c["y1"] for c in table_cells)
                x2 = max(c["x2"] for c in table_cells)
                y2 = max(c["y2"] for c in table_cells)
                
                candidate = {
                    "cells": table_cells,
                    "rows": consecutive_rows,
                    "bbox": (x1, y1, x2, y2),
                    "num_rows": len(consecutive_rows),
                    "num_cols": len(row_group)  # 첫 행 기준
                }
                candidates.append(candidate)
        
        return candidates
    
    def _build_table(
        self,
        candidate: Dict,
        page_num: int
    ) -> Optional[ExtractedTable]:
        """표 구조 생성"""
        cells = candidate["cells"]
        num_rows = candidate["num_rows"]
        num_cols = candidate["num_cols"]
        bbox = candidate["bbox"]
        
        # 행/열 인덱스 할당
        rows = candidate["rows"]
        table_cells = []
        
        for row_idx, row in enumerate(rows):
            # X 좌표로 열 순서 정렬
            sorted_row = sorted(row, key=lambda c: c["cx"])
            
            for col_idx, cell in enumerate(sorted_row):
                if col_idx >= num_cols:
                    break
                
                table_cell = TableCell(
                    text=cell["text"],
                    row=row_idx,
                    col=col_idx,
                    bbox=(cell["x1"], cell["y1"], cell["x2"], cell["y2"]),
                    confidence=0.85
                )
                table_cells.append(table_cell)
        
        # 표 품질 검증
        if len(table_cells) < num_rows * num_cols * 0.7:
            # 셀이 너무 적으면 표가 아닐 가능성
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


# 간단한 테스트
if __name__ == "__main__":
    # 샘플 OCR 결과
    sample_ocr = [
        {"text": "구분", "bbox": [[10, 10], [50, 10], [50, 30], [10, 30]]},
        {"text": "항목1", "bbox": [[60, 10], [100, 10], [100, 30], [60, 30]]},
        {"text": "항목2", "bbox": [[110, 10], [150, 10], [150, 30], [110, 30]]},
        {"text": "행1", "bbox": [[10, 40], [50, 40], [50, 60], [10, 60]]},
        {"text": "데이터1", "bbox": [[60, 40], [100, 40], [100, 60], [60, 60]]},
        {"text": "데이터2", "bbox": [[110, 40], [150, 40], [150, 60], [110, 60]]},
    ]
    
    extractor = FallbackTableExtractor(min_cols=2, min_rows=2)
    tables = extractor.extract_tables(sample_ocr, page_num=1)
    
    print(f"✅ Found {len(tables)} table(s)")
    for i, table in enumerate(tables):
        print(f"\n표 {i+1}:")
        print(f"  크기: {table.num_rows}x{table.num_cols}")
        print(f"  신뢰도: {table.confidence:.2f}")
        print(f"\nMarkdown:\n{table.to_markdown()}")
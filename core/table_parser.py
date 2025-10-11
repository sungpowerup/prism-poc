"""
PRISM Phase 2 - Table Parser

표 구조를 파싱하여 Markdown/JSON 형식으로 변환합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

import pdfplumber
from PIL import Image
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

from models.layout_detector import DocumentElement, BoundingBox


@dataclass
class TableCell:
    """표 셀 정보"""
    row: int
    col: int
    text: str
    rowspan: int = 1
    colspan: int = 1


@dataclass
class StructuredTable:
    """구조화된 표 데이터"""
    headers: List[str]
    rows: List[List[str]]
    page_num: int
    bbox: BoundingBox
    caption: Optional[str] = None
    
    def to_markdown(self) -> str:
        """Markdown 테이블로 변환"""
        lines = []
        
        # 캡션 (있으면)
        if self.caption:
            lines.append(f"**{self.caption}**\n")
        
        # 헤더
        if self.headers:
            lines.append("| " + " | ".join(self.headers) + " |")
            lines.append("|" + "|".join(["---"] * len(self.headers)) + "|")
        
        # 데이터 행
        for row in self.rows:
            lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)
    
    def to_json(self) -> Dict:
        """JSON 형식으로 변환"""
        if self.headers:
            # 헤더가 있으면 dict 배열로
            json_rows = []
            for row in self.rows:
                row_dict = {
                    header: value 
                    for header, value in zip(self.headers, row)
                }
                json_rows.append(row_dict)
            
            return {
                "caption": self.caption,
                "headers": self.headers,
                "data": json_rows,
                "page": self.page_num,
                "bbox": self.bbox.to_dict()
            }
        else:
            # 헤더 없으면 2D 배열로
            return {
                "caption": self.caption,
                "data": self.rows,
                "page": self.page_num,
                "bbox": self.bbox.to_dict()
            }
    
    def to_html(self) -> str:
        """HTML 테이블로 변환"""
        lines = ["<table>"]
        
        # 캡션
        if self.caption:
            lines.append(f"  <caption>{self.caption}</caption>")
        
        # 헤더
        if self.headers:
            lines.append("  <thead>")
            lines.append("    <tr>")
            for header in self.headers:
                lines.append(f"      <th>{header}</th>")
            lines.append("    </tr>")
            lines.append("  </thead>")
        
        # 바디
        lines.append("  <tbody>")
        for row in self.rows:
            lines.append("    <tr>")
            for cell in row:
                lines.append(f"      <td>{cell}</td>")
            lines.append("    </tr>")
        lines.append("  </tbody>")
        
        lines.append("</table>")
        return "\n".join(lines)


class TableParser:
    """
    표 파싱 모듈
    
    전략:
    1. pdfplumber로 표 구조 파싱 (선 기반)
    2. 실패 시 이미지 기반 파싱 (향후 Table Transformer 통합)
    """
    
    def __init__(self):
        pass
    
    def parse_from_pdf(
        self, 
        pdf_path: str, 
        element: DocumentElement
    ) -> Optional[StructuredTable]:
        """
        PDF에서 표 파싱
        
        Args:
            pdf_path: PDF 파일 경로
            element: 표 요소
            
        Returns:
            구조화된 표 (실패 시 None)
        """
        # pdfplumber로 표 추출
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[element.page_num - 1]
            
            # BBox 영역만 크롭
            bbox = element.bbox
            cropped = page.crop((
                bbox.x, 
                bbox.y, 
                bbox.x + bbox.width, 
                bbox.y + bbox.height
            ))
            
            # 표 추출
            tables = cropped.extract_tables()
            
            if not tables or len(tables) == 0:
                return None
            
            # 첫 번째 표 사용
            table_data = tables[0]
            
            # 헤더와 데이터 분리
            headers = None
            rows = table_data
            
            # 첫 행이 헤더인지 판단 (휴리스틱)
            if len(table_data) > 1 and self._is_header_row(table_data[0]):
                headers = [str(cell).strip() for cell in table_data[0]]
                rows = table_data[1:]
            
            # 데이터 정제
            clean_rows = []
            for row in rows:
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                clean_rows.append(clean_row)
            
            return StructuredTable(
                headers=headers,
                rows=clean_rows,
                page_num=element.page_num,
                bbox=element.bbox,
                caption=None  # 캡션은 별도 감지 필요
            )
    
    def _is_header_row(self, row: List) -> bool:
        """첫 행이 헤더인지 판단"""
        # 간단한 휴리스틱:
        # - 텍스트가 짧고 간결함
        # - 특수문자나 숫자가 적음
        
        if not row:
            return False
        
        # 평균 길이 체크
        avg_len = sum(len(str(cell)) for cell in row if cell) / len(row)
        
        # 숫자 비율 체크
        digit_count = sum(str(cell).replace('.', '').replace(',', '').isdigit() 
                         for cell in row if cell)
        digit_ratio = digit_count / len(row)
        
        # 헤더는 보통 짧고 숫자가 적음
        return avg_len < 20 and digit_ratio < 0.3
    
    def parse_all_tables(
        self, 
        pdf_path: str, 
        elements: List[DocumentElement]
    ) -> List[StructuredTable]:
        """
        여러 표를 일괄 파싱
        """
        results = []
        
        for element in elements:
            parsed = self.parse_from_pdf(pdf_path, element)
            if parsed:
                results.append(parsed)
        
        return results


# 테스트 코드
if __name__ == "__main__":
    from core.document_analyzer import DocumentAnalyzer
    from models.layout_detector import ElementType
    import json
    
    # 1. 문서 분석
    analyzer = DocumentAnalyzer()
    structure = analyzer.analyze("data/uploads/test_document.pdf", max_pages=3)
    
    # 2. 표 요소만 추출
    table_elements = structure.get_all_elements_by_type(ElementType.TABLE)
    print(f"표 {len(table_elements)}개 발견")
    
    # 3. 표 파싱
    parser = TableParser()
    parsed_tables = parser.parse_all_tables("data/uploads/test_document.pdf", table_elements)
    
    print(f"표 파싱 완료: {len(parsed_tables)}개")
    
    # 4. 결과 출력
    print("\n=== 파싱된 표 ===")
    for i, table in enumerate(parsed_tables):
        print(f"\n[Table {i+1}] (Page {table.page_num})")
        
        # Markdown 출력
        print("\n### Markdown:")
        print(table.to_markdown())
        
        # JSON 저장
        with open(f"data/processed/table_{i+1}.json", "w", encoding="utf-8") as f:
            json.dump(table.to_json(), f, ensure_ascii=False, indent=2)
        
        print(f"\nJSON 저장: data/processed/table_{i+1}.json")
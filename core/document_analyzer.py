"""
PRISM Phase 2 - Document Analyzer

문서 전체를 분석하여 구조화된 요소로 분리합니다.

Author: 이서영 (Backend Lead)
Date: 2025-10-11
"""

import fitz  # PyMuPDF
from PIL import Image
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import io

from models.layout_detector import LayoutDetector, DocumentElement, ElementType


@dataclass
class PageLayout:
    """페이지 레이아웃 정보"""
    page_num: int
    width: int
    height: int
    elements: List[DocumentElement] = field(default_factory=list)
    
    def get_elements_by_type(self, element_type: ElementType) -> List[DocumentElement]:
        """특정 타입의 요소만 필터링"""
        return [e for e in self.elements if e.type == element_type]
    
    def to_dict(self) -> Dict:
        return {
            "page": self.page_num,
            "width": self.width,
            "height": self.height,
            "elements": [e.to_dict() for e in self.elements]
        }


@dataclass
class DocumentStructure:
    """문서 전체 구조"""
    total_pages: int
    pages: List[PageLayout] = field(default_factory=list)
    
    def get_all_elements_by_type(self, element_type: ElementType) -> List[DocumentElement]:
        """전체 문서에서 특정 타입의 요소 추출"""
        elements = []
        for page in self.pages:
            elements.extend(page.get_elements_by_type(element_type))
        return elements
    
    def to_dict(self) -> Dict:
        return {
            "total_pages": self.total_pages,
            "pages": [p.to_dict() for p in self.pages]
        }


class DocumentAnalyzer:
    """
    PDF 문서를 분석하여 구조화된 요소로 분리
    
    처리 흐름:
    1. PDF → 페이지별 이미지 추출
    2. Layout Detection (텍스트/표/이미지 분리)
    3. 구조화된 DocumentStructure 반환
    """
    
    def __init__(self, dpi: int = 200):
        """
        Args:
            dpi: PDF → 이미지 변환 해상도
        """
        self.dpi = dpi
        self.layout_detector = LayoutDetector()
    
    def analyze(self, pdf_path: str, max_pages: Optional[int] = None) -> DocumentStructure:
        """
        PDF 문서 전체 분석
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수 (None이면 전체)
            
        Returns:
            DocumentStructure: 문서 구조 정보
        """
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), max_pages) if max_pages else len(doc)
        
        document_structure = DocumentStructure(total_pages=total_pages)
        
        for page_num in range(total_pages):
            print(f"Analyzing page {page_num + 1}/{total_pages}...")
            
            # 페이지 레이아웃 분석
            page_layout = self._analyze_page(doc[page_num], page_num + 1)
            document_structure.pages.append(page_layout)
        
        doc.close()
        
        return document_structure
    
    def _analyze_page(self, page: fitz.Page, page_num: int) -> PageLayout:
        """
        단일 페이지 분석
        
        Args:
            page: PyMuPDF Page 객체
            page_num: 페이지 번호 (1-based)
            
        Returns:
            PageLayout: 페이지 레이아웃 정보
        """
        # 1. 페이지를 이미지로 변환
        pix = page.get_pixmap(dpi=self.dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 2. Layout Detection 수행
        elements = self.layout_detector.detect(img, page_num)
        
        # 3. PageLayout 생성
        page_layout = PageLayout(
            page_num=page_num,
            width=pix.width,
            height=pix.height,
            elements=elements
        )
        
        return page_layout
    
    def extract_element_image(
        self, 
        pdf_path: str, 
        element: DocumentElement
    ) -> Image.Image:
        """
        특정 요소의 이미지 크롭
        
        Args:
            pdf_path: PDF 파일 경로
            element: 추출할 요소
            
        Returns:
            크롭된 이미지
        """
        doc = fitz.open(pdf_path)
        page = doc[element.page_num - 1]  # 0-based index
        
        # 페이지를 이미지로 변환
        pix = page.get_pixmap(dpi=self.dpi)
        full_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 요소 영역 크롭
        bbox = element.bbox
        cropped = full_image.crop((
            bbox.x,
            bbox.y,
            bbox.x + bbox.width,
            bbox.y + bbox.height
        ))
        
        doc.close()
        
        return cropped


# 테스트 코드
if __name__ == "__main__":
    import json
    
    # 테스트 PDF 분석
    analyzer = DocumentAnalyzer(dpi=200)
    
    pdf_path = "data/uploads/test_document.pdf"
    structure = analyzer.analyze(pdf_path, max_pages=3)
    
    # 결과 출력
    print(f"\n총 {structure.total_pages}페이지 분석 완료")
    print(f"\n요소 통계:")
    for element_type in ElementType:
        elements = structure.get_all_elements_by_type(element_type)
        print(f"  {element_type.value}: {len(elements)}개")
    
    # JSON 저장
    result = structure.to_dict()
    with open("data/processed/document_structure.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n분석 결과 저장 완료: data/processed/document_structure.json")
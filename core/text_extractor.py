"""
PRISM Phase 2 - Text Extractor

문서에서 텍스트를 추출하고 원본 구조를 최대한 보존합니다.

Author: 이서영 (Backend Lead)
Date: 2025-10-11
"""

import fitz  # PyMuPDF
from paddleocr import PaddleOCR
from PIL import Image
from typing import List, Dict, Optional
from dataclasses import dataclass

from models.layout_detector import DocumentElement, BoundingBox


@dataclass
class ExtractedText:
    """추출된 텍스트 정보"""
    content: str
    bbox: BoundingBox
    confidence: float
    page_num: int
    method: str  # "pymupdf" or "paddleocr"
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "page": self.page_num,
            "method": self.method
        }


class TextExtractor:
    """
    텍스트 추출 모듈
    
    전략:
    1. PyMuPDF로 먼저 텍스트 추출 (원본 보존)
    2. 실패 시 PaddleOCR로 대체 (이미지 OCR)
    """
    
    def __init__(self, use_ocr_fallback: bool = True):
        """
        Args:
            use_ocr_fallback: PyMuPDF 실패 시 OCR 사용 여부
        """
        self.use_ocr_fallback = use_ocr_fallback
        
        if use_ocr_fallback:
            print("Loading PaddleOCR...")
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean',
                show_log=False
            )
            print("PaddleOCR loaded successfully")
    
    def extract_from_pdf(
        self, 
        pdf_path: str, 
        element: DocumentElement
    ) -> Optional[ExtractedText]:
        """
        PDF에서 특정 요소의 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            element: 추출할 텍스트 요소
            
        Returns:
            추출된 텍스트 (실패 시 None)
        """
        # 1. PyMuPDF로 텍스트 추출 시도
        text = self._extract_with_pymupdf(pdf_path, element)
        
        if text and len(text.strip()) > 0:
            return ExtractedText(
                content=text,
                bbox=element.bbox,
                confidence=1.0,  # PyMuPDF는 정확도 100%
                page_num=element.page_num,
                method="pymupdf"
            )
        
        # 2. PaddleOCR로 대체
        if self.use_ocr_fallback:
            result = self._extract_with_ocr(pdf_path, element)
            if result:
                return result
        
        return None
    
    def _extract_with_pymupdf(
        self, 
        pdf_path: str, 
        element: DocumentElement
    ) -> Optional[str]:
        """
        PyMuPDF로 텍스트 추출 (원본 보존)
        """
        doc = fitz.open(pdf_path)
        page = doc[element.page_num - 1]
        
        # BBox 영역의 텍스트만 추출
        bbox = element.bbox
        rect = fitz.Rect(bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height)
        
        text = page.get_text("text", clip=rect)
        doc.close()
        
        return text.strip() if text else None
    
    def _extract_with_ocr(
        self, 
        pdf_path: str, 
        element: DocumentElement
    ) -> Optional[ExtractedText]:
        """
        PaddleOCR로 텍스트 추출 (이미지 OCR)
        """
        # 페이지를 이미지로 변환
        doc = fitz.open(pdf_path)
        page = doc[element.page_num - 1]
        pix = page.get_pixmap(dpi=200)
        full_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 요소 영역 크롭
        bbox = element.bbox
        cropped = full_image.crop((
            bbox.x, bbox.y, 
            bbox.x + bbox.width, 
            bbox.y + bbox.height
        ))
        
        doc.close()
        
        # OCR 수행
        import numpy as np
        result = self.ocr.ocr(np.array(cropped), cls=True)
        
        if not result or not result[0]:
            return None
        
        # 텍스트 병합
        texts = []
        confidences = []
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            texts.append(text)
            confidences.append(confidence)
        
        combined_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return ExtractedText(
            content=combined_text,
            bbox=element.bbox,
            confidence=avg_confidence,
            page_num=element.page_num,
            method="paddleocr"
        )
    
    def extract_all_text(
        self, 
        pdf_path: str, 
        elements: List[DocumentElement]
    ) -> List[ExtractedText]:
        """
        여러 텍스트 요소를 일괄 추출
        
        Args:
            pdf_path: PDF 파일 경로
            elements: 텍스트 요소 리스트
            
        Returns:
            추출된 텍스트 리스트
        """
        results = []
        
        for element in elements:
            extracted = self.extract_from_pdf(pdf_path, element)
            if extracted:
                results.append(extracted)
        
        return results


# 테스트 코드
if __name__ == "__main__":
    from core.document_analyzer import DocumentAnalyzer
    from models.layout_detector import ElementType
    import json
    
    # 1. 문서 분석
    analyzer = DocumentAnalyzer()
    structure = analyzer.analyze("data/uploads/test_document.pdf", max_pages=3)
    
    # 2. 텍스트 요소만 추출
    text_elements = structure.get_all_elements_by_type(ElementType.TEXT)
    print(f"텍스트 블록 {len(text_elements)}개 발견")
    
    # 3. 텍스트 추출
    extractor = TextExtractor(use_ocr_fallback=True)
    extracted_texts = extractor.extract_all_text("data/uploads/test_document.pdf", text_elements)
    
    print(f"텍스트 추출 완료: {len(extracted_texts)}개")
    
    # 4. 결과 저장
    results = [t.to_dict() for t in extracted_texts]
    with open("data/processed/extracted_texts.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 5. 샘플 출력
    print("\n=== 추출된 텍스트 샘플 ===")
    for i, text in enumerate(extracted_texts[:3]):
        print(f"\n[Block {i+1}] ({text.method}, conf: {text.confidence:.2f})")
        print(text.content[:200] + "..." if len(text.content) > 200 else text.content)
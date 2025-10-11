"""
PRISM Phase 2 - Image Captioner

이미지/차트에 대해 선택적으로 VLM 캡션을 생성합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

from PIL import Image
from typing import Optional, Dict
from dataclasses import dataclass
import base64
import io

from models.layout_detector import DocumentElement, ElementType, ImageTypeClassifier
from core.providers import VLMProvider


@dataclass
class ImageCaption:
    """이미지 캡션 정보"""
    element: DocumentElement
    caption: str
    confidence: float
    provider: str  # "claude", "azure", "ollama"
    
    def to_dict(self) -> Dict:
        return {
            "element": self.element.to_dict(),
            "caption": self.caption,
            "confidence": self.confidence,
            "provider": self.provider
        }


class ImageCaptioner:
    """
    이미지/차트 캡션 생성 모듈
    
    전략:
    1. 장식 이미지는 건너뜀
    2. 차트/도표만 VLM 처리
    3. 캡션은 간결하고 정보적
    """
    
    def __init__(self, provider: str = "claude"):
        """
        Args:
            provider: VLM 프로바이더 ("claude", "azure", "ollama")
        """
        self.provider = VLMProvider.create(provider)
        self.classifier = ImageTypeClassifier()
        self.provider_name = provider
    
    def should_caption(self, element: DocumentElement) -> bool:
        """
        캡션 생성 필요 여부 판단
        
        Args:
            element: 문서 요소
            
        Returns:
            True if 캡션 생성 필요
        """
        # 표는 이미 구조화되어 있으므로 제외
        if element.type == ElementType.TABLE:
            return False
        
        # 차트만 캡션 생성
        return element.type == ElementType.CHART
    
    def generate_caption(
        self, 
        image: Image.Image, 
        element: DocumentElement,
        context: Optional[str] = None
    ) -> Optional[ImageCaption]:
        """
        이미지 캡션 생성
        
        Args:
            image: 크롭된 이미지
            element: 문서 요소
            context: 문서 맥락 (선택)
            
        Returns:
            생성된 캡션 (실패 시 None)
        """
        if not self.should_caption(element):
            return None
        
        # 프롬프트 생성
        prompt = self._build_prompt(element.type, context)
        
        # VLM 호출
        result = self.provider.analyze(image, prompt)
        
        if not result:
            return None
        
        return ImageCaption(
            element=element,
            caption=result,
            confidence=element.confidence,  # Layout Detection 신뢰도 사용
            provider=self.provider_name
        )
    
    def _build_prompt(self, element_type: ElementType, context: Optional[str]) -> str:
        """
        요소 타입별 최적화된 프롬프트 생성
        """
        base_prompts = {
            ElementType.CHART: """이 이미지는 문서 내 차트/그래프입니다.

다음 형식으로 분석해주세요:

1. **차트 유형**: (막대/선/파이/산점도/...)
2. **주요 데이터**: (핵심 수치와 트렌드)
3. **인사이트**: (한 문장 요약)

예시:
2023년 매출 추이를 보여주는 선 그래프. 1분기 100억원에서 4분기 150억원으로 50% 증가. 지속적인 성장세 확인.

**간결하고 정보적으로 작성해주세요.**""",
            
            ElementType.IMAGE: """이 이미지를 간단히 설명해주세요.

- 주요 객체/내용
- 문서에서의 역할 (설명/예시/장식)

2-3문장으로 간결하게 작성해주세요."""
        }
        
        prompt = base_prompts.get(element_type, base_prompts[ElementType.IMAGE])
        
        # 문맥 추가 (있으면)
        if context:
            prompt = f"**문서 맥락**: {context}\n\n{prompt}"
        
        return prompt
    
    def generate_captions_batch(
        self,
        pdf_path: str,
        elements: list[DocumentElement],
        analyzer
    ) -> list[ImageCaption]:
        """
        여러 이미지를 일괄 처리
        
        Args:
            pdf_path: PDF 파일 경로
            elements: 이미지 요소 리스트
            analyzer: DocumentAnalyzer 인스턴스
            
        Returns:
            생성된 캡션 리스트
        """
        captions = []
        
        for element in elements:
            # 캡션 필요 여부 체크
            if not self.should_caption(element):
                continue
            
            # 이미지 크롭
            cropped = analyzer.extract_element_image(pdf_path, element)
            
            # 캡션 생성
            caption = self.generate_caption(cropped, element)
            
            if caption:
                captions.append(caption)
                print(f"✓ Page {element.page_num}: {element.type.value} captioned")
        
        return captions


# 테스트 코드
if __name__ == "__main__":
    from core.document_analyzer import DocumentAnalyzer
    from models.layout_detector import ElementType
    import json
    
    # 1. 문서 분석
    analyzer = DocumentAnalyzer()
    structure = analyzer.analyze("data/uploads/test_document.pdf", max_pages=3)
    
    # 2. 이미지/차트 요소만 추출
    image_elements = structure.get_all_elements_by_type(ElementType.IMAGE)
    chart_elements = structure.get_all_elements_by_type(ElementType.CHART)
    all_visual = image_elements + chart_elements
    
    print(f"시각 요소 {len(all_visual)}개 발견")
    
    # 3. 캡션 생성
    captioner = ImageCaptioner(provider="claude")
    
    captions = captioner.generate_captions_batch(
        "data/uploads/test_document.pdf",
        all_visual,
        analyzer
    )
    
    print(f"\n캡션 생성 완료: {len(captions)}개")
    
    # 4. 결과 저장
    results = [c.to_dict() for c in captions]
    with open("data/processed/image_captions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 5. 샘플 출력
    print("\n=== 생성된 캡션 ===")
    for i, caption in enumerate(captions[:3]):
        print(f"\n[Image {i+1}] (Page {caption.element.page_num}, {caption.provider})")
        print(caption.caption)
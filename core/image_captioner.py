"""
PRISM Phase 2 - Image Captioner

이미지/차트에 대해 선택적으로 VLM 캡션을 생성합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

from PIL import Image
from typing import Optional, Dict, List
from dataclasses import dataclass
import base64
import io

from models.layout_detector import DocumentElement, ElementType, ImageTypeClassifier
from core.providers import VLMProvider, ClaudeProvider


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
    
    def __init__(self, provider: str = "claude", require_key: bool = False):
        """
        Args:
            provider: VLM 프로바이더 ("claude", "azure", "ollama")
            require_key: API 키 필수 여부
        """
        try:
            # API 키 선택적으로 생성
            if provider == "claude":
                self.provider = ClaudeProvider(require_key=require_key)
            else:
                self.provider = VLMProvider.create(provider)
            
            self.classifier = ImageTypeClassifier()
            self.provider_name = provider
        except ValueError as e:
            if not require_key:
                # API 키 없어도 OK
                print(f"⚠️  {e}. VLM features will be disabled.")
                self.provider = None
                self.classifier = ImageTypeClassifier()
                self.provider_name = provider
            else:
                raise
    
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
        
        if not self.provider:
            print("⚠️  VLM provider not available. Skipping caption generation.")
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

**주요 내용과 목적을 한두 문장으로 요약해주세요.**"""
        }
        
        prompt = base_prompts.get(element_type, base_prompts[ElementType.IMAGE])
        
        # 문맥 추가
        if context:
            prompt = f"문서 맥락: {context}\n\n{prompt}"
        
        return prompt
    
    def generate_captions_batch(
        self,
        pdf_path: str,
        elements: List[DocumentElement],
        analyzer
    ) -> List[ImageCaption]:
        """
        여러 이미지 일괄 캡션 생성
        
        Args:
            pdf_path: PDF 경로
            elements: 이미지 요소 목록
            analyzer: DocumentAnalyzer
            
        Returns:
            캡션 목록
        """
        captions = []
        
        for element in elements:
            if not self.should_caption(element):
                continue
            
            # 이미지 크롭
            image = analyzer.crop_element(pdf_path, element)
            if not image:
                continue
            
            # 캡션 생성
            caption = self.generate_caption(image, element)
            if caption:
                captions.append(caption)
        
        return captions
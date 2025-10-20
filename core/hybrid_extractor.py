"""
PRISM Phase 2.7 - Hybrid Content Extractor (2-Pass 전략)
Pass 1: OCR로 정확한 텍스트 추출
Pass 2: VLM으로 구조화 및 해석

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-20
Fix: 2-Pass 전략으로 정확도 + 구조화 동시 달성
"""

import os
import base64
import logging
from io import BytesIO
from typing import Dict
from PIL import Image
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# VLM Provider 임포트
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# OCR 엔진 임포트
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class ExtractedContent:
    """추출된 컨텐츠"""
    type: str
    content: str
    metadata: Dict
    confidence: float = 0.0


class HybridExtractor:
    """
    2-Pass 하이브리드 추출기
    
    전략:
    Pass 1: OCR로 모든 텍스트 정확하게 추출
    Pass 2: VLM이 OCR 결과를 참고하여 구조화
    
    장점:
    - OCR의 정확도 + VLM의 구조화 능력
    - 오인식 최소화
    """
    
    def __init__(self, vlm_provider: str = 'claude', ocr_engine: str = 'tesseract'):
        """초기화"""
        self.vlm_provider = vlm_provider
        self.ocr_engine = ocr_engine
        self.claude = None
        self.tesseract_available = TESSERACT_AVAILABLE
        
        # Claude API 초기화
        if vlm_provider == 'claude':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key and ANTHROPIC_AVAILABLE:
                try:
                    self.claude = Anthropic(api_key=api_key)
                    logger.info("✅ Claude Vision API initialized (2-Pass mode)")
                    print("✅ 2-Pass Extraction enabled (OCR → VLM)")
                except Exception as e:
                    logger.warning(f"Claude API initialization failed: {e}")
        
        # Tesseract 설정
        if TESSERACT_AVAILABLE:
            self.tesseract_config = '--psm 6 --oem 3'
            logger.info("✅ Tesseract OCR initialized")
        
        print(f"✅ HybridExtractor initialized (2-Pass: OCR + VLM)")
    
    def extract(
        self, 
        image: Image.Image, 
        region_type: str, 
        description: str
    ) -> ExtractedContent:
        """
        2-Pass 추출
        
        Args:
            image: PIL Image 객체
            region_type: 영역 타입
            description: 영역 설명
            
        Returns:
            추출된 컨텐츠
        """
        
        # Pass 1: OCR로 정확한 텍스트 추출
        ocr_text = self._extract_with_ocr(image)
        
        # Pass 2: VLM으로 구조화 (OCR 결과 참고)
        if self.claude and ocr_text:
            try:
                result = self._extract_with_vlm_guided(image, region_type, ocr_text)
                if result and result.content:
                    return result
            except Exception as e:
                logger.warning(f"VLM extraction failed: {e}, using OCR result")
        
        # VLM 실패 시 OCR 결과 반환
        return ExtractedContent(
            type='text',
            content=ocr_text if ocr_text else "",
            metadata={'source': 'ocr_only', 'description': description},
            confidence=0.80 if ocr_text else 0.0
        )
    
    def _extract_with_ocr(self, image: Image.Image) -> str:
        """Pass 1: OCR로 정확한 텍스트 추출"""
        
        if not self.tesseract_available:
            return ""
        
        try:
            text = pytesseract.image_to_string(
                image, 
                lang='kor+eng',
                config=self.tesseract_config
            ).strip()
            
            if text:
                logger.debug(f"[Pass 1] OCR extracted {len(text)} chars")
                return text
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
        
        return ""
    
    def _extract_with_vlm_guided(
        self, 
        image: Image.Image, 
        region_type: str,
        ocr_text: str
    ) -> ExtractedContent:
        """Pass 2: VLM으로 구조화 (OCR 텍스트 참고)"""
        
        # 이미지 → base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # 2-Pass 프롬프트 생성
        prompt = self._build_2pass_prompt(region_type, ocr_text)
        
        # Claude API 호출
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # 응답 추출
            content = response.content[0].text
            
            logger.debug(f"[Pass 2] VLM structured {len(content)} chars")
            
            return ExtractedContent(
                type=region_type,
                content=content,
                metadata={
                    'source': 'ocr_vlm_2pass',
                    'description': description,
                    'model': 'claude-sonnet-4',
                    'ocr_length': len(ocr_text)
                },
                confidence=0.95
            )
            
        except Exception as e:
            logger.error(f"VLM extraction failed: {e}")
            return None
    
    def _build_2pass_prompt(self, region_type: str, ocr_text: str) -> str:
        """2-Pass 전략 프롬프트"""
        
        prompt = f"""이 이미지와 OCR 추출 텍스트를 참고하여 구조화된 마크다운을 생성하세요.

**중요: OCR 텍스트의 정확도를 최우선으로 하되, 이미지를 보고 구조를 파악하세요.**

---
**OCR로 추출된 텍스트:**
```
{ocr_text[:1000]}...
```
---

**요구사항:**

1. **정확성 최우선**:
   - OCR 텍스트에 있는 모든 단어, 숫자를 **정확히** 사용하세요
   - 절대로 단어를 바꾸거나 추측하지 마세요
   - 예: "고관여" → "고찰어" 같은 오인식 금지
   - 예: "프로스포츠" → "프로포츠" 같은 오타 금지

2. **구조화**:
   - 이미지를 보고 표, 차트, 리스트 구조를 파악
   - OCR 텍스트를 적절한 마크다운 형식으로 배치
   - 표는 반드시 마크다운 표 형식으로 (| 열1 | 열2 |)

3. **차트/그래프 처리**:
   - 차트 타입 명시 (원그래프, 막대그래프 등)
   - OCR에서 추출된 숫자를 정확히 사용
   - 상세한 해석 추가:
     * 가장 높은/낮은 값 언급
     * 주요 패턴이나 경향 설명
     * 비교 분석 포함
     * 차트를 보지 못한 사람도 이해할 수 있게 자세히 설명

4. **표 처리**:
   - 행/열 구조를 정확히 파악
   - 헤더와 데이터를 명확히 구분
   - 병합된 셀이 있다면 적절히 처리

5. **가독성**:
   - 적절한 제목과 소제목 사용
   - 중요한 내용은 **굵게** 표시
   - 목록은 불릿 포인트 사용

**절대 금지 사항:**
- ❌ OCR 텍스트에 없는 단어 추가
- ❌ 숫자나 단어 변경
- ❌ 맥락에 맞지 않는 해석
- ❌ 추측이나 가정

**출력 형식:**
구조화된 마크다운만 출력하세요. 추가 설명이나 메타 정보는 제외하세요.
"""
        
        return prompt
    
    def _extract_with_ocr_fallback(
        self, 
        image: Image.Image, 
        description: str
    ) -> ExtractedContent:
        """OCR 폴백 (VLM 실패 시)"""
        
        text = self._extract_with_ocr(image)
        
        return ExtractedContent(
            type='text',
            content=text if text else "",
            metadata={'source': 'ocr_fallback', 'description': description},
            confidence=0.75 if text else 0.0
        )


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - 2-Pass Hybrid Extractor Test")
    print("="*60 + "\n")
    
    extractor = HybridExtractor(vlm_provider='claude', ocr_engine='tesseract')
    
    if extractor.claude:
        print("✅ 2-Pass extraction ready (OCR → VLM)")
        print("   Pass 1: OCR extracts accurate text")
        print("   Pass 2: VLM structures with OCR guidance")
    else:
        print("⚠️  VLM not available, using OCR only")
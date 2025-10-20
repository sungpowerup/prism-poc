"""
PRISM Phase 2.7 - Hybrid Content Extractor
OCR + VLM 하이브리드 컨텐츠 추출

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-20
Fixed: Anthropic client initialization (proxies 제거)
"""

import os
import base64
from io import BytesIO
from typing import Dict, Optional
from PIL import Image
from dataclasses import dataclass


# VLM Provider 임포트
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


@dataclass
class ExtractedContent:
    """추출된 컨텐츠"""
    type: str  # 'text', 'table', 'chart', 'image'
    content: str  # 추출된 내용
    metadata: Dict
    confidence: float = 0.0


class HybridExtractor:
    """
    하이브리드 컨텐츠 추출기
    
    전략:
    - TEXT 영역: OCR 우선 (정확한 원문)
    - TABLE 영역: VLM 구조화
    - CHART 영역: VLM 데이터 추출
    - IMAGE 영역: VLM 설명
    """
    
    def __init__(self, vlm_provider: str = 'claude'):
        """
        초기화
        
        Args:
            vlm_provider: VLM 프로바이더 ('claude', 'azure_openai', 'ollama')
        """
        self.vlm_provider = vlm_provider
        self.claude = None
        
        # VLM Provider별 클라이언트 초기화
        if vlm_provider == 'claude':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key and Anthropic:
                try:
                    # ✅ 수정: proxies 파라미터 완전 제거
                    self.claude = Anthropic(api_key=api_key)
                    print("✅ Claude API initialized for hybrid extraction")
                except Exception as e:
                    print(f"❌ Claude API initialization failed: {e}")
                    self.claude = None
            else:
                print("⚠️  Claude API key not found")
        
        # OCR 초기화 (옵션)
        self.ocr = None
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean',
                use_gpu=False,
                show_log=False
            )
            print("✅ HybridExtractor initialized with OCR + VLM")
        except ImportError:
            print("⚠️  PaddleOCR not available - using VLM only")
        except Exception as e:
            print(f"⚠️  PaddleOCR initialization failed: {e}")
        
        if not self.claude:
            print("⚠️  Claude API not available")
    
    def extract_content(
        self, 
        image: Image.Image, 
        region_type: str,
        page_text: str = ""
    ) -> ExtractedContent:
        """
        영역에서 컨텐츠 추출
        
        Args:
            image: 영역 이미지
            region_type: 'text', 'table', 'chart', 'image'
            page_text: 페이지 전체 텍스트 (OCR fallback용)
            
        Returns:
            ExtractedContent 객체
        """
        
        if region_type == 'text':
            return self._extract_text(image, page_text)
        elif region_type == 'table':
            return self._extract_table(image)
        elif region_type == 'chart':
            return self._extract_chart(image)
        elif region_type == 'image':
            return self._extract_image(image)
        else:
            # 알 수 없는 타입: 텍스트로 추출 시도
            return self._extract_text(image, page_text)
    
    def _extract_text(self, image: Image.Image, page_text: str = "") -> ExtractedContent:
        """텍스트 영역 추출 (OCR 우선)"""
        
        # 1. OCR 시도
        if self.ocr:
            try:
                import numpy as np
                result = self.ocr.ocr(np.array(image), cls=True)
                
                if result and result[0]:
                    lines = []
                    for line in result[0]:
                        text = line[1][0]
                        lines.append(text)
                    
                    content = '\n'.join(lines)
                    if content.strip():
                        return ExtractedContent(
                            type='text',
                            content=content,
                            metadata={'source': 'ocr'},
                            confidence=0.9
                        )
            except Exception as e:
                print(f"⚠️  OCR failed: {e}")
        
        # 2. Fallback: 페이지 전체 텍스트
        if page_text:
            return ExtractedContent(
                type='text',
                content=page_text,
                metadata={'source': 'fallback'},
                confidence=0.7
            )
        
        # 3. VLM 시도
        if self.claude:
            try:
                content = self._call_vlm(image, "텍스트를 추출하세요.")
                return ExtractedContent(
                    type='text',
                    content=content,
                    metadata={'source': 'vlm'},
                    confidence=0.8
                )
            except Exception as e:
                print(f"⚠️  VLM text extraction failed: {e}")
        
        # 최종 fallback
        return ExtractedContent(
            type='text',
            content="[텍스트 추출 실패]",
            metadata={'source': 'error'},
            confidence=0.0
        )
    
    def _extract_table(self, image: Image.Image) -> ExtractedContent:
        """표 추출 (VLM)"""
        
        if not self.claude:
            return ExtractedContent(
                type='table',
                content="[VLM 없음]",
                metadata={},
                confidence=0.0
            )
        
        try:
            prompt = """이 표를 마크다운 형식으로 변환하세요.

출력 형식:
```markdown
| 컬럼1 | 컬럼2 | 컬럼3 |
|-------|-------|-------|
| 값1   | 값2   | 값3   |
```

주의: 모든 값을 정확히 입력하세요."""

            content = self._call_vlm(image, prompt)
            
            return ExtractedContent(
                type='table',
                content=content,
                metadata={'source': 'vlm'},
                confidence=0.95
            )
            
        except Exception as e:
            print(f"⚠️  Table extraction failed: {e}")
            return ExtractedContent(
                type='table',
                content="[표 추출 실패]",
                metadata={},
                confidence=0.0
            )
    
    def _extract_chart(self, image: Image.Image) -> ExtractedContent:
        """차트 추출 (VLM)"""
        
        if not self.claude:
            return ExtractedContent(
                type='chart',
                content="[VLM 없음]",
                metadata={},
                confidence=0.0
            )
        
        try:
            prompt = """이 차트를 분석하여 다음 정보를 추출하세요:

1. 차트 타입 (bar/line/pie/...)
2. 제목
3. 모든 데이터 포인트 (레이블 + 값)

JSON 형식으로 출력:
```json
{
  "type": "차트타입",
  "title": "제목",
  "data": [
    {"label": "항목1", "value": 숫자},
    {"label": "항목2", "value": 숫자}
  ]
}
```"""

            content = self._call_vlm(image, prompt)
            
            return ExtractedContent(
                type='chart',
                content=content,
                metadata={'source': 'vlm'},
                confidence=0.9
            )
            
        except Exception as e:
            print(f"⚠️  Chart extraction failed: {e}")
            return ExtractedContent(
                type='chart',
                content="[차트 추출 실패]",
                metadata={},
                confidence=0.0
            )
    
    def _extract_image(self, image: Image.Image) -> ExtractedContent:
        """이미지/다이어그램 설명 (VLM)"""
        
        if not self.claude:
            return ExtractedContent(
                type='image',
                content="[VLM 없음]",
                metadata={},
                confidence=0.0
            )
        
        try:
            prompt = "이 이미지를 상세히 설명하세요 (2-3문장)."
            
            content = self._call_vlm(image, prompt)
            
            return ExtractedContent(
                type='image',
                content=content,
                metadata={'source': 'vlm'},
                confidence=0.85
            )
            
        except Exception as e:
            print(f"⚠️  Image description failed: {e}")
            return ExtractedContent(
                type='image',
                content="[이미지 설명 실패]",
                metadata={},
                confidence=0.0
            )
    
    def _call_vlm(self, image: Image.Image, prompt: str) -> str:
        """
        VLM API 호출
        
        Args:
            image: PIL Image
            prompt: 프롬프트
            
        Returns:
            응답 텍스트
        """
        # 이미지를 base64로 인코딩
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # API 호출
        response = self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
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
        if response.content and len(response.content) > 0:
            return response.content[0].text
        else:
            return ""


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Hybrid Extractor Test")
    print("="*60 + "\n")
    
    extractor = HybridExtractor(vlm_provider='claude')
    
    if extractor.claude:
        print("✅ Ready to extract content!")
    else:
        print("❌ Claude API not available")
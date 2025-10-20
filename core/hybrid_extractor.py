"""
PRISM Phase 2.7 - Hybrid Content Extractor
OCR + VLM 하이브리드 컨텐츠 추출

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-20
"""

import os
import base64
from io import BytesIO
from typing import Dict, Optional
from PIL import Image
from dataclasses import dataclass


# VLM Provider 임포트는 필요할 때만
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
                self.claude = Anthropic(api_key=api_key)
        
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
                image_array = np.array(image)
                
                result = self.ocr.ocr(image_array, cls=True)
                
                if result and result[0]:
                    lines = []
                    total_confidence = 0
                    
                    for line in result[0]:
                        text = line[1][0]
                        conf = line[1][1]
                        lines.append(text)
                        total_confidence += conf
                    
                    content = '\n'.join(lines)
                    confidence = total_confidence / len(result[0]) if result[0] else 0
                    
                    return ExtractedContent(
                        type='text',
                        content=content,
                        metadata={
                            'method': 'ocr',
                            'line_count': len(lines)
                        },
                        confidence=confidence
                    )
            
            except Exception as e:
                print(f"⚠️  OCR failed: {str(e)}")
        
        # 2. Fallback: PyMuPDF 텍스트
        if page_text:
            return ExtractedContent(
                type='text',
                content=page_text,
                metadata={'method': 'pymupdf'},
                confidence=0.8
            )
        
        # 3. 최종 Fallback: 빈 텍스트
        return ExtractedContent(
            type='text',
            content='[No text extracted]',
            metadata={'method': 'none'},
            confidence=0.0
        )
    
    def _extract_table(self, image: Image.Image) -> ExtractedContent:
        """표 영역 추출 (VLM 구조화)"""
        
        if not self.claude:
            # VLM 없을 때: OCR 폴백
            return self._extract_text(image)
        
        image_base64 = self._encode_image(image)
        
        prompt = """Extract this table into Markdown format.

**Requirements:**
1. Preserve header row
2. Align columns properly
3. Include all data
4. Use `|` for column separators
5. Use `---` for header separator

**Output format:**
```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

Extract now:"""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            content = message.content[0].text.strip()
            
            # Markdown 코드 블록 제거
            import re
            md_match = re.search(r'```markdown\s*(.*?)\s*```', content, re.DOTALL)
            if md_match:
                content = md_match.group(1)
            
            return ExtractedContent(
                type='table',
                content=content,
                metadata={'method': 'vlm'},
                confidence=0.9
            )
            
        except Exception as e:
            print(f"❌ Table extraction failed: {str(e)}")
            return ExtractedContent(
                type='table',
                content='[Table extraction failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _extract_chart(self, image: Image.Image) -> ExtractedContent:
        """차트 영역 추출 (VLM 데이터 추출)"""
        
        if not self.claude:
            return ExtractedContent(
                type='chart',
                content='[Chart - VLM not available]',
                metadata={'method': 'none'},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Describe this chart/graph.

**Include:**
1. Chart type (bar, pie, line, etc.)
2. Axis labels and units
3. Data values
4. Trends or patterns
5. Title/legend

**Format:**
```
Chart Type: [type]
Title: [title]
Data:
- [point 1]: [value]
- [point 2]: [value]
...
```

Describe now:"""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            content = message.content[0].text.strip()
            
            return ExtractedContent(
                type='chart',
                content=content,
                metadata={'method': 'vlm'},
                confidence=0.85
            )
            
        except Exception as e:
            print(f"❌ Chart extraction failed: {str(e)}")
            return ExtractedContent(
                type='chart',
                content='[Chart extraction failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _extract_image(self, image: Image.Image) -> ExtractedContent:
        """이미지 영역 추출 (VLM 설명)"""
        
        if not self.claude:
            return ExtractedContent(
                type='image',
                content='[Image - VLM not available]',
                metadata={'method': 'none'},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Describe this image briefly.

**Task:** Generate a factual, searchable description.

**Guidelines:**
1. Describe key visual elements
2. Identify objects, text, context
3. Note colors, layout, composition
4. Keep it factual (no interpretation)
5. 2-3 sentences maximum

Describe now:"""

        try:
            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            content = message.content[0].text.strip()
            
            return ExtractedContent(
                type='image',
                content=content,
                metadata={'method': 'vlm'},
                confidence=0.85
            )
            
        except Exception as e:
            print(f"❌ Image description failed: {str(e)}")
            return ExtractedContent(
                type='image',
                content='[Image description failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _encode_image(self, image: Image.Image) -> str:
        """이미지를 base64 인코딩"""
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Hybrid Extractor Test")
    print("="*60 + "\n")
    
    extractor = HybridExtractor(vlm_provider='claude')
    
    if extractor.claude:
        print("✅ Ready for hybrid extraction!")
    else:
        print("❌ VLM not available")
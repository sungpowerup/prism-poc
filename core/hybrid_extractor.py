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
from anthropic import Anthropic
from dataclasses import dataclass


@dataclass
class ExtractedContent:
    """추출된 컨텐츠"""
    type: str  # 'text', 'table', 'chart', 'image'
    content: str  # 추출된 내용
    metadata: Dict
    confidence: float


class HybridExtractor:
    """
    하이브리드 컨텐츠 추출기
    
    전략:
    - TEXT 영역: OCR 우선 (정확한 원문)
    - TABLE 영역: VLM 구조화
    - CHART 영역: VLM 데이터 추출
    - IMAGE 영역: VLM 설명
    """
    
    def __init__(self):
        """초기화"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.claude = Anthropic(api_key=api_key) if api_key else None
        
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
    
    def extract(self, region_image: Image.Image, region_type: str, description: str = "") -> ExtractedContent:
        """
        영역에서 컨텐츠 추출
        
        Args:
            region_image: 영역 이미지
            region_type: 'text', 'table', 'chart', 'image'
            description: 영역 설명
            
        Returns:
            ExtractedContent 객체
        """
        
        if region_type == 'text':
            return self._extract_text(region_image, description)
        elif region_type == 'table':
            return self._extract_table(region_image, description)
        elif region_type == 'chart':
            return self._extract_chart(region_image, description)
        elif region_type == 'image':
            return self._extract_image(region_image, description)
        else:
            # 알 수 없는 타입: VLM으로 범용 추출
            return self._extract_generic(region_image, description)
    
    def _extract_text(self, image: Image.Image, description: str) -> ExtractedContent:
        """텍스트 영역 추출 (OCR 우선)"""
        
        # 1. OCR 시도
        if self.ocr:
            try:
                import numpy as np
                img_array = np.array(image)
                result = self.ocr.ocr(img_array, cls=True)
                
                if result and result[0]:
                    # OCR 텍스트 추출
                    lines = []
                    total_confidence = 0.0
                    
                    for line in result[0]:
                        text = line[1][0]
                        confidence = line[1][1]
                        lines.append(text)
                        total_confidence += confidence
                    
                    content = '\n'.join(lines)
                    avg_confidence = total_confidence / len(result[0])
                    
                    return ExtractedContent(
                        type='text',
                        content=content,
                        metadata={
                            'method': 'ocr',
                            'description': description,
                            'line_count': len(lines)
                        },
                        confidence=avg_confidence
                    )
            except Exception as e:
                print(f"⚠️  OCR failed: {str(e)}, falling back to VLM")
        
        # 2. OCR 실패 시 VLM 사용
        return self._extract_text_vlm(image, description)
    
    def _extract_text_vlm(self, image: Image.Image, description: str) -> ExtractedContent:
        """VLM으로 텍스트 추출"""
        
        if not self.claude:
            return ExtractedContent(
                type='text',
                content='[VLM not available]',
                metadata={'method': 'none'},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Extract the EXACT text from this image region.

**Task:** Transcribe all text exactly as written.

**Rules:**
1. Preserve original text character-by-character
2. Maintain line breaks and formatting
3. Do NOT summarize or interpret
4. Do NOT add explanations
5. Return ONLY the extracted text

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
            
            return ExtractedContent(
                type='text',
                content=content,
                metadata={
                    'method': 'vlm',
                    'description': description
                },
                confidence=0.85
            )
            
        except Exception as e:
            print(f"❌ VLM text extraction failed: {str(e)}")
            return ExtractedContent(
                type='text',
                content='[Extraction failed]',
                metadata={'method': 'error', 'error': str(e)},
                confidence=0.0
            )
    
    def _extract_table(self, image: Image.Image, description: str) -> ExtractedContent:
        """표 추출 (VLM 구조화)"""
        
        if not self.claude:
            return ExtractedContent(
                type='table',
                content='[VLM not available]',
                metadata={},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Extract this table in markdown format.

**Task:** Convert the table to structured markdown.

**Output Format:**
```markdown
| Header1 | Header2 | Header3 |
|---------|---------|---------|
| Value1  | Value2  | Value3  |
| Value4  | Value5  | Value6  |
```

**Rules:**
1. Preserve exact values (numbers, text)
2. Maintain table structure
3. Use markdown table syntax
4. Do NOT add explanations
5. Return ONLY the markdown table

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
            
            # 마크다운 코드 블록 제거
            import re
            content = re.sub(r'```markdown\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            return ExtractedContent(
                type='table',
                content=content,
                metadata={
                    'method': 'vlm',
                    'description': description
                },
                confidence=0.90
            )
            
        except Exception as e:
            print(f"❌ Table extraction failed: {str(e)}")
            return ExtractedContent(
                type='table',
                content='[Extraction failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _extract_chart(self, image: Image.Image, description: str) -> ExtractedContent:
        """차트 데이터 추출 (VLM)"""
        
        if not self.claude:
            return ExtractedContent(
                type='chart',
                content='[VLM not available]',
                metadata={},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Extract data from this chart/graph.

**Task:** Convert chart to structured text data.

**Output Format:**
```
Chart Type: [pie/bar/line/etc.]
Title: [chart title]

Data:
- Label1: Value1 (unit)
- Label2: Value2 (unit)
- Label3: Value3 (unit)

Key Insight: [one sentence summary]
```

**Rules:**
1. Extract ALL data points accurately
2. Include units if shown
3. Preserve exact values
4. Identify chart type
5. Add brief insight

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
            
            return ExtractedContent(
                type='chart',
                content=content,
                metadata={
                    'method': 'vlm',
                    'description': description
                },
                confidence=0.88
            )
            
        except Exception as e:
            print(f"❌ Chart extraction failed: {str(e)}")
            return ExtractedContent(
                type='chart',
                content='[Extraction failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _extract_image(self, image: Image.Image, description: str) -> ExtractedContent:
        """이미지 설명 생성 (VLM)"""
        
        if not self.claude:
            return ExtractedContent(
                type='image',
                content='[VLM not available]',
                metadata={},
                confidence=0.0
            )
        
        image_base64 = self._encode_image(image)
        
        prompt = """Describe this image concisely for RAG retrieval.

**Task:** Generate a factual, searchable description.

**Guidelines:**
1. Describe key visual elements
2. Identify objects, people, text
3. Note colors, layout, composition
4. Keep it factual (no interpretation)
5. 2-3 sentences maximum

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
                type='image',
                content=content,
                metadata={
                    'method': 'vlm',
                    'description': description
                },
                confidence=0.85
            )
            
        except Exception as e:
            print(f"❌ Image description failed: {str(e)}")
            return ExtractedContent(
                type='image',
                content='[Extraction failed]',
                metadata={'error': str(e)},
                confidence=0.0
            )
    
    def _extract_generic(self, image: Image.Image, description: str) -> ExtractedContent:
        """범용 추출 (타입 불명)"""
        
        # TEXT로 시도
        return self._extract_text(image, description)
    
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
    
    extractor = HybridExtractor()
    
    if extractor.claude:
        print("✅ Ready for hybrid extraction!")
    else:
        print("❌ VLM not available")
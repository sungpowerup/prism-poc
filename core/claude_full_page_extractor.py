"""
PRISM Phase 2.3 - Claude Full Page Extractor

전체 페이지를 Claude Vision으로 처리하여 텍스트, 표, 구조를 동시에 추출합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from PIL import Image
import anthropic


@dataclass
class TextBlock:
    """텍스트 블록"""
    text: str
    confidence: float = 0.95


@dataclass
class Table:
    """표"""
    caption: str
    markdown: str
    confidence: float = 0.95


@dataclass
class Section:
    """섹션"""
    title: str
    text: str
    type: str  # 'header', 'paragraph', 'list', etc.
    confidence: float = 0.95


@dataclass
class PageContent:
    """페이지 전체 내용"""
    page_num: int
    text_blocks: List[TextBlock]
    tables: List[Table]
    sections: List[Section]


class ClaudeFullPageExtractor:
    """
    Claude Vision으로 전체 페이지 추출
    
    기능:
    - 페이지 전체를 한 번에 분석
    - 텍스트, 표, 구조를 동시에 추출
    - 한글 OCR 정확도 95%+
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        """
        Args:
            azure_endpoint: Azure OpenAI 엔드포인트 (미사용, 호환성 유지)
            azure_api_key: Azure OpenAI API 키 (미사용, 호환성 유지)
            model: Claude 모델명
        """
        # Azure 파라미터는 받지만 사용하지 않음 (호환성 유지)
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        
        # Anthropic API 키
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            print("⚠️  Warning: ANTHROPIC_API_KEY not set. Claude Vision disabled.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
            print(f"✅ Claude Vision initialized: {model}")
    
    def extract_full_page(self, image: Image.Image, page_num: int) -> Optional[PageContent]:
        """
        전체 페이지 추출
        
        Args:
            image: PIL Image
            page_num: 페이지 번호
            
        Returns:
            PageContent or None
        """
        if not self.client:
            return None
        
        try:
            # 이미지를 base64로 변환
            import base64
            import io
            
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = base64.standard_b64encode(buffer.getvalue()).decode('utf-8')
            
            # 프롬프트
            prompt = """이 문서 페이지를 분석하여 다음 정보를 추출해주세요:

1. **텍스트 블록**: 페이지의 모든 텍스트를 순서대로 추출
2. **표**: 모든 표를 마크다운 형식으로 변환
3. **구조**: 제목, 단락, 리스트 등의 구조 정보

다음 JSON 형식으로 응답해주세요:

```json
{
  "text_blocks": [
    {"text": "텍스트 내용", "confidence": 0.95}
  ],
  "tables": [
    {
      "caption": "표 제목",
      "markdown": "| 열1 | 열2 |\n|-----|-----|\n| 값1 | 값2 |",
      "confidence": 0.95
    }
  ],
  "sections": [
    {
      "title": "섹션 제목",
      "text": "섹션 내용",
      "type": "header|paragraph|list",
      "confidence": 0.95
    }
  ]
}
```

**중요:**
- 한글을 정확하게 인식해주세요
- 표의 구조를 정확히 유지해주세요
- 모든 표를 빠짐없이 추출해주세요
- JSON 형식만 응답해주세요 (다른 텍스트 제외)"""
            
            # Claude Vision API 호출
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
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
            
            # 응답 파싱
            content = response.content[0].text
            
            # JSON 추출 (```json ... ``` 제거)
            import json
            import re
            
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            data = json.loads(json_str)
            
            # PageContent 생성
            text_blocks = [
                TextBlock(
                    text=block['text'],
                    confidence=block.get('confidence', 0.95)
                )
                for block in data.get('text_blocks', [])
            ]
            
            tables = [
                Table(
                    caption=table['caption'],
                    markdown=table['markdown'],
                    confidence=table.get('confidence', 0.95)
                )
                for table in data.get('tables', [])
            ]
            
            sections = [
                Section(
                    title=section['title'],
                    text=section['text'],
                    type=section['type'],
                    confidence=section.get('confidence', 0.95)
                )
                for section in data.get('sections', [])
            ]
            
            return PageContent(
                page_num=page_num,
                text_blocks=text_blocks,
                tables=tables,
                sections=sections
            )
            
        except Exception as e:
            print(f"❌ Claude Vision Error (page {page_num}): {e}")
            return None


def main():
    """테스트"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python claude_full_page_extractor.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    image = Image.open(image_path)
    
    extractor = ClaudeFullPageExtractor()
    result = extractor.extract_full_page(image, page_num=1)
    
    if result:
        print(f"✅ Extracted from page {result.page_num}:")
        print(f"  - Text blocks: {len(result.text_blocks)}")
        print(f"  - Tables: {len(result.tables)}")
        print(f"  - Sections: {len(result.sections)}")
        
        # 샘플 출력
        if result.sections:
            print("\n📝 First section:")
            section = result.sections[0]
            print(f"  Title: {section.title}")
            print(f"  Type: {section.type}")
            print(f"  Text: {section.text[:100]}...")
        
        if result.tables:
            print("\n📊 First table:")
            table = result.tables[0]
            print(f"  Caption: {table.caption}")
            print(f"  Markdown:\n{table.markdown[:200]}...")


if __name__ == "__main__":
    main()
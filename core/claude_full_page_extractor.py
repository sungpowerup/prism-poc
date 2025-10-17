"""
PRISM Phase 2.4 - Claude Full Page Extractor with Chart Extraction

전체 페이지를 Claude Vision으로 분석하여 텍스트, 표, 차트, 그래프를 모두 추출

개선사항:
- 차트/그래프 명시적 추출
- 시각적 요소(다이어그램, 지도 등) 설명
- 데이터 포인트까지 상세 추출
- 529 에러 자동 재시도

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-16
"""

import os
import base64
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import io
import json
import re

# ✅ .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env file loaded")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")

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
class Chart:
    """차트/그래프"""
    type: str  # 'pie', 'bar', 'line', 'area', 'scatter', etc.
    title: str
    description: str
    data_points: List[Dict[str, Any]]  # [{"label": "남성", "value": 45.2, "unit": "%"}]
    confidence: float = 0.95


@dataclass
class Figure:
    """이미지/다이어그램"""
    type: str  # 'map', 'diagram', 'photo', 'illustration'
    description: str
    confidence: float = 0.95


@dataclass
class Section:
    """문서 섹션"""
    title: str
    text: str
    type: str  # 'paragraph', 'list', 'heading', 'caption'
    confidence: float = 0.95


@dataclass
class PageContent:
    """페이지 전체 내용"""
    page_num: int
    text_blocks: List[TextBlock]
    tables: List[Table]
    charts: List[Chart]
    figures: List[Figure]
    sections: List[Section]


class ClaudeFullPageExtractor:
    """
    Claude Vision API를 사용한 전체 페이지 추출기 (Phase 2.4)
    
    .env 파일 또는 환경변수에서 ANTHROPIC_API_KEY를 자동으로 읽습니다.
    """
    
    def __init__(self, api_key: Optional[str] = None, azure_endpoint: Optional[str] = None, azure_api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API 키 (없으면 .env 또는 환경변수에서 읽음)
            azure_endpoint: Azure OpenAI 엔드포인트 (미사용, 호환성용)
            azure_api_key: Azure OpenAI API 키 (미사용, 호환성용)
        """
        # API 키 우선순위: 파라미터 > 환경변수 > .env
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("=" * 60)
            print("❌ ANTHROPIC_API_KEY not found")
            print("=" * 60)
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print(f"✅ Claude Full Page Extractor (Phase 2.4) initialized")
            print(f"   API Key: {self.api_key[:20]}...{self.api_key[-4:]}")
        
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 8192
    
    def extract_full_page(
        self,
        page_image: Image.Image,
        page_num: int,
        max_retries: int = 3
    ) -> Optional[PageContent]:
        """
        전체 페이지를 분석하여 텍스트, 표, 차트, 그래프, 이미지 추출
        
        Args:
            page_image: PIL Image 객체
            page_num: 페이지 번호
            max_retries: 최대 재시도 횟수 (529 에러 대응)
            
        Returns:
            PageContent 또는 None (실패 시)
        """
        if not self.client:
            print(f"  ⚠️  Claude Vision unavailable (no API key)")
            return None
        
        # Retry 로직
        for attempt in range(max_retries):
            try:
                return self._extract_with_api(page_image, page_num)
            except Exception as e:
                error_msg = str(e)
                
                # 529 Overloaded Error 체크
                if '529' in error_msg or 'overloaded' in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 지수 백오프: 1초, 2초, 4초
                        print(f"  ⚠️  API Overloaded (attempt {attempt + 1}/{max_retries})")
                        print(f"  ⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ❌ Max retries reached for page {page_num}")
                        return None
                else:
                    # 다른 에러는 즉시 실패
                    print(f"❌ Claude Vision Error (page {page_num}): {e}")
                    import traceback
                    traceback.print_exc()
                    return None
        
        return None
    
    def _extract_with_api(
        self,
        page_image: Image.Image,
        page_num: int
    ) -> Optional[PageContent]:
        """
        실제 API 호출 (내부 메서드)
        """
        # 1. 이미지를 Base64로 인코딩
        buffer = io.BytesIO()
        page_image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 2. 프롬프트 준비
        prompt = self._create_full_page_prompt()
        
        # 3. Claude Vision API 호출
        print(f"  📡 Calling Claude Vision API (Phase 2.4) for page {page_num}...")
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
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
        
        # 4. 응답 파싱
        content = message.content[0].text
        
        # 디버깅: 응답 확인
        print(f"  📄 Response length: {len(content)} chars")
        
        # JSON 추출 (여러 패턴 시도)
        json_str = None
        
        # 패턴 1: ```json ... ```
        json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            print(f"  ✓ Found JSON in ```json block")
        else:
            # 패턴 2: { ... } (전체)
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print(f"  ✓ Found JSON in raw text")
        
        if not json_str:
            print(f"  ❌ No JSON found in response")
            print(f"  📄 Response preview: {content[:300]}...")
            return self._fallback_parse(content, page_num)
        
        # JSON 파싱 시도
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON Parse Error: {e}")
            print(f"  📄 JSON preview: {json_str[:500]}...")
            return self._fallback_parse(content, page_num)
        
        # PageContent 생성 (안전한 파싱)
        text_blocks = []
        for block in data.get('text_blocks', []):
            if isinstance(block, dict) and 'text' in block:
                text_blocks.append(TextBlock(
                    text=block['text'],
                    confidence=block.get('confidence', 0.95)
                ))
        
        tables = []
        for table in data.get('tables', []):
            if isinstance(table, dict) and 'markdown' in table:
                tables.append(Table(
                    caption=table.get('caption', ''),
                    markdown=table['markdown'],
                    confidence=table.get('confidence', 0.95)
                ))
        
        # ✅ 차트 파싱
        charts = []
        for chart in data.get('charts', []):
            if isinstance(chart, dict):
                charts.append(Chart(
                    type=chart.get('type', 'unknown'),
                    title=chart.get('title', ''),
                    description=chart.get('description', ''),
                    data_points=chart.get('data_points', []),
                    confidence=chart.get('confidence', 0.95)
                ))
        
        # ✅ 이미지/다이어그램 파싱
        figures = []
        for figure in data.get('figures', []):
            if isinstance(figure, dict):
                figures.append(Figure(
                    type=figure.get('type', 'unknown'),
                    description=figure.get('description', ''),
                    confidence=figure.get('confidence', 0.95)
                ))
        
        sections = []
        for section in data.get('sections', []):
            if isinstance(section, dict):
                section_text = section.get('text') or section.get('content', '')
                if section_text:
                    sections.append(Section(
                        title=section.get('title', ''),
                        text=section_text,
                        type=section.get('type', 'paragraph'),
                        confidence=section.get('confidence', 0.95)
                    ))
        
        print(f"  ✅ Extracted: {len(text_blocks)} text blocks, {len(tables)} tables, {len(charts)} charts, {len(figures)} figures, {len(sections)} sections")
        
        return PageContent(
            page_num=page_num,
            text_blocks=text_blocks,
            tables=tables,
            charts=charts,
            figures=figures,
            sections=sections
        )
    
    def _fallback_parse(self, content: str, page_num: int) -> Optional[PageContent]:
        """
        JSON 파싱 실패 시 간단한 텍스트 추출
        """
        print(f"  🔄 Attempting fallback parsing...")
        
        try:
            text_blocks = [TextBlock(text=content, confidence=0.8)]
            sections = [Section(
                title=f"Page {page_num}",
                text=content,
                type="paragraph",
                confidence=0.8
            )]
            
            print(f"  ✅ Fallback: Created 1 text block and 1 section")
            
            return PageContent(
                page_num=page_num,
                text_blocks=text_blocks,
                tables=[],
                charts=[],
                figures=[],
                sections=sections
            )
        except Exception as e:
            print(f"  ❌ Fallback parsing failed: {e}")
            return None
    
    def _create_full_page_prompt(self) -> str:
        """전체 페이지 분석 프롬프트 생성 (Phase 2.4)"""
        return """이 PDF 페이지의 모든 내용을 완전히 분석하여 JSON으로 반환해주세요.

**중요**: 
1. 반드시 완전한 JSON만 출력하세요. 설명이나 추가 텍스트 없이 순수 JSON만 반환하세요.
2. **모든 차트, 그래프, 다이어그램을 빠짐없이 찾아서 상세히 설명**하세요.
3. 차트의 **모든 데이터 포인트**(수치, 레이블, 단위)를 정확히 추출하세요.

**출력 형식**:
```json
{
  "text_blocks": [
    {"text": "페이지의 모든 텍스트를 순서대로", "confidence": 0.95}
  ],
  "tables": [
    {
      "caption": "표 제목 또는 설명",
      "markdown": "| 열1 | 열2 |\\n|-----|-----|\\n| 값1 | 값2 |",
      "confidence": 0.95
    }
  ],
  "charts": [
    {
      "type": "pie_chart",
      "title": "차트 제목",
      "description": "이 차트는 무엇을 보여주는지 1-2문장으로 설명",
      "data_points": [
        {"label": "항목명", "value": 45.2, "unit": "%"},
        {"label": "항목명2", "value": 54.8, "unit": "%"}
      ],
      "confidence": 0.95
    }
  ],
  "figures": [
    {
      "type": "map",
      "description": "이미지가 무엇을 보여주는지 2-3문장으로 상세히 설명",
      "confidence": 0.95
    }
  ],
  "sections": [
    {
      "title": "섹션 제목",
      "text": "섹션의 전체 내용",
      "type": "heading",
      "confidence": 0.95
    }
  ]
}
```

지금 분석을 시작하세요:"""


def main():
    """테스트"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python claude_full_page_extractor.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    image = Image.open(image_path)
    
    extractor = ClaudeFullPageExtractor()
    
    if not extractor.client:
        print("\n❌ Cannot proceed without API key")
        sys.exit(1)
    
    result = extractor.extract_full_page(image, page_num=1)
    
    if result:
        print(f"\n✅ Extracted from page {result.page_num}:")
        print(f"  - Text blocks: {len(result.text_blocks)}")
        print(f"  - Tables: {len(result.tables)}")
        print(f"  - Charts: {len(result.charts)}")
        print(f"  - Figures: {len(result.figures)}")
        print(f"  - Sections: {len(result.sections)}")
    else:
        print("\n❌ Failed to extract content")


if __name__ == "__main__":
    main()
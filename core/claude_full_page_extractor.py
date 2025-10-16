"""
PRISM Phase 2.4 - Claude Full Page Extractor with Chart Extraction

전체 페이지를 Claude Vision으로 분석하여 텍스트, 표, 차트, 그래프를 모두 추출

개선사항:
- 차트/그래프 명시적 추출
- 시각적 요소(다이어그램, 지도 등) 설명
- 데이터 포인트까지 상세 추출

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-16
"""

import os
import base64
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
    charts: List[Chart]  # ✅ 새로 추가
    figures: List[Figure]  # ✅ 새로 추가
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
            print("\n📋 .env 파일 확인:")
            print("   ANTHROPIC_API_KEY=sk-ant-...")
            print("\n💡 해결 방법:")
            print("  1. .env 파일이 프로젝트 루트에 있는지 확인")
            print("  2. .env 파일에 ANTHROPIC_API_KEY가 설정되어 있는지 확인")
            print("  3. 환경변수로 직접 설정 (PowerShell):")
            print("     $env:ANTHROPIC_API_KEY='sk-ant-...'")
            print("  4. 또는 Streamlit 재시작")
            print("=" * 60)
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print(f"✅ Claude Full Page Extractor (Phase 2.4) initialized")
            print(f"   API Key: {self.api_key[:20]}...{self.api_key[-4:]}")
        
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 8192  # ✅ Claude Sonnet의 최대값 (8192)
    
    def extract_full_page(
        self,
        page_image: Image.Image,
        page_num: int
    ) -> Optional[PageContent]:
        """
        전체 페이지를 분석하여 텍스트, 표, 차트, 그래프, 이미지 추출
        
        Args:
            page_image: PIL Image 객체
            page_num: 페이지 번호
            
        Returns:
            PageContent 또는 None (실패 시)
        """
        if not self.client:
            print(f"  ⚠️  Claude Vision unavailable (no API key)")
            return None
        
        try:
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
                charts=charts,  # ✅ 추가
                figures=figures,  # ✅ 추가
                sections=sections
            )
            
        except Exception as e:
            print(f"❌ Claude Vision Error (page {page_num}): {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
      "type": "pie_chart" | "bar_chart" | "line_chart" | "area_chart" | "scatter_plot" | "histogram",
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
      "type": "map" | "diagram" | "photo" | "illustration" | "icon",
      "description": "이미지가 무엇을 보여주는지 2-3문장으로 상세히 설명",
      "confidence": 0.95
    }
  ],
  "sections": [
    {
      "title": "섹션 제목",
      "text": "섹션의 전체 내용",
      "type": "heading" | "paragraph" | "list" | "caption",
      "confidence": 0.95
    }
  ]
}
```

**필드별 상세 가이드**:

1. **text_blocks**: 페이지의 모든 텍스트 (제목, 본문, 캡션 등)

2. **tables**: 표 형태의 데이터
   - Markdown 형식으로 정확히 변환
   - 모든 행과 열 포함

3. **charts** (중요!):
   - 원그래프(pie chart): 각 항목의 비율과 수치
   - 막대그래프(bar chart): 각 막대의 항목명과 값
   - 선그래프(line chart): 각 데이터 포인트의 좌표
   - 면적그래프(area chart): 영역의 값
   - 산점도(scatter plot): 점들의 분포
   - **data_points에 반드시 모든 수치를 포함**하세요

4. **figures**: 차트가 아닌 시각적 요소
   - 지도: 지역별 표시된 정보
   - 다이어그램: 구조나 관계 설명
   - 사진/일러스트: 내용 설명

5. **sections**: 문서의 논리적 구조

**예시 (차트가 있는 경우)**:
만약 "남성 45.2%, 여성 54.8%"를 보여주는 원그래프가 있다면:
```json
{
  "charts": [
    {
      "type": "pie_chart",
      "title": "응답자 성별 분포",
      "description": "응답자의 성별 분포를 보여주는 원그래프입니다. 여성이 54.8%로 남성 45.2%보다 높습니다.",
      "data_points": [
        {"label": "남성", "value": 45.2, "unit": "%"},
        {"label": "여성", "value": 54.8, "unit": "%"}
      ],
      "confidence": 0.99
    }
  ]
}
```

**규칙**:
1. 모든 텍스트를 빠짐없이 추출
2. 한국어와 영어를 정확히 인식
3. 표는 정확한 Markdown 형식으로
4. **차트/그래프를 절대 놓치지 마세요**
5. JSON은 반드시 완전하게 (잘리지 않도록)
6. 이스케이프 필요 시: \\" 사용

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
        
        # 샘플 출력
        if result.charts:
            print(f"\n📊 First chart:")
            chart = result.charts[0]
            print(f"  Type: {chart.type}")
            print(f"  Title: {chart.title}")
            print(f"  Description: {chart.description}")
            print(f"  Data points: {len(chart.data_points)}")
            for dp in chart.data_points[:3]:
                print(f"    - {dp}")
        
        if result.tables:
            print(f"\n📋 First table:")
            table = result.tables[0]
            print(f"  Caption: {table.caption}")
            print(f"  Markdown:\n{table.markdown[:200]}...")
    else:
        print("\n❌ Failed to extract content")


if __name__ == "__main__":
    main()
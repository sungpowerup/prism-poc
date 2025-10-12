"""
PRISM Phase 2.3 - Claude Vision Full Page Extractor

전체 페이지를 Claude Vision으로 처리하여 텍스트, 표, 구조를 모두 추출합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

import os
import base64
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from PIL import Image
import io

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic


@dataclass
class ExtractedSection:
    """추출된 섹션"""
    title: str
    content: str
    level: int  # 1=main, 2=sub, 3=subsub
    page_num: int


@dataclass
class ExtractedTable:
    """추출된 표"""
    title: str
    markdown: str
    description: str
    page_num: int
    num_rows: int
    num_cols: int
    confidence: float = 0.95


@dataclass
class PageContent:
    """페이지 전체 내용"""
    page_num: int
    main_title: str
    sections: List[ExtractedSection]
    tables: List[ExtractedTable]
    text_blocks: List[str]
    raw_json: Dict


class ClaudeFullPageExtractor:
    """
    Claude Vision으로 전체 페이지 분석
    
    추출 내용:
    - 문서 구조 (제목, 섹션 계층)
    - 모든 텍스트 (한글, 숫자, 특수문자)
    - 모든 표 (Markdown 형식)
    - 차트 설명
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API 키
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("❌ ANTHROPIC_API_KEY not found")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print(f"✅ Claude Full Page Extractor initialized")
    
    def extract_page(
        self,
        page_image: Image.Image,
        page_num: int
    ) -> Optional[PageContent]:
        """
        페이지 전체 분석
        
        Args:
            page_image: PIL Image 객체
            page_num: 페이지 번호
            
        Returns:
            추출된 페이지 내용
        """
        if not self.client:
            print("  ⚠️  Claude Vision unavailable")
            return None
        
        print(f"  🤖 Processing page {page_num} with Claude Vision...")
        
        try:
            # 1. 이미지를 base64로 인코딩
            buffered = io.BytesIO()
            page_image.save(buffered, format="PNG")
            image_data = base64.b64encode(buffered.getvalue()).decode()
            
            # 2. Claude Vision API 호출
            prompt = self._create_extraction_prompt()
            
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,  # 전체 페이지라 더 많은 토큰 필요
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
            
            # 3. 응답 파싱
            response_text = message.content[0].text
            
            # JSON 추출
            page_data = self._extract_json(response_text)
            
            if not page_data:
                print(f"  ⚠️  Failed to parse page {page_num}")
                return None
            
            # 4. PageContent 생성
            page_content = self._build_page_content(page_data, page_num)
            
            print(f"  ✅ Page {page_num} extracted:")
            print(f"     - Sections: {len(page_content.sections)}")
            print(f"     - Tables: {len(page_content.tables)}")
            print(f"     - Text blocks: {len(page_content.text_blocks)}")
            
            return page_content
            
        except Exception as e:
            print(f"  ❌ Error processing page {page_num}: {e}")
            return None
    
    def _create_extraction_prompt(self) -> str:
        """추출 프롬프트 생성"""
        return """이 문서 페이지를 완벽하게 분석하고 다음 형식의 JSON으로 응답해주세요.

**분석 요구사항:**

1. **문서 구조**: 제목과 섹션의 계층 구조를 파악하세요.
2. **텍스트**: 모든 텍스트를 정확히 추출하세요 (한글, 숫자, 특수문자, 띄어쓰기 보존).
3. **표**: 모든 표를 Markdown 형식으로 변환하세요.
4. **차트**: 차트가 있다면 내용을 설명하세요.

**JSON 형식:**

```json
{
  "main_title": "페이지의 주 제목 (예: 06 응답자 특성)",
  "sections": [
    {
      "title": "섹션 제목 (예: ☉ 응답자 성별 및 연령)",
      "level": 2,
      "content": "섹션 내용 (차트 설명 포함)",
      "has_chart": true,
      "chart_description": "차트에 대한 상세 설명"
    }
  ],
  "tables": [
    {
      "title": "표 제목",
      "markdown": "| 헤더1 | 헤더2 |\\n|---|---|\\n| 데이터1 | 데이터2 |",
      "description": "표에 대한 1-2문장 설명",
      "num_rows": 5,
      "num_cols": 3
    }
  ],
  "text_blocks": [
    "독립적인 텍스트 블록1",
    "독립적인 텍스트 블록2"
  ]
}
```

**중요 지침:**

1. 모든 한글을 **정확히** 인식하세요 (예: "일반국민", "프로스포츠").
2. 숫자와 단위를 정확히 보존하세요 (예: "35,000명", "58.4%").
3. 표의 **모든 행과 열**을 빠짐없이 추출하세요.
4. 표가 **여러 개**라면 각각 별도로 추출하세요.
5. 섹션 제목의 특수문자도 보존하세요 (예: "☉").
6. 응답은 **JSON만** 출력하고 다른 텍스트는 포함하지 마세요.

**JSON 응답:**"""
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """응답에서 JSON 추출"""
        try:
            # JSON 코드 블록 제거
            text = text.strip()
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.rindex("```")
                text = text[start:end].strip()
            elif "```" in text:
                start = text.index("```") + 3
                end = text.rindex("```")
                text = text[start:end].strip()
            
            return json.loads(text)
        except Exception as e:
            print(f"  ⚠️  JSON parse error: {e}")
            # 디버깅용 출력
            print(f"  Response preview: {text[:200]}...")
            return None
    
    def _build_page_content(
        self,
        data: Dict,
        page_num: int
    ) -> PageContent:
        """JSON 데이터를 PageContent 객체로 변환"""
        
        # 섹션 추출
        sections = []
        for sec in data.get("sections", []):
            sections.append(ExtractedSection(
                title=sec.get("title", ""),
                content=sec.get("content", ""),
                level=sec.get("level", 2),
                page_num=page_num
            ))
        
        # 표 추출
        tables = []
        for tbl in data.get("tables", []):
            tables.append(ExtractedTable(
                title=tbl.get("title", ""),
                markdown=tbl.get("markdown", ""),
                description=tbl.get("description", ""),
                page_num=page_num,
                num_rows=tbl.get("num_rows", 0),
                num_cols=tbl.get("num_cols", 0),
                confidence=0.95
            ))
        
        # 텍스트 블록
        text_blocks = data.get("text_blocks", [])
        
        return PageContent(
            page_num=page_num,
            main_title=data.get("main_title", ""),
            sections=sections,
            tables=tables,
            text_blocks=text_blocks,
            raw_json=data
        )


# 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("Claude Full Page Extractor Test")
    print("=" * 60)
    print()
    
    extractor = ClaudeFullPageExtractor()
    
    if not extractor.client:
        print("\n❌ Initialization failed")
    else:
        print("\n✅ Initialization successful!")
        print("\nTo test:")
        print("  streamlit run app_phase2.py")
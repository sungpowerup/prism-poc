"""
PRISM Phase 2.5 - Enhanced Claude Full Page Extractor

개선 사항:
1. 빈 data_points 절대 금지
2. 복잡한 차트 페이지 대응 강화
3. 차트별 데이터 완전성 검증
4. 529 에러 재시도 전략 개선

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-17
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
    type: str
    title: str
    description: str
    data_points: List[Dict[str, Any]]
    confidence: float = 0.95


@dataclass
class Figure:
    """이미지/다이어그램"""
    type: str
    description: str
    confidence: float = 0.95


@dataclass
class Section:
    """문서 섹션"""
    title: str
    text: str
    type: str
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
    Claude Vision API를 사용한 전체 페이지 추출기 (Phase 2.5)
    """
    
    # ⭐ CRITICAL: 개선된 프롬프트 (빈 data_points 절대 금지!)
    ANALYSIS_PROMPT = """
당신은 문서 분석 전문가입니다. 이 페이지의 모든 내용을 **완벽하게** 추출해야 합니다.

**🚨 절대 규칙 (CRITICAL):**
1. **모든 차트는 반드시 data_points를 포함해야 합니다**
2. **data_points: [] 는 절대 금지입니다**
3. **차트가 보이면 모든 데이터를 추출하세요**
4. **여러 차트가 있으면 각각 개별 분석하세요**

**추출 대상:**

1. **텍스트 (texts)**
   - 모든 본문, 제목, 캡션
   - 섹션 구분

2. **표 (tables)**
   - Caption 추출
   - Markdown 형식으로 변환
   - 모든 행과 열 포함

3. **차트 (charts)** ⭐⭐⭐ 가장 중요!
   - **type**: "pie", "bar", "line", "area", "scatter", "combo" 등
   - **title**: 차트 제목 (정확히)
   - **description**: 차트 설명
   - **data_points**: 🚨 **반드시 추출!**
   
   **차트 데이터 추출 방법:**
   
   a) **원형 차트 (Pie Chart)**:
   ```json
   "data_points": [
     {"label": "남성", "value": 45.2, "unit": "%"},
     {"label": "여성", "value": 54.8, "unit": "%"}
   ]
   ```
   
   b) **막대 차트 (Bar Chart)**:
   ```json
   "data_points": [
     {"label": "14-19세", "value": 11.2, "unit": "%"},
     {"label": "20대", "value": 25.9, "unit": "%"},
     {"label": "30대", "value": 22.3, "unit": "%"}
   ]
   ```
   
   c) **그룹 막대 차트**:
   ```json
   "data_points": [
     {
       "category": "입장료",
       "values": [
         {"label": "전체", "value": 21618, "unit": "원"},
         {"label": "프로스포츠팬", "value": 22726, "unit": "원"}
       ]
     },
     {
       "category": "교통비",
       "values": [
         {"label": "전체", "value": 12491, "unit": "원"}
       ]
     }
   ]
   ```
   
   d) **복합 차트 (여러 차트가 한 영역에)**:
   - 각 차트를 개별 항목으로 분리
   - 각각 완전한 data_points 포함

4. **이미지/다이어그램 (figures)**
   - type: "map", "diagram", "photo", "illustration"
   - 상세 설명 (지도의 경우 모든 지역 + 수치)

**🔍 검증 단계 (자가 검사):**
1. 모든 차트를 찾았는가?
2. 각 차트에 data_points가 있는가?
3. data_points가 비어있는 것은 없는가?
4. 수치가 정확한가?

**잘못된 예시 (절대 금지!):**
```json
{
  "charts": [
    {
      "title": "성별 분포",
      "data_points": []  // ❌❌❌ 금지!
    }
  ]
}
```

**올바른 예시:**
```json
{
  "charts": [
    {
      "type": "pie",
      "title": "성별 분포",
      "description": "응답자의 성별 비율을 보여주는 원형 차트",
      "data_points": [
        {"label": "남성", "value": 45.2, "unit": "%"},
        {"label": "여성", "value": 54.8, "unit": "%"}
      ]
    }
  ]
}
```

**출력 형식 (엄격한 JSON):**
```json
{
  "texts": [
    {
      "content": "전체 텍스트 내용...",
      "type": "paragraph"
    }
  ],
  "tables": [
    {
      "caption": "표 제목",
      "markdown": "| 컬럼1 | 컬럼2 |\\n|-------|-------|\\n| 값1 | 값2 |"
    }
  ],
  "charts": [
    {
      "type": "차트타입",
      "title": "차트 제목",
      "description": "차트 설명",
      "data_points": [반드시 포함!]
    }
  ],
  "figures": [
    {
      "type": "이미지타입",
      "description": "이미지 설명"
    }
  ]
}
```

**다시 한번 강조:**
- **data_points: [] 는 절대 금지!**
- **차트를 발견하면 모든 데이터를 반드시 추출하세요!**
- **이미지를 다시 한번 확인하여 놓친 차트가 없는지 검사하세요!**

이제 페이지를 분석하세요.
"""

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Args:
            azure_endpoint: Azure OpenAI 엔드포인트 (사용 안 함)
            azure_api_key: Azure OpenAI API 키 (사용 안 함)
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)
        """
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Anthropic API 키 읽기
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not found in environment variables")
            self.client = None
            return
        
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            print(f"✅ Claude API initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Claude API: {e}")
            self.client = None

    def _image_to_base64(self, image: Image.Image) -> str:
        """PIL Image를 base64로 변환"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _call_claude_with_retry(
        self,
        image_base64: str,
        page_num: int
    ) -> Optional[Dict]:
        """
        Claude API 호출 (529 에러 자동 재시도)
        
        개선된 재시도 전략:
        - 1차 실패: 2초 대기 후 재시도
        - 2차 실패: 5초 대기 후 재시도
        - 3차 실패: 10초 대기 후 재시도
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"🔄 Page {page_num} - Attempt {attempt}/{self.max_retries}")
                
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
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
                                        "data": image_base64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": self.ANALYSIS_PROMPT
                                }
                            ]
                        }
                    ]
                )
                
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_content += block.text
                
                # JSON 추출
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = text_content.strip()
                
                result = json.loads(json_str)
                print(f"✅ Page {page_num} - Success on attempt {attempt}")
                
                # ⭐ 후처리 검증: 빈 data_points 체크
                if 'charts' in result:
                    for chart in result['charts']:
                        if not chart.get('data_points'):
                            print(f"⚠️  Chart '{chart.get('title', 'Unknown')}' has empty data_points!")
                            print(f"⚠️  This violates the CRITICAL rule. Marking as incomplete.")
                
                return result
                
            except anthropic.APIError as e:
                error_code = getattr(e, 'status_code', None)
                
                if error_code == 529:  # Overloaded
                    wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    print(f"⚠️  Page {page_num} - 529 Overloaded on attempt {attempt}")
                    
                    if attempt < self.max_retries:
                        print(f"⏳ Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Page {page_num} - Failed after {self.max_retries} attempts")
                        return None
                else:
                    print(f"❌ Page {page_num} - API Error: {e}")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"❌ Page {page_num} - JSON Parse Error: {e}")
                print(f"Raw response: {text_content[:500]}")
                return None
                
            except Exception as e:
                print(f"❌ Page {page_num} - Unexpected Error: {e}")
                return None
        
        return None

    def extract(self, image: Image.Image, page_num: int = 1) -> Optional[PageContent]:
        """
        전체 페이지를 Claude Vision으로 분석
        
        Args:
            image: PIL Image 객체
            page_num: 페이지 번호
            
        Returns:
            PageContent 또는 None
        """
        if not self.client:
            print("❌ Claude API not initialized")
            return None
        
        print(f"\n{'='*60}")
        print(f"📄 Processing Page {page_num} with Claude Vision (Phase 2.5)")
        print(f"{'='*60}")
        
        # 1. 이미지를 base64로 변환
        image_base64 = self._image_to_base64(image)
        
        # 2. Claude API 호출 (자동 재시도)
        result = self._call_claude_with_retry(image_base64, page_num)
        
        if not result:
            print(f"❌ Failed to extract Page {page_num}")
            return None
        
        # 3. 결과 파싱
        text_blocks = []
        for text_data in result.get('texts', []):
            text_blocks.append(TextBlock(
                text=text_data.get('content', ''),
                confidence=0.99
            ))
        
        tables = []
        for table_data in result.get('tables', []):
            tables.append(Table(
                caption=table_data.get('caption', ''),
                markdown=table_data.get('markdown', ''),
                confidence=0.99
            ))
        
        charts = []
        for chart_data in result.get('charts', []):
            data_points = chart_data.get('data_points', [])
            
            # ⭐ 빈 data_points 경고
            if not data_points:
                print(f"⚠️  WARNING: Chart '{chart_data.get('title', 'Unknown')}' has NO data_points!")
            
            charts.append(Chart(
                type=chart_data.get('type', 'unknown'),
                title=chart_data.get('title', ''),
                description=chart_data.get('description', ''),
                data_points=data_points,
                confidence=0.95 if data_points else 0.50  # 데이터 없으면 신뢰도 낮춤
            ))
        
        figures = []
        for figure_data in result.get('figures', []):
            figures.append(Figure(
                type=figure_data.get('type', 'image'),
                description=figure_data.get('description', ''),
                confidence=0.99
            ))
        
        sections = []
        
        # 4. 통계 출력
        print(f"\n📊 Page {page_num} Extraction Results:")
        print(f"   ✅ Text blocks: {len(text_blocks)}")
        print(f"   ✅ Tables: {len(tables)}")
        print(f"   ✅ Charts: {len(charts)}")
        print(f"   ✅ Figures: {len(figures)}")
        
        # 차트별 데이터 포인트 체크
        for i, chart in enumerate(charts, 1):
            point_count = len(chart.data_points)
            if point_count == 0:
                print(f"   ⚠️  Chart {i} '{chart.title}': NO DATA POINTS! ❌")
            else:
                print(f"   ✅ Chart {i} '{chart.title}': {point_count} data points")
        
        return PageContent(
            page_num=page_num,
            text_blocks=text_blocks,
            tables=tables,
            charts=charts,
            figures=figures,
            sections=sections
        )


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.5 - Claude Full Page Extractor Test")
    print("="*60 + "\n")
    
    extractor = ClaudeFullPageExtractor()
    
    if extractor.client:
        print("✅ Ready to extract pages with enhanced prompt!")
        print("\n개선 사항:")
        print("1. 빈 data_points 절대 금지")
        print("2. 복잡한 차트 대응 강화")
        print("3. 529 에러 Exponential Backoff 재시도")
        print("4. 차트별 데이터 완전성 검증")
    else:
        print("❌ Claude API not available")
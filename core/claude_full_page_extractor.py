"""
PRISM Phase 2.7 - Claude Full Page Extractor
전체 페이지 한번에 추출 (개선된 프롬프트)

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
Fixed: Anthropic client initialization (proxies 파라미터 제거)
"""

import os
import base64
import json
import re
from io import BytesIO
from typing import Optional, Dict, List
from PIL import Image
from dataclasses import dataclass, asdict


try:
    import anthropic
except ImportError:
    anthropic = None


@dataclass
class PageContent:
    """페이지 콘텐츠 추출 결과"""
    texts: List[Dict]      # 텍스트 영역들
    tables: List[Dict]     # 표들
    charts: List[Dict]     # 차트들
    figures: List[Dict]    # 이미지/다이어그램들
    raw_response: str      # 원본 응답


class ClaudeFullPageExtractor:
    """
    Claude를 사용한 전체 페이지 추출기
    
    특징:
    - 한 번의 API 호출로 전체 페이지 분석
    - 차트 데이터 완벽 추출 강제
    - 구조화된 JSON 출력
    """
    
    # 강화된 프롬프트 (차트 데이터 추출 강제)
    SYSTEM_PROMPT = """당신은 문서 페이지를 완벽하게 분석하는 전문가입니다.

**핵심 원칙:**
1. **차트를 발견하면 반드시 모든 데이터를 추출하세요!**
2. **data_points: [] 는 절대 금지입니다!**
3. **누락 없이 완벽하게 추출하세요!**

**추출 대상 (우선순위):**

1. **차트 (charts) - 최우선!**
   - type: "bar", "line", "pie", "area", "scatter", "mixed"
   - title: 차트 제목
   - description: 차트가 보여주는 내용
   - **data_points: [반드시 모든 데이터 포함!]**
     - label: 레이블/카테고리
     - value: 정확한 수치
     - unit: 단위 (%, 명, 원, 개 등)
   
2. **표 (tables)**
   - caption: 표 제목/번호
   - markdown: 마크다운 표 형식
   - rows/columns: 행/열 수
   
3. **텍스트 (texts)**
   - content: 본문 텍스트
   - type: "heading", "paragraph", "list", "quote"
   
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
            # ✅ 수정: proxies 파라미터 제거
            self.client = anthropic.Anthropic(api_key=api_key)
            print(f"✅ Claude API initialized successfully")
        except Exception as e:
            print(f"❌ Claude API initialization failed: {e}")
            self.client = None
    
    def extract_page(self, page_image: Image.Image) -> PageContent:
        """
        페이지 전체 추출
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            PageContent 객체
        """
        if not self.client:
            print("⚠️  Claude API not available")
            return PageContent(
                texts=[{"content": "API not available", "type": "error"}],
                tables=[],
                charts=[],
                figures=[],
                raw_response=""
            )
        
        try:
            # 이미지를 base64로 인코딩
            buffered = BytesIO()
            page_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # API 호출
            response_text = self._call_api(img_base64)
            
            # 응답 파싱
            content = self._parse_response(response_text)
            
            return content
            
        except Exception as e:
            print(f"❌ Extraction error: {str(e)}")
            return PageContent(
                texts=[{"content": f"Error: {str(e)}", "type": "error"}],
                tables=[],
                charts=[],
                figures=[],
                raw_response=""
            )
    
    def _call_api(self, img_base64: str) -> str:
        """
        Claude API 호출
        
        Args:
            img_base64: base64 인코딩된 이미지
            
        Returns:
            응답 텍스트
        """
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
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
                            "text": self.SYSTEM_PROMPT
                        }
                    ]
                }]
            )
            
            # 응답 텍스트 추출
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return ""
                
        except Exception as e:
            print(f"❌ API call failed: {str(e)}")
            raise
    
    def _parse_response(self, response_text: str) -> PageContent:
        """
        응답 파싱
        
        Args:
            response_text: API 응답 텍스트
            
        Returns:
            PageContent 객체
        """
        try:
            # JSON 추출 (마크다운 코드 블록 제거)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSON 마커 없이 직접 파싱 시도
                json_str = response_text
            
            # JSON 파싱
            data = json.loads(json_str)
            
            return PageContent(
                texts=data.get('texts', []),
                tables=data.get('tables', []),
                charts=data.get('charts', []),
                figures=data.get('figures', []),
                raw_response=response_text
            )
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {str(e)}")
            print(f"Response preview: {response_text[:300]}...")
            
            # 파싱 실패 시 텍스트로 반환
            return PageContent(
                texts=[{"content": response_text, "type": "raw"}],
                tables=[],
                charts=[],
                figures=[],
                raw_response=response_text
            )
        
        except Exception as e:
            print(f"❌ Response parsing error: {str(e)}")
            return PageContent(
                texts=[{"content": f"Parsing error: {str(e)}", "type": "error"}],
                tables=[],
                charts=[],
                figures=[],
                raw_response=response_text
            )


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Claude Full Page Extractor Test")
    print("="*60 + "\n")
    
    extractor = ClaudeFullPageExtractor()
    
    if extractor.client:
        print("✅ Ready to extract pages!")
    else:
        print("❌ Claude API not available")
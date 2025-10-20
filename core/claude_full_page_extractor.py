"""
PRISM Phase 2.7 - Claude Full Page Extractor v2
전체 페이지 추출 (개선된 프롬프트 - 라벨 정확도 향상)

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
Update: 인포그래픽 라벨 정확도 개선
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
    Claude를 사용한 전체 페이지 추출기 v2
    
    개선사항:
    - 차트 라벨 정확도 향상
    - 복합 인포그래픽 해석 개선
    - 시각적 위치 고려
    """
    
    # 강화된 프롬프트 v2 (라벨 정확도 개선)
    SYSTEM_PROMPT = """당신은 문서 페이지를 완벽하게 분석하는 전문가입니다.

**🎯 최우선 원칙: 라벨 정확성**

**절대 규칙:**
1. **차트의 라벨은 이미지에 표시된 원본 텍스트를 그대로 추출**
2. **추측하거나 의미를 해석하지 말 것**
3. **보이는 그대로 정확히 복사**

**잘못된 예시 (절대 금지):**
```json
{
  "data": [
    {"label": "어시스트", "value": 13.9}  // ❌ 차트에 "14~19세"라고 쓰여있는데 추측함
  ]
}
```

**올바른 예시:**
```json
{
  "data": [
    {"label": "14~19세", "value": 13.9}  // ✅ 원본 그대로
  ]
}
```

---

**📋 추출 대상 (우선순위)**

### 1. **차트 (charts) - 최우선!**

**필수 필드:**
```json
{
  "type": "차트 타입",  // bar, pie, line, area, scatter, mixed
  "title": "차트 제목 (원본 그대로)",
  "description": "차트가 보여주는 내용 (1-2문장)",
  "data": [
    {
      "label": "라벨 (원본 텍스트 그대로!)",
      "value": 숫자,
      "unit": "단위"  // %, 명, 원, 개 등
    }
  ]
}
```

**복합 차트 (인포그래픽) 처리:**
- 여러 차트가 그룹으로 표시되면 **각각 별도 객체로 분리**
- 예: "KBL 통계" 인포그래픽에 파이차트 + 막대차트 + 원형차트가 있으면:
  ```json
  {
    "type": "infographic_group",
    "title": "KBL 통계",
    "charts": [
      {
        "type": "pie",
        "title": "성별 분포",
        "data": [...]
      },
      {
        "type": "bar",
        "title": "연령 분포",
        "data": [
          {"label": "14~19세", "value": 13.9},  // ← 원본 그대로!
          {"label": "20대", "value": 26.3}
        ]
      },
      {
        "type": "donut",
        "title": "관람행태",
        "data": [...]
      }
    ]
  }
  ```

**검증 단계 (자가 검사):**
1. 이미지를 다시 보고 라벨 확인
2. "어시스트", "리바운드" 같은 일반 명사가 라벨이면 의심
3. 숫자 옆에 표시된 실제 텍스트 재확인
4. 추측한 부분이 있으면 원본 확인

---

### 2. **표 (tables)**

```json
{
  "caption": "표 제목/번호",
  "markdown": "마크다운 표 형식",
  "rows": 행 수,
  "columns": 열 수
}
```

**마크다운 예시:**
```markdown
| 리그 | 비율 | 사례수 | 남 | 여 |
|------|------|--------|-----|-----|
| 프로야구 | 68.3 | 6,316 | 36.2 | 63.8 |
```

---

### 3. **텍스트 (texts)**

```json
{
  "content": "본문 텍스트 (원문 그대로)",
  "type": "heading/paragraph/list/quote"
}
```

---

### 4. **이미지/다이어그램 (figures)**

```json
{
  "type": "map/diagram/photo/illustration",
  "description": "이미지 설명",
  "elements": ["구성 요소 목록"]  // 지도의 경우 지역명 + 수치
}
```

**지도 예시:**
```json
{
  "type": "map",
  "description": "대한민국 권역별 응답자 분포",
  "elements": [
    "수도권: 52.5%",
    "경남권: 14.9%",
    "충청권: 10.3%"
  ]
}
```

---

**🔍 최종 검증 (출력 전 필수)**

1. **모든 차트 라벨이 원본과 일치하는가?**
   - ❌ "어시스트" → ✅ "사무직" (예시)
   - ❌ "득점" → ✅ "30대" (예시)

2. **data_points가 비어있지 않은가?**
   - ❌ `"data": []`
   - ✅ `"data": [{"label": "...", "value": ...}, ...]`

3. **수치가 정확한가?**
   - 차트의 눈금/레이블 재확인

4. **복합 차트를 제대로 분리했는가?**
   - 여러 차트가 있으면 각각 별도 객체

---

**📤 출력 형식 (엄격한 JSON)**

```json
{
  "texts": [
    {
      "content": "...",
      "type": "paragraph"
    }
  ],
  "tables": [
    {
      "caption": "...",
      "markdown": "..."
    }
  ],
  "charts": [
    {
      "type": "...",
      "title": "...",
      "data": [
        {"label": "원본 텍스트 그대로!", "value": 123, "unit": "%"}
      ]
    }
  ],
  "figures": [
    {
      "type": "...",
      "description": "..."
    }
  ]
}
```

---

**🚨 다시 한번 강조**

- **라벨은 절대 추측하지 마세요!**
- **이미지에 표시된 원본 텍스트를 정확히 복사하세요!**
- **"어시스트", "리바운드" 같은 일반 명사가 라벨이면 다시 확인하세요!**
- **data_points: [] 는 절대 금지!**

이제 페이지를 분석하세요. 라벨 정확성이 가장 중요합니다!
"""
    
    def __init__(self):
        """초기화"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key or not anthropic:
            raise ValueError("ANTHROPIC_API_KEY가 필요합니다")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def extract_page(self, page_image: Image.Image) -> PageContent:
        """
        페이지 전체 추출
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            PageContent 객체
        """
        
        # 이미지 → base64
        buffered = BytesIO()
        page_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # API 호출
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,  # 복잡한 페이지를 위해 증가
            temperature=0,     # 정확성 우선
            system=self.SYSTEM_PROMPT,
            messages=[
                {
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
                            "text": "위 이미지의 모든 콘텐츠를 JSON 형식으로 추출하세요. 특히 차트 라벨은 원본 텍스트를 정확히 복사하세요!"
                        }
                    ]
                }
            ]
        )
        
        response_text = message.content[0].text
        
        # JSON 파싱
        parsed = self._parse_response(response_text)
        
        return PageContent(
            texts=parsed.get('texts', []),
            tables=parsed.get('tables', []),
            charts=parsed.get('charts', []),
            figures=parsed.get('figures', []),
            raw_response=response_text
        )
    
    def _parse_response(self, response_text: str) -> Dict:
        """응답 파싱"""
        
        try:
            # JSON 블록 추출
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # 마크다운 없이 바로 JSON인 경우
                json_str = response_text.strip()
            
            # 파싱
            parsed = json.loads(json_str)
            
            return parsed
            
        except Exception as e:
            print(f"⚠️  JSON 파싱 실패: {e}")
            return {
                'texts': [],
                'tables': [],
                'charts': [],
                'figures': []
            }


# 사용 예시
if __name__ == '__main__':
    extractor = ClaudeFullPageExtractor()
    
    # 테스트 이미지
    test_image = Image.open('test.png')
    
    # 추출
    result = extractor.extract_page(test_image)
    
    print(f"📝 텍스트: {len(result.texts)}개")
    print(f"📊 차트: {len(result.charts)}개")
    print(f"📋 표: {len(result.tables)}개")
    print(f"🖼️  이미지: {len(result.figures)}개")
    
    # 차트 라벨 검증
    for chart in result.charts:
        print(f"\n차트: {chart.get('title')}")
        for dp in chart.get('data', []):
            print(f"  - {dp.get('label')}: {dp.get('value')}")
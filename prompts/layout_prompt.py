"""
prompts/layout_prompt.py
PRISM Phase 3.0 - Layout Detection VLM 프롬프트
"""

LAYOUT_CLASSIFICATION_PROMPT = """
이 이미지를 보고 영역 타입을 정확히 분류하세요.

가능한 타입:
- header: 섹션 제목 (☉ 기호, 큰 폰트, 좌측 정렬)
- chart: 차트/그래프 (축, 데이터 시각화, 색상)
- table: 표 (행/열 구조, 셀)
- map: 지도 (지역 경계, 지명, 색상 구역)
- text: 일반 텍스트 (문장, 단락)
- image: 사진/이미지

**한 단어로만 대답**하세요.

예시:
- "chart"
- "table"
- "map"

한 단어:"""


MAP_REGION_PROMPT = """
이 이미지는 대한민국 지역별 분포를 나타내는 지도입니다.

**모든 지역의 이름과 수치를 정확히 추출**하세요.

출력 형식 (JSON):
```json
{
  "type": "regional_map",
  "title": "지도 제목 (있는 경우)",
  "regions": [
    {"name": "수도권", "value": 52.5},
    {"name": "충청권", "value": 10.3},
    {"name": "전라권", "value": 7.8},
    {"name": "경남권", "value": 14.9},
    {"name": "경북권", "value": 9.8},
    {"name": "강원/제주", "value": 4.7}
  ],
  "unit": "%" (또는 해당 단위)
}
```

**CRITICAL 주의사항**:
1. 모든 지역을 빠짐없이 포함하세요
2. 수치는 소수점까지 정확히 추출하세요
3. 지역명은 원문 그대로 사용하세요
4. 지역의 순서는 상관없습니다
5. 비슷한 숫자끼리 혼동하지 마세요 (예: 10.3 ≠ 14.9)

**검증**:
- 모든 지역 포함 여부 확인
- 숫자 합계가 100 근처인지 확인 (퍼센트인 경우)
- 지역명 중복 없는지 확인

JSON만 출력하세요:"""


HEADER_EXTRACTION_PROMPT = """
이 이미지는 문서의 섹션 헤더입니다.

**헤더 텍스트를 정확히 추출**하세요.

특징:
- ☉ 기호로 시작할 수 있음
- 숫자로 시작할 수 있음 (예: "06 응답자 특성")
- 큰 폰트
- 짧은 한 줄

출력 형식 (JSON):
```json
{
  "type": "header",
  "level": 1 (또는 2, 3 - 계층 수준),
  "text": "정확한 헤더 텍스트",
  "has_symbol": true/false,
  "has_number": true/false
}
```

**주의사항**:
- 텍스트는 원문 그대로
- 기호(☉)는 제거하지 말고 포함
- 공백도 정확히

JSON만 출력하세요:"""


CHART_TYPE_PROMPT = """
이 차트의 타입을 정확히 식별하세요.

가능한 타입:
- pie: 원그래프/파이 차트
- bar: 막대그래프 (세로/가로)
- line: 선 그래프
- scatter: 산점도
- area: 영역 그래프
- mixed: 복합 차트
- unknown: 알 수 없음

출력 형식 (JSON):
```json
{
  "chart_type": "pie",
  "orientation": "horizontal" (bar인 경우만),
  "confidence": 0.95,
  "reasoning": "원형 차트가 명확하게 보입니다"
}
```

JSON만 출력하세요:"""


REGION_DESCRIPTION_PROMPT = """
이 영역을 간단히 설명하세요 (1-2문장).

포함할 내용:
- 영역의 타입 (차트/표/텍스트 등)
- 주요 내용 요약
- 특징적인 요소

출력 형식 (JSON):
```json
{
  "description": "이 영역은 응답자의 성별 분포를 나타내는 원그래프입니다.",
  "keywords": ["성별", "분포", "원그래프"],
  "confidence": 0.9
}
```

JSON만 출력하세요:"""
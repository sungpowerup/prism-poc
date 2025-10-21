"""
core/structured_prompts.py
구조화된 VLM 프롬프트 생성기

개선 사항:
1. 섹션 구조 명시적 추출
2. 차트 타입별 특화 프롬프트
3. 지역 데이터 정확도 강조
"""

from typing import Dict, List, Optional


class StructuredPrompts:
    """
    구조화된 프롬프트 생성기
    
    특징:
    - 섹션 헤더 강제 추출
    - 차트별 맞춤 프롬프트
    - 정확도 검증 요구
    """
    
    def __init__(self):
        self.base_instructions = """
당신은 문서 분석 전문가입니다.
주어진 페이지를 분석하여 구조화된 텍스트로 변환하세요.

**중요: 한글로만 응답하세요.**
"""
    
    def get_full_page_analysis_prompt(self) -> str:
        """
        전체 페이지 분석 프롬프트
        """
        return self.base_instructions + """

## 분석 요구사항

### 1. 섹션 구조 파악
- 페이지의 섹션 헤더를 정확히 추출하세요
- 예: "06. 응답자 특성", "☉ 응답자 성별 및 연령"
- **섹션 번호와 기호를 그대로 유지**하세요

### 2. 시각화 요소 분석
- 차트/그래프의 **정확한 타입**을 명시하세요
  - 원그래프, 막대그래프, 선그래프, 산점도 등
- 각 차트마다 **독립적으로 설명**하세요

### 3. 데이터 추출
- **모든 수치를 정확히** 기록하세요
- 지역 데이터는 **지역명과 값을 1:1 매칭**하세요
- 백분율은 소수점 첫째 자리까지 기록하세요

### 4. 인사이트
- 데이터에서 발견되는 패턴을 설명하세요
- 최댓값/최솟값, 추세를 명시하세요

## 출력 형식

```
### [섹션 헤더 그대로]

#### [하위 섹션]

**차트 1 - [차트 타입]**
이 차트는 [설명]입니다.

**데이터:**
- 항목1: 값1
- 항목2: 값2

**인사이트:**
[패턴 설명]

---

**차트 2 - [차트 타입]**
...
```

## ⚠️ 주의사항
- 섹션 구조를 **절대 무시하지 마세요**
- 차트 타입을 **명확히 구분**하세요
- 지역 데이터는 **철저히 검증**하세요
"""
    
    def get_chart_specific_prompt(self, chart_type: str) -> str:
        """
        차트별 특화 프롬프트
        
        Args:
            chart_type: 'pie', 'bar', 'line', 'table', 'map'
        """
        prompts = {
            'pie': self._pie_chart_prompt(),
            'bar': self._bar_chart_prompt(),
            'line': self._line_chart_prompt(),
            'table': self._table_prompt(),
            'map': self._map_prompt()
        }
        
        return prompts.get(chart_type, self.get_full_page_analysis_prompt())
    
    def _pie_chart_prompt(self) -> str:
        """원그래프 프롬프트"""
        return self.base_instructions + """

## 원그래프 분석

### 필수 정보
1. 차트 제목
2. 각 항목과 백분율 (정확히!)
3. 최대/최소 항목
4. 전체 합계가 100%인지 확인

### 출력 형식
```
**원그래프 - [제목]**

이 원그래프는 [무엇의 분포]를 나타냅니다.

**데이터:**
- 항목1: X.X%
- 항목2: Y.Y%
...

**인사이트:**
- 가장 큰 비율: 항목1 (X.X%)
- 가장 작은 비율: 항목N (Z.Z%)
```
"""
    
    def _bar_chart_prompt(self) -> str:
        """막대그래프 프롬프트"""
        return self.base_instructions + """

## 막대그래프 분석

### 필수 정보
1. X축, Y축 의미
2. 각 막대의 높이 (수치)
3. 순위 (내림차순)
4. 평균값

### 출력 형식
```
**막대그래프 - [제목]**

이 막대그래프는 [X축]별 [Y축]을 나타냅니다.

**데이터 (내림차순):**
1. 항목1: 값1
2. 항목2: 값2
...

**인사이트:**
- 평균: XX
- 최댓값: 항목1 (값1)
- 최솟값: 항목N (값N)
```
"""
    
    def _line_chart_prompt(self) -> str:
        """선그래프 프롬프트"""
        return self.base_instructions + """

## 선그래프 분석

### 필수 정보
1. X축 (시간/카테고리)
2. Y축 (측정값)
3. 추세 (증가/감소/변동)
4. 주요 변곡점

### 출력 형식
```
**선그래프 - [제목]**

이 선그래프는 [X축]에 따른 [Y축]의 변화를 나타냅니다.

**추세:**
- 전체 추세: [증가/감소/유지]
- 시작: 값1
- 종료: 값2
- 변화율: ±X%

**주요 포인트:**
- [시점]: 급등/급락
```
"""
    
    def _table_prompt(self) -> str:
        """표 프롬프트"""
        return self.base_instructions + """

## 표 분석

### 필수 정보
1. 표 제목
2. 열(Column) 헤더
3. 모든 행(Row) 데이터
4. 합계/평균 (있다면)

### 출력 형식
```
**표 - [제목]**

| 열1 | 열2 | 열3 |
|-----|-----|-----|
| 값1 | 값2 | 값3 |
...

**요약:**
- 총 N개 항목
- [주요 인사이트]
```
"""
    
    def _map_prompt(self) -> str:
        """지도 프롬프트"""
        return self.base_instructions + """

## 지도 분석 (⚠️ 고정확도 요구)

### 필수 정보
**모든 지역을 빠짐없이 기록하세요!**

1. 지도 제목
2. **전체 지역 목록** (순서대로)
3. 각 지역의 **정확한 값**
4. 단위 명시

### 출력 형식
```
**지도 - [제목]**

이 지도는 [무엇의 지역별 분포]를 나타냅니다. 단위: [단위]

**지역별 데이터:**
1. 지역1: X.X%
2. 지역2: Y.Y%
3. 지역3: Z.Z%
...

**인사이트:**
- 최고: 지역1 (X.X%)
- 최저: 지역N (N.N%)
- 평균: M.M%
```

## ⚠️ 특별 주의
- **지역명과 값을 절대 혼동하지 마세요**
- 경남권 ≠ 경북권
- 수도권 ≠ 충청권
- 모든 지역을 누락 없이 기록하세요
"""
    
    def build_prompt_with_context(
        self,
        element_type: str,
        page_number: int,
        total_pages: int,
        detected_regions: int = 1
    ) -> str:
        """
        컨텍스트를 포함한 프롬프트 생성
        
        Args:
            element_type: 감지된 element 타입
            page_number: 현재 페이지 번호
            total_pages: 전체 페이지 수
            detected_regions: 감지된 영역 수
        """
        context = f"""
## 문서 컨텍스트
- 페이지: {page_number}/{total_pages}
- 감지된 element 타입: {element_type}
- 영역 수: {detected_regions}개
"""
        
        # 타입별 프롬프트 선택
        if 'chart' in element_type.lower():
            base_prompt = self.get_chart_specific_prompt('bar')  # 기본 차트
        elif 'table' in element_type.lower():
            base_prompt = self.get_chart_specific_prompt('table')
        elif 'map' in element_type.lower():
            base_prompt = self.get_chart_specific_prompt('map')
        else:
            base_prompt = self.get_full_page_analysis_prompt()
        
        return context + "\n" + base_prompt


# 테스트
if __name__ == '__main__':
    prompts = StructuredPrompts()
    
    print("=== 전체 페이지 프롬프트 ===")
    print(prompts.get_full_page_analysis_prompt()[:500])
    print("\n...")
    
    print("\n=== 원그래프 프롬프트 ===")
    print(prompts.get_chart_specific_prompt('pie')[:500])
    print("\n...")
    
    print("\n=== 컨텍스트 포함 프롬프트 ===")
    contextual = prompts.build_prompt_with_context(
        element_type='chart',
        page_number=1,
        total_pages=3,
        detected_regions=2
    )
    print(contextual[:500])
    print("\n...")
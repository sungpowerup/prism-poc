"""
core/vlm_service.py
PRISM Phase 4.4 - VLM Service (강제 Complex 전략)

✅ Phase 4.4 개선사항:
1. 다이어그램 감지 → 무조건 Complex 전략
2. VLM 복잡도 판단 무시 (신뢰 불가)
3. 안전한 기본값: Complex
4. 더 엄격한 품질 평가

Author: 박준호 (AI/ML Lead)
Date: 2025-10-23
Version: 4.4
"""

import os
import logging
import re
from typing import Dict, Any, Optional, List
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV43:
    """
    Vision Language Model 서비스 v4.3
    
    Phase 4.3 특징:
    - 3-Step 지능형 처리
    - 복잡도 기반 전략 분기
    - 영역별 독립 처리
    - 환각 방지
    """
    
    def __init__(self, provider: str = "azure_openai"):
        """VLM 서비스 초기화"""
        self.provider = provider
        
        if provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            
            if not all([api_key, azure_endpoint, deployment]):
                raise ValueError("❌ Azure OpenAI 환경 변수 누락")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            self.deployment = deployment
            logger.info(f"✅ Azure OpenAI 초기화: {deployment}")
            
        elif provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("❌ ANTHROPIC_API_KEY 환경 변수 누락")
            
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
            logger.info(f"✅ Claude 초기화: {self.model}")
        
        else:
            raise ValueError(f"❌ 지원하지 않는 프로바이더: {provider}")
        
        logger.info(f"✅ VLM Service v4.3 초기화 완료: {provider}")
    
    def analyze_page_intelligent(
        self,
        image_data: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        3-Step 지능형 페이지 분석 (Phase 4.3)
        
        Step 1: 구조 분석 + 복잡도 판단
        Step 2A/B: 복잡도에 따라 전략 분기
        Step 3: 검증 & 통합
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
            
        Returns:
            {
                'content': str,
                'structure': dict,
                'confidence': float,
                'strategy': str  # 'simple' or 'complex'
            }
        """
        logger.info(f"🎯 Page {page_num}: 3-Step 지능형 분석 시작")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 1: 구조 분석 + 복잡도 판단
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 1] 구조 분석 + 복잡도 판단...")
        structure = self._analyze_structure(image_data)
        
        complexity = structure.get('complexity', 'medium')
        logger.info(f"  [Step 1] 복잡도: {complexity}")
        logger.info(f"  [Step 1] 감지: {structure.get('elements', [])}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 2: 전략 분기 (Phase 4.4: 다이어그램 강제 Complex)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # 🔥 Phase 4.4 핵심: 다이어그램이 있으면 무조건 Complex!
        has_diagram = 'diagram' in structure.get('elements', [])
        diagram_count = structure.get('diagram_count', 0)
        
        # 강제 Complex 조건
        force_complex = (
            has_diagram or 
            diagram_count >= 2 or 
            structure.get('estimated_data_points', 0) >= 40
        )
        
        if force_complex:
            logger.info(f"  [Step 2B] 복잡 처리 전략 (다이어그램 감지: {diagram_count}개)")
            content = self._extract_complex(image_data, structure)
            strategy = 'complex'
            
        else:
            logger.info(f"  [Step 2A] 단순 처리 전략 (단일 VLM)")
            content = self._extract_simple(image_data, structure)
            strategy = 'simple'
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 3: 검증
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 3] 검증 중...")
        is_valid, issues = self._validate_output(content, structure)
        
        if not is_valid:
            logger.warning(f"  [Step 3] 검증 실패: {issues}")
            # 재시도 또는 이슈 명시
            content = self._add_validation_notes(content, issues)
        
        confidence = self._calculate_confidence(content, structure)
        
        logger.info(f"  [완료] {len(content)} 글자, 신뢰도: {confidence:.2f}, 전략: {strategy}")
        
        return {
            'content': content,
            'structure': structure,
            'confidence': confidence,
            'strategy': strategy
        }
    
    def _analyze_structure(self, image_data: str) -> Dict:
        """Step 1: 구조 분석 + 복잡도 판단"""
        
        prompt = """당신은 문서 구조 분석 전문가입니다.

🎯 **임무: 이 페이지의 구조와 복잡도를 파악하세요**

다음을 분석하세요:

1. **페이지 제목/주제**
2. **주요 요소** (예: text, pie_chart, bar_chart, table, map, diagram)
3. **복잡도 판단**:
   - `simple`: 텍스트 + 차트 1~2개
   - `medium`: 차트 3~4개 또는 표 포함
   - `high`: 복잡한 다이어그램 3개 이상, 또는 50개 이상 데이터 포인트

4. **특수 요소**:
   - 지도 차트 여부
   - 복잡한 다이어그램 개수
   - 읽기 어려운 영역 존재 여부

JSON으로 응답:
```json
{
  "title": "페이지 제목",
  "elements": ["text", "pie_chart", "map", "diagram"],
  "complexity": "simple/medium/high",
  "diagram_count": 3,
  "has_map": true,
  "has_tiny_text": false,
  "estimated_data_points": 50
}
```

간단히 분석하세요!"""
        
        result = self._call_vlm(image_data, prompt, temperature=0.3)
        return self._parse_json_response(result)
    
    def _extract_simple(self, image_data: str, structure: Dict) -> str:
        """Step 2A: 단순 문서 처리 (단일 VLM)"""
        
        prompt = """당신은 전문 문서 분석가입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 임무: 이 페이지를 정확히 분석하세요

### ⚠️ 절대 준수 사항
1. **100% 원본 충실도** - 한 글자도 바꾸지 말 것
2. **숫자 정확성** - 반올림 금지, 소수점 그대로
3. **환각 방지** - 불확실하면 "읽기 불가" 명시

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 출력 형식

### 섹션 구분
- 각 독립 주제는 `---`로 구분
- RAG 친화적 청킹

### 예시:
```markdown
### [페이지 제목]

---

#### [섹션 1]

[자연어 설명]

**데이터:**
- 항목1: 값1
- 항목2: 값2

---

#### [섹션 2]

...
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 차트별 가이드

### 원그래프/막대그래프
- 정확한 백분율/값
- 합계 검증

### 표
- Markdown 표 형식
- 모든 셀 정확히

### 지도
- 지역명 그대로
- 라벨 정확히

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 분석을 시작하세요!"""
        
        return self._call_vlm(image_data, prompt, temperature=0.1)
    
    def _extract_complex(self, image_data: str, structure: Dict) -> str:
        """Step 2B: 복잡한 문서 처리 (분할 정복)"""
        
        diagram_count = structure.get('diagram_count', 1)
        
        prompt = f"""당신은 전문 문서 분석가입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 임무: 복잡한 문서를 정확히 분석하세요

### ⚠️ 이 페이지는 복잡합니다!
- 다이어그램 개수: {diagram_count}개
- 예상 데이터 포인트: {structure.get('estimated_data_points', 50)}개

### 🔥 중요: 환각 방지 전략
**읽을 수 없는 정류장/항목이 있다면:**
- ❌ 추측하지 마세요
- ❌ 같은 값을 반복하지 마세요
- ✅ "읽기 불가" 또는 "[불명확]"로 표시하세요

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 출력 형식

### 상단 정보
먼저 페이지 상단의 기본 정보를 추출하세요.

---

### 지도 (있는 경우)
지도에 표시된 라벨만 추출하세요.

---

### 다이어그램 영역

⚠️ **각 다이어그램을 독립적으로 처리하세요**

#### 다이어그램 1
**출발점**: [시작점]
**경유지**: 
- [정류장1]
- [정류장2]
- [읽기 불가]  ← 불명확하면 명시
- [정류장3]
**종점**: [종점]

#### 다이어그램 2
(동일 형식)

#### 다이어그램 3
(동일 형식)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ 체크리스트

출력 전 확인:
- [ ] 모든 다이어그램을 구분했는가?
- [ ] 불명확한 항목을 "읽기 불가"로 표시했는가?
- [ ] 같은 값을 불필요하게 반복하지 않았는가?
- [ ] 숫자를 정확히 추출했는가?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 분석을 시작하세요. 천천히, 정확하게!"""
        
        return self._call_vlm(image_data, prompt, temperature=0.1, max_tokens=6000)
    
    def _validate_output(self, content: str, structure: Dict) -> tuple[bool, List[str]]:
        """Step 3: 출력 검증"""
        issues = []
        
        # 1. 최소 길이
        if len(content) < 100:
            issues.append("내용이 너무 짧음")
        
        # 2. 반복 패턴 감지 (환각)
        lines = content.split('\n')
        line_counts = {}
        for line in lines:
            clean = line.strip()
            if len(clean) > 5 and clean.startswith('- '):
                line_counts[clean] = line_counts.get(clean, 0) + 1
        
        # 동일한 줄이 10번 이상 반복되면 환각
        for line, count in line_counts.items():
            if count >= 10:
                issues.append(f"반복 패턴 감지: '{line}' x{count}")
        
        # 3. 백분율 검증 (있는 경우)
        percentages = re.findall(r'(\d+\.?\d*)%', content)
        if len(percentages) >= 3:
            values = [float(p) for p in percentages]
            
            # 연속된 백분율 그룹이 100에 가까운지 확인
            valid_group = False
            for i in range(len(values)):
                group_sum = values[i]
                for j in range(i+1, min(i+10, len(values))):
                    group_sum += values[j]
                    if 99.0 <= group_sum <= 101.0:
                        valid_group = True
                        break
                if valid_group:
                    break
            
            if not valid_group and len(values) >= 5:
                issues.append(f"백분율 합계 이상: {sum(values):.1f}%")
        
        # 4. 다이어그램 개수 확인 (복잡한 경우)
        if structure.get('complexity') == 'high':
            expected = structure.get('diagram_count', 0)
            actual = content.count('#### 다이어그램')
            
            if expected > 0 and actual < expected:
                issues.append(f"다이어그램 누락: {actual}/{expected}")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _add_validation_notes(self, content: str, issues: List[str]) -> str:
        """검증 이슈를 명시"""
        notes = "\n\n---\n\n⚠️ **품질 이슈:**\n"
        for issue in issues:
            notes += f"- {issue}\n"
        
        return content + notes
    
    def _call_vlm(
        self,
        image_data: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """VLM API 호출"""
        
        try:
            if self.provider == "azure_openai":
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                result = response.choices[0].message.content
                
            elif self.provider == "claude":
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{
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
                            {"type": "text", "text": prompt}
                        ]
                    }]
                )
                result = message.content[0].text
            
            else:
                raise ValueError(f"지원하지 않는 프로바이더: {self.provider}")
            
            return result.strip() if result else ""
            
        except Exception as e:
            logger.error(f"❌ VLM API 오류: {e}")
            return ""
    
    def _parse_json_response(self, response: str) -> Dict:
        """JSON 응답 파싱"""
        import json
        
        try:
            # JSON 블록 찾기
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # JSON 블록 없으면 전체 파싱
            return json.loads(response)
            
        except Exception as e:
            logger.warning(f"⚠️ JSON 파싱 실패: {e}")
            # 기본값
            return {
                'title': 'Unknown',
                'elements': ['text'],
                'complexity': 'medium',
                'diagram_count': 0,
                'has_map': False,
                'estimated_data_points': 10
            }
    
    def _calculate_confidence(self, content: str, structure: Dict) -> float:
        """신뢰도 계산"""
        confidence = 0.95  # 기본값
        
        # 1. 길이 체크
        if len(content) < 200:
            confidence -= 0.15
        
        # 2. 반복 패턴 감지
        lines = content.split('\n')
        line_counts = {}
        for line in lines:
            clean = line.strip()
            if len(clean) > 5:
                line_counts[clean] = line_counts.get(clean, 0) + 1
        
        max_repeat = max(line_counts.values()) if line_counts else 1
        if max_repeat >= 10:
            confidence -= 0.2
        elif max_repeat >= 5:
            confidence -= 0.1
        
        # 3. "읽기 불가" 개수
        unreadable_count = content.count('읽기 불가') + content.count('[불명확]')
        if unreadable_count > 0:
            confidence -= min(0.1, unreadable_count * 0.02)
        
        # 4. 백분율 검증
        percentages = re.findall(r'(\d+\.?\d*)%', content)
        if len(percentages) >= 3:
            values = [float(p) for p in percentages]
            
            valid_group = False
            for i in range(len(values)):
                group_sum = values[i]
                for j in range(i+1, min(i+10, len(values))):
                    group_sum += values[j]
                    if 99.0 <= group_sum <= 101.0:
                        valid_group = True
                        break
                if valid_group:
                    break
            
            if not valid_group:
                confidence -= 0.1
        
        return max(0.5, min(1.0, confidence))
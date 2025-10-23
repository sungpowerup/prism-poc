"""
core/vlm_service.py
PRISM Phase 4.2 - VLM Service (멀티스텝 검증)

✅ Phase 4.2 개선사항:
1. 2-Pass Processing (구조 파악 → 정밀 추출)
2. 지도 차트 전용 프롬프트
3. 숫자 정확도 검증 강화
4. 범용 프롬프트 (하드코딩 제거)
5. 자동 청킹 (섹션 구분)

Author: 박준호 (AI/ML Lead)
Date: 2025-10-23
Version: 4.2
"""

import os
import logging
from typing import Dict, Any, Optional
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV42:
    """
    Vision Language Model 서비스 v4.2
    
    Phase 4.2 특징:
    - 2-Pass 멀티스텝 처리
    - 강화된 프롬프팅
    - 범용성 확보
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
        
        logger.info(f"✅ VLM Service v4.2 초기화 완료: {provider}")
    
    def analyze_page_multipass(
        self,
        image_data: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        2-Pass 멀티스텝 페이지 분석 (Phase 4.2)
        
        Pass 1: 구조 파악
        Pass 2: 정밀 추출
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
            
        Returns:
            {
                'content': str,  # 최종 Markdown
                'pass1_structure': dict,  # Pass 1 구조 정보
                'confidence': float  # 신뢰도
            }
        """
        logger.info(f"🎯 Page {page_num}: 2-Pass 분석 시작")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Pass 1: 구조 파악
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Pass 1] 구조 파악...")
        pass1_prompt = self._get_pass1_prompt()
        pass1_result = self._call_vlm(image_data, pass1_prompt, temperature=0.2)
        
        # Pass 1 결과 파싱
        structure = self._parse_structure(pass1_result)
        logger.info(f"  [Pass 1] 감지: {structure.get('chart_types', [])}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Pass 2: 정밀 추출
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Pass 2] 정밀 추출...")
        pass2_prompt = self._get_pass2_prompt(structure)
        pass2_result = self._call_vlm(image_data, pass2_prompt, temperature=0.1)
        
        # 최종 결과
        return {
            'content': pass2_result,
            'pass1_structure': structure,
            'confidence': self._calculate_confidence(pass2_result)
        }
    
    def _get_pass1_prompt(self) -> str:
        """Pass 1: 구조 파악 프롬프트"""
        return """당신은 문서 구조 분석 전문가입니다. 이 페이지의 구조를 파악하세요.

🎯 **목표: 레이아웃 이해 (데이터 추출 아님)**

다음 정보만 간단히 파악:
1. **페이지 제목/섹션**: 큰 제목이 있나요?
2. **차트 종류**: 원그래프, 막대그래프, 지도, 표 등 어떤 차트가 있나요?
3. **지도 차트 여부**: 한국 지도가 있나요? (지역 라벨 확인)
4. **섹션 개수**: 몇 개의 독립적인 섹션(☉, ◎ 등)으로 나뉘나요?

JSON으로 응답:
```json
{
  "title": "페이지 제목",
  "has_map_chart": true/false,
  "chart_types": ["pie", "bar", "map", "table"],
  "section_count": 3,
  "complexity": "simple/medium/high"
}
```

간단히! 데이터는 Pass 2에서 추출합니다."""
    
    def _get_pass2_prompt(self, structure: Dict) -> str:
        """Pass 2: 정밀 추출 프롬프트 (구조 정보 활용)"""
        
        has_map = structure.get('has_map_chart', False)
        complexity = structure.get('complexity', 'medium')
        
        base_prompt = """당신은 전문 문서 분석가입니다. 이 페이지를 **완벽한 정확도**로 분석하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 Phase 4.2 핵심 원칙

### ⚠️ 절대 준수 사항 (CRITICAL)

1. **100% 원본 충실도**
   - 텍스트를 **한 글자도** 바꾸지 말 것
   - 숫자를 **절대** 반올림하지 말 것
   - 지역명/단위를 **절대** 변경하지 말 것

2. **데이터 정확성 검증**
   - 백분율 합계가 99~101%인지 확인
   - 모든 숫자를 **두 번** 확인
   - 애매하면 **다시 보기**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 출력 형식

### 섹션 구분 규칙
- 각 독립적인 주제는 `---`로 구분
- RAG 친화적 청킹 제공

### 예시:
```markdown
### [페이지 제목]

---

#### [섹션 1 제목]

[자연어 설명]

**데이터:**
- 항목1: 값1
- 항목2: 값2

---

#### [섹션 2 제목]

[자연어 설명]

**데이터:**
- ...

---
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 차트별 가이드

### 원그래프/막대그래프
- 정확한 백분율 또는 값 추출
- 합계 검증 (99~101%)

### 표 (Table)
- Markdown 표 형식
- 모든 셀 정확히
"""

        # 지도 차트 특수 처리
        if has_map:
            base_prompt += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🗺️ 지도 차트 특별 지침 (CRITICAL)

⚠️ **이 페이지에는 한국 지도 차트가 있습니다!**

### 지도 읽기 방법:
1. **지도를 천천히 스캔**
   - 각 지역 라벨을 찾으세요
   - 라벨 옆 숫자를 정확히 읽으세요

2. **지역명 그대로 추출**
   - 보이는 그대로 작성 (변경 금지)
   - 예: "강원/제주" → "강원/제주" ✅
   - 예: "강원/제주" → "강원권", "제주권" ❌ (분리 금지!)

3. **숫자 정확히**
   - 소수점 이하까지
   - 반올림 금지

4. **검증**
   - 지역별 합계가 99~101%인지 확인
   - 틀리면 다시 읽기!

### 출력 예시:
```markdown
**권역별 분포:**
- 수도권: XX.X%
- 충청권: XX.X%
- 전라권: XX.X%
- 경북권: XX.X%
- 경남권: XX.X%
- 강원/제주권: XX.X%

(합계: 100.0%)
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        base_prompt += """
## ✅ 최종 체크리스트

출력 전에 확인:
- [ ] 모든 텍스트를 원본 그대로 추출
- [ ] 모든 숫자를 정확히 추출 (소수점 포함)
- [ ] 백분율 합계가 99~101% 범위
- [ ] 지역명/용어를 변경하지 않음
- [ ] 섹션을 `---`로 구분
- [ ] 자연어 설명 포함

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 분석을 시작하세요. **정확도가 생명입니다!**
"""
        
        return base_prompt
    
    def _call_vlm(
        self,
        image_data: str,
        prompt: str,
        temperature: float = 0.1
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
                    max_tokens=4000,
                    temperature=temperature
                )
                result = response.choices[0].message.content
                
            elif self.provider == "claude":
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
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
    
    def _parse_structure(self, pass1_result: str) -> Dict:
        """Pass 1 결과 파싱"""
        import json
        import re
        
        try:
            # JSON 블록 찾기
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', pass1_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # JSON 블록 없으면 전체 파싱 시도
            return json.loads(pass1_result)
            
        except Exception as e:
            logger.warning(f"⚠️ Pass 1 파싱 실패: {e}")
            # 기본값 반환
            return {
                'title': 'Unknown',
                'has_map_chart': False,
                'chart_types': [],
                'section_count': 1,
                'complexity': 'medium'
            }
    
    def _calculate_confidence(self, content: str) -> float:
        """신뢰도 계산"""
        import re
        
        # 백분율 검증
        percentages = re.findall(r'(\d+\.?\d*)%', content)
        
        if len(percentages) < 3:
            return 0.9  # 백분율 없으면 기본 신뢰도
        
        # 백분율 그룹 찾기
        values = [float(p) for p in percentages]
        
        # 연속된 백분율이 99~101% 합계를 이루는지 확인
        for i in range(len(values)):
            group_sum = values[i]
            for j in range(i+1, min(i+10, len(values))):
                group_sum += values[j]
                
                if 99.0 <= group_sum <= 101.0:
                    return 0.95  # 검증 성공
                
                if group_sum > 105.0:
                    break
        
        return 0.7  # 검증 실패
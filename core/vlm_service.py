"""
core/vlm_service.py
PRISM Phase 4.5 - VLM Service (OCR + VLM 하이브리드)

✅ Phase 4.5 개선사항:
1. OCR로 텍스트 추출 → VLM으로 구조 이해
2. 다이어그램 정확 감지 (비전 분석 강화)
3. 환각 방지 (OCR 텍스트 기반 검증)
4. RAG 최적화 (불필요 내용 제거)

Author: 박준호 (AI/ML Lead)
Date: 2025-10-23
Version: 4.5
"""

import os
import logging
import re
from typing import Dict, Any, Optional, List
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv
import base64
from io import BytesIO
from PIL import Image

# OCR 라이브러리
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available - OCR disabled")

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV45:
    """
    Vision Language Model 서비스 v4.5
    
    Phase 4.5 특징:
    - OCR + VLM 하이브리드
    - 다이어그램 정확 감지
    - 환각 방지
    - RAG 최적화
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
        
        logger.info(f"✅ VLM Service v4.5 초기화 완료: {provider}")
    
    def analyze_page_intelligent(
        self,
        image_data: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        OCR + VLM 하이브리드 페이지 분석 (Phase 4.5)
        
        Step 1: OCR로 텍스트 추출
        Step 2: VLM으로 구조 분석
        Step 3: OCR + VLM 통합 추출
        Step 4: 검증
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
            
        Returns:
            {
                'content': str,
                'structure': dict,
                'confidence': float,
                'strategy': str
            }
        """
        logger.info(f"🎯 Page {page_num}: OCR + VLM 하이브리드 분석 시작")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 1: OCR 텍스트 추출
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 1] OCR 텍스트 추출...")
        ocr_text = self._extract_text_ocr(image_data)
        
        if ocr_text:
            logger.info(f"  [Step 1] OCR 추출: {len(ocr_text)} 글자")
        else:
            logger.warning(f"  [Step 1] OCR 실패 - VLM 단독 사용")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 2: VLM 구조 분석
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 2] VLM 구조 분석...")
        structure = self._analyze_structure_enhanced(image_data)
        
        diagram_count = structure.get('diagram_count', 0)
        logger.info(f"  [Step 2] 다이어그램: {diagram_count}개")
        logger.info(f"  [Step 2] 요소: {structure.get('elements', [])}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 3: OCR + VLM 통합 추출
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 3] OCR + VLM 통합 추출...")
        
        if diagram_count >= 2 or structure.get('complexity') == 'high':
            # Complex: OCR 텍스트 활용
            content = self._extract_with_ocr(image_data, structure, ocr_text)
            strategy = 'complex_ocr'
        else:
            # Simple: VLM 단독
            content = self._extract_simple(image_data, structure)
            strategy = 'simple'
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 4: 검증
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"  [Step 4] 검증 중...")
        is_valid, issues = self._validate_output(content, structure, ocr_text)
        
        if not is_valid:
            logger.warning(f"  [Step 4] 검증 실패: {issues}")
        
        confidence = self._calculate_confidence(content, structure, ocr_text)
        
        logger.info(f"  [완료] {len(content)} 글자, 신뢰도: {confidence:.2f}, 전략: {strategy}")
        
        return {
            'content': content,
            'structure': structure,
            'confidence': confidence,
            'strategy': strategy
        }
    
    def _extract_text_ocr(self, image_data: str) -> str:
        """Step 1: OCR로 텍스트 추출"""
        if not TESSERACT_AVAILABLE:
            return ""
        
        try:
            # Base64 → PIL Image
            img_bytes = base64.b64decode(image_data)
            img = Image.open(BytesIO(img_bytes))
            
            # OCR 실행 (한글 + 영어)
            text = pytesseract.image_to_string(img, lang='kor+eng')
            return text.strip()
            
        except Exception as e:
            logger.warning(f"OCR 실패: {e}")
            return ""
    
    def _analyze_structure_enhanced(self, image_data: str) -> Dict:
        """Step 2: VLM 구조 분석 (강화)"""
        
        prompt = """당신은 문서 구조 분석 전문가입니다.

🎯 **임무: 이 페이지의 구조를 정확히 분석하세요**

### 🔍 중요: 다이어그램 개수 정확히 세기!

이 페이지에는 여러 개의 **노선도 다이어그램**이 있을 수 있습니다.
각 다이어그램은:
- 출발점에서 시작
- 여러 정류장을 거쳐
- 종점까지 연결되는 선형 구조

**반드시 모든 다이어그램을 세고 개수를 정확히 보고하세요!**

### 📋 분석 항목

1. **페이지 제목/주제**
2. **주요 요소** (text, map, diagram 등)
3. **다이어그램 개수** (정확히!)
4. **복잡도 판단**:
   - `simple`: 다이어그램 0~1개
   - `medium`: 다이어그램 2~3개
   - `high`: 다이어그램 4개 이상

5. **예상 데이터 포인트 수**

JSON으로 응답:
```json
{
  "title": "페이지 제목",
  "elements": ["text", "map", "diagram"],
  "diagram_count": 3,
  "complexity": "medium",
  "has_map": true,
  "estimated_data_points": 50
}
```

**다이어그램 개수를 정확히 세는 것이 가장 중요합니다!**"""
        
        result = self._call_vlm(image_data, prompt, temperature=0.3)
        structure = self._parse_json_response(result)
        
        # 다이어그램 개수 재검증
        diagram_count = structure.get('diagram_count', 0)
        if diagram_count >= 2:
            structure['complexity'] = 'high'
        
        return structure
    
    def _extract_with_ocr(self, image_data: str, structure: Dict, ocr_text: str) -> str:
        """Step 3: OCR + VLM 통합 추출 (Complex)"""
        
        diagram_count = structure.get('diagram_count', 1)
        
        # OCR 텍스트에서 정류장 이름 추출
        stop_names = self._extract_stop_names(ocr_text)
        
        prompt = f"""당신은 전문 문서 분석가입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 임무: 버스 노선도를 정확히 분석하세요

### ⚠️ 중요 정보

**이 페이지에는 {diagram_count}개의 다이어그램이 있습니다.**

**OCR로 추출된 정류장 이름:**
```
{chr(10).join(stop_names[:50])}
```

### 📋 출력 형식

#### 상단 정보
(노선명, 배차간격, 운행구간 등)

---

#### 지도 (있는 경우)
(지도에 표시된 주요 라벨)

---

#### 다이어그램 {diagram_count}개

각 다이어그램을 순서대로:

**다이어그램 1**
- 출발: [시작점]
- 경유:
  - [정류장1]
  - [정류장2]
  - ...
- 종점: [종점]

**다이어그램 2**
...

**다이어그램 {diagram_count}**
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ 필수 규칙

1. **OCR 텍스트 우선 사용**
   - 위의 OCR 정류장 이름을 최대한 활용하세요
   - 추측하지 말고 OCR 결과를 신뢰하세요

2. **{diagram_count}개 다이어그램 모두 추출**
   - 빠뜨리지 마세요!

3. **정류장 순서 정확히**
   - 노선도의 흐름대로 순서를 지키세요

4. **불필요한 내용 제거**
   - 체크리스트 ❌
   - 품질 이슈 ❌
   - 주석 최소화 ✅

5. **RAG 최적화**
   - 간결하고 명확하게
   - 중복 제거

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 분석을 시작하세요!"""
        
        return self._call_vlm(image_data, prompt, temperature=0.1, max_tokens=6000)
    
    def _extract_stop_names(self, ocr_text: str) -> List[str]:
        """OCR 텍스트에서 정류장 이름 추출"""
        if not ocr_text:
            return []
        
        # 한글이 포함된 라인만 추출
        lines = ocr_text.split('\n')
        stop_names = []
        
        for line in lines:
            clean = line.strip()
            # 한글이 있고, 3글자 이상, 50글자 이하
            if re.search(r'[가-힣]', clean) and 3 <= len(clean) <= 50:
                # 숫자만 있는 줄 제외
                if not clean.replace(' ', '').isdigit():
                    stop_names.append(clean)
        
        return stop_names
    
    def _extract_simple(self, image_data: str, structure: Dict) -> str:
        """Step 3: VLM 단독 추출 (Simple)"""
        
        prompt = """당신은 전문 문서 분석가입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 임무: 이 페이지를 정확히 분석하세요

### 📋 출력 형식

자연스러운 문장으로 설명하세요.

#### 섹션 구분
- `---`로 주요 섹션 구분
- RAG 친화적 청킹

#### 예시:
```markdown
#### [섹션 제목]

[자연어 설명]

**데이터:**
- 항목1: 값1
- 항목2: 값2

---

#### [다음 섹션]
...
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ 필수 규칙

1. **정확성 최우선**
2. **불필요한 내용 제거** (체크리스트, 품질 이슈 등)
3. **RAG 최적화** (간결, 명확)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 분석을 시작하세요!"""
        
        return self._call_vlm(image_data, prompt, temperature=0.1)
    
    def _validate_output(self, content: str, structure: Dict, ocr_text: str) -> tuple[bool, List[str]]:
        """Step 4: 출력 검증 (강화)"""
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
        
        for line, count in line_counts.items():
            if count >= 10:
                issues.append(f"반복 패턴 감지: '{line}' x{count}")
        
        # 3. 다이어그램 개수 확인
        expected_diagrams = structure.get('diagram_count', 0)
        actual_diagrams = content.count('**다이어그램')
        
        if expected_diagrams > 0 and actual_diagrams < expected_diagrams:
            issues.append(f"다이어그램 누락: {actual_diagrams}/{expected_diagrams}")
        
        # 4. OCR 텍스트 매칭 (있는 경우)
        if ocr_text and len(ocr_text) > 100:
            stop_names = self._extract_stop_names(ocr_text)
            if stop_names:
                # OCR에서 추출한 정류장 중 content에 없는 것
                missing = [name for name in stop_names[:20] if name not in content]
                if len(missing) > len(stop_names) * 0.5:  # 50% 이상 누락
                    issues.append(f"OCR 정류장 대량 누락: {len(missing)}/{len(stop_names[:20])}")
        
        # 5. 불필요한 내용 체크
        if '✅ 체크리스트' in content:
            issues.append("불필요한 체크리스트 포함")
        if '⚠️ **품질 이슈:**' in content:
            issues.append("불필요한 품질 이슈 섹션 포함")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
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
    
    def _calculate_confidence(self, content: str, structure: Dict, ocr_text: str) -> float:
        """신뢰도 계산 (강화)"""
        confidence = 0.95
        
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
        
        # 3. 다이어그램 개수 매칭
        expected = structure.get('diagram_count', 0)
        actual = content.count('**다이어그램')
        if expected > 0 and actual < expected:
            confidence -= 0.15
        
        # 4. OCR 매칭 (있는 경우)
        if ocr_text and len(ocr_text) > 100:
            stop_names = self._extract_stop_names(ocr_text)
            if stop_names:
                matched = sum(1 for name in stop_names[:20] if name in content)
                match_rate = matched / len(stop_names[:20])
                if match_rate < 0.5:
                    confidence -= 0.2
        
        # 5. 불필요한 내용
        if '✅ 체크리스트' in content or '⚠️ **품질 이슈:**' in content:
            confidence -= 0.05
        
        return max(0.5, min(1.0, confidence))
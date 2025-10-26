"""
core/vlm_service.py
PRISM Phase 5.1.1 - VLM Service (RAG 최적화 강화)
"""

import os
import logging
import json
import re
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

from .document_classifier import DocumentClassifierV50

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV50:
    """범용 VLM 서비스 v5.1.1 - RAG 최적화 강화"""
    
    def __init__(self, provider: str = "azure_openai"):
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
            
        elif provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("❌ ANTHROPIC_API_KEY 환경 변수 누락")
            
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        
        self.classifier = DocumentClassifierV50(provider)
        logger.info(f"✅ VLM Service v5.1.1 초기화 완료: {provider}")
    
    def analyze_page_v50(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """Phase 5.1.1: RAG 최적화 강화 문서 분석"""
        logger.info(f"🎯 Page {page_num}: Phase 5.1.1 분석 시작")
        
        doc_type_result = self.classifier.classify(image_data, page_num)
        doc_type = doc_type_result.get('type', 'mixed')
        subtype = doc_type_result.get('subtype', 'unknown')
        confidence = doc_type_result.get('confidence', 0.5)
        
        logger.info(f"✅ 타입: {doc_type} ({subtype}), 신뢰도: {confidence:.2f}")
        
        if doc_type == 'text_document':
            content = self._extract_text_document(image_data, subtype)
        elif doc_type == 'diagram':
            content = self._extract_diagram(image_data, subtype)
        elif doc_type == 'technical_drawing':
            content = self._extract_technical_drawing(image_data, subtype)
        elif doc_type == 'image_content':
            content = self._extract_image_content(image_data, subtype)
        elif doc_type == 'chart_statistics':
            content = self._extract_chart_statistics(image_data, subtype)
        else:
            content = self._extract_mixed(image_data)
        
        logger.info(f"✅ 추출 완료: {len(content)} 글자")
        
        quality_score = self._calculate_quality(content, doc_type)
        
        return {
            'content': content,
            'confidence': confidence,
            'strategy': f'{doc_type}_v511',
            'doc_type': doc_type,
            'subtype': subtype,
            'quality_score': quality_score,
            'structure': doc_type_result
        }
    
    def _extract_text_document(self, image_data: str, subtype: str) -> str:
        prompt = f"""이 {subtype} 문서의 내용을 Markdown으로 추출하세요.

**규칙:**
1. 원본 텍스트를 정확히 추출
2. 조항/항 번호 정확히 보존
3. 표는 Markdown 표로 변환

**절대 금지:**
- 메타 설명 ("이 이미지는", "다음과 같습니다", "아래는")
- 안내 문구 ("필요하신", "말씀해 주세요", "재구성 가능")
- 요약 섹션 ("**요약:**", "**구조 요약:**")

**오직 원본 내용만 출력하세요.**"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_diagram(self, image_data: str, subtype: str) -> str:
        if subtype == 'transport_route':
            prompt = """이 교통 노선도의 정보를 추출하세요.

**형식:**
## 노선 정보
**노선명**: [노선번호/이름]

### 경로
1. [정류장 1]
2. [정류장 2]

**절대 금지:**
- "다이어그램의 구조는", "필요하신", "재구성 가능" 등
- 오직 노선 정보만 출력"""
        else:
            prompt = """이 다이어그램의 정보를 추출하세요.

**절대 금지:**
- 메타 설명, 안내 문구, 요약
- 오직 다이어그램 내용만 출력"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_technical_drawing(self, image_data: str, subtype: str) -> str:
        prompt = """이 도면의 정보를 추출하세요.

## 평면도

### 공간 구성
1. **[공간 이름]** ([면적])
   - 위치: [방향/위치]
   - 치수: [가로 × 세로]

**절대 금지:**
- 메타 설명, 안내 문구
- 오직 도면 내용만 출력"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_image_content(self, image_data: str, subtype: str) -> str:
        prompt = """이 이미지를 객관적으로 설명하세요.

## 이미지 설명

### 주요 요소
- [요소]: [설명]

### 시각적 특징
- 색상: [주요 색상]
- 스타일: [스타일]

**절대 금지:**
- "이 이미지는", "아래는" 등 메타 설명
- 오직 이미지 내용만 출력"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_chart_statistics(self, image_data: str, subtype: str) -> str:
        prompt = """이 차트/표의 데이터를 추출하세요.

## 데이터

**차트 제목**: [제목]

### 데이터 테이블
| 항목 | 값 1 | 값 2 |
|------|------|------|
| 행 1 | [값] | [값] |

**절대 금지:**
- "아래는 이미지의 차트/표에서 추출한"
- "필요한 데이터가 더 있으면"
- 오직 차트/표 데이터만 출력"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_mixed(self, image_data: str) -> str:
        prompt = """이 문서의 내용을 Markdown으로 추출하세요.

**절대 금지:**
- 메타 설명, 안내 문구, 요약
- 오직 문서 내용만 출력"""
        return self._call_vlm(image_data, prompt)
    
    def _call_vlm(self, image_data: str, prompt: str) -> str:
        try:
            if self.provider == "azure_openai":
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image_data}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.2
                )
                return response.choices[0].message.content.strip()
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.2,
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
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                )
                return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"❌ VLM 호출 실패: {e}")
            return f"## 추출 실패\n오류: {str(e)}"
    
    def _calculate_quality(self, content: str, doc_type: str) -> float:
        score = 100.0
        if len(content) < 50:
            score -= 30
        headers = re.findall(r'^#+\s+', content, re.MULTILINE)
        if len(headers) == 0:
            score -= 20
        elif len(headers) >= 3:
            score += 10
        return max(0.0, min(100.0, score))
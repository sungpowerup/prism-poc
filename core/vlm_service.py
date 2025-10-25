"""
core/vlm_service.py
PRISM Phase 5.0 - VLM Service (범용 전략 패턴)
"""

import os
import logging
import json
import re
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

# ✅ 상대 임포트 사용
from .document_classifier import DocumentClassifierV50

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV50:
    """범용 VLM 서비스 v5.0"""
    
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
        logger.info(f"✅ VLM Service v5.0 초기화 완료: {provider}")
    
    def analyze_page_v50(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """Phase 5.0: 범용 문서 분석"""
        logger.info(f"🎯 Page {page_num}: Phase 5.0 범용 분석 시작")
        
        # Step 1: 문서 타입 판별
        doc_type_result = self.classifier.classify(image_data, page_num)
        doc_type = doc_type_result.get('type', 'mixed')
        subtype = doc_type_result.get('subtype', 'unknown')
        confidence = doc_type_result.get('confidence', 0.5)
        
        logger.info(f"✅ 타입: {doc_type} ({subtype}), 신뢰도: {confidence:.2f}")
        
        # Step 2-4: 타입별 전략 실행
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
        
        # Step 5: 품질 평가
        quality_score = self._calculate_quality(content, doc_type)
        
        return {
            'content': content,
            'confidence': confidence,
            'strategy': f'{doc_type}_v50',
            'doc_type': doc_type,
            'subtype': subtype,
            'quality_score': quality_score,
            'structure': doc_type_result
        }
    
    def _extract_text_document(self, image_data: str, subtype: str) -> str:
        prompt = f"""이 {subtype} 문서의 내용을 Markdown으로 추출하세요.

**중요 규칙:**
1. 원본 텍스트를 정확히 추출하세요
2. 조항/항 번호를 정확히 보존하세요
3. 표가 있으면 Markdown 표로 변환하세요
4. 메타 정보는 최소화하세요
5. 간결하게 작성하세요"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_diagram(self, image_data: str, subtype: str) -> str:
        if subtype == 'transport_route':
            prompt = """이 교통 노선도를 분석하여 노선 정보를 추출하세요.

**형식:**
## 노선 정보
**노선명**: [노선번호/이름]

### 경로
1. [출발지]
2. [경유지 1]
...

**주의:** 정류장/역 이름을 정확히 추출하고 순서를 지키세요."""
        else:
            prompt = """이 다이어그램을 분석하여 구조를 추출하세요."""
        return self._call_vlm(image_data, prompt)
    
    def _extract_technical_drawing(self, image_data: str, subtype: str) -> str:
        prompt = """이 도면을 분석하여 공간 정보를 추출하세요.

**형식:**
## 평면도

### 공간 구성
1. **[공간 이름]** ([면적])
   - 위치: [방향/위치]
   - 치수: [가로 × 세로]"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_image_content(self, image_data: str, subtype: str) -> str:
        prompt = """이 이미지를 객관적으로 설명하세요.

**형식:**
## 이미지 설명

### 주요 요소
- [요소]: [설명]

### 시각적 특징
- 색상: [주요 색상]
- 스타일: [스타일]"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_chart_statistics(self, image_data: str, subtype: str) -> str:
        prompt = """이 차트/표를 분석하여 데이터를 추출하세요.

**형식:**
## 데이터

**차트 제목**: [제목]

### 데이터 테이블
| 항목 | 값 1 | 값 2 |
|------|------|------|
| 행 1 | [값] | [값] |"""
        return self._call_vlm(image_data, prompt)
    
    def _extract_mixed(self, image_data: str) -> str:
        prompt = """이 문서의 내용을 Markdown으로 추출하세요."""
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
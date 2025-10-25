"""
core/document_classifier.py
PRISM Phase 5.0 - Document Type Classifier
"""

import os
import logging
import json
import re
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DocumentClassifierV50:
    """문서 타입 분류기 v5.0"""
    
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
        
        logger.info(f"✅ DocumentClassifierV50 초기화 완료")
    
    def classify(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """문서 타입 판별"""
        logger.info(f"📋 문서 타입 판별 시작 (Page {page_num})")
        
        prompt = """이 문서의 타입을 정확히 판별하세요.

**문서 타입:**
1. text_document: 규정/계약서/보고서
2. diagram: 노선도/플로우차트/조직도
3. technical_drawing: 도면
4. image_content: 사진
5. chart_statistics: 차트/표
6. mixed: 복합

**JSON으로만 응답:**
```json
{
  "type": "text_document",
  "subtype": "regulation",
  "confidence": 0.95,
  "reasoning": "이유"
}
```"""
        
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
                    max_tokens=800,
                    temperature=0.1
                )
                result_text = response.choices[0].message.content.strip()
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=800,
                    temperature=0.1,
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
                result_text = response.content[0].text.strip()
            
            # JSON 추출
            result_text = re.sub(r'^```json\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
            result = json.loads(result_text.strip())
            
            doc_type = result.get('type', 'mixed')
            subtype = result.get('subtype', 'unknown')
            confidence = result.get('confidence', 0.5)
            
            logger.info(f"✅ 타입: {doc_type} ({subtype}), 신뢰도: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 문서 타입 판별 실패: {e}")
            return {
                'type': 'mixed',
                'subtype': 'unknown',
                'confidence': 0.3,
                'reasoning': f'오류: {str(e)}'
            }
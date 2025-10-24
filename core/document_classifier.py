"""
core/document_classifier_v50.py
PRISM Phase 5.0 - Document Type Classifier (범용 문서 타입 분류기)

✅ Phase 5.0 핵심 특징:
1. VLM 기반 문서 타입 자동 판별
2. 7가지 주요 문서 타입 지원
3. 문서 특성 분석
4. 하드코딩 제로 (완전 범용)

지원 문서 타입:
- text_document: 공공기관 사규, 계약서, 보고서
- diagram: 버스 노선도, 플로우차트, 조직도
- technical_drawing: 인테리어 도면, 설계도
- image_content: 패션 사진, 제품 사진
- chart_statistics: 통계표, 차트
- mixed: 복합 문서

Author: 박준호 (AI/ML Lead)
Date: 2025-10-24
Version: 5.0
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
    """
    문서 타입 분류기 v5.0
    
    특징:
    - VLM 기반 자동 판별
    - 완전 범용 설계
    - 문서 특성 상세 분석
    """
    
    def __init__(self, provider: str = "azure_openai"):
        """분류기 초기화"""
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
        
        logger.info(f"✅ DocumentClassifierV50 초기화 완료")
    
    def classify(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """
        문서 타입 판별 (Phase 5.0)
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
        
        Returns:
            {
                'type': 'text_document',
                'subtype': 'regulation',
                'confidence': 0.95,
                'characteristics': {
                    'has_text': True,
                    'has_diagram': False,
                    'has_table': True,
                    'has_image': False,
                    'layout': 'hierarchical',
                    'language': 'korean'
                }
            }
        """
        logger.info(f"📋 문서 타입 판별 시작 (Page {page_num})")
        
        prompt = """이 문서의 타입을 정확히 판별하세요.

**문서 타입 분류:**

1. **text_document** (텍스트 중심 문서)
   - regulation: 규정/규칙/사규 (조항, 제1조, 제2조 등)
   - contract: 계약서 (갑/을, 계약 조항)
   - report: 보고서 (목차, 섹션, 분석 내용)
   - manual: 매뉴얼 (설명서, 가이드)
   - letter: 공문/서신

2. **diagram** (다이어그램 중심)
   - transport_route: 교통 노선도 (버스, 지하철)
   - flowchart: 순서도/프로세스
   - organization: 조직도
   - network: 네트워크 다이어그램
   - mind_map: 마인드맵

3. **technical_drawing** (기술 도면)
   - interior: 인테리어 평면도
   - architecture: 건축 도면
   - engineering: 공학 설계도
   - blueprint: 청사진

4. **image_content** (이미지 콘텐츠)
   - product_photo: 제품 사진
   - fashion: 패션/의류 사진
   - lifestyle: 라이프스타일 이미지
   - advertisement: 광고 이미지

5. **chart_statistics** (차트/통계)
   - bar_chart: 막대 차트
   - pie_chart: 원형 차트
   - line_chart: 선 차트
   - table: 표/테이블
   - infographic: 인포그래픽

6. **mixed** (복합 문서)
   - 여러 타입이 혼합된 문서

**판별 기준:**
- 문서의 주요 내용이 무엇인지 (텍스트/다이어그램/이미지/차트)
- 문서의 목적 (규정/계약/설명/분석/홍보)
- 레이아웃 구조 (계층적/다이어그램/표/이미지)

**JSON 형식으로만 응답하세요:**
```json
{
  "type": "text_document",
  "subtype": "regulation",
  "confidence": 0.95,
  "characteristics": {
    "has_text": true,
    "has_diagram": false,
    "has_table": true,
    "has_image": false,
    "text_density": "high",
    "layout": "hierarchical",
    "language": "korean",
    "primary_content": "legal text with articles"
  },
  "reasoning": "문서에 제1조, 제2조 등 조항이 명확히 보이며, 계층적 구조를 가진 규정 문서입니다."
}
```

**중요:**
- JSON만 출력하세요 (```json 태그 포함 가능)
- 문서를 정확히 분석하세요
- confidence는 0.0~1.0 사이 값
"""
        
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
                    temperature=0.1  # 일관성 우선
                )
                
                result_text = response.choices[0].message.content.strip()
                
            else:  # claude
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
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            doc_type = result.get('type', 'mixed')
            subtype = result.get('subtype', 'unknown')
            confidence = result.get('confidence', 0.5)
            
            logger.info(f"✅ 타입: {doc_type} ({subtype}), 신뢰도: {confidence:.2f}")
            logger.info(f"   이유: {result.get('reasoning', 'N/A')[:100]}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            logger.error(f"   응답: {result_text[:200]}")
            
            # 폴백: mixed 타입
            return {
                'type': 'mixed',
                'subtype': 'unknown',
                'confidence': 0.3,
                'characteristics': {
                    'has_text': True,
                    'has_diagram': False,
                    'has_table': False,
                    'has_image': False,
                    'layout': 'unknown',
                    'language': 'unknown'
                },
                'reasoning': 'VLM 응답 파싱 실패',
                'error': str(e)
            }
        
        except Exception as e:
            logger.error(f"❌ 문서 타입 판별 실패: {e}")
            
            # 폴백
            return {
                'type': 'mixed',
                'subtype': 'unknown',
                'confidence': 0.3,
                'characteristics': {
                    'has_text': True,
                    'has_diagram': False,
                    'has_table': False,
                    'has_image': False,
                    'layout': 'unknown',
                    'language': 'unknown'
                },
                'reasoning': '예외 발생',
                'error': str(e)
            }
    
    def get_document_category(self, doc_type: str) -> str:
        """
        문서 타입 → 카테고리 매핑
        
        Returns:
            'text', 'visual', 'data', 'mixed'
        """
        category_map = {
            'text_document': 'text',
            'diagram': 'visual',
            'technical_drawing': 'visual',
            'image_content': 'visual',
            'chart_statistics': 'data',
            'mixed': 'mixed'
        }
        
        return category_map.get(doc_type, 'mixed')
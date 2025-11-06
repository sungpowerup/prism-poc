"""
core/vlm_service.py
PRISM Phase 0 Hotfix - VLM Service with Retry Logic

✅ Phase 0 추가:
- call_with_retry(): 빈 응답 재시도 로직
- 페이지 역할별 재시도 예산 차등 적용
- 429/5xx 에러 핸들링 (지터 백오프)

Author: 박준호 (AI/ML Lead)
Date: 2025-11-06
Version: Phase 0 Hotfix
"""

import os
import logging
import json
import re
import time
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

try:
    from .document_classifier import DocumentClassifierV50
except ImportError:
    DocumentClassifierV50 = None

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV50:
    """범용 VLM 서비스 Phase 0 - 재시도 로직 추가"""
    
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
        
        # DocumentClassifier는 선택적
        if DocumentClassifierV50:
            self.classifier = DocumentClassifierV50(provider)
        else:
            self.classifier = None
            logger.warning("⚠️ DocumentClassifier 없음 - call() 메서드만 사용")
        
        logger.info(f"✅ VLM Service Phase 0 초기화 완료: {provider}")
    
    def call(self, image_data: str, prompt: str) -> str:
        """
        VLM 호출 (단일 시도)
        
        Args:
            image_data: Base64 인코딩된 이미지
            prompt: VLM 프롬프트
        
        Returns:
            VLM 응답 텍스트 (Markdown)
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
                    max_tokens=3000,  # ✅ Phase 0: 개정이력 표를 위해 증가
                    temperature=0,     # ✅ Phase 0: 결정적 출력
                    top_p=1
                )
                return response.choices[0].message.content.strip()
            
            else:  # claude
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=3000,
                    temperature=0,
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
            raise
    
    def call_with_retry(
        self,
        image_data: str,
        prompt: str,
        page_role: str = "general",
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        ✅ Phase 0 신규: 빈 응답 재시도 로직
        
        전략:
        - 페이지 역할별 재시도 예산 차등 적용
        - 재시도 시 프롬프트 단순화
        - 429/5xx 에러는 지터 백오프
        
        Args:
            image_data: Base64 이미지
            prompt: VLM 프롬프트
            page_role: 페이지 역할 ("revision_table", "general")
            max_retries: 최대 재시도 횟수 (무시됨, page_role로 결정)
        
        Returns:
            {
                'content': str,
                'retry_count': int,
                'fallback': bool,
                'fallback_reason': str
            }
        """
        # 페이지 역할별 재시도 예산
        if page_role == "revision_table":
            budget = 2  # 개정이력 표는 2회
            logger.info("      🎯 개정이력 페이지 - 재시도 예산 2회")
        else:
            budget = 1  # 일반 페이지는 1회
        
        for attempt in range(budget + 1):
            try:
                # 첫 시도는 원본 프롬프트, 재시도는 단순화
                if attempt == 0:
                    current_prompt = prompt
                else:
                    logger.info(f"      🔄 재시도 {attempt}/{budget} - 프롬프트 단순화")
                    current_prompt = self._simplify_prompt(page_role)
                
                # VLM 호출
                response = self.call(image_data, current_prompt)
                
                # 빈 응답 체크
                if response and len(response.strip()) >= 50:
                    if attempt > 0:
                        logger.info(f"      ✅ 재시도 {attempt}회 만에 성공!")
                    return {
                        'content': response,
                        'retry_count': attempt,
                        'fallback': False,
                        'fallback_reason': ''
                    }
                else:
                    logger.warning(f"      ⚠️ 시도 {attempt+1} 빈 응답 ({len(response)} 글자)")
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # 429 또는 5xx 에러는 지터 백오프
                if '429' in error_str or '5' in error_str[:1]:
                    wait_time = 0.6 + 0.2 * attempt  # jitter
                    logger.warning(f"      ⚠️ Rate limit/Server error - {wait_time:.1f}초 대기")
                    time.sleep(wait_time)
                else:
                    logger.error(f"      ❌ VLM 오류: {e}")
                    break
        
        # 모든 재시도 실패
        logger.error(f"      ❌ {budget+1}회 시도 모두 실패 → Fallback")
        return {
            'content': '',
            'retry_count': budget,
            'fallback': True,
            'fallback_reason': 'empty_response_after_retries'
        }
    
    def _simplify_prompt(self, page_role: str) -> str:
        """
        재시도용 단순화 프롬프트
        
        Args:
            page_role: 페이지 역할
        
        Returns:
            단순화된 프롬프트
        """
        if page_role == "revision_table":
            return """Extract the revision history table.

Output as a Markdown table with columns: 차수 | 날짜

Example:
| 차수 | 날짜 |
| --- | --- |
| 제37차 개정 | 2019.05.27 |

Extract ALL rows. Do NOT add any commentary."""
        
        else:
            return """Extract all text from this page. Preserve formatting. Output as Markdown.

Do NOT add any meta descriptions or commentary."""
    
    def analyze_page_v50(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        Phase 5.0-5.1 호환: 문서 타입별 분석
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
        
        Returns:
            {
                'content': str,
                'confidence': float,
                'strategy': str,
                'doc_type': str,
                'subtype': str,
                'quality_score': float,
                'structure': Dict
            }
        """
        if not self.classifier:
            logger.warning("⚠️ DocumentClassifier 없음 - mixed 타입으로 처리")
            doc_type = 'mixed'
            subtype = 'unknown'
            confidence = 0.5
            doc_type_result = {}
        else:
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
        return self.call(image_data, prompt)
    
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
        return self.call(image_data, prompt)
    
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
        return self.call(image_data, prompt)
    
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
        return self.call(image_data, prompt)
    
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
        return self.call(image_data, prompt)
    
    def _extract_mixed(self, image_data: str) -> str:
        prompt = """이 문서의 내용을 Markdown으로 추출하세요.

**절대 금지:**
- 메타 설명, 안내 문구, 요약
- 오직 문서 내용만 출력"""
        return self.call(image_data, prompt)
    
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
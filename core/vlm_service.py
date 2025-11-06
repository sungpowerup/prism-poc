"""
core/vlm_service.py
PRISM Phase 0.2 Hotfix - VLM Service with Article Number Validator

✅ Phase 0.2 긴급 수정:
1. 조문 번호 사후 검증기 추가
2. 페이지 번호 오인식 방지
3. "기본 정신" 추출 프롬프트 강화
4. 재시도 로직 안정화

Author: 박준호 (AI/ML Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import os
import time
import logging
import base64
import re
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# ✅ .env 파일 로드
load_dotenv()

logger = logging.getLogger(__name__)


class VLMServiceV50:
    """
    Phase 0.2 VLM 서비스 (조문 번호 검증)
    
    ✅ Phase 0.2 개선:
    - 조문 번호 사후 검증 (1~200조 범위)
    - 페이지 번호 패턴 감지 및 차단
    - "기본 정신" 추출 프롬프트 강화
    - 재시도 프롬프트 단순화
    """
    
    # ✅ Phase 0.2: 조문 번호 패턴
    ARTICLE_PATTERN = re.compile(r'제\s?(\d+)조(?:의\s?(\d+))?')
    
    # ✅ Phase 0.2: 페이지 번호 패턴 (블랙리스트)
    PAGE_NUMBER_PATTERN = re.compile(r'\b\d{3,4}-\d{1,2}\b')
    
    # 허용 가능한 조문 번호 범위
    VALID_ARTICLE_RANGE = (1, 200)
    
    def __init__(self, provider: str = 'azure_openai'):
        """
        초기화
        
        Args:
            provider: VLM 제공자 ('azure_openai', 'openai', 'local_sllm')
        """
        self.provider = provider
        
        if provider == 'azure_openai':
            from openai import AzureOpenAI
            
            # 환경변수 체크
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
            
            if not api_key:
                raise ValueError("❌ AZURE_OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
            
            if not endpoint:
                raise ValueError("❌ AZURE_OPENAI_ENDPOINT 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
            
            logger.info(f"   🔑 API Key: {'*' * 20}{api_key[-4:] if len(api_key) > 4 else '****'}")
            logger.info(f"   🌐 Endpoint: {endpoint}")
            logger.info(f"   🤖 Deployment: {deployment}")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version="2024-12-01-preview",
                azure_endpoint=endpoint
            )
            self.model = deployment
        
        elif provider == 'openai':
            from openai import OpenAI
            
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4o"
        
        elif provider == 'local_sllm':
            import ollama
            self.client = ollama
            self.model = os.getenv("OLLAMA_MODEL", "llama3.2-vision")
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        logger.info(f"✅ VLM Service Phase 0.2 초기화 완료: {provider}")
    
    def call(self, image_data: str, prompt: str) -> str:
        """
        VLM 호출 (단일 시도)
        
        Args:
            image_data: Base64 인코딩된 이미지
            prompt: VLM 프롬프트
        
        Returns:
            추출된 Markdown
        """
        try:
            if self.provider == 'local_sllm':
                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [image_data]
                        }
                    ]
                )
                return response['message']['content'].strip()
            
            else:  # Azure OpenAI or OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
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
        ✅ Phase 0.2: VLM 재시도 + 조문 번호 검증
        
        전략:
        1. 페이지 역할별 재시도 예산 차등 적용
        2. 재시도 시 프롬프트 단순화
        3. ✅ 조문 번호 사후 검증
        4. 429/5xx 에러는 백오프
        
        Args:
            image_data: Base64 이미지
            prompt: VLM 프롬프트
            page_role: 페이지 역할 ("revision_table", "general")
            max_retries: 무시됨 (page_role로 결정)
        
        Returns:
            {
                'content': str,
                'retry_count': int,
                'fallback': bool,
                'fallback_reason': str,
                'validation_passed': bool
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
                if not response or len(response.strip()) < 50:
                    logger.warning(f"      ⚠️ VLM 빈 응답 ({len(response) if response else 0}자)")
                    
                    if attempt < budget:
                        time.sleep(1)
                        continue
                    else:
                        return {
                            'content': '',
                            'retry_count': attempt + 1,
                            'fallback': True,
                            'fallback_reason': 'empty_response',
                            'validation_passed': False
                        }
                
                # ✅ Phase 0.2: 조문 번호 검증
                validation_result = self._validate_article_numbers(response, page_role)
                
                if not validation_result['valid']:
                    logger.warning(f"      ⚠️ 조문 번호 검증 실패: {validation_result['reason']}")
                    
                    # 개정이력 페이지는 검증 스킵
                    if page_role == "revision_table":
                        logger.info("      ℹ️ 개정이력 페이지 - 검증 스킵")
                    elif attempt < budget:
                        # 재시도 (보정 프롬프트)
                        logger.info(f"      🔄 조문 번호 보정 재시도")
                        current_prompt = self._create_correction_prompt()
                        time.sleep(1)
                        continue
                    else:
                        logger.warning("      ⚠️ 재시도 예산 소진 - 검증 실패로 진행")
                
                # 성공
                if attempt > 0:
                    logger.info(f"      ✅ 재시도 {attempt}회 만에 성공!")
                
                return {
                    'content': response,
                    'retry_count': attempt,
                    'fallback': False,
                    'fallback_reason': '',
                    'validation_passed': validation_result['valid']
                }
            
            except Exception as e:
                error_str = str(e).lower()
                
                # 429 Rate Limit
                if '429' in error_str or 'rate limit' in error_str:
                    wait_time = 60
                    logger.warning(f"      ⚠️ Rate limit (429) - {wait_time}초 대기")
                    time.sleep(wait_time)
                    
                    if attempt < budget:
                        continue
                
                # 5xx Server Error
                elif '5' in error_str[:3]:
                    wait_time = 5
                    logger.warning(f"      ⚠️ Server error (5xx) - {wait_time}초 대기")
                    time.sleep(wait_time)
                    
                    if attempt < budget:
                        continue
                
                # 기타 에러
                logger.error(f"      ❌ VLM 오류: {e}")
                
                if attempt < budget:
                    time.sleep(2)
                    continue
                else:
                    return {
                        'content': '',
                        'retry_count': attempt + 1,
                        'fallback': True,
                        'fallback_reason': f'error: {e}',
                        'validation_passed': False
                    }
        
        # 모든 재시도 실패
        return {
            'content': '',
            'retry_count': budget + 1,
            'fallback': True,
            'fallback_reason': 'max_retries_exceeded',
            'validation_passed': False
        }
    
    def _validate_article_numbers(
        self, 
        content: str, 
        page_role: str
    ) -> Dict[str, Any]:
        """
        ✅ Phase 0.2: 조문 번호 사후 검증
        
        검증 항목:
        1. 조문 번호가 1~200 범위 내인가?
        2. 페이지 번호(402-3)가 조문으로 오인식되지 않았는가?
        
        Args:
            content: VLM 추출 결과
            page_role: 페이지 역할
        
        Returns:
            {
                'valid': bool,
                'reason': str,
                'article_count': int,
                'page_marker_count': int
            }
        """
        # 개정이력 페이지는 검증 스킵
        if page_role == "revision_table":
            return {
                'valid': True,
                'reason': 'skip_revision_table',
                'article_count': 0,
                'page_marker_count': 0
            }
        
        # 1) 조문 번호 추출
        article_matches = self.ARTICLE_PATTERN.findall(content)
        article_numbers = []
        
        for match in article_matches:
            main_num = int(match[0])
            article_numbers.append(main_num)
        
        article_count = len(set(article_numbers))
        
        # 2) 페이지 번호 패턴 감지
        page_markers = self.PAGE_NUMBER_PATTERN.findall(content)
        page_marker_count = len(page_markers)
        
        # 3) 검증 로직
        
        # 페이지 번호가 있고 조문이 없으면 의심
        if page_marker_count > 0 and article_count == 0:
            return {
                'valid': False,
                'reason': f'page_number_confusion: {page_marker_count}개 페이지 마커, 0개 조문',
                'article_count': article_count,
                'page_marker_count': page_marker_count
            }
        
        # 조문 번호가 범위 밖
        invalid_articles = [
            num for num in article_numbers 
            if num < self.VALID_ARTICLE_RANGE[0] or num > self.VALID_ARTICLE_RANGE[1]
        ]
        
        if invalid_articles:
            return {
                'valid': False,
                'reason': f'invalid_article_range: {invalid_articles}',
                'article_count': article_count,
                'page_marker_count': page_marker_count
            }
        
        # 통과
        return {
            'valid': True,
            'reason': 'ok',
            'article_count': article_count,
            'page_marker_count': page_marker_count
        }
    
    def _simplify_prompt(self, page_role: str) -> str:
        """
        ✅ Phase 0.2: 재시도 프롬프트 단순화
        
        Args:
            page_role: 페이지 역할
        
        Returns:
            단순화된 프롬프트
        """
        if page_role == "revision_table":
            return """Extract the revision history table from this image.

**Output Format:**
| 차수 | 날짜 |
| --- | --- |
| 제37차 개정 | 2019.05.27 |

**Requirements:**
- Extract ALL rows
- Keep original date format
- Text only, no explanations
"""
        else:
            return """Extract the text content from this image in Markdown format.

**Rules:**
- Preserve article numbers (제N조)
- Use ### for headers
- Keep original structure
- No meta-commentary

Start immediately with the content."""
    
    def _create_correction_prompt(self) -> str:
        """
        ✅ Phase 0.2: 조문 번호 보정 프롬프트
        
        Returns:
            보정 프롬프트
        """
        return """Extract the text content from this image in Markdown format.

**CRITICAL: Article Number Accuracy**
- Extract EXACT article numbers: 제1조, 제2조, ..., 제9조
- DO NOT confuse page numbers (e.g., 402-3) with article numbers
- Article numbers are typically 1~200
- Format: 제N조, 제N조의M

**CRITICAL: Preamble ("기본 정신")**
- If you see headers like "기본 정신", "제정이유", "입법취지"
- Extract the FULL paragraph under that header
- This is essential content

**Rules:**
- Use ### for article headers
- Preserve structure
- No meta-commentary

Start immediately with the content."""
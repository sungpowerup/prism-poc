"""
core/vlm_service.py
PRISM Phase 0.2.1 긴급 패치 - Azure OpenAI 응답 파싱 수정

🚨 긴급 수정 사항:
1. Azure OpenAI API 응답 파싱 오류 수정
   - BEFORE: response.content[0].text (❌ AttributeError)
   - AFTER: response.choices[0].message.content (✅ 정상)
2. call_with_retry에서도 동일하게 수정

원인: Azure OpenAI SDK의 ChatCompletion 객체 구조 오해
결과: VLM Fallback 100% → 예상 0~10%

Author: 박준호 (AI/ML Lead) + GPT 피드백 반영
Date: 2025-11-06
Version: Phase 0.2.1 Hotfix
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
    Phase 0.2.1 VLM 서비스 (파싱 오류 수정)
    
    ✅ Phase 0.2.1 긴급 패치:
    - Azure OpenAI 응답 파싱 수정
    - 조문 번호 검증 유지
    - 재시도 로직 유지
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
                
                # ✅ Phase 0.2.1 긴급 수정: 올바른 파싱
                # BEFORE (오류): return response.content[0].text.strip()
                # AFTER (정상): return response.choices[0].message.content.strip()
                return response.choices[0].message.content.strip()
        
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
        1. 일반 페이지: 재시도 1회
        2. 개정이력 페이지: 재시도 2회 (중요하므로)
        3. 재시도 시 프롬프트 단순화
        4. 조문 번호 사후 검증
        
        Args:
            image_data: Base64 이미지
            prompt: 원본 프롬프트
            page_role: 페이지 역할 ('general', 'revision_table')
            max_retries: 최대 재시도 횟수
        
        Returns:
            {
                'content': 추출된 텍스트,
                'fallback': True/False,
                'retry_count': 재시도 횟수
            }
        """
        # 개정이력 페이지는 재시도 2회, 일반 페이지는 1회
        if page_role == "revision_table":
            budget = 2
            logger.info(f"      🎯 개정이역 페이지 - 재시도 예산 {budget}회")
        else:
            budget = 1
        
        for attempt in range(budget + 1):
            try:
                if attempt == 0:
                    # 첫 시도: 원본 프롬프트
                    current_prompt = prompt
                else:
                    # 재시도: 프롬프트 단순화
                    logger.info(f"      🔄 재시도 {attempt}/{budget} - 프롬프트 단순화")
                    current_prompt = self._simplify_prompt(prompt)
                    time.sleep(2)  # Rate limit 대비
                
                # VLM 호출
                content = self.call(image_data, current_prompt)
                
                # 길이 검증
                if len(content.strip()) < 50:
                    logger.warning(f"      ⚠️ VLM 응답 너무 짧음 ({len(content)} 글자)")
                    if attempt < budget:
                        continue
                    else:
                        logger.error(f"      ❌ VLM 오류: 응답 길이 부족")
                        return {'content': '', 'fallback': True, 'retry_count': attempt}
                
                # ✅ Phase 0.2: 조문 번호 검증
                if not self._validate_article_numbers(content):
                    logger.warning(f"      ⚠️ 조문 번호 검증 실패 (페이지 번호 오인식 의심)")
                    if attempt < budget:
                        continue
                
                # 성공
                return {
                    'content': content,
                    'fallback': False,
                    'retry_count': attempt
                }
            
            except Exception as e:
                logger.error(f"      ❌ VLM 오류: {e}")
                if attempt < budget:
                    continue
                else:
                    return {'content': '', 'fallback': True, 'retry_count': attempt}
        
        # 모든 재시도 실패
        return {'content': '', 'fallback': True, 'retry_count': budget}
    
    def _simplify_prompt(self, original: str) -> str:
        """
        재시도용 프롬프트 단순화
        
        Args:
            original: 원본 프롬프트
        
        Returns:
            단순화된 프롬프트
        """
        return """이 페이지의 텍스트를 Markdown으로 정확히 추출하세요.

**규칙:**
1. 원본 내용 그대로 추출
2. 조문 번호는 "제○조" 형식 유지
3. 표가 있으면 Markdown 표 형식으로
4. 메타 설명 금지

출력만 제공하세요."""
    
    def _validate_article_numbers(self, content: str) -> bool:
        """
        ✅ Phase 0.2: 조문 번호 검증
        
        페이지 번호(402-1, 402-2)를 조문 번호로 오인식했는지 확인
        
        Args:
            content: VLM 출력 텍스트
        
        Returns:
            True: 정상, False: 페이지 번호 오인식 의심
        """
        # 페이지 번호 패턴 감지
        page_numbers = self.PAGE_NUMBER_PATTERN.findall(content)
        
        if page_numbers:
            logger.warning(f"      🚨 페이지 번호 패턴 감지: {page_numbers}")
            
            # 조문 번호도 있는지 확인
            articles = self.ARTICLE_PATTERN.findall(content)
            
            if not articles:
                # 조문 번호는 없고 페이지 번호만 있음 → 오인식
                logger.error(f"      ❌ 조문 번호 없음 - 페이지 번호 오인식")
                return False
            
            # 조문 번호의 범위 검증
            for match in articles:
                article_no = int(match[0])
                if article_no < self.VALID_ARTICLE_RANGE[0] or article_no > self.VALID_ARTICLE_RANGE[1]:
                    logger.warning(f"      ⚠️ 비정상 조문 번호: 제{article_no}조")
                    return False
        
        return True
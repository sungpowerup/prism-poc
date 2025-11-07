"""
core/vlm_service.py
PRISM Phase 0.3.2 - VLM Service (조문 번호 검증)

✅ Phase 0.3.2 개선:
1. 조문 번호 정확성 검증 추가
2. 페이지 번호 오인식 방지
3. OCR 기반 교정 로직

Author: 박준호 (AI/ML Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.2
"""

import os
import time
import logging
import base64
import re
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class VLMServiceV50:
    """
    Phase 0.3.2 VLM 서비스 (조문 번호 검증)
    
    ✅ Phase 0.3.2 개선:
    - 조문 번호 정확성 검증
    - 페이지 번호 오인식 방지
    """
    
    # ✅ Phase 0.2: 조문 번호 패턴
    ARTICLE_PATTERN = re.compile(r'제\s?(\d+)조(?:의\s?(\d+))?')
    
    # ✅ Phase 0.2: 페이지 번호 패턴
    PAGE_NUMBER_PATTERN = re.compile(r'\b\d{3,4}-\d{1,2}\b')
    
    # ✅ Phase 0.3.2: 허용 가능한 조문 번호 범위
    VALID_ARTICLE_RANGE = (1, 200)
    
    def __init__(self, provider: str = 'azure_openai'):
        """초기화"""
        self.provider = provider
        
        if provider == 'azure_openai':
            from openai import AzureOpenAI
            
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
            
            if not api_key:
                raise ValueError("❌ AZURE_OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            
            if not endpoint:
                raise ValueError("❌ AZURE_OPENAI_ENDPOINT 환경변수가 설정되지 않았습니다.")
            
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
        
        logger.info(f"✅ VLM Service Phase 0.3.2 초기화 완료: {provider}")
    
    def call(self, image_data: str, prompt: str, ocr_text: str = "") -> str:
        """
        VLM 호출 (조문 번호 검증 포함)
        
        Args:
            image_data: Base64 인코딩된 이미지
            prompt: 프롬프트
            ocr_text: OCR 텍스트 (조문 번호 검증용)
        
        Returns:
            추출된 텍스트
        """
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
            result = response['message']['content'].strip()
        
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
            result = response.choices[0].message.content.strip()
        
        # ✅ Phase 0.3.2: 조문 번호 검증
        if ocr_text:
            result = self._validate_article_numbers(result, ocr_text)
        
        # ✅ Phase 0.2: 페이지 번호 패턴 경고
        page_numbers = self.PAGE_NUMBER_PATTERN.findall(result)
        if page_numbers:
            logger.warning(f"      🚨 페이지 번호 패턴 감지: {page_numbers}")
        
        return result
    
    def _validate_article_numbers(self, text: str, ocr_text: str) -> str:
        """
        ✅ Phase 0.3.2: 조문 번호 검증 및 교정
        
        Args:
            text: VLM 추출 텍스트
            ocr_text: OCR 텍스트
        
        Returns:
            검증된 텍스트
        """
        # VLM에서 추출된 조문 번호
        vlm_articles = self.ARTICLE_PATTERN.findall(text)
        
        # OCR에서 추출된 조문 번호 (검증용)
        ocr_articles = self.ARTICLE_PATTERN.findall(ocr_text)
        
        for article_tuple in vlm_articles:
            number = int(article_tuple[0])
            
            # ✅ Phase 0.3.2: 페이지 번호 범위 체크
            if number > self.VALID_ARTICLE_RANGE[1]:  # 200 초과
                # OCR에서 올바른 조문 번호 찾기
                valid_ocr_articles = [
                    f"제{a[0]}조{f'의{a[1]}' if a[1] else ''}"
                    for a in ocr_articles
                    if int(a[0]) <= self.VALID_ARTICLE_RANGE[1]
                ]
                
                if valid_ocr_articles:
                    wrong_article = f"제{article_tuple[0]}조"
                    if article_tuple[1]:
                        wrong_article += f"의{article_tuple[1]}"
                    
                    correct_article = valid_ocr_articles[0]
                    
                    logger.warning(
                        f"      ⚠️ 조문 번호 교정: {wrong_article} → {correct_article}"
                    )
                    
                    text = text.replace(wrong_article, correct_article)
        
        return text
    
    def call_with_retry(
        self,
        image_data: str,
        prompt: str,
        ocr_text: str = "",
        page_role: str = "general",
        max_retries: int = 3
    ) -> str:
        """
        재시도 로직이 있는 VLM 호출
        
        Args:
            image_data: Base64 인코딩된 이미지
            prompt: 프롬프트
            ocr_text: OCR 텍스트
            page_role: 페이지 역할
            max_retries: 최대 재시도 횟수
        
        Returns:
            추출된 텍스트
        """
        # 개정이력 페이지는 재시도 예산 2회
        if page_role == "revision_table":
            max_retries = min(max_retries, 2)
            logger.info(f"      🎯 개정이역 페이지 - 재시도 예산 {max_retries}회")
        
        for attempt in range(1, max_retries + 1):
            try:
                result = self.call(image_data, prompt, ocr_text)
                
                # 빈 응답 체크
                if not result or len(result.strip()) < 10:
                    if attempt < max_retries:
                        logger.warning(f"      ⚠️ 빈 응답 (시도 {attempt}/{max_retries}) - 재시도")
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        logger.error(f"      ❌ 빈 응답 (최종 실패)")
                        return ""
                
                return result
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Rate limit 에러
                if "rate" in error_str or "429" in error_str:
                    if attempt < max_retries:
                        wait_time = 60
                        logger.warning(
                            f"      ⚠️ Rate limit (시도 {attempt}/{max_retries}) - {wait_time}초 대기"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"      ❌ Rate limit (최종 실패)")
                        return ""
                
                # 기타 에러
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"      ⚠️ VLM 오류 (시도 {attempt}/{max_retries}): {e} - {wait_time}초 대기"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"      ❌ VLM 오류 (최종 실패): {e}")
                    return ""
        
        return ""
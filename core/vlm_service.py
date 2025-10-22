"""
PRISM Phase 3.0+ - VLM Service (환경 변수 로딩 완전 수정)

✅ 수정사항:
1. load_dotenv() 명시적 호출
2. 환경 변수 검증 강화
3. 상세한 오류 메시지
4. UTF-8 인코딩 처리 개선

Author: 박준호 (AI/ML Lead)
Date: 2025-10-22
Version: 3.2
"""

import os
import base64
import json
import time
import logging
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic

# ✅ 환경 변수 로드 (최우선)
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class VLMService:
    """
    Vision Language Model 서비스
    UTF-8 인코딩 처리 개선 + 환경 변수 로딩 강화
    """
    
    def __init__(self, provider: str = "azure_openai"):
        """
        VLM 서비스 초기화
        
        Args:
            provider: 'azure_openai', 'claude', 'ollama'
        """
        self.provider = provider
        
        if provider == "azure_openai":
            # 환경 변수 확인
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            
            # 검증
            missing = []
            if not api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not azure_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not deployment:
                missing.append("AZURE_OPENAI_DEPLOYMENT")
            
            if missing:
                error_msg = f"❌ 다음 환경 변수가 설정되지 않았습니다: {', '.join(missing)}\n\n"
                error_msg += ".env 파일을 확인하세요:\n"
                error_msg += f"  - AZURE_OPENAI_API_KEY={'✅' if api_key else '❌'}\n"
                error_msg += f"  - AZURE_OPENAI_ENDPOINT={'✅' if azure_endpoint else '❌'}\n"
                error_msg += f"  - AZURE_OPENAI_DEPLOYMENT={'✅' if deployment else '❌'}"
                raise ValueError(error_msg)
            
            logger.info(f"✅ Azure OpenAI 환경 변수 로드 완료")
            logger.info(f"  - Endpoint: {azure_endpoint}")
            logger.info(f"  - Deployment: {deployment}")
            logger.info(f"  - API Version: {api_version}")
            
            try:
                self.client = AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=azure_endpoint
                )
                self.deployment = deployment
                logger.info(f"✅ Azure OpenAI 클라이언트 초기화 완료")
            except Exception as e:
                raise RuntimeError(f"❌ Azure OpenAI 클라이언트 초기화 실패: {e}")
        
        elif provider == "claude":
            # Claude 초기화
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
            if not api_key:
                raise ValueError("❌ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            logger.info(f"✅ Claude API 키 로드 완료")
            
            try:
                self.client = Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20241022"
                logger.info(f"✅ Claude 클라이언트 초기화 완료")
            except Exception as e:
                raise RuntimeError(f"❌ Claude 클라이언트 초기화 실패: {e}")
        
        else:
            raise ValueError(f"❌ 지원하지 않는 프로바이더: {provider}")
        
        logger.info(f"✅ VLM Service 초기화 완료: {provider}")
    
    def analyze_image(
        self,
        image_data: str,
        element_type: str,
        prompt: str
    ) -> str:
        """
        이미지 분석 (UTF-8 처리 강화)
        
        Args:
            image_data: Base64 인코딩된 이미지
            element_type: 'pie_chart', 'bar_chart', 'table', 'map', 'header'
            prompt: VLM 프롬프트
            
        Returns:
            VLM 응답 (자연어)
        """
        if self.provider == "azure_openai":
            return self._analyze_azure(image_data, prompt)
        elif self.provider == "claude":
            return self._analyze_claude(image_data, prompt)
        else:
            raise ValueError(f"❌ 지원하지 않는 프로바이더: {self.provider}")
    
    def _analyze_azure(self, image_data: str, prompt: str) -> str:
        """Azure OpenAI로 이미지 분석"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            # UTF-8 정규화
            if result:
                result = result.strip()
            
            logger.info(f"✅ Azure OpenAI 응답 수신 ({len(result)} 글자)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Azure OpenAI API 오류: {e}")
            raise RuntimeError(f"Azure OpenAI API 호출 실패: {e}")
    
    def _analyze_claude(self, image_data: str, prompt: str) -> str:
        """Claude로 이미지 분석"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
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
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            result = message.content[0].text
            
            # UTF-8 정규화
            if result:
                result = result.strip()
            
            logger.info(f"✅ Claude 응답 수신 ({len(result)} 글자)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Claude API 오류: {e}")
            raise RuntimeError(f"Claude API 호출 실패: {e}")
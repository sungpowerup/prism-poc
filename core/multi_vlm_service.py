# core/multi_vlm_service.py

import os
import logging
import base64
from typing import Dict, Any, Optional
import anthropic
from openai import AzureOpenAI
import requests

logger = logging.getLogger(__name__)


class MultiVLMService:
    """다중 VLM 서비스 통합 클래스"""
    
    def __init__(self, default_provider: str = "claude"):
        """
        Args:
            default_provider: 기본 프로바이더 ('claude', 'azure_openai', 'ollama')
        """
        logger.info(f"MultiVLMService 초기화: {default_provider}")
        
        self.current_provider = default_provider
        self.providers = {}
        self.provider_status = {}
        
        # 각 프로바이더 초기화
        self._init_claude()
        self._init_azure_openai()
        self._init_ollama()
        
        # 기본 프로바이더 설정
        self.set_provider(default_provider)
    
    def _init_claude(self):
        """Claude 초기화"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            logger.info(f"Claude API 키 확인: {'있음' if api_key else '없음'}")
            
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")
            
            self.providers['claude'] = anthropic.Anthropic(api_key=api_key)
            self.provider_status['claude'] = {'available': True}
            logger.info("[OK] Claude 초기화 완료")
            
        except Exception as e:
            logger.error(f"Claude 초기화 실패: {e}")
            self.provider_status['claude'] = {
                'available': False,
                'error': str(e)
            }
    
    def _init_azure_openai(self):
        """Azure OpenAI 초기화"""
        try:
            endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            api_key = os.getenv('AZURE_OPENAI_API_KEY')
            api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4-vision')
            
            if not endpoint or not api_key:
                raise ValueError("Azure OpenAI 설정이 불완전합니다")
            
            self.providers['azure_openai'] = {
                'client': AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version
                ),
                'deployment': deployment
            }
            self.provider_status['azure_openai'] = {'available': True}
            logger.info("Azure OpenAI 초기화 완료")
            
        except Exception as e:
            logger.error(f"Azure OpenAI 초기화 실패: {e}")
            self.provider_status['azure_openai'] = {
                'available': False,
                'error': str(e)
            }
    
    def _init_ollama(self):
        """Ollama 초기화"""
        try:
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            model = os.getenv('OLLAMA_MODEL', 'llava:7b')
            
            # Ollama 서버 연결 테스트
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            self.providers['ollama'] = {
                'base_url': base_url,
                'model': model
            }
            self.provider_status['ollama'] = {'available': True}
            logger.info(f"Ollama 초기화 완료: {model}")
            
        except Exception as e:
            logger.error(f"Ollama 초기화 실패: {e}")
            self.provider_status['ollama'] = {
                'available': False,
                'error': str(e)
            }
    
    def set_provider(self, provider: str):
        """프로바이더 변경"""
        if provider not in self.providers:
            raise ValueError(f"지원하지 않는 프로바이더: {provider}")
        
        if not self.provider_status.get(provider, {}).get('available', False):
            raise ValueError(f"사용할 수 없는 프로바이더: {provider}")
        
        self.current_provider = provider
        logger.info(f"프로바이더 변경: {provider}")
    
    def get_current_provider(self) -> str:
        """현재 프로바이더 반환"""
        return self.current_provider
    
    def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        이미지 분석
        
        Args:
            image_base64: base64 인코딩된 이미지
            prompt: 분석 프롬프트
            max_tokens: 최대 토큰 수
            
        Returns:
            분석 결과 딕셔너리
        """
        logger.info(f"프로바이더 선택: {self.current_provider}")
        
        if self.current_provider == 'claude':
            return self._analyze_with_claude(image_base64, prompt, max_tokens)
        elif self.current_provider == 'azure_openai':
            return self._analyze_with_azure(image_base64, prompt, max_tokens)
        elif self.current_provider == 'ollama':
            return self._analyze_with_ollama(image_base64, prompt, max_tokens)
        else:
            raise ValueError(f"알 수 없는 프로바이더: {self.current_provider}")
    
    def _analyze_with_claude(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Claude로 이미지 분석"""
        try:
            client = self.providers['claude']
            
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            return {
                "content": message.content[0].text,
                "provider": "claude",
                "model": "claude-sonnet-4-20250514"
            }
            
        except Exception as e:
            logger.error(f"Claude 분석 오류: {e}")
            raise
    
    def _analyze_with_azure(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Azure OpenAI로 이미지 분석"""
        try:
            provider_info = self.providers['azure_openai']
            client = provider_info['client']
            deployment = provider_info['deployment']
            
            response = client.chat.completions.create(
                model=deployment,
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
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )
            
            return {
                "content": response.choices[0].message.content,
                "provider": "azure_openai",
                "model": deployment
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI 분석 오류: {e}")
            raise
    
    def _analyze_with_ollama(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Ollama로 이미지 분석"""
        try:
            provider_info = self.providers['ollama']
            base_url = provider_info['base_url']
            model = provider_info['model']
            
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "content": result.get('response', ''),
                "provider": "ollama",
                "model": model
            }
            
        except Exception as e:
            logger.error(f"Ollama 분석 오류: {e}")
            raise
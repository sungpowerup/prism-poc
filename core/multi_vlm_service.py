"""
Multi VLM Service - Claude, Azure OpenAI, Ollama 지원
"""

import os
import logging
import base64
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class MultiVLMService:
    """멀티 VLM 서비스"""
    
    def __init__(self, default_provider: str = 'claude'):
        """
        초기화
        
        Args:
            default_provider: 기본 프로바이더 ('claude', 'azure_openai', 'ollama')
        """
        logger.info(f"MultiVLMService 초기화: {default_provider}")
        
        self.providers = {}
        self.current_provider_key = None
        
        # 프로바이더 초기화
        self._init_providers()
        
        # 기본 프로바이더 설정 (우선순위: 설정값 > 사용가능한 것)
        provider_priority = [default_provider, 'claude', 'azure_openai', 'ollama']
        
        for provider_key in provider_priority:
            if provider_key in self.providers and self.providers[provider_key]['available']:
                self.set_provider(provider_key)
                logger.info(f"프로바이더 선택: {provider_key}")
                break
    
    def _init_providers(self):
        """프로바이더 초기화 (Claude 우선)"""
        
        # Claude (최우선)
        try:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            logger.info(f"Claude API 키 확인: {'있음' if anthropic_key else '없음'}")
            
            if anthropic_key:
                from anthropic import Anthropic
                client = Anthropic(api_key=anthropic_key)
                
                self.providers['claude'] = {
                    'name': 'Claude Sonnet 4',
                    'client': client,
                    'available': True,
                    'type': 'cloud'
                }
                logger.info("[OK] Claude 초기화 완료")
            else:
                self.providers['claude'] = {
                    'name': 'Claude Sonnet 4',
                    'client': None,
                    'available': False,
                    'type': 'cloud'
                }
                logger.warning("[WARN] Claude API 키 없음")
        except Exception as e:
            logger.error(f"[ERROR] Claude 초기화 실패: {e}", exc_info=True)
            self.providers['claude'] = {
                'name': 'Claude Sonnet 4',
                'client': None,
                'available': False,
                'type': 'cloud'
            }
        
        # Azure OpenAI
        try:
            azure_key = os.getenv('AZURE_OPENAI_API_KEY')
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            
            if azure_key and azure_endpoint:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    api_key=azure_key,
                    api_version="2024-02-01",
                    azure_endpoint=azure_endpoint
                )
                
                self.providers['azure_openai'] = {
                    'name': 'Azure OpenAI GPT-4',
                    'client': client,
                    'available': True,
                    'type': 'cloud'
                }
                logger.info("Azure OpenAI 초기화 완료")
            else:
                self.providers['azure_openai'] = {
                    'name': 'Azure OpenAI GPT-4',
                    'client': None,
                    'available': False,
                    'type': 'cloud'
                }
        except Exception as e:
            logger.error(f"Azure OpenAI 초기화 실패: {e}")
            self.providers['azure_openai'] = {
                'name': 'Azure OpenAI GPT-4',
                'client': None,
                'available': False,
                'type': 'cloud'
            }
        
        # Ollama
        try:
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            ollama_model = os.getenv('OLLAMA_MODEL', 'llava:7b')
            
            # Ollama 연결 테스트
            import requests
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            
            if response.status_code == 200:
                self.providers['ollama'] = {
                    'name': f'Ollama ({ollama_model})',
                    'client': {
                        'base_url': ollama_url,
                        'model': ollama_model
                    },
                    'available': True,
                    'type': 'local'
                }
                logger.info(f"Ollama 초기화 완료: {ollama_model}")
            else:
                self.providers['ollama'] = {
                    'name': 'Ollama',
                    'client': None,
                    'available': False,
                    'type': 'local'
                }
        except Exception as e:
            logger.warning(f"Ollama 초기화 실패 (정상): {e}")
            self.providers['ollama'] = {
                'name': 'Ollama',
                'client': None,
                'available': False,
                'type': 'local'
            }
    
    def set_provider(self, provider_key: str):
        """프로바이더 설정"""
        if provider_key not in self.providers:
            raise ValueError(f"알 수 없는 프로바이더: {provider_key}")
        
        if not self.providers[provider_key]['available']:
            raise ValueError(f"사용 불가능한 프로바이더: {provider_key}")
        
        self.current_provider_key = provider_key
        logger.info(f"프로바이더 변경: {provider_key}")
    
    def get_available_providers(self) -> Dict:
        """사용 가능한 프로바이더 목록"""
        return self.providers
    
    def analyze_image(self, image_base64: str, prompt: str) -> str:
        """
        이미지 분석
        
        Args:
            image_base64: Base64 인코딩된 이미지
            prompt: 분석 프롬프트
        
        Returns:
            분석 결과 텍스트
        """
        if not self.current_provider_key:
            raise ValueError("프로바이더가 설정되지 않았습니다.")
        
        provider = self.providers[self.current_provider_key]
        
        if self.current_provider_key == 'claude':
            return self._analyze_with_claude(image_base64, prompt, provider['client'])
        
        elif self.current_provider_key == 'azure_openai':
            return self._analyze_with_azure(image_base64, prompt, provider['client'])
        
        elif self.current_provider_key == 'ollama':
            return self._analyze_with_ollama(image_base64, prompt, provider['client'])
        
        else:
            raise ValueError(f"지원하지 않는 프로바이더: {self.current_provider_key}")
    
    def _analyze_with_claude(self, image_base64: str, prompt: str, client) -> str:
        """Claude로 이미지 분석"""
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
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
            
            return response.content[0].text
        
        except Exception as e:
            logger.error(f"Claude 분석 오류: {e}")
            raise
    
    def _analyze_with_azure(self, image_base64: str, prompt: str, client) -> str:
        """Azure OpenAI로 이미지 분석"""
        try:
            response = client.chat.completions.create(
                model="gpt-4-vision",
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
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Azure OpenAI 분석 오류: {e}")
            raise
    
    def _analyze_with_ollama(self, image_base64: str, prompt: str, client_config: Dict) -> str:
        """Ollama로 이미지 분석"""
        try:
            import requests
            
            base_url = client_config['base_url']
            model = client_config['model']
            
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
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Ollama API 오류: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Ollama 분석 오류: {e}")
            raise
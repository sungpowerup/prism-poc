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
            
            # ✅ 수정: 기본 초기화만 사용 (proxies 제거)
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
            logger.info("[OK] Azure OpenAI 초기화 완료")
            
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
            
            # Health check
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            if response.status_code != 200:
                raise ConnectionError("Ollama 서버 연결 실패")
            
            self.providers['ollama'] = {
                'base_url': base_url,
                'model': model
            }
            self.provider_status['ollama'] = {'available': True}
            logger.info("[OK] Ollama 초기화 완료")
            
        except Exception as e:
            logger.warning(f"Ollama 초기화 실패 (선택사항): {e}")
            self.provider_status['ollama'] = {
                'available': False,
                'error': str(e)
            }
    
    def set_provider(self, provider: str):
        """프로바이더 전환"""
        if provider not in self.providers:
            raise ValueError(f"프로바이더를 찾을 수 없음: {provider}")
        
        if not self.provider_status[provider]['available']:
            raise RuntimeError(f"{provider}가 사용 불가능합니다")
        
        self.current_provider = provider
        logger.info(f"프로바이더 전환: {provider}")
    
    def get_status(self) -> Dict[str, Any]:
        """모든 프로바이더 상태 조회"""
        return {
            'current': self.current_provider,
            'providers': self.provider_status
        }
    
    def analyze_image(self, image_data: bytes, prompt: str, max_tokens: int = 2000) -> str:
        """
        이미지 분석 (현재 프로바이더 사용)
        
        Args:
            image_data: 이미지 바이트
            prompt: 분석 프롬프트
            max_tokens: 최대 토큰 수
            
        Returns:
            분석 결과 텍스트
        """
        if self.current_provider == 'claude':
            return self._analyze_claude(image_data, prompt, max_tokens)
        elif self.current_provider == 'azure_openai':
            return self._analyze_azure(image_data, prompt, max_tokens)
        elif self.current_provider == 'ollama':
            return self._analyze_ollama(image_data, prompt, max_tokens)
        else:
            raise ValueError(f"지원하지 않는 프로바이더: {self.current_provider}")
    
    def _analyze_claude(self, image_data: bytes, prompt: str, max_tokens: int) -> str:
        """Claude로 이미지 분석"""
        client = self.providers['claude']
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
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
        
        return message.content[0].text
    
    def _analyze_azure(self, image_data: bytes, prompt: str, max_tokens: int) -> str:
        """Azure OpenAI로 이미지 분석"""
        config = self.providers['azure_openai']
        client = config['client']
        deployment = config['deployment']
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
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
        
        return response.choices[0].message.content
    
    def _analyze_ollama(self, image_data: bytes, prompt: str, max_tokens: int) -> str:
        """Ollama로 이미지 분석"""
        config = self.providers['ollama']
        base_url = config['base_url']
        model = config['model']
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False
            },
            timeout=60
        )
        
        response.raise_for_status()
        return response.json()['response']
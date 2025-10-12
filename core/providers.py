"""
PRISM Phase 2 - VLM Provider 추상화

다양한 VLM 제공자를 통합 인터페이스로 관리합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

import os
import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from PIL import Image
import io


class VLMProvider(ABC):
    """VLM Provider 추상 클래스"""
    
    @abstractmethod
    def analyze(self, image: Image.Image, prompt: str) -> Optional[str]:
        """
        이미지 분석
        
        Args:
            image: PIL Image
            prompt: 분석 프롬프트
            
        Returns:
            분석 결과 텍스트 (실패 시 None)
        """
        pass
    
    @staticmethod
    def create(provider_name: str) -> 'VLMProvider':
        """
        팩토리 메서드
        
        Args:
            provider_name: "claude", "azure", "ollama"
            
        Returns:
            VLMProvider 인스턴스
        """
        providers = {
            "claude": ClaudeProvider,
            "azure": AzureProvider,
            "ollama": OllamaProvider
        }
        
        provider_class = providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return provider_class()


class ClaudeProvider(VLMProvider):
    """Anthropic Claude Vision API"""
    
    def __init__(self, require_key: bool = True):
        """
        Args:
            require_key: API 키 필수 여부 (False면 None 허용)
        """
        from anthropic import Anthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key and require_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.model = "claude-3-5-sonnet-20241022"
        self.has_key = api_key is not None
    
    def analyze(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Claude Vision으로 이미지 분석"""
        try:
            # PIL Image를 base64로 변환
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # API 호출
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
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
        
        except Exception as e:
            print(f"Claude Vision Error: {e}")
            return None


class AzureProvider(VLMProvider):
    """Azure OpenAI GPT-4V"""
    
    def __init__(self):
        import requests
        
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4-vision")
        
        if not self.api_key or not self.endpoint:
            raise ValueError("Azure OpenAI credentials not found")
        
        self.api_version = "2024-02-15-preview"
    
    def analyze(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Azure GPT-4V로 이미지 분석"""
        try:
            import requests
            
            # PIL Image를 base64로 변환
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # API 엔드포인트
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
            
            # 요청 헤더
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # 요청 바디
            payload = {
                "messages": [
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
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            # API 호출
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            print(f"Azure Vision Error: {e}")
            return None


class OllamaProvider(VLMProvider):
    """Ollama LLaVA (로컬)"""
    
    def __init__(self):
        import requests
        
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llava:13b")
        
        # 연결 테스트
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Cannot connect to Ollama: {e}")
    
    def analyze(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Ollama LLaVA로 이미지 분석"""
        try:
            import requests
            
            # PIL Image를 base64로 변환
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # API 엔드포인트
            url = f"{self.base_url}/api/generate"
            
            # 요청 바디
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False
            }
            
            # API 호출
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
        
        except Exception as e:
            print(f"Ollama Vision Error: {e}")
            return None


# 편의 함수
def get_provider(provider_name: str = "claude") -> VLMProvider:
    """
    VLM Provider 인스턴스 생성
    
    Args:
        provider_name: "claude", "azure", "ollama"
        
    Returns:
        VLMProvider 인스턴스
    """
    return VLMProvider.create(provider_name)
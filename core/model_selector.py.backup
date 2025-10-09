"""
core/model_selector.py
PRISM POC - Local sLLM 지원 (Ollama)
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
import os
import base64
import requests
import json

class VLMProvider(ABC):
    """VLM 프로바이더 추상 클래스"""
    
    @abstractmethod
    def generate_caption(self, image_data: bytes, element_type: str, context: str = "") -> Dict:
        """이미지 → 자연어 캡션 생성"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """프로바이더 이름"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부"""
        pass


class LocalSLLMProvider(VLMProvider):
    """Local sLLM (Ollama) 프로바이더"""
    
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2-vision')
    
    def is_available(self) -> bool:
        """Ollama 서버 실행 여부 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_provider_name(self) -> str:
        return f"Local sLLM ({self.model})"
    
    def generate_caption(self, image_data: bytes, element_type: str, context: str = "") -> Dict:
        """Ollama Vision API 호출"""
        
        try:
            # 이미지를 base64로 인코딩
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # 프롬프트 생성
            prompt = self._create_prompt(element_type, context)
            
            # Ollama API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                caption = result.get('response', '').strip()
                
                return {
                    'caption': caption,
                    'confidence': self._estimate_confidence(caption, element_type),
                    'provider': 'local_sllm',
                    'model': self.model,
                    'error': None
                }
            else:
                return {
                    'caption': None,
                    'confidence': 0.0,
                    'error': f"Ollama API error: {response.status_code}",
                    'provider': 'local_sllm'
                }
        
        except Exception as e:
            return {
                'caption': None,
                'confidence': 0.0,
                'error': str(e),
                'provider': 'local_sllm'
            }
    
    def _create_prompt(self, element_type: str, context: str) -> str:
        """Element 타입별 프롬프트 생성"""
        
        prompts = {
            'chart': "Describe this chart or graph in detail. What type of chart is it? What data does it show? What are the key trends?",
            'table': "Describe this table. What information does it contain? What are the column headers and key data points?",
            'image': "Describe this image in detail. What are the main subjects and their context?",
            'diagram': "Describe this diagram and its components. How are the elements connected?"
        }
        
        prompt = prompts.get(element_type, prompts['image'])
        if context:
            prompt += f"\n\nContext: {context}"
        
        return prompt
    
    def _estimate_confidence(self, caption: str, element_type: str) -> float:
        """신뢰도 추정 (sLLM은 보수적으로)"""
        if not caption or len(caption) < 20:
            return 0.3
        
        # 길이 기반 신뢰도 (최대 0.75)
        return min(0.4 + len(caption) / 500, 0.75)


class ModelSelector:
    """VLM 모델 선택 및 관리"""
    
    def __init__(self):
        self.providers = {
            'local_sllm': LocalSLLMProvider()
        }
    
    def get_available_providers(self) -> Dict[str, VLMProvider]:
        """사용 가능한 프로바이더 목록"""
        return {
            name: provider 
            for name, provider in self.providers.items() 
            if provider.is_available()
        }
    
    def get_provider(self, provider_name: str) -> Optional[VLMProvider]:
        """특정 프로바이더 가져오기"""
        provider = self.providers.get(provider_name)
        if provider and provider.is_available():
            return provider
        return None
    
    def get_default_provider(self) -> Optional[VLMProvider]:
        """기본 프로바이더"""
        provider = self.providers.get('local_sllm')
        if provider and provider.is_available():
            return provider
        return None
    
    def generate_caption(
        self, 
        image_data: bytes, 
        element_type: str,
        provider_name: str = None,
        context: str = ""
    ) -> Dict:
        """캡션 생성"""
        
        if provider_name:
            provider = self.get_provider(provider_name)
        else:
            provider = self.get_default_provider()
        
        if not provider:
            return {
                'caption': None,
                'confidence': 0.0,
                'error': 'No VLM provider available. Is Ollama running?',
                'provider': 'none'
            }
        
        return provider.generate_caption(image_data, element_type, context)
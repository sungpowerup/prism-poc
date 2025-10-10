"""
Multi VLM Provider Service
Claude + Azure OpenAI + Ollama 통합
"""

import os
import base64
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


# ========== 추상 클래스 ==========
class VLMProvider(ABC):
    """VLM 프로바이더 추상 클래스"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부 확인"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """프로바이더 이름"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """프로바이더 정보"""
        pass
    
    @abstractmethod
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """캡션 생성"""
        pass


# ========== Claude Provider ==========
class ClaudeProvider(VLMProvider):
    """Anthropic Claude 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-sonnet-4-20250514"
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def is_available(self) -> bool:
        """API 키 존재 여부"""
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))
    
    def get_name(self) -> str:
        return "Claude 3.5 Sonnet"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            'name': self.get_name(),
            'provider': 'Anthropic',
            'model': self.model,
            'speed': '⚡⚡⚡ 매우 빠름 (1-2초)',
            'quality': '⭐⭐⭐⭐⭐ 최고',
            'cost': '💰 유료 ($0.003/image)',
            'internet': '✅ 필요',
            'gpu': '❌ 불필요'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Claude API 호출"""
        
        if not self.is_available():
            raise RuntimeError("Claude API 키가 설정되지 않았습니다.")
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # API 호출
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
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
                }],
            )
            
            caption = response.content[0].text.strip()
            processing_time = time.time() - start_time
            
            # 비용 계산
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
            
            return {
                'caption': caption,
                'confidence': 0.95,
                'processing_time': processing_time,
                'model': self.model,
                'provider': 'Claude',
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                },
                'cost_usd': cost_usd
            }
            
        except Exception as e:
            logger.error(f"Claude API 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성"""
        type_names = {
            'chart': '차트',
            'table': '표',
            'image': '이미지',
            'diagram': '다이어그램'
        }
        
        type_name = type_names.get(element_type, '요소')
        
        if extracted_text and len(extracted_text) > 10:
            return f"""다음은 OCR로 추출한 텍스트입니다:

{extracted_text[:1000]}

위 텍스트와 이미지를 분석하여, 이 {type_name}의 내용을 설명해주세요:

1. 주요 내용: 제목, 핵심 데이터
2. 구조: 레이아웃, 시각적 요소
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""
        else:
            return f"""이 {type_name} 이미지를 분석하여 설명해주세요:

1. 내용: 제목, 데이터
2. 구조: 레이아웃
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""


# ========== Azure OpenAI Provider ==========
class AzureOpenAIProvider(VLMProvider):
    """Azure OpenAI 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4-vision")
        self.api_version = "2024-02-15-preview"
    
    def is_available(self) -> bool:
        """API 키와 엔드포인트 존재 여부"""
        return bool(self.api_key and self.endpoint)
    
    def get_name(self) -> str:
        return "Azure OpenAI GPT-4V"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            'name': self.get_name(),
            'provider': 'Microsoft Azure',
            'model': self.deployment,
            'speed': '⚡⚡ 빠름 (1-3초)',
            'quality': '⭐⭐⭐⭐ 우수',
            'cost': '💰💰 유료 ($0.01/image)',
            'internet': '✅ 필요',
            'gpu': '❌ 불필요',
            'special': '🏛️ 공공기관 승인 가능'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Azure OpenAI API 호출"""
        
        if not self.is_available():
            raise RuntimeError("Azure OpenAI 설정이 완료되지 않았습니다.")
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # API URL
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
            
            # 요청 데이터
            data = {
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
                "max_tokens": 1000
            }
            
            # API 호출
            response = requests.post(
                url,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Azure API 오류: {response.status_code} - {response.text}")
            
            result = response.json()
            caption = result['choices'][0]['message']['content'].strip()
            processing_time = time.time() - start_time
            
            # 토큰 사용량
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # 비용 계산 (GPT-4V 기준)
            cost_usd = (input_tokens * 0.01 / 1000) + (output_tokens * 0.03 / 1000)
            
            return {
                'caption': caption,
                'confidence': 0.90,
                'processing_time': processing_time,
                'model': self.deployment,
                'provider': 'Azure OpenAI',
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                },
                'cost_usd': cost_usd
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI API 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성 (Claude와 동일)"""
        type_names = {
            'chart': '차트',
            'table': '표',
            'image': '이미지',
            'diagram': '다이어그램'
        }
        
        type_name = type_names.get(element_type, '요소')
        
        if extracted_text and len(extracted_text) > 10:
            return f"""다음은 OCR로 추출한 텍스트입니다:

{extracted_text[:1000]}

위 텍스트와 이미지를 분석하여, 이 {type_name}의 내용을 설명해주세요:

1. 주요 내용: 제목, 핵심 데이터
2. 구조: 레이아웃, 시각적 요소
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""
        else:
            return f"""이 {type_name} 이미지를 분석하여 설명해주세요:

1. 내용: 제목, 데이터
2. 구조: 레이아웃
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""


# ========== Ollama Provider ==========
class OllamaProvider(VLMProvider):
    """Ollama 로컬 프로바이더"""
    
    # 타임아웃 설정
    TIMEOUTS = {
        'llava:7b': 60,
        'llama3.2-vision:11b': 120,
        'llama3.2-vision:latest': 120,
        'default': 60
    }
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.preferred_model = os.getenv("OLLAMA_MODEL", "llava:7b")
        self.available_models: List[str] = []
        self.current_model: Optional[str] = None
        
        # 초기화
        self._initialize()
    
    def _initialize(self):
        """Ollama 초기화"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [
                    model['name'] 
                    for model in data.get('models', [])
                    if 'vision' in model['name'].lower() or 'llava' in model['name'].lower()
                ]
                
                if self.preferred_model in self.available_models:
                    self.current_model = self.preferred_model
                elif self.available_models:
                    self.current_model = self.available_models[0]
                
                if self.current_model:
                    logger.info(f"Ollama 초기화: {self.current_model}")
        except Exception as e:
            logger.warning(f"Ollama 연결 실패: {e}")
    
    def is_available(self) -> bool:
        """Ollama 사용 가능 여부"""
        return bool(self.current_model)
    
    def get_name(self) -> str:
        return f"Ollama ({self.current_model or 'N/A'})"
    
    def get_info(self) -> Dict[str, Any]:
        model_info = {
            'llava:7b': {
                'vram': '4GB',
                'speed': '⚡ 보통 (10-30초)',
                'quality': '⭐⭐⭐ 보통'
            },
            'llama3.2-vision:11b': {
                'vram': '8GB',
                'speed': '⚡⚡ 느림 (30-60초)',
                'quality': '⭐⭐⭐⭐ 좋음'
            }
        }
        
        info = model_info.get(self.current_model, {
            'vram': 'Unknown',
            'speed': '⚡ 보통',
            'quality': '⭐⭐⭐ 보통'
        })
        
        return {
            'name': self.get_name(),
            'provider': 'Ollama (Local)',
            'model': self.current_model or 'N/A',
            'speed': info['speed'],
            'quality': info['quality'],
            'cost': '💰 무료',
            'internet': '❌ 불필요',
            'gpu': '⚠️ 권장 (4GB+)',
            'vram': info['vram']
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Ollama API 호출"""
        
        if not self.is_available():
            raise RuntimeError("Ollama 모델이 없습니다. 'ollama pull llava:7b' 실행")
        
        start_time = time.time()
        timeout = self.TIMEOUTS.get(self.current_model, self.TIMEOUTS['default'])
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 300
                    }
                },
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")
            
            result = response.json()
            caption = result.get('response', '').strip()
            processing_time = time.time() - start_time
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(caption, extracted_text, element_type)
            
            return {
                'caption': caption,
                'confidence': confidence,
                'processing_time': processing_time,
                'model': self.current_model,
                'provider': 'Ollama',
                'usage': {
                    'input_tokens': 0,
                    'output_tokens': 0
                },
                'cost_usd': 0.0
            }
            
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Ollama 타임아웃 ({timeout}초). "
                f"더 작은 모델을 사용하거나 GPU를 확인하세요."
            )
        except Exception as e:
            logger.error(f"Ollama 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성 (동일)"""
        type_names = {
            'chart': '차트',
            'table': '표',
            'image': '이미지',
            'diagram': '다이어그램'
        }
        
        type_name = type_names.get(element_type, '요소')
        
        if extracted_text and len(extracted_text) > 10:
            return f"""다음은 OCR로 추출한 텍스트입니다:

{extracted_text[:1000]}

위 텍스트와 이미지를 분석하여, 이 {type_name}의 내용을 설명해주세요:

1. 주요 내용
2. 구조
3. 의미

한국어로 간결하게 설명해주세요."""
        else:
            return f"""이 {type_name} 이미지를 분석하여 설명해주세요:

1. 내용
2. 구조
3. 의미

한국어로 간결하게 설명해주세요."""
    
    def _calculate_confidence(self, caption: str, extracted_text: str, element_type: str) -> float:
        """신뢰도 계산"""
        if not caption or len(caption) < 20:
            return 0.3
        
        confidence = 0.5
        
        if extracted_text:
            ocr_words = set(extracted_text.lower().split())
            caption_words = set(caption.lower().split())
            if ocr_words and caption_words:
                overlap = len(ocr_words & caption_words)
                confidence += min(0.3, overlap / len(ocr_words) * 0.5)
        
        if len(caption) > 100:
            confidence += 0.1
        
        return min(0.95, max(0.1, confidence))


# ========== 멀티 프로바이더 매니저 ==========
class MultiVLMService:
    """멀티 VLM 프로바이더 매니저"""
    
    def __init__(self):
        # 프로바이더 초기화
        self.providers = {
            'claude': ClaudeProvider(),
            'azure': AzureOpenAIProvider(),
            'ollama': OllamaProvider()
        }
        
        # 기본 프로바이더 설정
        self.current_provider_key = self._get_default_provider()
        
        logger.info(f"MultiVLMService 초기화: {self.current_provider_key}")
    
    def _get_default_provider(self) -> str:
        """기본 프로바이더 결정"""
        # .env에서 설정된 기본 프로바이더
        default = os.getenv("DEFAULT_VLM_PROVIDER", "auto")
        
        if default != "auto" and default in self.providers:
            if self.providers[default].is_available():
                return default
        
        # 자동 선택: Claude > Azure > Ollama
        for key in ['claude', 'azure', 'ollama']:
            if self.providers[key].is_available():
                return key
        
        # 모두 사용 불가능
        return 'ollama'  # 기본값
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """사용 가능한 프로바이더 목록"""
        result = []
        for key, provider in self.providers.items():
            result.append({
                'key': key,
                'name': provider.get_name(),
                'available': provider.is_available(),
                'info': provider.get_info()
            })
        return result
    
    def set_provider(self, provider_key: str):
        """프로바이더 변경"""
        if provider_key not in self.providers:
            raise ValueError(f"알 수 없는 프로바이더: {provider_key}")
        
        if not self.providers[provider_key].is_available():
            raise RuntimeError(f"{provider_key} 프로바이더를 사용할 수 없습니다.")
        
        self.current_provider_key = provider_key
        logger.info(f"프로바이더 변경: {provider_key}")
    
    def get_current_provider(self) -> VLMProvider:
        """현재 프로바이더 반환"""
        return self.providers[self.current_provider_key]
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """현재 프로바이더로 캡션 생성"""
        provider = self.get_current_provider()
        
        if not provider.is_available():
            raise RuntimeError(
                f"{provider.get_name()} 프로바이더를 사용할 수 없습니다. "
                f"설정을 확인하세요."
            )
        
        return await provider.generate_caption(
            image_base64=image_base64,
            element_type=element_type,
            extracted_text=extracted_text
        )
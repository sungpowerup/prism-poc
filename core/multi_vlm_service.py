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
import asyncio
from concurrent.futures import ThreadPoolExecutor

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


# ========== Claude Provider (REST API 직접 호출) ==========
class ClaudeProvider(VLMProvider):
    """Anthropic Claude 프로바이더 - REST API 직접 호출"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-sonnet-4-20250514"
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def is_available(self) -> bool:
        """API 키 존재 여부"""
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))
    
    def get_name(self) -> str:
        return "Claude Sonnet 4"
    
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
        """Claude API 호출 - REST API 직접 사용"""
        
        if not self.is_available():
            raise RuntimeError("Claude API 키가 설정되지 않았습니다.")
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # 요청 본문 구성
            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [{
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
            }
            
            # 헤더 구성
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # 비동기로 requests 호출 (ThreadPoolExecutor 사용)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
            )
            
            # 응답 확인
            if response.status_code != 200:
                error_msg = f"Claude API 오류 (HTTP {response.status_code}): {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # 응답 파싱
            result = response.json()
            caption = result['content'][0]['text'].strip()
            processing_time = time.time() - start_time
            
            # 비용 계산
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
            
            logger.info(
                f"Claude 처리 완료: {processing_time:.2f}초, "
                f"{input_tokens}+{output_tokens} tokens, ${cost_usd:.4f}"
            )
            
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API 네트워크 오류: {e}")
            raise RuntimeError(f"Claude API 호출 실패: {e}")
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
    """Azure OpenAI GPT-4V 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        # ✅ API Version을 환경변수에서 읽도록 수정
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def is_available(self) -> bool:
        """API 키와 엔드포인트 확인"""
        return bool(self.api_key and self.endpoint)
    
    def get_name(self) -> str:
        return "Azure OpenAI GPT-4"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            'name': self.get_name(),
            'provider': 'Azure OpenAI',
            'model': self.deployment,
            'speed': '⚡⚡ 빠름 (2-3초)',
            'quality': '⭐⭐⭐⭐ 우수',
            'cost': '💰💰 유료 ($0.01/image)',
            'internet': '✅ 필요 (한국 리전 가능)',
            'gpu': '❌ 불필요'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Azure OpenAI API 호출"""
        
        if not self.is_available():
            raise RuntimeError("Azure OpenAI API 설정이 올바르지 않습니다.")
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # URL 구성 (✅ self.api_version 사용)
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
            
            # 요청 본문
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
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            # 헤더
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # 비동기 호출
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: requests.post(url, headers=headers, json=payload, timeout=30)
            )
            
            # 응답 확인
            if response.status_code != 200:
                error_msg = f"Azure OpenAI 오류 (HTTP {response.status_code}): {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # 응답 파싱
            result = response.json()
            caption = result['choices'][0]['message']['content'].strip()
            processing_time = time.time() - start_time
            
            # 토큰 사용량
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            cost_usd = (input_tokens * 10 / 1_000_000) + (output_tokens * 30 / 1_000_000)
            
            logger.info(
                f"Azure OpenAI 처리 완료: {processing_time:.2f}초, "
                f"{input_tokens}+{output_tokens} tokens, ${cost_usd:.4f}"
            )
            
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Azure OpenAI 네트워크 오류: {e}")
            raise RuntimeError(f"Azure OpenAI 호출 실패: {e}")
        except Exception as e:
            logger.error(f"Azure OpenAI 오류: {e}")
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


# ========== Ollama Local Provider ==========
class OllamaProvider(VLMProvider):
    """Ollama (LLaVA) 로컬 프로바이더"""
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llava:7b")
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 초기화 로그
        logger.info(f"Ollama 초기화: {self.model}")
    
    def is_available(self) -> bool:
        """Ollama 서버 동작 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(m['name'] == self.model for m in models)
            return False
        except:
            return False
    
    def get_name(self) -> str:
        return f"Ollama ({self.model})"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            'name': self.get_name(),
            'provider': 'Ollama (Local)',
            'model': self.model,
            'speed': '⚡ 느림 (5-10초, GPU 필요)',
            'quality': '⭐⭐⭐ 보통',
            'cost': '💰 무료 (전기료만)',
            'internet': '❌ 불필요 (완전 오프라인)',
            'gpu': '✅ 필요 (8GB VRAM)'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Ollama API 호출"""
        
        if not self.is_available():
            raise RuntimeError(
                f"Ollama 서버에 연결할 수 없거나 {self.model} 모델이 없습니다. "
                f"'ollama pull {self.model}' 실행 후 다시 시도하세요."
            )
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(element_type, extracted_text)
            
            # 요청 본문
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False
            }
            
            # 비동기 호출
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: requests.post(url, json=payload, timeout=60)
            )
            
            # 응답 확인
            if response.status_code != 200:
                error_msg = f"Ollama 오류 (HTTP {response.status_code}): {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # 응답 파싱
            result = response.json()
            caption = result.get('response', '').strip()
            processing_time = time.time() - start_time
            
            logger.info(f"Ollama 처리 완료: {processing_time:.2f}초")
            
            return {
                'caption': caption,
                'confidence': 0.75,
                'processing_time': processing_time,
                'model': self.model,
                'provider': 'Ollama',
                'usage': {
                    'input_tokens': 0,
                    'output_tokens': 0
                },
                'cost_usd': 0.0
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 네트워크 오류: {e}")
            raise RuntimeError(f"Ollama 호출 실패: {e}")
        except Exception as e:
            logger.error(f"Ollama 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성"""
        type_names = {
            'chart': 'chart',
            'table': 'table',
            'image': 'image',
            'diagram': 'diagram'
        }
        
        type_name = type_names.get(element_type, 'element')
        
        if extracted_text and len(extracted_text) > 10:
            return f"""Analyze this {type_name}. OCR text: {extracted_text[:500]}

Describe:
1. Main content and title
2. Layout structure
3. Key message

Answer in Korean, clearly and concisely."""
        else:
            return f"""Describe this {type_name}:

1. Content and title
2. Layout
3. Key message

Answer in Korean, clearly and concisely."""


# ========== Multi VLM Service ==========
class MultiVLMService:
    """멀티 VLM 통합 서비스"""
    
    def __init__(self, default_provider: str = "claude"):
        """
        초기화
        
        Args:
            default_provider: 기본 프로바이더 (claude/azure_openai/ollama)
        """
        # 프로바이더 초기화
        self.providers = {
            'claude': ClaudeProvider(),
            'azure_openai': AzureOpenAIProvider(),
            'ollama': OllamaProvider()
        }
        
        # 기본 프로바이더 설정
        if default_provider in self.providers:
            self.current_provider_key = default_provider
        else:
            # 사용 가능한 첫 번째 프로바이더
            for key, provider in self.providers.items():
                if provider.is_available():
                    self.current_provider_key = key
                    break
            else:
                self.current_provider_key = 'claude'  # fallback
        
        logger.info(f"MultiVLMService 초기화: {self.current_provider_key}")
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 프로바이더 목록"""
        result = {}
        for key, provider in self.providers.items():
            info = provider.get_info()
            info['available'] = provider.is_available()
            result[key] = info
        return result
    
    def set_provider(self, provider_key: str):
        """프로바이더 변경"""
        if provider_key not in self.providers:
            raise ValueError(f"알 수 없는 프로바이더: {provider_key}")
        
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
"""
core/vlm_service.py
멀티 VLM 프로바이더 지원 (Claude + Ollama)
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class VLMProvider(ABC):
    """VLM 프로바이더 추상 클래스"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """사용 가능 여부 확인"""
        pass
    
    @abstractmethod
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str,
        extracted_text: str
    ) -> Dict[str, Any]:
        """캡션 생성"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, str]:
        """프로바이더 정보"""
        pass


class AzureOpenAIProvider(VLMProvider):
    """Azure OpenAI 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4-vision")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.client = None
        
        if self.api_key and self.endpoint:
            try:
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint
                )
                logger.info("Azure OpenAI 초기화 완료")
            except ImportError:
                logger.warning("openai 패키지가 설치되지 않았습니다. pip install openai")
            except Exception as e:
                logger.error(f"Azure OpenAI 초기화 실패: {e}")
    
    def is_available(self) -> bool:
        """사용 가능 여부"""
        return self.client is not None
    
    def get_info(self) -> Dict[str, str]:
        """프로바이더 정보"""
        return {
            'name': 'GPT-4 Vision (Azure)',
            'provider': 'Azure OpenAI',
            'speed': '⚡ 빠름 (3-5초)',
            'quality': '⭐⭐⭐⭐⭐ 최고',
            'cost': '💰 유료 (~$0.015/페이지)',
            'description': 'Microsoft Azure 기반. 엔터프라이즈급 보안. 한글 문서 우수'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Azure OpenAI API 호출"""
        start_time = time.time()
        
        try:
            prompt = self._build_prompt(element_type, extracted_text)
            
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
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            processing_time = time.time() - start_time
            caption = response.choices[0].message.content.strip()
            
            # 토큰 사용량 및 비용 계산
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Azure OpenAI GPT-4 Vision 가격 (대략적)
            # Input: $10 / 1M tokens
            # Output: $30 / 1M tokens
            cost_usd = (input_tokens * 10 / 1_000_000) + (output_tokens * 30 / 1_000_000)
            
            logger.info(
                f"✅ Azure OpenAI 완료 | {processing_time:.1f}초 | "
                f"토큰: {input_tokens + output_tokens:,} | ${cost_usd:.4f}"
            )
            
            return {
                'caption': caption,
                'confidence': 0.93,
                'processing_time': processing_time,
                'model': f'GPT-4 Vision ({self.deployment})',
                'provider': 'Azure OpenAI',
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cost_usd': cost_usd,
                    'cost_krw': int(cost_usd * 1300)
                }
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI API 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성"""
        base = """이 한글 문서 페이지를 매우 상세히 분석하여 설명해주세요.

포함 내용:
1. 제목/헤더
2. 주요 내용 (표/차트/다이어그램/본문)
3. 구체적인 수치 (날짜, 숫자, 비율)
4. 시각적 특징

200-600자, 자연스러운 한국어로 작성"""
        
        if extracted_text and len(extracted_text) > 50:
            return f"""{base}

**OCR 텍스트 참고**:
{extracted_text[:2500]}"""
        
        return base


class ClaudeProvider(VLMProvider):
    """Claude API 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.model = "claude-sonnet-4-20250514"
        
        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                logger.info("Claude API 초기화 완료")
            except ImportError:
                logger.warning("anthropic 패키지가 설치되지 않았습니다. pip install anthropic")
            except Exception as e:
                logger.error(f"Claude API 초기화 실패: {e}")
    
    def is_available(self) -> bool:
        """사용 가능 여부"""
        return self.client is not None
    
    def get_info(self) -> Dict[str, str]:
        """프로바이더 정보"""
        return {
            'name': 'Claude Sonnet 4',
            'provider': 'Anthropic',
            'speed': '⚡ 빠름 (2-3초)',
            'quality': '⭐⭐⭐⭐⭐ 최고',
            'cost': '💰 유료 (~$0.01/페이지)',
            'description': '최고 품질의 한글 문서 이해. 표, 차트, 다이어그램 완벽 분석'
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Claude API 호출"""
        start_time = time.time()
        
        try:
            prompt = self._build_prompt(element_type, extracted_text)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1536,
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
            
            processing_time = time.time() - start_time
            caption = response.content[0].text.strip()
            
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
            
            logger.info(
                f"✅ Claude 완료 | {processing_time:.1f}초 | "
                f"토큰: {input_tokens + output_tokens:,} | ${cost_usd:.4f}"
            )
            
            return {
                'caption': caption,
                'confidence': 0.95,
                'processing_time': processing_time,
                'model': 'Claude Sonnet 4',
                'provider': 'Anthropic',
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cost_usd': cost_usd,
                    'cost_krw': int(cost_usd * 1300)
                }
            }
            
        except Exception as e:
            logger.error(f"Claude API 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성"""
        base = """이 한글 문서 페이지를 매우 상세히 분석하여 설명해주세요.

포함 내용:
1. 제목/헤더
2. 주요 내용 (표/차트/다이어그램/본문)
3. 구체적인 수치 (날짜, 숫자, 비율)
4. 시각적 특징

200-600자, 자연스러운 한국어로 작성"""
        
        if extracted_text and len(extracted_text) > 50:
            return f"""{base}

**OCR 텍스트 참고**:
{extracted_text[:2500]}"""
        
        return base


class OllamaProvider(VLMProvider):
    """Ollama 로컬 프로바이더"""
    
    def __init__(self, model_name: str):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model_name
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Ollama 연결 확인"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if any(self.model in name for name in model_names):
                    logger.info(f"Ollama {self.model} 사용 가능")
                    return True
                else:
                    logger.warning(f"Ollama 모델 '{self.model}' 미설치")
                    return False
            
            return False
            
        except Exception as e:
            logger.warning(f"Ollama 연결 실패: {e}")
            return False
    
    def is_available(self) -> bool:
        return self.available
    
    def get_info(self) -> Dict[str, str]:
        """프로바이더 정보"""
        model_info = {
            'llava:7b': {
                'name': 'LLaVA 7B',
                'speed': '🐢 느림 (60-80초)',
                'quality': '⭐⭐ 기본',
                'description': '기본 모델. 한글 약함'
            },
            'llava:13b': {
                'name': 'LLaVA 13B',
                'speed': '🐌 매우 느림 (90-120초)',
                'quality': '⭐⭐⭐ 보통',
                'description': '더 큰 모델. 한글 개선'
            },
            'llama3.2-vision:11b': {
                'name': 'Llama 3.2 Vision 11B',
                'speed': '🐢 느림 (30-60초)',
                'quality': '⭐⭐⭐ 보통',
                'description': 'Meta 최신. 한글 준수'
            }
        }
        
        info = model_info.get(self.model, {
            'name': self.model,
            'speed': '❓ 알 수 없음',
            'quality': '❓ 알 수 없음',
            'description': '사용자 정의 모델'
        })
        
        return {
            'name': info['name'],
            'provider': 'Ollama (로컬)',
            'speed': info['speed'],
            'quality': info['quality'],
            'cost': '✅ 무료',
            'description': info['description']
        }
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Ollama API 호출"""
        import requests
        
        start_time = time.time()
        
        try:
            prompt = self._build_prompt(element_type, extracted_text)
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "num_predict": 600
                    }
                },
                timeout=180
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")
            
            processing_time = time.time() - start_time
            result_data = response.json()
            caption = result_data.get('response', '').strip()
            
            confidence = self._calculate_confidence(caption, extracted_text)
            
            logger.info(f"✅ Ollama 완료 | {processing_time:.1f}초 | 신뢰도: {confidence:.2f}")
            
            return {
                'caption': caption,
                'confidence': confidence,
                'processing_time': processing_time,
                'model': self.model,
                'provider': 'Ollama (로컬)',
                'usage': {
                    'cost_usd': 0.0,
                    'cost_krw': 0
                }
            }
            
        except Exception as e:
            logger.error(f"Ollama 오류: {e}")
            raise
    
    def _build_prompt(self, element_type: str, extracted_text: str) -> str:
        """프롬프트 생성"""
        if extracted_text and len(extracted_text) > 50:
            return f"""이 한글 문서 페이지를 분석하세요.

OCR 텍스트:
{extracted_text[:2000]}

위 텍스트와 이미지를 보고 200-500자로 상세히 설명하세요:
- 제목/헤더
- 주요 내용 (표/차트/본문)
- 구체적인 값들
- 레이아웃

한국어로만 답변하세요."""
        else:
            return """이 한글 문서 페이지를 200-500자로 상세히 설명하세요:
- 제목
- 내용
- 구조
한국어로만 답변하세요."""
    
    def _calculate_confidence(self, caption: str, extracted_text: str) -> float:
        """신뢰도 계산"""
        confidence = 0.70
        
        if len(caption) > 150:
            confidence += 0.10
        
        korean_chars = sum(1 for c in caption if '가' <= c <= '힣')
        total_chars = len(caption.replace(' ', ''))
        
        if total_chars > 0 and korean_chars / total_chars > 0.5:
            confidence += 0.10
        
        import re
        if len(re.findall(r'\d+', caption)) >= 3:
            confidence += 0.05
        
        return min(0.90, confidence)


class VLMService:
    """멀티 프로바이더 VLM 서비스"""
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        초기화
        
        Args:
            provider_name: 프로바이더 이름 ('claude', 'llava:7b', 'llama3.2-vision:11b' 등)
        """
        self.providers = self._initialize_providers()
        self.current_provider = None
        
        if provider_name:
            self.set_provider(provider_name)
        else:
            # 사용 가능한 첫 번째 프로바이더 선택
            self._select_default_provider()
    
    def _initialize_providers(self) -> Dict[str, VLMProvider]:
        """모든 프로바이더 초기화"""
        providers = {
            'claude': ClaudeProvider(),
            'llava:7b': OllamaProvider('llava:7b'),
            'llava:13b': OllamaProvider('llava:13b'),
            'llama3.2-vision:11b': OllamaProvider('llama3.2-vision:11b'),
        }
        
        return providers
    
    def _select_default_provider(self):
        """기본 프로바이더 선택"""
        # Claude 우선, 없으면 사용 가능한 Ollama 모델
        for name in ['claude', 'llama3.2-vision:11b', 'llava:13b', 'llava:7b']:
            if self.providers[name].is_available():
                self.current_provider = self.providers[name]
                logger.info(f"기본 프로바이더 선택: {name}")
                return
        
        raise RuntimeError(
            "사용 가능한 VLM 프로바이더가 없습니다.\n"
            "1. Claude API: .env에 ANTHROPIC_API_KEY 추가\n"
            "2. Ollama: ollama pull llama3.2-vision:11b"
        )
    
    def get_available_providers(self) -> Dict[str, Dict[str, str]]:
        """사용 가능한 프로바이더 목록"""
        available = {}
        
        for name, provider in self.providers.items():
            if provider.is_available():
                info = provider.get_info()
                info['id'] = name
                available[name] = info
        
        return available
    
    def set_provider(self, provider_name: str) -> bool:
        """프로바이더 변경"""
        if provider_name not in self.providers:
            logger.error(f"알 수 없는 프로바이더: {provider_name}")
            return False
        
        if not self.providers[provider_name].is_available():
            logger.error(f"프로바이더 사용 불가: {provider_name}")
            return False
        
        self.current_provider = self.providers[provider_name]
        logger.info(f"프로바이더 변경: {provider_name}")
        return True
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """현재 프로바이더로 캡션 생성"""
        if not self.current_provider:
            raise RuntimeError("프로바이더가 설정되지 않았습니다.")
        
        return await self.current_provider.generate_caption(
            image_base64, element_type, extracted_text
        )
    
    def get_current_provider_info(self) -> Dict[str, str]:
        """현재 프로바이더 정보"""
        if not self.current_provider:
            return {'name': 'None', 'provider': 'None'}
        
        return self.current_provider.get_info()
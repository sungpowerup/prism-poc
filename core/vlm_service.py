"""
core/vlm_service.py
PRISM Phase 3.0 - VLM API 통합 서비스 (수정판)

Azure OpenAI / Anthropic Claude / Ollama 지원
"""

import os
import base64
import time
import json
from typing import Optional, Dict, Any, Union
import logging
import cv2
import numpy as np
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)


class VLMService:
    """VLM API 서비스 (멀티 프로바이더)"""
    
    def __init__(self, provider='azure_openai'):
        """
        Args:
            provider: 'azure_openai', 'claude', 'ollama'
        """
        self.provider = provider
        
        if provider == 'azure_openai':
            self._init_azure_openai()
        elif provider == 'claude':
            self._init_claude()
        elif provider == 'ollama':
            self._init_ollama()
        else:
            raise ValueError(f"지원하지 않는 프로바이더: {provider}")
        
        logger.info(f"VLM Service 초기화: {provider}")
    
    def _init_azure_openai(self):
        """Azure OpenAI 초기화"""
        from openai import AzureOpenAI
        
        self.client = AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        self.deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
    
    def _init_claude(self):
        """Anthropic Claude 초기화"""
        from anthropic import Anthropic
        
        self.client = Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.model = "claude-sonnet-4-20250514"
    
    def _init_ollama(self):
        """Ollama 초기화"""
        import requests
        
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llava:7b')
    
    def analyze_image(
        self,
        image: Union[np.ndarray, bytes],
        prompt: str,
        max_tokens: int = 2000
    ) -> Union[str, Dict]:
        """
        이미지 분석 (통합 인터페이스)
        
        Args:
            image: numpy array 또는 bytes
            prompt: 분석 프롬프트
            max_tokens: 최대 토큰 수
            
        Returns:
            str 또는 dict (JSON인 경우)
        """
        start_time = time.time()
        
        # numpy array → bytes 변환
        if isinstance(image, np.ndarray):
            image_bytes = self._numpy_to_bytes(image)
        else:
            image_bytes = image
        
        # Base64 인코딩
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 프로바이더별 호출
        try:
            if self.provider == 'azure_openai':
                result = self._call_azure_openai(image_b64, prompt, max_tokens)
            elif self.provider == 'claude':
                result = self._call_claude(image_b64, prompt, max_tokens)
            elif self.provider == 'ollama':
                result = self._call_ollama(image_b64, prompt, max_tokens)
            
            elapsed = time.time() - start_time
            logger.info(f"   VLM 분석 완료: {elapsed:.2f}초")
            
            # JSON 파싱 시도
            if isinstance(result, str) and (result.strip().startswith('{') or 'json' in prompt.lower()):
                try:
                    # 마크다운 코드 블록 제거
                    clean_result = result.replace('```json', '').replace('```', '').strip()
                    return json.loads(clean_result)
                except json.JSONDecodeError:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"   VLM 분석 실패: {e}")
            raise
    
    def _call_azure_openai(self, image_b64: str, prompt: str, max_tokens: int) -> str:
        """Azure OpenAI 호출"""
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
                                "url": f"data:image/png;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=max_tokens,
            temperature=0.0
        )
        
        return response.choices[0].message.content
    
    def _call_claude(self, image_b64: str, prompt: str, max_tokens: int) -> str:
        """Anthropic Claude 호출"""
        message = self.client.messages.create(
            model=self.model,
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
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            temperature=0.0
        )
        
        return message.content[0].text
    
    def _call_ollama(self, image_b64: str, prompt: str, max_tokens: int) -> str:
        """Ollama 호출"""
        import requests
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.0
                }
            },
            timeout=120
        )
        
        response.raise_for_status()
        return response.json()['response']
    
    def _numpy_to_bytes(self, image: np.ndarray) -> bytes:
        """numpy array → PNG bytes"""
        # BGR → RGB 변환 (OpenCV 사용하는 경우)
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # PNG 인코딩
        success, encoded = cv2.imencode('.png', image)
        
        if not success:
            raise ValueError("이미지 인코딩 실패")
        
        return encoded.tobytes()


# 테스트 코드
if __name__ == '__main__':
    # 간단한 테스트
    vlm = VLMService(provider='azure_openai')
    
    # 테스트 이미지 생성
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.putText(test_image, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 테스트 호출
    result = vlm.analyze_image(test_image, "이 이미지에 무엇이 있나요?")
    
    print(f"결과: {result}")
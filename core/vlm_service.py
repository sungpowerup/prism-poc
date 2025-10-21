"""
core/vlm_service.py
VLM 서비스 (UTF-8 인코딩 완전 수정)

핵심 수정:
1. Azure OpenAI 응답 강제 UTF-8 인코딩
2. 프롬프트에 "한국어로 응답" 명시
3. JSON 저장 시 ensure_ascii=False
"""

import os
import time
from typing import Dict, List
from dotenv import load_dotenv
import json

# 프롬프트 임포트
from prompts.chart_prompt import get_chart_prompt
from prompts.table_prompt import get_table_prompt
from prompts.diagram_prompt import get_diagram_prompt

load_dotenv()


class VLMService:
    """
    멀티 VLM 서비스
    
    지원:
    - azure_openai: Azure OpenAI GPT-4V
    - claude: Anthropic Claude 3.5
    - local_sllm: Ollama (LLaVA)
    """
    
    def __init__(self, provider: str = 'azure_openai'):
        self.provider = provider
        
        if provider == 'azure_openai':
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
            )
            self.deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4-vision')
        
        elif provider == 'claude':
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        elif provider == 'local_sllm':
            import requests
            self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            self.model = os.getenv('OLLAMA_MODEL', 'llava:13b')
        
        else:
            raise ValueError(f"지원하지 않는 provider: {provider}")
    
    def generate_caption(
        self, 
        image_data: str, 
        element_type: str,
        subtypes: List[str] = None
    ) -> Dict:
        """
        이미지 캡션 생성
        
        Args:
            image_data: Base64 인코딩된 이미지
            element_type: 'chart', 'table', 'diagram', 'text', 'image'
            subtypes: ['pie', 'bar'] 등
        
        Returns:
            {
                'caption': str,
                'tokens_used': int,
                'processing_time_sec': float
            }
        """
        start_time = time.time()
        
        # 프롬프트 선택
        prompt = self._select_prompt(element_type, subtypes)
        
        # ✅ 수정: 프롬프트에 한국어 응답 강제 추가
        prompt = f"{prompt}\n\n**중요: 반드시 한국어로 응답하세요. 모든 텍스트는 UTF-8 인코딩으로 작성하세요.**"
        
        # VLM 호출
        if self.provider == 'azure_openai':
            result = self._call_azure_openai(image_data, prompt)
        elif self.provider == 'claude':
            result = self._call_claude(image_data, prompt)
        elif self.provider == 'local_sllm':
            result = self._call_ollama(image_data, prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # ✅ 수정: UTF-8 인코딩 강제 보장
        caption = self._force_utf8(result['caption'])
        
        processing_time = time.time() - start_time
        
        return {
            'caption': caption,
            'tokens_used': result.get('tokens_used', 0),
            'processing_time_sec': processing_time
        }
    
    def _select_prompt(self, element_type: str, subtypes: List[str]) -> str:
        """
        Element 타입과 세부 타입에 맞는 프롬프트 선택
        """
        if element_type == 'chart':
            return get_chart_prompt(subtypes)
        elif element_type == 'table':
            return get_table_prompt()
        elif element_type == 'diagram':
            return get_diagram_prompt(subtypes)
        else:
            # 기본 프롬프트
            return "이 이미지를 자세히 설명하세요."
    
    def _call_azure_openai(self, image_data: str, prompt: str) -> Dict:
        """
        Azure OpenAI 호출 (UTF-8 강제)
        """
        # data:image/png;base64, 제거
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes images in Korean. Always respond in UTF-8 encoded Korean."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        # ✅ 수정: 응답 텍스트 UTF-8 강제 변환
        raw_caption = response.choices[0].message.content
        
        # 1차: 바이트 → UTF-8
        caption_bytes = raw_caption.encode('utf-8', errors='ignore')
        caption = caption_bytes.decode('utf-8', errors='ignore')
        
        tokens_used = response.usage.total_tokens
        
        return {
            'caption': caption,
            'tokens_used': tokens_used
        }
    
    def _call_claude(self, image_data: str, prompt: str) -> Dict:
        """
        Claude 호출
        """
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        message = self.client.messages.create(
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
        
        caption = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens
        
        return {
            'caption': caption,
            'tokens_used': tokens_used
        }
    
    def _call_ollama(self, image_data: str, prompt: str) -> Dict:
        """
        Ollama 호출
        """
        import requests
        
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False
            },
            timeout=120
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            'caption': result['response'],
            'tokens_used': 0  # Ollama는 토큰 미제공
        }
    
    def _force_utf8(self, text: str) -> str:
        """
        UTF-8 인코딩 강제 보장
        
        Steps:
        1. bytes → UTF-8 디코딩
        2. 깨진 문자 제거
        3. 재검증
        """
        try:
            # 1차: 바이트 변환
            text_bytes = text.encode('utf-8', errors='ignore')
            clean_text = text_bytes.decode('utf-8', errors='ignore')
            
            # 2차: 깨진 패턴 확인
            if self._has_encoding_issue(clean_text):
                # Latin1로 재인코딩 시도
                text_bytes = clean_text.encode('latin1', errors='ignore')
                clean_text = text_bytes.decode('utf-8', errors='ignore')
            
            return clean_text
        
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            print(f"⚠️  인코딩 변환 실패: {e}")
            return text
    
    def _has_encoding_issue(self, text: str) -> bool:
        """
        인코딩 문제 감지
        
        특징:
        - 한글이 깨지면 ì, ë, í 등의 특정 패턴 나타남
        """
        bad_patterns = ['ì', 'ë', 'í', 'ê', 'î', 'ï', 'ð', 'ñ', 'Â']
        
        # 패턴이 여러 개 나타나면 인코딩 문제
        count = sum(1 for p in bad_patterns if p in text)
        
        return count >= 3


# 테스트
if __name__ == '__main__':
    import base64
    
    # 테스트용 이미지 (1x1 투명 PNG)
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    service = VLMService(provider='azure_openai')
    result = service.generate_caption(
        image_data=test_image,
        element_type='chart',
        subtypes=['pie', 'bar']
    )
    
    print(f"Caption: {result['caption']}")
    print(f"Tokens: {result['tokens_used']}")
    print(f"Time: {result['processing_time_sec']:.2f}s")
    
    # 한글 테스트
    if 'ì' in result['caption'] or 'ë' in result['caption']:
        print("❌ 한글 인코딩 실패")
    else:
        print("✅ 한글 인코딩 성공")
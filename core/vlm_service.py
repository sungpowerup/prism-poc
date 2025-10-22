"""
PRISM Phase 3.0 - VLM Service (UTF-8 처리 개선)
"""

import os
import base64
import json
import time
import logging
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class VLMService:
    """
    Vision Language Model 서비스
    UTF-8 인코딩 처리 개선
    """
    
    def __init__(self, provider: str = "azure_openai"):
        """
        VLM 서비스 초기화
        
        Args:
            provider: 'azure_openai', 'claude', 'ollama'
        """
        self.provider = provider
        
        if provider == "azure_openai":
            self.client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        elif provider == "claude":
            self.client = Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            self.model = "claude-3-5-sonnet-20241022"
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"VLM Service 초기화: {provider}")
    
    def analyze_image(
        self,
        image_data: str,
        element_type: str,
        prompt: str
    ) -> str:
        """
        이미지 분석 (UTF-8 처리 강화)
        
        Args:
            image_data: Base64 인코딩된 이미지
            element_type: 'pie_chart', 'bar_chart', 'table', 'map', 'header'
            prompt: 분석 프롬프트
            
        Returns:
            분석 결과 (UTF-8 문자열)
        """
        start_time = time.time()
        
        try:
            if self.provider == "azure_openai":
                result = self._analyze_with_azure(image_data, prompt)
            elif self.provider == "claude":
                result = self._analyze_with_claude(image_data, prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # ✅ UTF-8 인코딩 검증 및 수정
            result = self._ensure_utf8(result)
            
            elapsed = time.time() - start_time
            logger.info(f"   VLM 분석 완료: {elapsed:.2f}초")
            
            return result
        
        except Exception as e:
            logger.error(f"   VLM 분석 실패: {str(e)}")
            raise
    
    def _analyze_with_azure(self, image_data: str, prompt: str) -> str:
        """
        Azure OpenAI로 이미지 분석
        
        Args:
            image_data: Base64 이미지
            prompt: 프롬프트
            
        Returns:
            분석 결과
        """
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
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        return response.choices[0].message.content
    
    def _analyze_with_claude(self, image_data: str, prompt: str) -> str:
        """
        Claude로 이미지 분석
        
        Args:
            image_data: Base64 이미지
            prompt: 프롬프트
            
        Returns:
            분석 결과
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.1,
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
        
        return response.content[0].text
    
    def _ensure_utf8(self, text: str) -> str:
        """
        UTF-8 인코딩 검증 및 수정
        
        Args:
            text: 입력 텍스트
            
        Returns:
            UTF-8로 보장된 텍스트
        """
        try:
            # 1. 이미 UTF-8인지 확인
            text.encode('utf-8').decode('utf-8')
            return text
        
        except UnicodeDecodeError:
            logger.warning("   UTF-8 디코딩 오류 감지, 수정 시도 중...")
            
            # 2. Latin-1 → UTF-8 변환 시도
            try:
                # Latin-1로 인코딩 후 UTF-8로 디코딩
                fixed_text = text.encode('latin-1').decode('utf-8')
                logger.info("   ✅ UTF-8 변환 성공 (Latin-1 → UTF-8)")
                return fixed_text
            
            except (UnicodeDecodeError, UnicodeEncodeError):
                # 3. 강제 변환 (잘못된 문자 제거)
                logger.warning("   ⚠️ 강제 UTF-8 변환 (일부 문자 손실 가능)")
                return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        
        except Exception as e:
            logger.error(f"   UTF-8 처리 실패: {str(e)}")
            return text
    
    def _fix_mojibake(self, text: str) -> str:
        """
        Mojibake (문자 깨짐) 수정
        
        Args:
            text: 깨진 텍스트 (예: "ì§€ì—­ë³„")
            
        Returns:
            복원된 텍스트 (예: "지역별")
        """
        try:
            # Latin-1로 잘못 디코딩된 UTF-8을 복원
            return text.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text
    
    def extract_map_data(self, content: str) -> Dict[str, Any]:
        """
        지도 데이터 추출 (JSON 파싱 강화)
        
        Args:
            content: VLM 응답 텍스트
            
        Returns:
            추출된 데이터
        """
        # JSON 블록 추출 시도
        try:
            # 1. 직접 JSON 파싱
            data = json.loads(content)
            return data
        
        except json.JSONDecodeError:
            # 2. Markdown 코드 블록 제거 후 재시도
            try:
                # ```json ... ``` 제거
                cleaned = content.replace('```json', '').replace('```', '').strip()
                data = json.loads(cleaned)
                return data
            
            except json.JSONDecodeError:
                # 3. 자연어 텍스트로 반환 (JSON이 아님)
                logger.warning("   JSON 파싱 실패, 자연어 텍스트로 처리")
                return {
                    "text": content,
                    "regions": []
                }


class MultiVLMService:
    """
    다중 VLM 서비스 관리자 (폴백 지원)
    """
    
    def __init__(self, primary: str = "azure_openai", fallback: str = "claude"):
        """
        다중 VLM 초기화
        
        Args:
            primary: 주 VLM
            fallback: 폴백 VLM
        """
        self.primary = VLMService(primary)
        
        try:
            self.fallback = VLMService(fallback)
        except Exception as e:
            logger.warning(f"폴백 VLM 초기화 실패: {e}")
            self.fallback = None
    
    def analyze_image(
        self,
        image_data: str,
        element_type: str,
        prompt: str
    ) -> str:
        """
        이미지 분석 (폴백 지원)
        
        Args:
            image_data: Base64 이미지
            element_type: Element 타입
            prompt: 프롬프트
            
        Returns:
            분석 결과
        """
        try:
            return self.primary.analyze_image(image_data, element_type, prompt)
        
        except Exception as e:
            logger.warning(f"Primary VLM 실패: {e}")
            
            if self.fallback:
                logger.info("Fallback VLM으로 재시도...")
                return self.fallback.analyze_image(image_data, element_type, prompt)
            else:
                raise
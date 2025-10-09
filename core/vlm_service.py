"""
VLM Service with Ollama (Local sLLM)
Ollama Vision Model 서비스 (OCR 통합)
"""

import os
import logging
import base64
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VLMService:
    """Vision Language Model 서비스 (Ollama 로컬)"""
    
    def __init__(self):
        """초기화"""
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llava:7b")
        
        # Ollama 연결 확인
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"Ollama 연결 성공 (모델: {self.model})")
            else:
                raise ConnectionError("Ollama 서버 응답 없음")
        except Exception as e:
            logger.error(f"Ollama 연결 실패: {e}")
            raise ConnectionError(
                f"Ollama 서버에 연결할 수 없습니다. "
                f"'ollama serve'가 실행 중인지 확인하세요."
            )
    
    def _build_prompt_with_ocr(
        self, 
        element_type: str,
        extracted_text: str
    ) -> str:
        """
        OCR 텍스트를 포함한 프롬프트 생성
        
        Args:
            element_type: Element 타입
            extracted_text: OCR로 추출한 텍스트
            
        Returns:
            프롬프트 문자열
        """
        
        type_names = {
            'chart': '차트',
            'table': '표',
            'image': '이미지',
            'diagram': '다이어그램'
        }
        
        type_name = type_names.get(element_type, '요소')
        
        if extracted_text and len(extracted_text) > 10:
            prompt = f"""다음은 문서 이미지에서 OCR로 추출한 텍스트입니다:

---
{extracted_text[:1500]}
---

위 텍스트와 이미지를 함께 분석하여, 이 {type_name}의 내용을 자세히 설명해주세요:

1. 주요 내용: 제목, 핵심 데이터, 중요 정보
2. 구조: 레이아웃, 시각적 요소
3. 의미: 핵심 메시지와 중요성

한국어로 명확하게 설명해주세요."""
        else:
            prompt = f"""이 {type_name} 이미지를 분석하여 설명해주세요:

1. 내용: 제목, 데이터, 정보
2. 구조: 레이아웃, 시각적 요소
3. 의미: 핵심 메시지

한국어로 명확하게 설명해주세요."""
        
        return prompt
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """
        Ollama로 캡션 생성 (OCR 텍스트 포함)
        
        Args:
            image_base64: Base64 인코딩된 이미지
            element_type: Element 타입
            extracted_text: OCR로 추출한 텍스트
            
        Returns:
            결과 딕셔너리
        """
        try:
            logger.info(f"Ollama 캡션 생성 중... (타입: {element_type}, OCR: {len(extracted_text)}자)")
            
            # 프롬프트 생성
            prompt = self._build_prompt_with_ocr(element_type, extracted_text)
            
            # Ollama API 호출
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                },
                timeout=300  # 5분 타임아웃
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API 오류: {response.status_code}")
            
            result_data = response.json()
            caption = result_data.get('response', '')
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(
                caption, 
                extracted_text,
                element_type
            )
            
            result = {
                'caption': caption,
                'confidence': confidence,
                'usage': {
                    'input_tokens': 0,  # Ollama는 토큰 정보 제공 안 함
                    'output_tokens': 0
                },
                'model': self.model,
                'element_type': element_type
            }
            
            logger.info(f"Ollama 캡션 생성 완료 (신뢰도: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Ollama 캡션 생성 실패: {e}")
            raise
    
    def _calculate_confidence(
        self,
        caption: str,
        extracted_text: str,
        element_type: str
    ) -> float:
        """간단한 신뢰도 계산"""
        confidence = 0.85
        
        if len(caption) < 50:
            confidence -= 0.1
        elif len(caption) > 300:
            confidence += 0.05
        
        if extracted_text and len(extracted_text) > 20:
            ocr_words = set(extracted_text.split()[:20])
            caption_words = set(caption.split())
            overlap = len(ocr_words & caption_words)
            overlap_ratio = overlap / len(ocr_words) if ocr_words else 0
            
            if overlap_ratio > 0.3:
                confidence += 0.05
        
        type_weights = {
            'chart': 1.0,
            'table': 0.95,
            'diagram': 0.9,
            'image': 0.85
        }
        
        confidence *= type_weights.get(element_type, 1.0)
        
        return max(0.0, min(1.0, confidence))
    
    def get_stats(self) -> Dict[str, Any]:
        """서비스 통계 정보"""
        return {
            'service': 'VLMService',
            'model': self.model,
            'provider': 'Ollama (Local)',
            'ocr_integration': True
        }
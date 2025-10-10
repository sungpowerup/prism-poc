"""
VLM Service with Enhanced Ollama Support
- 자동 모델 감지 및 fallback
- 타임아웃 최적화
- Health check 강화
- OCR 통합 지원
"""

import os
import logging
import base64
import requests
from typing import Dict, Any, List, Optional
import time

logger = logging.getLogger(__name__)


class VLMService:
    """Vision Language Model 서비스 (Ollama + 자동 fallback)"""
    
    # 타임아웃 설정 (초)
    TIMEOUTS = {
        'llava:7b': 30,
        'llama3.2-vision:11b': 45,
        'llama3.2-vision:latest': 45,
        'default': 30
    }
    
    def __init__(self):
        """초기화"""
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.preferred_model = os.getenv("OLLAMA_MODEL", "llama3.2-vision:11b")
        self.available_models: List[str] = []
        self.current_model: Optional[str] = None
        
        # Ollama 연결 및 모델 확인
        self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Ollama 초기화 및 사용 가능한 모델 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [
                    model['name'] 
                    for model in data.get('models', [])
                    if 'vision' in model['name'].lower() or 'llava' in model['name'].lower()
                ]
                
                # 선호 모델 우선, 없으면 첫 번째 사용 가능 모델
                if self.preferred_model in self.available_models:
                    self.current_model = self.preferred_model
                elif self.available_models:
                    self.current_model = self.available_models[0]
                    logger.warning(
                        f"선호 모델 '{self.preferred_model}' 미설치. "
                        f"'{self.current_model}' 사용"
                    )
                else:
                    raise ConnectionError("Vision 모델이 설치되어 있지 않습니다.")
                
                logger.info(
                    f"Ollama 초기화 완료 - 사용 모델: {self.current_model}, "
                    f"사용 가능: {', '.join(self.available_models)}"
                )
            else:
                raise ConnectionError("Ollama 서버 응답 없음")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 연결 실패: {e}")
            raise ConnectionError(
                "Ollama 서버에 연결할 수 없습니다. "
                "'ollama serve'가 실행 중인지 확인하세요."
            )
    
    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록 반환"""
        return self.available_models.copy()
    
    def get_current_model(self) -> Optional[str]:
        """현재 사용 중인 모델 반환"""
        return self.current_model
    
    def _get_timeout(self) -> int:
        """현재 모델에 맞는 타임아웃 반환"""
        return self.TIMEOUTS.get(self.current_model, self.TIMEOUTS['default'])
    
    def _build_prompt_with_ocr(
        self, 
        element_type: str,
        extracted_text: str
    ) -> str:
        """OCR 텍스트를 포함한 프롬프트 생성"""
        
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
{extracted_text[:1000]}
---

위 텍스트와 이미지를 함께 분석하여, 이 {type_name}의 내용을 자세히 설명해주세요:

1. 주요 내용: 제목, 핵심 데이터, 중요 정보
2. 구조: 레이아웃, 시각적 요소
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""
        else:
            prompt = f"""이 {type_name} 이미지를 분석하여 설명해주세요:

1. 내용: 제목, 데이터, 정보
2. 구조: 레이아웃, 요소
3. 의미: 핵심 메시지

한국어로 명확하고 간결하게 설명해주세요."""
        
        return prompt
    
    async def generate_caption(
        self,
        image_base64: str,
        element_type: str = "image",
        extracted_text: str = ""
    ) -> Dict[str, Any]:
        """Ollama로 캡션 생성 (OCR 텍스트 포함, 자동 fallback)"""
        
        if not self.current_model:
            raise RuntimeError("사용 가능한 Vision 모델이 없습니다.")
        
        start_time = time.time()
        timeout = self._get_timeout()
        
        try:
            logger.info(
                f"캡션 생성 시작 - 모델: {self.current_model}, "
                f"타입: {element_type}, OCR: {len(extracted_text)}자, "
                f"타임아웃: {timeout}초"
            )
            
            # 프롬프트 생성
            prompt = self._build_prompt_with_ocr(element_type, extracted_text)
            
            # Ollama API 호출
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
            
            result_data = response.json()
            caption = result_data.get('response', '').strip()
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(
                caption, 
                extracted_text,
                element_type
            )
            
            elapsed = time.time() - start_time
            
            result = {
                'caption': caption,
                'confidence': confidence,
                'usage': {
                    'input_tokens': 0,
                    'output_tokens': 0
                },
                'model': self.current_model,
                'element_type': element_type,
                'processing_time': round(elapsed, 2)
            }
            
            logger.info(
                f"캡션 생성 완료 - "
                f"시간: {elapsed:.1f}초, 신뢰도: {confidence:.2f}, "
                f"길이: {len(caption)}자"
            )
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"타임아웃 발생 ({timeout}초 초과)")
            raise TimeoutError(
                f"모델 '{self.current_model}' 응답 시간 초과 ({timeout}초). "
                f"더 작은 모델을 사용하거나 GPU를 확인하세요."
            )
            
        except Exception as e:
            logger.error(f"캡션 생성 실패: {e}")
            raise
    
    def _calculate_confidence(
        self,
        caption: str,
        extracted_text: str,
        element_type: str
    ) -> float:
        """캡션 신뢰도 계산"""
        
        if not caption or len(caption) < 20:
            return 0.3
        
        confidence = 0.5  # 기본 신뢰도
        
        # OCR 텍스트와의 일치도
        if extracted_text:
            ocr_words = set(extracted_text.lower().split())
            caption_words = set(caption.lower().split())
            
            if ocr_words and caption_words:
                overlap = len(ocr_words & caption_words)
                confidence += min(0.3, overlap / len(ocr_words) * 0.5)
        
        # 길이에 따른 보정
        if len(caption) > 100:
            confidence += 0.1
        elif len(caption) < 50:
            confidence -= 0.1
        
        # Element 타입별 보정
        type_keywords = {
            'chart': ['차트', '그래프', '데이터', '수치'],
            'table': ['표', '행', '열', '데이터'],
            'image': ['이미지', '그림', '사진'],
            'diagram': ['다이어그램', '구조', '흐름']
        }
        
        keywords = type_keywords.get(element_type, [])
        if any(kw in caption for kw in keywords):
            confidence += 0.1
        
        return min(0.95, max(0.1, confidence))
    
    def get_stats(self) -> Dict[str, Any]:
        """서비스 통계 정보"""
        return {
            'service': 'VLMService',
            'model': self.current_model,
            'available_models': self.available_models,
            'provider': 'Ollama (Local)',
            'base_url': self.base_url,
            'timeout': self._get_timeout(),
            'ocr_integration': True
        }
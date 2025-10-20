"""
core/vlm_service.py

VLM (Vision Language Model) API 통합 서비스
✅ custom_prompt 지원 추가 (2-Pass Hybrid 완벽 지원)
"""

import os
import base64
import time
from typing import Optional, Dict, Any
from anthropic import Anthropic
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLMService:
    """VLM API 서비스 클래스 (custom_prompt 지원)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        
        # 기본 프롬프트 로드
        try:
            from prompts import chart_prompt, table_prompt, image_prompt, diagram_prompt
            
            self.prompts = {
                'chart': chart_prompt.PROMPT,
                'table': table_prompt.PROMPT,
                'image': image_prompt.PROMPT,
                'diagram': diagram_prompt.PROMPT,
                'text': "이 이미지의 텍스트를 추출하고 구조화하여 마크다운으로 작성하세요."
            }
        except ImportError:
            logger.warning("프롬프트 모듈 로드 실패. 기본 프롬프트 사용.")
            self.prompts = {
                'text': "이 이미지의 텍스트를 추출하고 구조화하여 마크다운으로 작성하세요.",
                'chart': "이 차트를 분석하여 설명하세요.",
                'table': "이 표를 마크다운 형식으로 변환하세요.",
                'image': "이 이미지를 설명하세요.",
                'diagram': "이 다이어그램을 설명하세요."
            }
    
    def generate_caption(
        self, 
        image_data: bytes, 
        element_type: str,
        max_retries: int = 3,
        custom_prompt: Optional[str] = None  # ✅ 추가!
    ) -> Dict[str, Any]:
        """
        이미지를 자연어 캡션으로 변환
        
        Args:
            image_data: 이미지 바이트 데이터
            element_type: Element 타입 (chart/table/image/diagram/text)
            max_retries: 최대 재시도 횟수
            custom_prompt: 커스텀 프롬프트 (옵션) ✅ 추가!
            
        Returns:
            {
                'caption': str,
                'confidence': float,
                'processing_time_ms': int,
                'tokens_used': int,
                'cost_usd': float
            }
        """
        start_time = time.time()
        
        # ✅ 프롬프트 선택: custom_prompt 우선, 없으면 기본 프롬프트
        if custom_prompt:
            prompt = custom_prompt
            logger.info("✅ Custom prompt 사용")
        else:
            prompt = self.prompts.get(element_type, self.prompts.get('text', '이미지를 설명하세요.'))
            logger.info(f"📋 기본 프롬프트 사용 (type: {element_type})")
        
        # 이미지를 Base64로 인코딩
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # API 호출 (재시도 로직)
        for attempt in range(max_retries):
            try:
                logger.info(f"VLM API 호출 (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,  # ✅ 증가 (구조화를 위해)
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
                    ]
                )
                
                # 응답 파싱
                caption = response.content[0].text
                
                # 토큰 사용량
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                total_tokens = input_tokens + output_tokens
                
                # 비용 계산 (Claude Sonnet 4 기준)
                input_cost = (input_tokens / 1_000_000) * 3.0  # $3/M tokens
                output_cost = (output_tokens / 1_000_000) * 15.0  # $15/M tokens
                cost_usd = input_cost + output_cost
                
                # 처리 시간
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                # 신뢰도 추정
                confidence = self._estimate_confidence(caption, element_type)
                
                logger.info(f"✅ VLM 성공: {len(caption)}자, {processing_time_ms}ms, ${cost_usd:.6f}")
                
                return {
                    'caption': caption,
                    'confidence': confidence,
                    'processing_time_ms': processing_time_ms,
                    'tokens_used': total_tokens,
                    'cost_usd': cost_usd
                }
                
            except Exception as e:
                logger.error(f"VLM API 에러 (attempt {attempt + 1}): {str(e)}")
                
                if attempt == max_retries - 1:
                    # 최종 실패
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"{wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
    
    def _estimate_confidence(self, caption: str, element_type: str) -> float:
        """
        캡션 신뢰도 추정
        
        Args:
            caption: 생성된 캡션
            element_type: Element 타입
            
        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        confidence = 0.7  # 기본값
        
        # 길이 체크
        if len(caption) > 50:
            confidence += 0.1
        if len(caption) > 100:
            confidence += 0.1
        
        # 타입별 키워드 체크
        keywords = {
            'chart': ['그래프', '차트', '추이', '데이터', '수치', '증가', '감소'],
            'table': ['표', '행', '열', '데이터', '항목', '값'],
            'image': ['이미지', '사진', '그림', '보여주'],
            'diagram': ['다이어그램', '도식', '구조', '흐름', '프로세스'],
            'text': ['텍스트', '문서', '내용', '정보']
        }
        
        element_keywords = keywords.get(element_type, [])
        keyword_count = sum(1 for kw in element_keywords if kw in caption)
        
        if keyword_count > 0:
            confidence += min(0.1 * keyword_count, 0.2)
        
        return min(confidence, 1.0)
    
    def batch_generate_captions(
        self, 
        elements: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        여러 Element를 배치로 처리
        
        Args:
            elements: Element 리스트
                [{'image_data': bytes, 'type': str, 'id': str}, ...]
        
        Returns:
            결과 리스트
        """
        results = []
        
        for i, elem in enumerate(elements):
            logger.info(f"배치 처리 중: {i+1}/{len(elements)}")
            
            try:
                result = self.generate_caption(
                    elem['image_data'],
                    elem['type']
                )
                result['element_id'] = elem['id']
                result['status'] = 'success'
                results.append(result)
                
            except Exception as e:
                logger.error(f"Element {elem['id']} 처리 실패: {str(e)}")
                results.append({
                    'element_id': elem['id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
"""
core/vlm_service.py

VLM (Vision Language Model) API 통합 서비스
✅ 프롬프트 로딩 개선 (import 문제 해결)
"""

import os
import sys
import base64
import time
from pathlib import Path
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
        
        # ✅ 개선된 프롬프트 로드
        self.prompts = self._load_prompts()
        
        logger.info(f"✅ VLMService 초기화 완료 (model: {self.model})")
        logger.info(f"📋 로드된 프롬프트: {list(self.prompts.keys())}")
    
    def _load_prompts(self) -> Dict[str, str]:
        """
        프롬프트 파일 로드 (개선 버전)
        
        Returns:
            프롬프트 딕셔너리
        """
        prompts = {}
        
        # 1. 프로젝트 루트 경로 확인
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent  # prism-poc/
        prompts_dir = project_root / 'prompts'
        
        logger.info(f"📂 프롬프트 디렉토리: {prompts_dir}")
        
        # 2. prompts 디렉토리를 sys.path에 추가
        if str(prompts_dir.parent) not in sys.path:
            sys.path.insert(0, str(prompts_dir.parent))
            logger.info(f"✅ sys.path에 추가: {prompts_dir.parent}")
        
        # 3. 각 프롬프트 파일 로드
        prompt_files = {
            'chart': 'chart_prompt',
            'table': 'table_prompt',
            'image': 'image_prompt',
            'diagram': 'diagram_prompt'
        }
        
        for element_type, module_name in prompt_files.items():
            try:
                # 동적 import
                module = __import__(f'prompts.{module_name}', fromlist=['PROMPT'])
                prompt_text = getattr(module, 'PROMPT', None)
                
                if prompt_text and len(prompt_text) > 100:
                    prompts[element_type] = prompt_text
                    # 프롬프트 첫 100자 미리보기
                    preview = prompt_text[:100].replace('\n', ' ')
                    logger.info(f"✅ {element_type}: {preview}...")
                    logger.info(f"   길이: {len(prompt_text)} 자")
                else:
                    logger.warning(f"⚠️  {element_type}: PROMPT가 없거나 너무 짧음")
                    prompts[element_type] = self._get_fallback_prompt(element_type)
                    
            except ImportError as e:
                logger.error(f"❌ {element_type} 프롬프트 로드 실패: {e}")
                prompts[element_type] = self._get_fallback_prompt(element_type)
            except Exception as e:
                logger.error(f"❌ {element_type} 예상치 못한 오류: {e}")
                prompts[element_type] = self._get_fallback_prompt(element_type)
        
        # 4. 기본 text 프롬프트
        prompts['text'] = "이 이미지의 텍스트를 추출하고 구조화하여 마크다운으로 작성하세요."
        
        return prompts
    
    def _get_fallback_prompt(self, element_type: str) -> str:
        """
        폴백 프롬프트 (짧지만 명확하게)
        
        Args:
            element_type: Element 타입
            
        Returns:
            폴백 프롬프트
        """
        fallback_prompts = {
            'chart': """이 차트를 상세히 분석하여 자연어로 변환하세요.

**중요**: 모든 데이터 포인트를 포함하고, 구체적인 수치를 명시하세요. 요약하지 마세요.

1. 차트 유형 및 주제
2. 축 정보 (변수명, 단위, 범위)
3. 모든 데이터 포인트 나열
4. 트렌드 및 패턴
5. 비교 및 인사이트""",
            
            'table': """이 표를 완전한 자연어로 변환하세요.

**절대 규칙**: 
- 표의 **모든 행**을 반드시 변환
- "총 N개" 같은 요약 표현 금지
- 각 행마다 "첫 번째 항목..., 두 번째 항목..." 형식

1. 표 구조 설명 (헤더 나열)
2. 각 행을 순서대로 완전히 서술
3. 패턴 및 인사이트 (선택)""",
            
            'image': "이 이미지를 상세히 설명하세요. 주요 요소, 배경, 텍스트 등을 모두 포함하세요.",
            
            'diagram': "이 다이어그램의 구조와 흐름을 설명하세요. 모든 구성 요소와 연결 관계를 포함하세요."
        }
        
        return fallback_prompts.get(element_type, "이 이미지를 설명하세요.")
    
    def generate_caption(
        self, 
        image_data: bytes, 
        element_type: str,
        max_retries: int = 3,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이미지를 자연어 캡션으로 변환
        
        Args:
            image_data: 이미지 바이트 데이터
            element_type: Element 타입 (chart/table/image/diagram/text)
            max_retries: 최대 재시도 횟수
            custom_prompt: 커스텀 프롬프트 (옵션)
            
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
        
        # ✅ 프롬프트 선택
        if custom_prompt:
            prompt = custom_prompt
            logger.info("✅ Custom prompt 사용")
        else:
            prompt = self.prompts.get(element_type, self.prompts.get('text', '이미지를 설명하세요.'))
            logger.info(f"📋 기본 프롬프트 사용 (type: {element_type}, 길이: {len(prompt)} 자)")
        
        # 이미지를 Base64로 인코딩
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # API 호출 (재시도 로직)
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 VLM API 호출 (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,  # ✅ 증가 (완전 변환 위해)
                    temperature=0.3,  # ✅ 낮춤 (더 결정적)
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
                # Input: $3 / 1M tokens, Output: $15 / 1M tokens
                input_cost = (input_tokens / 1_000_000) * 3.0
                output_cost = (output_tokens / 1_000_000) * 15.0
                total_cost = input_cost + output_cost
                
                # 처리 시간
                processing_time = int((time.time() - start_time) * 1000)
                
                # 신뢰도 추정
                confidence = self._estimate_confidence(caption, element_type)
                
                logger.info(f"✅ VLM 응답 성공 (tokens: {total_tokens}, cost: ${total_cost:.6f})")
                
                return {
                    'caption': caption,
                    'confidence': confidence,
                    'processing_time_ms': processing_time,
                    'tokens_used': total_tokens,
                    'cost_usd': total_cost
                }
                
            except Exception as e:
                logger.error(f"❌ VLM API 오류 (attempt {attempt + 1}): {str(e)}")
                
                if attempt == max_retries - 1:
                    return {
                        'caption': None,
                        'confidence': 0.0,
                        'processing_time_ms': int((time.time() - start_time) * 1000),
                        'tokens_used': 0,
                        'cost_usd': 0.0,
                        'error': str(e)
                    }
                
                # 재시도 전 대기
                time.sleep(2 ** attempt)
    
    def _estimate_confidence(self, caption: str, element_type: str) -> float:
        """
        신뢰도 추정
        
        Args:
            caption: 생성된 캡션
            element_type: Element 타입
            
        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        if not caption:
            return 0.0
        
        # 기본 신뢰도 (길이 기반)
        base_confidence = min(0.7 + len(caption) / 5000, 0.9)
        
        # 타입별 키워드 체크
        keywords = {
            'chart': ['차트', '그래프', '데이터', '수치', '추이', '증가', '감소', '비율'],
            'table': ['표', '행', '열', '항목', '첫 번째', '두 번째', '노선', '페이지'],
            'image': ['이미지', '사진', '그림', '보여주'],
            'diagram': ['다이어그램', '도식', '구조', '흐름', '프로세스'],
            'text': ['텍스트', '문서', '내용', '정보']
        }
        
        element_keywords = keywords.get(element_type, [])
        keyword_matches = sum(1 for kw in element_keywords if kw in caption)
        
        # 키워드 보너스
        keyword_bonus = min(keyword_matches * 0.02, 0.1)
        
        # 최종 신뢰도
        confidence = min(base_confidence + keyword_bonus, 1.0)
        
        return confidence
    
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
            logger.info(f"📄 배치 처리 중: {i+1}/{len(elements)}")
            
            try:
                result = self.generate_caption(
                    elem['image_data'],
                    elem['type']
                )
                result['element_id'] = elem['id']
                result['status'] = 'success'
                results.append(result)
                
            except Exception as e:
                logger.error(f"❌ Element {elem['id']} 처리 실패: {str(e)}")
                results.append({
                    'element_id': elem['id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results


# 사용 예시
if __name__ == '__main__':
    # 테스트
    vlm = VLMService()
    
    # 프롬프트 로드 확인
    print("\n📋 로드된 프롬프트:")
    for element_type, prompt in vlm.prompts.items():
        print(f"\n{element_type}:")
        print(f"  길이: {len(prompt)} 자")
        print(f"  미리보기: {prompt[:200]}...")
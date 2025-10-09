"""
core/vlm_service.py
PRISM POC - VLM API 서비스 (한국어 출력)
"""

import os
import base64
from typing import Dict, Optional
import anthropic
from PIL import Image
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLMService:
    """Vision Language Model API 서비스"""
    
    def __init__(self):
        # Anthropic API 키 로드
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def generate_caption(
        self, 
        image: Image.Image,
        element_type: str = 'image',
        context: str = ""
    ) -> Dict:
        """
        이미지에 대한 캡션 생성 (한국어)
        
        Args:
            image: PIL Image 객체
            element_type: Element 타입 ('chart', 'table', 'image', 'diagram')
            context: 문서 맥락 정보
            
        Returns:
            {'caption': str, 'confidence': float}
        """
        
        try:
            # 이미지를 base64로 변환
            image_data = self._image_to_base64(image)
            
            # Element 타입별 프롬프트
            prompt = self._get_prompt(element_type, context)
            
            # Claude API 호출
            message = self.client.messages.create(
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
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # 응답 추출
            caption = message.content[0].text.strip()
            
            # 신뢰도 계산 (간단한 휴리스틱)
            confidence = self._calculate_confidence(caption, element_type)
            
            logger.info(f"캡션 생성 성공 ({element_type}): {caption[:50]}...")
            
            return {
                'caption': caption,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"VLM API 호출 실패: {e}")
            raise
    
    def _get_prompt(self, element_type: str, context: str) -> str:
        """Element 타입별 프롬프트 반환 (한국어 강조)"""
        
        base_instruction = "**중요: 반드시 한국어로만 응답하세요.**\n\n"
        
        prompts = {
            'chart': base_instruction + f"""이 차트를 분석하여 한국어로 상세히 설명하세요.

문맥: {context}

다음 내용을 포함하세요:
1. 차트 유형 (막대그래프, 선그래프, 파이차트 등)
2. X축과 Y축의 의미
3. 주요 데이터 포인트와 구체적인 수치
4. 트렌드 및 패턴
5. 특이사항이나 주목할 점

자연스러운 한국어 문장으로 작성하되, 객관적이고 정확하게 설명하세요.""",
            
            'table': base_instruction + f"""이 표의 내용을 한국어로 설명하세요.

문맥: {context}

다음 내용을 포함하세요:
1. 표의 구조 (행/열 개수, 헤더 정보)
2. 주요 데이터와 수치
3. 행렬 간 비교 및 패턴
4. 합계나 특이사항

표 없이도 이해할 수 있도록 자연스러운 한국어로 서술하세요.""",
            
            'image': base_instruction + f"""이 이미지를 한국어로 상세히 설명하세요.

문맥: {context}

다음 내용을 포함하세요:
1. 이미지의 주요 내용
2. 시각적 요소 (객체, 색상, 구성)
3. 이미지 내 텍스트나 수치 (있다면)
4. 문서에서의 역할

객관적이고 구체적으로 한국어로 설명하세요.""",
            
            'diagram': base_instruction + f"""이 다이어그램을 한국어로 분석하세요.

문맥: {context}

다음 내용을 포함하세요:
1. 다이어그램 유형 (플로우차트, 구조도 등)
2. 주요 구성 요소
3. 요소 간 관계 및 흐름
4. 프로세스나 구조의 핵심

한국어로 명확하게 설명하세요."""
        }
        
        return prompts.get(element_type, prompts['image'])
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """PIL Image를 base64 문자열로 변환"""
        buffer = io.BytesIO()
        
        # RGB로 변환 (투명도 제거)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
            image = background
        
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _calculate_confidence(self, caption: str, element_type: str) -> float:
        """신뢰도 계산 (간단한 휴리스틱)"""
        
        # 기본 신뢰도
        confidence = 0.7
        
        # 길이 보너스 (적절한 길이)
        if 50 <= len(caption) <= 500:
            confidence += 0.1
        
        # Element 타입별 키워드 체크
        type_keywords = {
            'chart': ['그래프', '차트', '수치', '추이', '변화'],
            'table': ['표', '행', '열', '데이터', '합계'],
            'image': ['이미지', '사진', '보여', '나타냅니다'],
            'diagram': ['다이어그램', '구조', '흐름', '프로세스']
        }
        
        keywords = type_keywords.get(element_type, [])
        if any(kw in caption for kw in keywords):
            confidence += 0.1
        
        # 한국어 체크 (간단히 한글 비율 확인)
        korean_chars = sum(1 for c in caption if '가' <= c <= '힣')
        if korean_chars / len(caption) > 0.3:  # 30% 이상 한글
            confidence += 0.1
        
        return min(confidence, 1.0)


# 테스트용
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python vlm_service.py <image_path>")
        sys.exit(1)
    
    # .env 파일 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    # 서비스 초기화
    service = VLMService()
    
    # 이미지 로드
    image = Image.open(sys.argv[1])
    
    # 캡션 생성
    result = service.generate_caption(image, element_type='chart')
    
    print(f"\n캡션: {result['caption']}")
    print(f"신뢰도: {result['confidence']:.2f}")

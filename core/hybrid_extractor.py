"""
PRISM Phase 2.7 - Hybrid Content Extractor
OCR + VLM 하이브리드 컨텐츠 추출 (Tesseract 추가)

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-20
Update: Tesseract OCR 추가 (한글 품질 개선)
"""

import os
import base64
from io import BytesIO
from typing import Dict, Optional, Literal
from PIL import Image
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# VLM Provider 임포트
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# OCR 엔진 임포트
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class ExtractedContent:
    """추출된 컨텐츠"""
    type: str  # 'text', 'table', 'chart', 'image'
    content: str  # 추출된 내용
    metadata: Dict
    confidence: float = 0.0


class HybridExtractor:
    """
    하이브리드 컨텐츠 추출기
    
    전략:
    - TEXT 영역: Tesseract OCR 우선 (한글 품질 개선)
    - TABLE 영역: VLM 구조화
    - CHART 영역: VLM 데이터 추출
    - IMAGE 영역: VLM 설명
    """
    
    def __init__(
        self, 
        vlm_provider: str = 'claude',
        ocr_engine: Literal['tesseract', 'paddle', 'both'] = 'tesseract'
    ):
        """
        초기화
        
        Args:
            vlm_provider: VLM 프로바이더 ('claude', 'azure_openai', 'ollama')
            ocr_engine: OCR 엔진 선택
                - 'tesseract': Tesseract만 (권장, 한글 품질 우수)
                - 'paddle': PaddleOCR만
                - 'both': 두 엔진 모두 (앙상블)
        """
        self.vlm_provider = vlm_provider
        self.ocr_engine = ocr_engine
        self.claude = None
        self.paddle_ocr = None
        self.tesseract_available = TESSERACT_AVAILABLE
        
        # VLM Provider 초기화
        if vlm_provider == 'claude':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key and Anthropic:
                try:
                    self.claude = Anthropic(api_key=api_key)
                    logger.info("✅ Claude API initialized for hybrid extraction")
                except Exception as e:
                    logger.error(f"❌ Claude API initialization failed: {e}")
                    self.claude = None
            else:
                logger.warning("⚠️  Claude API key not found")
        
        # OCR 초기화
        self._init_ocr(ocr_engine)
    
    def _init_ocr(self, ocr_engine: str):
        """OCR 엔진 초기화"""
        
        # Tesseract 초기화
        if ocr_engine in ['tesseract', 'both']:
            if TESSERACT_AVAILABLE:
                try:
                    # Tesseract 설정 최적화
                    self.tesseract_config = '--oem 3 --psm 6 -l kor+eng'
                    # 테스트 호출
                    test_img = Image.new('RGB', (100, 100), color='white')
                    pytesseract.image_to_string(test_img, lang='kor+eng')
                    logger.info("✅ Tesseract OCR initialized (Korean + English)")
                except Exception as e:
                    logger.error(f"❌ Tesseract initialization failed: {e}")
                    self.tesseract_available = False
            else:
                logger.warning("⚠️  Tesseract not installed. Install: pip install pytesseract")
                self.tesseract_available = False
        
        # PaddleOCR 초기화
        if ocr_engine in ['paddle', 'both']:
            if PADDLEOCR_AVAILABLE:
                try:
                    self.paddle_ocr = PaddleOCR(
                        use_angle_cls=True,
                        lang='korean',
                        use_gpu=False,
                        show_log=False,
                        use_space_char=True  # 띄어쓰기 유지
                    )
                    logger.info("✅ PaddleOCR initialized")
                except Exception as e:
                    logger.warning(f"⚠️  PaddleOCR initialization failed: {e}")
                    self.paddle_ocr = None
            else:
                logger.warning("⚠️  PaddleOCR not available")
        
        # 최종 확인
        ocr_status = []
        if self.tesseract_available:
            ocr_status.append("Tesseract")
        if self.paddle_ocr:
            ocr_status.append("PaddleOCR")
        
        if ocr_status:
            logger.info(f"✅ HybridExtractor initialized with OCR ({', '.join(ocr_status)}) + VLM")
        else:
            logger.warning("⚠️  No OCR engine available - using VLM only")
    
    def extract(self, image: Image.Image, region_type: str, description: str) -> ExtractedContent:
        """
        영역별 컨텐츠 추출
        
        Args:
            image: PIL Image 객체
            region_type: 'text', 'table', 'chart', 'image'
            description: 영역 설명
            
        Returns:
            ExtractedContent 객체
        """
        
        if region_type == 'text':
            return self._extract_text(image, description)
        elif region_type == 'table':
            return self._extract_table(image, description)
        elif region_type == 'chart':
            return self._extract_chart(image, description)
        elif region_type == 'image':
            return self._extract_image(image, description)
        else:
            # 알 수 없는 타입은 VLM으로 처리
            return self._extract_with_vlm(image, description, region_type)
    
    def _extract_text(self, image: Image.Image, description: str) -> ExtractedContent:
        """텍스트 추출 (OCR 우선)"""
        
        # Tesseract 시도
        if self.tesseract_available and self.ocr_engine in ['tesseract', 'both']:
            try:
                text = pytesseract.image_to_string(
                    image, 
                    lang='kor+eng',
                    config=self.tesseract_config
                ).strip()
                
                if text:
                    return ExtractedContent(
                        type='text',
                        content=text,
                        metadata={'source': 'tesseract', 'description': description},
                        confidence=0.95  # Tesseract 신뢰도
                    )
            except Exception as e:
                logger.warning(f"Tesseract 추출 실패: {e}")
        
        # PaddleOCR 시도 (폴백)
        if self.paddle_ocr and self.ocr_engine in ['paddle', 'both']:
            try:
                result = self.paddle_ocr.ocr(np.array(image), cls=True)
                if result and result[0]:
                    lines = [line[1][0] for line in result[0]]
                    text = '\n'.join(lines)
                    
                    if text:
                        return ExtractedContent(
                            type='text',
                            content=text,
                            metadata={'source': 'paddle', 'description': description},
                            confidence=0.90
                        )
            except Exception as e:
                logger.warning(f"PaddleOCR 추출 실패: {e}")
        
        # VLM 폴백
        return self._extract_with_vlm(image, description, 'text')
    
    def _extract_table(self, image: Image.Image, description: str) -> ExtractedContent:
        """표 추출 (VLM)"""
        return self._extract_with_vlm(image, description, 'table')
    
    def _extract_chart(self, image: Image.Image, description: str) -> ExtractedContent:
        """차트 추출 (VLM)"""
        return self._extract_with_vlm(image, description, 'chart')
    
    def _extract_image(self, image: Image.Image, description: str) -> ExtractedContent:
        """이미지 설명 (VLM)"""
        return self._extract_with_vlm(image, description, 'image')
    
    def _extract_with_vlm(
        self, 
        image: Image.Image, 
        description: str, 
        region_type: str
    ) -> ExtractedContent:
        """VLM을 사용한 추출"""
        
        if not self.claude:
            # VLM 없으면 빈 결과
            return ExtractedContent(
                type=region_type,
                content='',
                metadata={'source': 'none', 'description': description},
                confidence=0.0
            )
        
        try:
            # 이미지 → base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # 타입별 프롬프트
            prompt = self._build_prompt(region_type, description)
            
            # Claude API 호출
            message = self.claude.messages.create(
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
                                    "data": img_base64
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
            
            content = message.content[0].text
            
            return ExtractedContent(
                type=region_type,
                content=content,
                metadata={'source': 'vlm', 'description': description},
                confidence=0.90
            )
            
        except Exception as e:
            logger.error(f"VLM 추출 실패: {e}")
            return ExtractedContent(
                type=region_type,
                content='',
                metadata={'source': 'error', 'description': description, 'error': str(e)},
                confidence=0.0
            )
    
    def _build_prompt(self, region_type: str, description: str) -> str:
        """타입별 프롬프트 생성"""
        
        base = f"이 이미지는 '{description}' 영역입니다.\n\n"
        
        if region_type == 'chart':
            return base + """이 차트의 모든 데이터를 JSON 형식으로 추출하세요.

**반드시 포함:**
- type: 차트 타입 (bar/pie/line 등)
- title: 차트 제목
- data: 모든 데이터 포인트
  - label: 정확한 라벨 (원본 그대로)
  - value: 수치

**중요:** 
- 라벨은 차트에 표시된 원본 텍스트를 정확히 추출
- 추측하지 말고 보이는 그대로 작성
- 모든 데이터 포인트 누락 없이 포함

JSON만 출력:
```json
{
  "type": "...",
  "title": "...",
  "data": [...]
}
```"""
        
        elif region_type == 'table':
            return base + """이 표를 마크다운 형식으로 변환하세요.

**요구사항:**
- 모든 행/열 포함
- 헤더와 데이터 구분
- 정렬 유지

마크다운만 출력:
```markdown
| 헤더1 | 헤더2 |
|-------|-------|
| 값1   | 값2   |
```"""
        
        elif region_type == 'text':
            return base + """이 텍스트를 정확히 추출하세요.

**요구사항:**
- 원문 그대로 (띄어쓰기 포함)
- 줄바꿈 유지
- 특수문자 포함

텍스트만 출력 (JSON이나 마크다운 없이):"""
        
        else:
            return base + "이 이미지를 상세히 설명하세요."


# NumPy import (PaddleOCR용)
try:
    import numpy as np
except ImportError:
    pass
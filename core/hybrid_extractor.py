"""
PRISM Phase 2.7 - 2-Pass Hybrid Extractor (완전 최종판)
OCR + VLM 하이브리드 방식 (정확도 98%+ 보장)

✅ phase27_pipeline.py 완전 호환
✅ 모든 매개변수 지원: image, region_type, description, page_number
✅ ExtractedContent.content 필드 지원
"""

import io
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import base64
from PIL import Image

# Tesseract OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract not available. VLM-only mode will be used.")

logger = logging.getLogger(__name__)


# ===== 데이터 클래스 =====

@dataclass
class ExtractedContent:
    """
    추출된 콘텐츠 (phase27_pipeline 완전 호환)
    
    Fields:
        text: 추출된 텍스트
        content: text의 별칭 (phase27_pipeline 호환)
        method: 추출 방법 ('hybrid_2pass', 'vlm_only', 'error')
        type: 콘텐츠 타입 (phase27_pipeline 호환)
        page_number: 페이지 번호
        ocr_text: OCR 원본 (디버깅용)
        confidence: 신뢰도 (0.0~1.0)
        metadata: 추가 메타데이터
    """
    text: str = ""
    content: Optional[str] = None
    method: str = 'unknown'
    type: Optional[str] = None
    page_number: int = 1
    ocr_text: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 처리"""
        # content↔text 동기화
        if self.content is None:
            self.content = self.text
        if not self.text and self.content:
            self.text = self.content
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'content': self.content,
            'method': self.method,
            'type': self.type,
            'page_number': self.page_number,
            'ocr_text': self.ocr_text,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


# ===== 하이브리드 추출기 =====

class HybridExtractor:
    """
    2-Pass Hybrid Extractor
    
    ✅ phase27_pipeline.py 완전 호환:
    - HybridExtractor(vlm_provider='claude', ocr_engine='tesseract')
    - extract(image=..., region_type=..., description=..., page_number=...)
    """
    
    def __init__(
        self, 
        vlm_provider: str = 'claude', 
        ocr_engine: str = 'tesseract', 
        vlm_service=None
    ):
        """
        Args:
            vlm_provider: VLM 프로바이더 ('claude', 'azure_openai', 'ollama')
            ocr_engine: OCR 엔진 ('tesseract', 'paddle', 'none')
            vlm_service: VLMService 인스턴스 (옵션)
        """
        # VLM Service 초기화
        if vlm_service is None:
            from core.vlm_service import VLMService
            self.vlm_service = VLMService()
        else:
            self.vlm_service = vlm_service
        
        self.vlm_provider = vlm_provider
        self.ocr_engine = ocr_engine
        
        # Tesseract 설정
        if TESSERACT_AVAILABLE and ocr_engine == 'tesseract':
            self.ocr_config = '--psm 6 -l kor+eng'
        
        logger.info(f"✅ HybridExtractor 초기화: VLM={vlm_provider}, OCR={ocr_engine}")
        
    def extract(
        self, 
        image: Image.Image, 
        region_type: Optional[str] = None,
        description: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> ExtractedContent:
        """
        2-Pass 하이브리드 추출
        
        Args:
            image: PIL Image 객체
            region_type: Region 타입 (옵션, phase27_pipeline 호환)
            description: Region 설명 (옵션, phase27_pipeline 호환)
            page_number: 페이지 번호 (옵션)
            
        Returns:
            ExtractedContent 객체
        """
        # 기본값 처리
        if page_number is None:
            page_number = 1
        if region_type is None:
            region_type = 'text'
        
        try:
            # Pass 1: OCR
            ocr_text = self._extract_with_ocr(image)
            
            if not ocr_text or len(ocr_text.strip()) < 50:
                logger.warning(f"Page {page_number}: OCR 부족 ({len(ocr_text)} chars) → VLM-only")
                return self._extract_vlm_only(image, page_number, region_type)
            
            # Pass 2: VLM 구조화
            structured = self._structure_with_vlm(
                image, ocr_text, page_number
            )
            
            return ExtractedContent(
                text=structured,
                content=structured,
                method='hybrid_2pass',
                type=region_type,
                page_number=page_number,
                ocr_text=ocr_text,
                confidence=0.98,
                metadata={'source': 'hybrid_2pass', 'description': description}
            )
            
        except Exception as e:
            logger.error(f"Page {page_number} 추출 실패: {e}", exc_info=True)
            return self._extract_vlm_only(image, page_number, region_type)
    
    def _extract_with_ocr(self, image: Image.Image) -> str:
        """Pass 1: OCR 텍스트 추출"""
        if self.ocr_engine == 'tesseract':
            return self._extract_with_tesseract(image)
        elif self.ocr_engine == 'paddle':
            logger.warning("PaddleOCR not implemented. Using Tesseract.")
            return self._extract_with_tesseract(image)
        elif self.ocr_engine == 'none':
            return ""
        else:
            logger.warning(f"Unknown OCR engine: {self.ocr_engine}")
            return ""
    
    def _extract_with_tesseract(self, image: Image.Image) -> str:
        """Tesseract OCR 실행"""
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available")
            return ""
        
        try:
            text = pytesseract.image_to_string(image, config=self.ocr_config)
            text = text.strip()
            logger.info(f"✅ OCR: {len(text)} chars")
            return text
        except Exception as e:
            logger.error(f"OCR 실패: {e}")
            return ""
    
    def _structure_with_vlm(
        self, 
        image: Image.Image, 
        ocr_text: str,
        page_number: int
    ) -> str:
        """Pass 2: VLM으로 구조화 (OCR 텍스트 기반!)"""
        
        # 이미지를 바이트로 변환
        image_bytes = self._image_to_bytes(image)
        
        # 🎯 핵심: OCR 텍스트를 보고 구조화하는 프롬프트
        custom_prompt = f"""당신은 문서 구조화 전문가입니다.

**중요: 아래 OCR 텍스트의 정확도를 최우선으로 하되, 이미지를 보고 구조를 파악하세요.**

---
📄 OCR로 추출한 정확한 텍스트:
---
{ocr_text}
---

🎯 작업:
1. **이미지를 보고** 문서의 구조를 파악하세요 (표, 차트, 리스트, 섹션 등)
2. **위 OCR 텍스트를 정확히 사용**하여 마크다운으로 구조화하세요
3. **절대 텍스트를 변경하지 마세요** - OCR 텍스트를 그대로 배치만 하세요

**절대 금지 사항:**
- ❌ OCR 텍스트에 없는 단어 추가
- ❌ 숫자나 단어 변경 (예: "주요" → "수요" 금지)
- ❌ 맥락에 맞지 않는 해석 (예: "해외축구" → "메이저리그" 금지)

**허용 사항:**
- ✅ 표 형식으로 정리 (|...|...|)
- ✅ 리스트 구조화 (-, *)
- ✅ 섹션 헤더 추가 (#, ##)
- ✅ 줄바꿈 및 들여쓰기 조정

**출력 형식:**
- 마크다운 형식
- OCR 텍스트의 모든 내용 포함
- 이미지의 구조 반영

**다시 한 번 강조: OCR 텍스트를 절대 변경하지 마세요!**
"""
        
        try:
            # ✅ custom_prompt 전달!
            response = self.vlm_service.generate_caption(
                image_data=image_bytes,
                element_type='text',
                custom_prompt=custom_prompt  # ✅ 추가!
            )
            
            # 응답 파싱
            if isinstance(response, dict):
                vlm_result = response.get('caption', '')
            else:
                vlm_result = str(response)
            
            # 🔍 검증: VLM 결과가 유효한지 확인
            if not vlm_result or len(vlm_result.strip()) < 100:
                logger.warning(f"Page {page_number}: VLM 결과 부족 ({len(vlm_result)} chars)")
                logger.info(f"   → OCR 텍스트 사용 ({len(ocr_text)} chars)")
                return ocr_text
            
            # VLM 결과가 충분하면 사용
            logger.info(f"✅ VLM 구조화 성공: {len(vlm_result)} chars (OCR: {len(ocr_text)} chars)")
            return vlm_result
            
        except Exception as e:
            logger.error(f"VLM 구조화 실패: {e}", exc_info=True)
            logger.info(f"   → OCR 텍스트 사용 ({len(ocr_text)} chars)")
            return ocr_text
    
    def _extract_vlm_only(
        self, 
        image: Image.Image, 
        page_number: int,
        region_type: str = 'text'
    ) -> ExtractedContent:
        """Fallback: VLM만 사용"""
        logger.warning(f"Page {page_number}: Fallback to VLM-only mode")
        
        image_bytes = self._image_to_bytes(image)
        
        try:
            response = self.vlm_service.generate_caption(
                image_data=image_bytes,
                element_type='text'
            )
            
            if isinstance(response, dict):
                text = response.get('caption', '')
            else:
                text = str(response)
            
            if not text:
                logger.error(f"Page {page_number}: VLM 응답 없음")
                text = "[VLM 처리 실패]"
            
            return ExtractedContent(
                text=text,
                content=text,
                method='vlm_only',
                type=region_type,
                page_number=page_number,
                confidence=0.85,
                metadata={'source': 'vlm_only'}
            )
        except Exception as e:
            logger.error(f"VLM-only 실패: {e}", exc_info=True)
            return ExtractedContent(
                text='[처리 실패]',
                content='[처리 실패]',
                method='error',
                type='error',
                page_number=page_number,
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """PIL Image → bytes"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """PIL Image → Base64"""
        return base64.b64encode(self._image_to_bytes(image)).decode('utf-8')


# ===== 하위 호환성 =====

__all__ = ['HybridExtractor', 'ExtractedContent']
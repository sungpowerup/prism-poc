"""
core/hybrid_extractor.py
PRISM Phase 0.3.4 P1 - GPT 핫픽스 반영

✅ 변경사항:
1. quality_score → None 고정 (Golden 미연동)
2. 로그에서 "품질=100/100" 제거
3. 추출 길이와 source만 로깅
"""

import logging
from typing import Dict, Any
import base64

logger = logging.getLogger(__name__)


class HybridExtractor:
    """Phase 0.3.4 P1 하이브리드 추출기"""
    
    def __init__(self, vlm_service, pdf_path: str, allow_tables: bool = False):
        self.vlm_service = vlm_service
        self.pdf_path = pdf_path
        self.allow_tables = allow_tables
        
        # 필요한 하위 모듈들 (실제 구현에서 import)
        from core.quick_layout_analyzer import QuickLayoutAnalyzer
        from core.prompt_rules import PromptRules
        from core.post_merge_normalizer_safe import PostMergeNormalizer
        from core.typo_normalizer_safe import TypoNormalizer
        
        self.layout_analyzer = QuickLayoutAnalyzer()
        self.prompt_rules = PromptRules()
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        logger.info("✅ HybridExtractor Phase 0.3.4 P1 초기화")
        logger.info(f"   - PDF: {pdf_path}")
        logger.info(f"   - 표 허용: {allow_tables}")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        페이지 추출
        
        Returns:
            {
                'content': str,        # 추출된 텍스트
                'source': str,         # 'vlm' or 'fallback'
                'quality_score': None, # GPT 핫픽스: 항상 None
                'page_num': int,
                'hints': dict
            }
        """
        logger.info(f"   🔍 페이지 {page_num} 추출 시작")
        
        # 1. 레이아웃 분석
        hints = self.layout_analyzer.analyze(image_data)
        hints['allow_tables'] = self.allow_tables
        
        # 2. 프롬프트 생성
        prompt = self.prompt_rules.build_prompt(hints)
        
        # 3. VLM 호출
        try:
            content = self.vlm_service.call_with_image(
                image_data=image_data,
                prompt=prompt,
                page_num=page_num
            )
            
            if content and len(content.strip()) >= 50:
                source = 'vlm'
                # GPT 핫픽스: 품질 점수 로그 제거, 길이와 source만
                logger.info(f"      ✅ VLM 성공: {len(content)}자")
            else:
                content = self._fallback_extraction(page_num)
                source = 'fallback'
                logger.warning(f"      ⚠️ VLM 응답 부족 → Fallback")
        
        except Exception as e:
            logger.warning(f"      ⚠️ VLM 실패: {e}")
            content = self._fallback_extraction(page_num)
            source = 'fallback'
        
        # 4. 후처리
        content = self.post_normalizer.normalize(content)
        content = self.typo_normalizer.normalize(content)
        
        # GPT 핫픽스: quality_score는 항상 None
        logger.info(f"      ✅ 추출 완료: {len(content)}자, source={source}")
        
        return {
            'content': content,
            'source': source,
            'quality_score': None,  # Golden 미연동
            'page_num': page_num,
            'hints': hints
        }
    
    def _fallback_extraction(self, page_num: int) -> str:
        """Fallback 추출 (pypdf)"""
        # 실제 구현에서는 pypdf 사용
        return f"# 페이지 {page_num}\n[Fallback 추출]"
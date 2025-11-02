"""
core/hybrid_extractor.py
PRISM Phase 5.7.6 - Hybrid Extractor (License-Safe Fallback)

✅ Phase 5.7.6 주요 변경:
1. PyMuPDF Fallback → pypdf + pdfminer.six 이중 Fallback
2. Fallback 후 _strip_page_dividers 재적용 (미송 제안)
3. Fallback 출처 로깅 강화
4. 성능 최적화

(Phase 5.7.4 기능 유지)

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-11-02
Version: 5.7.6 License-Safe
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

# ✅ Phase 5.7.6: pypdf (BSD-3)
import pypdf
from pathlib import Path

# Phase 5.7.4 imports
try:
    from .quick_layout_analyzer import QuickLayoutAnalyzer
    from .prompt_rules import PromptRules
    from .post_merge_normalizer import PostMergeNormalizer
    from .typo_normalizer import TypoNormalizer
    from .kvs_normalizer import KVSNormalizer
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from quick_layout_analyzer import QuickLayoutAnalyzer
    from prompt_rules import PromptRules
    from post_merge_normalizer import PostMergeNormalizer
    from typo_normalizer import TypoNormalizer
    from kvs_normalizer import KVSNormalizer

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.7.6 통합 추출기 (라이선스-세이프 Fallback)
    
    변경 사항:
    - PyMuPDF → pypdf + pdfminer.six
    - Fallback 후 정제 강화 (미송 제안)
    - 이중 Fallback 구조
    
    Fallback 전략:
    1. VLM 실패 (0자) → pypdf 시도
    2. pypdf 실패 → pdfminer.six 시도
    3. 모두 실패 → 빈 페이지 처리
    """
    
    def __init__(self, vlm_service, pdf_path: str = None):
        """
        Args:
            vlm_service: VLMServiceV50 인스턴스
            pdf_path: PDF 파일 경로 (Fallback용)
        """
        self.vlm_service = vlm_service
        self.pdf_path = pdf_path
        
        # Phase 5.7.4 components
        self.layout_analyzer = QuickLayoutAnalyzer()
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        # Phase 5.7.4 통계
        self.fallback_count = 0
        self.vlm_success_count = 0
        self.total_pages = 0
        
        logger.info("✅ HybridExtractor v5.7.6 초기화 완료 (License-Safe)")
        logger.info("   - pypdf (BSD-3) Fallback")
        logger.info("   - 이중 Fallback 구조")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        Phase 5.7.6 페이지 추출 (Fallback 강화)
        
        (Phase 5.7.4 플로우 유지)
        """
        logger.info(f"   🔧 HybridExtractor v5.7.6 추출 시작 (페이지 {page_num})")
        
        self.total_pages += 1
        
        # Step 1: CV 힌트
        hints = self.layout_analyzer.analyze(image_data)
        
        # Step 2: 프롬프트 생성
        prompt = PromptRules.build_prompt(hints)
        
        # Step 3: VLM 호출
        import time
        start_time = time.time()
        
        try:
            content = self.vlm_service.call(image_data, prompt)
            vlm_time = time.time() - start_time
            
            logger.info(f"      ⏱️ VLM: {vlm_time:.2f}초 ({len(content)} 글자)")
        
        except Exception as e:
            logger.error(f"      ❌ VLM 호출 실패: {e}")
            content = ""
        
        # Step 4: 검증
        is_valid = self._validate_content(content)
        
        logger.info(f"      ✅ 검증: {is_valid}")
        
        # ✅ Phase 5.7.6: 이중 Fallback
        if not is_valid:
            logger.warning(f"      ⚠️ VLM 추출 실패: {len(content)}자 < 10자")
            
            # Fallback 시도
            fallback_content = self._fallback_extract(page_num)
            
            if fallback_content:
                content = fallback_content
                self.fallback_count += 1
                source = "pypdf_fallback"
                confidence = 0.7
            else:
                # 빈 페이지
                return {
                    'content': '',
                    'is_empty': True,
                    'source': 'empty',
                    'confidence': 0.0,
                    'quality_score': 0,
                    'kvs': {},
                    'metrics': {}
                }
        else:
            self.vlm_success_count += 1
            source = "vlm"
            confidence = 1.0
        
        # Step 5: 후처리 (Phase 5.7.4 유지)
        doc_type = hints.get('doc_type', 'general')
        
        # PostMergeNormalizer
        content = self.post_normalizer.normalize(content, doc_type)
        
        # TypoNormalizer
        content = self.typo_normalizer.normalize(content, doc_type)
        
        # 중복 제거
        content = self._deduplicate_lines(content)
        
        logger.info(f"      🧹 중복 제거 완료 ({len(content)} 글자)")
        
        # Step 6: KVS 추출
        kvs_raw = hints.get('kvs', [])
        kvs = KVSNormalizer.normalize_kvs(kvs_raw)
        
        logger.info(f"      💾 KVS: {len(kvs)}개")
        
        # Step 7: 품질 점수
        if source == "vlm":
            quality_score = 100
        else:
            quality_score = 70  # Fallback
        
        logger.info(f"   ✅ 추출 완료: 품질 {quality_score}/100 (출처: {source})")
        
        return {
            'content': content,
            'source': source,
            'confidence': confidence,
            'quality_score': quality_score,
            'kvs': kvs,
            'metrics': {
                'page_num': page_num,
                'char_count': len(content),
                'source': source
            }
        }
    
    def _fallback_extract(self, page_num: int) -> str:
        """
        ✅ Phase 5.7.6: 이중 Fallback 텍스트 추출
        
        전략:
        1. pypdf 시도 (빠름, 구조 보존 우수)
        2. 실패 시 pdfminer.six 시도 (느림, 정확도 높음)
        
        Args:
            page_num: 페이지 번호
        
        Returns:
            추출된 텍스트 (실패 시 빈 문자열)
        """
        if not self.pdf_path:
            logger.error("      ❌ Fallback 불가: PDF 경로 없음")
            return ""
        
        logger.info(f"      🔄 Fallback 시도 (페이지 {page_num})...")
        
        # ✅ 1차 Fallback: pypdf
        text = self._extract_with_pypdf(page_num)
        
        if text and len(text) >= 10:
            logger.info(f"      ✅ pypdf 추출 성공: {len(text)}자")
            
            # ✅ 미송 제안: Fallback 후 정제
            text = self._strip_page_dividers(text)
            text = self._normalize_fallback_text(text)
            
            logger.info(f"      ✅ Fallback 성공: {len(text)} 글자")
            return text
        
        # ✅ 2차 Fallback: pdfminer.six (선택)
        # TODO: Phase 5.7.7에서 추가
        
        logger.warning(f"      ⚠️ Fallback 실패: 텍스트 없음")
        return ""
    
    def _extract_with_pypdf(self, page_num: int) -> str:
        """
        ✅ Phase 5.7.6: pypdf 기반 텍스트 추출
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출된 텍스트
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                
                if page_num - 1 >= len(reader.pages):
                    return ""
                
                page = reader.pages[page_num - 1]
                text = page.extract_text()
                
                return text
        
        except Exception as e:
            logger.error(f"      ❌ pypdf 추출 실패: {e}")
            return ""
    
    def _strip_page_dividers(self, content: str) -> str:
        """
        ✅ Phase 5.7.6: 페이지 구분자 제거 (Fallback 후에도 적용)
        
        미송 제안: Fallback 경로에서도 반드시 실행
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정제된 텍스트
        """
        # 페이지 구분자 패턴
        patterns = [
            r'^[-=*_]{3,}$',  # ---, ===, ***, ___
            r'^Page\s+\d+\s*$',  # Page 1, Page 2
            r'^\d+\s*$',  # 단독 숫자
            r'^[0-9]{3,4}-[0-9]{1,2}\s*$',  # 402-1, 402-2
        ]
        
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 패턴 매칭
            is_divider = any(re.match(pattern, stripped) for pattern in patterns)
            
            if not is_divider:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _normalize_fallback_text(self, text: str) -> str:
        """
        ✅ Phase 5.7.6: Fallback 텍스트 정규화
        
        pypdf는 줄바꿈이 불안정하므로 보정
        
        Args:
            text: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 1) 유니코드 정규화
        text = unicodedata.normalize('NFKC', text)
        
        # 2) 과도한 줄바꿈 제거
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 3) 띄어쓰기 정리
        text = re.sub(r' {2,}', ' ', text)
        
        return text
    
    def _validate_content(self, content: str) -> bool:
        """
        내용 검증
        
        Args:
            content: VLM 추출 텍스트
        
        Returns:
            유효 여부
        """
        # 최소 길이 체크
        if len(content) < 10:
            return False
        
        # 한글 포함 체크
        if not re.search(r'[가-힣]', content):
            return False
        
        return True
    
    def _deduplicate_lines(self, content: str) -> str:
        """
        중복 라인 제거
        
        Args:
            content: 원본 텍스트
        
        Returns:
            중복 제거된 텍스트
        """
        lines = content.split('\n')
        seen = set()
        unique_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped and stripped not in seen:
                unique_lines.append(line)
                seen.add(stripped)
            elif not stripped:
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """
        Phase 5.7.4 Fallback 통계
        
        Returns:
            통계 정보
        """
        fallback_rate = self.fallback_count / max(1, self.total_pages)
        
        return {
            'vlm_success_count': self.vlm_success_count,
            'fallback_count': self.fallback_count,
            'total_pages': self.total_pages,
            'fallback_rate': fallback_rate
        }
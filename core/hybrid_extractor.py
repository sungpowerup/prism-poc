"""
core/hybrid_extractor.py
PRISM Phase 5.7.8.2 - Hybrid Extractor (긴급 패치 - doc_type 강제 설정)

✅ Phase 5.7.8.2 긴급 수정:
1. doc_type을 'statute'로 강제 설정 (규정 문서 기본)
2. 규정 키워드 감지 강화
3. 로깅 개선

🎯 해결 문제:
- doc_type='general'로 인한 사전 미적용
- "1명의직원에게", "부여할수있는", "사 제" 미수정

Author: 이서영 (Backend Lead) + 긴급 진단
Date: 2025-11-05
Version: 5.7.8.2 Emergency Hotfix
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
    Phase 5.7.8.2 통합 추출기 (doc_type 강제 설정)
    
    ✅ Phase 5.7.8.2 개선:
    - doc_type을 'statute'로 강제 설정
    - 규정 키워드 감지 강화
    - 로깅 개선
    
    Fallback 전략:
    1. VLM 실패 (0자) → pypdf 시도
    2. pypdf 성공 시 → 인라인 마커 제거 + 정규화
    3. 모두 실패 → 빈 페이지 처리
    """
    
    # ✅ Phase 5.7.8.2: 규정 키워드 확장
    STATUTE_KEYWORDS = [
        '조', '항', '호', '목', '개정', '신설', '삭제',
        '규정', '법령', '정관', '직원', '임용', '채용',
        '제1조', '제2조', '제3조', '제4조', '제5조',
        '제1장', '제2장', '총칙', '부칙'
    ]
    
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
        
        logger.info("✅ HybridExtractor v5.7.8.2 초기화 완료 (doc_type 강제 설정)")
        logger.info("   - pypdf (BSD-3) Fallback")
        logger.info("   - doc_type='statute' 강제 적용")
        logger.info("   - 규정 키워드 감지 강화")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        Phase 5.7.8.2 페이지 추출 (doc_type 강제)
        
        (Phase 5.7.7.1 플로우 유지)
        """
        logger.info(f"   🔧 HybridExtractor v5.7.8.2 추출 시작 (페이지 {page_num})")
        
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
        
        # ✅ Phase 5.7.7.2: Fallback + 인라인 마커 제거
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
        
        # ✅ Phase 5.7.8.2: doc_type 강제 설정
        doc_type = self._detect_doc_type(content, hints)
        
        logger.info(f"      📋 문서 타입: {doc_type}")
        
        # Step 5: 후처리 (Phase 5.7.8.2 doc_type 전달)
        # PostMergeNormalizer (v5.7.8.1 - OrderedDict)
        content = self.post_normalizer.normalize(content, doc_type)
        
        # TypoNormalizer (v5.7.8.1 - OrderedDict)
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
        
        logger.info(f"   ✅ 추출 완료: 품질 {quality_score}/100 (출처: {source}, 타입: {doc_type})")
        
        return {
            'content': content,
            'source': source,
            'confidence': confidence,
            'quality_score': quality_score,
            'kvs': kvs,
            'metrics': {
                'page_num': page_num,
                'char_count': len(content),
                'source': source,
                'doc_type': doc_type  # ✅ 추가
            }
        }
    
    def _detect_doc_type(self, content: str, hints: Dict[str, Any]) -> str:
        """
        ✅ Phase 5.7.8.2: 문서 타입 감지 (규정 우선)
        
        전략:
        1. hints에서 doc_type 확인
        2. 규정 키워드 감지
        3. 기본값: 'statute' (규정 문서 우선)
        
        Args:
            content: 추출된 텍스트
            hints: 레이아웃 힌트
        
        Returns:
            'statute', 'general', 'bus_diagram', 'table'
        """
        # 1) hints에서 확인
        hint_type = hints.get('doc_type')
        if hint_type in ['statute', 'bus_diagram', 'table']:
            logger.debug(f"      doc_type from hints: {hint_type}")
            return hint_type
        
        # 2) 규정 키워드 감지
        keyword_count = sum(1 for keyword in self.STATUTE_KEYWORDS if keyword in content)
        
        if keyword_count >= 3:
            logger.debug(f"      doc_type detected: statute (keywords: {keyword_count})")
            return 'statute'
        
        # 3) 조문 패턴 감지
        article_pattern = r'제\s*\d+\s*조'
        article_matches = re.findall(article_pattern, content)
        
        if len(article_matches) >= 1:
            logger.debug(f"      doc_type detected: statute (articles: {len(article_matches)})")
            return 'statute'
        
        # 4) 기본값: 'statute' (규정 문서 우선)
        logger.debug("      doc_type default: statute")
        return 'statute'
    
    def _fallback_extract(self, page_num: int) -> str:
        """
        ✅ Phase 5.7.7.2: Fallback 텍스트 추출 (인라인 마커 제거)
        
        전략:
        1. pypdf 시도 (빠름, 구조 보존 우수)
        2. ✅ 인라인 페이지 마커 제거 강화 (미송 제안)
        3. 정규화 적용
        
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
            
            # ✅ Phase 5.7.7.2: 인라인 페이지 마커 제거 강화 (미송 제안)
            text = self._remove_inline_page_markers(text)
            text = self._strip_page_dividers(text)
            text = self._normalize_fallback_text(text)
            
            logger.info(f"      ✅ Fallback 성공: {len(text)} 글자")
            return text
        
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
    
    def _remove_inline_page_markers(self, content: str) -> str:
        """
        ✅ Phase 5.7.7.3: 인라인 페이지 마커 제거 강화 (미송 제안)
        
        문제:
        - "402-2" + "1." → "402-21."로 합쳐짐
        - "402-3" + "용을" → "402-3용을"로 합쳐짐 (신규 발견)
        - 페이지 번호가 항목 번호 또는 한글과 결합
        
        해결:
        - 인라인 패턴 감지 및 제거 강화
        - "402-21." → "1."로 복구
        - "402-3용을" → "용을"로 복구
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정제된 텍스트
        """
        # 1) 페이지 마커 + 항목 번호 패턴
        # "402-21." → "1."
        content = re.sub(r'\b\d{3,4}-\d{1,2}\s*(\d+[.)])', r'\1', content)
        
        # 2) 페이지 마커 + 공백 + 항목 번호
        # "402-2 1." → "1."
        content = re.sub(r'\b\d{3,4}-\d{1,2}\s+(\d+[.)])', r'\1', content)
        
        # ✅ Phase 5.7.7.3: 3) 페이지 마커 + 한글 결합 (신규)
        # "402-3용을" → "용을"
        content = re.sub(r'\b\d{3,4}-\d{1,2}([가-힣])', r'\1', content)
        
        # 4) 페이지 마커만 단독 (줄 중간)
        # "...내용 402-2 내용..." → "...내용 내용..."
        content = re.sub(r'\s+\d{3,4}-\d{1,2}\s+', ' ', content)
        
        logger.debug(f"      인라인 페이지 마커 제거 완료 (Phase 5.7.8.2)")
        return content
    
    def _strip_page_dividers(self, content: str) -> str:
        """
        ✅ Phase 5.7.7.1: 페이지 구분자 제거 강화 (미송 제안)
        
        개선 사항:
        - "인사규정" 헤더 제거 추가
        - "402-1", "402-2", "402-3" 패턴 강화
        - 단독 숫자 제거 강화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정제된 텍스트
        """
        lines = content.split('\n')
        filtered_lines = []
        
        # ✅ Phase 5.7.7.1: 페이지 구분자 패턴 강화
        page_patterns = [
            r'^[-=*_]{3,}$',  # ---, ===, ***, ___
            r'^Page\s+\d+\s*$',  # Page 1, Page 2
            r'^\d{1,2}$',  # 단독 숫자 (1, 2, 3)
            r'^[0-9]{3,4}-[0-9]{1,2}$',  # 402-1, 402-2 (정확히 매칭)
            r'^인사규정$',  # "인사규정" 헤더 (미송 제안)
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # 패턴 매칭
            is_divider = any(re.match(pattern, stripped) for pattern in page_patterns)
            
            if not is_divider:
                filtered_lines.append(line)
            else:
                logger.debug(f"      페이지 마커 제거: '{stripped}'")
        
        logger.debug(f"      페이지 마커 제거 완료: {len(lines)} → {len(filtered_lines)} 줄")
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
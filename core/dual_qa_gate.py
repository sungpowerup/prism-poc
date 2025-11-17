"""
dual_qa_gate.py - PDF ↔ VLM/LawMode 이중 검증
Phase 0.7.5 Annex Fallback (긴급 핫픽스)

✅ Phase 0.7.5 핫픽스:
- 텍스트 커버리지 기반 QA 추가
- Annex 페이지: 조문 0개 + 텍스트 90%+ → 통과
- 로그 개선: coverage 표시

Author: 정수아 (QA Lead) + GPT + CEO 피드백
Date: 2025-11-16
Version: Phase 0.7.5 Annex Fallback
"""

import re
import logging
from typing import Dict, Any, Set, Literal

logger = logging.getLogger(__name__)

SourceType = Literal["vlm", "lawmode"]


class DualQAGate:
    """
    Phase 0.7.5 DualQA Gate
    
    ✅ Phase 0.7.5: Annex Fallback 지원
    - 텍스트 커버리지 기반 QA 추가
    - 조문 0개 + 텍스트 90%+ → 통과
    """
    
    ARTICLE_STRICT = re.compile(
        r'제\s*(\d+)\s*조(?:의\s*(\d+))?\s*\(',
        re.MULTILINE
    )
    
    ARTICLE_LOOSE = re.compile(
        r'제\s*(\d+)\s*조(?:의\s*(\d+))?(?=\s|$)',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info("✅ DualQA Gate 초기화 (Phase 0.7.5 Annex Fallback)")
    
    def validate(
        self,
        pdf_text: str,
        processed_text: str,
        source: SourceType = "vlm",
        min_match_rate: float = 0.95,
        min_coverage: float = 0.90  # ✅ Phase 0.7.5: 텍스트 커버리지 임계값
    ) -> Dict[str, Any]:
        """
        ✅ Phase 0.7.5: PDF ↔ 처리된 텍스트 이중 검증 (Annex Fallback 지원)
        
        Args:
            pdf_text: PDF 원본 텍스트
            processed_text: VLM 또는 LawMode로 처리된 텍스트
            source: "vlm" 또는 "lawmode"
            min_match_rate: 최소 매칭률 (기본: 0.95)
            min_coverage: 최소 텍스트 커버리지 (기본: 0.90) - ✅ Phase 0.7.5
        
        Returns:
            {
                'pdf_articles': Set[str],
                'processed_articles': Set[str],
                'matched': Set[str],
                'missing_in_processed': Set[str],
                'extra_in_processed': Set[str],
                'match_rate': float,
                'text_coverage': float,  # ✅ Phase 0.7.5
                'qa_flags': List[str],
                'is_pass': bool
            }
        """
        source_label = "VLM" if source == "vlm" else "LawMode"
        
        logger.info("🔬 DualQA 검증 시작 (Phase 0.7.5 Annex Fallback)")
        logger.info(f"   📊 소스: {source_label}")
        logger.info(f"   📏 최소 매칭률: {min_match_rate*100:.1f}%")
        logger.info(f"   📏 최소 커버리지: {min_coverage*100:.1f}%")  # ✅ Phase 0.7.5
        
        # 1. PDF 조문 헤더 추출
        pdf_articles = self._extract_article_headers(pdf_text, source="PDF")
        
        # 2. 처리된 텍스트 조문 헤더 추출
        processed_articles = self._extract_article_headers(
            processed_text, 
            source=source_label
        )
        
        # 3. 매칭
        matched = pdf_articles & processed_articles
        missing_in_processed = pdf_articles - processed_articles
        extra_in_processed = processed_articles - pdf_articles
        
        # 4. 매칭률
        if len(pdf_articles) > 0:
            match_rate = len(matched) / len(pdf_articles)
        else:
            match_rate = 0.0
        
        # ✅ Phase 0.7.5: 텍스트 커버리지 계산
        pdf_len = len(pdf_text.strip())
        processed_len = len(processed_text.strip())
        
        if pdf_len > 0:
            text_coverage = processed_len / pdf_len
        else:
            text_coverage = 0.0
        
        logger.info(f"   📊 텍스트 커버리지: {text_coverage:.1%} ({processed_len} / {pdf_len}자)")
        
        # 5. QA 플래그
        qa_flags = []
        
        # ✅ Phase 0.7.5: Annex 모드 판단
        is_annex_mode = (len(pdf_articles) == 0 and pdf_len > 500)
        
        if is_annex_mode:
            logger.info(f"   🔄 Annex 모드 감지 (조문 0개 + 텍스트 {pdf_len}자)")
            
            # Annex 모드: 텍스트 커버리지 기반 QA
            if text_coverage < min_coverage:
                qa_flags.append('low_coverage')
                logger.error(f"      ❌ 텍스트 커버리지 부족: {text_coverage:.1%} < {min_coverage:.1%}")
            else:
                logger.info(f"      ✅ Annex 모드 QA 통과 (커버리지: {text_coverage:.1%})")
        
        else:
            # 법조문 모드: 기존 로직
            if match_rate < min_match_rate:
                qa_flags.append('low_match_rate')
            
            if missing_in_processed:
                qa_flags.append('processed_missing_articles')
            
            if extra_in_processed:
                qa_flags.append('processed_extra_articles')
        
        # 6. 통과 여부
        if is_annex_mode:
            # Annex 모드: 텍스트 커버리지만 체크
            is_pass = (text_coverage >= min_coverage)
        else:
            # 법조문 모드: 기존 로직
            is_pass = (match_rate >= min_match_rate and len(qa_flags) == 0)
        
        # 로그 출력
        logger.info("✅ DualQA 검증 완료 (Phase 0.7.5):")
        logger.info(f"   📊 [PDF] 조문: {len(pdf_articles)}개")
        logger.info(f"   📊 [{source_label}] 조문: {len(processed_articles)}개")
        logger.info(f"   📊 일치: {len(matched)}개")
        logger.info(f"   📊 매칭률: {match_rate:.1%}")
        
        if missing_in_processed:
            logger.error(f"   ❌ [{source_label}] 누락: {sorted(missing_in_processed)}")
        
        if extra_in_processed:
            logger.warning(f"   ⚠️ [{source_label}] 추가: {sorted(extra_in_processed)}")
        
        if qa_flags:
            logger.error(f"   🚨 QA 플래그: {qa_flags}")
            logger.error(f"      → 원문 불일치! 수동 검수 필요합니다!")
        else:
            if is_annex_mode:
                logger.info(f"   ✅ Annex 모드 QA 통과 (커버리지: {text_coverage:.1%})")
            else:
                logger.info("   ✅ 원문 일치 (QA 통과)")
        
        result = {
            'pdf_articles': pdf_articles,
            'processed_articles': processed_articles,
            'matched': matched,
            'missing_in_processed': missing_in_processed,
            'extra_in_processed': extra_in_processed,
            'match_rate': match_rate,
            'text_coverage': text_coverage,  # ✅ Phase 0.7.5
            'qa_flags': qa_flags,
            'is_pass': is_pass,
            'is_annex_mode': is_annex_mode,  # ✅ Phase 0.7.5
            'source': source_label
        }
        
        return result
    
    def _extract_article_headers(self, text: str, source: str = "") -> Set[str]:
        """조문 헤더 추출"""
        headers = set()
        
        # 1. Strict 패턴
        for m in self.ARTICLE_STRICT.finditer(text):
            matched = m.group(0).split('(')[0].strip()
            matched = re.sub(r'\s+', '', matched)
            headers.add(matched)
        
        # 2. Loose 패턴
        for m in self.ARTICLE_LOOSE.finditer(text):
            matched = m.group(0).strip()
            matched = re.sub(r'\s+', '', matched)
            headers.add(matched)
        
        if source:
            logger.info(f"   📖 [{source}] 조문 헤더: {len(headers)}개")
        
        return headers


def extract_pdf_text_layer(pdf_path: str) -> str:
    """PDF 텍스트 레이어 추출"""
    try:
        from pypdf import PdfReader
        
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        full_text = '\n\n'.join(text_parts)
        
        logger.info(f"✅ PDF 텍스트 추출 완료:")
        logger.info(f"   페이지: {len(reader.pages)}개")
        logger.info(f"   텍스트: {len(full_text)}자")
        
        return full_text
    
    except Exception as e:
        logger.error(f"❌ PDF 텍스트 추출 실패: {e}")
        return ""
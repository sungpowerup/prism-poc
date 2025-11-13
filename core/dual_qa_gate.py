"""
core/dual_qa_gate.py
PRISM Phase 0.4.0 P0-3b - Dual QA Gate

✅ GPT 피드백 반영:
1. PDF 원본 vs VLM 결과 이중 검증
2. VLM을 거치지 않은 순수 텍스트 추출
3. 관찰 모드 (하드 fail 금지)
4. 경고 + 메타데이터 플래그만

Author: 이서영 (Backend Lead) + GPT 보정
Date: 2025-11-13
Version: Phase 0.4.0 P0-3b
"""

import re
import logging
from typing import Dict, Set, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DualQAGate:
    """
    PDF 원본 vs VLM 결과 이중 검증
    
    ✅ GPT 핵심:
    - VLM을 진실로 가정하지 않음
    - PDF 텍스트 레이어와 직접 비교
    - 불일치는 경고만 (하드 fail 금지)
    """
    
    # ============================================
    # 조문 헤더 패턴 (semantic_chunker와 동일)
    # ============================================
    NUM = r'\d+(?:의\d+)?'
    AFTER_JO_NOT_NUM = r'(?!\s*제?\s*\d)'
    
    # Strict: 제N조( 형식
    ARTICLE_STRICT = re.compile(
        rf'(제\s*{NUM}\s*조){AFTER_JO_NOT_NUM}(?=\s*\()',
        re.MULTILINE
    )
    
    # Loose: 제N조 단독
    ARTICLE_LOOSE = re.compile(
        rf'(제\s*{NUM}\s*조){AFTER_JO_NOT_NUM}(?=\s|$)',
        re.MULTILINE
    )
    
    def __init__(self):
        logger.info("✅ DualQAGate Phase 0.4.0 P0-3b 초기화")
        logger.info("   🔬 PDF vs VLM 이중 검증 (관찰 모드)")
    
    def validate(self, pdf_text: str, vlm_markdown: str) -> Dict:
        """
        PDF 원본 vs VLM 결과 검증
        
        Args:
            pdf_text: pypdfium2로 추출한 순수 PDF 텍스트
            vlm_markdown: VLM이 생성한 최종 Markdown
        
        Returns:
            검증 결과 딕셔너리
        """
        logger.info("🔬 DualQA 검증 시작")
        
        # 1. PDF 텍스트에서 조문 헤더 추출
        pdf_articles = self._extract_article_headers(pdf_text, source="PDF")
        
        # 2. VLM Markdown에서 조문 헤더 추출
        vlm_articles = self._extract_article_headers(vlm_markdown, source="VLM")
        
        # 3. 차이 분석
        missing_in_vlm = pdf_articles - vlm_articles  # PDF에는 있는데 VLM에 없음
        extra_in_vlm = vlm_articles - pdf_articles    # VLM에는 있는데 PDF에 없음
        matched = pdf_articles & vlm_articles         # 일치
        
        # 4. 매칭률 계산
        if len(pdf_articles) == 0:
            match_rate = 1.0 if len(vlm_articles) == 0 else 0.0
        else:
            match_rate = len(matched) / len(pdf_articles)
        
        # 5. 결과 정리
        result = {
            'pdf_count': len(pdf_articles),
            'vlm_count': len(vlm_articles),
            'matched_count': len(matched),
            'missing_in_vlm': sorted(missing_in_vlm),
            'extra_in_vlm': sorted(extra_in_vlm),
            'match_rate': match_rate,
            'qa_flags': []
        }
        
        # 6. QA 플래그 생성
        if match_rate < 0.95:
            result['qa_flags'].append('article_mismatch')
        
        if missing_in_vlm:
            result['qa_flags'].append('vlm_missing_articles')
        
        if extra_in_vlm:
            result['qa_flags'].append('vlm_extra_articles')
        
        # 7. 로깅
        self._log_result(result)
        
        return result
    
    def _extract_article_headers(self, text: str, source: str = "TEXT") -> Set[str]:
        """
        텍스트에서 조문 헤더 추출
        
        ✅ GPT 핵심: 인라인 참조 필터링
        """
        headers = set()
        
        # Strict 패턴으로 추출
        for m in self.ARTICLE_STRICT.finditer(text):
            header = m.group(1).strip()
            header = re.sub(r'\s+', '', header)  # 공백 제거
            headers.add(header)
        
        # Loose 패턴으로 보강 (인라인 참조 필터링)
        loose_candidates = []
        for m in self.ARTICLE_LOOSE.finditer(text):
            pos = m.start()
            header = m.group(1).strip()
            header = re.sub(r'\s+', '', header)
            
            if header not in headers:
                loose_candidates.append((pos, header))
        
        # 인라인 참조 필터링
        loose_candidates = self._filter_inline_references(text, loose_candidates)
        for _, header in loose_candidates:
            headers.add(header)
        
        logger.info(f"   📖 {source} 조문 헤더: {len(headers)}개")
        if headers:
            sample = sorted(headers)[:5]
            logger.info(f"      샘플: {sample}")
        
        return headers
    
    def _filter_inline_references(self, text: str, candidates: List[tuple]) -> List[tuple]:
        """
        인라인 참조 필터링
        
        제28조에 따른, 제73조제1항 같은 참조 제거
        """
        filtered = []
        
        for pos, matched in candidates:
            # 전후 컨텍스트
            start = max(0, pos - 50)
            end = min(len(text), pos + 100)
            context = text[start:end]
            
            # 인라인 참조 패턴
            inline_patterns = [
                rf'{re.escape(matched)}\s*제\s*\d+항',      # 제73조제1항
                rf'{re.escape(matched)}\s*에\s*따른',       # 제34조에 따른
                rf'{re.escape(matched)}\s*및',              # 제41조 및
                rf'{re.escape(matched)}\s*또는',            # 제28조 또는
                rf'{re.escape(matched)}\s*의\s*규정',       # 제35조의 규정
                rf'{re.escape(matched)}\s*과',              # 제28조과
            ]
            
            is_inline = any(re.search(p, context) for p in inline_patterns)
            
            if not is_inline:
                filtered.append((pos, matched))
        
        return filtered
    
    def _log_result(self, result: Dict) -> None:
        """
        검증 결과 로깅
        
        ✅ GPT 핵심: 관찰 모드 (ERROR 레벨이지만 중단 없음)
        """
        logger.info("✅ DualQA 검증 완료:")
        logger.info(f"   📊 PDF 조문: {result['pdf_count']}개")
        logger.info(f"   📊 VLM 조문: {result['vlm_count']}개")
        logger.info(f"   📊 일치: {result['matched_count']}개")
        logger.info(f"   📊 매칭률: {result['match_rate']:.1%}")
        
        if result['missing_in_vlm']:
            logger.error(f"   ❌ VLM 누락: {result['missing_in_vlm']}")
            logger.error(f"      → PDF에는 있지만 VLM이 추출하지 못한 조문입니다!")
        
        if result['extra_in_vlm']:
            logger.warning(f"   ⚠️ VLM 추가: {result['extra_in_vlm']}")
            logger.warning(f"      → VLM이 만들어낸 조문입니다 (PDF 원본에 없음)")
        
        if result['qa_flags']:
            logger.error(f"   🚨 QA 플래그: {result['qa_flags']}")
            logger.error(f"      → 원문 불일치! 수동 검수 필요합니다!")
        else:
            logger.info(f"   ✅ QA 플래그: 없음 (원본과 일치)")


# ============================================
# 유틸리티: PDF 텍스트 추출
# ============================================

def extract_pdf_text_layer(pdf_path: str) -> str:
    """
    pypdfium2로 PDF 텍스트 레이어 추출
    
    ✅ GPT 핵심: VLM을 거치지 않은 순수 텍스트
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.error("❌ pypdfium2 없음 - DualQA 불가")
        return ""
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error(f"❌ PDF 파일 없음: {pdf_path}")
        return ""
    
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        all_text = []
        
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            all_text.append(text)
        
        combined = '\n'.join(all_text)
        logger.info(f"   📄 PDF 텍스트 추출 완료: {len(combined)}자")
        
        return combined
        
    except Exception as e:
        logger.error(f"❌ PDF 텍스트 추출 실패: {e}")
        return ""

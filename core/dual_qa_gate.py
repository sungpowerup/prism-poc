"""
dual_qa_gate.py - PDF ↔ VLM/LawMode 이중 검증
Phase 0.6 "Elegance & Refinement"

✅ Phase 0.6 개선 (GPT 피드백):
- source 파라미터 추가 ("vlm" | "lawmode")
- 로그에 [PDF] vs [LawMode] 명확한 prefix
- 새벽 2시 디버깅 편의성 극대화

Author: 정수아 (QA Lead) + GPT 설계
Date: 2025-11-14
Version: Phase 0.6
"""

import re
import logging
from typing import Dict, Any, Set, Literal

logger = logging.getLogger(__name__)

# ✅ Phase 0.6: Source 타입 정의 (GPT 권장)
SourceType = Literal["vlm", "lawmode"]


class DualQAGate:
    """
    Phase 0.6 DualQA Gate
    
    ✅ Phase 0.6 개선:
    - source 파라미터: "vlm" | "lawmode"
    - 로그 prefix: [PDF] vs [VLM] or [LawMode]
    - 디버깅 편의성 극대화
    """
    
    # 조문 헤더 패턴 (Strict)
    ARTICLE_STRICT = re.compile(
        r'제\s*(\d+)\s*조(?:의\s*(\d+))?\s*\(',
        re.MULTILINE
    )
    
    # 조문 헤더 패턴 (Loose)
    ARTICLE_LOOSE = re.compile(
        r'제\s*(\d+)\s*조(?:의\s*(\d+))?(?=\s|$)',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info("✅ DualQA Gate 초기화 (Phase 0.6)")
    
    def validate(
        self,
        pdf_text: str,
        processed_text: str,
        source: SourceType = "vlm",  # ✅ Phase 0.6: 소스 명시 (GPT 권장)
        min_match_rate: float = 0.95
    ) -> Dict[str, Any]:
        """
        ✅ Phase 0.6: PDF ↔ 처리된 텍스트 이중 검증
        
        Args:
            pdf_text: PDF 원본 텍스트
            processed_text: VLM 또는 LawMode로 처리된 텍스트
            source: "vlm" 또는 "lawmode" (GPT 권장 - 로그 명확화)
            min_match_rate: 최소 매칭률 (기본: 0.95)
        
        Returns:
            {
                'pdf_articles': Set[str],
                'processed_articles': Set[str],
                'matched': Set[str],
                'missing_in_processed': Set[str],  # ✅ Phase 0.6: 명확화
                'extra_in_processed': Set[str],  # ✅ Phase 0.6: 명확화
                'match_rate': float,
                'qa_flags': List[str],
                'is_pass': bool
            }
        """
        # ✅ Phase 0.6: 소스 레이블 (GPT 권장 - 새벽 2시 디버깅용)
        source_label = "VLM" if source == "vlm" else "LawMode"
        
        logger.info("🔬 DualQA 검증 시작 (Phase 0.6)")
        logger.info(f"   📊 소스: {source_label}")
        logger.info(f"   📏 최소 매칭률: {min_match_rate*100:.1f}%")
        
        # 1. PDF 조문 헤더 추출
        pdf_articles = self._extract_article_headers(pdf_text, source="PDF")
        
        # 2. 처리된 텍스트 조문 헤더 추출
        processed_articles = self._extract_article_headers(
            processed_text, 
            source=source_label  # ✅ Phase 0.6: 로그에 실제 소스명 표시
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
        
        # 5. QA 플래그
        qa_flags = []
        
        if match_rate < min_match_rate:
            qa_flags.append('low_match_rate')
        
        if missing_in_processed:
            qa_flags.append('processed_missing_articles')  # ✅ Phase 0.6: 명확한 이름
        
        if extra_in_processed:
            qa_flags.append('processed_extra_articles')  # ✅ Phase 0.6: 명확한 이름
        
        # 6. 통과 여부
        is_pass = (match_rate >= min_match_rate and len(qa_flags) == 0)
        
        # ✅ Phase 0.6: 로그 출력 (GPT 권장 - [PDF] vs [소스] 명확화)
        logger.info("✅ DualQA 검증 완료 (Phase 0.6):")
        logger.info(f"   📊 [PDF] 조문: {len(pdf_articles)}개")
        logger.info(f"   📊 [{source_label}] 조문: {len(processed_articles)}개")
        logger.info(f"   📊 일치: {len(matched)}개")
        logger.info(f"   📊 매칭률: {match_rate:.1%}")
        
        if missing_in_processed:
            logger.error(f"   ❌ [{source_label}] 누락: {sorted(missing_in_processed)}")
            logger.error(f"      → PDF에는 있지만 {source_label}이 추출하지 못한 조문입니다!")
        
        if extra_in_processed:
            logger.warning(f"   ⚠️ [{source_label}] 추가: {sorted(extra_in_processed)}")
            logger.warning(f"      → {source_label}이 만들어낸 조문입니다 (PDF 원본에 없음)")
        
        if qa_flags:
            logger.error(f"   🚨 QA 플래그: {qa_flags}")
            logger.error(f"      → 원문 불일치! 수동 검수 필요합니다!")
        else:
            logger.info("   ✅ 원문 일치 (QA 통과)")
        
        result = {
            'pdf_articles': pdf_articles,
            'processed_articles': processed_articles,
            'matched': matched,
            'missing_in_processed': missing_in_processed,  # ✅ Phase 0.6
            'extra_in_processed': extra_in_processed,  # ✅ Phase 0.6
            'match_rate': match_rate,
            'qa_flags': qa_flags,
            'is_pass': is_pass,
            'source': source_label  # ✅ Phase 0.6: 결과에도 소스 명시
        }
        
        return result
    
    def _extract_article_headers(self, text: str, source: str = "") -> Set[str]:
        """
        조문 헤더 추출
        
        Args:
            text: 텍스트
            source: 소스명 (로깅용) - ✅ Phase 0.6: "PDF", "VLM", "LawMode"
        
        Returns:
            조문 헤더 집합 (예: {'제1조', '제2조', ...})
        """
        headers = set()
        
        # 1. Strict 패턴 (제N조( 형식)
        for m in self.ARTICLE_STRICT.finditer(text):
            matched = m.group(0).split('(')[0].strip()  # "제1조(" → "제1조"
            # 공백 정규화
            matched = re.sub(r'\s+', '', matched)
            headers.add(matched)
        
        # 2. Loose 패턴 (제N조 단독)
        for m in self.ARTICLE_LOOSE.finditer(text):
            matched = m.group(0).strip()
            matched = re.sub(r'\s+', '', matched)
            headers.add(matched)
        
        # ✅ Phase 0.6: 로그에 소스 명시 (GPT 권장)
        if source:
            logger.info(f"   📖 [{source}] 조문 헤더: {len(headers)}개")
            if headers and len(headers) <= 10:
                sample = sorted(headers)[:5]
                logger.info(f"       샘플: {sample}")
        
        return headers


# ============================================
# 유틸리티 함수
# ============================================

def extract_pdf_text_layer(pdf_path: str) -> str:
    """
    PDF 텍스트 레이어 추출 (pypdf 기반)
    
    Args:
        pdf_path: PDF 파일 경로
    
    Returns:
        추출된 텍스트
    """
    try:
        from pypdf import PdfReader
        
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for page_num, page in enumerate(reader.pages, start=1):
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


# ============================================
# 테스트
# ============================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 1: VLM 모드
    pdf_text = """
    제1조(목적) 이 규정은 ...
    제2조(적용범위) 이 규정은 ...
    제3조(정의) 다음 각 호의 ...
    """
    
    vlm_text = """
    ### 제1조(목적)
    이 규정은 ...
    
    ### 제2조(적용범위)
    이 규정은 ...
    """
    
    gate = DualQAGate()
    
    print("\n" + "="*60)
    print("테스트 1: VLM 모드")
    print("="*60)
    result = gate.validate(
        pdf_text=pdf_text,
        processed_text=vlm_text,
        source="vlm"  # ✅ Phase 0.6
    )
    print(f"\n매칭률: {result['match_rate']:.1%}")
    print(f"통과 여부: {result['is_pass']}")
    print(f"QA 플래그: {result['qa_flags']}")
    
    # 테스트 2: LawMode
    lawmode_text = """
    제1조(목적) 이 규정은 ...
    제2조(적용범위) 이 규정은 ...
    제3조(정의) 다음 각 호의 ...
    """
    
    print("\n" + "="*60)
    print("테스트 2: LawMode")
    print("="*60)
    result = gate.validate(
        pdf_text=pdf_text,
        processed_text=lawmode_text,
        source="lawmode"  # ✅ Phase 0.6
    )
    print(f"\n매칭률: {result['match_rate']:.1%}")
    print(f"통과 여부: {result['is_pass']}")
    print(f"소스: {result['source']}")
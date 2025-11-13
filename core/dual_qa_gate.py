"""
core/dual_qa_gate.py
PRISM Phase 0.4.0 P0-3.1 - Hotfix (SemanticChunker와 패턴 통합)

✅ P0-3.1 긴급 수정:
1. SemanticChunker와 완전히 동일한 패턴 사용
2. 공백/특수문자 허용 강화
3. 이중 검증 로직 유지

Author: 마창수산팀 + GPT 피드백 반영
Date: 2025-11-13
Version: Phase 0.4.0 P0-3.1
"""

import re
import logging
from typing import Dict, Set, List
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pdf_text_layer(pdf_path: str) -> str:
    """
    PDF 텍스트 레이어 추출 (VLM 거치지 않음)
    
    Args:
        pdf_path: PDF 파일 경로
    
    Returns:
        순수 텍스트
    """
    try:
        import pypdfium2 as pdfium
        
        pdf = pdfium.PdfDocument(pdf_path)
        text_parts = []
        
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            text_parts.append(text)
        
        full_text = '\n'.join(text_parts)
        logger.info(f"   📄 PDF 텍스트 추출 완료: {len(full_text)}자")
        
        return full_text
    
    except Exception as e:
        logger.error(f"   ❌ PDF 텍스트 추출 실패: {e}")
        return ""


class DualQAGate:
    """
    PDF 원본 vs VLM 결과 이중 검증
    
    ✅ P0-3.1: SemanticChunker와 완전히 동일한 패턴 사용
    """
    
    # ============================================
    # ✅ P0-3.1: SemanticChunker와 완전히 동일한 패턴
    # ============================================
    NUM = r'\d+(?:의\d+)?'
    
    # Strict: 제N조( 형식
    # ✅ SemanticChunker와 동일: 앞에 공백/특수문자 허용
    ARTICLE_STRICT = re.compile(
        rf'^[\s⟨<\[]*(제\s*{NUM}\s*조)\s*\(',
        re.MULTILINE
    )
    
    # Loose: 제N조 단독
    # ✅ SemanticChunker와 동일: 앞에 공백/특수문자 허용
    ARTICLE_LOOSE = re.compile(
        rf'^[\s⟨<\[]*(제\s*{NUM}\s*조)(?=\s|$)',
        re.MULTILINE
    )
    
    def __init__(self):
        logger.info("✅ DualQAGate Phase 0.4.0 P0-3.1 초기화 (Hotfix)")
        logger.info("   🔬 PDF vs VLM 이중 검증 (SemanticChunker 패턴 통합)")
    
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
        
        # 7. 로그 출력
        logger.info("✅ DualQA 검증 완료:")
        logger.info(f"   📊 PDF 조문: {len(pdf_articles)}개")
        logger.info(f"   📊 VLM 조문: {len(vlm_articles)}개")
        logger.info(f"   📊 일치: {len(matched)}개")
        logger.info(f"   📊 매칭률: {match_rate:.1%}")
        
        if missing_in_vlm:
            logger.error(f"   ❌ VLM 누락: {sorted(missing_in_vlm)}")
            logger.error(f"      → PDF에는 있지만 VLM이 추출하지 못한 조문입니다!")
        
        if extra_in_vlm:
            logger.warning(f"   ⚠️ VLM 추가: {sorted(extra_in_vlm)}")
            logger.warning(f"      → VLM이 만들어낸 조문입니다 (PDF 원본에 없음)")
        
        if result['qa_flags']:
            logger.error(f"   🚨 QA 플래그: {result['qa_flags']}")
            logger.error(f"      → 원문 불일치! 수동 검수 필요합니다!")
        else:
            logger.info("   ✅ 원문 일치 (QA 통과)")
        
        return result
    
    def _extract_article_headers(self, text: str, source: str = "") -> Set[str]:
        """
        조문 헤더 추출 (SemanticChunker와 완전히 동일한 로직)
        
        Args:
            text: 텍스트
            source: 소스명 (로깅용)
        
        Returns:
            조문 헤더 집합 (예: {'제1조', '제2조', ...})
        """
        headers = set()
        
        # 1. Strict 패턴 (제N조( 형식)
        for m in self.ARTICLE_STRICT.finditer(text):
            matched = m.group(1).strip()
            # 공백 정규화 (제 1 조 → 제1조)
            matched = re.sub(r'\s+', '', matched)
            headers.add(matched)
        
        # 2. Loose 패턴 (제N조 단독)
        for m in self.ARTICLE_LOOSE.finditer(text):
            matched = m.group(1).strip()
            # 공백 정규화
            matched = re.sub(r'\s+', '', matched)
            
            # ✅ 인라인 참조 필터링 (SemanticChunker와 동일)
            pos = m.start()
            
            # 패턴 1: "제N조제M항" (조문 참조)
            context_start = max(0, pos - 20)
            context_end = min(len(text), pos + len(matched) + 20)
            context = text[context_start:context_end]
            
            if re.search(r'제\d+조제\d+[항호]', context):
                continue  # 인라인 참조 제외
            
            # 패턴 2: "제N조 및 제M조" (나열)
            if re.search(r'제\d+조\s*[및과]\s*제\d+조', context):
                continue  # 나열 제외
            
            # 패턴 3: 문장 중간 (앞에 한글이 바로 붙음)
            if pos > 0 and re.match(r'[가-힣]', text[pos-1]):
                continue  # 문장 중간 제외
            
            headers.add(matched)
        
        # 3. 로그 출력
        headers_list = sorted(headers)
        logger.info(f"   📖 {source} 조문 헤더: {len(headers_list)}개")
        if headers_list:
            logger.info(f"      샘플: {headers_list[:5]}")
        
        return headers
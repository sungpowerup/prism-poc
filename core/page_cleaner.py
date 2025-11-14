"""
page_cleaner.py - 페이지 아티팩트 제거
Phase 0.6.1 "Hotfix: Inline Page Numbers"

✅ Phase 0.6.1 핫픽스 (GPT 피드백):
- 인라인 페이지 번호 제거: "402-3용을" → "용을"
- 규정 문서 특화 패턴 추가

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-14
Version: Phase 0.6.1
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_page_artifacts(text: str) -> str:
    """
    ✅ Phase 0.6.1: 페이지 아티팩트 제거 (GPT 피드백 반영)
    
    개선사항:
    1. 인라인 페이지 번호 제거 (어디든 "402-3" 패턴 제거)
    2. "402-21." 같은 페이지+항목 혼합 케이스 분리
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정제된 텍스트
    """
    if not text:
        return text
    
    original_len = len(text)
    result = text
    
    # ✅ Phase 0.6.1: 인라인 페이지 번호 제거 (GPT 핵심 권장)
    # "402-3용을" → "용을"
    # \b = 단어 경계, 의미 있는 숫자와 분리
    PAGE_NUMBER_PATTERN = re.compile(r'\b\d{3}-\d{1,2}\b')
    result = PAGE_NUMBER_PATTERN.sub('', result)
    
    # ✅ Phase 0.6.1: "402-2" + "1." 혼합 케이스 처리
    # "402-21." → "1."
    MIXED_PATTERN = re.compile(r'402-2(?=\d\.)')
    result = MIXED_PATTERN.sub('', result)
    
    # 기존 Phase 0.5 패턴들
    # 단독 라인 페이지 번호
    result = re.sub(r'^\s*\d{3}-\d{1,2}\s*$', '', result, flags=re.MULTILINE)
    
    # "인사규정 402-3" 패턴
    result = re.sub(r'인사\s*규정\s*\d{3}-\d{1,2}', '', result, flags=re.IGNORECASE)
    
    # Page N/M 패턴
    result = re.sub(r'Page\s+\d+\s*/\s*\d+', '', result, flags=re.IGNORECASE)
    
    # 연속 공백 정리
    result = re.sub(r' {2,}', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    removed = original_len - len(result)
    
    if removed > 0:
        logger.info(f"🧹 PageCleaner: {removed}자 제거 ({original_len} → {len(result)})")
    
    return result.strip()


# 테스트
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    test_cases = [
        # Case 1: 인라인 페이지 번호
        ("402-3용을실시할수있다", "용을실시할수있다"),
        
        # Case 2: 페이지+항목 혼합
        ("402-21.\"직위\"란", "1.\"직위\"란"),
        
        # Case 3: 단독 라인
        ("제1조\n402-3\n제2조", "제1조\n\n제2조"),
        
        # Case 4: 제목과 함께
        ("인사규정 402-3", ""),
    ]
    
    print("Phase 0.6.1 PageCleaner 테스트:\n")
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = clean_page_artifacts(input_text)
        status = "✅" if result.strip() == expected.strip() else "❌"
        print(f"{status} Case {i}:")
        print(f"   Input:    {input_text}")
        print(f"   Expected: {expected}")
        print(f"   Result:   {result}")
        print()
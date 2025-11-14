"""
page_cleaner.py - 페이지 아티팩트 제거
Phase 0.5 "Polishing"

GPT 설계 기반: 페이지 번호, 문서 헤더 제거

Author: 이서영 (Backend Lead) + GPT 설계
Date: 2025-11-14
Version: Phase 0.5
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_page_artifacts(text: str) -> str:
    """
    페이지 아티팩트 제거 (함수형)
    
    ✅ 제거 대상:
    1. 페이지 번호: "402-3", "105-12" (단독 라인)
    2. 문서 제목: "인사규정" (단독 라인)
    3. 조합형: "인사규정 402-3" (한 줄)
    4. 인라인: 본문 중간에 섞인 "인사규정 402-3"
    
    Args:
        text: 원본 PDF 텍스트
    
    Returns:
        정제된 텍스트
    """
    if not text:
        return text
    
    original_len = len(text)
    
    # 1. 페이지 번호 라인 제거 (단독)
    # 예: "402-3"
    text = re.sub(r'^\s*\d{3}-\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 2. 문서 제목 라인 제거 (단독)
    # 예: "인사규정"
    text = re.sub(r'^\s*인사\s*규정\s*$', '', text, flags=re.MULTILINE)
    
    # 3. 문서 제목 + 페이지 번호 (한 줄)
    # 예: "인사규정 402-3"
    text = re.sub(r'^\s*인사\s*규정\s*\d{3}-\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 4. 인라인 페이지 번호 제거
    # 예: "...채\n인사규정\n402-3\n용을..." → "...채용을..."
    # 주의: 조문 번호(제1조)는 보존!
    text = re.sub(r'인사\s*규정\s*\d{3}-\d+', '', text)
    
    # 5. 공백 정리
    text = re.sub(r'\n{3,}', '\n\n', text)  # 3줄 이상 → 2줄
    text = re.sub(r' {2,}', ' ', text)  # 2칸 이상 → 1칸
    text = text.strip()
    
    cleaned_len = len(text)
    removed = original_len - cleaned_len
    
    logger.info(f"🧹 PageCleaner: {removed}자 제거 ({original_len} → {cleaned_len})")
    
    return text


# ============================================
# 클래스형 (옵션)
# ============================================

class PageArtifactCleaner:
    """
    페이지 아티팩트 제거 (클래스형)
    
    함수형 clean_page_artifacts()를 래핑한 클래스
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PageArtifactCleaner 초기화")
    
    def clean(self, text: str) -> str:
        """
        페이지 아티팩트 제거
        
        Args:
            text: 원본 PDF 텍스트
        
        Returns:
            정제된 텍스트
        """
        return clean_page_artifacts(text)


# ============================================
# 테스트
# ============================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 케이스
    test_text = """
    기본정신
    
    이 규정은 한국농어촌공사 직원의 인사관리에 관한 사항을 정함으로써...
    
    인사규정
    402-3
    
    제1조(목적) 이 규정은...
    
    인사규정 402-4
    
    제2조(적용범위) 이 규정은...
    """
    
    print("=" * 60)
    print("원본:")
    print("=" * 60)
    print(test_text)
    
    print("\n" + "=" * 60)
    print("정제 후:")
    print("=" * 60)
    
    cleaned = clean_page_artifacts(test_text)
    print(cleaned)
    
    print("\n" + "=" * 60)
    print("통계:")
    print("=" * 60)
    print(f"원본: {len(test_text)}자")
    print(f"정제: {len(cleaned)}자")
    print(f"제거: {len(test_text) - len(cleaned)}자")
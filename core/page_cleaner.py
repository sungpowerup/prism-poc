"""
page_cleaner.py - 페이지 아티팩트 제거
Phase 0.5 "Polishing"

GPT 설계 기반: 페이지 번호, 문서 헤더 제거

Author: 이서영 (Backend Lead) + GPT 설계
Date: 2025-11-13
Version: Phase 0.5
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class PageArtifactCleaner:
    """
    PDF 텍스트 레이어에서 페이지 번호/헤더 제거
    
    ✅ 제거 대상:
    1. 페이지 번호: "402-3", "105-12"
    2. 문서 제목: "인사규정"
    3. 조합형: "인사규정 402-3"
    """
    
    # 1. 페이지 번호 라인 (단독)
    PAGE_NUM_LINE = re.compile(r'^\s*\d{3}-\d+\s*$', re.MULTILINE)
    
    # 2. 문서 제목 라인 (단독)
    DOC_TITLE_LINE = re.compile(r'^\s*(인사\s*규정)\s*$', re.MULTILINE)
    
    # 3. 문서 제목 + 페이지 번호 (한 줄)
    DOC_TITLE_WITH_PAGE = re.compile(
        r'^\s*(인사\s*규정)\s*\d{3}-\d+\s*$',
        re.MULTILINE
    )
    
    # 4. 인라인 페이지 번호 (본문 중간에 섞인 경우)
    INLINE_PAGE_NUM = re.compile(r'(인사\s*규정)\s*\d{3}-\d+')
    
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
        original_len = len(text)
        
        # 1. 라인 단위 제거
        text = self._remove_line_artifacts(text)
        
        # 2. 인라인 제거
        text = self._remove_inline_artifacts(text)
        
        cleaned_len = len(text)
        removed = original_len - cleaned_len
        
        logger.info(f"✅ 페이지 아티팩트 제거 완료:")
        logger.info(f"   원본: {original_len}자")
        logger.info(f"   제거: {removed}자")
        logger.info(f"   결과: {cleaned_len}자")
        
        return text
    
    def _remove_line_artifacts(self, text: str) -> str:
        """라인 단위 아티팩트 제거"""
        lines = text.splitlines()
        cleaned = []
        
        removed_count = 0
        
        for line in lines:
            # 페이지 번호 라인
            if self.PAGE_NUM_LINE.match(line):
                removed_count += 1
                logger.debug(f"   제거 (페이지번호): {line.strip()}")
                continue
            
            # 문서 제목 라인
            if self.DOC_TITLE_LINE.match(line):
                removed_count += 1
                logger.debug(f"   제거 (문서제목): {line.strip()}")
                continue
            
            # 문서 제목 + 페이지 번호
            if self.DOC_TITLE_WITH_PAGE.match(line):
                removed_count += 1
                logger.debug(f"   제거 (제목+번호): {line.strip()}")
                continue
            
            cleaned.append(line)
        
        logger.info(f"   라인 제거: {removed_count}개")
        
        return '\n'.join(cleaned)
    
    def _remove_inline_artifacts(self, text: str) -> str:
        """인라인 아티팩트 제거"""
        
        # "인사규정 402-3" → "인사규정"
        before = text
        text = self.INLINE_PAGE_NUM.sub(r'\1', text)
        
        if text != before:
            logger.info(f"   인라인 제거: {len(before) - len(text)}자")
        
        return text


# 편의 함수
def clean_page_artifacts(text: str) -> str:
    """
    페이지 아티팩트 제거 (편의 함수)
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정제된 텍스트
    """
    cleaner = PageArtifactCleaner()
    return cleaner.clean(text)


# 테스트
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    sample = """
인사규정
402-1

제1조(목적) 이 규정은 한국농어촌공사 직원에게 적용할 인사관리의 기준을 정하여
합리적이고 적정한 인사관리를 기하게 하는 것을 목적으로 한다.

인사규정
402-2

제2조(적용범위) 직원의 인사관리는 법령 및 정관에 정한 것을 제외하고는
이 규정에 따른다.

제3조(직원 등의 구분) ① 직원은 일반직, 별정직으로 구분한다.
    """
    
    result = clean_page_artifacts(sample)
    
    print("\n=== 정제 결과 ===")
    print(result)

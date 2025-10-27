"""
core/typo_normalizer.py
PRISM Phase 5.6.0 - Typo Normalizer

목적: OCR 오탈자 및 용어 표준화

개선:
- 규정 용어 사전 적용
- OCR 오류 패턴 교정
- 특수문자 정규화

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.6.0
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 5.6.0 오탈자 정규화
    
    목적:
    - OCR 오탈자 교정
    - 규정 용어 표준화
    - 특수문자 정규화
    
    처리 순서:
    1. 규정 용어 사전 적용
    2. OCR 오류 패턴 교정
    3. 특수문자 정규화
    """
    
    # 규정 용어 사전
    STATUTE_TERMS = {
        # OCR 오탈자
        '임용·용훈': '임용권',
        '성과계재선발자': '성과개선대상자',
        '공급인사위원회': '상급인사위원회',
        '전문·전종': '전문직종',
        '시행전반': '채용전반',
        
        # 띄어쓰기 오류
        '직권에 임용': '직원의 임용',
        '수입임용': '수습임용',
        '채용소재지검사': '채용신체검사',
        '징계처분결정': '확정판결',
        
        # 한자 오류
        '복권': '복권',
        '집행유예': '집행유예',
        '선고유예': '선고유예',
    }
    
    # OCR 오류 패턴
    OCR_PATTERNS = [
        # 숫자 오인식
        (r'제(\d+)3조', r'제\1조'),  # 제73조 → 제7조
        (r'제(\d+)4조', r'제\1조'),
        
        # 특수문자 오인식
        (r'·', '·'),  # 중점 통일
        (r'‧', '·'),
        (r'•', '·'),
        
        # 괄호 오인식
        (r'（', '('),
        (r'）', ')'),
        
        # 날짜 형식 통일
        (r'(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})', r'\1.\2.\3'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TypoNormalizer v5.6.0 초기화 완료")
        logger.info(f"   📖 규정 용어 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        오탈자 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        corrections = 0
        
        # 1) 규정 용어 사전 적용 (규정 모드만)
        if doc_type == 'statute':
            content, term_corrections = self._apply_statute_terms(content)
            corrections += term_corrections
        
        # 2) OCR 오류 패턴 교정
        content, pattern_corrections = self._apply_ocr_patterns(content)
        corrections += pattern_corrections
        
        # 3) 특수문자 정규화
        content = self._normalize_special_chars(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정")
        return content
    
    def _apply_statute_terms(self, content: str) -> tuple:
        """
        규정 용어 사전 적용
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 개수)
        """
        corrections = 0
        
        for wrong, correct in self.STATUTE_TERMS.items():
            if wrong in content:
                count = content.count(wrong)
                content = content.replace(wrong, correct)
                corrections += count
                if count > 0:
                    logger.debug(f"      용어 교정: '{wrong}' → '{correct}' ({count}회)")
        
        return content, corrections
    
    def _apply_ocr_patterns(self, content: str) -> tuple:
        """
        OCR 오류 패턴 교정
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 개수)
        """
        corrections = 0
        
        for pattern, replacement in self.OCR_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                corrections += len(matches)
                logger.debug(f"      패턴 교정: {len(matches)}회")
        
        return content, corrections
    
    def _normalize_special_chars(self, content: str) -> str:
        """
        특수문자 정규화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 중점 통일
        content = content.replace('‧', '·')
        content = content.replace('•', '·')
        
        # 괄호 통일
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        
        # 따옴표 통일
        content = content.replace('"', '"')
        content = content.replace('"', '"')
        content = content.replace(''', "'")
        content = content.replace(''', "'")
        
        logger.debug("      특수문자 정규화 완료")
        return content
    
    def add_custom_term(self, wrong: str, correct: str):
        """
        사용자 정의 용어 추가
        
        Args:
            wrong: 잘못된 표현
            correct: 올바른 표현
        """
        self.STATUTE_TERMS[wrong] = correct
        logger.info(f"   ✅ 사용자 용어 추가: '{wrong}' → '{correct}'")
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """
        정규화 통계
        
        Args:
            original: 원본 텍스트
            normalized: 정규화된 텍스트
        
        Returns:
            통계 정보
        """
        corrections = 0
        
        # 용어 교정 개수
        for wrong in self.STATUTE_TERMS.keys():
            corrections += original.count(wrong)
        
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'corrections': corrections
        }

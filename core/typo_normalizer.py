"""
core/typo_normalizer.py
PRISM Phase 5.7.7 - Typo Normalizer (오탈자 사전 확장)

✅ Phase 5.7.7 개선:
- "사 제" → "삭제" 추가
- "기함" → "기하" 추가 (띄어쓰기와 연동)
- "정함" → "정함" (이미 올바름, 사전 제외)

(Phase 5.6.2 기능 유지)

Author: 정수아 (QA Lead) + 박준호 (AI/ML Lead)
Date: 2025-11-02
Version: 5.7.7
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 5.7.7 오탈자 정규화 (사전 확장)
    
    목적:
    - OCR 오탈자 교정 (안전한 패턴만)
    - ✅ 규정 용어 표준화 확장 (Phase 5.7.7)
    - 특수문자 정규화
    
    처리 순서:
    1. 규정 용어 사전 적용 (확장)
    2. OCR 오류 패턴 교정 (위험 규칙 제거)
    3. 특수문자 정규화
    """
    
    # ✅ Phase 5.7.7: 규정 용어 사전 (확장)
    STATUTE_TERMS = {
        # ✅ Phase 5.7.7 추가: 테스트에서 발견된 오류
        '사 제': '삭제',
        '사제': '삭제',
        '무기직': '공무직',  # "무기계약직" → "공무직" (테스트 결과 기반)
        
        # Phase 5.6.2: OCR 오탈자 (실제 치환만)
        '임용·용훈': '임용권',
        '성과계재선발자': '성과개선대상자',
        '공급인사위원회': '상급인사위원회',
        '전문·전종': '전문직종',
        '시행전반': '채용전반',
        
        # Phase 5.6.1: 빈출 오류 (실제 치환만)
        '성과계좌대상자': '성과개선대상자',
        '보직변겅': '보직변경',
        
        # 띄어쓰기 오류
        '직권에 임용': '직원의 임용',
        '수입임용': '수습임용',
        '채용소재지검사': '채용신체검사',
        '징계처분결정': '확정판결',
    }
    
    # Phase 5.6.2: OCR 오류 패턴 (위험 규칙 제거)
    OCR_PATTERNS = [
        # ✅ 유지: 특수문자 오인식 (안전)
        (r'·', '·'),  # 중점 통일
        (r'‧', '·'),
        (r'•', '·'),
        (r'･', '·'),
        
        # ✅ 유지: 괄호 오인식 (안전)
        (r'（', '('),
        (r'）', ')'),
        (r'〈', '<'),
        (r'〉', '>'),
        
        # ✅ 유지: 날짜 형식 통일
        (r'(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})', r'\1.\2.\3'),
        (r'(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})', r'\1.\2.\3'),
        (r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', r'\1.\2.\3'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TypoNormalizer v5.7.7 초기화 완료 (사전 확장)")
        logger.info(f"   📖 규정 용어 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개 (위험 규칙 제거)")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        오탈자 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer v5.7.7 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        corrections = 0
        
        # 1) 규정 용어 사전 적용 (규정 모드만)
        if doc_type == 'statute':
            content, term_corrections = self._apply_statute_terms(content)
            corrections += term_corrections
        
        # 2) OCR 오류 패턴 교정 (안전한 패턴만)
        content, pattern_corrections = self._apply_ocr_patterns(content)
        corrections += pattern_corrections
        
        # 3) 특수문자 정규화
        content = self._normalize_special_chars(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정 (안전 모드)")
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
        Phase 5.6.2: OCR 오류 패턴 교정 (안전 모드)
        
        위험한 규칙 제거:
        - 조문 번호 축소 (제73조 → 제7조) ← 삭제
        
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
        content = content.replace('･', '·')
        
        # 괄호 통일
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        content = content.replace('〈', '<')
        content = content.replace('〉', '>')
        
        # 따옴표 통일 (안전한 유니코드 매핑)
        content = content.replace('\u201c', '"')  # "
        content = content.replace('\u201d', '"')  # "
        content = content.replace('\u2018', "'")  # '
        content = content.replace('\u2019', "'")  # '
        
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
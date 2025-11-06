"""
core/typo_normalizer.py
PRISM Phase 0.2 Hotfix - Typo Normalizer with Enhanced Header Normalization

✅ Phase 0.2 긴급 수정:
1. 조문 헤더 정규화 강화 (Markdown ### 지원)
2. 특수공백 전처리 (NBSP, 전각공백)
3. "제N조의M" 패턴 지원
4. 전각 숫자/괄호 정규화

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import re
import logging
from typing import Dict, Any, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 0.2 오탈자 정규화 (조문 헤더 강화)
    
    ✅ Phase 0.2 개선:
    - Markdown 헤더 (###) 포함 정규화
    - 특수공백 (NBSP \u00A0, 전각 \u3000) 전처리
    - "조의N" 패턴 추가 지원
    - raw string으로 SyntaxWarning 해결
    """
    
    # ✅ Phase 0.2: 규정 용어 사전 (확장)
    STATUTE_TERMS = OrderedDict([
        ('성과계재단상자', '성과개선대상자'),
        ('공금관리위원회', '상급인사위원회'),
        ('임용훈', '임용권'),
        ('상금인사위원회', '상급인사위원회'),
        ('채용소재결과', '채용신체검사'),
        ('공공기관 및 국민권익위원회', '부패방지 및 국민권익위원회'),
        ('주택법령', '성폭력범죄'),
        ('징계결정', '확정판결'),
        ('제 정', '제정'),
        ('제 1 조', '제1조'),
        ('제 2 조', '제2조'),
        ('제 3 조', '제3조'),
        ('제 4 조', '제4조'),
        ('제 5 조', '제5조'),
        ('제 6 조', '제6조'),
        ('제 7 조', '제7조'),
        ('제 8 조', '제8조'),
        ('제 9 조', '제9조'),
        ('제 1 장', '제1장'),
        ('제 2 장', '제2장'),
        ('제 3 장', '제3장'),
        ('직원에 게', '직원에게'),
        ('부여할 수있는', '부여할 수 있는'),
        ('가 진다', '가진다'),
        ('에 게', '에게'),
        ('에서', '에서'),
    ])
    
    # ✅ Phase 0.2: OCR 패턴 (raw string)
    OCR_PATTERNS = [
        (r'(\d+)\.(\d+)\.(\d+)', r'\1.\2.\3'),  # 날짜
        (r'제(\d+)조 의 (\d+)', r'제\1조의\2'),  # 조의N
        (r'제 (\d+) 조', r'제\1조'),            # 제N조
        (r'제 (\d+) 장', r'제\1장'),            # 제N장
        (r'([가-힣])\.', r'\1. '),              # 호 리스트
        (r'(\d+)\.', r'\1. '),                  # 번호 리스트
        (r'\s+\(', r'('),                       # 괄호 전 공백
        (r'\)\s+', r') '),                      # 괄호 후 공백
        (r'「\s+', r'「'),                      # 법령 인용 시작
        (r'\s+」', r'」'),                      # 법령 인용 끝
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TypoNormalizer Phase 0.2 초기화 완료")
        logger.info(f"   📖 규정 용어 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
        logger.info("   🔧 조문 헤더 정규화: Markdown ### 지원")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        ✅ Phase 0.2: 오탈자 정규화 (조문 헤더 강화)
        
        Args:
            content: 원본 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer Phase 0.2 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        corrections = 0
        
        # 0) ✅ Phase 0.2: 특수공백 전처리
        content = self._normalize_special_spaces(content)
        
        # 1) ✅ Phase 0.2: statute 모드 전용 - 조문 헤더 정규화
        if doc_type == 'statute':
            content, header_corrections = self._normalize_statute_headers(content)
            corrections += header_corrections
            logger.info(f"   🔧 조문 헤더 정규화 완료: {header_corrections}회")
        
        # 2) 규정 용어 사전
        content, term_corrections = self._apply_statute_terms(content)
        corrections += term_corrections
        
        # 3) OCR 패턴
        content, ocr_corrections = self._apply_ocr_patterns(content)
        corrections += ocr_corrections
        
        # 4) 특수문자 정규화
        content = self._normalize_special_chars(content)
        
        # 5) 전각 숫자/괄호 정규화
        content = self._normalize_fullwidth(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정")
        logger.info(f"      길이 변화: {original_len} → {normalized_len} ({normalized_len - original_len:+d})")
        
        return content
    
    def _normalize_special_spaces(self, content: str) -> str:
        """
        ✅ Phase 0.2: 특수공백 전처리
        
        대상:
        - NBSP (\u00A0)
        - 전각공백 (\u3000)
        - 탭 (\t)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            공백 정규화된 텍스트
        """
        # 모든 특수공백을 일반 공백으로 통합
        content = re.sub(r'[ \t\u00A0\u3000]+', ' ', content)
        
        return content
    
    def _normalize_statute_headers(self, content: str) -> Tuple[str, int]:
        """
        ✅ Phase 0.2: statute 모드 전용 조문 헤더 정규화
        
        목표:
        - "### 제 1 조" → "### 제1조"
        - "제 7 조의 2" → "제7조의2"
        - "제 1 장" → "제1장"
        
        전략:
        - Markdown 헤더 (###) 포함
        - 라인 시작 anchor (^) 사용 (본문 보호)
        - "조의N" 패턴 우선 처리
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (정규화된 텍스트, 교정 횟수)
        """
        corrections = 0
        
        # 1) "제N조의M" 패턴 (우선순위 높음)
        # "### 제 7 조의 2" → "### 제7조의2"
        pattern_jo_ui = re.compile(
            r'^(#{0,6}\s*)제\s+(\d+)\s*조\s*의\s*(\d+)',
            re.MULTILINE
        )
        
        def replace_jo_ui(match):
            nonlocal corrections
            corrections += 1
            header = match.group(1) if match.group(1) else ''
            num1 = match.group(2)
            num2 = match.group(3)
            return f'{header}제{num1}조의{num2}'
        
        content = pattern_jo_ui.sub(replace_jo_ui, content)
        
        # 2) "제N조" 패턴
        # "### 제 1 조" → "### 제1조"
        pattern_jo = re.compile(
            r'^(#{0,6}\s*)제\s+(\d+)\s*조',
            re.MULTILINE
        )
        
        def replace_jo(match):
            nonlocal corrections
            corrections += 1
            header = match.group(1) if match.group(1) else ''
            num = match.group(2)
            return f'{header}제{num}조'
        
        content = pattern_jo.sub(replace_jo, content)
        
        # 3) "제N장" 패턴
        # "### 제 1 장" → "### 제1장"
        pattern_jang = re.compile(
            r'^(#{0,6}\s*)제\s+(\d+)\s*장',
            re.MULTILINE
        )
        
        def replace_jang(match):
            nonlocal corrections
            corrections += 1
            header = match.group(1) if match.group(1) else ''
            num = match.group(2)
            return f'{header}제{num}장'
        
        content = pattern_jang.sub(replace_jang, content)
        
        # 4) 헤더 없는 조문에 ### 추가 (선택적)
        # "제1조" → "### 제1조" (라인 시작에만 적용)
        pattern_no_header = re.compile(
            r'^(제\d+조(?:의\d+)?)',
            re.MULTILINE
        )
        
        def add_header(match):
            # 이미 헤더가 있으면 스킵
            if match.string[max(0, match.start()-4):match.start()].strip().startswith('#'):
                return match.group(0)
            return f'### {match.group(1)}'
        
        content = pattern_no_header.sub(add_header, content)
        
        return content, corrections
    
    def _apply_statute_terms(self, content: str) -> Tuple[str, int]:
        """규정 용어 사전 적용"""
        corrections = 0
        
        for wrong, correct in self.STATUTE_TERMS.items():
            if wrong in content:
                count = content.count(wrong)
                content = content.replace(wrong, correct)
                corrections += count
                
                if count > 0:
                    logger.debug(f"      용어 교정: '{wrong}' → '{correct}' ({count}회)")
        
        return content, corrections
    
    def _apply_ocr_patterns(self, content: str) -> Tuple[str, int]:
        """OCR 패턴 교정"""
        corrections = 0
        
        for pattern, replacement in self.OCR_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                corrections += len(matches)
        
        return content, corrections
    
    def _normalize_special_chars(self, content: str) -> str:
        """특수문자 정규화"""
        # 중점
        content = content.replace('‧', '·')
        content = content.replace('•', '·')
        content = content.replace('･', '·')
        
        # 괄호
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        content = content.replace('〈', '<')
        content = content.replace('〉', '>')
        
        # 따옴표
        content = content.replace('\u201c', '"')
        content = content.replace('\u201d', '"')
        content = content.replace('\u2018', "'")
        content = content.replace('\u2019', "'")
        
        return content
    
    def _normalize_fullwidth(self, content: str) -> str:
        """
        ✅ Phase 0.2: 전각 숫자/괄호 정규화
        
        전각 → 반각 변환:
        - ０-９ → 0-9
        - （） → ()
        
        Args:
            content: 원본 텍스트
        
        Returns:
            반각 정규화된 텍스트
        """
        # 전각 숫자 → 반각
        fullwidth_digits = '０１２３４５６７８９'
        halfwidth_digits = '0123456789'
        trans_table = str.maketrans(fullwidth_digits, halfwidth_digits)
        content = content.translate(trans_table)
        
        # 전각 괄호 → 반각
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        
        return content
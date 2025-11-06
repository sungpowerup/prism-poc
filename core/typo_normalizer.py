"""
core/typo_normalizer.py
PRISM Phase 0 Hotfix - Typo Normalizer with Statute Header Normalization

✅ Phase 0 긴급 수정:
1. statute 모드에서만 조문 헤더 정규화
2. 라인 시작 anchor 기반 패턴 (본문 보호)
3. "제 1 조" → "제1조", "제 1 장" → "제1장" 통일

Author: 황태민 (DevOps Lead) + 미송 제안
Date: 2025-11-06
Version: Phase 0 Hotfix
"""

import re
import logging
from typing import Dict, Any, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 0 오탈자 정규화 (statute 헤더 정규화)
    
    ✅ Phase 0 개선:
    - statute 모드 전용 헤더 정규화
    - 본문 보호 (라인 시작만)
    - "제 1 조" → "제1조" 완전 통일
    """
    
    # 규정 용어 사전 (OrderedDict - Longest-First)
    STATUTE_TERMS = OrderedDict([
        # 복합 패턴 (긴 것부터)
        ('1명의직원에 게부여할 수있는', '1명의 직원에게 부여할 수 있는'),
        ('직원에 게부여할 수있는', '직원에게 부여할 수 있는'),
        ('부여할 수있는', '부여할 수 있는'),
        ('1명의직원에 게', '1명의 직원에게'),
        ('직원에 게', '직원에게'),
        
        # OCR 오탈자
        ('성과계재단상자', '성과개선대상자'),
        ('공금관리위원회', '상급인사위원회'),
        ('임용·용훈', '임용권'),
        ('성과계재선발자', '성과개선대상자'),
        ('공급인사위원회', '상급인사위원회'),
        ('전문·전종', '전문직종'),
        ('시행전반', '채용전반'),
        
        # 띄어쓰기 오류
        ('직권에 임용', '직원의 임용'),
        ('수입임용', '수습임용'),
        ('채용소재지검사', '채용신체검사'),
        ('징계처분결정', '확정판결'),
        ('직무의종류', '직무의 종류'),
        ('그밖에', '그 밖에'),
        ('가 진다', '가진다'),
        ('에 게', '에게'),
        ('에 서', '에서'),
        ('로 부터', '로부터'),
        ('사 제', '삭제'),
        ('사제', '삭제'),
        ('무기직', '공무직'),
        
        # 단순 패턴
        ('수있는', '수 있는'),
        ('수없는', '수 없는'),
    ])
    
    # OCR 오류 패턴
    OCR_PATTERNS = [
        # 특수문자
        (r'·', '·'),
        (r'‧', '·'),
        (r'•', '·'),
        (r'･', '·'),
        
        # 괄호
        (r'（', '('),
        (r'）', ')'),
        (r'〈', '<'),
        (r'〉', '>'),
        
        # 날짜 통일
        (r'(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})', r'\1.\2.\3'),
        (r'(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})', r'\1.\2.\3'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TypoNormalizer Phase 0 초기화 완료")
        logger.info(f"   📖 규정 용어 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        ✅ Phase 0: 오탈자 정규화 + statute 헤더 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer Phase 0 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        corrections = 0
        
        # 1) 규정 용어 사전 (statute 모드만)
        if doc_type == 'statute':
            content, term_corrections = self._apply_statute_terms(content)
            corrections += term_corrections
        
        # 2) OCR 패턴
        content, pattern_corrections = self._apply_ocr_patterns(content)
        corrections += pattern_corrections
        
        # 3) 특수문자 정규화
        content = self._normalize_special_chars(content)
        
        # 4) ✅ Phase 0: statute 모드 전용 헤더 정규화
        if doc_type == 'statute':
            content, header_corrections = self._normalize_statute_headers(content)
            corrections += header_corrections
            logger.info(f"   🔧 조문 헤더 정규화 완료: {header_corrections}회")
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정")
        logger.info(f"      길이 변화: {original_len} → {normalized_len} ({normalized_len - original_len:+d})")
        
        return content
    
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
    
    def _normalize_statute_headers(self, content: str) -> Tuple[str, int]:
        """
        ✅ Phase 0: statute 모드 전용 조문 헤더 정규화
        
        목표:
        - "제 1 조" → "제1조"
        - "제 1 장" → "제1장"
        - "제 7 조의 2" → "제7조의2"
        
        전략:
        - 라인 시작 anchor (^) 사용
        - 본문 "제1조에 따른..." 보호
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (정규화된 텍스트, 교정 개수)
        """
        corrections = 0
        
        # 패턴 1: "제 1 조의 2" → "제1조의2"
        before = content
        content = re.sub(
            r'^(#{0,3}\s*)제\s+(\d+)\s*조의\s*(\d+)',
            r'\1제\2조의\3',
            content,
            flags=re.MULTILINE
        )
        corrections += len(re.findall(r'^#{0,3}\s*제\s+\d+\s*조의\s*\d+', before, re.MULTILINE))
        
        # 패턴 2: "제 1 조" → "제1조"
        before = content
        content = re.sub(
            r'^(#{0,3}\s*)제\s+(\d+)\s*조',
            r'\1제\2조',
            content,
            flags=re.MULTILINE
        )
        corrections += len(re.findall(r'^#{0,3}\s*제\s+\d+\s*조', before, re.MULTILINE))
        
        # 패턴 3: "제 1 장" → "제1장"
        before = content
        content = re.sub(
            r'^(#{0,3}\s*)제\s+(\d+)\s*장',
            r'\1제\2장',
            content,
            flags=re.MULTILINE
        )
        corrections += len(re.findall(r'^#{0,3}\s*제\s+\d+\s*장', before, re.MULTILINE))
        
        # 패턴 4: "제 1 항" → "제1항" (선택적)
        before = content
        content = re.sub(
            r'^(#{0,3}\s*)제\s+(\d+)\s*항',
            r'\1제\2항',
            content,
            flags=re.MULTILINE
        )
        corrections += len(re.findall(r'^#{0,3}\s*제\s+\d+\s*항', before, re.MULTILINE))
        
        return content, corrections
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """정규화 통계"""
        corrections = 0
        
        for wrong in self.STATUTE_TERMS.keys():
            corrections += original.count(wrong)
        
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'corrections': corrections,
            'rules_count': len(self.STATUTE_TERMS)
        }
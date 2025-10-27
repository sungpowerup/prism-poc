"""
core/post_merge_normalizer.py
PRISM Phase 5.6.0 - Post-merge Normalizer

목적: 번호 목록 끊김 복구 및 문장 연속성 보장

개선:
- "1.\n직원은" → "1. 직원은"
- "(1)\n내용" → "(1) 내용"
- 조문 번호 뒤 공백 보존

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.6.0
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 5.6.0 문장 결속 정규화
    
    목적:
    - 번호 목록 끊김 복구
    - 문장 연속성 보장
    - RAG 문맥 파편화 제거
    
    처리 순서:
    1. 번호 목록 결속 (1. 2. 3.)
    2. 괄호 번호 결속 (1) (2) (3))
    3. 조문 번호 결속 (제○조, 제○항)
    4. 불필요한 공백 정리
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PostMergeNormalizer v5.6.0 초기화 완료")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        문장 결속 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입 ('statute', 'general', 'bus_diagram', 'table')
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        
        # 1) 숫자 목록 결속: "1.\n내용" → "1. 내용"
        content = self._normalize_numbered_lists(content)
        
        # 2) 괄호 번호 결속: "(1)\n내용" → "(1) 내용"
        content = self._normalize_parenthesized_numbers(content)
        
        # 3) 조문 번호 결속 (규정 모드만)
        if doc_type == 'statute':
            content = self._normalize_article_numbers(content)
        
        # 4) 불필요한 공백 정리
        content = self._clean_whitespace(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {normalized_len} 글자")
        return content
    
    def _normalize_numbered_lists(self, content: str) -> str:
        """
        숫자 목록 결속
        
        패턴:
        - "1.\n직원은" → "1. 직원은"
        - "1.\n\n직원은" → "1. 직원은"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # 1. 뒤에 공백 + 줄바꿈
        content = re.sub(r'(\d+\.)\s*\n+\s*', r'\1 ', content)
        
        logger.debug("      숫자 목록 결속 완료")
        return content
    
    def _normalize_parenthesized_numbers(self, content: str) -> str:
        """
        괄호 번호 결속
        
        패턴:
        - "(1)\n내용" → "(1) 내용"
        - "①\n내용" → "① 내용"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # (1) (2) (3) 형태
        content = re.sub(r'(\(\d+\))\s*\n+\s*', r'\1 ', content)
        
        # ① ② ③ 형태
        content = re.sub(r'([①-⑳])\s*\n+\s*', r'\1 ', content)
        
        logger.debug("      괄호 번호 결속 완료")
        return content
    
    def _normalize_article_numbers(self, content: str) -> str:
        """
        조문 번호 결속 (규정 모드)
        
        패턴:
        - "제1조\n(목적)" → "제1조 (목적)"
        - "제1항\n내용" → "제1항 내용"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # 제○조 + 괄호 제목
        content = re.sub(r'(제\s?\d+조)\s*\n+\s*(\([^)]+\))', r'\1 \2', content)
        
        # 제○항 + 내용
        content = re.sub(r'(제\s?\d+항)\s*\n+\s*', r'\1 ', content)
        
        # 제○호 + 내용
        content = re.sub(r'(제\s?\d+호)\s*\n+\s*', r'\1 ', content)
        
        logger.debug("      조문 번호 결속 완료")
        return content
    
    def _clean_whitespace(self, content: str) -> str:
        """
        불필요한 공백 정리
        
        패턴:
        - 연속 공백 → 단일 공백
        - 3개 이상 줄바꿈 → 2개 줄바꿈
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정리된 텍스트
        """
        # 연속 공백 → 단일 공백 (줄바꿈 제외)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 3개 이상 줄바꿈 → 2개 줄바꿈
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 줄 끝 공백 제거
        content = re.sub(r' +\n', '\n', content)
        
        logger.debug("      공백 정리 완료")
        return content
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """
        정규화 통계
        
        Args:
            original: 원본 텍스트
            normalized: 정규화된 텍스트
        
        Returns:
            통계 정보
        """
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'reduction': len(original) - len(normalized),
            'reduction_percent': (len(original) - len(normalized)) / max(1, len(original)) * 100
        }

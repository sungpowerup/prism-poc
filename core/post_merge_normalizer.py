"""
core/post_merge_normalizer.py
PRISM Phase 5.6.2 - Post-merge Normalizer (Emergency Patch)

🚨 Phase 5.6.2 긴급 패치:
- 한글 범위 수정 ([가-하] → [가-힣])
- 번호목록 결속 강화 (헤더/코드 보호)
- 조문 결속 보수화

(Phase 5.6.1 기능 유지)

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.6.2
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 5.6.2 문장 결속 정규화 (Emergency Patch)
    
    목적:
    - 번호 목록 끊김 완전 복구
    - 문장 연속성 보장
    - RAG 문맥 파편화 제거
    
    처리 순서:
    1. 숫자 목록 결속 (1. 2. 3.)
    2. 한글 순서 결속 (가. 나. 다.) ← 🚨 범위 수정
    3. 괄호 번호 결속 (1) (2) ①②)
    4. 조문 번호 결속 (제○조, 제○항)
    5. 불필요한 공백 정리
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PostMergeNormalizer v5.6.2 초기화 완료 (Emergency Patch)")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        문장 결속 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입 ('statute', 'general', 'bus_diagram', 'table')
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer v5.6.2 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        
        # 1) 숫자 목록 결속 강화: "1.\n내용" → "1. 내용"
        content = self._normalize_numbered_lists(content)
        
        # 🚨 2) 한글 순서 결속 (범위 수정): "가.\n내용" → "가. 내용"
        content = self._normalize_korean_lists(content)
        
        # 3) 괄호 번호 결속: "(1)\n내용" → "(1) 내용"
        content = self._normalize_parenthesized_numbers(content)
        
        # 4) 조문 번호 결속 (규정 모드만)
        if doc_type == 'statute':
            content = self._normalize_article_numbers(content)
        
        # 5) 불필요한 공백 정리 (보수적)
        content = self._clean_whitespace(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {normalized_len} 글자")
        return content
    
    def _normalize_numbered_lists(self, content: str) -> str:
        """
        🚨 Phase 5.6.2: 숫자 목록 결속 강화 (헤더 보호)
        
        패턴:
        - "1.\n직원은" → "1. 직원은"
        - "1.\n\n직원은" → "1. 직원은"
        
        보호:
        - 다음 줄이 #으로 시작하면 결속 안 함 (헤더)
        - 다음 줄이 ---로 시작하면 결속 안 함 (구분선)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        lines = content.split('\n')
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 숫자 목록 패턴 (1. 2. 3. ...)
            if re.match(r'^\d+\.\s*$', line.strip()):
                # 다음 줄 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # 헤더/구분선이면 결속 안 함
                    if next_line.startswith('#') or next_line.startswith('---') or next_line.startswith('```'):
                        result.append(line)
                    elif next_line:  # 평문이면 결속
                        result.append(line.strip() + ' ' + next_line)
                        i += 1  # 다음 줄 스킵
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
            
            i += 1
        
        logger.debug("      숫자 목록 결속 강화 완료")
        return '\n'.join(result)
    
    def _normalize_korean_lists(self, content: str) -> str:
        """
        🚨 Phase 5.6.2: 한글 순서 결속 (범위 수정)
        
        패턴:
        - "가.\n내용" → "가. 내용"
        - "나.\n내용" → "나. 내용"
        
        ✅ 수정: [가-하] → [가-힣] (전체 한글)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        lines = content.split('\n')
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 🚨 한글 순서 패턴 (가. 나. 다. ...) - 전체 범위
            if re.match(r'^[가-힣]\.\s*$', line.strip()):
                # 다음 줄 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # 헤더/구분선이면 결속 안 함
                    if next_line.startswith('#') or next_line.startswith('---') or next_line.startswith('```'):
                        result.append(line)
                    elif next_line:  # 평문이면 결속
                        result.append(line.strip() + ' ' + next_line)
                        i += 1  # 다음 줄 스킵
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
            
            i += 1
        
        logger.debug("      한글 순서 결속 완료 (전체 범위)")
        return '\n'.join(result)
    
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
        content = re.sub(r'(\(\d+\))\s*\n{1,3}\s*', r'\1 ', content)
        
        # ① ② ③ 형태
        content = re.sub(r'([①-⑳])\s*\n{1,3}\s*', r'\1 ', content)
        
        logger.debug("      괄호 번호 결속 완료")
        return content
    
    def _normalize_article_numbers(self, content: str) -> str:
        """
        🚨 Phase 5.6.2: 조문 번호 결속 (보수적 적용)
        
        패턴:
        - "제1조\n(목적)" → "제1조 (목적)"
        - "제1항\n내용" → "제1항 내용"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # 제○조 + 괄호 제목 (헤더 마커 없을 때만)
        content = re.sub(r'(제\s?\d+조)\s*\n+\s*(\([^)]+\))(?!\s*\n#)', r'\1 \2', content)
        
        # 제○항 + 내용
        content = re.sub(r'(제\s?\d+항)\s*\n+\s*(?!#)', r'\1 ', content)
        
        # 제○호 + 내용
        content = re.sub(r'(제\s?\d+호)\s*\n+\s*(?!#)', r'\1 ', content)
        
        logger.debug("      조문 번호 결속 완료 (보수적)")
        return content
    
    def _clean_whitespace(self, content: str) -> str:
        """
        🚨 Phase 5.6.2: 불필요한 공백 정리 (보수적)
        
        패턴:
        - 연속 공백 → 단일 공백
        - 3개 이상 줄바꿈 → 2개 줄바꿈
        
        보호:
        - 코드블럭 (```) 내부 보존
        - 헤더 앞뒤 공백 보존
        
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
        
        logger.debug("      공백 정리 완료 (보수적)")
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
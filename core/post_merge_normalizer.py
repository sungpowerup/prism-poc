"""
core/post_merge_normalizer.py
PRISM Phase 5.7.8.1 - PostMergeNormalizer (긴급 패치 - 순서 명시)

✅ Phase 5.7.8.1 긴급 수정:
1. OrderedDict로 사전 순서 명시
2. Longest-First 정책 적용
3. 헤더 라인 보호 (### 제n조는 스킵)
4. 적용 순서 로깅

🎯 해결 문제:
- 복합 띄어쓰기 패턴 미적용
- 헤더 라인 오수정 방지
- Dict 순서 불안정

Author: 이서영 (Backend Lead) + GPT 제안 반영
Date: 2025-11-05
Version: 5.7.8.1 Hotfix
"""

import re
import logging
from typing import Dict, Any
from collections import OrderedDict

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 5.7.8.1 후처리 정규화 (순서 최적화)
    
    핵심 개선:
    - OrderedDict로 순서 보장
    - Longest-First 정책
    - 헤더 라인 보호
    
    역할:
    - Fallback 후 텍스트 정리
    - 띄어쓰기 복원
    - 줄바꿈 정규화
    """
    
    # ✅ Phase 5.7.8.1: OrderedDict로 순서 명시 (Longest-First)
    HIGH_FREQ_TERMS = OrderedDict([
        # ========================================
        # 🔥 복합 패턴 (긴 것부터) - 최우선 적용
        # ========================================
        
        # Phase 5.7.8: 고빈도 띄어쓰기 (미송 제안)
        ('1명의직원에게부여할수있는', '1명의 직원에게 부여할 수 있는'),
        ('직원에게부여할수있는', '직원에게 부여할 수 있는'),
        ('1명의 직원에게부여할수있는', '1명의 직원에게 부여할 수 있는'),
        ('직원에 게부여할수있는', '직원에게 부여할 수 있는'),
        ('부여할수있는', '부여할 수 있는'),
        ('1명의직원에게', '1명의 직원에게'),
        ('직원에게', '직원에게'),  # 정상 (보존)
        
        # Phase 5.7.7.2: 복합 패턴
        ('직무의종류', '직무의 종류'),
        ('그밖에', '그 밖에'),
        
        # ========================================
        # 📌 중간 패턴
        # ========================================
        
        # Phase 5.7.7.1: 조문 표현
        ('제1조', '제1조'),  # 정상 (보존)
        ('제 1조', '제1조'),  # 공백 제거
        ('제  1조', '제1조'),  # 공백 2개 제거
        
        # Phase 5.7.6: 단어 경계
        ('가진다', '가진다'),  # 정상 (보존)
        ('가 진다', '가진다'),
        
        # ========================================
        # 🔻 단순 패턴 (짧은 것) - 맨 마지막 적용
        # ========================================
        
        ('할수있는', '할 수 있는'),
        ('할수없는', '할 수 없는'),
        ('수있는', '수 있는'),
        ('수없는', '수 없는'),
        ('에게', '에게'),  # 정상 (보존)
        ('에 게', '에게'),
        ('에서', '에서'),  # 정상 (보존)
        ('에 서', '에서'),
    ])
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PostMergeNormalizer v5.7.8.1 초기화 완료 (순서 최적화)")
        logger.info(f"   📖 고빈도 사전: {len(self.HIGH_FREQ_TERMS)}개 (OrderedDict)")
        logger.info("   🎯 적용 정책: Longest-First (긴 패턴 우선)")
        logger.info("   🛡️ 헤더 보호: ### 제n조 라인 스킵")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        ✅ Phase 5.7.8.1: 후처리 정규화 (헤더 보호)
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer v5.7.8.1 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        
        # ✅ Phase 5.7.8.1: 헤더 라인 보호
        lines = content.split('\n')
        protected_lines = []
        
        for line in lines:
            # 헤더 라인 감지 (### 제n조)
            if re.match(r'^\s*#{1,3}\s*제\s*\d+\s*조', line):
                # 헤더는 그대로 보존
                protected_lines.append(line)
                logger.debug(f"      헤더 보호: {line[:50]}")
            else:
                # 일반 라인만 정규화
                normalized_line = self._normalize_line(line, doc_type)
                protected_lines.append(normalized_line)
        
        content = '\n'.join(protected_lines)
        
        # 줄바꿈 정규화
        content = self._normalize_newlines(content)
        
        # 리스트 정규화
        content = self._normalize_lists(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {normalized_len} 글자")
        
        return content
    
    def _normalize_line(self, line: str, doc_type: str) -> str:
        """
        개별 라인 정규화
        
        Args:
            line: 원본 라인
            doc_type: 문서 타입
        
        Returns:
            정규화된 라인
        """
        original_line = line
        
        # 고빈도 용어 사전 적용 (규정 모드만)
        if doc_type == 'statute':
            for wrong, correct in self.HIGH_FREQ_TERMS.items():
                if wrong in line:
                    line = line.replace(wrong, correct)
        
        # 과도한 공백 정리
        line = re.sub(r' {2,}', ' ', line)
        
        return line
    
    def _normalize_newlines(self, content: str) -> str:
        """
        줄바꿈 정규화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 3개 이상 줄바꿈 → 2개
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 조문 헤더 앞뒤 정리
        content = re.sub(r'\n+(#{1,3}\s*제\s*\d+\s*조)', r'\n\n\1', content)
        content = re.sub(r'(#{1,3}\s*제\s*\d+\s*조[^\n]*)\n+', r'\1\n', content)
        
        return content
    
    def _normalize_lists(self, content: str) -> str:
        """
        리스트 정규화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 번호 리스트 정규화 (1. 2. 3.)
        content = re.sub(r'(\d+)\s*\.\s*', r'\1. ', content)
        
        # 호 리스트 정규화 (가. 나. 다.)
        content = re.sub(r'([가-힣])\s*\.\s*', r'\1. ', content)
        
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
        corrections = 0
        
        # 고빈도 용어 교정 개수
        for wrong in self.HIGH_FREQ_TERMS.keys():
            corrections += original.count(wrong)
        
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'corrections': corrections,
            'rules_count': len(self.HIGH_FREQ_TERMS)
        }
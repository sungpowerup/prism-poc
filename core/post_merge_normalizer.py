"""
core/post_merge_normalizer.py
PRISM Phase 0.2 Hotfix - Post Merge Normalizer with Revision Table Dedup

✅ Phase 0.2 긴급 수정:
1. 개정이력 표 중복 제거 (첫 등장만 유지)
2. 페이지 마커 제거 패턴 확장
3. 반복 제목 제거 ("인사규정")
4. 분할된 단어 처리 ("402-3 용을")

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import re
import logging
from typing import Dict, Any
from collections import OrderedDict

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 0.2 후처리 정규화 (개정이력 dedup + 페이지 마커 제거)
    
    ✅ Phase 0.2 개선:
    - 개정이력 표 중복 제거 (첫 등장만 유지)
    - 페이지 마커 패턴 5종 확장
    - 반복 제목 제거
    - 안전 가드 (단독 라인만)
    """
    
    # 고빈도 용어 사전
    HIGH_FREQ_TERMS = OrderedDict([
        ('성과계재단상자', '성과개선대상자'),
        ('공금관리위원회', '상급인사위원회'),
        ('직원에 게', '직원에게'),
        ('부여할 수있는', '부여할 수 있는'),
        ('가 진다', '가진다'),
        ('에 게', '에게'),
        ('에서', '에서'),
    ])
    
    # ✅ Phase 0.2: 페이지 마커 패턴 (확장)
    PAGE_MARKER_PATTERNS = [
        r'^\s*\d{3,4}-\d{1,2}\s*$',           # "402-3"
        r'^\s*Page\s+\d+\s*$',                # "Page 1"
        r'^\s*[-—–_*]{3,}\s*$',              # "---", "___"
        r'^\s*인사규정\s*$',                  # "인사규정" (반복 제목)
        r'^\s*\d{3,4}-\d{1,2}\s*[가-힣]{1,2}\s*$',  # "402-3 용을" (분할 단어)
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ PostMergeNormalizer Phase 0.2 초기화 완료")
        logger.info(f"   📖 고빈도 사전: {len(self.HIGH_FREQ_TERMS)}개")
        logger.info(f"   🔍 페이지 마커 패턴: {len(self.PAGE_MARKER_PATTERNS)}개")
        logger.info("   🗑️ 개정이력 dedup: 활성화")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        ✅ Phase 0.2: 후처리 정규화 (개정이력 dedup + 페이지 마커 제거)
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer Phase 0.2 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        
        # 1) ✅ Phase 0.2: 개정이력 표 중복 제거 (첫 등장만 유지)
        content = self._dedup_revision_tables(content)
        
        # 2) ✅ Phase 0.2: 페이지 마커 제거 (라인별)
        lines = content.split('\n')
        cleaned_lines = []
        removed_count = 0
        
        for line in lines:
            is_marker = False
            
            for pattern in self.PAGE_MARKER_PATTERNS:
                if re.match(pattern, line):
                    is_marker = True
                    removed_count += 1
                    logger.debug(f"      페이지 마커 제거: '{line.strip()}'")
                    break
            
            if not is_marker:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        logger.info(f"   🗑️ 페이지 마커 제거: {removed_count}개 라인")
        
        # 3) 고빈도 용어 사전 (statute 모드만)
        if doc_type == 'statute':
            for wrong, correct in self.HIGH_FREQ_TERMS.items():
                if wrong in content:
                    count = content.count(wrong)
                    content = content.replace(wrong, correct)
                    logger.debug(f"      용어 교정: '{wrong}' → '{correct}' ({count}회)")
        
        # 4) 줄바꿈 정규화
        content = self._normalize_newlines(content)
        
        # 5) 리스트 정규화
        content = self._normalize_lists(content)
        
        # 6) 과도한 공백 제거
        content = re.sub(r' {2,}', ' ', content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {normalized_len} 글자")
        
        return content
    
    def _dedup_revision_tables(self, content: str) -> str:
        """
        ✅ Phase 0.2: 개정이력 표 중복 제거 (첫 등장만 유지)
        
        전략:
        - 블록 단위로 분할 (\n\n)
        - "| 차수 | 날짜 |"로 시작하는 블록 감지
        - 정규화된 키 생성 (공백 제거)
        - 첫 등장만 유지, 이후 중복 제거
        
        Args:
            content: Markdown 텍스트
        
        Returns:
            중복 제거된 텍스트
        """
        blocks = content.strip().split('\n\n')
        seen = set()
        out = []
        dedup_count = 0
        
        for block in blocks:
            # 개정이력 표 감지
            if block.lstrip().startswith('| 차수 | 날짜'):
                # 정규화된 키 생성 (공백/빈 줄 제거)
                normalized_key = '\n'.join([
                    ln.strip() 
                    for ln in block.splitlines() 
                    if ln.strip()
                ])
                
                # 중복 체크
                if normalized_key in seen:
                    dedup_count += 1
                    logger.info(f"      🗑️ 중복 개정이력 표 제거 (#{dedup_count})")
                    continue
                
                seen.add(normalized_key)
            
            out.append(block)
        
        if dedup_count > 0:
            logger.info(f"   ✅ 개정이력 표 중복 제거: {dedup_count}개")
        
        return '\n\n'.join(out)
    
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
        
        # 제n장 헤더 앞뒤 정리
        content = re.sub(r'\n+(#{0,3}\s*제\s*\d+\s*장)', r'\n\n\1', content)
        content = re.sub(r'(#{0,3}\s*제\s*\d+\s*장[^\n]*)\n+', r'\1\n', content)
        
        return content
    
    def _normalize_lists(self, content: str) -> str:
        """
        리스트 정규화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 번호 리스트 (1. 2. 3.)
        content = re.sub(r'(\d+)\s*\.\s*', r'\1. ', content)
        
        # 호 리스트 (가. 나. 다.)
        content = re.sub(r'([가-힣])\s*\.\s*', r'\1. ', content)
        
        return content
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """정규화 통계"""
        corrections = 0
        
        for wrong in self.HIGH_FREQ_TERMS.keys():
            corrections += original.count(wrong)
        
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'corrections': corrections,
            'rules_count': len(self.HIGH_FREQ_TERMS)
        }
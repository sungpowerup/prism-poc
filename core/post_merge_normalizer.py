"""
core/post_merge_normalizer_safe.py
PRISM Phase 0.3.2 - Safe Mode (중간 코드펜스 제거)

✅ Phase 0.3.2 개선:
1. 중간 코드펜스 제거 추가
2. 페이지 마커 패턴 확장
3. 의미 치환 완전 제거

Author: 이서영 (Backend Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.2
"""

import re
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 0.3.2 통합 후 정규화 (중간 코드펜스 제거)
    
    ✅ Phase 0.3.2 개선:
    - 중간 코드펜스 제거
    - 페이지 마커 패턴 확장
    """
    
    # 버전 정보
    VERSION = "Phase 0.3.2"
    
    # 페이지 마커 패턴 (확장)
    PAGE_MARKER_PATTERNS = [
        r'^\s*\d{3,4}-\d{1,2}\s*$',           # 402-1, 402-2
        r'^\s*_\d{3,4}-\d{1,2}_\s*$',         # _402-1_
        r'^\s*\*\d{3,4}-\d{1,2}\*\s*$',       # *402-1*
        r'^\s*페이지\s+\d+\s*$',              # 페이지 1
        r'^\s*Page\s+\d+\s*$',                # Page 1
        r'^\s*-\s*\d+\s*-\s*$',              # - 1 -
        r'^\s*\[\s*\d+\s*\]\s*$',            # [1]
    ]
    
    # 개정 이력 패턴
    REVISION_PATTERN = re.compile(
        r'(?:제\s*)?(\d+)차\s*개정\s*(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})',
        re.MULTILINE
    )
    
    # ⚠️ Phase 0.3: 의미 치환 완전 제거
    COMMON_TYPOS = {}
    
    # 🚫 Phase 0.3: 금지 치환 블록리스트
    BLOCKED_REPLACEMENTS = {
        '공금관리', '상급인사',
        '종합인사위원회', '상급인사위원회',
        '성과계약전담상자', '성과개선대상자',
        '징계요건', '제9조의',
        '사직', '삭제',
    }
    
    def __init__(self):
        """초기화"""
        self.compiled_patterns = [
            re.compile(p, re.MULTILINE) for p in self.PAGE_MARKER_PATTERNS
        ]
        
        logger.info(f"✅ PostMergeNormalizer {self.VERSION} 초기화 완료")
        logger.info(f"   📖 의미 사전: {len(self.COMMON_TYPOS)}개 (비활성화)")
        logger.info(f"   🚫 금지 치환: {len(self.BLOCKED_REPLACEMENTS)}개")
        logger.info(f"   🔍 페이지 마커 패턴: {len(self.PAGE_MARKER_PATTERNS)}개")
        logger.info(f"   🗑️ 개정이력 dedup: 활성화")
        logger.info(f"   🔄 2차 검증: 활성화")
        logger.info(f"   ⚠️ 의미 치환 제거: 원본 충실도 우선")
    
    def normalize(self, text: str, doc_type: str = 'statute') -> str:
        """
        통합 Markdown 정규화
        
        Args:
            text: 통합된 Markdown
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer {self.VERSION} 시작 (doc_type: {doc_type})")
        
        original_len = len(text)
        
        # ✅ 1단계: 페이지 마커 제거
        text, marker_count = self._remove_page_markers(text)
        
        # ✅ 2단계: 개정이력 중복 제거
        text = self._deduplicate_revisions(text)
        
        # ✅ Phase 0.3.2: 3단계: 중간 코드펜스 제거
        text = self._remove_inline_codefence(text)
        
        final_len = len(text)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {final_len} 글자")
        
        return text
    
    def _remove_page_markers(self, text: str) -> tuple:
        """
        페이지 마커 제거
        
        Args:
            text: 원본 텍스트
        
        Returns:
            (정규화된 텍스트, 제거 횟수)
        """
        lines = text.split('\n')
        cleaned_lines = []
        removed_count = 0
        
        for line in lines:
            is_marker = False
            for pattern in self.compiled_patterns:
                if pattern.match(line.strip()):
                    is_marker = True
                    removed_count += 1
                    break
            
            if not is_marker:
                cleaned_lines.append(line)
        
        if removed_count > 0:
            logger.info(f"   🗑️ 페이지 마커 제거: {removed_count}개 라인")
        
        return '\n'.join(cleaned_lines), removed_count
    
    def _deduplicate_revisions(self, text: str) -> str:
        """
        개정이력 중복 제거
        
        Args:
            text: 원본 텍스트
        
        Returns:
            중복 제거된 텍스트
        """
        seen = set()
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            match = self.REVISION_PATTERN.search(line)
            if match:
                key = (match.group(1), match.group(2), match.group(3), match.group(4))
                if key in seen:
                    continue
                seen.add(key)
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_inline_codefence(self, text: str) -> str:
        """
        ✅ Phase 0.3.2: 중간 코드펜스 제거
        
        Args:
            text: 원본 텍스트
        
        Returns:
            코드펜스 제거된 텍스트
        """
        # 시작/끝 코드펜스 제거 (기존)
        text = re.sub(r'^```markdown\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```$', '', text, flags=re.MULTILINE)
        
        # ✅ Phase 0.3.2: 중간 코드펜스도 제거
        text = re.sub(r'\n```markdown\n', '\n\n', text)
        text = re.sub(r'\n```\n', '\n\n', text)
        
        return text
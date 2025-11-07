"""
post_merge_normalizer_v033.py
PRISM Phase 0.3.3 - Post Merge Normalizer (간소화)

✅ Phase 0.3.3 개선:
1. 페이지 마커 제거
2. 개정이력 중복 제거
3. 중간 코드펜스 제거
4. 불필요한 의미 치환 완전 제거

설치: core/post_merge_normalizer_safe.py 대체

Author: 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.3
"""

import re
import logging

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 0.3.3 통합 후 정규화 (간소화)
    
    ✅ 핵심 개선:
    - 페이지 마커 제거
    - 개정이력 중복 제거
    - 의미 치환 완전 제거
    """
    
    VERSION = "Phase 0.3.3"
    
    # 페이지 마커 패턴
    PAGE_MARKER_PATTERNS = [
        r'^\s*\d{3,4}-\d{1,2}\s*$',      # 402-1
        r'^\s*_\d{3,4}-\d{1,2}_\s*$',    # _402-1_
        r'^\s*\*\d{3,4}-\d{1,2}\*\s*$',  # *402-1*
        r'^\s*페이지\s+\d+\s*$',         # 페이지 1
        r'^\s*Page\s+\d+\s*$',           # Page 1
    ]
    
    # 개정 이력 패턴
    REVISION_PATTERN = re.compile(
        r'(?:제\s*)?(\d+)차\s*개정\s*(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        self.compiled_patterns = [
            re.compile(p, re.MULTILINE) for p in self.PAGE_MARKER_PATTERNS
        ]
        
        logger.info(f"✅ PostMergeNormalizer {self.VERSION} 초기화")
        logger.info(f"   🗑️ 페이지 마커 패턴: {len(self.PAGE_MARKER_PATTERNS)}개")
        logger.info(f"   🗑️ 개정이력 dedup: 활성화")
    
    def normalize(self, text: str, doc_type: str = 'statute') -> str:
        """
        통합 Markdown 정규화
        
        Args:
            text: 통합된 Markdown
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🧹 PostMergeNormalizer {self.VERSION} 시작")
        
        original_len = len(text)
        
        # 1. 페이지 마커 제거
        text, marker_count = self._remove_page_markers(text)
        
        # 2. 개정이력 중복 제거
        text, revision_count = self._deduplicate_revisions(text)
        
        # 3. 중간 코드펜스 제거
        text, fence_count = self._remove_inline_fences(text)
        
        # 4. 빈 줄 정리
        text = self._cleanup_empty_lines(text)
        
        final_len = len(text)
        
        logger.info(f"   ✅ 정규화 완료:")
        logger.info(f"      페이지 마커: {marker_count}개 제거")
        logger.info(f"      개정이력: {revision_count}개 중복 제거")
        logger.info(f"      코드펜스: {fence_count}개 제거")
        logger.info(f"      길이: {original_len} → {final_len} ({final_len - original_len:+d})")
        
        return text
    
    def _remove_page_markers(self, text: str):
        """페이지 마커 제거"""
        count = 0
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            is_marker = False
            for pattern in self.compiled_patterns:
                if pattern.match(line):
                    is_marker = True
                    count += 1
                    break
            
            if not is_marker:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), count
    
    def _deduplicate_revisions(self, text: str):
        """개정이력 중복 제거"""
        revisions = {}
        
        def replacer(match):
            key = (match.group(1), match.group(2), match.group(3), match.group(4))
            if key not in revisions:
                revisions[key] = match.group(0)
                return match.group(0)
            else:
                return ''
        
        text = self.REVISION_PATTERN.sub(replacer, text)
        
        # 중복 제거된 개수
        count = len([v for v in revisions.values() if v == ''])
        
        return text, count
    
    def _remove_inline_fences(self, text: str):
        """중간 코드펜스 제거 (시작/끝 제외)"""
        lines = text.split('\n')
        
        # 첫 번째와 마지막 코드펜스 위치 찾기
        fence_positions = []
        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                fence_positions.append(i)
        
        if len(fence_positions) <= 2:
            # 2개 이하면 제거 안 함
            return text, 0
        
        # 중간 펜스만 제거 (첫/마지막 제외)
        count = 0
        for i in fence_positions[1:-1]:
            if lines[i].strip().startswith('```'):
                lines[i] = ''
                count += 1
        
        return '\n'.join(lines), count
    
    def _cleanup_empty_lines(self, text: str) -> str:
        """과도한 빈 줄 정리 (3개 이상 → 2개)"""
        # 3개 이상의 연속 빈 줄을 2개로
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        
        return text
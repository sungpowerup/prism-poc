"""
core/post_merge_normalizer_safe.py
PRISM Phase 0.3.1 - Safe Mode (의미 치환 제거)

⚠️ Phase 0.3.1 긴급 수정:
1. 의미 치환 완전 제거
2. 페이지 마커 제거만 집중
3. 2차 검증 유지
4. 과교정 방지

Author: 이서영 (Backend Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.1 (Safe Mode)
"""

import re
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 0.3.1 통합 후 정규화 (안전 모드)
    
    ⚠️ Phase 0.3.1 핵심:
    - 의미 치환 완전 제거
    - 페이지 마커 제거만 수행
    - 2차 검증 유지
    """
    
    # 버전 정보
    VERSION = "Phase 0.3.1 (Safe Mode)"
    
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
    
    # ⚠️ Phase 0.3.1: 의미 치환 완전 제거 (빈 사전)
    COMMON_TYPOS = {}
    
    # 🚫 Phase 0.3.1: 금지 치환 블록리스트
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
        통합 Markdown 정규화 (안전 모드)
        
        Args:
            text: 통합된 Markdown
            doc_type: 문서 타입
        
        Returns:
            정규화된 Markdown
        """
        if not text or not text.strip():
            return text
        
        logger.info(f"   🔧 PostMergeNormalizer {self.VERSION} 시작 (doc_type: {doc_type})")
        
        original_len = len(text)
        
        # Step 1: 페이지 마커 제거 (1차)
        text, removed_1st = self._remove_page_markers(text)
        
        # ✅ Phase 0.3: 2차 제거 루프
        text, removed_2nd = self._remove_page_markers(text)
        
        total_removed = removed_1st + removed_2nd
        
        if removed_2nd > 0:
            logger.info(f"   🔄 2차 검증으로 추가 제거: {removed_2nd}개")
        
        logger.info(f"   🗑️ 페이지 마커 제거: {total_removed}개 라인")
        
        # Step 2: 개정이력 중복 제거
        if doc_type == 'statute':
            text = self._deduplicate_revisions(text)
        
        # Step 3: 의미 치환 완전 제거 (빈 사전)
        # (아무것도 하지 않음)
        
        # Step 4: 과도한 공백 제거
        text = re.sub(r'\n{4,}', '\n\n\n', text)  # 4+ 줄바꿈 → 3줄
        text = re.sub(r' {3,}', '  ', text)       # 3+ 공백 → 2공백
        
        final_len = len(text)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {final_len} 글자")
        
        # ⚠️ Phase 0.3.1: 과교정 경고
        if original_len > 0:
            deletion_rate = (original_len - final_len) / original_len
            if deletion_rate > 0.02:
                logger.warning(f"   ⚠️ 과교정 의심: 삭제율 {deletion_rate:.1%}")
        
        return text
    
    def _remove_page_markers(self, text: str) -> tuple:
        """페이지 마커 제거 (단일 패스)"""
        lines = text.split('\n')
        result = []
        removed = 0
        
        for line in lines:
            is_marker = False
            
            for pattern in self.compiled_patterns:
                if pattern.match(line.strip()):
                    is_marker = True
                    removed += 1
                    break
            
            if not is_marker:
                result.append(line)
        
        return '\n'.join(result), removed
    
    def _deduplicate_revisions(self, text: str) -> str:
        """개정 이력 중복 제거"""
        matches = list(self.REVISION_PATTERN.finditer(text))
        
        if len(matches) <= 17:
            return text
        
        seen: Set[str] = set()
        to_remove: List[str] = []
        
        for match in matches:
            key = f"{match.group(1)}-{match.group(2)}.{match.group(3)}.{match.group(4)}"
            
            if key in seen:
                to_remove.append(match.group(0))
            else:
                seen.add(key)
        
        for dup in to_remove:
            text = text.replace(dup, '', 1)
        
        if to_remove:
            logger.info(f"   🗑️ 개정이력 중복 제거: {len(to_remove)}개")
        
        return text
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            'version': self.VERSION,
            'typo_dict_size': len(self.COMMON_TYPOS),
            'blocked_count': len(self.BLOCKED_REPLACEMENTS),
            'marker_patterns': len(self.PAGE_MARKER_PATTERNS),
            'double_check_enabled': True
        }
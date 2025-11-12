"""
core/post_merge_normalizer_safe.py
PRISM Phase 0.3.4 P1 - GPT 핫픽스 반영

✅ 변경사항:
1. 코드펜스 완전 제거 (```markdown 등)
2. 페이지 마커 강화 (402-1, Page 1/3 등)
3. 제거 전후 diff 로그
"""

import re
import logging

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """Phase 0.3.4 P1 후처리 정규화"""
    
    # GPT 핫픽스: 코드펜스 완전 제거
    CODE_FENCE_PATTERN = re.compile(r'```[a-zA-Z0-9_-]*\s*', re.MULTILINE)
    CODE_FENCE_END = re.compile(r'\s*```', re.MULTILINE)
    
    # GPT 핫픽스: 페이지 마커 강화
    PAGE_MARKERS = [
        re.compile(r'\b\d{3,4}\s*-\s*\d{1,2}\b'),  # 402-1
        re.compile(r'Page\s+\d+\s*/\s*\d+', re.IGNORECASE),  # Page 1/3
        re.compile(r'^\s*-\s*\d+\s*-\s*$', re.MULTILINE),  # - 1 -
    ]
    
    def __init__(self):
        logger.info("✅ PostMergeNormalizer Phase 0.3.4 P1 초기화")
        logger.info(f"   🗑️ 코드펜스 패턴: 2개")
        logger.info(f"   🗑️ 페이지 마커 패턴: {len(self.PAGE_MARKERS)}개")
    
    def normalize(self, text: str) -> str:
        """정규화 실행"""
        if not text:
            return text
        
        original_len = len(text)
        result = text
        
        # 1. 코드펜스 제거
        fence_before = len(re.findall(r'```', result))
        result = self.CODE_FENCE_PATTERN.sub('', result)
        result = self.CODE_FENCE_END.sub('', result)
        fence_after = len(re.findall(r'```', result))
        fence_removed = (fence_before - fence_after) // 2
        
        # 2. 페이지 마커 제거
        marker_count = 0
        for pattern in self.PAGE_MARKERS:
            matches = len(pattern.findall(result))
            if matches > 0:
                result = pattern.sub('', result)
                marker_count += matches
        
        # 3. 공백 정리
        result = re.sub(r'\s{2,}', ' ', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = result.strip()
        
        logger.info(f"✅ 정규화 완료:")
        logger.info(f"   코드펜스: {fence_removed}개 제거")
        logger.info(f"   페이지 마커: {marker_count}개 제거")
        logger.info(f"   길이: {original_len} → {len(result)} ({len(result)-original_len:+d})")
        
        return result
"""
core/typo_normalizer_safe.py
PRISM Phase 0.3.4 P2 - GPT 오탈자 사전 확대

✅ 변경사항:
1. CRITICAL_FIXES 10개로 확대
2. 문서에서 발견된 실제 오탈자 전부 추가
"""

import re
import logging

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """Phase 0.3.4 P2 오탈자 정규화 (사전 확대)"""
    
    # GPT 핫픽스: 실제 발견된 오탈자 10종
    CRITICAL_FIXES = {
        # 기존 5개
        "경용범위": "적용범위",
        "임용한": "임용권",
        "진본보정": "신분보장",
        "성과계좌대상자": "성과개선대상자",
        "따른 정한다": "따로 정한다",
        
        # 신규 5개 (GPT 제안)
        "정용범위": "적용범위",
        "진보보장": "신분보장",
        "공급인사위원회": "상급인사위원회",
        "성과계제선발자": "성과개선대상자",
        "변경임시임": "변경시킴"
    }
    
    SAFE_PATTERNS = [
        (r'\s+', ' '),
        (r'\n{3,}', '\n\n'),
        (r'^\s+', ''),
        (r'\s+$', ''),
    ]
    
    OCR_PATTERNS = [
        (r'(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)', r'\1.\2.\3'),
        (r'제\s*(\d+)\s*조', r'제\1조'),
        (r'제\s*(\d+)\s*항', r'제\1항'),
    ]
    
    def __init__(self):
        logger.info("✅ TypoNormalizer Phase 0.3.4 P2 초기화")
        logger.info(f"   📖 CRITICAL_FIXES: {len(self.CRITICAL_FIXES)}개 (확대)")
        logger.info(f"   📖 Safe: {len(self.SAFE_PATTERNS)}개")
        logger.info(f"   📖 OCR: {len(self.OCR_PATTERNS)}개")
    
    def normalize(self, text: str) -> str:
        """정규화 실행"""
        if not text:
            return text
        
        original_len = len(text)
        result = text
        
        # 1. CRITICAL_FIXES (단어 경계 보존)
        critical_count = 0
        for wrong, correct in self.CRITICAL_FIXES.items():
            pattern = rf'\b{re.escape(wrong)}\b'
            matches = len(re.findall(pattern, result))
            if matches > 0:
                result = re.sub(pattern, correct, result)
                critical_count += matches
                logger.debug(f"   ✏️ {wrong} → {correct} ({matches}건)")
        
        # 2. Safe 패턴
        safe_count = 0
        for pattern, replacement in self.SAFE_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                safe_count += before
        
        # 3. OCR 패턴
        ocr_count = 0
        for pattern, replacement in self.OCR_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                ocr_count += before
        
        logger.info(f"✅ 정규화 완료: Critical {critical_count}, Safe {safe_count}, OCR {ocr_count}")
        logger.info(f"   길이: {original_len} → {len(result)} ({len(result)-original_len:+d})")
        
        return result
"""
core/typo_normalizer_safe.py
PRISM Phase 0.3.4 P2.4 - 도메인 사전 확대

✅ 변경사항:
1. OCR 오탈자 추가 (GPT 제안)
2. 도메인 특화 교정
"""

import re
import logging

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """Phase 0.3.4 P2.4 오탈자 정규화 (도메인 사전 확대)"""
    
    # CRITICAL_FIXES 10개
    CRITICAL_FIXES = {
        "경용범위": "적용범위",
        "임용한": "임용권",
        "진본보정": "신분보장",
        "성과계좌대상자": "성과개선대상자",
        "따른 정한다": "따로 정한다",
        "정용범위": "적용범위",
        "진보보정": "신분보장",
        "공급인사위원회": "상급인사위원회",
        "성과계제선발자": "성과개선대상자",
        "성과계제선발심사": "성과개선대상자",
    }
    
    # GPT 제안: 도메인 사전 확대
    DOMAIN_FIXES = {
        "기 본 정 신": "기본정신",
        "용상": "통상",
        "전족": "전속",
        "해파군직채용": "예비군지휘관",
        "수습임용잔료": "수습임용자",
        "병에 계산": "포함 계산",
        "부무": "복무",
        "전일연구원": "전임연구원",
        "또는의": "고도의",
        "시첨정": "시험성적",
        "채용소씨결과": "채용신체검사",
        "신원조직결과": "신원조회결과",
        "감사위원": "부패방지",
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
        logger.info("✅ TypoNormalizer Phase 0.3.4 P2.4 초기화")
        logger.info(f"   📖 CRITICAL_FIXES: {len(self.CRITICAL_FIXES)}개 룰")
        logger.info(f"   📖 DOMAIN_FIXES: {len(self.DOMAIN_FIXES)}개 룰 (신규)")
        logger.info(f"   📖 Safe: {len(self.SAFE_PATTERNS)}개 룰")
        logger.info(f"   📖 OCR: {len(self.OCR_PATTERNS)}개 룰")
    
    def normalize(self, text: str) -> str:
        """정규화 실행"""
        if not text:
            return text
        
        original_len = len(text)
        result = text
        
        # 1. CRITICAL_FIXES (단어 경계 보존)
        critical_count = 0
        for wrong, correct in self.CRITICAL_FIXES.items():
            matches = result.count(wrong)
            if matches > 0:
                result = result.replace(wrong, correct)
                critical_count += matches
        
        # 2. DOMAIN_FIXES (GPT 제안)
        domain_count = 0
        for wrong, correct in self.DOMAIN_FIXES.items():
            matches = result.count(wrong)
            if matches > 0:
                result = result.replace(wrong, correct)
                domain_count += matches
        
        # 3. Safe 패턴
        safe_count = 0
        for pattern, replacement in self.SAFE_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                safe_count += before
        
        # 4. OCR 패턴
        ocr_count = 0
        for pattern, replacement in self.OCR_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                ocr_count += before
        
        logger.info(f"✅ 정규화 완료:")
        logger.info(f"   Critical: {len(self.CRITICAL_FIXES)}개 룰 / {critical_count}건 치환")
        logger.info(f"   Domain: {len(self.DOMAIN_FIXES)}개 룰 / {domain_count}건 치환")
        logger.info(f"   Safe: {len(self.SAFE_PATTERNS)}개 룰 / {safe_count}건 치환")
        logger.info(f"   OCR: {len(self.OCR_PATTERNS)}개 룰 / {ocr_count}건 치환")
        logger.info(f"   길이: {original_len} → {len(result)} ({len(result)-original_len:+d})")
        
        return result
"""
core/typo_normalizer_safe.py
PRISM Phase 0.4.0 P0-3.1 - Hotfix (위험 룰 제거)

✅ P0-3.1 긴급 수정:
1. "또는의 → 고도의" 위험 룰 제거
2. 안전한 교정만 유지
3. 조문 번호 보호 유지

Author: 마창수산팀 + GPT 피드백 반영
Date: 2025-11-13
Version: Phase 0.4.0 P0-3.1
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """Phase 0.4.0 P0-3.1 오탈자 교정 (위험 룰 제거)"""
    
    # ============================================
    # Critical Fixes (필수 교정)
    # ============================================
    CRITICAL_FIXES = {
        # 조문 표기 오류
        "임용한": "임용권",
        "장관": "정관",
        
        # 기본정신 필수 정규화
        "기 본 정 신": "기본정신",
        "기본 정신": "기본정신",
        
        # 명백한 오타
        "읹용": "임용",
        "직원의의": "직원의",
        "사항을을": "사항을",
        "규정은은": "규정은",
        "한국농어촌공사공사": "한국농어촌공사",
        "따라따라": "따라",
    }
    
    # ============================================
    # Domain Fixes (도메인 특화 교정)
    # ✅ P0-3.1: 위험 룰 제거
    # ============================================
    DOMAIN_FIXES = {
        # ✅ 안전한 교정만 유지
        "용상": "통상",
        "전족": "전속",
        "해파군직채용": "예비군지휘관",
        "수습임용잔료": "수습임용자",
        "병에 계산": "포함 계산",
        "읹무": "업무",
        "규칙": "규정",
        "인사규정정": "인사규정",
        "한국농어촌공사사": "한국농어촌공사",
        
        # ❌ 제거된 위험 룰
        # "또는의": "고도의",  # 의미 왜곡 위험!
    }
    
    # ============================================
    # OCR Fixes (OCR 오류 패턴)
    # ============================================
    OCR_FIXES = [
        # 조문 번호 주변 오류
        (r'제(\d+)조의(\d+)', r'제\1조의\2'),  # 제5조의2
        (r'제(\d+)죄', r'제\1조'),
        (r'제(\d+)즈', r'제\1조'),
        (r'제(\d+)쪼', r'제\1조'),
        
        # 일반 오류
        (r'겸입', '겸임'),
        (r'직원의의', '직원의'),
        (r'사장이이', '사장이'),
        (r'규정은은', '규정은'),
        (r'한국농어촌공사사', '한국농어촌공사'),
        
        # 날짜 패턴 오류
        (r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*\)', r'\1.\2.\3'),
        
        # 공백 오류
        (r'제\s+(\d+)\s+조', r'제\1조'),
        (r'제\s+(\d+)\s+장', r'제\1장'),
        (r'(\d+)\s*급', r'\1급'),
        
        # 특수문자 오류
        (r'⟨\s*(\d+)\s*⟩', r'\1'),
        (r'［\s*(\d+)\s*］', r'\1'),
        
        # OCR 혼동 문자
        (r'읹용', '임용'),
        (r'용상', '통상'),
        (r'전족', '전속'),
        (r'병해 계산', '포함 계산'),
        (r'임용권다', '임용한다'),
        (r'규칙에', '규정에'),
    ]
    
    # ============================================
    # Safe Fixes (안전한 정규화)
    # ============================================
    SAFE_FIXES = {
        "  ": " ",           # 연속 공백
        "　": " ",           # 전각 공백
        "。": ".",           # 전각 마침표
        "\u3000": " ",       # 전각 공백 (유니코드)
    }
    
    # ============================================
    # 조문 번호 보호 패턴
    # ============================================
    ARTICLE_PATTERN = re.compile(r'제\s*\d+\s*조(?:의\s*\d+)?')
    
    def __init__(self):
        logger.info("✅ TypoNormalizer Phase 0.4.0 P0-3.1 초기화 (Hotfix)")
        logger.info(f"   📖 CRITICAL_FIXES: {len(self.CRITICAL_FIXES)}개 룰")
        logger.info(f"   📖 DOMAIN_FIXES: {len(self.DOMAIN_FIXES)}개 룰")
        logger.info(f"   📖 OCR_FIXES: {len(self.OCR_FIXES)}개 패턴")
        logger.info(f"   📖 Safe: {len(self.SAFE_FIXES)}개 룰")
        logger.info("   🛡️ 조문 번호 절대 보호 활성화")
        logger.info("   ⚠️ 위험 룰 제거: 또는의 → 고도의")
    
    def normalize(self, text: str) -> str:
        """텍스트 정규화 (조문 번호 보호)"""
        
        # 1. 조문 번호 보호 영역 마킹
        protected_regions = []
        for m in self.ARTICLE_PATTERN.finditer(text):
            protected_regions.append((m.start(), m.end()))
        
        logger.info(f"   🛡️ 조문 번호 보호 영역: {len(protected_regions)}개")
        
        original_len = len(text)
        
        # 2. Critical Fixes (조문 번호 제외)
        critical_count = 0
        critical_examples = []
        
        for wrong, right in self.CRITICAL_FIXES.items():
            if wrong in text:
                # 조문 번호 내부가 아닌 경우만 치환
                for m in re.finditer(re.escape(wrong), text):
                    pos = m.start()
                    # 보호 영역 체크
                    in_protected = any(start <= pos < end for start, end in protected_regions)
                    if not in_protected:
                        text = text[:pos] + right + text[pos + len(wrong):]
                        critical_count += 1
                        if len(critical_examples) < 3:
                            critical_examples.append(f"{wrong} → {right}")
        
        # 3. Domain Fixes (조문 번호 제외)
        domain_count = 0
        domain_examples = []
        
        for wrong, right in self.DOMAIN_FIXES.items():
            if wrong in text:
                for m in re.finditer(re.escape(wrong), text):
                    pos = m.start()
                    in_protected = any(start <= pos < end for start, end in protected_regions)
                    if not in_protected:
                        text = text[:pos] + right + text[pos + len(wrong):]
                        domain_count += 1
                        if len(domain_examples) < 3:
                            domain_examples.append(f"{wrong} → {right}")
        
        # 4. OCR Fixes (패턴 기반)
        ocr_count = 0
        ocr_examples = []
        
        for pattern, replacement in self.OCR_FIXES:
            matches = list(re.finditer(pattern, text))
            for m in matches:
                pos = m.start()
                in_protected = any(start <= pos < end for start, end in protected_regions)
                if not in_protected:
                    before = m.group(0)
                    after = re.sub(pattern, replacement, before)
                    text = text[:pos] + after + text[m.end():]
                    ocr_count += 1
                    if len(ocr_examples) < 3 and before != after:
                        ocr_examples.append(f"{before} → {after}")
        
        # 5. Safe Fixes (전체 적용)
        safe_count = 0
        for wrong, right in self.SAFE_FIXES.items():
            count = text.count(wrong)
            if count > 0:
                text = text.replace(wrong, right)
                safe_count += count
        
        # 6. OCR 기본 정리 (전체 적용)
        ocr_basic_count = 0
        
        # 연속 공백
        before_spaces = text
        text = re.sub(r' {2,}', ' ', text)
        ocr_basic_count += len(before_spaces) - len(text)
        
        # 연속 줄바꿈 (3개 이상 → 2개)
        before_newlines = text
        text = re.sub(r'\n{3,}', '\n\n', text)
        ocr_basic_count += len(before_newlines) - len(text)
        
        # 조문 번호 공백 정리
        text = re.sub(r'제\s+(\d+)\s+조', r'제\1조', text)
        
        # 7. 로그 출력
        logger.info("✅ 정규화 완료 (조문 번호 보호):")
        logger.info(f"   Critical: {len(self.CRITICAL_FIXES)}개 룰 / {critical_count}건 치환")
        if critical_examples:
            logger.info(f"      예: {', '.join(critical_examples)}")
        
        logger.info(f"   Domain: {len(self.DOMAIN_FIXES)}개 룰 / {domain_count}건 치환")
        if domain_examples:
            logger.info(f"      예: {', '.join(domain_examples)}")
        
        logger.info(f"   OCR_Fixes: {len(self.OCR_FIXES)}개 패턴 / {ocr_count}건 치환")
        if ocr_examples:
            logger.info(f"      예: {', '.join(ocr_examples)}")
        
        logger.info(f"   Safe: {len(self.SAFE_FIXES)}개 룰 / {safe_count}건 치환")
        logger.info(f"   OCR: 3개 룰 / {ocr_basic_count}건 치환")
        
        final_len = len(text)
        logger.info(f"   길이: {original_len} → {final_len} ({final_len - original_len:+d})")
        
        return text
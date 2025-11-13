"""
core/typo_normalizer_safe.py
PRISM Phase 0.4.0 P0-1 긴급 패치 (조문 번호 보호)

✅ 핵심 개선:
1. 조문 번호 영역 절대 보호 (제N조, 제N조의N)
2. 보호 영역 외부에서만 OCR 교정
3. 숫자 왜곡 완전 차단 (7→73, 8→90 방지)

Author: 마창수산팀 (이서영 Backend Lead) + GPT 보정
Date: 2025-11-13
Version: Phase 0.4.0 P0-1 (Emergency Patch)
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """Phase 0.4.0 P0-1 오탈자 정규화 (조문 번호 보호)"""
    
    # ✅ 조문 번호 보호 패턴 (최우선)
    ARTICLE_PATTERN = re.compile(
        r'제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*(?:항|호))?',
        re.IGNORECASE
    )
    
    # CRITICAL_FIXES 10개 (기존)
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
    
    # DOMAIN_FIXES 13개 (기존)
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
    
    # OCR_FIXES 24개 (기존)
    OCR_FIXES = [
        (re.compile(r'채\s*채\s*규정'), '채용규정'),
        (re.compile(r'인턴\s*채\s*통상'), '인턴·통상'),
        (re.compile(r'임\s*통상'), '인턴·통상'),
        (re.compile(r'설\s*차\s*적'), '절차적'),
        (re.compile(r'주식\s*법\s*처벌\s*법'), '성폭력범죄 처벌 등에 관한 특례법'),
        (re.compile(r'성과\s*계\s*거\s*시\s*단\s*상'), '성과개선대상자'),
        (re.compile(r'성과\s*개\s*개\s*진\s*상\s*자'), '성과개선대상자'),
        (re.compile(r'변경\s*시\s*임\s*함'), '변경시킴'),
        (re.compile(r'복직\s*시\s*임'), '복직시킴'),
        (re.compile(r'채용\s*소\s*재\s*결과'), '채용신체검사'),
        (re.compile(r'채용\s*소\s*씨\s*결과'), '채용신체검사'),
        (re.compile(r'판결\s*판결'), '징계판결'),
        (re.compile(r'저질러\s*라\s*하면'), '저질러 파면'),
        (re.compile(r'반\s*한\s*결격'), '불합격 처리'),
        (re.compile(r'군\s*법무관'), '부패방지'),
        (re.compile(r'대\s*연\s*보안'), '대외 보안'),
        (re.compile(r'태\s*연\s*보안'), '대외 보안'),
        (re.compile(r'수습\s*임용\s*잔\s*료'), '수습임용자'),
        (re.compile(r'직원\s*방식\s*절차'), '직권면직'),
        (re.compile(r'병해\s*계산'), '포함 계산'),
        (re.compile(r'공개\s*경진\s*심사'), '상급인사위원회'),
        (re.compile(r'경력\s*직\s*임용'), '직원으로 임용'),
        (re.compile(r'임용\s*권\s*다'), '임용한다'),
        (re.compile(r'사\s*채'), '삭제'),
    ]
    
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
        logger.info("✅ TypoNormalizer Phase 0.4.0 P0-1 초기화 (조문 번호 보호)")
        logger.info(f"   📖 CRITICAL_FIXES: {len(self.CRITICAL_FIXES)}개 룰")
        logger.info(f"   📖 DOMAIN_FIXES: {len(self.DOMAIN_FIXES)}개 룰")
        logger.info(f"   📖 OCR_FIXES: {len(self.OCR_FIXES)}개 패턴")
        logger.info(f"   📖 Safe: {len(self.SAFE_PATTERNS)}개 룰")
        logger.info(f"   📖 OCR: {len(self.OCR_PATTERNS)}개 룰")
        logger.info("   🛡️ 조문 번호 절대 보호 활성화")
    
    def _extract_protected_zones(self, text: str) -> List[Tuple[int, int, str]]:
        """
        ✅ P0-1: 조문 번호 영역 추출 (절대 보호)
        
        보호 대상:
        - 제N조
        - 제N조의N
        - 제N조 제N항
        - 제N조 제N호
        
        Returns:
            List[(start, end, matched_text)]
        """
        protected_zones = []
        
        for match in self.ARTICLE_PATTERN.finditer(text):
            start = match.start()
            end = match.end()
            matched = match.group(0)
            
            protected_zones.append((start, end, matched))
        
        if protected_zones:
            logger.info(f"   🛡️ 조문 번호 보호 영역: {len(protected_zones)}개")
            # 샘플 표시 (처음 3개)
            for i, (s, e, m) in enumerate(protected_zones[:3], 1):
                logger.debug(f"      [{i}] {m}")
        
        return protected_zones
    
    def _is_in_protected_zone(self, pos: int, protected_zones: List[Tuple[int, int, str]]) -> bool:
        """위치가 보호 영역 내부인지 확인"""
        for start, end, _ in protected_zones:
            if start <= pos < end:
                return True
        return False
    
    def _safe_replace(
        self,
        text: str,
        pattern: str,
        replacement: str,
        protected_zones: List[Tuple[int, int, str]],
        is_regex: bool = False
    ) -> Tuple[str, int]:
        """
        ✅ 보호 영역을 피해서 안전하게 치환
        
        Args:
            text: 원본 텍스트
            pattern: 치환 패턴 (문자열 또는 정규식)
            replacement: 치환 문자열
            protected_zones: 보호 영역 리스트
            is_regex: 정규식 여부
        
        Returns:
            (치환된 텍스트, 치환 횟수)
        """
        if not protected_zones:
            # 보호 영역 없으면 일반 치환
            if is_regex:
                matches = list(re.finditer(pattern, text))
                count = len(matches)
                text = re.sub(pattern, replacement, text)
            else:
                count = text.count(pattern)
                text = text.replace(pattern, replacement)
            return text, count
        
        # 보호 영역이 있으면 안전 치환
        if is_regex:
            matches = list(re.finditer(pattern, text))
        else:
            # 문자열 패턴을 정규식으로 변환
            escaped = re.escape(pattern)
            matches = list(re.finditer(escaped, text))
        
        # 역순으로 치환 (인덱스 꼬임 방지)
        count = 0
        for match in reversed(matches):
            start = match.start()
            
            # 보호 영역 체크
            if not self._is_in_protected_zone(start, protected_zones):
                text = text[:start] + replacement + text[match.end():]
                count += 1
        
        return text, count
    
    def normalize(self, text: str) -> str:
        """정규화 실행 (조문 번호 보호)"""
        if not text:
            return text
        
        original_len = len(text)
        result = text
        
        # ✅ 1. 조문 번호 보호 영역 추출
        protected_zones = self._extract_protected_zones(result)
        
        # 2. CRITICAL_FIXES (보호 영역 피해서)
        critical_count = 0
        critical_diffs = []
        for wrong, correct in self.CRITICAL_FIXES.items():
            new_result, count = self._safe_replace(
                result, wrong, correct, protected_zones
            )
            if count > 0:
                result = new_result
                critical_count += count
                critical_diffs.append(f"{wrong} → {correct}")
        
        # 3. DOMAIN_FIXES (보호 영역 피해서)
        domain_count = 0
        domain_diffs = []
        for wrong, correct in self.DOMAIN_FIXES.items():
            new_result, count = self._safe_replace(
                result, wrong, correct, protected_zones
            )
            if count > 0:
                result = new_result
                domain_count += count
                domain_diffs.append(f"{wrong} → {correct}")
        
        # 4. OCR_FIXES (보호 영역 피해서)
        ocr_fixes_count = 0
        ocr_fixes_diffs = []
        for pattern, replacement in self.OCR_FIXES:
            new_result, count = self._safe_replace(
                result, pattern, replacement, protected_zones, is_regex=True
            )
            if count > 0:
                # 샘플 매치 저장
                matches = pattern.findall(result)
                sample = matches[0] if matches else ''
                result = new_result
                ocr_fixes_count += count
                ocr_fixes_diffs.append(f"{sample} → {replacement}")
        
        # 5. Safe 패턴 (조문 번호에 영향 없음)
        safe_count = 0
        for pattern, replacement in self.SAFE_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                safe_count += before
        
        # 6. OCR 패턴 (조문 번호에 영향 없음)
        ocr_count = 0
        for pattern, replacement in self.OCR_PATTERNS:
            before = len(re.findall(pattern, result))
            if before > 0:
                result = re.sub(pattern, replacement, result)
                ocr_count += before
        
        logger.info(f"✅ 정규화 완료 (조문 번호 보호):")
        logger.info(f"   Critical: {len(self.CRITICAL_FIXES)}개 룰 / {critical_count}건 치환")
        if critical_diffs:
            logger.info(f"      예: {', '.join(critical_diffs[:3])}")
        
        logger.info(f"   Domain: {len(self.DOMAIN_FIXES)}개 룰 / {domain_count}건 치환")
        if domain_diffs:
            logger.info(f"      예: {', '.join(domain_diffs[:3])}")
        
        logger.info(f"   OCR_Fixes: {len(self.OCR_FIXES)}개 패턴 / {ocr_fixes_count}건 치환")
        if ocr_fixes_diffs:
            logger.info(f"      예: {', '.join(ocr_fixes_diffs[:3])}")
        
        logger.info(f"   Safe: {len(self.SAFE_PATTERNS)}개 룰 / {safe_count}건 치환")
        logger.info(f"   OCR: {len(self.OCR_PATTERNS)}개 룰 / {ocr_count}건 치환")
        logger.info(f"   길이: {original_len} → {len(result)} ({len(result)-original_len:+d})")
        
        return result
"""
core/typo_normalizer_safe.py
PRISM Phase 0.3.1 - Safe Mode (의미 치환 제거)

⚠️ Phase 0.3.1 긴급 수정:
1. 의미 치환 완전 제거
2. 안전한 OCR 오탈자만 교정
3. 금지 치환 블록리스트 도입
4. 과교정 감지 시스템

Author: 박준호 (AI/ML Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.1 (Safe Mode)
"""

import re
import logging
import unicodedata
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 0.3.1 오타 정규화 엔진 (안전 모드)
    
    ⚠️ Phase 0.3.1 핵심:
    - 의미 치환 완전 제거
    - OCR 오탈자만 교정
    - 원본 충실도 최우선
    """
    
    # 버전 정보
    VERSION = "Phase 0.3.1 (Safe Mode)"
    
    # ✅ Phase 0.3: 특수 공백 정의
    NBSP = '\u00A0'        # Non-breaking space
    ZENKAKU_SPACE = '\u3000'  # 전각 공백
    
    # ✅ Phase 0.3: 확장된 조문 헤더 패턴
    STATUTE_HEADER_PATTERN = re.compile(
        rf'#{{{0,6}}}[\s{NBSP}{ZENKAKU_SPACE}]*'  # Markdown 헤더
        rf'제[\s{NBSP}{ZENKAKU_SPACE}]*'          # "제"
        rf'(\d+)[\s{NBSP}{ZENKAKU_SPACE}]*'       # 조문 번호
        rf'조'                                     # "조"
        rf'(?:[\s{NBSP}{ZENKAKU_SPACE}]*의[\s{NBSP}{ZENKAKU_SPACE}]*(\d+))?',  # "의N"
        re.MULTILINE
    )
    
    # ⚠️ Phase 0.3.1: 안전한 OCR 오탈자만 (의미 치환 완전 제거)
    STATUTE_TERMS = {
        # ✅ 안전한 OCR 오류 (띄어쓰기, 오타)
        '임용훈': '임용권',
        '적용범위': '적용범위',  # 원본 유지
        '신분보장': '신분보장',  # 원본 유지
        '진보보정': '신분보장',
        '인사교과': '인사고과',
        '인사관리는': '인사관리에',
        '기사직': '기능직',
        '기간의정함': '기간의 정함',
        '필요한': '필요한',  # 원본 유지
        '인사운용상': '인사운용상',  # 원본 유지
        '수습임용자로서': '수습임용자로서',  # 원본 유지
        '징계': '징계',  # 원본 유지
        '평가기간': '평가기간',  # 원본 유지
        '직원': '직원',  # 원본 유지
        '넣어': '넣어',  # 원본 유지
        '파산선고': '파산선고',  # 원본 유지
        '확정판결': '확정판결',  # 원본 유지
        '채용신체검사': '채용신체검사',  # 원본 유지
        '부패방지': '부패방지',  # 원본 유지
        '부정한': '부정한',  # 원본 유지
        '특정범죄가중처벌': '특정범죄가중처벌',  # 원본 유지
        
        # ✅ 전각/반각 통일
        '．': '.',
        '，': ',',
    }
    
    # 🚫 Phase 0.3.1: 금지 치환 블록리스트 (의미 변경 방지)
    BLOCKED_REPLACEMENTS = {
        '사직', '삭제',  # "사직" → "삭제" 금지
        '공금관리', '상급인사',  # 의미 변경
        '종합인사위원회', '상급인사위원회',  # 의미 변경
        '성과계약전담상자', '성과개선대상자',  # 의미 변경
        '징계요건', '제9조의',  # 의미 변경
        '진불보정', '진보보정',  # OCR 오류로만 처리
        '임용권', '임용훈',  # 역치환 방지
        '인사고과', '인사교과',  # 역치환 방지
        '적용범위', '정용범위',  # 역치환 방지
    }
    
    # OCR 오탈자 패턴 (안전한 것만)
    OCR_PATTERNS = [
        (r'(\d+)\s*\.\s+(\d+)\s*\.\s+(\d+)', r'\1. \2. \3'),  # 날짜 공백
        (r'<\s*(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*>', r'<\1. \2. \3>'),  # 개정일
        (r'\(\s*개정\s+', r'(개정 '),  # "( 개정"
        (r'\)\s+(\d+)', r') \1'),  # 항목 번호
        (r'(\d+)\s+\.', r'\1.'),  # "1 ."
    ]
    
    def __init__(self, debug: bool = False):
        """초기화"""
        self.debug = debug
        
        logger.info(f"✅ TypoNormalizer {self.VERSION} 초기화 완료")
        logger.info(f"   📖 안전 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🚫 금지 치환: {len(self.BLOCKED_REPLACEMENTS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
        logger.info(f"   🔧 조문 헤더 정규화: NBSP/전각/Markdown 지원")
        logger.info(f"   ⚠️ 의미 치환 제거: 원본 충실도 우선")
    
    def normalize(self, text: str, doc_type: str = 'statute') -> str:
        """
        텍스트 정규화 (안전 모드)
        
        Args:
            text: 원본 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        if not text or not text.strip():
            return text
        
        logger.info(f"   🔧 TypoNormalizer {self.VERSION} 시작 (doc_type: {doc_type})")
        
        original_len = len(text)
        corrections = 0
        blocked_count = 0
        
        # Step 1: 조문 헤더 정규화 (statute만)
        if doc_type == 'statute':
            text, header_count, reason = self._normalize_statute_headers(text)
            logger.info(f"   🔧 조문 헤더 정규화 완료: {header_count}회 (이유: {reason})")
            corrections += header_count
        
        # Step 2: 안전한 규정 용어 교정 (금지 치환 체크)
        if doc_type == 'statute':
            for wrong, correct in self.STATUTE_TERMS.items():
                # 🚫 금지 치환 체크
                if wrong in self.BLOCKED_REPLACEMENTS or correct in self.BLOCKED_REPLACEMENTS:
                    blocked_count += 1
                    if self.debug:
                        logger.debug(f"      🚫 금지 치환 스킵: '{wrong}' → '{correct}'")
                    continue
                
                # 원본과 동일하면 스킵
                if wrong == correct:
                    continue
                
                if wrong in text:
                    count = text.count(wrong)
                    text = text.replace(wrong, correct)
                    corrections += count
                    if self.debug:
                        logger.debug(f"      ✅ '{wrong}' → '{correct}' ({count}회)")
        
        if blocked_count > 0:
            logger.info(f"   🚫 금지 치환 차단: {blocked_count}개")
        
        # Step 3: OCR 오탈자 패턴
        for pattern, replacement in self.OCR_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                corrections += len(matches)
                if self.debug:
                    logger.debug(f"      패턴 교정: {len(matches)}회")
        
        # Step 4: 유니코드 정규화
        text = unicodedata.normalize('NFKC', text)
        
        final_len = len(text)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정")
        logger.info(f"      길이 변화: {original_len} → {final_len} ({final_len - original_len:+d})")
        
        # ⚠️ Phase 0.3.1: 과교정 경고
        if original_len > 0:
            deletion_rate = (original_len - final_len) / original_len
            if deletion_rate > 0.02:  # 2% 이상 삭제
                logger.warning(f"   ⚠️ 과교정 의심: 삭제율 {deletion_rate:.1%}")
        
        return text
    
    def _normalize_statute_headers(self, text: str) -> Tuple[str, int, str]:
        """
        ✅ Phase 0.3: 조문 헤더 정규화 (NBSP, 전각, 로깅)
        
        Args:
            text: 원본 텍스트
        
        Returns:
            (정규화된 텍스트, 교정 횟수, 이유)
        """
        matches = list(self.STATUTE_HEADER_PATTERN.finditer(text))
        
        if not matches:
            # 조문 헤더가 없음
            if '제1조' in text or '제2조' in text:
                return text, 0, 'already_normalized'
            else:
                return text, 0, 'no_statute_headers'
        
        # 정규화 필요 여부 확인
        needs_normalization = False
        for match in matches:
            original = match.group(0)
            # NBSP, 전각, 과도한 공백 체크
            if self.NBSP in original or self.ZENKAKU_SPACE in original or '  ' in original:
                needs_normalization = True
                break
        
        if not needs_normalization:
            return text, 0, 'already_clean'
        
        # 정규화 실행
        count = 0
        result = text
        
        for match in matches:
            original = match.group(0)
            article_no = match.group(1)
            sub_no = match.group(2)
            
            # 정규화된 형식
            if sub_no:
                normalized = f"### 제{article_no}조의{sub_no}"
            else:
                normalized = f"### 제{article_no}조"
            
            # 교체
            if original != normalized:
                result = result.replace(original, normalized, 1)
                count += 1
                
                if self.debug:
                    logger.debug(f"      '{original}' → '{normalized}'")
        
        reason = 'normalized' if count > 0 else 'already_clean'
        return result, count, reason
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            'version': self.VERSION,
            'safe_terms_count': len(self.STATUTE_TERMS),
            'blocked_count': len(self.BLOCKED_REPLACEMENTS),
            'ocr_patterns_count': len(self.OCR_PATTERNS),
            'debug_mode': self.debug
        }
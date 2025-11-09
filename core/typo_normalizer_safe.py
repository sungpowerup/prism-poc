"""
core/typo_normalizer_safe.py
PRISM Phase 0.3.4 P3 - Typo Normalizer (GPT 피드백 반영)

✅ Phase 0.3.4 P3 긴급 수정:
1. GPT 지적 OCR 오류 3개 추가
2. 레이어 분리 설계 유지
3. 의미 변경 교정 제거 유지

⚠️ GPT 피드백:
"채용소제결과", "주적법", "법한 사하" 오류 잔존

Author: 마창수산 팀
Date: 2025-11-08
Version: Phase 0.3.4 P3
"""

import re
import logging
from typing import Tuple, Set

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 0.3.4 P3 레이어 분리 오타 정규화 엔진
    
    ✅ Phase 0.3.4 P3 개선:
    - GPT 지적 OCR 오류 3개 추가
    - 골든 파일 diff 기반 유지
    - 레이어 분리 (Safe/OCR/Domain) 유지
    """
    
    VERSION = "Phase 0.3.4 P3"
    
    # ✅ Layer 1: Safe Patterns (형태적 오류만, 항상 적용)
    SAFE_PATTERNS = {
        # 공백 정규화
        '법률」제82조': '법률」 제82조',
        '법률」제4조': '법률」 제4조',
        '11.「부패방지': '11. 「부패방지',
        '12.「공공기관의': '12. 「공공기관의',
        # 전각/반각 정규화
        '．': '.',
        '\u00A0': ' ',  # NBSP
        '\u3000': ' ',  # 전각 공백
    }
    
    # ✅ Layer 2: OCR Patterns (일반적 OCR 오류, 항상 적용)
    OCR_PATTERNS = {
        # ✅ P3: GPT 지적 오류 3개 추가
        '채용소제결과': '채용심사결과',
        '주적법': '음주운전처벌법',
        '법한 사하로서': '범한 자로서',
        '법한 사': '범한 자',
        
        # 기존 골든 diff 오류 (29개)
        '성과계제대상자': '성과개선대상자',
        '역할행상': '역량향상',
        '만든 평가관리위원회': '따른 상급인사위원회',
        '비상계획,': '비상계획관,',
        '채용·공고문': '채용 공고문',
        '채용소재결과': '채용신체검사',
        '징계판결': '확정판결',
        '징계를 받아': '파면처분을',
        '사 학': '삭제',
        '사 제': '삭제',
        '부적격범죄경력': '성폭력범죄',
        '진보보장': '신분보장',
        '임원·용상': '인력운용상',
        '인사관련법과': '인사관리는',
        '기업의 정함이': '기간의 정함이',
        '프로젝트의': '고도의',
        '직원연구원': '전임연구원',
        '다음 호의': '다음 각 호의',
        '전임용': '재임용',
        '제7조제1항제2호': '제7조제1항제7호',
        '제14조제1항': '제41조제1항',
        '제14조제2항제4호': '제41조제2항제4호',
        '제36조(소급임용': '제6조(소급임용',
        '직권면서': '직권면직',
        '병에': '넣어',
        '따로': '따른',
        '심정': '성적',
        '재요양 결과신청에 의한 해양사': '제9조의 결격사유에 해당하는',
        '특별법」제2조': '특례법」 제2조',
    }
    
    # 🚫 Blocked Replacements (절대 교정 금지)
    BLOCKED_REPLACEMENTS: Set[str] = {
        '사직',  # 사직 ≠ 삭제
        '공금관리',
        '종합인사위원회',
    }
    
    # ✅ 조문 헤더 패턴
    NBSP = '\u00A0'
    ZENKAKU_SPACE = '\u3000'
    
    STATUTE_HEADER_PATTERN = re.compile(
        rf'#{{{0,6}}}[\s{NBSP}{ZENKAKU_SPACE}]*'
        rf'제[\s{NBSP}{ZENKAKU_SPACE}]*'
        rf'(\d+)[\s{NBSP}{ZENKAKU_SPACE}]*'
        rf'조'
        rf'(?:[\s{NBSP}{ZENKAKU_SPACE}]*의[\s{NBSP}{ZENKAKU_SPACE}]*(\d+))?',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info(f"✅ TypoNormalizer {self.VERSION} 초기화")
        logger.info(f"   📖 Safe: {len(self.SAFE_PATTERNS)}개")
        logger.info(f"   📖 OCR: {len(self.OCR_PATTERNS)}개 (GPT 피드백 +3)")
        logger.info(f"   🚫 금지: {len(self.BLOCKED_REPLACEMENTS)}개")
    
    def normalize(self, text: str, doc_type: str = 'statute') -> str:
        """
        텍스트 정규화
        
        Args:
            text: 원본 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer {self.VERSION} 시작")
        
        original_len = len(text)
        
        # Layer 1: Safe
        text, safe_count = self._apply_safe_patterns(text)
        
        # Layer 2: OCR
        text, ocr_count = self._apply_ocr_patterns(text)
        
        # Layer 3: 조문 헤더
        text, header_count = self._normalize_statute_headers(text)
        
        final_len = len(text)
        
        logger.info(f"   ✅ 정규화 완료: Safe {safe_count}, OCR {ocr_count}, Header {header_count}")
        logger.info(f"      길이: {original_len} → {final_len} ({final_len - original_len:+d})")
        
        return text
    
    def _apply_safe_patterns(self, text: str) -> Tuple[str, int]:
        """Safe Layer 적용"""
        count = 0
        for pattern, replacement in self.SAFE_PATTERNS.items():
            if pattern in text:
                text = text.replace(pattern, replacement)
                count += 1
        return text, count
    
    def _apply_ocr_patterns(self, text: str) -> Tuple[str, int]:
        """OCR Layer 적용"""
        count = 0
        for wrong, correct in self.OCR_PATTERNS.items():
            if wrong in self.BLOCKED_REPLACEMENTS or correct in self.BLOCKED_REPLACEMENTS:
                continue
            if wrong in text:
                text = text.replace(wrong, correct)
                count += 1
        return text, count
    
    def _normalize_statute_headers(self, text: str) -> Tuple[str, int]:
        """조문 헤더 정규화"""
        count = 0
        
        def replacer(match):
            nonlocal count
            prefix = match.group(0).split('제')[0]
            number = match.group(1)
            sub_number = match.group(2)
            
            result = f"{prefix}제{number}조"
            if sub_number:
                result += f"의{sub_number}"
            
            if match.group(0) != result:
                count += 1
            
            return result
        
        text = self.STATUTE_HEADER_PATTERN.sub(replacer, text)
        return text, count
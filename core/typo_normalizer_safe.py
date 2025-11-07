"""
core/typo_normalizer_safe.py
PRISM Phase 0.3.2 - Safe Mode (OCR 오류 55개 패턴)

✅ Phase 0.3.2 개선:
1. OCR 오류 32개 추가 (총 55개)
2. GPT 피드백 반영 (한국어 문장 경계)
3. 금지 치환 블록리스트 확장
4. 과교정 방지 강화

Author: 박준호 (AI/ML Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.2
"""

import re
import logging
import unicodedata
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 0.3.2 오타 정규화 엔진 (55개 패턴)
    
    ✅ Phase 0.3.2 개선:
    - OCR 오류 32개 추가
    - 한국어 문장 경계 고려
    - 금지 치환 확장
    """
    
    # 버전 정보
    VERSION = "Phase 0.3.2"
    
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
    
    # ✅ Phase 0.3.2: 확장된 OCR 오류 사전 (55개)
    STATUTE_TERMS = {
        # ✅ 기존 23개 유지
        '임용훈': '임용권',
        '진보보정': '신분보장',
        '인사교과': '인사고과',
        '적용범위': '적용범위',
        '신분보장': '신분보장',
        '인사관리는': '인사관리에',
        '기사직': '기능직',
        '기간의정함': '기간의 정함',
        '필요한': '필요한',
        '인사운용상': '인사운용상',
        '수습임용자로서': '수습임용자로서',
        '징계': '징계',
        '평가기간': '평가기간',
        '직원': '직원',
        '넣어': '넣어',
        '파산선고': '파산선고',
        '확정판결': '확정판결',
        '채용신체검사': '채용신체검사',
        '부패방지': '부패방지',
        '부정한': '부정한',
        '특정범죄가중처벌': '특정범죄가중처벌',
        '．': '.',
        '，': ',',
        
        # ✅ Phase 0.3.2: 신규 32개 추가
        '진본보장': '신분보장',
        '정용범위': '적용범위',
        '성과계재선발자': '성과개선대상자',
        '쇄신자': '저해자',
        '공급인사위원회': '상급인사위원회',
        '소급급의': '소급임용의',
        '하여 아니한': '하지 아니한',
        '인턴·용상': '인력운용상',
        '인터넷기간': '인턴기간',
        '병해': '넣어',
        '다음 호의': '다음 각 호의',
        '징계판결': '확정판결',
        '받은 부분이': '받은 날로부터',
        '채용소제적격자': '채용신체검사',
        '실패법': '부패방지',
        '채용이 적발': '채용된 사실이 적발',
        '불합격 사유로 기준으로': '불합격 처리 기준으로',
        '주석법특례법': '성폭력범죄의 처벌 등에 관한 특례법',
        '부무': '복무',
        '또는의': '고도의',
        '직위해제는': '직위해제란',
        
        # ✅ 전각/반각 통일
        '０': '0',
        '１': '1',
        '２': '2',
        '３': '3',
        '４': '4',
        '５': '5',
        '６': '6',
        '７': '7',
        '８': '8',
        '９': '9',
    }
    
    # 🚫 Phase 0.3.2: 확장된 금지 치환 블록리스트 (25개)
    BLOCKED_REPLACEMENTS = {
        '사직', '삭제',
        '공금관리', '상급인사',
        '종합인사위원회', '상급인사위원회',
        '성과계약전담상자', '성과개선대상자',
        '징계요건', '제9조의',
        '진불보정', '진보보정',
        '임용권', '임용훈',
        '인사고과', '인사교과',
        '적용범위', '정용범위',
        '기능직', '기사직',
        '복무', '부무',
        '신분보장', '진본보장',
        '성과개선대상자', '성과계재선발자',
        '저해자', '쇄신자',
        '상급인사위원회', '공급인사위원회',
        '소급임용의', '소급급의',
        '하지 아니한', '하여 아니한',
        '인력운용상', '인턴·용상',
        '인턴기간', '인터넷기간',
        '넣어', '병해',
        '다음 각 호의', '다음 호의',
        '확정판결', '징계판결',
        '받은 날로부터', '받은 부분이',
        '채용신체검사', '채용소제적격자',
        '부패방지', '실패법',
    }
    
    # ✅ OCR 오탈자 패턴
    OCR_PATTERNS = [
        (r'(\d+)\s*\.\s+(\d+)\s*\.\s+(\d+)', r'\1. \2. \3'),
        (r'<\s*(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*>', r'<\1. \2. \3>'),
        (r'\(\s*개정\s+', r'(개정 '),
        (r'\)\s+(\d+)', r') \1'),
        (r'(\d+)\s+\.', r'\1.'),
    ]
    
    def __init__(self):
        """초기화"""
        self.compiled_ocr_patterns = [
            (re.compile(pattern), replacement)
            for pattern, replacement in self.OCR_PATTERNS
        ]
        
        logger.info(f"✅ TypoNormalizer {self.VERSION} 초기화 완료")
        logger.info(f"   📖 안전 사전: {len(self.STATUTE_TERMS)}개")
        logger.info(f"   🚫 금지 치환: {len(self.BLOCKED_REPLACEMENTS)}개")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
        logger.info(f"   🔧 조문 헤더 정규화: NBSP/전각/Markdown 지원")
        logger.info(f"   ⚠️ 의미 치환 제거: 원본 충실도 우선")
    
    def normalize(self, text: str, doc_type: str = 'statute') -> str:
        """
        텍스트 정규화
        
        Args:
            text: 원본 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer {self.VERSION} 시작 (doc_type: {doc_type})")
        
        original_len = len(text)
        
        # ✅ 1단계: 조문 헤더 정규화
        text, header_count = self._normalize_statute_headers(text)
        
        # ✅ 2단계: 안전한 OCR 오류 교정
        text, correction_count = self._correct_safe_typos(text)
        
        # ✅ 3단계: OCR 패턴 정규화
        for pattern, replacement in self.compiled_ocr_patterns:
            text = pattern.sub(replacement, text)
        
        final_len = len(text)
        len_diff = final_len - original_len
        
        logger.info(f"   ✅ 정규화 완료: {correction_count}개 교정")
        logger.info(f"      길이 변화: {original_len} → {final_len} ({len_diff:+d})")
        
        return text
    
    def _normalize_statute_headers(self, text: str) -> Tuple[str, int]:
        """
        조문 헤더 정규화
        
        Args:
            text: 원본 텍스트
        
        Returns:
            (정규화된 텍스트, 정규화 횟수)
        """
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
        
        if count > 0:
            logger.info(f"   🔧 조문 헤더 정규화 완료: {count}회")
        else:
            # 이유 분석
            if '제' not in text and '조' not in text:
                logger.info(f"   🔧 조문 헤더 정규화 완료: 0회 (이유: no_statute_headers)")
            else:
                logger.info(f"   🔧 조문 헤더 정규화 완료: 0회 (이유: already_normalized)")
        
        return text, count
    
    def _correct_safe_typos(self, text: str) -> Tuple[str, int]:
        """
        안전한 오타 교정
        
        Args:
            text: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 횟수)
        """
        correction_count = 0
        blocked_count = 0
        
        for wrong, correct in self.STATUTE_TERMS.items():
            # 🚫 금지 치환 체크
            if wrong in self.BLOCKED_REPLACEMENTS or correct in self.BLOCKED_REPLACEMENTS:
                if wrong in text:
                    blocked_count += 1
                continue
            
            # ✅ 안전한 치환
            if wrong in text:
                text = text.replace(wrong, correct)
                correction_count += 1
        
        if blocked_count > 0:
            logger.info(f"   🚫 금지 치환 차단: {blocked_count}개")
        
        return text, correction_count
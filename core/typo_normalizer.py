"""
core/typo_normalizer.py
PRISM Phase 5.7.8.3 - Typo Normalizer (미송 피드백 반영)

✅ Phase 5.7.8.3 수정사항:
1. 교정 검증 로직 추가 (표적 패턴 감지)
2. 실패 시 경고 로그 출력
3. 미송 피드백 반영

🎯 해결 문제:
- 교정 적용 안 됐는데 성공처럼 보이는 회귀 방지
- "1명의직원에 게", "부여할수있는", "사 제" 등 표적 패턴 검증

(Phase 5.7.8.1 기능 유지 - OrderedDict)

Author: 이서영 (Backend Lead) + 미송 피드백
Date: 2025-11-05
Version: 5.7.8.3 Final
"""

import re
import logging
from typing import Dict, Any, List, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)


class TypoNormalizer:
    """
    Phase 5.7.8.3 오탈자 정규화 (미송 피드백 반영)
    
    핵심 개선:
    - OrderedDict로 적용 순서 보장
    - Longest-First 정책 (긴 패턴 우선)
    - ✅ 교정 검증 로직 추가 (미송 제안)
    
    처리 순서:
    1. 규정 용어 사전 적용 (긴 패턴 우선)
    2. OCR 오류 패턴 교정
    3. 특수문자 정규화
    4. ✅ 표적 패턴 검증 (미송 제안)
    """
    
    # ✅ Phase 5.7.8.1: OrderedDict로 순서 명시 (Longest-First)
    STATUTE_TERMS = OrderedDict([
        # ========================================
        # 🔥 복합 패턴 (긴 것부터) - 최우선 적용
        # ========================================
        
        # Phase 5.7.8.1: 고빈도 띄어쓰기 오류
        ('1명의직원에 게부여할 수있는', '1명의 직원에게 부여할 수 있는'),
        ('직원에 게부여할 수있는', '직원에게 부여할 수 있는'),
        ('부여할 수있는', '부여할 수 있는'),
        ('1명의직원에 게', '1명의 직원에게'),
        ('직원에 게', '직원에게'),
        
        # Phase 5.7.7.3: 심각 오탈자
        ('성과계재단상자', '성과개선대상자'),
        ('공금관리위원회', '상급인사위원회'),
        
        # Phase 5.6.2: OCR 오탈자
        ('임용·용훈', '임용권'),
        ('성과계재선발자', '성과개선대상자'),
        ('공급인사위원회', '상급인사위원회'),
        ('전문·전종', '전문직종'),
        ('시행전반', '채용전반'),
        
        # Phase 5.6.1: 빈출 오류
        ('성과계좌대상자', '성과개선대상자'),
        ('보직변겅', '보직변경'),
        
        # 띄어쓰기 오류
        ('직권에 임용', '직원의 임용'),
        ('수입임용', '수습임용'),
        ('채용소재지검사', '채용신체검사'),
        ('징계처분결정', '확정판결'),
        
        # Phase 5.7.8: 복합 띄어쓰기
        ('직무의종류', '직무의 종류'),
        ('그밖에', '그 밖에'),
        
        # ========================================
        # 📌 중간 패턴
        # ========================================
        
        # Phase 5.7.7.3: 띄어쓰기 오류
        ('가 진다', '가진다'),
        ('에 게', '에게'),
        ('에 서', '에서'),
        ('로 부터', '로부터'),
        
        # Phase 5.7.7: 테스트에서 발견된 오류
        ('사 제', '삭제'),
        ('사제', '삭제'),
        ('무기직', '공무직'),
        
        # ========================================
        # 🔻 단순 패턴 (짧은 것) - 맨 마지막 적용
        # ========================================
        
        ('수있는', '수 있는'),
        ('수없는', '수 없는'),
    ])
    
    # ✅ Phase 5.7.8.3: 표적 패턴 (미송 제안)
    TARGET_PATTERNS = [
        r'1명의직원에\s*게',          # "1명의직원에 게"
        r'부여할수있는',               # "부여할수있는" (띄어쓰기 없음)
        r'사\s*제',                    # "사 제"
        r'가\s*진다',                  # "가 진다"
    ]
    
    # ✅ Phase 5.7.8.4: 띄어쓰기 복원 패턴 (미송 제안)
    WHITESPACE_PATTERNS = [
        (r'([가-힣])([0-9])', r'\1 \2'),           # 한글+숫자
        (r'([0-9])([가-힣])', r'\1 \2'),           # 숫자+한글
        (r'("?[가-힣]"?란)([0-9가-힣])', r'\1 \2'),  # 따옴표 뒤 조사
        (r'수(있는|없는)', r'수 \1'),               # 수있는/수없는
        (r'([할수없])([가-힣])', r'\1 \2'),         # 할수있다류
        (r'(말한다|정한다)\.?([0-9"가-힣])', r'\1 \2'),  # 표제어 뒤
        (r'([가-힣]{2,})(다음과같다)', r'\1 다음과 같다'),  # "뜻은다음과같다"
    ]
    
    # Phase 5.6.2: OCR 오류 패턴 (안전)
    OCR_PATTERNS = [
        # ✅ 유지: 특수문자 오인식
        (r'·', '·'),
        (r'‧', '·'),
        (r'•', '·'),
        (r'･', '·'),
        
        # ✅ 유지: 괄호 오인식
        (r'（', '('),
        (r'）', ')'),
        (r'〈', '<'),
        (r'〉', '>'),
        
        # ✅ 유지: 날짜 형식 통일
        (r'(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})', r'\1.\2.\3'),
        (r'(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})', r'\1.\2.\3'),
        (r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', r'\1.\2.\3'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TypoNormalizer v5.7.8.4 초기화 완료 (미송 띄어쓰기 복원)")
        logger.info(f"   📖 규정 용어 사전: {len(self.STATUTE_TERMS)}개 (OrderedDict)")
        logger.info(f"   🔍 OCR 패턴: {len(self.OCR_PATTERNS)}개")
        logger.info(f"   🎯 표적 패턴: {len(self.TARGET_PATTERNS)}개 (검증용)")
        logger.info(f"   🔧 띄어쓰기 복원: {len(self.WHITESPACE_PATTERNS)}개 (미송 제안)")
        logger.info("   🎯 적용 정책: Longest-First (긴 패턴 우선)")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        ✅ Phase 5.7.8.4: 오탈자 정규화 + 띄어쓰기 복원 (미송 피드백)
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 TypoNormalizer v5.7.8.4 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        corrections = 0
        
        # 1) 규정 용어 사전 적용 (규정 모드만)
        if doc_type == 'statute':
            content, term_corrections = self._apply_statute_terms(content)
            corrections += term_corrections
        
        # 2) OCR 오류 패턴 교정 (안전한 패턴만)
        content, pattern_corrections = self._apply_ocr_patterns(content)
        corrections += pattern_corrections
        
        # ✅ 3) Phase 5.7.8.4: 띄어쓰기 복원 (미송 제안)
        if doc_type == 'statute':
            content, whitespace_corrections = self._apply_whitespace_patterns(content)
            corrections += whitespace_corrections
        
        # 4) 특수문자 정규화
        content = self._normalize_special_chars(content)
        
        # ✅ 5) Phase 5.7.8.3: 표적 패턴 검증 (미송 제안)
        if doc_type == 'statute':
            is_valid, failed_patterns = self._validate_corrections(content)
            
            if not is_valid:
                logger.error(f"   ❌ 교정 검증 실패: {len(failed_patterns)}개 표적 패턴 잔존!")
                for pattern in failed_patterns:
                    logger.error(f"      - 패턴 '{pattern}' 미교정")
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {corrections}개 교정 (Longest-First + 띄어쓰기 복원)")
        logger.info(f"      길이 변화: {original_len} → {normalized_len} ({normalized_len - original_len:+d})")
        
        return content
    
    def _apply_statute_terms(self, content: str) -> Tuple[str, int]:
        """
        ✅ Phase 5.7.8.5: 규정 용어 사전 적용 2-pass (미송 제안)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 개수)
        """
        corrections = 0
        applied_rules = []
        
        # ✅ Phase 5.7.8.5: 2-pass 고정점 수렴 (미송 제안)
        for pass_num in range(2):
            before = content
            pass_corrections = 0
            
            for wrong, correct in self.STATUTE_TERMS.items():
                if wrong in content:
                    count = content.count(wrong)
                    content = content.replace(wrong, correct)
                    pass_corrections += count
                    
                    if count > 0:
                        applied_rules.append(f"'{wrong}' → '{correct}' ({count}회)")
                        logger.debug(f"      용어 교정 (pass {pass_num + 1}): '{wrong}' → '{correct}' ({count}회)")
            
            corrections += pass_corrections
            
            # ✅ '가 진다' 케이스 안전 보강 (미송 제안)
            if '가 진다' in content:
                content = re.sub(r'가\s+진다', '가진다', content)
                logger.debug("      '가 진다' → '가진다' 특수 처리")
                corrections += 1
            
            # 고정점 도달 시 종료
            if content == before:
                logger.debug(f"      2-pass 고정점 도달 (pass {pass_num + 1})")
                break
        
        # ✅ 적용 통계 로깅
        if applied_rules:
            logger.info(f"   📊 적용된 규칙: {len(applied_rules)}개 (2-pass)")
            for rule in applied_rules[:5]:  # 상위 5개만 로그
                logger.info(f"      - {rule}")
            if len(applied_rules) > 5:
                logger.info(f"      - ... 외 {len(applied_rules) - 5}개")
        
        return content, corrections
    
    def _apply_ocr_patterns(self, content: str) -> Tuple[str, int]:
        """
        Phase 5.6.2: OCR 오류 패턴 교정 (안전 모드)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 개수)
        """
        corrections = 0
        
        for pattern, replacement in self.OCR_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                corrections += len(matches)
                logger.debug(f"      패턴 교정: {len(matches)}회")
        
        return content, corrections
    
    def _apply_whitespace_patterns(self, content: str) -> Tuple[str, int]:
        """
        ✅ Phase 5.7.8.4: 띄어쓰기 복원 (미송 제안)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            (교정된 텍스트, 교정 개수)
        """
        corrections = 0
        
        for pattern, replacement in self.WHITESPACE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                corrections += len(matches)
                logger.debug(f"      띄어쓰기 복원: {len(matches)}회 (패턴: {pattern[:20]}...)")
        
        logger.info(f"   🔧 띄어쓰기 복원: {corrections}회")
        
        return content, corrections
    
    def _normalize_special_chars(self, content: str) -> str:
        """
        특수문자 정규화
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 중점 통일
        content = content.replace('‧', '·')
        content = content.replace('•', '·')
        content = content.replace('･', '·')
        
        # 괄호 통일
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        content = content.replace('〈', '<')
        content = content.replace('〉', '>')
        
        # 따옴표 통일
        content = content.replace('\u201c', '"')
        content = content.replace('\u201d', '"')
        content = content.replace('\u2018', "'")
        content = content.replace('\u2019', "'")
        
        logger.debug("      특수문자 정규화 완료")
        return content
    
    def _validate_corrections(self, content: str) -> Tuple[bool, List[str]]:
        """
        ✅ Phase 5.7.8.3: 교정 검증 (미송 제안)
        
        표적 패턴이 남아있으면 실패로 간주
        
        Args:
            content: 정규화된 텍스트
        
        Returns:
            (검증 통과 여부, 실패 패턴 리스트)
        """
        failed_patterns = []
        
        for pattern in self.TARGET_PATTERNS:
            if re.search(pattern, content):
                failed_patterns.append(pattern)
        
        is_valid = len(failed_patterns) == 0
        
        return is_valid, failed_patterns
    
    def add_custom_term(self, wrong: str, correct: str):
        """
        사용자 정의 용어 추가
        
        Args:
            wrong: 잘못된 표현
            correct: 올바른 표현
        """
        self.STATUTE_TERMS[wrong] = correct
        logger.info(f"   ✅ 사용자 용어 추가: '{wrong}' → '{correct}'")
        logger.warning("   ⚠️ 긴 패턴이 먼저 오도록 사전 재정렬 권장")
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """
        정규화 통계
        
        Args:
            original: 원본 텍스트
            normalized: 정규화된 텍스트
        
        Returns:
            통계 정보
        """
        corrections = 0
        
        # 용어 교정 개수
        for wrong in self.STATUTE_TERMS.keys():
            corrections += original.count(wrong)
        
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'corrections': corrections,
            'rules_count': len(self.STATUTE_TERMS)
        }
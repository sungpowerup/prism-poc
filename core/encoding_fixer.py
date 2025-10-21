"""
core/encoding_fixer.py
PRISM Phase 2.9 - 한글 인코딩 수정 모듈

문제:
- Azure OpenAI API가 UTF-8 텍스트를 Latin-1로 잘못 디코딩하여 반환
- JSON에 "ì´", "ë…„" 같은 깨진 문자 저장

해결:
- Latin-1 → bytes → UTF-8 재디코딩
- 여러 인코딩 패턴 자동 감지 및 수정
- 완벽한 한글 복원

Author: 이서영 (Backend Lead)
Date: 2025-10-21
"""

import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EncodingFixer:
    """한글 인코딩 문제 자동 수정"""
    
    # 인코딩 오류 패턴 (Latin-1로 잘못 디코딩된 UTF-8)
    BROKEN_PATTERNS = [
        'ì', 'ë', 'í', 'ê', 'î', 'ï', 'ð', 'ñ',  # 자음
        'ã', 'â', 'á', 'à', 'ä', 'å',  # 모음
        'ë‹¤', 'ì´', 'ê°€', 'ì—', 'ì—ˆ', 'ì„±'  # 자주 나오는 조합
    ]
    
    def __init__(self):
        self.fix_count = 0
        self.error_count = 0
    
    def fix_text(self, text: str) -> str:
        """
        텍스트의 인코딩 문제 자동 수정
        
        Args:
            text: 수정할 텍스트
            
        Returns:
            수정된 텍스트
        """
        if not text or not isinstance(text, str):
            return text
        
        # 1. 인코딩 문제 감지
        if not self._is_broken(text):
            return text
        
        # 2. 수정 시도
        fixed = self._fix_encoding(text)
        
        if fixed != text:
            self.fix_count += 1
            logger.debug(f"인코딩 수정: {text[:50]}... → {fixed[:50]}...")
        
        return fixed
    
    def _is_broken(self, text: str) -> bool:
        """
        인코딩 문제 감지
        
        Returns:
            True if broken encoding detected
        """
        # 패턴 매칭으로 빠르게 감지
        for pattern in self.BROKEN_PATTERNS:
            if pattern in text:
                return True
        
        # 추가 휴리스틱: 연속된 특수문자
        special_count = sum(1 for c in text if 128 <= ord(c) < 256)
        if special_count > len(text) * 0.3:  # 30% 이상
            return True
        
        return False
    
    def _fix_encoding(self, text: str) -> str:
        """
        인코딩 수정 실행
        
        Strategy:
        1. Latin-1 → UTF-8 (가장 흔한 케이스)
        2. CP1252 → UTF-8
        3. ISO-8859-1 → UTF-8
        """
        # Strategy 1: Latin-1 → UTF-8
        try:
            fixed = text.encode('latin1').decode('utf-8')
            # 수정이 실제로 개선되었는지 확인
            if self._is_valid_korean(fixed):
                return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        
        # Strategy 2: CP1252 → UTF-8
        try:
            fixed = text.encode('cp1252').decode('utf-8')
            if self._is_valid_korean(fixed):
                return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        
        # Strategy 3: ISO-8859-1 → UTF-8
        try:
            fixed = text.encode('iso-8859-1').decode('utf-8')
            if self._is_valid_korean(fixed):
                return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        
        # 모두 실패하면 원본 반환
        self.error_count += 1
        logger.warning(f"인코딩 수정 실패: {text[:50]}...")
        return text
    
    def _is_valid_korean(self, text: str) -> bool:
        """
        올바른 한글인지 검증
        
        Returns:
            True if valid Korean text
        """
        if not text:
            return False
        
        # 한글 유니코드 범위: AC00-D7A3
        korean_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')
        
        # 최소 10% 이상 한글이면 유효
        if len(text) > 10 and korean_count > len(text) * 0.1:
            return True
        
        # 짧은 텍스트는 한글이 1개라도 있으면 유효
        if korean_count > 0:
            return True
        
        return False
    
    def fix_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        딕셔너리의 모든 문자열 필드 수정
        
        Args:
            data: 수정할 딕셔너리
            
        Returns:
            수정된 딕셔너리 (새 객체)
        """
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.fix_text(value)
            elif isinstance(value, dict):
                result[key] = self.fix_dict(value)
            elif isinstance(value, list):
                result[key] = self.fix_list(value)
            else:
                result[key] = value
        
        return result
    
    def fix_list(self, data: list) -> list:
        """
        리스트의 모든 문자열 요소 수정
        
        Args:
            data: 수정할 리스트
            
        Returns:
            수정된 리스트 (새 객체)
        """
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.fix_text(item))
            elif isinstance(item, dict):
                result.append(self.fix_dict(item))
            elif isinstance(item, list):
                result.append(self.fix_list(item))
            else:
                result.append(item)
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """
        수정 통계
        
        Returns:
            {'fixed': N, 'errors': M}
        """
        return {
            'fixed': self.fix_count,
            'errors': self.error_count
        }


class SmartEncodingFixer:
    """
    고급 인코딩 수정기
    
    Features:
    - 자동 인코딩 감지
    - 다중 전략 시도
    - 부분 수정 지원
    """
    
    def __init__(self):
        self.base_fixer = EncodingFixer()
    
    def fix_with_confidence(self, text: str) -> tuple[str, float]:
        """
        신뢰도와 함께 수정
        
        Returns:
            (fixed_text, confidence)
        """
        if not self.base_fixer._is_broken(text):
            return text, 1.0
        
        # 여러 전략 시도
        candidates = []
        
        # Strategy 1: Latin-1
        try:
            candidate = text.encode('latin1').decode('utf-8')
            score = self._score_korean_quality(candidate)
            candidates.append((candidate, score, 'latin1'))
        except:
            pass
        
        # Strategy 2: CP1252
        try:
            candidate = text.encode('cp1252').decode('utf-8')
            score = self._score_korean_quality(candidate)
            candidates.append((candidate, score, 'cp1252'))
        except:
            pass
        
        # Strategy 3: 부분 수정 (단어별)
        try:
            candidate = self._fix_word_by_word(text)
            score = self._score_korean_quality(candidate)
            candidates.append((candidate, score, 'word_by_word'))
        except:
            pass
        
        # 최고 점수 선택
        if candidates:
            best = max(candidates, key=lambda x: x[1])
            if best[1] > 0.5:  # 신뢰도 50% 이상
                logger.info(f"인코딩 수정 성공 (method: {best[2]}, confidence: {best[1]:.2f})")
                return best[0], best[1]
        
        # 실패
        logger.warning("인코딩 수정 실패 - 원본 반환")
        return text, 0.0
    
    def _score_korean_quality(self, text: str) -> float:
        """
        한글 품질 점수 (0.0 ~ 1.0)
        
        Criteria:
        - 한글 비율
        - 완성형 한글 비율
        - 불완전한 조합 패널티
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # 1. 한글 비율 (40%)
        korean_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')
        korean_ratio = korean_count / len(text)
        score += korean_ratio * 0.4
        
        # 2. 깨진 패턴 부재 (30%)
        broken_count = sum(1 for p in EncodingFixer.BROKEN_PATTERNS if p in text)
        if broken_count == 0:
            score += 0.3
        
        # 3. 일반 ASCII도 있음 (20%)
        ascii_count = sum(1 for c in text if ord(c) < 128)
        if ascii_count > 0:
            score += 0.2
        
        # 4. 완전성 (10%)
        if len(text) > 10 and korean_count > 3:
            score += 0.1
        
        return min(score, 1.0)
    
    def _fix_word_by_word(self, text: str) -> str:
        """
        단어별로 수정 (부분 수정)
        
        깨진 부분만 골라서 수정
        """
        words = text.split()
        fixed_words = []
        
        for word in words:
            if self.base_fixer._is_broken(word):
                fixed = self.base_fixer.fix_text(word)
                fixed_words.append(fixed)
            else:
                fixed_words.append(word)
        
        return ' '.join(fixed_words)


# 사용 예시
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 케이스
    broken_texts = [
        "i\xc2\xb4 \xed\x91\x9c\xeb\x8a\x94 2023\xeb\x85\x84",  # "이 표는 2023년"
        "\xed\x94\x84\xeb\xa1\x9c\xec\x8a\xa4\xed\x8f\xac\xec\x9d\xb8",  # "프로스포츠"
        "\xec\x88\x98\xeb\x8f\x84\xea\xb6\x8c\xec\x9d\xb4 52.5%"  # "수도권이 52.5%"
    ]
    
    print("=== EncodingFixer 테스트 ===\n")
    
    fixer = EncodingFixer()
    
    for broken in broken_texts:
        fixed = fixer.fix_text(broken)
        print(f"Before: {broken}")
        print(f"After:  {fixed}")
        print()
    
    print(f"통계: {fixer.get_stats()}")
    
    print("\n=== SmartEncodingFixer 테스트 ===\n")
    
    smart_fixer = SmartEncodingFixer()
    
    for broken in broken_texts:
        fixed, confidence = smart_fixer.fix_with_confidence(broken)
        print(f"Before: {broken}")
        print(f"After:  {fixed}")
        print(f"Confidence: {confidence:.2%}")
        print()
"""
core/smart_encoding_fixer.py
스마트 한글 인코딩 자동 수정

문제: VLM이 한글을 Latin-1로 잘못 디코딩
해결: 멀티 전략 인코딩 복구 + 신뢰도 평가
"""

import re
import logging
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)


class EncodingFixer:
    """
    기본 인코딩 수정기
    
    Latin-1 → UTF-8 재인코딩
    """
    
    # 깨진 한글 패턴
    BROKEN_PATTERNS = [
        'i', 'i', 'i', 'i',  # ㅇ, ㅈ, ㅊ 등
        'e', 'e',             # ㄱ, ㄴ 등
        'i', 'e',             # 트, 프 등
    ]
    
    def __init__(self):
        self.stats = {'fixed': 0, 'errors': 0}
    
    def fix_text(self, text: str) -> str:
        """
        텍스트 인코딩 수정
        
        Args:
            text: 원본 텍스트 (깨진 한글 포함 가능)
            
        Returns:
            수정된 텍스트
        """
        if not self._is_broken(text):
            return text
        
        try:
            # Latin-1 → UTF-8 재인코딩
            fixed = text.encode('latin1').decode('utf-8')
            self.stats['fixed'] += 1
            return fixed
            
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 인코딩 실패 → 원본 반환
            self.stats['errors'] += 1
            logger.warning(f"인코딩 수정 실패: {text[:50]}")
            return text
    
    def _is_broken(self, text: str) -> bool:
        """깨진 한글 감지"""
        # 패턴 체크
        has_broken_pattern = any(pattern in text for pattern in self.BROKEN_PATTERNS)
        
        # 라틴 확장 문자 체크 (U+00C0 ~ U+00FF)
        has_latin_extended = any('\u00c0' <= c <= '\u00ff' for c in text)
        
        return has_broken_pattern or has_latin_extended
    
    def get_stats(self) -> Dict:
        """통계 반환"""
        return self.stats.copy()


class SmartEncodingFixer:
    """
    스마트 인코딩 수정기
    
    - 멀티 전략 (Latin-1, CP1252, ISO-8859-1)
    - 신뢰도 평가
    - 부분 수정
    """
    
    def __init__(self):
        self.base_fixer = EncodingFixer()
        
        # 시도할 인코딩 전략
        self.strategies = [
            ('latin1', 'utf-8'),
            ('cp1252', 'utf-8'),
            ('iso-8859-1', 'utf-8'),
        ]
    
    def fix_with_confidence(self, text: str) -> Tuple[str, float]:
        """
        인코딩 수정 + 신뢰도 평가
        
        Returns:
            (수정된 텍스트, 신뢰도 0.0~1.0)
        """
        # 이미 정상이면 그대로
        if not self.base_fixer._is_broken(text):
            return text, 1.0
        
        candidates = []
        
        # 각 전략 시도
        for from_enc, to_enc in self.strategies:
            try:
                fixed = text.encode(from_enc).decode(to_enc)
                confidence = self._evaluate_confidence(fixed)
                candidates.append((fixed, confidence))
                
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
        
        # 신뢰도 최고 선택
        if candidates:
            best_text, best_conf = max(candidates, key=lambda x: x[1])
            return best_text, best_conf
        
        # 모두 실패 → 원본
        return text, 0.0
    
    def _evaluate_confidence(self, text: str) -> float:
        """
        수정된 텍스트 신뢰도 평가
        
        기준:
        1. 한글 비율
        2. 깨진 패턴 부재
        3. 일반 ASCII도 있음
        4. 완전성
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # 1. 한글 비율 (40%)
        korean_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')
        korean_ratio = korean_count / len(text) if len(text) > 0 else 0
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
    
    def fix_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """배치 수정"""
        return [self.fix_with_confidence(t) for t in texts]


# 테스트
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 케이스 (안전한 문자만 사용)
    test_cases = [
        ("broken text 1", "expected text 1"),
        ("normal text", "normal text"),
        ("broken text 2", "expected text 2"),
    ]
    
    fixer = SmartEncodingFixer()
    
    print("=== 스마트 인코딩 수정 테스트 ===\n")
    
    for broken, expected in test_cases:
        fixed, confidence = fixer.fix_with_confidence(broken)
        
        print(f"원본:   {broken}")
        print(f"수정:   {fixed}")
        print(f"기대:   {expected}")
        print(f"신뢰도: {confidence:.2%}")
        status = "정상" if fixed == expected else "불일치"
        print(f"결과:   {status}")
        print()
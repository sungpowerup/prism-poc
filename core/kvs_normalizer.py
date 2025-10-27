"""
core/kvs_normalizer.py
PRISM Phase 5.3.2 - KVS Normalizer

✅ Phase 5.3.2: Phase 5.3.1 유지
- 숫자 정규화
- 단위 통일
- 빈 값 제거

Author: 이서영 (Backend Lead)
Date: 2025-10-27
Version: 5.3.2
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class KVSNormalizer:
    """
    Key-Value Structured 데이터 정규화
    
    기능:
    - 숫자 천단위 구분 (10000 → 10,000)
    - 단위 통일 (분, 원, % 등)
    - 빈 값/중복 제거
    """
    
    @classmethod
    def normalize_kvs(cls, kvs: Dict[str, str]) -> Dict[str, str]:
        """
        KVS 정규화
        
        Args:
            kvs: 원본 KVS 데이터
        
        Returns:
            정규화된 KVS
        """
        normalized = {}
        
        for key, value in kvs.items():
            # 빈 값 스킵
            if not value or value.strip() == '' or value == ':':
                continue
            
            # 값 정규화
            normalized_value = cls._normalize_value(value)
            
            # 중복 키 처리 (더 긴 값 유지)
            if key in normalized:
                if len(normalized_value) > len(normalized[key]):
                    normalized[key] = normalized_value
            else:
                normalized[key] = normalized_value
        
        logger.debug(f"   📊 KVS 정규화: {len(kvs)} → {len(normalized)}개 항목")
        return normalized
    
    @classmethod
    def _normalize_value(cls, value: str) -> str:
        """
        값 정규화
        
        Args:
            value: 원본 값
        
        Returns:
            정규화된 값
        """
        # 1. 공백 제거
        value = value.strip()
        
        # 2. 숫자 천단위 구분
        # 예: 10000 → 10,000
        number_match = re.search(r'\d{4,}', value)
        if number_match:
            number_str = number_match.group()
            formatted_number = f"{int(number_str):,}"
            value = value.replace(number_str, formatted_number)
        
        # 3. 시간 형식 통일 (HH:MM)
        time_match = re.match(r'(\d{1,2}):(\d{2})', value)
        if time_match:
            hour, minute = time_match.groups()
            value = f"{int(hour):02d}:{minute}"
        
        # 4. 단위 정리
        value = value.replace(' 원', '원')
        value = value.replace(' 분', '분')
        value = value.replace(' %', '%')
        
        return value


# 테스트 코드
if __name__ == "__main__":
    # 테스트 데이터
    test_kvs = {
        '배차간격': '27분',
        '첫차': '5:30',
        '막차': '22:40',
        '노선번호': '111',
        '총 응답자': '35000명',
        '남성': '45.2 %',
        '빈값': '',
        '콜론만': ':'
    }
    
    print("=== 정규화 전 ===")
    for key, value in test_kvs.items():
        print(f"{key}: {value}")
    
    normalized = KVSNormalizer.normalize_kvs(test_kvs)
    
    print("\n=== 정규화 후 ===")
    for key, value in normalized.items():
        print(f"{key}: {value}")
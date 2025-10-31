"""
core/kvs_normalizer.py
PRISM Phase 5.7.2.3 - KVS Normalizer (List Support)

✅ Phase 5.7.2.3 긴급 수정:
- List[Dict] 입력 지원 추가
- Dict 입력 하위 호환성 유지
- 타입 안전성 강화

(Phase 5.3.2 기능 유지)

Author: 이서영 (Backend Lead)
Date: 2025-10-31
Version: 5.7.2.3
"""

import re
import logging
from typing import Dict, Any, List, Union

logger = logging.getLogger(__name__)


class KVSNormalizer:
    """
    Phase 5.7.2.3 Key-Value Structured 데이터 정규화
    
    기능:
    - ✅ List[Dict] / Dict 입력 모두 지원
    - 숫자 천단위 구분 (10000 → 10,000)
    - 단위 통일 (분, 원, % 등)
    - 빈 값/중복 제거
    """
    
    @classmethod
    def normalize_kvs(cls, kvs: Union[List[Dict[str, str]], Dict[str, str]]) -> Dict[str, str]:
        """
        ✅ Phase 5.7.2.3: KVS 정규화 (List/Dict 입력 모두 지원)
        
        Args:
            kvs: 원본 KVS 데이터
                - List[Dict]: [{'key': 'K', 'value': 'V', 'type': 'T'}, ...]
                - Dict: {'key1': 'value1', 'key2': 'value2', ...}
        
        Returns:
            정규화된 KVS (Dict)
        """
        normalized = {}
        
        # ✅ List[Dict] 형식 처리
        if isinstance(kvs, list):
            logger.debug(f"   📊 KVS 정규화: List 입력 ({len(kvs)}개 항목)")
            
            for item in kvs:
                if not isinstance(item, dict):
                    logger.warning(f"   ⚠️ 잘못된 항목 타입: {type(item)}")
                    continue
                
                key = item.get('key', '')
                value = item.get('value', '')
                
                # 빈 값 스킵
                if not key or not value or value.strip() == '' or value == ':':
                    continue
                
                # 값 정규화
                normalized_value = cls._normalize_value(value)
                
                # 중복 키 처리 (더 긴 값 유지)
                if key in normalized:
                    if len(normalized_value) > len(normalized[key]):
                        normalized[key] = normalized_value
                else:
                    normalized[key] = normalized_value
        
        # ✅ Dict 형식 처리 (하위 호환성)
        elif isinstance(kvs, dict):
            logger.debug(f"   📊 KVS 정규화: Dict 입력 ({len(kvs)}개 항목)")
            
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
        
        else:
            logger.error(f"   ❌ 지원하지 않는 KVS 타입: {type(kvs)}")
            return {}
        
        logger.debug(f"   ✅ 정규화 완료: {len(normalized)}개 항목")
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
            try:
                formatted_number = f"{int(number_str):,}"
                value = value.replace(number_str, formatted_number)
            except ValueError:
                pass  # 변환 실패 시 원본 유지
        
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
    print("=== KVSNormalizer v5.7.2.3 테스트 ===\n")
    
    # 테스트 1: Dict 입력 (하위 호환성)
    print("1️⃣ Dict 입력 테스트")
    test_dict = {
        '배차간격': '27분',
        '첫차': '5:30',
        '막차': '22:40',
        '노선번호': '111',
        '총 응답자': '35000명',
        '남성': '45.2 %',
        '빈값': '',
        '콜론만': ':'
    }
    
    print("정규화 전:")
    for key, value in test_dict.items():
        print(f"  {key}: {value}")
    
    normalized_dict = KVSNormalizer.normalize_kvs(test_dict)
    
    print("\n정규화 후:")
    for key, value in normalized_dict.items():
        print(f"  {key}: {value}")
    
    # 테스트 2: List[Dict] 입력 (Phase 5.7.2.3)
    print("\n\n2️⃣ List[Dict] 입력 테스트")
    test_list = [
        {'key': '제1조', 'value': '목적', 'type': 'article_title'},
        {'key': '개정', 'value': '2024.10.31', 'type': 'amendment_date'},
        {'key': '배차간격', 'value': '27분', 'type': 'transport'},
        {'key': '총 응답자', 'value': '35000명', 'type': 'statistics'},
        {'key': '빈값', 'value': '', 'type': 'empty'},
    ]
    
    print("정규화 전:")
    for item in test_list:
        print(f"  {item['key']}: {item['value']} (type: {item['type']})")
    
    normalized_list = KVSNormalizer.normalize_kvs(test_list)
    
    print("\n정규화 후:")
    for key, value in normalized_list.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 테스트 완료!")
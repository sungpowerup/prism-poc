"""
core/kvs_normalizer.py
PRISM Phase 5.3.0 - KVS Normalizer

목적: Key-Value 정규화로 RAG 필드 검색 최적화
GPT 제안 반영: 캐논 키 매핑 + 값 포맷 정규화
"""

import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class KVSNormalizer:
    """
    KVS 키/값 정규화 (GPT 제안 #4)
    
    목적:
    - 키 통일: '배차 간격' → '배차간격'
    - 값 포맷 정규화: '5:30' → '05:30', '27' → '27분'
    """
    
    # 캐논 키 매핑 (GPT 제안)
    CANONICAL_KEYS = {
        '배차간격': ['배차 간격', '배차간경', '간격', '배차'],
        '첫차': ['첫차시간', '첫 차', '기점 첫차', '첫차 시간'],
        '막차': ['막차시간', '막 차', '기점 막차', '막차 시간'],
        '노선번호': ['노선 번호', '버스번호', '번호', '노선'],
        '변경전': ['변경 전', '이전', '기존'],
        '변경후': ['변경 후', '이후', '신규']
    }
    
    # 역방향 매핑 (빠른 검색용)
    _REVERSE_MAP = None
    
    @classmethod
    def _build_reverse_map(cls):
        """역방향 매핑 빌드 (초기화 시 1회)"""
        if cls._REVERSE_MAP is None:
            cls._REVERSE_MAP = {}
            for canonical, aliases in cls.CANONICAL_KEYS.items():
                cls._REVERSE_MAP[canonical] = canonical  # 자기 자신도 포함
                for alias in aliases:
                    cls._REVERSE_MAP[alias] = canonical
    
    @classmethod
    def normalize_key(cls, key: str) -> str:
        """
        키 정규화
        
        Args:
            key: 원본 키 (예: '배차 간격', '첫차시간')
            
        Returns:
            정규화된 키 (예: '배차간격', '첫차')
        """
        cls._build_reverse_map()
        
        # 공백 제거 후 매칭
        key_clean = key.strip()
        
        # 직접 매칭
        if key_clean in cls._REVERSE_MAP:
            return cls._REVERSE_MAP[key_clean]
        
        # 부분 매칭 (키워드 포함 여부)
        for canonical, aliases in cls.CANONICAL_KEYS.items():
            if any(alias in key_clean for alias in [canonical] + aliases):
                return canonical
        
        # 매칭 실패 시 원본 반환
        return key_clean
    
    @classmethod
    def normalize_value(cls, key: str, value: str) -> str:
        """
        값 정규화 (GPT 제안)
        
        Args:
            key: 정규화된 키
            value: 원본 값
            
        Returns:
            정규화된 값
        """
        value_clean = value.strip()
        
        # 1. 시간 정규화 (첫차, 막차)
        if '차' in key:
            # 5:30 → 05:30
            match = re.match(r'(\d{1,2}):(\d{2})', value_clean)
            if match:
                h, m = match.groups()
                return f"{int(h):02d}:{m}"
        
        # 2. 분 단위 정규화 (배차간격)
        if '간격' in key:
            # "27분" 또는 "27" → "27분"
            match = re.search(r'(\d+)', value_clean)
            if match:
                num = match.group(1)
                if '분' not in value_clean:
                    return f"{num}분"
                return f"{num}분"
        
        # 3. 금액 정규화
        if '금액' in key or '요금' in key or '원' in value_clean:
            # 천단위 구분자 유지
            match = re.search(r'([\d,]+)', value_clean)
            if match:
                amount = match.group(1)
                if '원' not in value_clean:
                    return f"{amount}원"
                return f"{amount}원"
        
        # 4. 퍼센트 정규화
        if '%' in value_clean or '퍼센트' in value_clean:
            match = re.search(r'([\d.]+)', value_clean)
            if match:
                pct = match.group(1)
                return f"{pct}%"
        
        # 기본: 원본 반환
        return value_clean
    
    @classmethod
    def normalize_kvs(cls, kvs: Dict[str, str]) -> Dict[str, str]:
        """
        전체 KVS 딕셔너리 정규화
        
        Args:
            kvs: 원본 KVS
            
        Returns:
            정규화된 KVS
        """
        normalized = {}
        
        for key, value in kvs.items():
            # 키 정규화
            canonical_key = cls.normalize_key(key)
            
            # 값 정규화
            normalized_value = cls.normalize_value(canonical_key, value)
            
            # 중복 키 처리 (나중 값 우선)
            if canonical_key in normalized:
                logger.warning(
                    f"중복 키 발견: '{canonical_key}' "
                    f"(기존: '{normalized[canonical_key]}', 새: '{normalized_value}')"
                )
            
            normalized[canonical_key] = normalized_value
        
        logger.info(f"KVS 정규화: {len(kvs)}개 → {len(normalized)}개")
        return normalized
    
    @classmethod
    def add_custom_mapping(cls, canonical: str, aliases: list[str]):
        """
        커스텀 매핑 추가 (확장성)
        
        Args:
            canonical: 정규화된 키 이름
            aliases: 별칭 리스트
        """
        if canonical not in cls.CANONICAL_KEYS:
            cls.CANONICAL_KEYS[canonical] = []
        
        cls.CANONICAL_KEYS[canonical].extend(aliases)
        cls._REVERSE_MAP = None  # 재빌드 필요
        
        logger.info(f"커스텀 매핑 추가: {canonical} ← {aliases}")


# 사용 예시
if __name__ == "__main__":
    # 테스트
    test_kvs = {
        '배차 간격': '27',
        '첫차시간': '5:30',
        '막 차': '22:40',
        '노선 번호': '111'
    }
    
    normalized = KVSNormalizer.normalize_kvs(test_kvs)
    print("원본:", test_kvs)
    print("정규화:", normalized)
    
    # 예상 출력:
    # 원본: {'배차 간격': '27', '첫차시간': '5:30', '막 차': '22:40', '노선 번호': '111'}
    # 정규화: {'배차간격': '27분', '첫차': '05:30', '막차': '22:40', '노선번호': '111'}

"""
core/hierarchical_parser.py
PRISM Phase 5.7.0 - HierarchicalParser v1.0

목표: Tree 계층 검증 및 관계 강화

플로우:
1. 계층 구조 검증
2. 부모-자식 관계 재확인
3. 경계 누수 탐지
4. 계층 보존율 계산
5. Phase 5.6.3 DoD 검증

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.7.0 v1.0
"""

import logging
from typing import Dict, Any, List, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class HierarchicalParser:
    """
    Phase 5.7.0 계층 파서
    
    역할:
    - Tree 구조 검증
    - 관계 무결성 확인
    - Phase 5.6.3 Final+ 지표 검증
    
    ✅ 지표 대응:
    - hierarchy_preservation_rate (≥ 0.95)
    - boundary_cross_bleed_rate (= 0)
    - empty_article_rate (= 0)
    """
    
    # DoD 기준 (Phase 5.6.3 Final+)
    DOD_CRITERIA = {
        'hierarchy_preservation_rate': 0.95,
        'boundary_cross_bleed_rate': 0.0,
        'empty_article_rate': 0.0
    }
    
    def __init__(self):
        """초기화"""
        logger.info("✅ HierarchicalParser v5.7.0 초기화 완료")
    
    def parse(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tree 파싱 및 검증
        
        Args:
            document: TreeBuilder 출력 (Document 스키마)
        
        Returns:
            검증된 Document + 메트릭
        """
        logger.info("🔍 HierarchicalParser 시작")
        
        tree = document['document']['tree']
        
        # Step 1: 계층 보존율
        preservation_rate = self._calculate_hierarchy_preservation(tree)
        logger.info(f"   📊 계층 보존율: {preservation_rate:.3f} (목표: ≥{self.DOD_CRITERIA['hierarchy_preservation_rate']})")
        
        # Step 2: 경계 누수율
        cross_bleed_rate = self._calculate_boundary_cross_bleed(tree)
        logger.info(f"   📊 경계 누수율: {cross_bleed_rate:.3f} (목표: ={self.DOD_CRITERIA['boundary_cross_bleed_rate']})")
        
        # Step 3: 빈 조문율
        empty_rate = self._calculate_empty_article_rate(tree)
        logger.info(f"   📊 빈 조문율: {empty_rate:.3f} (목표: ={self.DOD_CRITERIA['empty_article_rate']})")
        
        # Step 4: 관계 무결성 검증
        integrity_errors = self._validate_integrity(tree)
        if integrity_errors:
            logger.warning(f"   ⚠️ 관계 무결성 오류: {len(integrity_errors)}개")
            for error in integrity_errors[:5]:
                logger.warning(f"      - {error}")
        
        # Step 5: DoD 검증
        dod_status = {
            'hierarchy_preservation_rate': {
                'value': preservation_rate,
                'target': self.DOD_CRITERIA['hierarchy_preservation_rate'],
                'pass': preservation_rate >= self.DOD_CRITERIA['hierarchy_preservation_rate']
            },
            'boundary_cross_bleed_rate': {
                'value': cross_bleed_rate,
                'target': self.DOD_CRITERIA['boundary_cross_bleed_rate'],
                'pass': cross_bleed_rate == self.DOD_CRITERIA['boundary_cross_bleed_rate']
            },
            'empty_article_rate': {
                'value': empty_rate,
                'target': self.DOD_CRITERIA['empty_article_rate'],
                'pass': empty_rate == self.DOD_CRITERIA['empty_article_rate']
            }
        }
        
        dod_pass = all(status['pass'] for status in dod_status.values())
        
        if dod_pass:
            logger.info("   ✅ DoD 검증 통과")
        else:
            logger.error("   ❌ DoD 검증 실패")
        
        # 메트릭 추가
        document['document']['metrics'] = {
            'hierarchy_preservation_rate': preservation_rate,
            'boundary_cross_bleed_rate': cross_bleed_rate,
            'empty_article_rate': empty_rate,
            'integrity_errors': integrity_errors,
            'dod_status': dod_status,
            'dod_pass': dod_pass
        }
        
        return document
    
    def _calculate_hierarchy_preservation(self, tree: List[Dict]) -> float:
        """
        계층 보존율 계산
        
        Returns:
            0.0 ~ 1.0 (1.0 = 완벽)
        """
        expected_layers = {'article', 'clause', 'item'}
        detected_layers = set()
        
        for article in tree:
            detected_layers.add('article')
            
            for child in article.get('children', []):
                if isinstance(child, dict):
                    if child.get('level') == 'clause':
                        detected_layers.add('clause')
                        
                        for item in child.get('children', []):
                            if isinstance(item, dict) and item.get('level') == 'item':
                                detected_layers.add('item')
        
        return len(detected_layers & expected_layers) / len(expected_layers)
    
    def _calculate_boundary_cross_bleed(self, tree: List[Dict]) -> float:
        """
        경계 누수율 계산
        
        Returns:
            0.0 ~ 1.0 (0.0 = 누수 없음)
        """
        total = len(tree)
        cross_bleed = sum(
            1 for article in tree
            if article['metadata'].get('has_cross_bleed', False)
        )
        
        return cross_bleed / max(1, total)
    
    def _calculate_empty_article_rate(self, tree: List[Dict]) -> float:
        """
        빈 조문율 계산
        
        Returns:
            0.0 ~ 1.0 (0.0 = 빈 조문 없음)
        """
        total = len(tree)
        empty = sum(
            1 for article in tree
            if article['metadata'].get('has_empty_content', False)
        )
        
        return empty / max(1, total)
    
    def _validate_integrity(self, tree: List[Dict]) -> List[str]:
        """
        관계 무결성 검증
        
        Returns:
            오류 메시지 리스트
        """
        errors = []
        
        for article in tree:
            article_no = article.get('article_no')
            
            # 항 검증
            for child in article.get('children', []):
                if isinstance(child, dict) and child.get('level') == 'clause':
                    # 부모 조문 번호 확인
                    if child.get('parent_article_no') != article_no:
                        errors.append(
                            f"Clause {child.get('clause_no')} has wrong parent: "
                            f"{child.get('parent_article_no')} != {article_no}"
                        )
                    
                    # 호 검증
                    clause_no = child.get('clause_no')
                    for item in child.get('children', []):
                        if isinstance(item, dict) and item.get('level') == 'item':
                            # 부모 조문 확인
                            if item.get('parent_article_no') != article_no:
                                errors.append(
                                    f"Item {item.get('item_no')} has wrong article parent"
                                )
                            
                            # 부모 항 확인
                            if item.get('parent_clause_no') != clause_no:
                                errors.append(
                                    f"Item {item.get('item_no')} has wrong clause parent"
                                )
        
        return errors

"""
PRISM Phase 0.9 - Golden Set 기반 Lookup
자동 파싱 없이 수동 JSON만 사용

Author: 마창수산팀
Date: 2025-11-17
Version: Phase 0.9.0
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PromotionRangeLookup:
    """
    승진후보자 범위 조회 서비스
    
    Golden Set 기반 (자동 파싱 없음)
    100% 정확도 보장
    """
    
    def __init__(self, golden_path: str = None):
        """
        초기화
        
        Args:
            golden_path: Golden Set JSON 경로
                        None이면 기본 경로 사용
        """
        if golden_path is None:
            # 기본 경로: ../golden_tables/promotion_range_3급승진제외.json
            golden_path = Path(__file__).parent.parent / "golden_tables" / "promotion_range_3급승진제외.json"
        
        try:
            with open(golden_path, 'r', encoding='utf-8') as f:
                self.golden_data = json.load(f)
            
            self.rows = self.golden_data['rows']
            logger.info(f"✅ Golden Set 로드: {len(self.rows)}개 행")
            logger.info(f"   출처: {self.golden_data['source']}")
            logger.info(f"   타입: {self.golden_data['grade_type']}")
        
        except FileNotFoundError:
            logger.error(f"❌ Golden Set 파일 없음: {golden_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            raise
    
    def query(self, people: int) -> Optional[Dict]:
        """
        임용 인원수 → 승진후보자 범위 조회
        
        Args:
            people: 임용하고자 하는 인원수 (예: 47)
        
        Returns:
            {
                "people": 47,
                "rank_max": 151,
                "source": "별표1 3급승진제외 Golden Set",
                "confidence": 1.0,
                "table_type": "promotion_candidate_range",
                "grade_type": "3급승진제외"
            }
            또는 None (범위 밖)
        """
        # 정확한 매칭
        for row in self.rows:
            if row['people'] == people:
                result = {
                    "people": people,
                    "rank_max": row['rank_max'],
                    "source": f"{self.golden_data['table_id']} Golden Set",
                    "confidence": 1.0,
                    "table_type": self.golden_data['table_type'],
                    "grade_type": self.golden_data['grade_type'],
                    "related_article": self.golden_data.get('related_article', '')
                }
                
                logger.info(f"✅ 조회 성공: {people}명 → {row['rank_max']}번까지")
                return result
        
        logger.warning(f"⚠️ 조회 실패: {people}명 (Golden Set 범위 밖: 1-{len(self.rows)})")
        return None
    
    def query_range(self, people_min: int, people_max: int) -> list:
        """
        범위 조회
        
        Args:
            people_min: 최소 인원
            people_max: 최대 인원
        
        Returns:
            해당 범위의 모든 결과 리스트
        """
        results = []
        for people in range(people_min, people_max + 1):
            result = self.query(people)
            if result:
                results.append(result)
        
        return results
    
    def get_all_rows(self) -> list:
        """전체 데이터 반환"""
        return self.rows
    
    def get_metadata(self) -> dict:
        """메타데이터 반환"""
        return {
            'table_id': self.golden_data['table_id'],
            'table_type': self.golden_data['table_type'],
            'grade_type': self.golden_data['grade_type'],
            'total_rows': len(self.rows),
            'source': self.golden_data['source'],
            'related_article': self.golden_data.get('related_article', ''),
            'verified_by': self.golden_data.get('verified_by', ''),
            'verified_date': self.golden_data.get('verified_date', '')
        }
    
    def validate(self) -> Dict:
        """
        Golden Set 자체 검증
        
        Returns:
            {
                'is_valid': True,
                'total_rows': 75,
                'issues': []
            }
        """
        issues = []
        
        # 1. 행 개수 체크
        if len(self.rows) == 0:
            issues.append("행 개수가 0개")
        
        # 2. people 연속성 체크
        for i, row in enumerate(self.rows):
            expected_people = i + 1
            if row['people'] != expected_people:
                issues.append(f"Row {i}: people={row['people']} (예상: {expected_people})")
        
        # 3. rank_max 증가 체크
        for i in range(len(self.rows) - 1):
            if self.rows[i]['rank_max'] >= self.rows[i + 1]['rank_max']:
                issues.append(f"Row {i}-{i+1}: rank_max 비증가")
        
        is_valid = len(issues) == 0
        
        return {
            'is_valid': is_valid,
            'total_rows': len(self.rows),
            'issues': issues
        }


# ============================================
# 테스트 & 사용 예시
# ============================================

def main():
    """메인 함수 - 테스트"""
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🚀 PRISM Phase 0.9 - Promotion Range Lookup")
    print("="*60)
    
    try:
        # Lookup 서비스 초기화
        lookup = PromotionRangeLookup()
        
        # 메타데이터 확인
        print("\n📊 Golden Set 정보:")
        metadata = lookup.get_metadata()
        for key, value in metadata.items():
            print(f"   {key}: {value}")
        
        # Golden Set 검증
        print("\n🔍 Golden Set 검증:")
        validation = lookup.validate()
        if validation['is_valid']:
            print(f"   ✅ 유효함 ({validation['total_rows']}개 행)")
        else:
            print(f"   ❌ 문제 발견:")
            for issue in validation['issues']:
                print(f"      - {issue}")
        
        # 테스트 케이스
        print("\n🧪 테스트 케이스:")
        test_cases = [1, 5, 10, 20, 47, 50, 75, 100]
        
        for people in test_cases:
            result = lookup.query(people)
            if result:
                print(f"   ✅ {people:3d}명 → {result['rank_max']:3d}번까지")
            else:
                print(f"   ⚠️ {people:3d}명 → 범위 밖")
        
        # 특정 케이스 상세
        print("\n🎯 중요 케이스 (47명):")
        result = lookup.query(47)
        if result:
            print(f"   임용 인원: {result['people']}명")
            print(f"   승진후보자: {result['rank_max']}번까지")
            print(f"   출처: {result['source']}")
            print(f"   신뢰도: {result['confidence']*100:.0f}%")
        
        print("\n🎉 Phase 0.9 Lookup 테스트 완료!")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

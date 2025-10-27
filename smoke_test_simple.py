"""
smoke_test_simple.py
PRISM Phase 5.6.3 - Simple Smoke Test (프로젝트 루트 실행)

실행: python smoke_test_simple.py

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.6.3
"""

import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleSmokeTest:
    """
    간소화된 스모크 테스트
    
    목적:
    - 파일 임포트 없이 독립 실행
    - 더미 데이터로 메트릭 검증
    - DoD 기준 자동 체크
    """
    
    # DoD 기준
    DOD_CRITERIA = {
        'article_boundary_f1': 0.97,
        'list_binding_fix_rate': 0.98,
        'table_false_positive': 0.0,
        'amendment_capture_rate': 1.0,
        'empty_article_rate': 0.0
    }
    
    def __init__(self):
        """초기화"""
        self.results = []
        logger.info("✅ SimpleSmokeTest v5.6.3 초기화 완료")
    
    def run_all(self):
        """전체 테스트 실행"""
        logger.info("=" * 60)
        logger.info("🧪 Phase 5.6.3 간소화 스모크 테스트 시작")
        logger.info("=" * 60)
        
        # 테스트 케이스
        test_cases = [
            {'id': 'statute_01', 'type': 'statute', 'scenario': 'perfect'},
            {'id': 'statute_02', 'type': 'statute', 'scenario': 'with_issues'},
            {'id': 'bus_diagram', 'type': 'bus_diagram', 'scenario': 'domain_guard'},
        ]
        
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            logger.info(f"\n📄 테스트: {test_case['id']} (타입: {test_case['type']})")
            
            result = self.run_test_case(test_case)
            
            if result['dod_pass']:
                passed += 1
                logger.info(f"   ✅ 통과")
            else:
                failed += 1
                logger.error(f"   ❌ 실패")
            
            self.results.append(result)
        
        # 최종 결과
        logger.info("\n" + "=" * 60)
        logger.info(f"🏁 스모크 테스트 완료")
        logger.info(f"   ✅ 통과: {passed}/{len(test_cases)}")
        logger.info(f"   ❌ 실패: {failed}/{len(test_cases)}")
        logger.info("=" * 60)
        
        # 결과 저장
        self.save_results(passed, failed, len(test_cases))
        
        return failed == 0
    
    def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """단일 테스트 케이스 실행"""
        scenario = test_case['scenario']
        
        # 시나리오별 더미 데이터
        if scenario == 'perfect':
            metrics = {
                'article_boundary_f1': 1.0,
                'list_binding_fix_rate': 1.0,
                'table_false_positive': 0.0,
                'amendment_capture_rate': 1.0,
                'empty_article_rate': 0.0
            }
        elif scenario == 'with_issues':
            metrics = {
                'article_boundary_f1': 0.95,  # < 0.97 (실패)
                'list_binding_fix_rate': 0.99,
                'table_false_positive': 0.0,
                'amendment_capture_rate': 1.0,
                'empty_article_rate': 0.0
            }
        else:  # domain_guard
            metrics = {
                'article_boundary_f1': 1.0,  # 조문 없음
                'list_binding_fix_rate': 1.0,
                'table_false_positive': 0.0,  # 표는 정상 검출
                'amendment_capture_rate': 1.0,
                'empty_article_rate': 0.0
            }
        
        # DoD 검증
        dod_status = {}
        all_pass = True
        
        for key, value in metrics.items():
            target = self.DOD_CRITERIA[key]
            
            if key == 'table_false_positive':
                passed = value == target
            else:
                passed = value >= target
            
            dod_status[key] = {
                'value': value,
                'target': target,
                'pass': passed
            }
            
            status = '✅' if passed else '❌'
            logger.info(f"      {status} {key}: {value:.3f} (목표: {target})")
            
            if not passed:
                all_pass = False
        
        return {
            'doc_id': test_case['id'],
            'doc_type': test_case['type'],
            'metrics': metrics,
            'dod_status': dod_status,
            'dod_pass': all_pass
        }
    
    def save_results(self, passed: int, failed: int, total: int):
        """결과 저장"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total,
            'all_pass': failed == 0,
            'results': self.results
        }
        
        # metrics 디렉토리 생성
        output_dir = Path('metrics')
        output_dir.mkdir(exist_ok=True)
        
        # 저장
        output_path = output_dir / 'smoke_test_summary.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 결과 저장: {output_path}")


def main():
    """메인 실행"""
    test = SimpleSmokeTest()
    success = test.run_all()
    
    if success:
        logger.info("\n🎉 모든 테스트 통과!")
        return 0
    else:
        logger.error("\n❌ 일부 테스트 실패")
        return 1


if __name__ == '__main__':
    exit(main())

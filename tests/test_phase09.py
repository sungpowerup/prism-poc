"""
tests/test_phase09.py - PRISM Phase 0.9 통합 테스트
TableParser + Golden Set 정확도 평가

실행: python tests/test_phase09.py

Author: 마창수산팀
Date: 2025-11-20
Version: Phase 0.9.0
"""

import sys
import json
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from research.table_parser import TableParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_table_parser_basic():
    """기본 파싱 테스트"""
    print("\n" + "="*60)
    print("📋 테스트 1: TableParser 기본 동작")
    print("="*60)
    
    parser = TableParser()
    
    # 3급승진제외 테스트
    test_chunk = {
        'content': """1 2 3 4 5 6 7 8 9 10
5번까지 10번까지 15번까지 20번까지 25번까지 28번까지 31번까지 34번까지 37번까지 40번까지""",
        'metadata': {
            'type': 'annex_table_rows',
            'table_title': '3급승진제외'
        }
    }
    
    chunks = parser.parse_annex_chunk(test_chunk)
    
    print(f"✅ 청크 생성: {len(chunks)}개")
    
    # 질의 테스트
    test_queries = [
        ("1명이면 서열 몇 번까지?", "5번까지"),
        ("5명이면 서열 몇 번까지?", "25번까지"),
        ("10명이면 서열 몇 번까지?", "40번까지"),
    ]
    
    passed = 0
    for query, expected in test_queries:
        answer = parser.query(query, chunks)
        status = "✅" if answer == expected else "❌"
        print(f"  {status} Q: {query} → A: {answer} (기대: {expected})")
        if answer == expected:
            passed += 1
    
    print(f"\n질의 테스트: {passed}/{len(test_queries)} 통과")
    
    return passed == len(test_queries)


def test_golden_set_accuracy():
    """Golden Set 정확도 테스트"""
    print("\n" + "="*60)
    print("📋 테스트 2: Golden Set 정확도 평가")
    print("="*60)
    
    parser = TableParser()
    golden_path = project_root / "tests" / "golden" / "annex_table_golden.json"
    
    if not golden_path.exists():
        print(f"⚠️ Golden Set 없음: {golden_path}")
        return False
    
    # Golden Set 로드
    with open(golden_path, 'r', encoding='utf-8') as f:
        golden = json.load(f)
    
    print(f"✅ Golden Set 로드: {len(golden.get('tables', []))}개 테이블")
    
    # 테스트 청크 생성 - 두 테이블 모두
    all_chunks = []
    
    # 1. 3급승진제외 (5배수 → 3배수)
    test_chunk_1 = {
        'content': ' '.join([str(i) for i in range(1, 76)]),
        'metadata': {
            'type': 'annex_table_rows',
            'table_title': '3급승진제외'
        }
    }
    chunks_1 = parser.parse_annex_chunk(test_chunk_1)
    all_chunks.extend(chunks_1)
    print(f"  - 3급승진제외: {len(chunks_1)}개 행")
    
    # 2. 3급승진 (2배수)
    test_chunk_2 = {
        'content': ' '.join([str(i) for i in range(1, 76)]),
        'metadata': {
            'type': 'annex_table_rows',
            'table_title': '3급승진'
        }
    }
    chunks_2 = parser.parse_annex_chunk(test_chunk_2)
    all_chunks.extend(chunks_2)
    print(f"  - 3급승진: {len(chunks_2)}개 행")
    
    # 정확도 평가
    results = parser.evaluate_accuracy(all_chunks, str(golden_path))
    
    print(f"\n📊 정확도 결과:")
    print(f"  - 테이블 매칭: {results['matched_tables']}/{results['total_tables']}")
    print(f"  - 행 매칭: {results['matched_rows']}/{results['total_rows']}")
    print(f"  - 정확도: {results['accuracy']*100:.1f}%")
    
    # 95% 기준 통과 여부
    target_accuracy = 0.95
    passed = results['accuracy'] >= target_accuracy
    
    if passed:
        print(f"✅ DoD 통과: {results['accuracy']*100:.1f}% >= {target_accuracy*100:.0f}%")
    else:
        print(f"❌ DoD 실패: {results['accuracy']*100:.1f}% < {target_accuracy*100:.0f}%")
    
    return passed


def test_query_accuracy():
    """질의 정확도 테스트"""
    print("\n" + "="*60)
    print("📋 테스트 3: 질의 정확도")
    print("="*60)
    
    parser = TableParser()
    golden_path = project_root / "tests" / "golden" / "annex_table_golden.json"
    
    if not golden_path.exists():
        print(f"⚠️ Golden Set 없음")
        return False
    
    with open(golden_path, 'r', encoding='utf-8') as f:
        golden = json.load(f)
    
    # 테스트 청크 생성 - 두 테이블 모두
    all_chunks = []
    
    # 3급승진제외
    test_chunk_1 = {
        'content': ' '.join([str(i) for i in range(1, 76)]),
        'metadata': {
            'type': 'annex_table_rows',
            'table_title': '3급승진제외'
        }
    }
    all_chunks.extend(parser.parse_annex_chunk(test_chunk_1))
    
    # 3급승진
    test_chunk_2 = {
        'content': ' '.join([str(i) for i in range(1, 76)]),
        'metadata': {
            'type': 'annex_table_rows',
            'table_title': '3급승진'
        }
    }
    all_chunks.extend(parser.parse_annex_chunk(test_chunk_2))
    
    # 테스트 질의 실행
    test_queries = golden.get('test_queries', [])
    passed = 0
    
    for tq in test_queries:
        query = tq['query']
        expected = tq['expected_answer']
        table_id = tq.get('table_id', '')
        
        # 해당 테이블의 청크만 필터링
        if '3급승진제외' in table_id:
            target_chunks = [c for c in all_chunks if '3급승진제외' in c.get('table_id', '')]
        elif '3급승진' in table_id and '제외' not in table_id:
            # 3급승진이지만 제외가 아닌 경우
            target_chunks = [c for c in all_chunks 
                           if '3급승진' in c.get('table_id', '') 
                           and '제외' not in c.get('table_id', '')]
        else:
            target_chunks = all_chunks
        
        answer = parser.query(query, target_chunks)
        status = "✅" if answer == expected else "❌"
        print(f"  {status} {query}")
        print(f"      → 응답: {answer} (기대: {expected})")
        
        if answer == expected:
            passed += 1
    
    print(f"\n질의 테스트: {passed}/{len(test_queries)} 통과")
    
    return passed == len(test_queries)


def main():
    """메인 테스트 실행"""
    print("\n" + "#"*60)
    print("#  PRISM Phase 0.9 TableParser 통합 테스트")
    print("#"*60)
    
    results = {
        'basic': test_table_parser_basic(),
        'golden': test_golden_set_accuracy(),
        'query': test_query_accuracy()
    }
    
    print("\n" + "="*60)
    print("📊 최종 결과")
    print("="*60)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    if all_passed:
        print("\n🎉 Phase 0.9 TableParser 테스트 전체 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패 - 수정 필요")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

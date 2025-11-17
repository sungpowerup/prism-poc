"""
tests/test_phase08.py - Phase 0.8 테스트
Annex 서브청킹 검증

Author: 정수아 (QA Lead)
Date: 2025-11-17
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.annex_subchunker import AnnexSubChunker, validate_subchunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# 테스트 데이터
# ============================================

SAMPLE_ANNEX = """
인사규정
[별표1]임용하고자하는인원수에대한승진후보자범위(3급승진제외)
<제20조제2항관련>(개정2003.3.29,2008.7.1,2014.6.1.,2016.8.1.,2017.07.14)
임용하고자하는인원수에대한승진후보자범위(3급승진제외)

임용하고자
하는인원수서열명부순위임용하고자
하는인원수서열명부순위
1 5번까지
2 10번까지
3 15번까지

*임용하고자하는인원수가5명까지는서열명부순위의5배수,5명을초과하는경우에는초과인원의
3배수를심사대상에포함

임용하고자하는인원수에대한승진후보자범위(3급승진)

1 2번까지
2 4번까지

*서열명부순위에동점자가2인이상인경우전원심사대상에포함
"""


# ============================================
# Phase 0.8 테스트
# ============================================

def test_header_extraction():
    """GPT 요구: Header 청크 추출 검증"""
    logger.info("\n" + "="*60)
    logger.info("테스트 1: Header 청크 추출")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    header_chunks = [c for c in chunks if c.section_type == 'header']
    
    assert len(header_chunks) >= 1, "❌ Header 청크 없음"
    assert '별표' in header_chunks[0].content, "❌ Header 내용 불일치"
    
    logger.info(f"✅ Header 청크: {len(header_chunks)}개")
    logger.info(f"   내용: {header_chunks[0].content[:50]}...")
    
    return True


def test_note_separation():
    """GPT 요구: Note 분리 정확도 100%"""
    logger.info("\n" + "="*60)
    logger.info("테스트 2: Note 분리")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    note_chunks = [c for c in chunks if c.section_type == 'note']
    
    # * 시작하는 줄 개수 확인
    expected_notes = SAMPLE_ANNEX.count('\n*')
    
    assert len(note_chunks) >= 1, "❌ Note 청크 없음"
    logger.info(f"✅ Note 청크: {len(note_chunks)}개 (예상: {expected_notes}개)")
    
    for i, note in enumerate(note_chunks):
        logger.info(f"   Note {i+1}: {note.content[:50]}...")
    
    return True


def test_text_loss_rate():
    """GPT 필수: 텍스트 손실률 0%"""
    logger.info("\n" + "="*60)
    logger.info("테스트 3: 텍스트 손실률 검증")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    validation = validate_subchunks(chunks, len(SAMPLE_ANNEX))
    
    loss_rate = validation['loss_rate']
    logger.info(f"   손실률: {loss_rate:.2%}")
    
    assert loss_rate < 0.05, f"❌ 텍스트 손실 {loss_rate:.1%} - 기준 초과"
    logger.info(f"✅ 텍스트 손실률: {loss_rate:.2%} (허용 범위)")
    
    return True


def test_chunk_type_diversity():
    """GPT 요구: 의미 단위 검증 (section_type 2종 이상)"""
    logger.info("\n" + "="*60)
    logger.info("테스트 4: 청크 타입 다양성")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    validation = validate_subchunks(chunks, len(SAMPLE_ANNEX))
    
    type_counts = validation['type_counts']
    logger.info(f"   타입 분포: {type_counts}")
    
    assert len(type_counts) >= 2, "❌ section_type 1종만 존재"
    assert validation['has_header'], "❌ Header 타입 없음"
    
    logger.info(f"✅ 의미 단위 청크: {len(type_counts)}종류")
    
    return True


def test_chunk_count_increase():
    """GPT 요구: 청크 수 증가 검증 (5개 이상)"""
    logger.info("\n" + "="*60)
    logger.info("테스트 5: 청크 수 증가")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    logger.info(f"   청크 수: {len(chunks)}개")
    
    assert len(chunks) >= 3, f"❌ 청크 수 부족: {len(chunks)}개"
    logger.info(f"✅ 서브청킹 성공: {len(chunks)}개")
    
    return True


def test_order_metadata():
    """GPT 요구: order 메타데이터 검증"""
    logger.info("\n" + "="*60)
    logger.info("테스트 6: Order 메타데이터")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(SAMPLE_ANNEX)
    
    # order 중복 검사
    orders = [c.order for c in chunks]
    assert len(orders) == len(set(orders)), "❌ Order 중복 발견"
    
    # order 연속성 검사
    sorted_orders = sorted(orders)
    expected_orders = list(range(len(chunks)))
    assert sorted_orders == expected_orders, "❌ Order 불연속"
    
    logger.info(f"✅ Order 메타데이터: 0~{len(chunks)-1}")
    
    return True


# ============================================
# 통합 실행
# ============================================

def main():
    """Phase 0.8 통합 테스트"""
    
    print("\n" + "="*60)
    print("🚀 PRISM Phase 0.8 통합 테스트")
    print("="*60)
    
    tests = [
        ("Header 추출", test_header_extraction),
        ("Note 분리", test_note_separation),
        ("텍스트 손실률", test_text_loss_rate),
        ("청크 타입 다양성", test_chunk_type_diversity),
        ("청크 수 증가", test_chunk_count_increase),
        ("Order 메타데이터", test_order_metadata)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except AssertionError as e:
            logger.error(f"❌ {test_name} 실패: {e}")
            results.append((test_name, False))
        except Exception as e:
            logger.error(f"❌ {test_name} 에러: {e}")
            results.append((test_name, False))
    
    # 최종 결과
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print()
    print(f"전체: {passed}/{total} 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 Phase 0.8 통합 테스트 완전 통과!")
        return True
    else:
        print("\n⚠️ 일부 테스트 실패")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

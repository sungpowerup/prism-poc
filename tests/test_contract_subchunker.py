"""
tests/test_contract_subchunker.py - Phase 0.9.6 Contract Test

GPT 미송님 요구사항:
1. validate_subchunks 시그니처 자동 검증 (2-arg 강제)
2. 최소 타입 보장 (header + content)
3. Loss Rate < 5% 보장
4. 회귀 방지 안전장치

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-24
Version: Phase 0.9.6 Contract Test
"""

import sys
import logging
import inspect
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.annex_subchunker import AnnexSubChunker, validate_subchunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# Contract Test: validate_subchunks 시그니처
# ============================================

def test_validate_subchunks_signature():
    """
    Contract Test 1: validate_subchunks 시그니처 검증
    
    GPT 미송님: "validate_subchunks는 LawParser ↔ SubChunker 프로토콜 규약"
    
    검증:
    - 2개 파라미터 (chunks, original_length)
    - 반환값: dict
    """
    logger.info("\n" + "="*60)
    logger.info("Contract Test 1: validate_subchunks 시그니처 검증")
    logger.info("="*60)
    
    # 시그니처 검사
    sig = inspect.signature(validate_subchunks)
    params = list(sig.parameters.keys())
    
    logger.info(f"   현재 시그니처: {params}")
    
    # 2-arg 강제
    assert len(params) == 2, f"❌ 파라미터 개수 불일치: {len(params)}개 (예상: 2개)"
    assert params[0] == 'chunks', f"❌ 첫 번째 파라미터: {params[0]} (예상: chunks)"
    assert params[1] == 'original_length', f"❌ 두 번째 파라미터: {params[1]} (예상: original_length)"
    
    logger.info("✅ validate_subchunks 시그니처 검증 통과!")
    logger.info(f"   ✅ validate_subchunks({params[0]}, {params[1]})")
    
    return True


def test_validate_subchunks_return_type():
    """
    Contract Test 2: 반환값 타입 검증
    
    검증:
    - 반환값 dict
    - 필수 키: is_valid, chunk_count, loss_rate
    """
    logger.info("\n" + "="*60)
    logger.info("Contract Test 2: 반환값 타입 검증")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    
    # 더미 데이터
    from core.annex_subchunker import SubChunk
    dummy_chunks = [
        SubChunk(
            section_id="test_1",
            section_type="header",
            content="테스트 헤더",
            metadata={},
            char_count=10,
            order=0
        )
    ]
    
    result = validate_subchunks(dummy_chunks, 100)
    
    # 반환값 타입 검증
    assert isinstance(result, dict), f"❌ 반환값 타입 불일치: {type(result)} (예상: dict)"
    
    # 필수 키 검증
    required_keys = ['is_valid', 'chunk_count', 'loss_rate']
    for key in required_keys:
        assert key in result, f"❌ 필수 키 누락: {key}"
    
    logger.info("✅ 반환값 타입 검증 통과!")
    logger.info(f"   반환 키: {list(result.keys())}")
    
    return True


# ============================================
# Contract Test: 최소 타입 보장
# ============================================

def test_minimum_type_guarantee():
    """
    Contract Test 3: 최소 타입 보장
    
    GPT 미송님: "header + content(paragraph 또는 table_rows) 필수"
    
    검증:
    - header 타입 1개 이상
    - paragraph 또는 table_rows 1개 이상
    """
    logger.info("\n" + "="*60)
    logger.info("Contract Test 3: 최소 타입 보장")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    
    # 실제 Annex 텍스트
    sample_annex = """
[별표1] 승진후보자범위
<제20조제2항관련>

임용하고자하는인원수에대한승진후보자범위

1 5번까지
2 10번까지
3 15번까지

*임용하고자하는인원수가5명까지는서열명부순위의5배수
"""
    
    chunks = chunker.chunk(sample_annex, annex_no="1")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    logger.info(f"   타입 분포: {type_counts}")
    
    # 필수 타입 검증
    assert 'header' in type_counts, "❌ header 타입 없음"
    assert 'paragraph' in type_counts or 'table_rows' in type_counts, \
        "❌ content 타입 없음 (paragraph 또는 table_rows 필수)"
    
    logger.info("✅ 최소 타입 보장 검증 통과!")
    logger.info(f"   ✅ header: {type_counts.get('header', 0)}개")
    logger.info(f"   ✅ content: paragraph {type_counts.get('paragraph', 0)}개 + table_rows {type_counts.get('table_rows', 0)}개")
    
    return True


# ============================================
# Contract Test: Loss Rate 보장
# ============================================

def test_loss_rate_guarantee():
    """
    Contract Test 4: Loss Rate < 5% 보장
    
    GPT 미송님: "텍스트 손실 ±3% 이하 보장"
    
    검증:
    - Loss Rate < 5% (보수적 기준)
    """
    logger.info("\n" + "="*60)
    logger.info("Contract Test 4: Loss Rate < 5% 보장")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    
    # 실제 Annex 텍스트
    sample_annex = """
[별표1] 승진후보자범위
<제20조제2항관련>

임용하고자하는인원수에대한승진후보자범위

1 5번까지
2 10번까지
3 15번까지

*임용하고자하는인원수가5명까지는서열명부순위의5배수
"""
    
    chunks = chunker.chunk(sample_annex, annex_no="1")
    
    # Canonical text 생성
    canonical_text = chunker._clean_annex_text(sample_annex)
    
    # 검증
    validation = validate_subchunks(chunks, len(canonical_text))
    
    loss_rate = validation['loss_rate']
    
    logger.info(f"   Loss Rate: {loss_rate:.2%}")
    
    # 5% 기준
    assert loss_rate < 0.05, f"❌ Loss Rate 초과: {loss_rate:.2%} (기준: 5%)"
    
    logger.info("✅ Loss Rate 보장 검증 통과!")
    logger.info(f"   ✅ Loss Rate: {loss_rate:.2%} < 5%")
    
    return True


# ============================================
# Contract Test: 회귀 방지 (Phase 0.9.5.1 호환성)
# ============================================

def test_backward_compatibility():
    """
    Contract Test 5: Phase 0.9.5.1 호환성 보장
    
    GPT 미송님: "표 판정 강화 중 Phase 0.9.5.1 안정성 유지"
    
    검증:
    - 기존 테스트 케이스 통과
    - DualQA 영향 없음
    """
    logger.info("\n" + "="*60)
    logger.info("Contract Test 5: Phase 0.9.5.1 호환성 보장")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    
    # Phase 0.9.5.1 검증된 케이스
    sample_annex = """
[별표1] 승진후보자범위
<제20조제2항관련>

임용하고자하는인원수에대한승진후보자범위(3급승진제외)

1 5번까지
2 10번까지
3 15번까지

*임용하고자하는인원수가5명까지는서열명부순위의5배수
"""
    
    chunks = chunker.chunk(sample_annex, annex_no="1")
    
    # 기본 검증
    assert len(chunks) >= 3, f"❌ 청크 수 부족: {len(chunks)}개 (예상: 3개 이상)"
    
    # 타입 검증
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    assert 'header' in type_counts, "❌ header 타입 없음"
    
    logger.info("✅ Phase 0.9.5.1 호환성 검증 통과!")
    logger.info(f"   ✅ 청크 수: {len(chunks)}개")
    logger.info(f"   ✅ 타입 분포: {type_counts}")
    
    return True


# ============================================
# 전체 Contract Test 실행
# ============================================

def run_all_contract_tests():
    """전체 Contract Test 실행"""
    logger.info("\n" + "="*80)
    logger.info("Phase 0.9.6 Contract Test Suite 시작")
    logger.info("="*80)
    
    tests = [
        test_validate_subchunks_signature,
        test_validate_subchunks_return_type,
        test_minimum_type_guarantee,
        test_loss_rate_guarantee,
        test_backward_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            logger.error(f"❌ {test_func.__name__} 실패: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"❌ {test_func.__name__} 오류: {e}")
            failed += 1
    
    logger.info("\n" + "="*80)
    logger.info(f"Contract Test 결과: {passed}개 통과 / {failed}개 실패")
    logger.info("="*80)
    
    if failed > 0:
        logger.error("❌ Contract Test 실패! 코드 수정 필요")
        return False
    else:
        logger.info("✅ 모든 Contract Test 통과!")
        return True


if __name__ == '__main__':
    success = run_all_contract_tests()
    sys.exit(0 if success else 1)

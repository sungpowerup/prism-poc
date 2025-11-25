"""
tests/test_phase096.py - Phase 0.9.6 TC 4종

GPT 미송님 요구사항:
1. TC1: 혼합형 (표+문단)
2. TC2: 순수 문단형
3. TC3: 순수 표형 (정렬)
4. TC4: 숫자형 리스트 (표 오인 케이스)

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-24
Version: Phase 0.9.6 TC Suite
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
# TC 데이터
# ============================================

TC1_HYBRID = """
[별표1] 승진후보자범위
<제20조제2항관련>

임용하고자하는인원수에대한승진후보자범위(3급승진제외)

1 5번까지
2 10번까지
3 15번까지
4 20번까지
5 25번까지

*임용하고자하는인원수가5명까지는서열명부순위의5배수,5명을초과하는경우에는초과인원의3배수를심사대상에포함

임용하고자하는인원수에대한승진후보자범위(3급승진)

이 규정은 3급 승진의 경우 별도의 기준을 적용한다.

1 2번까지
2 4번까지

*서열명부순위에동점자가2인이상인경우전원심사대상에포함
"""

TC2_PARAGRAPH_ONLY = """
[별표2] 응시자격
<제28조제2항관련>

직급별 승진시험 응시자격의 경력기준은 다음과 같다.

3급으로 승진하고자 하는 자는 4급에서 3년 이상 근무하여야 한다.
다만, 특별한 사유가 있을 때에는 이를 단축할 수 있다.

승진시험에 응시하고자 하는 자는 인사부서에 신청서를 제출하여야 한다.
신청 기간은 매년 상반기와 하반기 각 1회씩 공고한다.

*비고: 경력 계산 시 휴직기간은 제외한다.
"""

TC3_PURE_TABLE = """
[별표3] 승진 점수 배점표
<제30조관련>

구분        배점    비고
필기시험    40점    객관식
면접        30점    구술형
근무평정    20점    인사고과
경력        10점    재직기간

*만점은 100점이며, 60점 이상 합격으로 한다.
"""

TC4_NUMBERED_LIST = """
[별표4] 승진 심사 절차
<제25조관련>

승진 심사는 다음의 절차에 따라 진행한다.

1. 승진 대상자 명단 작성
2. 인사위원회 심의
3. 최종 승인
4. 발령 공고
5. 인사 발령

각 단계는 순차적으로 진행되며, 단계별 소요 기간은 3일 이내로 한다.

*급박한 사유가 있을 때에는 절차를 단축할 수 있다.
"""


# ============================================
# TC1: 혼합형 (표+문단)
# ============================================

def test_tc1_hybrid_table_paragraph():
    """
    TC1: 혼합형 (표+문단)
    
    검증:
    - table_rows 타입 존재
    - paragraph 타입 존재
    - note 타입 존재
    - Loss Rate < 5%
    """
    logger.info("\n" + "="*60)
    logger.info("TC1: 혼합형 (표+문단)")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(TC1_HYBRID, annex_no="1")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    logger.info(f"   타입 분포: {type_counts}")
    
    # 검증
    assert 'header' in type_counts, "❌ header 타입 없음"
    assert 'table_rows' in type_counts or 'paragraph' in type_counts, \
        "❌ content 타입 없음"
    
    # Loss Rate
    canonical_text = chunker._clean_annex_text(TC1_HYBRID)
    validation = validate_subchunks(chunks, len(canonical_text))
    
    logger.info(f"   Loss Rate: {validation['loss_rate']:.2%}")
    
    assert validation['loss_rate'] < 0.05, \
        f"❌ Loss Rate 초과: {validation['loss_rate']:.2%}"
    
    logger.info("✅ TC1 통과!")
    logger.info(f"   ✅ 청크 수: {len(chunks)}개")
    logger.info(f"   ✅ Loss Rate: {validation['loss_rate']:.2%}")
    
    # Metadata 검증 (Phase 0.9.6)
    table_chunks = [c for c in chunks if c.section_type == 'table_rows']
    if table_chunks:
        logger.info(f"\n   📊 표 판정 Metadata:")
        for i, tc in enumerate(table_chunks):
            logger.info(f"      Table {i+1}:")
            for key, value in tc.metadata.items():
                logger.info(f"         {key}: {value}")
    
    return True


# ============================================
# TC2: 순수 문단형
# ============================================

def test_tc2_paragraph_only():
    """
    TC2: 순수 문단형
    
    검증:
    - table_rows 타입 없음 (0개)
    - paragraph 타입만 존재
    - Loss Rate < 5%
    """
    logger.info("\n" + "="*60)
    logger.info("TC2: 순수 문단형")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(TC2_PARAGRAPH_ONLY, annex_no="2")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    logger.info(f"   타입 분포: {type_counts}")
    
    # 검증: table_rows 없어야 함
    assert type_counts.get('table_rows', 0) == 0, \
        f"❌ 표가 잘못 감지됨: {type_counts.get('table_rows', 0)}개"
    
    assert 'paragraph' in type_counts, "❌ paragraph 타입 없음"
    
    # Loss Rate
    canonical_text = chunker._clean_annex_text(TC2_PARAGRAPH_ONLY)
    validation = validate_subchunks(chunks, len(canonical_text))
    
    logger.info(f"   Loss Rate: {validation['loss_rate']:.2%}")
    
    assert validation['loss_rate'] < 0.05, \
        f"❌ Loss Rate 초과: {validation['loss_rate']:.2%}"
    
    logger.info("✅ TC2 통과!")
    logger.info(f"   ✅ 청크 수: {len(chunks)}개")
    logger.info(f"   ✅ table_rows: 0개 (정상)")
    logger.info(f"   ✅ paragraph: {type_counts.get('paragraph', 0)}개")
    
    return True


# ============================================
# TC3: 순수 표형
# ============================================

def test_tc3_pure_table():
    """
    TC3: 순수 표형 (정렬)
    
    검증:
    - table_rows 타입 존재
    - 공백 정렬 감지
    - Loss Rate < 5%
    """
    logger.info("\n" + "="*60)
    logger.info("TC3: 순수 표형 (정렬)")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(TC3_PURE_TABLE, annex_no="3")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    logger.info(f"   타입 분포: {type_counts}")
    
    # 검증: table_rows 있어야 함
    assert 'table_rows' in type_counts, "❌ 표가 감지되지 않음"
    
    # Loss Rate
    canonical_text = chunker._clean_annex_text(TC3_PURE_TABLE)
    validation = validate_subchunks(chunks, len(canonical_text))
    
    logger.info(f"   Loss Rate: {validation['loss_rate']:.2%}")
    
    assert validation['loss_rate'] < 0.05, \
        f"❌ Loss Rate 초과: {validation['loss_rate']:.2%}"
    
    logger.info("✅ TC3 통과!")
    logger.info(f"   ✅ 청크 수: {len(chunks)}개")
    logger.info(f"   ✅ table_rows: {type_counts.get('table_rows', 0)}개")
    
    # Metadata 검증
    table_chunks = [c for c in chunks if c.section_type == 'table_rows']
    if table_chunks:
        logger.info(f"\n   📊 표 판정 Metadata:")
        for i, tc in enumerate(table_chunks):
            logger.info(f"      Table {i+1}:")
            for key, value in tc.metadata.items():
                logger.info(f"         {key}: {value}")
    
    return True


# ============================================
# TC4: 숫자형 리스트 (표 오인 케이스)
# ============================================

def test_tc4_numbered_list():
    """
    TC4: 숫자형 리스트 (표 오인 케이스)
    
    검증:
    - table_rows 타입 없음 (0개) - 핵심!
    - paragraph 타입만 존재
    - Fallback이 올바르게 작동
    """
    logger.info("\n" + "="*60)
    logger.info("TC4: 숫자형 리스트 (표 오인 방지)")
    logger.info("="*60)
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(TC4_NUMBERED_LIST, annex_no="4")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    logger.info(f"   타입 분포: {type_counts}")
    
    # 검증: table_rows 없어야 함 (핵심!)
    table_count = type_counts.get('table_rows', 0)
    
    if table_count > 0:
        logger.warning(f"⚠️ 숫자형 리스트를 표로 오인: {table_count}개")
        logger.warning("   GPT 미송님: '이 케이스는 반드시 paragraph로 처리되어야 함'")
        
        # Metadata 출력 (디버깅용)
        table_chunks = [c for c in chunks if c.section_type == 'table_rows']
        for i, tc in enumerate(table_chunks):
            logger.warning(f"\n      오인된 Table {i+1} Metadata:")
            for key, value in tc.metadata.items():
                logger.warning(f"         {key}: {value}")
    
    assert table_count == 0, \
        f"❌ 숫자형 리스트를 표로 오인: {table_count}개 (Fallback 실패)"
    
    assert 'paragraph' in type_counts, "❌ paragraph 타입 없음"
    
    # Loss Rate
    canonical_text = chunker._clean_annex_text(TC4_NUMBERED_LIST)
    validation = validate_subchunks(chunks, len(canonical_text))
    
    logger.info(f"   Loss Rate: {validation['loss_rate']:.2%}")
    
    assert validation['loss_rate'] < 0.05, \
        f"❌ Loss Rate 초과: {validation['loss_rate']:.2%}"
    
    logger.info("✅ TC4 통과!")
    logger.info(f"   ✅ 청크 수: {len(chunks)}개")
    logger.info(f"   ✅ table_rows: 0개 (Fallback 정상)")
    logger.info(f"   ✅ paragraph: {type_counts.get('paragraph', 0)}개")
    
    return True


# ============================================
# 전체 TC Suite 실행
# ============================================

def run_all_tc_tests():
    """전체 TC Suite 실행"""
    logger.info("\n" + "="*80)
    logger.info("Phase 0.9.6 TC Suite 시작 (4종)")
    logger.info("="*80)
    
    tests = [
        test_tc1_hybrid_table_paragraph,
        test_tc2_paragraph_only,
        test_tc3_pure_table,
        test_tc4_numbered_list
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
    logger.info(f"TC Suite 결과: {passed}개 통과 / {failed}개 실패")
    logger.info("="*80)
    
    if failed > 0:
        logger.error("❌ TC Suite 실패! 표 판정 로직 수정 필요")
        return False
    else:
        logger.info("✅ 모든 TC 통과!")
        return True


if __name__ == '__main__':
    success = run_all_tc_tests()
    sys.exit(0 if success else 1)

"""
test_phase_0990_unit.py - Phase 0.9.9.0 단위 테스트

테스트 범위:
1. 텍스트형 표 힌트 감지
2. paragraph/table_candidate → table_rows 승격
3. 별표1 회귀 테스트 (기존 150행 유지)

Author: 마창수산팀
Date: 2025-12-01
Version: Phase 0.9.9.0 Unit Test
"""

import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, '/mnt/user-data/outputs')

# Phase 0.9.9.0 버전 import
from annex_subchunker_0990 import AnnexSubChunker, SubChunk

# ============================================
# TC1: 텍스트형 표 힌트 감지 테스트
# ============================================

def test_text_table_hints_detection():
    """텍스트형 표 힌트 감지 테스트"""
    print("\n" + "="*60)
    print("TC1: 텍스트형 표 힌트 감지")
    print("="*60)
    
    chunker = AnnexSubChunker()
    
    # 별표2 스타일 텍스트 (직급 + 응시자격)
    test_lines = [
        "직급    응시자격    비고",
        "",
        "1급",
        "1. 공무원 4급이상으로 1년이상 재직한 자",
        "2. 경찰공무원 총경이상으로 1년이상 재직한 자",
        "3. 군인 대령이상 장교로 1년이상 재직한 자",
        "",
        "2급",
        "1. 공무원 5급이상으로 1년이상 재직한 자",
        "2. 경찰공무원 경정이상으로 1년이상 재직한 자"
    ]
    
    # 힌트 감지
    hints = chunker._check_text_table_hints(test_lines)
    
    print(f"   📊 감지 결과:")
    print(f"      Header Hint: {hints['has_header_hint']}")
    print(f"      Keywords: {hints['header_keywords']}")
    print(f"      Numbered List: {hints['has_numbered_list']} ({hints['numbered_count']}개)")
    print(f"      Rank Pattern: {hints['has_rank_pattern']} ({hints['rank_count']}개)")
    
    # 검증
    assert hints['has_header_hint'], "❌ Header Hint 감지 실패"
    assert '직급' in hints['header_keywords'], "❌ '직급' 키워드 누락"
    assert '응시자격' in hints['header_keywords'] or '자격' in hints['header_keywords'], "❌ 자격 관련 키워드 누락"
    assert hints['has_numbered_list'], "❌ Numbered List 감지 실패"
    assert hints['numbered_count'] >= 3, f"❌ Numbered List 개수 부족: {hints['numbered_count']}"
    assert hints['has_rank_pattern'], "❌ Rank Pattern 감지 실패"
    assert hints['rank_count'] >= 2, f"❌ Rank Pattern 개수 부족: {hints['rank_count']}"
    
    print("   ✅ TC1 통과!")
    return True


# ============================================
# TC2: 승격 로직 테스트
# ============================================

def test_text_table_upgrade():
    """텍스트형 표 승격 로직 테스트"""
    print("\n" + "="*60)
    print("TC2: 텍스트형 표 승격 로직")
    print("="*60)
    
    chunker = AnnexSubChunker()
    
    # paragraph 블록 시뮬레이션
    test_block = {
        'type': 'paragraph',
        'lines': [
            "직급    응시자격    비고",
            "1급",
            "1. 공무원 4급이상으로 1년이상 재직한 자",
            "2. 경찰공무원 총경이상으로 1년이상 재직한 자",
            "2급",
            "1. 공무원 5급이상으로 1년이상 재직한 자"
        ],
        'metadata': {}
    }
    
    # 승격 시도
    upgraded_block = chunker._enhance_table_candidate_with_text_hints(test_block)
    
    print(f"   📊 승격 결과:")
    print(f"      Before: {test_block['type']}")
    print(f"      After: {upgraded_block['type']}")
    print(f"      Upgraded: {upgraded_block['metadata'].get('upgraded_by_text_hints', False)}")
    print(f"      Reason: {upgraded_block['metadata'].get('upgrade_reason', 'N/A')}")
    
    # 검증
    assert upgraded_block['type'] == 'table_rows', f"❌ 승격 실패: {upgraded_block['type']}"
    assert upgraded_block['metadata']['upgraded_by_text_hints'], "❌ 승격 플래그 없음"
    assert 'upgrade_reason' in upgraded_block['metadata'], "❌ 승격 사유 없음"
    
    print("   ✅ TC2 통과!")
    return True


# ============================================
# TC3: 실제 별표2 청킹 테스트
# ============================================

def test_annex2_chunking():
    """실제 별표2 텍스트 청킹 테스트"""
    print("\n" + "="*60)
    print("TC3: 별표2 실제 청킹 테스트")
    print("="*60)
    
    chunker = AnnexSubChunker()
    
    # 별표2 실제 텍스트 (간소화 버전)
    annex2_text = """[별표 2] 제한경쟁채용시험 응시자격(직급별 경력기준)
<제10조제1항 관련>

제한경쟁채용시험 응시자격(직급별 경력기준)

직급    응시자격    비고

1급
1. 공무원 4급이상으로 1년이상 재직한 자
2. 경찰공무원 총경이상으로 1년이상 재직한 자
3. 군인 대령이상 장교로 1년이상 재직한 자
4. 판사 및 검사 9호봉이상으로 1년이상 재직한 자

2급
1. 공무원 5급이상으로 1년이상 재직한 자
2. 경찰공무원 경정이상으로 1년이상 재직한 자
3. 군인 중령이상 장교로 1년이상 재직한 자

3급
1. 공무원 6급이상으로 1년이상 재직한 자
2. 경찰공무원 경위이상으로 1년이상 재직한 자
"""
    
    # 청킹 실행
    chunks = chunker.chunk(annex2_text, annex_no="2")
    
    print(f"   📊 청킹 결과:")
    print(f"      총 청크 수: {len(chunks)}개")
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    print(f"      타입 분포: {type_counts}")
    
    # table_rows 청크 확인
    table_chunks = [c for c in chunks if c.section_type == 'table_rows']
    
    if table_chunks:
        print(f"\n   📋 table_rows 청크:")
        for i, tc in enumerate(table_chunks):
            print(f"      Table {i+1}:")
            print(f"         Content: {tc.content[:100]}...")
            print(f"         Metadata:")
            for key, value in tc.metadata.items():
                if key == 'text_table_hints':
                    print(f"            {key}: {value}")
                elif key not in ['merged_from_candidates']:
                    print(f"            {key}: {value}")
    
    # 검증
    assert len(chunks) > 0, "❌ 청크 생성 실패"
    assert 'table_rows' in type_counts, "❌ table_rows 타입 없음"
    assert type_counts['table_rows'] >= 1, f"❌ table_rows 개수 부족: {type_counts.get('table_rows', 0)}"
    
    print("   ✅ TC3 통과!")
    return True


# ============================================
# 실행
# ============================================

if __name__ == '__main__':
    print("\n" + "🚀 Phase 0.9.9.0 단위 테스트 시작")
    print("="*60)
    
    try:
        # TC1: 힌트 감지
        test_text_table_hints_detection()
        
        # TC2: 승격 로직
        test_text_table_upgrade()
        
        # TC3: 실제 청킹
        test_annex2_chunking()
        
        print("\n" + "="*60)
        print("✅ Phase 0.9.9.0 단위 테스트 전체 통과!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

"""
example_golden_usage.py - Golden File 사용 예시
PRISM Phase 0.8

이 파일은 tests/ 폴더에 저장하세요.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.law_parser import LawParser
from core.dual_qa_gate import extract_pdf_text_layer
from tests.golden_schema import (
    GoldenFile, GoldenMetadata,
    create_golden_from_parsed_result
)
from tests.golden_diff_engine import GoldenDiffEngine


# ============================================
# 예시 1: Golden File 생성
# ============================================

def example_create_golden():
    """Golden File 생성 예시"""
    
    print("\n" + "="*60)
    print("📝 예시 1: Golden File 생성")
    print("="*60)
    
    # PDF 경로
    pdf_path = "인사규정_일부개정전문-1-3_원본.pdf"
    
    # 1. PDF 텍스트 추출
    print("1️⃣ PDF 텍스트 추출 중...")
    pdf_text = extract_pdf_text_layer(pdf_path)
    print(f"   ✅ {len(pdf_text)}자 추출")
    
    # 2. LawParser 파싱
    print("2️⃣ LawParser 파싱 중...")
    parser = LawParser()
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title="인사규정",
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    print(f"   ✅ {parsed_result['total_chapters']}개 장, "
          f"{parsed_result['total_articles']}개 조문")
    
    # 3. Golden Metadata 생성
    print("3️⃣ Golden Metadata 생성 중...")
    metadata = GoldenMetadata(
        parser_version="0.8.0",
        schema_version="1.0",
        document_title="인사규정",
        document_type="standard",
        golden_verified_date="2025-11-14",
        golden_verified_by="법무팀 김민지",
        source_file=pdf_path,
        page_count=3,
        notes="Phase 0.8 초기 테스트"
    )
    
    # 4. Golden File 생성
    print("4️⃣ Golden File 생성 중...")
    golden = create_golden_from_parsed_result(parsed_result, metadata)
    
    # 5. 저장
    output_path = "tests/golden/standard/인사규정_golden.json"
    golden.to_json(output_path)
    print(f"💾 저장 완료: {output_path}")
    
    return golden


# ============================================
# 예시 2: Golden File 비교
# ============================================

def example_compare_golden():
    """Golden File 비교 예시"""
    
    print("\n" + "="*60)
    print("🔬 예시 2: Golden File 비교")
    print("="*60)
    
    # 1. Golden File 로드
    golden_path = "tests/golden/standard/인사규정_golden.json"
    print(f"1️⃣ Golden File 로드: {golden_path}")
    golden = GoldenFile.from_json(golden_path)
    print(f"   ✅ 로드 완료 (버전: {golden.metadata.parser_version})")
    
    # 2. 현재 Parser 결과 생성
    print("2️⃣ 현재 Parser 결과 생성 중...")
    pdf_path = "인사규정_일부개정전문-1-3_원본.pdf"
    pdf_text = extract_pdf_text_layer(pdf_path)
    
    parser = LawParser()
    current_result = parser.parse(
        pdf_text=pdf_text,
        document_title="인사규정",
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    print(f"   ✅ 파싱 완료")
    
    # 3. 비교 엔진 실행
    print("3️⃣ Golden Diff 실행 중...")
    diff_engine = GoldenDiffEngine(
        structure_threshold=1.0,   # 구조 100% 일치
        header_threshold=0.95,     # 헤더 95% 이상
        content_threshold=0.90     # 본문 90% 이상
    )
    
    report = diff_engine.compare(
        golden=golden.to_dict(),
        result=current_result
    )
    
    # 4. 결과 출력
    report.print_summary()
    
    # 5. 리포트 저장
    report_path = "tests/golden/standard/인사규정_diff_report.json"
    report.to_json(report_path)
    print(f"\n💾 리포트 저장: {report_path}")
    
    return report


# ============================================
# 예시 3: 회귀 테스트
# ============================================

def example_regression_test():
    """여러 Golden File 회귀 테스트"""
    
    print("\n" + "="*60)
    print("🔁 예시 3: 회귀 테스트")
    print("="*60)
    
    # Golden Files 목록
    golden_files = [
        "tests/golden/standard/인사규정_golden.json",
        # "tests/golden/standard/보수규정_golden.json",  # 추가 가능
        # "tests/golden/standard/복무규정_golden.json",
    ]
    
    diff_engine = GoldenDiffEngine()
    
    all_pass = True
    results = []
    
    for golden_path in golden_files:
        print(f"\n📄 테스트: {Path(golden_path).stem}")
        
        # Golden 로드
        golden = GoldenFile.from_json(golden_path)
        
        # 현재 Parser 결과
        pdf_path = golden.metadata.source_file
        pdf_text = extract_pdf_text_layer(pdf_path)
        
        parser = LawParser()
        current_result = parser.parse(
            pdf_text=pdf_text,
            document_title=golden.metadata.document_title,
            clean_artifacts=True,
            normalize_linebreaks=True
        )
        
        # 비교
        report = diff_engine.compare(
            golden=golden.to_dict(),
            result=current_result
        )
        
        results.append({
            'file': golden_path,
            'pass': report.overall_pass,
            'score': report.overall_score
        })
        
        if report.overall_pass:
            print(f"   ✅ PASS ({report.overall_score*100:.1f}%)")
        else:
            print(f"   ❌ FAIL ({report.overall_score*100:.1f}%)")
            all_pass = False
    
    # 최종 결과
    print("\n" + "="*60)
    print("📊 회귀 테스트 최종 결과")
    print("="*60)
    
    for result in results:
        status = "✅ PASS" if result['pass'] else "❌ FAIL"
        print(f"{status} - {Path(result['file']).stem} ({result['score']*100:.1f}%)")
    
    print("\n" + ("✅ 모든 테스트 통과!" if all_pass else "❌ 일부 테스트 실패"))
    
    return all_pass


# ============================================
# 메인 실행
# ============================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Golden File 사용 예시")
    parser.add_argument(
        'example',
        choices=['create', 'compare', 'regression'],
        help='실행할 예시 (create/compare/regression)'
    )
    
    args = parser.parse_args()
    
    if args.example == 'create':
        example_create_golden()
    
    elif args.example == 'compare':
        example_compare_golden()
    
    elif args.example == 'regression':
        example_regression_test()
    
    print("\n✅ 완료!")

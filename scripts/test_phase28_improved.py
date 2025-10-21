"""
scripts/test_phase28_improved.py
Phase 2.8 개선 버전 테스트

개선 사항:
- 한글 인코딩 수정
- Element 세부 분류
- 청킹 개선
- 프롬프트 개선

사용법:
    python scripts/test_phase28_improved.py input/test_parser_02.pdf
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.phase28_pipeline import Phase28Pipeline


def test_encoding_fix(result: dict):
    """
    한글 인코딩 수정 확인
    """
    print("\n" + "="*60)
    print("1️⃣ 한글 인코딩 테스트")
    print("="*60)
    
    bad_patterns = ['ì', 'ë', 'í', 'ê', 'î', 'ï']
    
    for chunk in result['stage2_chunks']:
        content = chunk['content']
        
        # 인코딩 문제 패턴 검사
        has_issue = any(p in content for p in bad_patterns)
        
        if has_issue:
            print(f"❌ 페이지 {chunk['page_number']}: 인코딩 오류 감지")
            print(f"   샘플: {content[:100]}...")
            return False
    
    print("✅ 모든 청크에서 한글 인코딩 정상")
    
    # 샘플 출력
    sample = result['stage2_chunks'][0]['content'][:200]
    print(f"\n📝 샘플 텍스트:")
    print(f"   {sample}...")
    
    return True


def test_element_classification(result: dict):
    """
    Element 세부 분류 확인
    """
    print("\n" + "="*60)
    print("2️⃣ Element 세부 분류 테스트")
    print("="*60)
    
    for element in result['stage1_elements']:
        page = element['page_number']
        etype = element['element_type']
        subtypes = element.get('subtypes', [])
        confidence = element['confidence']
        
        print(f"\n📄 페이지 {page}:")
        print(f"   타입: {etype}")
        print(f"   세부 타입: {', '.join(subtypes) if subtypes else '없음'}")
        print(f"   신뢰도: {confidence:.2f}")
        
        # 검증: 세부 타입이 있는지
        if etype in ['chart', 'diagram'] and not subtypes:
            print(f"   ⚠️ 경고: {etype}인데 세부 타입 없음")
    
    return True


def test_chunking_quality(result: dict):
    """
    청킹 품질 확인
    """
    print("\n" + "="*60)
    print("3️⃣ 청킹 품질 테스트")
    print("="*60)
    
    chunk_lengths = []
    sentence_breaks = 0
    
    for chunk in result['stage2_chunks']:
        content = chunk['content']
        length = len(content)
        chunk_lengths.append(length)
        
        # 문장 중간 자름 감지 (온점 없이 끝남)
        if not content.rstrip().endswith(('.', '!', '?', '"', ')', ']')):
            sentence_breaks += 1
    
    avg_length = sum(chunk_lengths) / len(chunk_lengths)
    min_length = min(chunk_lengths)
    max_length = max(chunk_lengths)
    
    print(f"📊 청크 통계:")
    print(f"   총 청크: {len(chunk_lengths)}개")
    print(f"   평균 길이: {avg_length:.0f}자")
    print(f"   최소/최대: {min_length} / {max_length}자")
    print(f"   문장 중간 자름: {sentence_breaks}개")
    
    if sentence_breaks > 0:
        print(f"   ⚠️ 경고: {sentence_breaks}개 청크가 문장 중간에서 잘림")
    else:
        print(f"   ✅ 모든 청크가 문장 단위로 분할됨")
    
    return sentence_breaks == 0


def test_caption_quality(result: dict):
    """
    캡션 품질 확인
    """
    print("\n" + "="*60)
    print("4️⃣ 캡션 품질 테스트")
    print("="*60)
    
    quality_checks = {
        'has_chart_type': 0,  # "원그래프", "막대그래프" 등 명시
        'has_numbers': 0,      # 구체적인 수치
        'has_insight': 0,      # "가장 높음", "패턴" 등
        'has_structure': 0     # "첫 번째", "**제목**" 등
    }
    
    chart_types = ['원그래프', '막대그래프', '선그래프', '파이 차트', '표', '차트']
    insight_keywords = ['가장', '높은', '낮은', '비율', '패턴', '특징', '분포']
    structure_markers = ['**', '첫 번째', '두 번째', '##']
    
    for chunk in result['stage2_chunks']:
        content = chunk['content']
        
        # 차트 타입 명시
        if any(ct in content for ct in chart_types):
            quality_checks['has_chart_type'] += 1
        
        # 숫자 포함
        if any(char.isdigit() for char in content):
            quality_checks['has_numbers'] += 1
        
        # 인사이트
        if any(kw in content for kw in insight_keywords):
            quality_checks['has_insight'] += 1
        
        # 구조적 서술
        if any(sm in content for sm in structure_markers):
            quality_checks['has_structure'] += 1
    
    total = len(result['stage2_chunks'])
    
    print(f"📈 캡션 품질 지표:")
    print(f"   차트 타입 명시: {quality_checks['has_chart_type']}/{total} ({quality_checks['has_chart_type']/total*100:.0f}%)")
    print(f"   구체적 수치: {quality_checks['has_numbers']}/{total} ({quality_checks['has_numbers']/total*100:.0f}%)")
    print(f"   인사이트 제공: {quality_checks['has_insight']}/{total} ({quality_checks['has_insight']/total*100:.0f}%)")
    print(f"   구조적 서술: {quality_checks['has_structure']}/{total} ({quality_checks['has_structure']/total*100:.0f}%)")
    
    # 샘플 출력
    print(f"\n📝 캡션 샘플 (페이지 1):")
    sample = result['stage2_chunks'][0]['content']
    print(f"   {sample[:300]}...")
    
    return True


def compare_with_baseline(result: dict, baseline_path: str = None):
    """
    경쟁사 결과와 비교 (옵션)
    """
    if not baseline_path or not Path(baseline_path).exists():
        print("\n⚠️ 경쟁사 비교 파일 없음 (생략)")
        return
    
    print("\n" + "="*60)
    print("5️⃣ 경쟁사 비교")
    print("="*60)
    
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = f.read()
    
    # 간단한 키워드 비교
    keywords = ['원그래프', '막대그래프', '비율', '가장 높은', '분포', '특성']
    
    prism_count = sum(k in str(result) for k in keywords)
    baseline_count = sum(k in baseline for k in keywords)
    
    print(f"키워드 출현 빈도:")
    print(f"   PRISM: {prism_count}회")
    print(f"   경쟁사: {baseline_count}회")
    
    if prism_count >= baseline_count * 0.8:
        print(f"   ✅ 경쟁사 대비 80% 이상 달성")
    else:
        print(f"   ⚠️ 경쟁사 대비 부족 ({prism_count/baseline_count*100:.0f}%)")


def main():
    """
    메인 테스트 실행
    """
    if len(sys.argv) < 2:
        print("사용법: python scripts/test_phase28_improved.py <pdf_path> [baseline_md]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    baseline_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("\n" + "="*60)
    print("🔷 PRISM Phase 2.8 개선 버전 테스트")
    print("="*60)
    print(f"PDF: {pdf_path}")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 처리 실행
    pipeline = Phase28Pipeline(vlm_provider='azure_openai')
    result = pipeline.process_pdf(pdf_path, output_dir='output', max_pages=3)
    
    # 테스트 실행
    tests = [
        ("한글 인코딩", test_encoding_fix),
        ("Element 분류", test_element_classification),
        ("청킹 품질", test_chunking_quality),
        ("캡션 품질", test_caption_quality),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func(result)
        except Exception as e:
            print(f"\n❌ {name} 테스트 실패: {e}")
            results[name] = False
    
    # 경쟁사 비교 (옵션)
    if baseline_path:
        compare_with_baseline(result, baseline_path)
    
    # 최종 결과
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    for name, passed in results.items():
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\n종합: {passed}/{total} 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 개선 완료!")
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패. 추가 개선 필요.")
    
    print(f"\n완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
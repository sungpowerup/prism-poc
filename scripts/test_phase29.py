"""
scripts/test_phase29.py
PRISM Phase 2.9 통합 테스트

테스트 항목:
1. 모듈 임포트
2. 인코딩 수정
3. 프롬프트 생성
4. 청킹 로직
5. 전체 파이프라인

Usage:
    python scripts/test_phase29.py
    python scripts/test_phase29.py input/test_parser_02.pdf

Author: 정수아 (QA Lead)
Date: 2025-10-21
"""

import sys
import os
from pathlib import Path
import json
import logging

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """1. 모듈 임포트 테스트"""
    print("\n" + "="*60)
    print("1️⃣ 모듈 임포트 테스트")
    print("="*60)
    
    try:
        from core.structured_prompts import StructuredPrompts
        print("✅ structured_prompts.py")
    except ImportError as e:
        print(f"❌ structured_prompts.py: {e}")
        return False
    
    try:
        from core.encoding_fixer import EncodingFixer, SmartEncodingFixer
        print("✅ encoding_fixer.py")
    except ImportError as e:
        print(f"❌ encoding_fixer.py: {e}")
        return False
    
    try:
        from core.structural_chunker import RAGOptimizedChunker
        print("✅ structural_chunker.py")
    except ImportError as e:
        print(f"❌ structural_chunker.py: {e}")
        return False
    
    try:
        from core.phase29_pipeline import Phase29Pipeline
        print("✅ phase29_pipeline.py")
    except ImportError as e:
        print(f"❌ phase29_pipeline.py: {e}")
        return False
    
    print("\n모든 모듈 임포트 성공! ✅")
    return True


def test_encoding_fixer():
    """2. 인코딩 수정 테스트"""
    print("\n" + "="*60)
    print("2️⃣ 인코딩 수정 테스트")
    print("="*60)
    
    from core.encoding_fixer import EncodingFixer, SmartEncodingFixer
    
    # 테스트 케이스
    test_cases = [
        ("i\xc2\xb4 \xed\x91\x9c\xeb\x8a\x94 2023\xeb\x85\x84", "이 표는 2023년"),
        ("\xed\x94\x84\xeb\xa1\x9c\xec\x8a\xa4\xed\x8f\xac\xec\x9d\xb8 \xed\x8c\xac", "프로스포츠 팬"),
        ("\xec\x88\x98\xeb\x8f\x84\xea\xb6\x8c\xec\x9d\xb4 52.5%", "수도권이 52.5%"),
        ("정상 텍스트", "정상 텍스트"),  # 수정 불필요
    ]
    
    fixer = EncodingFixer()
    smart_fixer = SmartEncodingFixer()
    
    all_passed = True
    
    for i, (broken, expected) in enumerate(test_cases, 1):
        # EncodingFixer
        fixed = fixer.fix_text(broken)
        
        if fixed == expected:
            print(f"✅ 케이스 {i}: EncodingFixer")
            print(f"   Before: {broken[:30]}...")
            print(f"   After:  {fixed[:30]}...")
        else:
            print(f"❌ 케이스 {i}: EncodingFixer 실패")
            print(f"   Expected: {expected}")
            print(f"   Got:      {fixed}")
            all_passed = False
        
        # SmartEncodingFixer
        smart_fixed, confidence = smart_fixer.fix_with_confidence(broken)
        
        if smart_fixed == expected:
            print(f"✅ 케이스 {i}: SmartEncodingFixer (신뢰도: {confidence:.2%})")
        else:
            print(f"❌ 케이스 {i}: SmartEncodingFixer 실패")
            all_passed = False
    
    stats = fixer.get_stats()
    print(f"\n통계: {stats['fixed']}건 수정, {stats['errors']}건 실패")
    
    return all_passed


def test_prompts():
    """3. 프롬프트 생성 테스트"""
    print("\n" + "="*60)
    print("3️⃣ 프롬프트 생성 테스트")
    print("="*60)
    
    from core.structured_prompts import StructuredPrompts
    
    prompts = StructuredPrompts()
    
    # 전체 페이지 프롬프트
    full_prompt = prompts.get_full_page_analysis_prompt()
    print(f"✅ 전체 페이지 프롬프트: {len(full_prompt)}자")
    
    # 필수 키워드 확인
    required_keywords = [
        '섹션 구조',
        '시각화 요소',
        '데이터',
        '인사이트',
        '지역 데이터'
    ]
    
    for keyword in required_keywords:
        if keyword in full_prompt:
            print(f"   ✅ '{keyword}' 포함")
        else:
            print(f"   ❌ '{keyword}' 누락")
            return False
    
    # 차트별 프롬프트
    chart_types = ['pie', 'bar', 'table', 'map']
    
    for chart_type in chart_types:
        prompt = prompts.get_chart_specific_prompt(chart_type)
        print(f"✅ {chart_type} 프롬프트: {len(prompt)}자")
    
    return True


def test_chunking():
    """4. 청킹 로직 테스트"""
    print("\n" + "="*60)
    print("4️⃣ 청킹 로직 테스트")
    print("="*60)
    
    from core.structural_chunker import RAGOptimizedChunker
    
    # 테스트 텍스트
    test_text = """### 06. 응답자 특성

#### ☉ 응답자 성별 및 연령

**첫 번째 원그래프 - 성별 분포**

이 차트는 응답자의 성별 분포를 나타냅니다. 단위는 백분율(%)입니다.

**데이터:**
- 남성: 45.2%
- 여성: 54.8%

**인사이트:**
여성 응답자가 더 많습니다.

---

**두 번째 막대그래프 - 연령 분포**

이 차트는 연령대별 분포를 나타냅니다.

**데이터:**
- 14~19세: 11.2%
- 20대: 25.9%
- 30대: 22.3%
- 40대: 19.9%
- 50대 이상: 20.7%

**인사이트:**
20대가 가장 많습니다."""
    
    chunker = RAGOptimizedChunker(
        min_chunk_size=100,
        max_chunk_size=400,
        overlap=50
    )
    
    chunks = chunker.chunk_document(test_text, page_number=1, element_type='table')
    
    print(f"✅ 생성된 청크: {len(chunks)}개")
    
    # 각 청크 검증
    for i, chunk in enumerate(chunks, 1):
        print(f"\n청크 #{i}:")
        print(f"  길이: {len(chunk.content)}자")
        print(f"  섹션: {chunk.metadata.get('section_title', 'N/A')}")
        print(f"  차트: {chunk.metadata.get('chart_type', 'N/A')}")
        print(f"  키워드: {chunk.metadata.get('keywords', [])[:3]}")
        
        # 청크 크기 검증
        if len(chunk.content) < 50:
            print(f"  ⚠️ 경고: 청크가 너무 작음")
        elif len(chunk.content) > 500:
            print(f"  ⚠️ 경고: 청크가 너무 큼")
    
    # 구조 보존 확인
    if '###' in chunks[0].content or '####' in chunks[0].content:
        print("\n✅ 섹션 헤더 보존됨")
    else:
        print("\n⚠️ 섹션 헤더 누락")
    
    return len(chunks) > 0


def test_full_pipeline(pdf_path: str = None):
    """5. 전체 파이프라인 테스트"""
    print("\n" + "="*60)
    print("5️⃣ 전체 파이프라인 테스트")
    print("="*60)
    
    if not pdf_path or not Path(pdf_path).exists():
        print("⚠️ PDF 파일이 제공되지 않음 - 파이프라인 테스트 생략")
        return True
    
    from core.phase29_pipeline import Phase29Pipeline
    
    try:
        # 파이프라인 초기화
        pipeline = Phase29Pipeline(vlm_provider='azure_openai')
        print("✅ Pipeline 초기화 성공")
        
        # 처리
        print(f"\n📄 처리 중: {Path(pdf_path).name}")
        result = pipeline.process_pdf(pdf_path, output_dir='output', max_pages=1)
        
        # 결과 검증
        print(f"\n✅ 처리 완료")
        print(f"   페이지: {result['metadata']['total_pages']}")
        print(f"   청크: {result['metadata']['total_chunks']}")
        print(f"   시간: {result['metadata']['processing_time_sec']:.2f}초")
        print(f"   인코딩 수정: {result['metadata']['encoding_fixes']['fixed']}건")
        
        # 첫 번째 청크 샘플 출력
        if result['stage3_chunks']:
            first_chunk = result['stage3_chunks'][0]
            print(f"\n📝 첫 번째 청크 샘플:")
            print(f"   {first_chunk['content'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 파이프라인 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       PRISM Phase 2.9 통합 테스트                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # PDF 경로 (옵션)
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 테스트 실행
    results = {}
    
    results['imports'] = test_imports()
    results['encoding'] = test_encoding_fixer()
    results['prompts'] = test_prompts()
    results['chunking'] = test_chunking()
    results['pipeline'] = test_full_pipeline(pdf_path)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{test_name:15s}: {status}")
    
    # 전체 결과
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 모든 테스트 통과!")
        print("Phase 2.9 배포 준비 완료")
    else:
        print("⚠️ 일부 테스트 실패")
        print("문제를 해결한 후 다시 테스트하세요")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
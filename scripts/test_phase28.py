"""
PRISM Phase 2.8 - 품질 비교 테스트 스크립트
경쟁사 대비 품질 자동 평가

Author: 정수아 (QA Lead)
Date: 2025-10-21
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Core 모듈
from core.phase28_pipeline import Phase28Pipeline


def test_document(pdf_path: str, output_dir: str = "output"):
    """문서 테스트"""
    
    print("="*60)
    print("🔷 PRISM Phase 2.8 - 품질 테스트")
    print("="*60)
    print(f"📄 테스트 문서: {pdf_path}")
    print(f"📂 출력 디렉토리: {output_dir}")
    print("="*60)
    print()
    
    # Pipeline 초기화
    pipeline = Phase28Pipeline(vlm_provider="claude")
    
    # 문서 처리
    print("🚀 처리 시작...\n")
    
    result = pipeline.process_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        max_pages=None  # 전체 페이지
    )
    
    print("\n" + "="*60)
    print("✅ 테스트 완료!")
    print("="*60)
    
    # 결과 요약
    meta = result['metadata']
    
    print("\n📊 결과 요약:")
    print(f"  - 총 페이지: {meta['total_pages']}")
    print(f"  - 총 청크: {meta['total_chunks']}")
    print(f"  - 처리 시간: {meta['processing_time_sec']:.2f}초")
    print(f"  - 페이지당 평균: {meta['processing_time_sec']/meta['total_pages']:.2f}초")
    
    print("\n📈 Element 타입별:")
    for element_type, count in meta['chunk_types'].items():
        print(f"  - {element_type}: {count}개")
    
    print("\n💾 저장된 파일:")
    output_path = Path(output_dir)
    for file in sorted(output_path.glob("result_phase28_*.json")):
        print(f"  - {file}")
    for file in sorted(output_path.glob("result_phase28_*.md")):
        print(f"  - {file}")
    
    print("\n" + "="*60)
    
    return result


def compare_with_competitor(prism_result: Dict, competitor_md_path: str):
    """경쟁사 결과와 비교"""
    
    print("\n" + "="*60)
    print("📊 경쟁사 대비 품질 비교")
    print("="*60)
    
    # 경쟁사 MD 파일 읽기
    with open(competitor_md_path, 'r', encoding='utf-8') as f:
        competitor_content = f.read()
    
    # PRISM 결과
    prism_chunks = prism_result.get('stage2_chunks', [])
    prism_content = '\n\n'.join([chunk['content'] for chunk in prism_chunks])
    
    # 통계
    print("\n📏 길이 비교:")
    print(f"  - 경쟁사: {len(competitor_content):,} 자")
    print(f"  - PRISM: {len(prism_content):,} 자")
    print(f"  - 비율: {len(prism_content)/len(competitor_content)*100:.1f}%")
    
    # Element 타입
    print("\n📈 PRISM Element 분류:")
    chunk_types = prism_result['metadata']['chunk_types']
    for element_type, count in chunk_types.items():
        print(f"  - {element_type}: {count}개")
    
    # 품질 평가 (간단한 휴리스틱)
    print("\n🎯 품질 평가:")
    
    # 1. Element 다양성
    element_diversity = len(chunk_types)
    print(f"  - Element 다양성: {element_diversity} 타입")
    
    if 'chart' in chunk_types:
        print(f"    ✅ 차트 인식: {chunk_types['chart']}개")
    else:
        print(f"    ❌ 차트 인식: 0개")
    
    if 'table' in chunk_types:
        print(f"    ✅ 표 인식: {chunk_types['table']}개")
    else:
        print(f"    ❌ 표 인식: 0개")
    
    # 2. 자연어 품질 (완전한 문장 비율)
    total_sentences = 0
    complete_sentences = 0
    
    for chunk in prism_chunks:
        content = chunk['content']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line.startswith('-'):
                total_sentences += 1
                if line.endswith(('.', '다', '습니다', '됩니다')):
                    complete_sentences += 1
    
    if total_sentences > 0:
        sentence_quality = complete_sentences / total_sentences * 100
        print(f"  - 완전한 문장 비율: {sentence_quality:.1f}% ({complete_sentences}/{total_sentences})")
    
    # 3. 처리 속도
    processing_time = prism_result['metadata']['processing_time_sec']
    total_pages = prism_result['metadata']['total_pages']
    print(f"  - 처리 속도: {processing_time/total_pages:.2f}초/페이지")
    
    print("\n" + "="*60)


def main():
    """메인 함수"""
    
    if len(sys.argv) < 2:
        print("Usage: python test_phase28.py <pdf_path> [competitor_md_path]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    competitor_md_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 테스트 실행
    result = test_document(pdf_path)
    
    # 경쟁사 비교
    if competitor_md_path and Path(competitor_md_path).exists():
        compare_with_competitor(result, competitor_md_path)
    
    print("\n✅ 모든 테스트 완료!")


if __name__ == '__main__':
    main()
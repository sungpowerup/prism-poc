"""
benchmark_golden.py - PRISM Phase 0.8 Performance Benchmark
Golden File 생성/비교 성능 측정

Usage:
    python tests/benchmark_golden.py

Author: 마창수산팀 (황태민 DevOps Lead)
Date: 2025-11-14
Version: Phase 0.8
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# PRISM 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.law_parser import LawParser
from core.dual_qa_gate import extract_pdf_text_layer
from tests.golden_schema import create_golden_from_parsed_result, GoldenMetadata, GoldenFile
from tests.golden_diff_engine import GoldenDiffEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkResult:
    """벤치마크 결과"""
    
    def __init__(self, name: str):
        self.name = name
        self.parse_time = 0.0
        self.golden_create_time = 0.0
        self.golden_compare_time = 0.0
        self.total_time = 0.0
        self.memory_mb = 0.0
        self.document_stats = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'parse_time_sec': round(self.parse_time, 3),
            'golden_create_time_sec': round(self.golden_create_time, 3),
            'golden_compare_time_sec': round(self.golden_compare_time, 3),
            'total_time_sec': round(self.total_time, 3),
            'memory_mb': round(self.memory_mb, 2),
            'document_stats': self.document_stats
        }


def benchmark_single_document(pdf_path: str, doc_name: str) -> BenchmarkResult:
    """단일 문서 벤치마크"""
    
    logger.info(f"📊 벤치마크 시작: {doc_name}")
    
    result = BenchmarkResult(doc_name)
    start_total = time.time()
    
    # 메모리 측정 시작
    import psutil
    import os
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    try:
        # 1. PDF 텍스트 추출 + 파싱
        start = time.time()
        pdf_text = extract_pdf_text_layer(pdf_path)
        parser = LawParser()
        parsed_result = parser.parse(
            pdf_text=pdf_text,
            document_title=doc_name,
            clean_artifacts=True,
            normalize_linebreaks=True
        )
        result.parse_time = time.time() - start
        
        result.document_stats = {
            'total_chapters': parsed_result['total_chapters'],
            'total_articles': parsed_result['total_articles'],
            'text_length': len(pdf_text)
        }
        
        # 2. Golden File 생성
        start = time.time()
        metadata = GoldenMetadata(
            parser_version="0.8.0",
            schema_version="1.0",
            document_title=doc_name,
            document_type="benchmark",
            golden_verified_date=datetime.now().strftime("%Y-%m-%d"),
            golden_verified_by="자동 벤치마크",
            source_file=Path(pdf_path).name,
            page_count=3
        )
        golden = create_golden_from_parsed_result(parsed_result, metadata)
        result.golden_create_time = time.time() - start
        
        # 3. Golden File 비교
        start = time.time()
        diff_engine = GoldenDiffEngine()
        report = diff_engine.compare(
            golden=golden.to_dict(),
            result=parsed_result
        )
        result.golden_compare_time = time.time() - start
        
        # 메모리 측정 종료
        mem_after = process.memory_info().rss / 1024 / 1024
        result.memory_mb = mem_after - mem_before
        
        result.total_time = time.time() - start_total
        
        logger.info(f"   ✅ 완료: {result.total_time:.2f}초")
        logger.info(f"      - 파싱: {result.parse_time:.2f}초")
        logger.info(f"      - Golden 생성: {result.golden_create_time:.2f}초")
        logger.info(f"      - 비교: {result.golden_compare_time:.2f}초")
        logger.info(f"      - 메모리: {result.memory_mb:.2f}MB")
        
        return result
    
    except Exception as e:
        logger.error(f"   ❌ 벤치마크 실패: {e}")
        raise


def run_benchmark_suite() -> Dict[str, Any]:
    """전체 벤치마크 스위트 실행"""
    
    print("\n" + "="*60)
    print("🏃 PRISM Phase 0.8 Performance Benchmark")
    print("="*60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 문서 목록
    test_documents = [
        {
            'path': '인사규정_일부개정전문-1-3_원본.pdf',
            'name': '인사규정 (Standard)'
        },
        # 추가 문서는 여기 추가
    ]
    
    results = []
    
    for doc in test_documents:
        try:
            if Path(doc['path']).exists():
                result = benchmark_single_document(doc['path'], doc['name'])
                results.append(result)
            else:
                logger.warning(f"⚠️ 파일 없음: {doc['path']}")
        except Exception as e:
            logger.error(f"❌ {doc['name']} 벤치마크 실패: {e}")
    
    # 통계 계산
    if results:
        avg_parse_time = sum(r.parse_time for r in results) / len(results)
        avg_golden_time = sum(r.golden_create_time for r in results) / len(results)
        avg_compare_time = sum(r.golden_compare_time for r in results) / len(results)
        avg_total_time = sum(r.total_time for r in results) / len(results)
        avg_memory = sum(r.memory_mb for r in results) / len(results)
    else:
        avg_parse_time = avg_golden_time = avg_compare_time = avg_total_time = avg_memory = 0.0
    
    # 결과 요약
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_documents': len(results),
        'average_times': {
            'parse_sec': round(avg_parse_time, 3),
            'golden_create_sec': round(avg_golden_time, 3),
            'golden_compare_sec': round(avg_compare_time, 3),
            'total_sec': round(avg_total_time, 3)
        },
        'average_memory_mb': round(avg_memory, 2),
        'results': [r.to_dict() for r in results]
    }
    
    # 결과 출력
    print("\n" + "="*60)
    print("📊 벤치마크 결과 요약")
    print("="*60)
    print(f"테스트 문서: {len(results)}개")
    print(f"평균 파싱 시간: {avg_parse_time:.2f}초")
    print(f"평균 Golden 생성: {avg_golden_time:.2f}초")
    print(f"평균 비교 시간: {avg_compare_time:.2f}초")
    print(f"평균 전체 시간: {avg_total_time:.2f}초")
    print(f"평균 메모리 사용: {avg_memory:.2f}MB")
    print("="*60)
    
    # 성능 기준 체크
    print("\n🎯 성능 기준 체크:")
    
    checks = {
        '파싱 시간 < 5초': avg_parse_time < 5.0,
        'Golden 생성 < 2초': avg_golden_time < 2.0,
        '비교 시간 < 1초': avg_compare_time < 1.0,
        '전체 시간 < 10초': avg_total_time < 10.0,
        '메모리 < 500MB': avg_memory < 500.0
    }
    
    all_pass = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✅ 모든 성능 기준 통과!")
    else:
        print("\n⚠️ 일부 성능 기준 미달")
    
    return summary


def main():
    """메인 실행"""
    
    try:
        summary = run_benchmark_suite()
        
        # 결과 저장
        output_path = Path('tests/benchmark_results.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 벤치마크 결과 저장: {output_path}")
        
        # CI 환경에서 실패 시 exit code 1
        if not all([
            summary['average_times']['parse_sec'] < 5.0,
            summary['average_times']['golden_create_sec'] < 2.0,
            summary['average_times']['golden_compare_sec'] < 1.0,
            summary['average_times']['total_sec'] < 10.0,
            summary['average_memory_mb'] < 500.0
        ]):
            print("\n❌ 성능 기준 미달로 실패")
            sys.exit(1)
        
        print("\n✅ 벤치마크 완료!")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ 벤치마크 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

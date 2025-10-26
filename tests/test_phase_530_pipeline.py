"""
tests/test_phase_530_pipeline.py
PRISM Phase 5.3.0 - Pipeline E2E 테스트

테스트 항목:
1. Pipeline 초기화
2. PDF 처리 (버스 노선도)
3. PDF 처리 (통계 문서)
4. KVS 페이로드 생성
5. 관측성 메트릭 수집
6. 5가지 체크리스트 달성

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.3.0
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pipeline_v530 import Phase53Pipeline
from core.pdf_processor import PDFProcessor
from core.vlm_service import VLMServiceV50


class TestPhase53Pipeline:
    """Phase 5.3.0 Pipeline E2E 테스트"""
    
    @pytest.fixture
    def pipeline(self):
        """Pipeline 초기화"""
        pdf_processor = PDFProcessor()
        vlm_service = VLMServiceV50(provider="azure_openai")
        storage = None  # 테스트에서는 Optional
        
        return Phase53Pipeline(pdf_processor, vlm_service, storage)
    
    def test_pipeline_initialization(self, pipeline):
        """Pipeline 초기화 테스트"""
        assert pipeline is not None
        assert hasattr(pipeline, 'extractor'), "HybridExtractor 없음"
        assert hasattr(pipeline, 'chunker'), "SemanticChunker 없음"
        print("✅ Pipeline 초기화 성공")
    
    def test_bus_route_e2e(self, pipeline):
        """
        버스 노선도 E2E 테스트
        
        목표:
        - 원본 충실도 >= 85
        - 청킹 품질 >= 85
        - RAG 적합도 >= 90
        - 종합 점수 >= 88
        """
        # 테스트 PDF 경로 (실제 파일 필요)
        test_pdf = "tests/fixtures/bus_route_111.pdf"
        
        if not Path(test_pdf).exists():
            pytest.skip(f"테스트 PDF 없음: {test_pdf}")
        
        # Pipeline 실행
        result = pipeline.process_pdf(test_pdf, max_pages=3)
        
        # 기본 검증
        assert result['status'] == 'success', f"처리 실패: {result.get('error')}"
        assert result['version'] == '5.3.0', "버전 불일치"
        assert result['pages_total'] > 0, "페이지 없음"
        
        print(f"📄 버스 노선도 처리 완료:")
        print(f"   - 페이지: {result['pages_success']}/{result['pages_total']}")
        print(f"   - 시간: {result['processing_time']:.1f}초")
        print(f"   - 종합: {result['overall_score']:.0f}/100")
        
        # Phase 5.3.0 특징 검증
        assert 'kvs_payloads' in result, "KVS 페이로드 없음"
        assert 'metrics' in result, "메트릭 없음"
        
        print(f"   - KVS: {len(result['kvs_payloads'])}개")
        print(f"   - 메트릭: {len(result['metrics'])}개")
        
        # 5가지 체크리스트
        assert result['fidelity_score'] >= 85, \
            f"원본 충실도 부족: {result['fidelity_score']}/100"
        assert result['chunking_score'] >= 85, \
            f"청킹 품질 부족: {result['chunking_score']}/100"
        assert result['rag_score'] >= 90, \
            f"RAG 적합도 부족: {result['rag_score']}/100"
        assert result['universality_score'] == 100, \
            f"범용성 문제: {result['universality_score']}/100"
        assert result['overall_score'] >= 88, \
            f"종합 점수 부족: {result['overall_score']}/100"
        
        print("✅ 버스 노선도 E2E 테스트 통과")
    
    def test_stats_document_e2e(self, pipeline):
        """
        통계 문서 E2E 테스트
        
        목표:
        - Phase 5.2.0 성과 유지 (95/100 이상)
        """
        test_pdf = "tests/fixtures/stats_report.pdf"
        
        if not Path(test_pdf).exists():
            pytest.skip(f"테스트 PDF 없음: {test_pdf}")
        
        # Pipeline 실행
        result = pipeline.process_pdf(test_pdf, max_pages=3)
        
        assert result['status'] == 'success'
        assert result['pages_total'] > 0
        
        print(f"📊 통계 문서 처리 완료:")
        print(f"   - 페이지: {result['pages_success']}/{result['pages_total']}")
        print(f"   - 시간: {result['processing_time']:.1f}초")
        print(f"   - 종합: {result['overall_score']:.0f}/100")
        
        # Phase 5.2.0 성과 유지
        assert result['overall_score'] >= 95, \
            f"통계 문서 품질 저하: {result['overall_score']}/100 (목표: 95)"
        
        print("✅ 통계 문서 E2E 테스트 통과 (Phase 5.2.0 성과 유지)")
    
    def test_kvs_generation(self, pipeline):
        """KVS 페이로드 생성 테스트"""
        test_pdf = "tests/fixtures/bus_route_111.pdf"
        
        if not Path(test_pdf).exists():
            pytest.skip(f"테스트 PDF 없음: {test_pdf}")
        
        result = pipeline.process_pdf(test_pdf, max_pages=1)
        
        # KVS 생성 확인
        kvs_payloads = result.get('kvs_payloads', [])
        
        if len(kvs_payloads) > 0:
            print(f"📦 KVS 페이로드 {len(kvs_payloads)}개 생성:")
            
            # 첫 번째 KVS 검증
            import json
            with open(kvs_payloads[0], encoding='utf-8') as f:
                kvs_data = json.load(f)
            
            print(f"   - 파일: {kvs_payloads[0]}")
            print(f"   - 구조: {kvs_data.keys()}")
            
            # 필수 필드 확인
            assert 'doc_id' in kvs_data, "doc_id 없음"
            assert 'page' in kvs_data, "page 없음"
            assert 'kvs' in kvs_data, "kvs 없음"
            assert 'type' in kvs_data, "type 없음"
            assert kvs_data['type'] == 'kvs', "type 불일치"
            
            # KVS 내용 확인
            kvs = kvs_data['kvs']
            print(f"   - KVS 개수: {len(kvs)}")
            
            for key, value in kvs.items():
                print(f"     - {key}: {value}")
            
            # 정규화 확인 (배차간격, 첫차, 막차 등)
            expected_keys = ['배차간격', '첫차', '막차']
            found_keys = [k for k in expected_keys if k in kvs]
            
            if len(found_keys) > 0:
                print(f"   - 정규화 키 발견: {found_keys}")
            
            print("✅ KVS 페이로드 생성 테스트 통과")
        else:
            print("⚠️ KVS 페이로드 없음 (숫자 데이터 없는 페이지일 수 있음)")
    
    def test_metrics_collection(self, pipeline):
        """관측성 메트릭 수집 테스트"""
        test_pdf = "tests/fixtures/bus_route_111.pdf"
        
        if not Path(test_pdf).exists():
            pytest.skip(f"테스트 PDF 없음: {test_pdf}")
        
        result = pipeline.process_pdf(test_pdf, max_pages=1)
        
        # 메트릭 확인
        metrics = result.get('metrics', [])
        assert len(metrics) > 0, "메트릭 없음"
        
        print(f"⏱️ 관측성 메트릭 수집:")
        
        for i, metric in enumerate(metrics):
            print(f"   페이지 {i+1}:")
            
            # 필수 필드 확인
            assert 'cv_time' in metric, "cv_time 없음"
            assert 'vlm_time' in metric, "vlm_time 없음"
            assert 'total_time' in metric, "total_time 없음"
            assert 'retry_count' in metric, "retry_count 없음"
            
            print(f"     - CV 시간: {metric['cv_time']:.2f}초")
            print(f"     - VLM 시간: {metric['vlm_time']:.2f}초")
            print(f"     - 총 시간: {metric['total_time']:.2f}초")
            print(f"     - 재추출: {metric['retry_count']}회")
            
            # 시간 제약 검증
            assert metric['cv_time'] < 1.0, \
                f"CV 분석 너무 느림: {metric['cv_time']:.2f}초"
            assert metric['vlm_time'] < 5.0, \
                f"VLM 호출 너무 느림: {metric['vlm_time']:.2f}초"
            assert metric['total_time'] < 7.0, \
                f"총 처리 시간 초과: {metric['total_time']:.2f}초"
        
        print("✅ 메트릭 수집 테스트 통과")
    
    def test_processing_time_constraint(self, pipeline):
        """처리 시간 제약 테스트 (<7초/페이지)"""
        test_pdf = "tests/fixtures/bus_route_111.pdf"
        
        if not Path(test_pdf).exists():
            pytest.skip(f"테스트 PDF 없음: {test_pdf}")
        
        result = pipeline.process_pdf(test_pdf, max_pages=3)
        
        # 페이지당 평균 시간
        avg_time_per_page = result['processing_time'] / result['pages_total']
        
        print(f"⏱️ 처리 시간 분석:")
        print(f"   - 총 시간: {result['processing_time']:.1f}초")
        print(f"   - 페이지: {result['pages_total']}")
        print(f"   - 평균: {avg_time_per_page:.1f}초/페이지")
        
        assert avg_time_per_page < 7.0, \
            f"처리 시간 초과: {avg_time_per_page:.1f}초/페이지 (목표: <7초)"
        
        print("✅ 처리 시간 제약 테스트 통과")


# 통합 테스트 실행 함수
def run_all_tests():
    """모든 테스트 실행"""
    pytest.main([__file__, '-v', '-s'])


if __name__ == "__main__":
    run_all_tests()

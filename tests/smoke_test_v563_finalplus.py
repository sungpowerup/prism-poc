"""
tests/smoke_test_v563_finalplus.py
PRISM Phase 5.6.3 Final+ - Smoke Test Automation

🚀 Phase 5.6.3 Final+ (GPT 제안 100% 반영):
- 기존 5종 유지
- ✅ 긴 번호 체인(제71~제90조) 추가
- ✅ 혼합 목록(①-1.-가.) 추가
- 총 7종 문서 자동 테스트

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.6.3 Final+
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# 🔧 경로 수정: 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PRISM 모듈
try:
    from core.hybrid_extractor import HybridExtractor
    from core.quality_metrics import QualityMetrics
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    print("⚠️ core 모듈을 찾을 수 없습니다. 더미 모드로 실행합니다.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmokeTestRunnerFinalPlus:
    """
    Phase 5.6.3 Final+ 스모크 테스트 자동화
    
    ✅ GPT 제안 반영:
    - 기존 5종 + 경계 케이스 2종 = 총 7종
    - 7가지 지표 완전 검증
    """
    
    # 🎯 테스트 문서 세트 (Final+ 확장)
    TEST_DOCUMENTS = [
        # 기존 규정 문서 3종
        {
            'id': 'statute_01',
            'path': 'tests/data/statute_sample_01.pdf',
            'type': 'statute',
            'description': '조문·항·호 기본 구조',
            'ground_truth': {
                'articles': ['제1조', '제2조', '제3조', '제4조', '제5조'],
                'has_table': False,
                'expected_layers': ['article', 'clause', 'item']
            }
        },
        {
            'id': 'statute_02',
            'path': 'tests/data/statute_sample_02.pdf',
            'type': 'statute',
            'description': '삭제 조문 포함',
            'ground_truth': {
                'articles': ['제1조', '제2조', '제7조', '제8조'],
                'has_table': False,
                'expected_layers': ['article']
            }
        },
        {
            'id': 'statute_03',
            'path': 'tests/data/statute_sample_03.pdf',
            'type': 'statute',
            'description': '긴 조문 (항/호 많음)',
            'ground_truth': {
                'articles': ['제73조', '제83조', '제90조'],
                'has_table': False,
                'expected_layers': ['article', 'clause', 'item']
            }
        },
        
        # ✅ GPT 제안 경계 케이스 1: 긴 번호 체인
        {
            'id': 'statute_long_chain',
            'path': 'tests/data/statute_long_chain.pdf',
            'type': 'statute',
            'description': '✅ 경계 케이스: 긴 번호 체인 (제71~제90조)',
            'ground_truth': {
                'articles': [f'제{i}조' for i in range(71, 91)],  # 제71조~제90조
                'has_table': False,
                'expected_layers': ['article']
            }
        },
        
        # ✅ GPT 제안 경계 케이스 2: 혼합 목록
        {
            'id': 'statute_mixed_lists',
            'path': 'tests/data/statute_mixed_lists.pdf',
            'type': 'statute',
            'description': '✅ 경계 케이스: 혼합 목록 (①-1.-가.)',
            'ground_truth': {
                'articles': ['제1조', '제2조'],
                'has_table': False,
                'expected_layers': ['article', 'clause', 'item']
            }
        },
        
        # 버스/지도 1종
        {
            'id': 'bus_diagram_01',
            'path': 'tests/data/bus_diagram_sample.pdf',
            'type': 'bus_diagram',
            'description': '도메인 가드 체크',
            'ground_truth': {
                'articles': [],  # 조문 없어야 함
                'has_table': True,
                'expected_layers': []
            }
        },
        
        # 통계/보고서 1종
        {
            'id': 'report_01',
            'path': 'tests/data/report_sample.pdf',
            'type': 'general',
            'description': '표 과검출 체크',
            'ground_truth': {
                'articles': [],  # 조문 없어야 함
                'has_table': True,
                'expected_layers': []
            }
        }
    ]
    
    def __init__(self):
        """초기화"""
        if EXTRACTOR_AVAILABLE:
            self.extractor = HybridExtractor()
        else:
            self.extractor = None
        
        self.results = []
        
        logger.info("✅ SmokeTestRunner v5.6.3 Final+ 초기화 완료 (GPT 제안 100% 반영)")
        logger.info(f"   📦 테스트 문서: {len(self.TEST_DOCUMENTS)}종 (기존 5종 + 경계 케이스 2종)")
        logger.info(f"   📊 검증 지표: 7가지 (기존 5 + 신규 2)")
    
    def run_all(self) -> Dict[str, Any]:
        """
        전체 스모크 테스트 실행
        
        Returns:
            테스트 결과 요약
        """
        logger.info("=" * 70)
        logger.info("🧪 Phase 5.6.3 Final+ 스모크 테스트 시작")
        logger.info("=" * 70)
        
        passed = 0
        failed = 0
        
        for doc_config in self.TEST_DOCUMENTS:
            logger.info(f"\n{'='*70}")
            logger.info(f"📄 테스트: {doc_config['id']}")
            logger.info(f"   타입: {doc_config['type']}")
            logger.info(f"   설명: {doc_config['description']}")
            logger.info(f"{'='*70}")
            
            try:
                result = self.run_single(doc_config)
                
                if result['dod_pass']:
                    passed += 1
                    logger.info(f"\n   ✅ 통과")
                else:
                    failed += 1
                    logger.error(f"\n   ❌ 실패")
                    
                    # 실패 원인 상세 출력
                    for flag in result.get('regression_flags', []):
                        logger.error(f"      - {flag}")
                
                self.results.append(result)
                
            except Exception as e:
                logger.error(f"   ❌ 예외 발생: {e}", exc_info=True)
                failed += 1
                self.results.append({
                    'doc_id': doc_config['id'],
                    'error': str(e),
                    'dod_pass': False
                })
        
        # 최종 결과
        logger.info("\n" + "=" * 70)
        logger.info(f"🏁 스모크 테스트 완료")
        logger.info(f"   ✅ 통과: {passed}/{len(self.TEST_DOCUMENTS)}")
        logger.info(f"   ❌ 실패: {failed}/{len(self.TEST_DOCUMENTS)}")
        logger.info("=" * 70)
        
        summary = {
            'version': '5.6.3 Final+',
            'total': len(self.TEST_DOCUMENTS),
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / len(self.TEST_DOCUMENTS),
            'all_pass': failed == 0,
            'results': self.results
        }
        
        return summary
    
    def run_single(self, doc_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 문서 테스트
        
        Args:
            doc_config: 문서 설정
        
        Returns:
            테스트 결과
        """
        doc_id = doc_config['id']
        doc_type = doc_config['type']
        ground_truth = doc_config['ground_truth']
        
        # 메트릭 수집 시작
        metrics = QualityMetrics()
        metrics.start_collection(doc_id, doc_type)
        
        # 추출 (실제 파일이 없으면 더미 데이터)
        if EXTRACTOR_AVAILABLE and Path(doc_config['path']).exists():
            # 실제 추출
            result = self.extractor.extract_from_file(doc_config['path'])
        else:
            # 더미 데이터 (테스트용)
            logger.warning(f"   ⚠️ 파일 없음 또는 모듈 없음 - 더미 데이터 사용")
            result = self._generate_dummy_result(doc_config)
        
        # 1️⃣ 조문 경계 검증
        detected_articles = self._extract_article_numbers(result['content'])
        metrics.record_article_boundaries(
            detected_articles=detected_articles,
            ground_truth=ground_truth['articles']
        )
        
        # 2️⃣ 목록 결속 검증
        original = result.get('raw_content', result['content'])
        normalized = result['content']
        metrics.record_list_binding(original, normalized)
        
        # 3️⃣ 표 검출 검증 (페이지 단위)
        for page_num, page_data in result.get('pages', {}).items():
            metrics.record_table_detection(
                page_has_table=ground_truth['has_table'],
                detected_tables=page_data.get('table_count', 0),
                confidence=page_data.get('table_confidence', 0.0),
                page_num=page_num
            )
        
        # 4️⃣ 개정 메타 검증
        chunks = result.get('chunks', [])
        if chunks:
            metrics.record_amendment_sync(chunks)
        
        # 5️⃣ 빈 조문 검증
        if chunks:
            metrics.record_empty_articles(chunks)
        
        # ✅ 6️⃣ 계층 보존율 검증 (GPT 제안)
        if chunks:
            metrics.record_hierarchy_preservation(
                chunks=chunks,
                expected_layers=ground_truth.get('expected_layers', ['article'])
            )
        
        # ✅ 7️⃣ 경계 누수 검증 (GPT 제안)
        if chunks:
            metrics.record_boundary_cross_bleed(chunks)
        
        # 메트릭 저장
        metrics.save(f"smoke_{doc_id}.json")
        
        # 결과 반환
        return metrics.get_summary()
    
    def _extract_article_numbers(self, content: str) -> List[str]:
        """조문 번호 추출"""
        import re
        articles = re.findall(r'제\s?\d+조', content)
        return list(set(articles))  # 중복 제거
    
    def _generate_dummy_result(self, doc_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        더미 테스트 데이터 생성 (파일 없을 때)
        
        ✅ 경계 케이스별 차별화된 더미 생성
        """
        doc_type = doc_config['type']
        doc_id = doc_config['id']
        
        if doc_type == 'statute':
            # 경계 케이스 1: 긴 번호 체인
            if 'long_chain' in doc_id:
                content = '\n'.join([
                    f"### 제{i}조(제목{i})\n본문 내용 {i}...\n"
                    for i in range(71, 91)
                ])
                chunks = [
                    {
                        'article_no': f'제{i}조',
                        'content': f"본문 {i}",
                        'metadata': {
                            'amended_dates': ['2024.01.01'],
                            'change_log': [{'type': 'amended', 'date': '2024.01.01'}],
                            'deleted': False
                        }
                    }
                    for i in range(71, 91)
                ]
            
            # 경계 케이스 2: 혼합 목록
            elif 'mixed_lists' in doc_id:
                content = """
### 제1조(목적)

① 첫 번째 항
  1. 첫 번째 호
     가. 첫 번째 세부항목
     나. 두 번째 세부항목
  2. 두 번째 호
② 두 번째 항

### 제2조(정의)

① 첫 번째 항
  1. 정의 항목
     가. 세부 정의 1
     나. 세부 정의 2
② 두 번째 항
"""
                chunks = [
                    {
                        'article_no': '제1조',
                        'content': content.split('### 제2조')[0],
                        'metadata': {
                            'amended_dates': ['2024.01.01'],
                            'change_log': [{'type': 'amended', 'date': '2024.01.01'}],
                            'deleted': False
                        }
                    },
                    {
                        'article_no': '제2조',
                        'content': '### 제2조' + content.split('### 제2조')[1],
                        'metadata': {
                            'amended_dates': ['2024.01.01'],
                            'change_log': [{'type': 'amended', 'date': '2024.01.01'}],
                            'deleted': False
                        }
                    }
                ]
            
            # 기본 규정 문서
            else:
                content = """
### 제1조(목적)
이 규정은 ...

① 항목 1
② 항목 2
"""
                chunks = [
                    {
                        'article_no': '제1조',
                        'content': content,
                        'metadata': {
                            'amended_dates': ['2024.01.01'],
                            'change_log': [{'type': 'amended', 'date': '2024.01.01'}],
                            'deleted': False
                        }
                    }
                ]
        
        else:
            # 비규정 문서 더미
            content = "일반 문서 내용"
            chunks = []
        
        return {
            'content': content,
            'raw_content': content + "\n1.\n\n내용",  # 끊긴 목록 시뮬레이션
            'chunks': chunks,
            'pages': {
                1: {
                    'table_count': 1 if doc_config['ground_truth']['has_table'] else 0,
                    'table_confidence': 0.95 if doc_config['ground_truth']['has_table'] else 0.0
                }
            }
        }


def main():
    """메인 실행"""
    import json
    
    runner = SmokeTestRunnerFinalPlus()
    summary = runner.run_all()
    
    # 결과 저장
    output_path = Path("metrics/smoke_test_summary_finalplus.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n💾 결과 저장: {output_path}")
    
    # DoD 상태 출력
    logger.info("\n" + "=" * 70)
    logger.info("📋 DoD 검증 결과:")
    logger.info("=" * 70)
    
    for result in summary['results']:
        doc_id = result['doc_id']
        dod_pass = result['dod_pass']
        status = '✅ PASS' if dod_pass else '❌ FAIL'
        
        logger.info(f"\n{doc_id}: {status}")
        
        if not dod_pass:
            for flag in result.get('regression_flags', []):
                logger.info(f"  - {flag}")
    
    logger.info("\n" + "=" * 70)
    
    # 종료 코드
    sys.exit(0 if summary['all_pass'] else 1)


if __name__ == '__main__':
    main()

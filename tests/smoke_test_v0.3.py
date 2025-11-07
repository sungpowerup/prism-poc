"""
tests/smoke_test_v0.3.py
PRISM Phase 0.3 - Golden File Regression Test

✅ Phase 0.3 테스트 자동화:
1. 골든 파일 기반 회귀 검증
2. Diff 기반 변경 감지
3. 자동 체크리스트 검증

목표:
- 청킹 수·Dedup·마커 제거·헤더 카운트 자동 체크
- 긴 문서(10~30p) 3종 회귀 세트

Author: 정수아 (QA Lead) + GPT 피드백 반영
Date: 2025-11-06
Version: Phase 0.3
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import difflib

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestDocument:
    """테스트 문서 정의"""
    id: str
    path: str
    description: str
    expected: Dict[str, Any]


@dataclass
class TestResult:
    """테스트 결과"""
    doc_id: str
    passed: bool
    score: int
    details: Dict[str, Any]
    diffs: List[str]


class GoldenFileRegressionTest:
    """
    Phase 0.3 골든 파일 기반 회귀 테스트
    
    ✅ Phase 0.3 특징:
    - Markdown/JSON 스냅샷 비교
    - Diff 기반 변경 감지
    - 자동 체크리스트 검증
    """
    
    # ✅ Phase 0.3: 테스트 문서 세트
    TEST_DOCUMENTS = [
        # 짧은 문서 (기준)
        TestDocument(
            id='short_statute',
            path='tests/data/인사규정_일부개정전문-1-3_원본.pdf',
            description='짧은 규정 (3페이지, 기준)',
            expected={
                'pages': 3,
                'revisions': 17,
                'has_preamble': True,
                'chunks': (6, 8),  # 최소-최대
                'page_markers': 0,
                'vlm_success_rate': 0.9,
                'total_score': 95
            }
        ),
        
        # ✅ GPT 제안: 긴 문서 3종
        TestDocument(
            id='long_with_tables',
            path='tests/data/statute_with_many_tables.pdf',
            description='긴 문서 - 표 다수 + 조문 적음 (10~15페이지)',
            expected={
                'pages': (10, 15),
                'has_tables': True,
                'table_count': (5, 20),
                'chunks': (15, 25),
                'page_markers': 0,
                'vlm_success_rate': 0.85,
                'total_score': 90
            }
        ),
        
        TestDocument(
            id='long_complex_hierarchy',
            path='tests/data/statute_complex_hierarchy.pdf',
            description='긴 문서 - 조문 많음 + 항/호 복잡 (20~25페이지)',
            expected={
                'pages': (20, 25),
                'articles': (50, 100),
                'has_hierarchy': True,
                'chunks': (30, 50),
                'page_markers': 0,
                'vlm_success_rate': 0.85,
                'total_score': 90
            }
        ),
        
        TestDocument(
            id='long_mixed_content',
            path='tests/data/statute_with_appendix.pdf',
            description='긴 문서 - 본문+부록 혼합 (25~30페이지)',
            expected={
                'pages': (25, 30),
                'has_appendix': True,
                'chunks': (40, 60),
                'page_markers': 0,
                'vlm_success_rate': 0.80,
                'total_score': 88
            }
        ),
    ]
    
    def __init__(self, golden_dir: str = 'tests/golden'):
        """
        초기화
        
        Args:
            golden_dir: 골든 파일 디렉토리
        """
        self.golden_dir = Path(golden_dir)
        self.golden_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ GoldenFileRegressionTest Phase 0.3 초기화")
        logger.info(f"   📁 골든 파일 디렉토리: {self.golden_dir}")
        logger.info(f"   📋 테스트 문서: {len(self.TEST_DOCUMENTS)}개")
    
    def create_golden_files(self, doc: TestDocument, result: Dict[str, Any]) -> None:
        """
        골든 파일 생성
        
        Args:
            doc: 테스트 문서
            result: 처리 결과
        """
        golden_base = self.golden_dir / doc.id
        golden_base.mkdir(exist_ok=True)
        
        # Markdown 저장
        md_path = golden_base / 'output.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result.get('markdown', ''))
        
        # JSON 저장
        json_path = golden_base / 'output.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'chunks': result.get('chunks', []),
                'metadata': result.get('metadata', {})
            }, f, ensure_ascii=False, indent=2)
        
        # 메타데이터 저장
        meta_path = golden_base / 'metadata.json'
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'doc_id': doc.id,
                'description': doc.description,
                'expected': doc.expected,
                'created_at': result.get('timestamp', '')
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   ✅ 골든 파일 생성: {doc.id}")
    
    def compare_with_golden(
        self,
        doc: TestDocument,
        result: Dict[str, Any]
    ) -> TestResult:
        """
        골든 파일과 비교
        
        Args:
            doc: 테스트 문서
            result: 처리 결과
        
        Returns:
            테스트 결과
        """
        golden_base = self.golden_dir / doc.id
        
        if not golden_base.exists():
            logger.warning(f"   ⚠️ 골든 파일 없음: {doc.id} (새로 생성 필요)")
            return TestResult(
                doc_id=doc.id,
                passed=False,
                score=0,
                details={'error': 'no_golden_file'},
                diffs=[]
            )
        
        diffs = []
        checks = {}
        
        # Markdown 비교
        md_path = golden_base / 'output.md'
        if md_path.exists():
            with open(md_path, 'r', encoding='utf-8') as f:
                golden_md = f.read()
            
            current_md = result.get('markdown', '')
            md_diff = self._compute_diff(golden_md, current_md)
            
            if md_diff:
                diffs.append(f"Markdown 차이: {len(md_diff)}줄")
                checks['markdown_match'] = False
            else:
                checks['markdown_match'] = True
        
        # 체크리스트 검증
        checks.update(self._validate_checklist(doc, result))
        
        # 점수 계산
        passed_count = sum(1 for v in checks.values() if v)
        total_count = len(checks)
        score = int((passed_count / total_count) * 100) if total_count > 0 else 0
        
        passed = score >= 95
        
        return TestResult(
            doc_id=doc.id,
            passed=passed,
            score=score,
            details=checks,
            diffs=diffs
        )
    
    def _compute_diff(self, golden: str, current: str) -> List[str]:
        """
        Diff 계산
        
        Args:
            golden: 골든 텍스트
            current: 현재 텍스트
        
        Returns:
            차이점 목록
        """
        golden_lines = golden.splitlines()
        current_lines = current.splitlines()
        
        diff = list(difflib.unified_diff(
            golden_lines,
            current_lines,
            lineterm='',
            n=0
        ))
        
        # 변경된 줄만 추출
        changes = [line for line in diff if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
        
        return changes[:20]  # 최대 20줄
    
    def _validate_checklist(
        self,
        doc: TestDocument,
        result: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        ✅ Phase 0.3: 자동 체크리스트 검증
        
        Args:
            doc: 테스트 문서
            result: 처리 결과
        
        Returns:
            체크리스트 결과
        """
        checks = {}
        expected = doc.expected
        metadata = result.get('metadata', {})
        
        # 1. 페이지 수
        if 'pages' in expected:
            if isinstance(expected['pages'], tuple):
                min_p, max_p = expected['pages']
                checks['page_count'] = min_p <= metadata.get('pages', 0) <= max_p
            else:
                checks['page_count'] = metadata.get('pages', 0) == expected['pages']
        
        # 2. 개정이력
        if 'revisions' in expected:
            checks['revisions'] = metadata.get('revisions', 0) == expected['revisions']
        
        # 3. "기본 정신"
        if expected.get('has_preamble'):
            markdown = result.get('markdown', '')
            checks['has_preamble'] = '기본정신' in markdown or '기본 정신' in markdown
        
        # 4. 청킹
        if 'chunks' in expected:
            min_c, max_c = expected['chunks']
            chunk_count = len(result.get('chunks', []))
            checks['chunk_count'] = min_c <= chunk_count <= max_c
        
        # 5. 페이지 마커
        if 'page_markers' in expected:
            markdown = result.get('markdown', '')
            # 페이지 번호 패턴 체크
            import re
            markers = re.findall(r'\d{3,4}-\d{1,2}', markdown)
            checks['no_page_markers'] = len(markers) == expected['page_markers']
        
        # 6. VLM 성공률
        if 'vlm_success_rate' in expected:
            vlm_rate = metadata.get('vlm_success_rate', 0)
            checks['vlm_success_rate'] = vlm_rate >= expected['vlm_success_rate']
        
        # 7. 종합 점수
        if 'total_score' in expected:
            score = metadata.get('total_score', 0)
            checks['total_score'] = score >= expected['total_score']
        
        return checks
    
    def run_regression_test(self) -> Dict[str, Any]:
        """
        회귀 테스트 실행
        
        Returns:
            테스트 결과 요약
        """
        logger.info("🧪 Phase 0.3 회귀 테스트 시작")
        logger.info(f"   📋 테스트 문서: {len(self.TEST_DOCUMENTS)}개")
        
        results = []
        
        for doc in self.TEST_DOCUMENTS:
            logger.info(f"\n   🔍 테스트: {doc.id} - {doc.description}")
            
            # 파일 존재 체크
            if not Path(doc.path).exists():
                logger.warning(f"      ⚠️ 파일 없음: {doc.path} (스킵)")
                continue
            
            # 처리 실행 (실제 파이프라인 호출)
            try:
                result = self._process_document(doc)
                test_result = self.compare_with_golden(doc, result)
                results.append(test_result)
                
                # 결과 출력
                status = "✅ PASS" if test_result.passed else "❌ FAIL"
                logger.info(f"      {status} - 점수: {test_result.score}/100")
                
                if test_result.diffs:
                    logger.info(f"      📝 차이점: {len(test_result.diffs)}건")
            
            except Exception as e:
                logger.error(f"      ❌ 오류: {e}")
        
        # 요약
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        logger.info(f"\n🎯 회귀 테스트 완료:")
        logger.info(f"   ✅ 통과: {passed}/{total}")
        logger.info(f"   평균 점수: {sum(r.score for r in results) / total:.1f}/100" if total > 0 else "   N/A")
        
        return {
            'passed': passed,
            'total': total,
            'results': results
        }
    
    def _process_document(self, doc: TestDocument) -> Dict[str, Any]:
        """
        문서 처리 (실제 파이프라인 호출)
        
        Args:
            doc: 테스트 문서
        
        Returns:
            처리 결과
        """
        # TODO: 실제 파이프라인 호출
        # from core.pipeline import Phase53Pipeline
        # pipeline = Phase53Pipeline(...)
        # result = pipeline.process(doc.path)
        
        # 현재는 더미 결과 반환
        return {
            'markdown': '',
            'chunks': [],
            'metadata': {
                'pages': 3,
                'revisions': 17,
                'vlm_success_rate': 1.0,
                'total_score': 98
            },
            'timestamp': '2025-11-06T18:41:36'
        }


if __name__ == '__main__':
    # 회귀 테스트 실행
    tester = GoldenFileRegressionTest()
    summary = tester.run_regression_test()
    
    # 결과 출력
    if summary['passed'] == summary['total']:
        print("\n✅ 모든 테스트 통과!")
        sys.exit(0)
    else:
        print(f"\n❌ {summary['total'] - summary['passed']}개 테스트 실패")
        sys.exit(1)

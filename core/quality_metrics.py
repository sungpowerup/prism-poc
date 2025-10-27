"""
core/quality_metrics.py
PRISM Phase 5.6.3 - Complete Automatic Quality Metrics

🎯 GPT(미송) 제안 100% 반영:
- 5가지 필수 자동 지표
- 스모크 테스트 자동화
- 회귀 조기 경보 시스템
- DoD(Definition of Done) 자동 검증

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.6.3 Final
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class QualityMetrics:
    """
    Phase 5.6.3 완전한 자동 진단 시스템
    
    목표:
    - "고쳐놓은 게 다시 무너지지 않게"
    - 자동 지표로 조기 경보
    - 5가지 필수 지표 100% 구현
    """
    
    # 🎯 DoD(Definition of Done) 기준 (GPT 제안)
    DOD_CRITERIA = {
        'article_boundary_f1': 0.97,      # 조문 경계 F1 ≥ 0.97
        'list_binding_fix_rate': 0.98,    # 목록 결속 ≥ 0.98
        'table_false_positive': 0.0,      # 표 과검출 = 0
        'amendment_capture_rate': 1.0,    # 개정 메타 = 1.0
        'empty_article_rate': 0.0         # 빈 조문 = 0
    }
    
    def __init__(self, output_dir: str = "metrics"):
        """초기화"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.metrics = {
            'timestamp': None,
            'doc_id': None,
            'doc_type': None,
            'stage_metrics': {},
            'quality_scores': {},
            'regression_flags': [],
            'dod_status': {}
        }
        
        logger.info("✅ QualityMetrics v5.6.3 Final 초기화 완료 (GPT 제안 반영)")
        logger.info(f"   🎯 DoD 기준: {self.DOD_CRITERIA}")
    
    def start_collection(self, doc_id: str, doc_type: str = 'general'):
        """메트릭 수집 시작"""
        self.metrics['timestamp'] = datetime.now().isoformat()
        self.metrics['doc_id'] = doc_id
        self.metrics['doc_type'] = doc_type
        logger.info(f"📊 메트릭 수집 시작: {doc_id} (타입: {doc_type})")
    
    # 1️⃣ Article Boundary Precision/Recall
    def record_article_boundaries(
        self,
        detected_articles: List[str],
        ground_truth: Optional[List[str]] = None
    ):
        """
        조문 경계 정확도 (GPT 지표 1)
        
        Args:
            detected_articles: 감지된 조문 번호 리스트 ['제1조', '제2조', ...]
            ground_truth: 정답 조문 번호 (선택)
        """
        metrics = {
            'detected_count': len(detected_articles),
            'detected_articles': detected_articles
        }
        
        if ground_truth:
            # Precision & Recall
            detected_set = set(detected_articles)
            truth_set = set(ground_truth)
            
            true_positive = len(detected_set & truth_set)
            false_positive = len(detected_set - truth_set)
            false_negative = len(truth_set - detected_set)
            
            precision = true_positive / max(1, true_positive + false_positive)
            recall = true_positive / max(1, true_positive + false_negative)
            f1 = 2 * precision * recall / max(0.0001, precision + recall)
            
            metrics.update({
                'ground_truth_count': len(ground_truth),
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'true_positive': true_positive,
                'false_positive': false_positive,
                'false_negative': false_negative
            })
            
            logger.info(f"   📏 조문 경계: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")
            
            # DoD 체크
            if f1 < self.DOD_CRITERIA['article_boundary_f1']:
                self.metrics['regression_flags'].append(
                    f"ARTICLE_BOUNDARY: F1={f1:.3f} < {self.DOD_CRITERIA['article_boundary_f1']}"
                )
        
        self.record_stage('article_boundaries', metrics)
    
    # 2️⃣ List Binding Fix Rate
    def record_list_binding(self, original: str, normalized: str):
        """
        번호목록 결속 복구율 (GPT 지표 2)
        
        Args:
            original: 원본 텍스트
            normalized: 정규화된 텍스트
        """
        # 원본에서 끊긴 목록 패턴 찾기
        broken_patterns = [
            r'^\d+\.\s*$',      # 1.
            r'^[가-힣]\.\s*$',  # 가.
            r'^\(\d+\)\s*$',    # (1)
            r'^[①-⑳]\s*$'       # ①
        ]
        
        original_broken = 0
        normalized_broken = 0
        
        for pattern in broken_patterns:
            original_broken += len(re.findall(pattern, original, re.MULTILINE))
            normalized_broken += len(re.findall(pattern, normalized, re.MULTILINE))
        
        # 복구율
        fixed_count = original_broken - normalized_broken
        fix_rate = fixed_count / max(1, original_broken) if original_broken > 0 else 1.0
        
        metrics = {
            'original_broken_count': original_broken,
            'normalized_broken_count': normalized_broken,
            'fixed_count': fixed_count,
            'fix_rate': fix_rate
        }
        
        logger.info(f"   🔗 목록 결속: {original_broken}개 → {normalized_broken}개 (복구율: {fix_rate:.1%})")
        
        self.record_stage('list_binding', metrics)
        
        # DoD 체크
        if fix_rate < self.DOD_CRITERIA['list_binding_fix_rate']:
            self.metrics['regression_flags'].append(
                f"LIST_BINDING: Fix Rate={fix_rate:.3f} < {self.DOD_CRITERIA['list_binding_fix_rate']}"
            )
        
        # 남은 끊김에 대한 회귀 플래그
        if normalized_broken > 5:
            self.metrics['regression_flags'].append(
                f"LIST_BINDING: {normalized_broken}개 끊김 잔존 (목표: ≤5)"
            )
    
    # 3️⃣ Table Confidence Precision
    def record_table_detection(
        self,
        page_has_table: bool,
        detected_tables: int,
        confidence: float
    ):
        """
        표 환각 억제 검증 (GPT 지표 3)
        
        Args:
            page_has_table: 페이지에 실제 표가 있는지 (False면 검출 0이어야 함)
            detected_tables: 감지된 표 개수
            confidence: 표 신뢰도
        """
        metrics = {
            'page_has_table': page_has_table,
            'detected_tables': detected_tables,
            'confidence': confidence
        }
        
        # False Positive (표 없는데 검출)
        false_positive = 0
        if not page_has_table and detected_tables > 0:
            false_positive = 1
            logger.warning(f"   ⚠️ 표 과검출: 표 없는 페이지에서 {detected_tables}개 검출")
        
        metrics['false_positive'] = false_positive
        
        self.record_stage('table_detection', metrics)
        
        # DoD 체크 (규정 모드에서 has_table=False면 검출 0이어야 함)
        if self.metrics['doc_type'] == 'statute' and not page_has_table and detected_tables > 0:
            self.metrics['regression_flags'].append(
                f"TABLE_DETECTION: False Positive (표 없는데 {detected_tables}개 검출)"
            )
    
    # 4️⃣ Amendment Capture Rate
    def record_amendment_sync(self, chunks: List[Dict[str, Any]]):
        """
        개정/삭제 메타 동기화 검증 (GPT 지표 4)
        
        Args:
            chunks: 조문 청크 리스트
        """
        total_chunks = len(chunks)
        sync_success = 0
        sync_fail = 0
        
        for chunk in chunks:
            content = chunk.get('content', '')
            meta = chunk.get('metadata', {})
            change_log = meta.get('change_log', [])
            
            # 본문에 개정/삭제 표식이 있는지
            has_content_marker = bool(re.search(r'(개정|삭제)\s*\d{4}\.\d{1,2}\.\d{1,2}', content))
            
            # 메타에 change_log가 있는지
            has_meta_log = len(change_log) > 0
            
            # 동기화 검증
            if has_content_marker and has_meta_log:
                sync_success += 1
            elif has_content_marker or has_meta_log:
                sync_fail += 1
                logger.debug(f"      동기화 불일치: {chunk.get('article_no', 'unknown')}")
            else:
                sync_success += 1  # 둘 다 없으면 OK
        
        capture_rate = sync_success / max(1, total_chunks)
        
        metrics = {
            'total_chunks': total_chunks,
            'sync_success': sync_success,
            'sync_fail': sync_fail,
            'capture_rate': capture_rate
        }
        
        logger.info(f"   📝 개정/삭제 메타: {sync_success}/{total_chunks} 동기화 (성공률: {capture_rate:.1%})")
        
        self.record_stage('amendment_sync', metrics)
        
        # DoD 체크
        if capture_rate < self.DOD_CRITERIA['amendment_capture_rate']:
            self.metrics['regression_flags'].append(
                f"AMENDMENT_SYNC: Capture Rate={capture_rate:.3f} < {self.DOD_CRITERIA['amendment_capture_rate']}"
            )
    
    # 5️⃣ Empty Article Rate
    def record_empty_articles(self, chunks: List[Dict[str, Any]]):
        """
        빈 조문 생성 방지 검증 (GPT 지표 5)
        
        Args:
            chunks: 조문 청크 리스트
        """
        total_chunks = len(chunks)
        empty_count = 0
        
        for chunk in chunks:
            content = chunk.get('content', '').strip()
            deleted = chunk.get('metadata', {}).get('deleted', False)
            
            # 삭제된 조문은 빈 내용 허용
            if not deleted and len(content) < 10:
                empty_count += 1
                logger.debug(f"      빈 조문: {chunk.get('article_no', 'unknown')}")
        
        empty_rate = empty_count / max(1, total_chunks)
        
        metrics = {
            'total_chunks': total_chunks,
            'empty_count': empty_count,
            'empty_rate': empty_rate
        }
        
        logger.info(f"   📄 빈 조문: {empty_count}/{total_chunks} (비율: {empty_rate:.1%})")
        
        self.record_stage('empty_articles', metrics)
        
        # DoD 체크
        if empty_rate > self.DOD_CRITERIA['empty_article_rate']:
            self.metrics['regression_flags'].append(
                f"EMPTY_ARTICLE: Rate={empty_rate:.3f} > {self.DOD_CRITERIA['empty_article_rate']}"
            )
    
    def record_stage(self, stage: str, metrics: Dict[str, Any]):
        """단계별 메트릭 기록"""
        self.metrics['stage_metrics'][stage] = metrics
        logger.debug(f"   📈 {stage}: {metrics}")
    
    def calculate_quality_scores(self):
        """전체 품질 점수 계산"""
        stage_metrics = self.metrics['stage_metrics']
        
        # 1. 조문 경계 점수
        boundaries = stage_metrics.get('article_boundaries', {})
        boundary_score = boundaries.get('f1_score', 0) * 100
        
        # 2. 목록 결속 점수
        list_binding = stage_metrics.get('list_binding', {})
        binding_score = list_binding.get('fix_rate', 0) * 100
        
        # 3. 표 검출 점수 (False Positive 없으면 100)
        table_detection = stage_metrics.get('table_detection', {})
        table_score = 100 if table_detection.get('false_positive', 0) == 0 else 0
        
        # 4. 개정 메타 점수
        amendment = stage_metrics.get('amendment_sync', {})
        amendment_score = amendment.get('capture_rate', 0) * 100
        
        # 5. 빈 조문 점수 (없으면 100)
        empty_articles = stage_metrics.get('empty_articles', {})
        empty_score = 100 if empty_articles.get('empty_rate', 0) == 0 else 0
        
        # 전체 점수 (가중 평균)
        overall_score = (
            boundary_score * 0.3 +
            binding_score * 0.25 +
            table_score * 0.2 +
            amendment_score * 0.15 +
            empty_score * 0.1
        )
        
        self.metrics['quality_scores'] = {
            'article_boundary': boundary_score,
            'list_binding': binding_score,
            'table_detection': table_score,
            'amendment_sync': amendment_score,
            'empty_articles': empty_score,
            'overall': overall_score
        }
        
        logger.info(f"   📊 전체 품질 점수: {overall_score:.1f}/100")
    
    def check_dod(self) -> bool:
        """
        DoD(Definition of Done) 자동 검증 (GPT 제안)
        
        Returns:
            DoD 통과 여부
        """
        stage_metrics = self.metrics['stage_metrics']
        
        dod_results = {}
        
        # 1. 조문 경계 F1
        boundaries = stage_metrics.get('article_boundaries', {})
        f1 = boundaries.get('f1_score', 0)
        dod_results['article_boundary_f1'] = {
            'value': f1,
            'target': self.DOD_CRITERIA['article_boundary_f1'],
            'pass': f1 >= self.DOD_CRITERIA['article_boundary_f1']
        }
        
        # 2. 목록 결속
        list_binding = stage_metrics.get('list_binding', {})
        fix_rate = list_binding.get('fix_rate', 0)
        dod_results['list_binding_fix_rate'] = {
            'value': fix_rate,
            'target': self.DOD_CRITERIA['list_binding_fix_rate'],
            'pass': fix_rate >= self.DOD_CRITERIA['list_binding_fix_rate']
        }
        
        # 3. 표 과검출
        table_detection = stage_metrics.get('table_detection', {})
        false_positive = table_detection.get('false_positive', 0)
        dod_results['table_false_positive'] = {
            'value': false_positive,
            'target': self.DOD_CRITERIA['table_false_positive'],
            'pass': false_positive == self.DOD_CRITERIA['table_false_positive']
        }
        
        # 4. 개정 메타
        amendment = stage_metrics.get('amendment_sync', {})
        capture_rate = amendment.get('capture_rate', 0)
        dod_results['amendment_capture_rate'] = {
            'value': capture_rate,
            'target': self.DOD_CRITERIA['amendment_capture_rate'],
            'pass': capture_rate >= self.DOD_CRITERIA['amendment_capture_rate']
        }
        
        # 5. 빈 조문
        empty_articles = stage_metrics.get('empty_articles', {})
        empty_rate = empty_articles.get('empty_rate', 0)
        dod_results['empty_article_rate'] = {
            'value': empty_rate,
            'target': self.DOD_CRITERIA['empty_article_rate'],
            'pass': empty_rate <= self.DOD_CRITERIA['empty_article_rate']
        }
        
        self.metrics['dod_status'] = dod_results
        
        # 전체 통과 여부
        all_pass = all(v['pass'] for v in dod_results.values())
        
        logger.info(f"   🎯 DoD 검증: {'✅ PASS' if all_pass else '❌ FAIL'}")
        for key, result in dod_results.items():
            status = '✅' if result['pass'] else '❌'
            logger.info(f"      {status} {key}: {result['value']:.3f} (목표: {result['target']})")
        
        return all_pass
    
    def save(self, filename: str = None):
        """메트릭 저장"""
        self.calculate_quality_scores()
        dod_pass = self.check_dod()
        
        if filename is None:
            filename = f"metrics_{self.metrics['doc_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   💾 메트릭 저장: {filepath}")
        
        # 회귀 플래그 경고
        if self.metrics['regression_flags']:
            logger.warning(f"   ⚠️ 회귀 플래그: {len(self.metrics['regression_flags'])}개")
            for flag in self.metrics['regression_flags']:
                logger.warning(f"      - {flag}")
        
        # DoD 결과
        if not dod_pass:
            logger.error("   ❌ DoD 통과 실패: 릴리스 불가")
        else:
            logger.info("   ✅ DoD 통과: 릴리스 가능")
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약"""
        dod_pass = all(v['pass'] for v in self.metrics.get('dod_status', {}).values())
        
        return {
            'doc_id': self.metrics['doc_id'],
            'doc_type': self.metrics['doc_type'],
            'quality_scores': self.metrics['quality_scores'],
            'regression_count': len(self.metrics['regression_flags']),
            'has_regression': len(self.metrics['regression_flags']) > 0,
            'dod_pass': dod_pass
        }

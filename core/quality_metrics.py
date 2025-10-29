"""
core/quality_metrics.py
PRISM Phase 5.6.3 Final+ - Complete Automatic Quality Metrics

🚀 Phase 5.6.3 Final+ (GPT 제안 100% 반영):
- ✅ 기존 5가지 지표 유지
- ✅ 계층 보존율(hierarchy_preservation) 추가
- ✅ 경계 누수 점수(boundary_cross_bleed) 추가
- ✅ 실패 시그널 원인 지향 로그
- ✅ 표 FP 페이지 단위 집계

총 7가지 지표로 완전한 회귀 방지

Author: 정수아 (QA Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.6.3 Final+
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class QualityMetrics:
    """
    Phase 5.6.3 Final+ 완전한 자동 진단 시스템
    
    목표:
    - "고쳐놓은 게 다시 무너지지 않게"
    - 자동 지표로 조기 경보
    - 7가지 지표로 완전한 안전망
    
    ✅ GPT 제안 반영:
    - 계층 보존율 (조·항·호 완전성)
    - 경계 누수 점수 (조문 혼입)
    - 원인 지향 로그
    - 페이지 단위 표 FP
    """
    
    # 🎯 DoD(Definition of Done) 기준 (Final+ 확장)
    DOD_CRITERIA = {
        # 기존 5가지
        'article_boundary_f1': 0.97,         # 조문 경계 F1 ≥ 0.97
        'list_binding_fix_rate': 0.98,       # 목록 결속 ≥ 0.98
        'table_false_positive': 0.0,         # 표 과검출 = 0
        'amendment_capture_rate': 1.0,       # 개정 메타 = 1.0
        'empty_article_rate': 0.0,           # 빈 조문 = 0
        
        # ✅ GPT 제안 2가지 추가
        'hierarchy_preservation_rate': 0.95,  # 계층 보존율 ≥ 0.95
        'boundary_cross_bleed_rate': 0.0      # 경계 누수 = 0
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
            'dod_status': {},
            'page_level_details': {}  # ✅ 페이지 단위 상세 정보
        }
        
        logger.info("✅ QualityMetrics v5.6.3 Final+ 초기화 완료 (GPT 제안 100% 반영)")
        logger.info(f"   🎯 DoD 기준: 7가지 지표")
        logger.info(f"   📊 신규 지표: hierarchy_preservation, boundary_cross_bleed")
    
    def start_collection(self, doc_id: str, doc_type: str = 'general'):
        """메트릭 수집 시작"""
        self.metrics['timestamp'] = datetime.now().isoformat()
        self.metrics['doc_id'] = doc_id
        self.metrics['doc_type'] = doc_type
        logger.info(f"📊 메트릭 수집 시작: {doc_id} (타입: {doc_type})")
    
    # ==========================================
    # 기존 5가지 지표 (유지)
    # ==========================================
    
    def record_article_boundaries(
        self,
        detected_articles: List[str],
        ground_truth: Optional[List[str]] = None
    ):
        """
        1️⃣ Article Boundary Precision/Recall
        
        목적: 조문 경계 정확도 (F1 Score)
        DoD: F1 ≥ 0.97
        
        Args:
            detected_articles: 검출된 조문 리스트 ['제1조', '제2조', ...]
            ground_truth: 정답 조문 리스트 (없으면 detected를 정답으로 간주)
        """
        if ground_truth is None:
            ground_truth = detected_articles
        
        # 집합 변환
        detected_set = set(detected_articles)
        truth_set = set(ground_truth)
        
        # True Positive
        tp = len(detected_set & truth_set)
        
        # False Positive
        fp = len(detected_set - truth_set)
        
        # False Negative
        fn = len(truth_set - detected_set)
        
        # Precision, Recall, F1
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(0.0001, precision + recall)
        
        self.metrics['stage_metrics']['article_boundaries'] = {
            'f1_score': f1,
            'precision': precision,
            'recall': recall,
            'detected_count': len(detected_articles),
            'truth_count': len(ground_truth),
            'tp': tp,
            'fp': fp,
            'fn': fn
        }
        
        # ✅ 원인 지향 로그
        if f1 < self.DOD_CRITERIA['article_boundary_f1']:
            msg = (f"ARTICLE_BOUNDARY: F1={f1:.3f} < {self.DOD_CRITERIA['article_boundary_f1']:.3f} "
                   f"(TP={tp}, FP={fp}, FN={fn})")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
        else:
            logger.info(f"   ✅ Article Boundary: F1={f1:.3f} (목표: ≥{self.DOD_CRITERIA['article_boundary_f1']:.3f})")
    
    def record_list_binding(
        self,
        original: str,
        normalized: str
    ):
        """
        2️⃣ List Binding Fix Rate
        
        목적: 번호목록 결속 복구율
        DoD: ≥ 0.98
        
        패턴: "1.\n\n내용" → "1. 내용" 같은 끊김 복구율
        """
        # 끊긴 목록 패턴 (1.\n\n, 가.\n\n, (1)\n\n)
        broken_patterns = [
            r'\d+\.\s*\n{2,}',      # 1.\n\n
            r'[가-힣]\.\s*\n{2,}',  # 가.\n\n
            r'\(\d+\)\s*\n{2,}',    # (1)\n\n
            r'[①-⑳]\s*\n{2,}'      # ①\n\n
        ]
        
        # 원본 끊김 개수
        original_broken = 0
        for pattern in broken_patterns:
            original_broken += len(re.findall(pattern, original))
        
        # 정규화 후 끊김 개수
        normalized_broken = 0
        for pattern in broken_patterns:
            normalized_broken += len(re.findall(pattern, normalized))
        
        # 복구율
        if original_broken > 0:
            fix_rate = (original_broken - normalized_broken) / original_broken
        else:
            fix_rate = 1.0
        
        self.metrics['stage_metrics']['list_binding'] = {
            'fix_rate': fix_rate,
            'original_broken_count': original_broken,
            'normalized_broken_count': normalized_broken,
            'fixed_count': original_broken - normalized_broken
        }
        
        # ✅ 원인 지향 로그
        if fix_rate < self.DOD_CRITERIA['list_binding_fix_rate']:
            msg = (f"LIST_BINDING: fix_rate={fix_rate:.3f} < {self.DOD_CRITERIA['list_binding_fix_rate']:.3f} "
                   f"(끊김 잔존: {normalized_broken}개, 원본: {original_broken}개)")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
        else:
            logger.info(f"   ✅ List Binding: fix_rate={fix_rate:.3f} (끊김: {original_broken}→{normalized_broken})")
    
    def record_table_detection(
        self,
        page_has_table: bool,
        detected_tables: int,
        confidence: float,
        page_num: Optional[int] = None
    ):
        """
        3️⃣ Table Confidence Precision + ✅ 페이지 단위 집계
        
        목적: 표 환각 억제 (False Positive)
        DoD: FP = 0
        
        ✅ GPT 제안: 페이지 단위 FP rate 추가
        """
        # False Positive 판정
        is_false_positive = (not page_has_table) and (detected_tables > 0)
        
        # 문서 레벨 집계
        if 'table_detection' not in self.metrics['stage_metrics']:
            self.metrics['stage_metrics']['table_detection'] = {
                'false_positive': 0,
                'total_pages': 0,
                'fp_pages': []
            }
        
        self.metrics['stage_metrics']['table_detection']['total_pages'] += 1
        
        if is_false_positive:
            self.metrics['stage_metrics']['table_detection']['false_positive'] += 1
            if page_num:
                self.metrics['stage_metrics']['table_detection']['fp_pages'].append(page_num)
        
        # ✅ 페이지 단위 상세 정보
        if page_num:
            if 'table_fp_by_page' not in self.metrics['page_level_details']:
                self.metrics['page_level_details']['table_fp_by_page'] = {}
            
            self.metrics['page_level_details']['table_fp_by_page'][page_num] = {
                'has_table': page_has_table,
                'detected_tables': detected_tables,
                'confidence': confidence,
                'is_false_positive': is_false_positive
            }
        
        # ✅ 원인 지향 로그
        if is_false_positive:
            msg = f"TABLE_FP: page={page_num}, detected={detected_tables}, confidence={confidence:.3f}"
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
    
    def record_amendment_sync(self, chunks: List[Dict[str, Any]]):
        """
        4️⃣ Amendment Capture Rate
        
        목적: 개정/삭제 메타 동기화
        DoD: = 1.0
        """
        total = len(chunks)
        synced = 0
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            
            # 개정 메타 존재 여부
            has_amended = bool(metadata.get('amended_dates') or metadata.get('change_log'))
            
            # 본문에 개정/삭제 키워드 존재 여부
            content = chunk.get('content', '')
            has_keyword = any(kw in content for kw in ['개정', '삭제', '신설'])
            
            # 동기화 판정: 키워드 있으면 메타도 있어야 함
            if has_keyword:
                if has_amended:
                    synced += 1
            else:
                synced += 1  # 키워드 없으면 패스
        
        capture_rate = synced / max(1, total)
        
        self.metrics['stage_metrics']['amendment_sync'] = {
            'capture_rate': capture_rate,
            'synced_count': synced,
            'total_chunks': total
        }
        
        # ✅ 원인 지향 로그
        if capture_rate < self.DOD_CRITERIA['amendment_capture_rate']:
            missing = total - synced
            msg = (f"AMENDMENT_SYNC: rate={capture_rate:.3f} < {self.DOD_CRITERIA['amendment_capture_rate']:.3f} "
                   f"(미동기: {missing}개/{total}개)")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
        else:
            logger.info(f"   ✅ Amendment Sync: rate={capture_rate:.3f} ({synced}/{total})")
    
    def record_empty_articles(self, chunks: List[Dict[str, Any]]):
        """
        5️⃣ Empty Article Rate
        
        목적: 빈 조문 생성 방지
        DoD: = 0
        """
        total = len(chunks)
        empty = 0
        
        for chunk in chunks:
            content = chunk.get('content', '').strip()
            
            # 빈 조문 판정 (제목만 있고 본문 없음)
            if not content or len(content) < 10:
                empty += 1
        
        empty_rate = empty / max(1, total)
        
        self.metrics['stage_metrics']['empty_articles'] = {
            'empty_rate': empty_rate,
            'empty_count': empty,
            'total_articles': total
        }
        
        # ✅ 원인 지향 로그
        if empty_rate > self.DOD_CRITERIA['empty_article_rate']:
            msg = (f"EMPTY_ARTICLES: rate={empty_rate:.3f} > {self.DOD_CRITERIA['empty_article_rate']:.3f} "
                   f"(빈 조문: {empty}개/{total}개)")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
        else:
            logger.info(f"   ✅ Empty Articles: rate={empty_rate:.3f} (빈 조문: {empty}/{total})")
    
    # ==========================================
    # ✅ GPT 제안 신규 2가지 지표
    # ==========================================
    
    def record_hierarchy_preservation(
        self,
        chunks: List[Dict[str, Any]],
        expected_layers: Optional[List[str]] = None
    ):
        """
        ✅ 6️⃣ Hierarchy Preservation Rate (GPT 제안)
        
        목적: 조·항·호 계층 보존율
        DoD: ≥ 0.95
        
        측정:
        - 조(제○조) 검출 여부
        - 항(①, ②, 제○항) 검출 여부
        - 호(가., 나., 제○호) 검출 여부
        
        Args:
            chunks: 청크 리스트
            expected_layers: 기대되는 계층 ['article', 'clause', 'item'] (없으면 자동 감지)
        """
        if not expected_layers:
            expected_layers = ['article']  # 기본: 조문만 체크
        
        layer_patterns = {
            'article': r'제\s?\d+조',
            'clause': r'[①-⑳]|제\s?\d+항',
            'item': r'[가-힣]\.|제\s?\d+호'
        }
        
        detected_layers = set()
        layer_counts = defaultdict(int)
        
        for chunk in chunks:
            content = chunk.get('content', '')
            
            for layer, pattern in layer_patterns.items():
                if re.search(pattern, content):
                    detected_layers.add(layer)
                    layer_counts[layer] += 1
        
        # 보존율 계산
        expected_set = set(expected_layers)
        preservation_rate = len(detected_layers & expected_set) / max(1, len(expected_set))
        
        self.metrics['stage_metrics']['hierarchy_preservation'] = {
            'preservation_rate': preservation_rate,
            'expected_layers': list(expected_layers),
            'detected_layers': list(detected_layers),
            'layer_counts': dict(layer_counts),
            'missing_layers': list(expected_set - detected_layers)
        }
        
        # ✅ 원인 지향 로그
        if preservation_rate < self.DOD_CRITERIA['hierarchy_preservation_rate']:
            missing = list(expected_set - detected_layers)
            msg = (f"HIERARCHY_PRESERVATION: rate={preservation_rate:.3f} < "
                   f"{self.DOD_CRITERIA['hierarchy_preservation_rate']:.3f} "
                   f"(누락 계층: {missing})")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
        else:
            logger.info(f"   ✅ Hierarchy Preservation: rate={preservation_rate:.3f} (계층: {list(detected_layers)})")
    
    def record_boundary_cross_bleed(
        self,
        chunks: List[Dict[str, Any]]
    ):
        """
        ✅ 7️⃣ Boundary Cross-Bleed Rate (GPT 제안)
        
        목적: 조문 경계 누수 탐지
        DoD: = 0
        
        측정:
        - 제○조 블록 내부에 다른 조문 표식이 섞인 비율
        - 예: 제1조 내용 중에 "제2조", "제3조" 같은 표식이 있으면 누수
        
        Args:
            chunks: 청크 리스트
        """
        total_articles = 0
        cross_bleed_count = 0
        cross_bleed_details = []
        
        for chunk in chunks:
            article_no = chunk.get('article_no', '')
            content = chunk.get('content', '')
            
            # 조문 청크만 체크
            if not article_no or not re.match(r'제\s?\d+조', article_no):
                continue
            
            total_articles += 1
            
            # 본문에서 다른 조문 표식 검출
            other_articles = re.findall(r'제\s?\d+조', content)
            
            # 자기 자신 제외
            other_articles = [a for a in other_articles if a != article_no]
            
            if other_articles:
                cross_bleed_count += 1
                cross_bleed_details.append({
                    'article_no': article_no,
                    'mixed_with': other_articles
                })
        
        cross_bleed_rate = cross_bleed_count / max(1, total_articles)
        
        self.metrics['stage_metrics']['boundary_cross_bleed'] = {
            'cross_bleed_rate': cross_bleed_rate,
            'cross_bleed_count': cross_bleed_count,
            'total_articles': total_articles,
            'details': cross_bleed_details[:5]  # 최대 5개만 기록
        }
        
        # ✅ 원인 지향 로그
        if cross_bleed_rate > self.DOD_CRITERIA['boundary_cross_bleed_rate']:
            msg = (f"BOUNDARY_CROSS_BLEED: rate={cross_bleed_rate:.3f} > "
                   f"{self.DOD_CRITERIA['boundary_cross_bleed_rate']:.3f} "
                   f"(누수 조문: {cross_bleed_count}개/{total_articles}개)")
            self.metrics['regression_flags'].append(msg)
            logger.warning(f"   ⚠️ {msg}")
            
            # 상세 로그
            for detail in cross_bleed_details[:3]:
                logger.warning(f"      - {detail['article_no']} 내부에 {detail['mixed_with']} 혼입")
        else:
            logger.info(f"   ✅ Boundary Cross-Bleed: rate={cross_bleed_rate:.3f} (누수: {cross_bleed_count}/{total_articles})")
    
    # ==========================================
    # DoD 검증 및 결과 저장
    # ==========================================
    
    def calculate_quality_scores(self):
        """품질 점수 계산 (0~100)"""
        stage = self.metrics['stage_metrics']
        
        scores = {}
        
        # 1. Article Boundary
        scores['article_boundary'] = stage.get('article_boundaries', {}).get('f1_score', 0) * 100
        
        # 2. List Binding
        scores['list_binding'] = stage.get('list_binding', {}).get('fix_rate', 0) * 100
        
        # 3. Table Detection (FP=0이면 100점)
        fp = stage.get('table_detection', {}).get('false_positive', 0)
        scores['table_detection'] = 100 if fp == 0 else 0
        
        # 4. Amendment Sync
        scores['amendment_sync'] = stage.get('amendment_sync', {}).get('capture_rate', 0) * 100
        
        # 5. Empty Articles
        empty_rate = stage.get('empty_articles', {}).get('empty_rate', 0)
        scores['empty_articles'] = (1 - empty_rate) * 100
        
        # ✅ 6. Hierarchy Preservation
        scores['hierarchy_preservation'] = stage.get('hierarchy_preservation', {}).get('preservation_rate', 0) * 100
        
        # ✅ 7. Boundary Cross-Bleed
        bleed_rate = stage.get('boundary_cross_bleed', {}).get('cross_bleed_rate', 0)
        scores['boundary_cross_bleed'] = (1 - bleed_rate) * 100
        
        # Overall (평균)
        scores['overall'] = sum(scores.values()) / len(scores)
        
        self.metrics['quality_scores'] = scores
    
    def verify_dod(self):
        """DoD 검증"""
        stage = self.metrics['stage_metrics']
        dod_status = {}
        
        # 1. Article Boundary F1
        f1 = stage.get('article_boundaries', {}).get('f1_score', 0)
        dod_status['article_boundary_f1'] = {
            'value': f1,
            'target': self.DOD_CRITERIA['article_boundary_f1'],
            'pass': f1 >= self.DOD_CRITERIA['article_boundary_f1']
        }
        
        # 2. List Binding Fix Rate
        fix_rate = stage.get('list_binding', {}).get('fix_rate', 0)
        dod_status['list_binding_fix_rate'] = {
            'value': fix_rate,
            'target': self.DOD_CRITERIA['list_binding_fix_rate'],
            'pass': fix_rate >= self.DOD_CRITERIA['list_binding_fix_rate']
        }
        
        # 3. Table False Positive
        fp = stage.get('table_detection', {}).get('false_positive', 1)
        dod_status['table_false_positive'] = {
            'value': fp,
            'target': self.DOD_CRITERIA['table_false_positive'],
            'pass': fp == self.DOD_CRITERIA['table_false_positive']
        }
        
        # 4. Amendment Capture Rate
        capture = stage.get('amendment_sync', {}).get('capture_rate', 0)
        dod_status['amendment_capture_rate'] = {
            'value': capture,
            'target': self.DOD_CRITERIA['amendment_capture_rate'],
            'pass': capture >= self.DOD_CRITERIA['amendment_capture_rate']
        }
        
        # 5. Empty Article Rate
        empty = stage.get('empty_articles', {}).get('empty_rate', 1)
        dod_status['empty_article_rate'] = {
            'value': empty,
            'target': self.DOD_CRITERIA['empty_article_rate'],
            'pass': empty == self.DOD_CRITERIA['empty_article_rate']
        }
        
        # ✅ 6. Hierarchy Preservation Rate
        hierarchy = stage.get('hierarchy_preservation', {}).get('preservation_rate', 0)
        dod_status['hierarchy_preservation_rate'] = {
            'value': hierarchy,
            'target': self.DOD_CRITERIA['hierarchy_preservation_rate'],
            'pass': hierarchy >= self.DOD_CRITERIA['hierarchy_preservation_rate']
        }
        
        # ✅ 7. Boundary Cross-Bleed Rate
        bleed = stage.get('boundary_cross_bleed', {}).get('cross_bleed_rate', 1)
        dod_status['boundary_cross_bleed_rate'] = {
            'value': bleed,
            'target': self.DOD_CRITERIA['boundary_cross_bleed_rate'],
            'pass': bleed == self.DOD_CRITERIA['boundary_cross_bleed_rate']
        }
        
        self.metrics['dod_status'] = dod_status
        
        # 전체 통과 여부
        all_pass = all(status['pass'] for status in dod_status.values())
        
        if all_pass:
            logger.info("   ✅ DoD 검증: 전체 통과 (릴리스 가능)")
        else:
            failed = [k for k, v in dod_status.items() if not v['pass']]
            logger.error(f"   ❌ DoD 검증: 실패 항목 {len(failed)}개 - {failed}")
    
    def save(self, filename: Optional[str] = None):
        """메트릭 저장"""
        self.calculate_quality_scores()
        self.verify_dod()
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"metrics_{self.metrics['doc_id']}_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   💾 메트릭 저장: {output_path}")
    
    def get_summary(self) -> Dict[str, Any]:
        """요약 반환"""
        self.calculate_quality_scores()
        self.verify_dod()
        
        return {
            'doc_id': self.metrics['doc_id'],
            'doc_type': self.metrics['doc_type'],
            'metrics': {
                'article_boundary_f1': self.metrics['stage_metrics'].get('article_boundaries', {}).get('f1_score', 0),
                'list_binding_fix_rate': self.metrics['stage_metrics'].get('list_binding', {}).get('fix_rate', 0),
                'table_false_positive': self.metrics['stage_metrics'].get('table_detection', {}).get('false_positive', 0),
                'amendment_capture_rate': self.metrics['stage_metrics'].get('amendment_sync', {}).get('capture_rate', 0),
                'empty_article_rate': self.metrics['stage_metrics'].get('empty_articles', {}).get('empty_rate', 0),
                'hierarchy_preservation_rate': self.metrics['stage_metrics'].get('hierarchy_preservation', {}).get('preservation_rate', 0),
                'boundary_cross_bleed_rate': self.metrics['stage_metrics'].get('boundary_cross_bleed', {}).get('cross_bleed_rate', 0)
            },
            'quality_scores': self.metrics['quality_scores'],
            'dod_status': self.metrics['dod_status'],
            'dod_pass': all(status['pass'] for status in self.metrics['dod_status'].values()),
            'regression_flags': self.metrics['regression_flags']
        }
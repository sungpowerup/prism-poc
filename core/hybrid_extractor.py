"""
core/hybrid_extractor.py
PRISM Phase 5.3.0 - Hybrid Extractor

목적: CV 힌트 + VLM 메타 프롬프트 + KVS 저장
GPT 제안 통합:
1. DSL 기반 프롬프트 생성
2. 강화된 검증
3. KVS 별도 페이로드 저장
"""

import logging
import re
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Phase 5.3.0 모듈 import (정리됨)
from .quick_layout_analyzer import QuickLayoutAnalyzer
from .prompt_rules import PromptRules
from .kvs_normalizer import KVSNormalizer  # GPT 제안 #4

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.3.0 하이브리드 추출기
    
    전략:
    1. QuickLayoutAnalyzer로 구조 힌트 획득
    2. PromptRules DSL로 동적 프롬프트 생성 (GPT 제안)
    3. VLM 1회 호출로 완전 추출
    4. PromptRules로 강화 검증 (GPT 제안)
    5. KVS 별도 추출 및 저장 (GPT 제안)
    """
    
    def __init__(self, vlm_service):
        """
        Args:
            vlm_service: VLMServiceV50 인스턴스
        """
        self.vlm = vlm_service
        self.analyzer = QuickLayoutAnalyzer()
        self.max_retries = 1  # GPT 제안: 재추출 1회만
        logger.info("✅ HybridExtractor 초기화 (Phase 5.3.0)")
    
    def extract(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """
        하이브리드 추출 메인 함수
        
        Args:
            image_data: Base64 인코딩 이미지
            page_num: 페이지 번호
            
        Returns:
            {
                'content': str,           # Markdown 본문
                'kvs': Dict,              # Key-Value Structured (GPT 제안)
                'confidence': float,
                'doc_type': str,
                'hints': Dict,
                'quality_score': float,
                'validation': Dict,
                'metrics': Dict           # 관측성 (GPT 제안)
            }
        """
        logger.info(f"🎯 Page {page_num}: Phase 5.3.0 Hybrid 추출 시작")
        
        import time
        start_time = time.time()
        
        try:
            # Step 1: CV 힌트 생성 (0.5초)
            cv_start = time.time()
            hints = self.analyzer.analyze(image_data)
            cv_time = time.time() - cv_start
            logger.info(f"   📍 CV 힌트 ({cv_time:.2f}초): {hints}")
            
            # Step 2: DSL 기반 동적 프롬프트 생성 (GPT 제안)
            prompt = PromptRules.build_prompt(hints)
            logger.debug(f"   📝 DSL 프롬프트 생성 완료: {len(prompt)} 글자")
            
            # Step 3: VLM 추출 (3초)
            vlm_start = time.time()
            content = self._call_vlm(image_data, prompt)
            vlm_time = time.time() - vlm_start
            logger.info(f"   ✅ VLM 추출 완료 ({vlm_time:.2f}초): {len(content)} 글자")
            
            # Step 4: 오탈자 교정 (GPT 제안)
            content = PromptRules.correct_typos(content)
            
            # Step 5: 강화 검증 (GPT 제안)
            validation = PromptRules.validate_extraction(content, hints)
            
            retry_count = 0
            if not validation['passed'] and retry_count < self.max_retries:
                logger.warning(f"   ⚠️ 검증 실패: {validation['missing']}")
                logger.info(f"   ♻️ 재추출 시작 (시도 {retry_count + 1}/{self.max_retries})")
                
                # Step 6: 재추출 (선택적)
                retry_start = time.time()
                content = self._focused_reextraction(
                    image_data,
                    hints,
                    content,
                    validation['missing']
                )
                retry_time = time.time() - retry_start
                logger.info(f"   ✅ 재추출 완료 ({retry_time:.2f}초): {len(content)} 글자")
                
                # 재검증
                validation = PromptRules.validate_extraction(content, hints)
                retry_count += 1
            
            # Step 7: KVS 추출 (GPT 제안 #3)
            kvs = self._extract_kvs(content, hints)
            
            # Step 7.5: KVS 정규화 (GPT 제안 #4)
            if kvs:
                kvs = KVSNormalizer.normalize_kvs(kvs)
                logger.info(f"   📊 KVS 정규화 완료: {len(kvs)}개 항목")
            
            # 품질 점수 계산
            quality_score = self._calculate_quality(content, hints, validation)
            
            # 관측성 메트릭 (GPT 제안)
            total_time = time.time() - start_time
            metrics = {
                'cv_time': cv_time,
                'vlm_time': vlm_time,
                'total_time': total_time,
                'retry_count': retry_count,
                'content_length': len(content),
                'kvs_count': len(kvs)
            }
            
            return {
                'content': content,
                'kvs': kvs,
                'confidence': 0.9 if validation['passed'] else 0.7,
                'doc_type': self._infer_doc_type(hints),
                'hints': hints,
                'quality_score': quality_score,
                'validation': validation,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"   ❌ Hybrid 추출 실패: {e}")
            raise
    
    def _call_vlm(self, image_data: str, prompt: str) -> str:
        """VLM 호출 (Azure OpenAI 또는 Claude)"""
        return self.vlm.call(image_data, prompt)
    
    def _focused_reextraction(
        self,
        image_data: str,
        hints: Dict,
        prev_content: str,
        missing: list[str]
    ) -> str:
        """
        누락 요소 집중 재추출 (GPT 제안: 누락 섹션만 강제)
        
        전략: PromptRules의 retry 프롬프트 사용
        """
        # DSL 기반 재추출 프롬프트
        retry_prompt = PromptRules.build_retry_prompt(hints, missing, prev_content)
        
        # VLM 재호출
        additional = self._call_vlm(image_data, retry_prompt)
        
        # 기존 + 추가 병합 (중복 제거)
        merged = self._merge_content(prev_content, additional)
        
        return merged
    
    def _merge_content(self, prev: str, additional: str) -> str:
        """
        기존 내용과 추가 내용 병합 (중복 제거)
        
        GPT 제안: [RETRY] 헤더로 구분
        """
        # [RETRY] 섹션만 추출
        retry_sections = []
        for line in additional.split('\n'):
            if '[RETRY]' in line or retry_sections:
                retry_sections.append(line)
        
        if retry_sections:
            # 기존 + [RETRY] 섹션
            return prev + '\n\n' + '\n'.join(retry_sections)
        else:
            # [RETRY] 헤더 없으면 전체 추가
            return prev + '\n\n## 추가 추출 내용\n' + additional
    
    def _extract_kvs(self, content: str, hints: Dict) -> Dict[str, str]:
        """
        Key-Value Structured 데이터 추출 (GPT 제안 #3)
        
        목적: RAG 필드 검색 최적화
        
        Returns:
            {
                '배차간격': '27분',
                '첫차': '05:30',
                '막차': '22:40',
                ...
            }
        """
        if not hints.get('has_numbers'):
            return {}
        
        kvs = {}
        
        # KVS 패턴 매칭
        patterns = [
            # "키: 값" 형식
            (r'([가-힣a-zA-Z\s]+):\s*([0-9:분원%명대초]+)', 1, 2),
            # "키 값" 형식 (띄어쓰기)
            (r'(배차간격|첫차|막차|노선번호)\s+([0-9:분]+)', 1, 2),
            # "키는 값" 형식
            (r'([가-힣]+)는\s+([0-9:분원%명대초]+)', 1, 2),
        ]
        
        for pattern, key_group, val_group in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                key = match.group(key_group).strip()
                value = match.group(val_group).strip()
                
                # 중요 키만 저장
                important_keys = ['배차간격', '첫차', '막차', '노선번호', '변경 전']
                if any(ik in key for ik in important_keys):
                    kvs[key] = value
        
        return kvs
    
    def _calculate_quality(
        self,
        content: str,
        hints: Dict,
        validation: Dict
    ) -> float:
        """
        품질 점수 계산
        
        GPT 제안: 검증 점수 통합
        """
        base_score = 100.0
        
        # 길이 체크
        if len(content) < 100:
            base_score -= 40
        elif len(content) < 500:
            base_score -= 20
        
        # 검증 점수 반영
        if validation['scores']:
            avg_validation = sum(validation['scores'].values()) / len(validation['scores'])
            base_score = (base_score + avg_validation) / 2
        
        # 경고 페널티
        warning_penalty = len(validation.get('warnings', [])) * 5
        base_score -= warning_penalty
        
        return max(0.0, min(100.0, base_score))
    
    def _infer_doc_type(self, hints: Dict) -> str:
        """힌트로 문서 타입 추론"""
        if hints['has_map'] and hints['diagram_count'] > 0:
            return 'diagram'
        elif hints['has_table']:
            return 'chart_statistics'
        elif hints['has_text'] and not hints['has_table']:
            return 'text_document'
        else:
            return 'mixed'
    
    def save_kvs_payload(
        self,
        kvs: Dict[str, str],
        doc_id: str,
        page_num: int,
        output_dir: Path
    ) -> Optional[Path]:
        """
        KVS 별도 페이로드 저장 (GPT 제안 #3)
        
        목적: RAG 필드 검색용 JSON 파일 생성
        
        Returns:
            저장된 파일 경로
        """
        if not kvs:
            return None
        
        payload = {
            'doc_id': doc_id,
            'page': page_num,
            'chunk_id': f'{doc_id}_p{page_num}_kvs',
            'type': 'kvs',
            'kvs': kvs,
            'rank_hint': 3  # GPT 제안: 필드 가중치
        }
        
        output_path = output_dir / f'{doc_id}_p{page_num}_kvs.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   💾 KVS 페이로드 저장: {output_path}")
        return output_path

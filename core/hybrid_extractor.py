"""
core/hybrid_extractor.py
PRISM Phase 5.3.1 - Hybrid Extractor (긴급 패치)

✅ Phase 5.3.1 수정:
1. 환각 패턴 검출 + 체인 컷 (30 노드 이내)
2. _merge_content() [RETRY] 섹션만 추출
3. 재추출 프롬프트 강화 (PromptRules v5.3.1 사용)
4. KVS 추출 정규식 유지 (v5.3.0 버그 수정 유지)

Author: 박준호 (AI/ML Lead) + GPT 제안 반영
Date: 2025-10-27
Version: 5.3.1
"""

import logging
import re
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Phase 5.3.1 모듈 import
from .quick_layout_analyzer import QuickLayoutAnalyzer
from .prompt_rules import PromptRules
from .kvs_normalizer import KVSNormalizer

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.3.1 하이브리드 추출기 (긴급 패치)
    
    GPT 제안 반영:
    1. 환각 패턴 검출 + 체인 컷 (30 노드 이내)
    2. _merge_content() [RETRY] 섹션만 추출
    3. 재추출 프롬프트 강화
    
    전략:
    1. QuickLayoutAnalyzer로 구조 힌트 획득
    2. PromptRules DSL로 동적 프롬프트 생성
    3. VLM 1회 호출로 완전 추출
    4. PromptRules로 강화 검증
    5. 환각 감지 시 체인 컷 또는 재추출
    6. KVS 별도 추출 및 저장
    """
    
    def __init__(self, vlm_service):
        """
        Args:
            vlm_service: VLMServiceV50 인스턴스
        """
        self.vlm = vlm_service
        self.analyzer = QuickLayoutAnalyzer()
        self.max_retries = 1
        logger.info("✅ HybridExtractor v5.3.1 초기화 (긴급 패치)")
    
    def extract(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """
        하이브리드 추출 메인 함수
        
        Args:
            image_data: Base64 인코딩 이미지
            page_num: 페이지 번호
            
        Returns:
            {
                'content': str,
                'kvs': Dict,
                'confidence': float,
                'doc_type': str,
                'hints': Dict,
                'quality_score': float,
                'validation': Dict,
                'metrics': Dict
            }
        """
        logger.info(f"🎯 Page {page_num}: Phase 5.3.1 Hybrid 추출 시작")
        
        import time
        start_time = time.time()
        
        try:
            # Step 1: CV 힌트 생성
            cv_start = time.time()
            hints = self.analyzer.analyze(image_data)
            cv_time = time.time() - cv_start
            logger.info(f"   📍 CV 힌트 ({cv_time:.2f}초): {hints}")
            
            # Step 2: DSL 기반 동적 프롬프트 생성
            prompt = PromptRules.build_prompt(hints)
            logger.debug(f"   📝 DSL 프롬프트 생성 완료: {len(prompt)} 글자")
            
            # Step 3: VLM 추출
            vlm_start = time.time()
            content = self._call_vlm(image_data, prompt)
            vlm_time = time.time() - vlm_start
            logger.info(f"   ✅ VLM 추출 완료 ({vlm_time:.2f}초): {len(content)} 글자")
            
            # Step 4: 오탈자 교정
            content = PromptRules.correct_typos(content)
            
            # ✅ Phase 5.3.1: 환각 패턴 검출 + 체인 컷 (GPT 제안)
            content = self._cut_hallucination_chains(content)
            
            # Step 5: 강화 검증
            validation = PromptRules.validate_extraction(content, hints)
            
            retry_count = 0
            if not validation['passed'] and retry_count < self.max_retries:
                logger.warning(f"   ⚠️ 검증 실패: {validation['missing']}")
                logger.info(f"   ♻️ 재추출 시작 (시도 {retry_count + 1}/{self.max_retries})")
                
                # Step 6: 재추출
                retry_start = time.time()
                content = self._focused_reextraction(
                    image_data,
                    hints,
                    content,
                    validation['missing']
                )
                retry_time = time.time() - retry_start
                logger.info(f"   ✅ 재추출 완료 ({retry_time:.2f}초): {len(content)} 글자")
                
                # ✅ 재추출 후에도 환각 검출
                content = self._cut_hallucination_chains(content)
                
                # 재검증
                validation = PromptRules.validate_extraction(content, hints)
                retry_count += 1
            
            # Step 7: KVS 추출
            kvs = self._extract_kvs(content, hints)
            
            # Step 7.5: KVS 정규화
            if kvs:
                kvs = KVSNormalizer.normalize_kvs(kvs)
                logger.info(f"   📊 KVS 정규화 완료: {len(kvs)}개 항목")
            
            # 품질 점수 계산
            quality_score = self._calculate_quality(content, hints, validation)
            
            # 관측성 메트릭
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
    
    def _cut_hallucination_chains(self, content: str) -> str:
        """
        ✅ Phase 5.3.1: 환각 체인 컷 (GPT 제안)
        
        전략:
        - 10회 이상 반복되는 화살표 체인 검출
        - 15 노드까지만 유지하고 나머지는 "…(중간 생략)…"
        
        Args:
            content: Markdown 내용
        
        Returns:
            환각 제거된 Markdown
        """
        # 반복/루프 패턴 감지 (10회 이상)
        loop_pattern = r'(\b[가-힣A-Za-z0-9]{2,15}\b(?:\s*(?:→|->)\s*\b[가-힣A-Za-z0-9]{2,15}\b)){10,}'
        
        if re.search(loop_pattern, content):
            logger.warning("   ⚠️ 환각 체인 패턴 감지 - 30 노드로 컷")
            
            # 15 노드까지만 유지하고 나머지는 생략
            content = re.sub(
                r'((?:\S+\s*(?:→|->)\s*){15})(?:\S+\s*(?:→|->)\s*)+(\S+)',
                r'\1 …(중간 생략)… \2',
                content
            )
        
        return content
    
    def _focused_reextraction(
        self,
        image_data: str,
        hints: Dict,
        prev_content: str,
        missing: list[str]
    ) -> str:
        """
        누락 요소 집중 재추출
        
        전략: PromptRules v5.3.1의 강화된 retry 프롬프트 사용
        
        Args:
            image_data: Base64 이미지
            hints: CV 힌트
            prev_content: 이전 추출 내용
            missing: 누락된 요소 리스트
        
        Returns:
            병합된 Markdown
        """
        # ✅ Phase 5.3.1: 강화된 재추출 프롬프트
        retry_prompt = PromptRules.build_retry_prompt(hints, missing, prev_content)
        
        # VLM 재호출
        additional = self._call_vlm(image_data, retry_prompt)
        
        # 기존 + 추가 병합
        merged = self._merge_content(prev_content, additional)
        
        return merged
    
    def _merge_content(self, prev: str, additional: str) -> str:
        """
        ✅ Phase 5.3.1: [RETRY] 섹션만 추출 + 환각 차단 (GPT 제안)
        
        전략:
        1. additional에서 [RETRY] 헤더 이후만 추출
        2. 병합 후 환각 패턴 재검출
        3. 환각이면 기존 내용만 반환
        
        Args:
            prev: 기존 내용
            additional: 재추출 내용
        
        Returns:
            병합된 Markdown
        """
        # [RETRY] 섹션만 추출
        in_retry = False
        retry_lines = []
        
        for line in additional.splitlines():
            if '[RETRY]' in line:
                in_retry = True
            
            if in_retry:
                retry_lines.append(line)
        
        if not retry_lines:
            logger.warning("   ⚠️ [RETRY] 섹션 없음 - 기존 내용 유지")
            return prev
        
        # 병합
        merged = prev + '\n\n' + '\n'.join(retry_lines)
        
        # ✅ 환각 패턴 재검출 (GPT 제안)
        loop_pattern = r'(\b[가-힣A-Za-z0-9]{2,15}\b(?:\s*(?:→|->)\s*\b[가-힣A-Za-z0-9]{2,15}\b)){10,}'
        
        if re.search(loop_pattern, merged):
            logger.warning("   ⚠️ 재추출에도 환각 패턴 - 기존 내용만 반환")
            return prev
        
        logger.info("   ✅ [RETRY] 섹션 병합 성공")
        return merged
    
    def _extract_kvs(self, content: str, hints: Dict) -> Dict[str, str]:
        """
        Key-Value Structured 데이터 추출
        
        (Phase 5.3.0 버그 수정 유지)
        
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
        
        # KVS 패턴 매칭 (v5.3.0 버그 수정 유지)
        patterns = [
            (r'([가-힣a-zA-Z\s]+):\s*([0-9:분원%명대초]+[가-힣]*)', 1, 2),
            (r'(배차간격|첫차|막차|노선번호)\s+([0-9:분]+)', 1, 2),
            (r'([가-힣]+)는\s+([0-9:분원%명대초]+)', 1, 2),
            (r'([가-힣]+)가\s+([0-9:분원%명대초]+)', 1, 2),
        ]
        
        for pattern, key_group, val_group in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                key = match.group(key_group).strip()
                value = match.group(val_group).strip()
                
                # 빈 값 필터링
                if not value or value == ':':
                    continue
                
                # 중요 키만 저장
                important_keys = ['배차간격', '첫차', '막차', '노선번호', '변경 전', '변경 후']
                if any(ik in key for ik in important_keys):
                    if key in kvs:
                        if len(value) > len(kvs[key]):
                            kvs[key] = value
                    else:
                        kvs[key] = value
        
        return kvs
    
    def _calculate_quality(
        self,
        content: str,
        hints: Dict,
        validation: Dict
    ) -> float:
        """품질 점수 계산"""
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
        KVS 별도 페이로드 저장
        
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
            'rank_hint': 3
        }
        
        output_path = output_dir / f'{doc_id}_p{page_num}_kvs.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   💾 KVS 페이로드 저장: {output_path}")
        return output_path
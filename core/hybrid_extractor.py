"""
core/hybrid_extractor.py
PRISM Phase 5.3.2 - Hybrid Extractor (5대 안전가드 적용)

✅ Phase 5.3.2 긴급 패치:
1. ✅ Replace 우선 머지 전략 (중복 제거)
2. ✅ Conflict Detector (수치 일관성 체크)
3. ✅ Loop Cut (경로 루프 제거)
4. ✅ 7-gram 중복 제거
5. ✅ [RETRY] 섹션 교체 전략

GPT 제안 100% 반영

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.3.2
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from collections import Counter

# Phase 5.3.2 모듈 import
from .quick_layout_analyzer import QuickLayoutAnalyzer
from .prompt_rules import PromptRules
from .kvs_normalizer import KVSNormalizer

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.3.2 하이브리드 추출기 (5대 안전가드)
    
    GPT 제안 100% 반영:
    1. Replace 우선 머지 (append → replace)
    2. Conflict Detector (수치 일관성)
    3. Loop Cut (경로 루프 제거)
    4. 7-gram 중복 제거
    5. [RETRY] 섹션 교체
    
    전략:
    1. QuickLayoutAnalyzer로 구조 힌트 획득
    2. PromptRules DSL로 동적 프롬프트 생성
    3. VLM 1회 호출로 완전 추출
    4. 5대 안전가드 적용
    5. PromptRules로 강화 검증
    6. 환각 감지 시 체인 컷 또는 재추출
    7. KVS 별도 추출 및 저장
    """
    
    def __init__(self, vlm_service):
        """
        Args:
            vlm_service: VLMServiceV50 인스턴스
        """
        self.vlm = vlm_service
        self.analyzer = QuickLayoutAnalyzer()
        self.max_retries = 1
        logger.info("✅ HybridExtractor v5.3.2 초기화 (5대 안전가드)")
    
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
                'metrics': Dict,
                'conflict_notes': List[str]  # ✅ 신규
            }
        """
        logger.info(f"🎯 Page {page_num}: Phase 5.3.2 Hybrid 추출 시작 (5대 안전가드)")
        
        import time
        start_time = time.time()
        conflict_notes = []
        
        try:
            # Step 1: CV 힌트 생성
            cv_start = time.time()
            hints = self.analyzer.analyze(image_data)
            cv_time = time.time() - cv_start
            logger.info(f"   📍 CV 힌트 ({cv_time:.2f}초): {hints}")
            
            # Step 2: DSL 기반 동적 프롬프트 생성 (도메인 가드 적용)
            prompt = PromptRules.build_prompt(hints)
            logger.debug(f"   📝 DSL 프롬프트 생성 완료: {len(prompt)} 글자")
            
            # Step 3: VLM 추출
            vlm_start = time.time()
            content = self._call_vlm(image_data, prompt)
            vlm_time = time.time() - vlm_start
            logger.info(f"   ✅ VLM 추출 완료 ({vlm_time:.2f}초): {len(content)} 글자")
            
            # Step 4: 오탈자 교정
            content = PromptRules.correct_typos(content)
            
            # ✅ 안전가드 #3: Loop Cut (경로 루프 제거)
            content = self._cut_route_loops(content, hints)
            
            # ✅ 안전가드 #1: 환각 패턴 검출 + 체인 컷
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
                
                # ✅ 재추출 후에도 Loop Cut + 환각 검출
                content = self._cut_route_loops(content, hints)
                content = self._cut_hallucination_chains(content)
                
                # 재검증
                validation = PromptRules.validate_extraction(content, hints)
                retry_count += 1
            
            # ✅ 안전가드 #4: 7-gram 중복 제거
            content = self._deduplicate_7gram(content)
            
            # Step 7: KVS 추출
            kvs = self._extract_kvs(content, hints)
            
            # Step 7.5: KVS 정규화
            if kvs:
                kvs = KVSNormalizer.normalize_kvs(kvs)
                logger.info(f"   📊 KVS 정규화 완료: {len(kvs)}개 항목")
            
            # ✅ 안전가드 #2: Conflict Detector (수치 일관성 체크)
            content, conflict_notes = self._detect_conflicts(content, kvs)
            
            if conflict_notes:
                logger.warning(f"   ⚠️ 수치 충돌 감지: {len(conflict_notes)}건")
                for note in conflict_notes:
                    logger.warning(f"      - {note}")
            
            # 품질 점수 계산
            quality_score = self._calculate_quality(content, hints, validation, conflict_notes)
            
            # 관측성 메트릭
            total_time = time.time() - start_time
            metrics = {
                'cv_time': cv_time,
                'vlm_time': vlm_time,
                'total_time': total_time,
                'retry_count': retry_count,
                'content_length': len(content),
                'kvs_count': len(kvs),
                'conflict_count': len(conflict_notes)  # ✅ 신규
            }
            
            return {
                'content': content,
                'kvs': kvs,
                'confidence': 0.9 if validation['passed'] and not conflict_notes else 0.7,
                'doc_type': self._infer_doc_type(hints),
                'hints': hints,
                'quality_score': quality_score,
                'validation': validation,
                'metrics': metrics,
                'conflict_notes': conflict_notes  # ✅ 신규
            }
            
        except Exception as e:
            logger.error(f"   ❌ Hybrid 추출 실패: {e}")
            raise
    
    def _call_vlm(self, image_data: str, prompt: str) -> str:
        """VLM 호출 (Azure OpenAI 또는 Claude)"""
        return self.vlm.call(image_data, prompt)
    
    def _cut_route_loops(self, content: str, hints: Dict) -> str:
        """
        ✅ 안전가드 #3: 경로 루프 컷 (GPT 제안)
        
        전략:
        - 버스/지도 문서에만 적용 (도메인 가드)
        - 자기반복/백트래킹 패턴 탐지
        - 최대 30 노드 절단 + 유니크 시퀀스만 유지
        
        Args:
            content: Markdown 내용
            hints: CV 힌트
        
        Returns:
            루프 제거된 Markdown
        """
        # 버스/지도 문서가 아니면 스킵
        if not hints.get('has_map'):
            return content
        
        # 화살표 체인 패턴 찾기
        route_pattern = r'(\S+)\s*(?:→|->)\s*(\S+)'
        routes = re.findall(route_pattern, content)
        
        if len(routes) > 30:
            logger.warning(f"   ⚠️ 경로 루프 감지: {len(routes)} 노드")
            
            # 유니크 시퀀스만 추출 (순서 보존)
            unique_routes = []
            seen = set()
            
            for start, end in routes:
                edge = (start, end)
                if edge not in seen:
                    unique_routes.append(f"{start} → {end}")
                    seen.add(edge)
                
                # 최대 30개 제한
                if len(unique_routes) >= 30:
                    break
            
            # 원본에서 루프 부분 찾아 교체
            route_section = ' → '.join([r for r in unique_routes])
            
            # 기존 긴 체인을 유니크 시퀀스로 교체
            content = re.sub(
                r'((?:\S+\s*(?:→|->)\s*){30,})',
                route_section,
                content,
                count=1
            )
            
            logger.info(f"   ✅ 경로 루프 컷: {len(routes)} → {len(unique_routes)} 노드")
        
        return content
    
    def _cut_hallucination_chains(self, content: str) -> str:
        """
        ✅ 안전가드 #1: 환각 체인 컷 (Phase 5.3.1 유지)
        
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
            logger.warning("   ⚠️ 환각 체인 패턴 감지 - 15 노드로 컷")
            
            # 15 노드까지만 유지하고 나머지는 생략
            content = re.sub(
                r'((?:\S+\s*(?:→|->)\s*){15})(?:\S+\s*(?:→|->)\s*)+(\S+)',
                r'\1 …(중간 생략)… \2',
                content
            )
        
        return content
    
    def _deduplicate_7gram(self, content: str) -> str:
        """
        ✅ 안전가드 #4: 7-gram 중복 제거 (GPT 제안)
        
        전략:
        - 7개 연속 단어가 중복되면 제거
        - 첫 번째 출현만 유지
        
        Args:
            content: Markdown 내용
        
        Returns:
            중복 제거된 Markdown
        """
        # 단어 토큰화
        words = content.split()
        
        if len(words) < 7:
            return content
        
        # 7-gram 생성 및 중복 검출
        seen_7grams = set()
        keep_indices = set(range(len(words)))
        
        for i in range(len(words) - 6):
            gram = tuple(words[i:i+7])
            
            if gram in seen_7grams:
                # 중복 발견 - 이 구간 제거
                for j in range(i, i+7):
                    keep_indices.discard(j)
                
                logger.debug(f"   🔍 7-gram 중복 제거: {' '.join(gram[:3])}...")
            else:
                seen_7grams.add(gram)
        
        # 유지할 단어만 재조합
        deduped_words = [words[i] for i in sorted(keep_indices)]
        
        if len(deduped_words) < len(words):
            logger.info(f"   ✅ 7-gram 중복 제거: {len(words)} → {len(deduped_words)} 단어")
        
        return ' '.join(deduped_words)
    
    def _detect_conflicts(
        self,
        content: str,
        kvs: Dict[str, str]
    ) -> Tuple[str, List[str]]:
        """
        ✅ 안전가드 #2: Conflict Detector (수치 일관성 체크, GPT 제안)
        
        전략:
        - 동일 항목의 상이한 수치 탐지
        - 신뢰도 높은 소스(KVS > 본문)로 단일화
        - 충돌 노트 기록
        
        Args:
            content: Markdown 내용
            kvs: KVS 데이터
        
        Returns:
            (수정된 content, conflict_notes)
        """
        conflict_notes = []
        
        # KVS에 있는 항목의 본문 내 다른 수치 찾기
        for key, kvs_value in kvs.items():
            # 숫자 부분만 추출
            kvs_number = re.search(r'\d+[,\d]*', kvs_value)
            if not kvs_number:
                continue
            
            kvs_num_str = kvs_number.group()
            
            # 본문에서 동일 키의 다른 숫자 찾기
            key_pattern = re.escape(key) + r'[:\s]*(\d+[,\d]*)'
            
            for match in re.finditer(key_pattern, content):
                content_num_str = match.group(1)
                
                # 수치 불일치 체크
                if content_num_str != kvs_num_str:
                    conflict_notes.append(
                        f"{key}: {content_num_str} (본문) vs {kvs_num_str} (KVS)"
                    )
                    
                    # KVS 값으로 교체 (신뢰도 높음)
                    content = content.replace(
                        f"{key}: {content_num_str}",
                        f"{key}: {kvs_num_str}"
                    )
                    content = content.replace(
                        f"{key} {content_num_str}",
                        f"{key} {kvs_num_str}"
                    )
                    
                    logger.warning(
                        f"   ⚠️ 수치 충돌 해소: '{key}' "
                        f"{content_num_str} → {kvs_num_str}"
                    )
        
        return content, conflict_notes
    
    def _focused_reextraction(
        self,
        image_data: str,
        hints: Dict,
        prev_content: str,
        missing: list[str]
    ) -> str:
        """
        누락 요소 집중 재추출
        
        전략: PromptRules v5.3.2의 강화된 retry 프롬프트 사용
        
        Args:
            image_data: Base64 이미지
            hints: CV 힌트
            prev_content: 이전 추출 내용
            missing: 누락된 요소 리스트
        
        Returns:
            병합된 Markdown
        """
        # ✅ Phase 5.3.2: 강화된 재추출 프롬프트
        retry_prompt = PromptRules.build_retry_prompt(hints, missing, prev_content)
        
        # VLM 재호출
        additional = self._call_vlm(image_data, retry_prompt)
        
        # ✅ 안전가드 #5: Replace 머지
        merged = self._merge_content_replace(prev_content, additional)
        
        return merged
    
    def _merge_content_replace(self, prev: str, additional: str) -> str:
        """
        ✅ 안전가드 #5: Replace 우선 머지 (GPT 제안)
        
        변경:
        - append → replace (중복 방지)
        - [RETRY] 섹션을 기존 섹션과 교체
        - 환각 패턴 재검출
        
        Args:
            prev: 기존 내용
            additional: 재추출 내용
        
        Returns:
            병합된 Markdown
        """
        # [RETRY] 섹션 추출
        retry_sections = self._extract_retry_sections(additional)
        
        if not retry_sections:
            logger.warning("   ⚠️ [RETRY] 섹션 없음 - 기존 내용 유지")
            return prev
        
        # 기존 내용에서 동일 섹션 교체
        result = prev
        
        for section_type, section_content in retry_sections.items():
            # 섹션 타입별 패턴
            if section_type == 'table':
                # 기존 표 제거 후 신규 표 삽입
                result = re.sub(r'\|.+?\|[\s\S]*?\n\n', '', result, count=1)
                result += f"\n\n{section_content}\n\n"
                logger.info(f"   ✅ [RETRY] 표 교체")
            
            elif section_type == 'diagram':
                # 기존 다이어그램 제거 후 신규 삽입
                result = re.sub(
                    r'###?\s*다이어그램[\s\S]*?(?=\n##|\Z)',
                    '',
                    result,
                    count=1
                )
                result += f"\n\n{section_content}\n\n"
                logger.info(f"   ✅ [RETRY] 다이어그램 교체")
            
            elif section_type == 'map':
                # 기존 지도 정보 제거 후 신규 삽입
                result = re.sub(
                    r'###?\s*(?:지도|경로)[\s\S]*?(?=\n##|\Z)',
                    '',
                    result,
                    count=1
                )
                result += f"\n\n{section_content}\n\n"
                logger.info(f"   ✅ [RETRY] 지도 정보 교체")
        
        # ✅ 환각 패턴 재검출
        loop_pattern = r'(\b[가-힣A-Za-z0-9]{2,15}\b(?:\s*(?:→|->)\s*\b[가-힣A-Za-z0-9]{2,15}\b)){10,}'
        
        if re.search(loop_pattern, result):
            logger.warning("   ⚠️ 재추출에도 환각 패턴 - 기존 내용만 반환")
            return prev
        
        logger.info("   ✅ [RETRY] 섹션 Replace 병합 성공")
        return result
    
    def _extract_retry_sections(self, additional: str) -> Dict[str, str]:
        """
        [RETRY] 섹션을 타입별로 추출
        
        Returns:
            {
                'table': '표 내용',
                'diagram': '다이어그램 내용',
                'map': '지도 내용'
            }
        """
        sections = {}
        lines = additional.splitlines()
        
        current_section = None
        section_lines = []
        
        for line in lines:
            # [RETRY] 마커 감지
            if '[RETRY]' in line:
                # 섹션 타입 추론
                if '표' in line or 'table' in line.lower():
                    current_section = 'table'
                elif '다이어그램' in line or 'diagram' in line.lower():
                    current_section = 'diagram'
                elif '지도' in line or 'map' in line.lower():
                    current_section = 'map'
                
                section_lines = [line]
                continue
            
            # 섹션 수집 중
            if current_section:
                section_lines.append(line)
                
                # 다음 섹션 시작 시 종료
                if line.startswith('##') and '[RETRY]' not in line:
                    sections[current_section] = '\n'.join(section_lines[:-1])
                    current_section = None
                    section_lines = []
        
        # 마지막 섹션 처리
        if current_section and section_lines:
            sections[current_section] = '\n'.join(section_lines)
        
        return sections
    
    def _extract_kvs(self, content: str, hints: Dict) -> Dict[str, str]:
        """
        Key-Value Structured 데이터 추출
        
        (Phase 5.3.1 유지)
        
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
        validation: Dict,
        conflict_notes: List[str]
    ) -> float:
        """품질 점수 계산 (충돌 페널티 추가)"""
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
        
        # ✅ 충돌 페널티 (GPT 제안)
        conflict_penalty = len(conflict_notes) * 10
        base_score -= conflict_penalty
        
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
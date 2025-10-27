"""
core/hybrid_extractor.py
PRISM Phase 5.6.0 - Hybrid Extractor (Integrated)

✅ Phase 5.6.0 통합 (GPT + 팀 의견 반영):
1. Post-merge Normalizer (문장 결속)
2. Statute-aware Chunker (조문 청킹)
3. Typo Normalizer (오탈자 교정)

(Phase 5.5.1 기능 유지)
- 표 포맷 감지 보수화
- 중복 제거 안전화
- 검증 강화

Author: 이서영 (Backend Lead)  
Date: 2025-10-27
Version: 5.6.0
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.6.0 통합 추출기
    
    플로우:
    1. QuickLayoutAnalyzer → CV 힌트
    2. PromptRules → DSL 프롬프트
    3. VLMService → Markdown 추출
    4. Validation → 검증
    5. Retry → 재추출
    6. Merge → Replace 병합
    7. ✅ PostMergeNormalizer → 문장 결속
    8. ✅ TypoNormalizer → 오탈자 교정
    9. Dedup → 중복 제거
    10. KVSNormalizer → KVS 정규화
    """
    
    def __init__(self, vlm_service, analyzer=None, prompt_rules=None, kvs_normalizer=None):
        """초기화"""
        self.vlm = vlm_service
        
        if analyzer is None:
            from .quick_layout_analyzer import QuickLayoutAnalyzer
            self.analyzer = QuickLayoutAnalyzer()
        else:
            self.analyzer = analyzer
        
        if prompt_rules is None:
            from .prompt_rules import PromptRules
            self.prompt_rules = PromptRules
        else:
            self.prompt_rules = prompt_rules
        
        if kvs_normalizer is None:
            from .kvs_normalizer import KVSNormalizer
            self.kvs_normalizer = KVSNormalizer
        else:
            self.kvs_normalizer = kvs_normalizer
        
        # ✅ Phase 5.6.0: 새 컴포넌트
        from .post_merge_normalizer import PostMergeNormalizer
        from .typo_normalizer import TypoNormalizer
        
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        logger.info("✅ HybridExtractor v5.6.0 초기화 완료 (Integrated)")
    
    def extract(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """페이지 추출"""
        import time
        start_time = time.time()
        
        logger.info(f"   🔧 HybridExtractor v5.6.0 추출 시작 (페이지 {page_num})")
        
        try:
            # Step 1: CV 힌트
            cv_start = time.time()
            hints = self.analyzer.analyze(image_data)
            cv_time = time.time() - cv_start
            
            # Step 2: 프롬프트
            prompt_start = time.time()
            prompt = self.prompt_rules.build_prompt(hints)
            prompt_time = time.time() - prompt_start
            
            # Step 3: VLM
            vlm_start = time.time()
            content = self.vlm.call(image_data, prompt)
            vlm_time = time.time() - vlm_start
            logger.info(f"      ⏱️ VLM: {vlm_time:.2f}초 ({len(content)} 글자)")
            
            # Step 4: 검증
            validation = self._validate_content(content, hints)
            logger.info(f"      ✅ 검증: {validation['passed']}")
            
            # Step 5: 재추출
            retry_count = 0
            if not validation['passed'] and 'TABLE_FORBIDDEN_USED' in validation['violations']:
                logger.info(f"      🔄 표 금지 재추출")
                
                retry_start = time.time()
                retry_content = self._retry_with_table_forbidden(image_data, hints)
                retry_time = time.time() - retry_start
                retry_count = 1
                
                content = self._replace_merge(content, retry_content)
                logger.info(f"      🔀 Replace 병합 완료")
                
                validation = self._validate_content(content, hints)
            
            # ✅ Step 6: Post-merge Normalizer (Phase 5.6.0)
            doc_type = self._determine_doc_type(hints)
            content = self.post_normalizer.normalize(content, doc_type)
            
            # ✅ Step 7: Typo Normalizer (Phase 5.6.0)
            content = self.typo_normalizer.normalize(content, doc_type)
            
            # Step 8: 중복 제거
            content = self._dedup_by_sentences(content)
            logger.info(f"      🧹 중복 제거 완료 ({len(content)} 글자)")
            
            # Step 9: KVS
            kvs = self._extract_kvs(content)
            if kvs:
                kvs = self.kvs_normalizer.normalize_kvs(kvs)
                logger.info(f"      💾 KVS: {len(kvs)}개")
            
            # Step 10: 품질
            quality_score = self._calculate_quality(content, validation)
            
            total_time = time.time() - start_time
            
            result = {
                'content': content,
                'doc_type': doc_type,
                'confidence': validation['confidence'],
                'quality_score': quality_score,
                'hints': hints,
                'validation': validation,
                'kvs': kvs,
                'metrics': {
                    'cv_time': cv_time,
                    'prompt_time': prompt_time,
                    'vlm_time': vlm_time,
                    'total_time': total_time,
                    'retry_count': retry_count
                }
            }
            
            logger.info(f"   ✅ 추출 완료: 품질 {quality_score:.0f}/100")
            return result
        
        except Exception as e:
            logger.error(f"   ❌ 추출 실패: {e}")
            raise
    
    def _validate_content(self, content: str, hints: Dict[str, Any]) -> Dict[str, Any]:
        """내용 검증"""
        violations = []
        scores = {}
        
        ocr_text = hints.get('ocr_text', '')
        
        from .prompt_rules import PromptRules
        table_confidence = PromptRules._calculate_table_confidence(hints, ocr_text)
        is_statute_mode = PromptRules._detect_statute_mode(hints, ocr_text)
        
        # 표 금지 위반 검사
        has_table = self._has_table_format_conservative(content)
        
        if is_statute_mode:
            if has_table and table_confidence < 3:
                violations.append('TABLE_FORBIDDEN_USED')
                logger.debug(f"         [위반] 규정 모드 표 사용")
        else:
            if has_table and table_confidence < 2:
                violations.append('TABLE_FORBIDDEN_USED')
                logger.debug(f"         [위반] 일반 모드 표 사용")
        
        # 길이
        char_count = len(content)
        if char_count < 50:
            violations.append('TOO_SHORT')
            scores['length'] = 0
        else:
            scores['length'] = min(100, char_count / 10)
        
        # 구조
        headers = re.findall(r'^#+\s+', content, re.MULTILINE)
        if len(headers) >= 2:
            scores['structure'] = 100
        elif len(headers) == 1:
            scores['structure'] = 70
        else:
            violations.append('NO_STRUCTURE')
            scores['structure'] = 30
        
        # 메타 설명
        meta_patterns = ['이 이미지는', '다음과 같습니다', '아래는', '필요하신', '말씀해 주세요']
        has_meta = any(re.search(p, content) for p in meta_patterns)
        if has_meta:
            violations.append('HAS_META_DESC')
            scores['meta'] = 0
        else:
            scores['meta'] = 100
        
        confidence = sum(scores.values()) / max(1, len(scores))
        confidence = max(0.0, min(100.0, confidence)) / 100.0
        
        passed = len(violations) == 0
        
        return {
            'passed': passed,
            'violations': violations,
            'confidence': confidence,
            'scores': scores
        }
    
    def _has_table_format_conservative(self, content: str) -> bool:
        """보수적 표 형식 감지"""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        
        # Markdown 표: 헤더-구분선-데이터 연속 블록
        blocks = 0
        for i in range(len(lines) - 2):
            if '|' in lines[i]:
                if set(lines[i+1].replace('|', '').strip()) <= set('- '):
                    if '|' in lines[i+2]:
                        blocks += 1
                        logger.debug(f"         Markdown 표 블록 감지: 줄 {i}-{i+2}")
        
        if blocks >= 1:
            logger.debug(f"         표 형식: Markdown 표 {blocks}개 블록")
            return True
        
        # CSV-like
        csv_run = 0
        for i, line in enumerate(lines):
            if line.count(',') >= 3:
                alnum_ratio = sum(c.isalnum() for c in line) / max(1, len(line))
                if alnum_ratio > 0.5:
                    csv_run += 1
                    if csv_run >= 3:
                        logger.debug(f"         표 형식: CSV-like 줄 {i-2}-{i}")
                        return True
                else:
                    csv_run = 0
            else:
                csv_run = 0
        
        logger.debug(f"         표 형식: 없음 (보수적 검사)")
        return False
    
    def _retry_with_table_forbidden(self, image_data: str, hints: Dict[str, Any]) -> str:
        """표 금지 재추출"""
        retry_prompt = """**CRITICAL: 표 사용 금지**

이전 출력에 표가 있었지만, 이 페이지는 표가 아닙니다.

**절대 금지:**
- Markdown 표 (|, ---) 절대 금지
- CSV 형식 (,) 절대 금지

**반드시 사용:**
- 문단: 본문 설명
- 불릿 목록: - 또는 1. 2. 3.

**예시:**
```
**개정 이력:**
- 제37차 개정: 2019.05.27
- 제38차 개정: 2019.07.01
```

다시 추출하세요.
"""
        
        retry_content = self.vlm.call(image_data, retry_prompt)
        return retry_content
    
    def _replace_merge(self, original: str, retry: str) -> str:
        """Replace 병합"""
        merged = retry
        logger.debug(f"         Replace: {len(original)} → {len(merged)} 글자")
        return merged
    
    def _dedup_by_sentences(self, text: str) -> str:
        """문장 단위 중복 제거"""
        sents = [s.strip() for s in re.split(r'(?<=[.!?。])\s+|\n{2,}', text) if s.strip()]
        
        seen = set()
        out = []
        
        for s in sents:
            key = re.sub(r'\s+', ' ', s)[:160]
            
            if key not in seen:
                seen.add(key)
                out.append(s)
        
        result = "\n\n".join(out)
        
        logger.debug(f"         중복 제거: {len(sents)}문장 → {len(out)}문장")
        return result
    
    def _extract_kvs(self, content: str) -> Dict[str, str]:
        """KVS 추출"""
        kvs = {}
        
        patterns = [
            r'[\*\*]?(.+?)[\*\*]?:\s*(.+)',
            r'•\s*(.+?):\s*(.+)',
            r'-\s*(.+?):\s*(.+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for key, value in matches:
                key = key.strip().strip('*')
                value = value.strip()
                if key and value and len(key) < 50 and len(value) < 200:
                    kvs[key] = value
        
        return kvs
    
    def _determine_doc_type(self, hints: Dict[str, Any]) -> str:
        """문서 타입 판별"""
        ocr_text = hints.get('ocr_text', '')
        from .prompt_rules import PromptRules
        
        if PromptRules._detect_statute_mode(hints, ocr_text):
            return 'statute'
        elif hints.get('has_map') and len(hints.get('bus_keywords', [])) >= 2:
            return 'bus_diagram'
        elif hints.get('has_table'):
            return 'table'
        else:
            return 'general'
    
    def _calculate_quality(self, content: str, validation: Dict[str, Any]) -> float:
        """품질 점수"""
        score = validation['confidence'] * 100
        
        if len(content) > 500:
            score += 10
        
        if validation['scores'].get('structure', 0) == 100:
            score += 10
        
        return max(0.0, min(100.0, score))
"""
core/hybrid_extractor.py
PRISM Phase 5.7.2.2 Hotfix - Hybrid Extractor (Pipeline Fix)

✅ Phase 5.7.2.2 긴급 수정 (GPT 의견 100% 반영):
1. 페이지 구분자 제거 - OCR 직후 실행
2. 빈 페이지는 Skip (실패로 카운트 안함)
3. 유니코드 정규화 (NFKC) 추가
4. 로그 레벨 조정 (INFO)

(Phase 5.6.1 기능 유지)

Author: 이서영 (Backend Lead) + GPT(미송) 의견 반영  
Date: 2025-10-31
Version: 5.7.2.2 Hotfix
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.7.2.2 통합 추출기 (Pipeline Hotfix)
    
    플로우:
    0. ✅ _strip_page_dividers → 페이지 구분자 제거 (Phase 5.7.2.2)
    1. QuickLayoutAnalyzer → CV 힌트
    2. PromptRules → DSL 프롬프트
    3. VLMService → Markdown 추출
    4. Validation → 검증
    5. ✅ Empty Guard → 빈 페이지 Skip (Phase 5.7.2.2)
    6. Retry → 재추출
    7. Merge → Replace 병합
    8. PostMergeNormalizer v5.6.1 → 문장 결속 강화
    9. TypoNormalizer v5.6.1 → 오탈자 교정 확장
    10. Dedup → 중복 제거
    11. KVSNormalizer → KVS 정규화
    12. Amendment Extractor → 개정 메모 추출
    """
    
    # ✅ Phase 5.7.2.2: 페이지 구분자 패턴
    PAGE_DIVIDER_PATTERNS = [
        re.compile(r'^#{0,3}\s*Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^[-—–_]{3,}\s*$'),
        re.compile(r'^\*{3,}\s*$'),
        re.compile(r'^={3,}\s*$'),
    ]
    
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
        
        # Phase 5.6.1: 새 컴포넌트 (v5.6.1)
        from .post_merge_normalizer import PostMergeNormalizer
        from .typo_normalizer import TypoNormalizer
        
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        logger.info("✅ HybridExtractor v5.7.2.2 초기화 완료 (Pipeline Hotfix)")
    
    def extract(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """페이지 추출"""
        import time
        start_time = time.time()
        
        logger.info(f"   🔧 HybridExtractor v5.7.2.2 추출 시작 (페이지 {page_num})")
        
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
            
            # ✅ Step 3.5: 페이지 구분자 제거 (Phase 5.7.2.2)
            content_before_clean = len(content)
            content = self._strip_page_dividers(content)
            if len(content) < content_before_clean:
                logger.info(f"      🧹 페이지 구분자 제거: {content_before_clean}자 → {len(content)}자")
            
            # Step 4: 검증
            validation = self._validate_content(content, hints)
            logger.info(f"      ✅ 검증: {validation['passed']}")
            
            # ✅ Step 5: 빈 페이지 Skip (Phase 5.7.2.2 개선)
            visible_chars = len([c for c in content if c.strip()])
            if visible_chars < 10:
                logger.info(f"      ℹ️ 빈 페이지 Skip (가시문자 {visible_chars}자)")
                return {
                    'content': '',
                    'doc_type': 'empty',
                    'confidence': 0.0,
                    'quality_score': 0.0,
                    'hints': hints,
                    'validation': {'passed': False, 'violations': ['EMPTY_PAGE'], 'confidence': 0.0},
                    'kvs': [],
                    'amendment_notes': [],
                    'quality_indicators': {
                        'statute_mode': False,
                        'table_confidence': 0.0,
                        'amendment_count': 0
                    },
                    'metrics': {
                        'cv_time': cv_time,
                        'prompt_time': prompt_time,
                        'vlm_time': vlm_time,
                        'total_time': time.time() - start_time,
                        'retry_count': 0
                    },
                    'is_empty': True  # ✅ 빈 페이지 플래그
                }
            
            # Step 6: 재추출 (표 금지)
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
            
            # Step 7: Post-merge Normalizer v5.6.1 (Phase 5.6.1)
            doc_type = self._determine_doc_type(hints)
            content = self.post_normalizer.normalize(content, doc_type)
            
            # Step 8: Typo Normalizer v5.6.1 (Phase 5.6.1)
            content = self.typo_normalizer.normalize(content, doc_type)
            
            # Step 9: 중복 제거
            content = self._dedup_by_sentences(content)
            logger.info(f"      🧹 중복 제거 완료 ({len(content)} 글자)")
            
            # Step 10: KVS
            kvs = self._extract_kvs(content)
            if kvs:
                kvs = self.kvs_normalizer.normalize_kvs(kvs)
                logger.info(f"      💾 KVS: {len(kvs)}개")
            
            # Step 11: 개정 메모 추출 (Phase 5.6.1)
            amendment_notes = self._extract_amendment_notes(content)
            
            # Step 12: 품질
            quality_score = self._calculate_quality(content, validation)
            
            # Step 13: 품질 지표 3종 (Phase 5.6.1)
            ocr_text = hints.get('ocr_text', '')
            quality_indicators = {
                'statute_mode': self.prompt_rules._detect_statute_mode(hints, ocr_text),
                'table_confidence': self.prompt_rules._calculate_table_confidence(hints, ocr_text),
                'amendment_count': len(amendment_notes)
            }
            
            total_time = time.time() - start_time
            
            result = {
                'content': content,
                'doc_type': doc_type,
                'confidence': validation['confidence'],
                'quality_score': quality_score,
                'hints': hints,
                'validation': validation,
                'kvs': kvs,
                'amendment_notes': amendment_notes,
                'quality_indicators': quality_indicators,
                'metrics': {
                    'cv_time': cv_time,
                    'prompt_time': prompt_time,
                    'vlm_time': vlm_time,
                    'total_time': total_time,
                    'retry_count': retry_count
                },
                'is_empty': False  # ✅ 정상 페이지 플래그
            }
            
            logger.info(f"   ✅ 추출 완료: 품질 {quality_score:.0f}/100")
            return result
        
        except Exception as e:
            logger.error(f"   ❌ 추출 실패: {e}")
            raise
    
    def _strip_page_dividers(self, text: str) -> str:
        """
        ✅ Phase 5.7.2.2: 페이지 구분자 제거
        
        제거 대상:
        - # Page 1, ## Page 2, Page 3
        - ---, ***, ===
        
        특징:
        - 유니코드 정규화 (NFKC)
        - 줄 단위 완전 매치
        - 원문 보존 (raw line 유지)
        """
        cleaned = []
        for raw_line in text.splitlines():
            # 유니코드 정규화 (보이지 않는 문자 제거)
            normalized = unicodedata.normalize('NFKC', raw_line).strip()
            
            # 페이지 구분자 패턴 매치
            if any(p.match(normalized) for p in self.PAGE_DIVIDER_PATTERNS):
                continue  # 이 줄은 제거
            
            # 원문 보존
            cleaned.append(raw_line)
        
        return "\n".join(cleaned)
    
    def _validate_content(self, content: str, hints: Dict[str, Any]) -> Dict[str, Any]:
        """내용 검증"""
        violations = []
        scores = {}
        
        ocr_text = hints.get('ocr_text', '')
        
        from .prompt_rules import PromptRules
        table_confidence = PromptRules._calculate_table_confidence(hints, ocr_text)
        is_statute_mode = PromptRules._detect_statute_mode(hints, ocr_text)
        
        # 표 금지 검사
        if is_statute_mode and table_confidence > 0.3:
            if '|' in content[:500] or content.count('|') > 10:
                violations.append('TABLE_FORBIDDEN_USED')
                scores['table_forbidden'] = 0.0
            else:
                scores['table_forbidden'] = 1.0
        
        # 구조 보존
        article_count = content.count('제') + content.count('조')
        if article_count >= 2:
            scores['structure'] = 1.0
        elif article_count == 1:
            scores['structure'] = 0.5
        else:
            scores['structure'] = 0.3
        
        # 길이 검사
        if len(content) < 50:
            violations.append('TOO_SHORT')
            scores['length'] = 0.3
        elif len(content) < 200:
            scores['length'] = 0.7
        else:
            scores['length'] = 1.0
        
        # 신뢰도 계산
        confidence = sum(scores.values()) / max(len(scores), 1)
        
        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'scores': scores,
            'confidence': confidence
        }
    
    def _retry_with_simple_prompt(self, image_data: str) -> str:
        """간단 프롬프트로 재추출"""
        simple_prompt = "이 페이지의 모든 텍스트를 추출하세요. Markdown 형식으로 출력하세요."
        return self.vlm.call(image_data, simple_prompt)
    
    def _retry_with_table_forbidden(self, image_data: str, hints: Dict[str, Any]) -> str:
        """표 금지 재추출"""
        forbidden_prompt = self.prompt_rules.build_prompt(hints)
        forbidden_prompt += "\n\n⚠️ 중요: 표 형식(|)을 절대 사용하지 마세요. 모든 내용을 문장으로 작성하세요."
        return self.vlm.call(image_data, forbidden_prompt)
    
    def _replace_merge(self, original: str, retry: str) -> str:
        """Replace 병합"""
        if len(retry) > len(original) * 0.8:
            return retry
        return original
    
    def _determine_doc_type(self, hints: Dict[str, Any]) -> str:
        """문서 타입 판정"""
        ocr_text = hints.get('ocr_text', '')
        
        from .prompt_rules import PromptRules
        is_statute = PromptRules._detect_statute_mode(hints, ocr_text)
        
        if is_statute:
            return 'statute'
        return 'general'
    
    def _dedup_by_sentences(self, content: str) -> str:
        """문장 단위 중복 제거"""
        lines = content.split('\n')
        seen = set()
        result = []
        
        for line in lines:
            normalized = line.strip()
            if not normalized:
                result.append(line)
                continue
            
            if normalized not in seen:
                seen.add(normalized)
                result.append(line)
        
        return '\n'.join(result)
    
    def _extract_kvs(self, content: str) -> List[Dict[str, str]]:
        """KVS 추출"""
        kvs = []
        
        # 괄호 패턴: 제1조(목적)
        for match in re.finditer(r'(제\s?\d+조)\s*\(([^)]+)\)', content):
            kvs.append({
                'key': match.group(1),
                'value': match.group(2),
                'type': 'article_title'
            })
        
        # 개정일 패턴
        for match in re.finditer(r'(개정|신설|삭제)\s*(\d{4}\.\d{1,2}\.\d{1,2})', content):
            kvs.append({
                'key': match.group(1),
                'value': match.group(2),
                'type': 'amendment_date'
            })
        
        return kvs
    
    def _extract_amendment_notes(self, content: str) -> List[str]:
        """✅ Phase 5.6.1: 개정 메모 추출"""
        notes = []
        
        # 패턴 1: [개정 2024.1.1]
        for match in re.finditer(r'\[([^]]+\d{4}\.\d{1,2}\.\d{1,2}[^]]*)\]', content):
            notes.append(match.group(1))
        
        # 패턴 2: (개정 2024.1.1)
        for match in re.finditer(r'\(([^)]+\d{4}\.\d{1,2}\.\d{1,2}[^)]*)\)', content):
            if '개정' in match.group(1) or '신설' in match.group(1) or '삭제' in match.group(1):
                notes.append(match.group(1))
        
        return list(set(notes))
    
    def _calculate_quality(self, content: str, validation: Dict[str, Any]) -> float:
        """품질 점수 계산"""
        score = 0.0
        
        # 검증 통과 여부 (40점)
        if validation['passed']:
            score += 40
        
        # 신뢰도 (30점)
        score += validation['confidence'] * 30
        
        # 길이 (20점)
        if len(content) >= 500:
            score += 20
        elif len(content) >= 200:
            score += 15
        elif len(content) >= 100:
            score += 10
        
        # 구조 (10점)
        structure_score = validation['scores'].get('structure', 0)
        score += structure_score * 10
        
        return min(score, 100)
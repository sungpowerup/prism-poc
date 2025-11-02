"""
core/hybrid_extractor.py
PRISM Phase 5.7.4 - Hybrid Extractor (PyMuPDF Fallback)

✅ Phase 5.7.4 주요 개선:
1. PyMuPDF Fallback 메커니즘 추가 (VLM 실패 시)
2. Fallback 로깅 및 모니터링
3. 품질 점수 차등 적용 (Fallback: 70점)
4. VLM 실패율 추적

(Phase 5.7.2.2 기능 유지)

Author: 이서영 (Backend Lead) + 마창수산 팀
Date: 2025-11-02
Version: 5.7.4
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 5.7.4 통합 추출기 (PyMuPDF Fallback)
    
    플로우:
    0. ✅ _strip_page_dividers → 페이지 구분자 제거
    1. QuickLayoutAnalyzer → CV 힌트
    2. PromptRules → DSL 프롬프트
    3. VLMService → Markdown 추출
    4. ✅ NEW: PyMuPDF Fallback (VLM 0글자 시)
    5. Validation → 검증
    6. ✅ Empty Guard → 빈 페이지 Skip
    7. Retry → 재추출
    8. Merge → Replace 병합
    9. PostMergeNormalizer → 문장 결속 강화
    10. TypoNormalizer → 오탈자 교정
    11. Dedup → 중복 제거
    12. KVSNormalizer → KVS 정규화
    13. Amendment Extractor → 개정 메모 추출
    """
    
    # ✅ Phase 5.7.2.2: 페이지 구분자 패턴
    PAGE_DIVIDER_PATTERNS = [
        re.compile(r'^#{0,3}\s*Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^[-—–_]{3,}\s*$'),
        re.compile(r'^\*{3,}\s*$'),
        re.compile(r'^={3,}\s*$'),
    ]
    
    def __init__(
        self, 
        vlm_service, 
        analyzer=None, 
        prompt_rules=None, 
        kvs_normalizer=None,
        pdf_path: Optional[str] = None  # ✅ Phase 5.7.4: PDF 경로 추가
    ):
        """
        초기화
        
        Args:
            vlm_service: VLM 서비스
            analyzer: QuickLayoutAnalyzer (Optional)
            prompt_rules: PromptRules (Optional)
            kvs_normalizer: KVSNormalizer (Optional)
            pdf_path: PDF 파일 경로 (Fallback용, Optional)
        """
        self.vlm = vlm_service
        self.pdf_path = pdf_path  # ✅ Fallback용 PDF 경로
        
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
        
        # Phase 5.6.1: 새 컴포넌트
        from .post_merge_normalizer import PostMergeNormalizer
        from .typo_normalizer import TypoNormalizer
        
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        # ✅ Phase 5.7.4: Fallback 통계
        self.fallback_count = 0
        self.vlm_success_count = 0
        
        logger.info("✅ HybridExtractor v5.7.4 초기화 완료 (PyMuPDF Fallback)")
        logger.info("   - VLM 실패 시 자동 Fallback 지원")
    
    def extract(self, image_data: str, page_num: int = 1) -> Dict[str, Any]:
        """
        페이지 추출 (PyMuPDF Fallback 포함)
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호
        
        Returns:
            추출 결과
        """
        import time
        start_time = time.time()
        
        logger.info(f"   🔧 HybridExtractor v5.7.4 추출 시작 (페이지 {page_num})")
        
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
            dividers_removed = content_before_clean - len(content)
            
            if len(content) < content_before_clean:
                logger.info(f"      🧹 페이지 구분자 제거: {content_before_clean}자 → {len(content)}자")
            
            # ✅ Phase 5.7.4: VLM 0글자 감지 및 Fallback
            visible_chars = len([c for c in content if c.strip()])
            
            if visible_chars < 10:
                logger.warning(f"      ⚠️ VLM 추출 실패: {visible_chars}자 < 10자")
                
                # ✅ PyMuPDF Fallback 시도
                fallback_result = self._try_pymupdf_fallback(page_num)
                
                if fallback_result is not None:
                    # Fallback 성공
                    logger.info(f"      ✅ PyMuPDF Fallback 성공: {len(fallback_result)} 글자")
                    self.fallback_count += 1
                    
                    content = fallback_result
                    visible_chars = len([c for c in content if c.strip()])
                    
                    # Fallback 사용 플래그
                    used_fallback = True
                else:
                    # Fallback도 실패 → 빈 페이지로 처리
                    logger.info(f"      ℹ️ PyMuPDF Fallback도 실패 → 빈 페이지 Skip")
                    
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
                            'retry_count': 0,
                            'fallback_used': False
                        },
                        'is_empty': True,
                        'source': 'vlm_failed'
                    }
            else:
                # VLM 정상 추출
                used_fallback = False
                self.vlm_success_count += 1
            
            # Step 4: 검증
            validation = self._validate_content(content, hints)
            logger.info(f"      ✅ 검증: {validation['passed']}")
            
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
            
            # Step 7: Post-merge Normalizer
            doc_type = self._determine_doc_type(hints)
            content = self.post_normalizer.normalize(content, doc_type)
            
            # Step 8: Typo Normalizer
            content = self.typo_normalizer.normalize(content, doc_type)
            
            # Step 9: 중복 제거
            content = self._dedup_by_sentences(content)
            logger.info(f"      🧹 중복 제거 완료 ({len(content)} 글자)")
            
            # Step 10: KVS
            kvs = self._extract_kvs(content)
            if kvs:
                kvs = self.kvs_normalizer.normalize_kvs(kvs)
                logger.info(f"      💾 KVS: {len(kvs)}개")
            
            # Step 11: 개정 메모 추출
            amendment_notes = self._extract_amendment_notes(content)
            
            # Step 12: 품질 (✅ Fallback 시 70점 상한)
            quality_score = self._calculate_quality(content, validation, used_fallback)
            
            # Step 13: 품질 지표 3종
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
                    'retry_count': retry_count,
                    'fallback_used': used_fallback  # ✅ Fallback 사용 여부
                },
                'is_empty': False,
                'source': 'pymupdf_fallback' if used_fallback else 'vlm'  # ✅ 출처 표시
            }
            
            logger.info(f"   ✅ 추출 완료: 품질 {quality_score:.0f}/100 (출처: {result['source']})")
            return result
        
        except Exception as e:
            logger.error(f"   ❌ 추출 실패: {e}")
            raise
    
    def _try_pymupdf_fallback(self, page_num: int) -> Optional[str]:
        """
        ✅ Phase 5.7.4: PyMuPDF Fallback 시도
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출된 텍스트 or None (실패 시)
        """
        if self.pdf_path is None:
            logger.warning(f"      ⚠️ PyMuPDF Fallback 불가: PDF 경로 없음")
            return None
        
        try:
            import fitz  # PyMuPDF
            
            logger.info(f"      🔄 PyMuPDF Fallback 시도 (페이지 {page_num})...")
            
            # PDF 열기
            doc = fitz.open(self.pdf_path)
            
            # 페이지 인덱스 (0-based)
            page_index = page_num - 1
            
            if page_index >= len(doc):
                logger.warning(f"      ⚠️ 페이지 {page_num}이 존재하지 않음")
                doc.close()
                return None
            
            # 페이지 텍스트 추출
            page = doc[page_index]
            text = page.get_text("text")
            
            doc.close()
            
            # 추출 성공 여부 확인
            visible_chars = len([c for c in text if c.strip()])
            
            if visible_chars >= 10:
                logger.info(f"      ✅ PyMuPDF 추출 성공: {visible_chars}자")
                return text
            else:
                logger.warning(f"      ⚠️ PyMuPDF도 텍스트 부족: {visible_chars}자")
                return None
        
        except ImportError:
            logger.error(f"      ❌ PyMuPDF(fitz) 미설치: pip install pymupdf")
            return None
        
        except Exception as e:
            logger.error(f"      ❌ PyMuPDF Fallback 실패: {e}")
            return None
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """
        ✅ Phase 5.7.4: Fallback 통계 반환
        
        Returns:
            {
                'vlm_success_count': int,
                'fallback_count': int,
                'total_pages': int,
                'fallback_rate': float (0~1)
            }
        """
        total = self.vlm_success_count + self.fallback_count
        
        return {
            'vlm_success_count': self.vlm_success_count,
            'fallback_count': self.fallback_count,
            'total_pages': total,
            'fallback_rate': self.fallback_count / max(1, total)
        }
    
    def _strip_page_dividers(self, text: str) -> str:
        """
        ✅ Phase 5.7.2.2: 페이지 구분자 제거
        
        제거 대상:
        - # Page 1, ## Page 2, Page 3
        - ---, ***, ===
        """
        cleaned = []
        removed_lines = 0
        
        for raw_line in text.splitlines():
            # 유니코드 정규화 (보이지 않는 문자 제거)
            normalized = unicodedata.normalize('NFKC', raw_line).strip()
            
            # 페이지 구분자 패턴 매치
            if any(p.match(normalized) for p in self.PAGE_DIVIDER_PATTERNS):
                removed_lines += 1
                continue  # 이 줄은 제거
            
            # 원문 보존
            cleaned.append(raw_line)
        
        if removed_lines > 0:
            logger.debug(f"         구분자 제거: {removed_lines}줄")
        
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
        """개정 메모 추출"""
        notes = []
        
        # 패턴 1: [개정 2024.1.1]
        for match in re.finditer(r'\[([^]]+\d{4}\.\d{1,2}\.\d{1,2}[^]]*)\]', content):
            notes.append(match.group(1))
        
        # 패턴 2: (개정 2024.1.1)
        for match in re.finditer(r'\(([^)]+\d{4}\.\d{1,2}\.\d{1,2}[^)]*)\)', content):
            if '개정' in match.group(1) or '신설' in match.group(1) or '삭제' in match.group(1):
                notes.append(match.group(1))
        
        return list(set(notes))
    
    def _calculate_quality(
        self, 
        content: str, 
        validation: Dict[str, Any],
        used_fallback: bool = False  # ✅ Phase 5.7.4: Fallback 여부
    ) -> float:
        """
        품질 점수 계산
        
        ✅ Phase 5.7.4: Fallback 사용 시 70점 상한
        
        Args:
            content: 추출된 내용
            validation: 검증 결과
            used_fallback: PyMuPDF Fallback 사용 여부
        
        Returns:
            품질 점수 (0~100)
        """
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
        
        # ✅ Fallback 사용 시 70점 상한
        if used_fallback:
            score = min(score, 70.0)
            logger.debug(f"         Fallback 사용: 품질 {score:.0f}/100 (상한 70)")
        
        return min(score, 100.0)
"""
core/hybrid_extractor.py
PRISM Phase 0.3.2 Hotfix - VLM 반환값 안전 처리

✅ Phase 0.3.2 Hotfix:
1. VLM 반환값 타입 안전 처리 (str/dict 모두 지원)
2. call_with_retry() 호환성 개선
3. 오류 복원력 강화

Author: 이서영 (Backend Lead) + 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.2 Hotfix
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

import pypdf
from pathlib import Path

try:
    from .quick_layout_analyzer import QuickLayoutAnalyzer
    from .prompt_rules import PromptRules
    from .post_merge_normalizer import PostMergeNormalizer
    from .typo_normalizer import TypoNormalizer
    from .kvs_normalizer import KVSNormalizer
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from quick_layout_analyzer import QuickLayoutAnalyzer
    from prompt_rules import PromptRules
    from post_merge_normalizer import PostMergeNormalizer
    from typo_normalizer import TypoNormalizer
    from kvs_normalizer import KVSNormalizer

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 0.3.2 통합 추출기 (안전 처리)
    
    ✅ Phase 0.3.2 Hotfix:
    - VLM 반환값 타입 안전 처리
    - 개정이력 감지 유지
    - Fallback 안정성 향상
    """
    
    STATUTE_KEYWORDS = [
        '조', '항', '호', '직원', '규정', '임용', '채용',
        '승진', '전보', '휴직', '면직', '해임', '파면',
        '인사', '보수', '급여', '수당', '복무', '징계',
        '위원회'
    ]
    
    def __init__(
        self,
        vlm_service,
        pdf_path: str,
        allow_tables: bool = False
    ):
        """초기화"""
        self.vlm_service = vlm_service
        self.pdf_path = pdf_path
        self.allow_tables = allow_tables
        
        self.layout_analyzer = QuickLayoutAnalyzer()
        self.prompt_rules = PromptRules()
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        self.vlm_success_count = 0
        self.fallback_count = 0
        
        logger.info("✅ HybridExtractor Phase 0.3.2 Hotfix 초기화 완료")
        logger.info(f"   - PDF: {pdf_path}")
        logger.info(f"   - 표 허용: {allow_tables}")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        ✅ Phase 0.3.2: 페이지별 추출 (안전 처리)
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출 결과
        """
        logger.info(f"   🔍 페이지 {page_num} 추출 시작")
        
        # Step 1: 레이아웃 분석 (OCR 포함)
        hints = self.layout_analyzer.analyze(image_data)
        
        # Step 2: 개정이력 감지
        has_revision_table = self._detect_revision_table(hints, page_num)
        
        if has_revision_table:
            logger.info(f"      📋 개정이력 표 감지 (페이지 {page_num})")
            hints['allow_tables'] = True
            page_role = "revision_table"
        else:
            page_role = "general"
        
        # Step 3: VLM 프롬프트 생성
        prompt = self.prompt_rules.build_prompt(hints)
        
        # Step 4: ✅ Phase 0.3.2 Hotfix - VLM 재시도 (안전 처리)
        if hasattr(self.vlm_service, 'call_with_retry'):
            logger.info(f"      🔄 VLM 재시도 로직 사용 (페이지 역할: {page_role})")
            
            try:
                vlm_result = self.vlm_service.call_with_retry(
                    image_data=image_data,
                    prompt=prompt,
                    page_role=page_role
                )
                
                # ✅ Phase 0.3.2 Hotfix: 반환값 타입 안전 처리
                if isinstance(vlm_result, dict):
                    # 딕셔너리 형식 (정상)
                    content = vlm_result.get('content', '')
                    is_fallback = vlm_result.get('fallback', False)
                    retry_count = vlm_result.get('retry_count', 0)
                    
                    if is_fallback or not content or len(content.strip()) < 50:
                        logger.warning(f"      ⚠️ VLM 재시도 실패 → Fallback")
                        content = self._fallback_extract(page_num)
                        self.fallback_count += 1
                        source = "fallback"
                        confidence = 0.7
                    else:
                        if retry_count > 0:
                            logger.info(f"      ✅ VLM 재시도 {retry_count}회 만에 성공")
                        self.vlm_success_count += 1
                        source = "vlm"
                        confidence = 1.0
                
                elif isinstance(vlm_result, str):
                    # 문자열 형식 (레거시 호환)
                    logger.warning(f"      ⚠️ VLM 반환값이 문자열 형식 (레거시 모드)")
                    content = vlm_result
                    
                    if content and len(content.strip()) >= 50:
                        self.vlm_success_count += 1
                        source = "vlm"
                        confidence = 1.0
                    else:
                        logger.warning(f"      ⚠️ VLM 응답 부족 → Fallback")
                        content = self._fallback_extract(page_num)
                        self.fallback_count += 1
                        source = "fallback"
                        confidence = 0.7
                
                else:
                    # 알 수 없는 형식
                    logger.error(f"      ❌ VLM 반환값 형식 오류: {type(vlm_result)}")
                    content = self._fallback_extract(page_num)
                    self.fallback_count += 1
                    source = "fallback"
                    confidence = 0.5
            
            except Exception as e:
                logger.error(f"      ❌ VLM 처리 오류: {e}")
                content = self._fallback_extract(page_num)
                self.fallback_count += 1
                source = "fallback"
                confidence = 0.5
        
        else:
            # 구버전 vlm_service (call만 있음)
            logger.warning("      ⚠️ call_with_retry 없음 - 단일 시도")
            
            try:
                response = self.vlm_service.call(image_data, prompt)
                
                if response and len(response.strip()) >= 50:
                    content = response
                    self.vlm_success_count += 1
                    source = "vlm"
                    confidence = 1.0
                else:
                    logger.warning(f"      ⚠️ VLM 빈 응답 → Fallback")
                    content = self._fallback_extract(page_num)
                    self.fallback_count += 1
                    source = "fallback"
                    confidence = 0.7
            
            except Exception as e:
                logger.error(f"      ❌ VLM 오류: {e} → Fallback")
                content = self._fallback_extract(page_num)
                self.fallback_count += 1
                source = "fallback"
                confidence = 0.5
        
        # Step 5: doc_type 조건부 승급
        doc_type = self._detect_doc_type_v2(content, hints)
        logger.info(f"      📋 문서 타입: {doc_type}")
        
        # Step 6: 후처리
        content = self.post_normalizer.normalize(content, doc_type)
        content = self.typo_normalizer.normalize(content, doc_type)
        content = self._deduplicate_lines(content)
        
        logger.info(f"      🧹 후처리 완료 ({len(content)} 글자)")
        
        # Step 7: KVS 추출
        kvs_raw = hints.get('kvs', [])
        kvs = KVSNormalizer.normalize_kvs(kvs_raw)
        
        logger.info(f"      💾 KVS: {len(kvs)}개")
        
        # Step 8: 품질 점수
        if source == "vlm":
            quality_score = 100
        else:
            quality_score = 70
        
        logger.info(f"   ✅ 추출 완료: 품질 {quality_score}/100 (출처: {source}, 타입: {doc_type})")
        
        return {
            'content': content,
            'source': source,
            'confidence': confidence,
            'quality_score': quality_score,
            'doc_type': doc_type,
            'kvs': kvs,
            'page_num': page_num
        }
    
    def _detect_revision_table(self, hints: Dict[str, Any], page_num: int) -> bool:
        """
        ✅ Phase 0: 개정이력 감지 (2축)
        
        축 A: OCR 텍스트에서 "제\\d+차\\s*개정" 3개 이상
        축 B: 날짜 패턴 "YYYY.MM.DD" 3개 이상
        
        Args:
            hints: QuickLayoutAnalyzer 힌트
            page_num: 페이지 번호
        
        Returns:
            True if 개정이력 표 감지됨
        """
        # 1페이지만 검사
        if page_num != 1:
            return False
        
        ocr_text = hints.get('ocr_text', '')
        
        # 축 A: "제N차 개정" 패턴
        revision_pattern = re.compile(r'제\s?\d+차\s*개정', re.IGNORECASE)
        revision_matches = revision_pattern.findall(ocr_text)
        revision_count = len(revision_matches)
        
        # 축 B: 날짜 패턴 "YYYY.MM.DD"
        date_pattern = re.compile(r'\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}')
        date_matches = date_pattern.findall(ocr_text)
        date_count = len(date_matches)
        
        # 판정: 둘 중 하나라도 3개 이상
        is_revision_table = (revision_count >= 3) or (date_count >= 3)
        
        if is_revision_table:
            logger.info(f"      ✅ 개정이력 감지 (OCR={revision_count}개, 날짜={date_count}개)")
        
        return is_revision_table
    
    def _fallback_extract(self, page_num: int) -> str:
        """
        Fallback 추출 (pypdf)
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출된 텍스트
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                
                if page_num - 1 < len(reader.pages):
                    page = reader.pages[page_num - 1]
                    text = page.extract_text()
                    
                    if text and len(text.strip()) > 0:
                        return text.strip()
        
        except Exception as e:
            logger.error(f"      ❌ Fallback 오류: {e}")
        
        return ""
    
    def _detect_doc_type_v2(self, content: str, hints: Dict[str, Any]) -> str:
        """
        문서 타입 탐지 v2
        
        Args:
            content: 추출된 내용
            hints: 레이아웃 힌트
        
        Returns:
            'statute', 'report', 'presentation', 'general'
        """
        # 조문 키워드 카운트
        keyword_count = sum(1 for kw in self.STATUTE_KEYWORDS if kw in content)
        
        # 조문 헤더 검색
        article_pattern = re.compile(r'제\s?\d+조')
        article_count = len(article_pattern.findall(content))
        
        # 규정 판정
        if article_count >= 2 or keyword_count >= 5:
            return 'statute'
        
        # 표 많으면 보고서
        if hints.get('has_table', False):
            return 'report'
        
        return 'general'
    
    def _deduplicate_lines(self, text: str) -> str:
        """
        중복 라인 제거
        
        Args:
            text: 원본 텍스트
        
        Returns:
            중복 제거된 텍스트
        """
        lines = text.split('\n')
        seen = set()
        result = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped and line_stripped not in seen:
                seen.add(line_stripped)
                result.append(line)
        
        return '\n'.join(result)
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        total = self.vlm_success_count + self.fallback_count
        
        return {
            'vlm_success': self.vlm_success_count,
            'fallback': self.fallback_count,
            'total': total,
            'fallback_ratio': self.fallback_count / total if total > 0 else 0
        }
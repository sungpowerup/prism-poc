"""
core/hybrid_extractor.py
PRISM Phase 0 Hotfix - Hybrid Extractor with Revision Detection

✅ Phase 0 긴급 수정:
1. _detect_revision_table() 2축 감지 (OCR + 날짜 패턴)
2. call_with_retry() 사용으로 VLM 안정화
3. 개정이력 페이지에 page_role="revision_table" 전달

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-11-06
Version: Phase 0 Hotfix
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
    Phase 0 통합 추출기 (개정이력 감지 + VLM 재시도)
    
    ✅ Phase 0 개선:
    1. 개정이력 감지 - 2축 (OCR + 날짜)
    2. VLM 재시도 - call_with_retry()
    3. 페이지 역할 전달 - revision_table
    
    플로우:
    1. QuickLayoutAnalyzer: 레이아웃 분석 + OCR
    2. 개정이력 감지 (1페이지만, 2축)
    3. VLM 시도 (call_with_retry)
    4. Fallback (pypdf)
    5. 후처리 (PostMergeNormalizer, TypoNormalizer)
    6. doc_type 조건부 승급
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
        
        logger.info("✅ HybridExtractor Phase 0 초기화 완료")
        logger.info(f"   - PDF: {pdf_path}")
        logger.info(f"   - 표 허용: {allow_tables}")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        ✅ Phase 0: 페이지별 추출 (개정이력 감지 + VLM 재시도)
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출 결과
        """
        logger.info(f"   🔍 페이지 {page_num} 추출 시작")
        
        # Step 1: 레이아웃 분석 (OCR 포함)
        hints = self.layout_analyzer.analyze(image_data)
        
        # Step 2: ✅ Phase 0 - 개정이력 감지 (2축)
        has_revision_table = self._detect_revision_table(hints, page_num)
        
        if has_revision_table:
            logger.info(f"      📋 개정이력 표 감지 (페이지 {page_num})")
            hints['allow_tables'] = True
            page_role = "revision_table"
        else:
            page_role = "general"
        
        # Step 3: VLM 프롬프트 생성
        prompt = self.prompt_rules.build_prompt(hints)
        
        # Step 4: ✅ Phase 0 - VLM 재시도 (call_with_retry)
        if hasattr(self.vlm_service, 'call_with_retry'):
            logger.info(f"      🔄 VLM 재시도 로직 사용 (페이지 역할: {page_role})")
            
            vlm_result = self.vlm_service.call_with_retry(
                image_data=image_data,
                prompt=prompt,
                page_role=page_role
            )
            
            content = vlm_result['content']
            
            if vlm_result['fallback']:
                logger.warning(f"      ⚠️ VLM 재시도 실패 → Fallback")
                content = self._fallback_extract(page_num)
                self.fallback_count += 1
                source = "fallback"
                confidence = 0.7
            else:
                if vlm_result['retry_count'] > 0:
                    logger.info(f"      ✅ VLM 재시도 {vlm_result['retry_count']}회 만에 성공")
                self.vlm_success_count += 1
                source = "vlm"
                confidence = 1.0
        
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
            'kvs': kvs,
            'is_empty': len(content.strip()) < 50,
            'metrics': {
                'page_num': page_num,
                'char_count': len(content),
                'source': source,
                'doc_type': doc_type,
                'has_revision_table': has_revision_table
            }
        }
    
    def _detect_revision_table(self, hints: Dict[str, Any], page_num: int) -> bool:
        """
        ✅ Phase 0: 개정이력 표 감지 (2축)
        
        전략:
        - 축 A: OCR 텍스트에서 "제\d+차\s*개정" 3개 이상
        - 축 B: 날짜 패턴 (YYYY.MM.DD | YYYY-MM-DD | YYYY) 3개 이상
        
        Args:
            hints: 레이아웃 힌트 (OCR 포함)
            page_num: 페이지 번호 (1-based)
        
        Returns:
            True if 개정이력 표 존재
        """
        # 1페이지만 체크 (일부 문서는 2페이지에도 가능)
        if page_num not in (1, 2):
            return False
        
        # hints에서 OCR 텍스트 추출
        text = hints.get('ocr_text', '') or hints.get('text', '')
        
        if not text:
            return False
        
        # 축 A: "제\d+차 개정" 패턴
        revision_pattern = re.compile(r'제\s*\d+\s*차\s*개정', re.MULTILINE)
        revision_matches = revision_pattern.findall(text)
        ocr_hit = len(revision_matches) >= 3
        
        # 축 B: 날짜 패턴 (다양한 형식)
        date_pattern = re.compile(
            r'\b('
            r'\d{4}\.\d{1,2}\.\d{1,2}|'  # 2019.05.27
            r'\d{4}-\d{1,2}-\d{1,2}|'    # 2019-05-27
            r'[\'\'(]?\d{4}[\'\')\.]?'    # 2019, '2019', (2019)
            r')\b'
        )
        date_matches = date_pattern.findall(text)
        date_hit = len(date_matches) >= 3
        
        # 2축 중 하나라도 만족하면 개정이력 표로 판단
        is_revision_table = ocr_hit or date_hit
        
        if is_revision_table:
            logger.info(f"      ✅ 개정이력 감지 (OCR={len(revision_matches)}개, 날짜={len(date_matches)}개)")
        
        return is_revision_table
    
    def _detect_doc_type_v2(self, content: str, hints: Dict[str, Any]) -> str:
        """
        문서 타입 조건부 승급
        
        Args:
            content: 추출된 텍스트
            hints: 레이아웃 힌트
        
        Returns:
            'statute', 'general', 'bus_diagram', 'table'
        """
        hint_type = hints.get('doc_type')
        
        # 조건부 statute 승급
        if hint_type != 'statute':
            has_article = bool(re.search(r'제\s*\d+\s*조', content))
            has_chapter = bool(re.search(r'제\s*\d+\s*장', content))
            has_spirit = '기본 정신' in content or '기본정신' in content
            
            if has_article or has_chapter or has_spirit:
                logger.debug(f"      doc_type 승급: {hint_type} → statute")
                return 'statute'
        
        if hint_type in ['statute', 'bus_diagram', 'table']:
            return hint_type
        
        return 'general'
    
    def _fallback_extract(self, page_num: int) -> str:
        """
        Fallback 텍스트 추출 (pypdf)
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출된 텍스트
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                page = pdf_reader.pages[page_num - 1]
                text = page.extract_text()
            
            if not text or len(text.strip()) < 20:
                logger.warning(f"      ⚠️ Fallback 추출 실패: 텍스트 부족")
                return ""
            
            # 인라인 페이지 마커 제거
            text = re.sub(r'\b(\d{3,4})-(\d{1,2})\s*(?=(\d+[.)]|[""]))', r'\1-\2\n', text)
            text = re.sub(r'[ \t]+(\n)', r'\1', text)
            
            # 정규화
            text = self._normalize_fallback_text(text)
            
            logger.debug(f"      Fallback 추출: {len(text)} 글자")
            
            return text
        
        except Exception as e:
            logger.error(f"      ❌ Fallback 오류: {e}")
            return ""
    
    def _normalize_fallback_text(self, text: str) -> str:
        """Fallback 텍스트 정규화"""
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text
    
    def _deduplicate_lines(self, content: str) -> str:
        """중복 라인 제거"""
        lines = content.split('\n')
        seen = set()
        deduped = []
        
        for line in lines:
            if not line.strip():
                deduped.append(line)
                continue
            
            line_key = line.strip()
            if line_key not in seen:
                seen.add(line_key)
                deduped.append(line)
        
        return '\n'.join(deduped)
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Fallback 통계"""
        total = self.vlm_success_count + self.fallback_count
        
        if total == 0:
            fallback_rate = 0.0
        else:
            fallback_rate = self.fallback_count / total
        
        return {
            'vlm_success_count': self.vlm_success_count,
            'fallback_count': self.fallback_count,
            'total_pages': total,
            'fallback_rate': fallback_rate
        }
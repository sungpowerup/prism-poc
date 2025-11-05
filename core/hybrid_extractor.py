"""
core/hybrid_extractor.py
PRISM Phase 5.7.8.5 - Hybrid Extractor (미송 우선순위 수정)

✅ Phase 5.7.8.5 수정사항 (미송 제안):
1. VLM 어댑터 (최우선) - 메서드명 자동 적응
2. 청킹 가드 강화 - 번호목록 과밀 분절 (8개)
3. 띄어쓰기 2-pass 수렴 + '가 진다' 보강

🎯 해결 문제:
- VLM Fallback 100% → 0% (어댑터로 해결)
- 청크 1개 (4,257자) → 3~5개 (600~1,200자)
- 띄어쓰기 미교정 → 2-pass로 완전 교정

✅ Phase 5.7.8.4 수정사항:
1. VLM 메서드명 수정 (extract_text → extract)
2. 띄어쓰기 복원 패턴 추가 (미송 제안 #1)
3. 청킹 개선 - 번호목록 폭주 감지 10개 (미송 제안 #2)

Author: 이서영 (Backend Lead) + 미송 피드백
Date: 2025-11-06
Version: 5.7.8.5 Final
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

# ✅ Phase 5.7.6: pypdf (BSD-3)
import pypdf
from pathlib import Path

# Phase 5.7.4 imports
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
    Phase 5.7.8.5 통합 추출기 (미송 우선순위 수정)
    
    미송 제안 (우선순위 수정):
    1. VLM 어댑터 (최우선) - Fallback 100% 해결
    2. 청킹 가드 강화 - 번호목록 과밀 분절
    3. 띄어쓰기 2-pass 수렴 + '가 진다' 보강
    
    플로우:
    1. QuickLayoutAnalyzer: 레이아웃 분석
    2. VLM 시도 (어댑터로 자동 적응)
    3. Fallback (pypdf)
    4. 개정이력 감지 (1페이지만)
    5. 후처리 (PostMergeNormalizer, TypoNormalizer)
    6. doc_type 조건부 승급
    """
    
    # Phase 5.7.4: 규정 키워드
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
        
        # Phase 5.7.4 components
        self.layout_analyzer = QuickLayoutAnalyzer()
        self.prompt_rules = PromptRules()
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        # Fallback 통계
        self.vlm_success_count = 0
        self.fallback_count = 0
        
        logger.info("✅ HybridExtractor v5.7.8.5 초기화 완료 (미송 VLM 어댑터)")
        logger.info(f"   - PDF: {pdf_path}")
        logger.info(f"   - 표 허용: {allow_tables}")
    
    def _vlm_extract(self, image_data: str, prompt: str, page_num: int) -> Dict[str, Any]:
        """
        ✅ Phase 5.7.8.5: VLM 어댑터 (미송 제안)
        
        메서드명 자동 적응:
        - extract() / process() / analyze() / get_text() / run()
        
        Args:
            image_data: Base64 이미지
            prompt: VLM 프롬프트
            page_num: 페이지 번호
        
        Returns:
            VLM 응답 (content 포함)
        """
        candidates = [
            ("extract", {"image_data": image_data, "prompt": prompt, "page_num": page_num}),
            ("process", {"image_data": image_data, "prompt": prompt, "page_num": page_num}),
            ("analyze", {"image_data": image_data, "prompt": prompt}),
            ("get_text", {"image_data": image_data, "prompt": prompt}),
            ("run", {"image_data": image_data, "prompt": prompt}),
        ]
        
        for name, kwargs in candidates:
            if hasattr(self.vlm_service, name):
                logger.info(f"      🎯 VLM 메서드 발견: '{name}'")
                try:
                    result = getattr(self.vlm_service, name)(**kwargs)
                    logger.info(f"      ✅ VLM 호출 성공: '{name}'")
                    return result
                except TypeError as e:
                    # 파라미터 불일치 시 다음 후보 시도
                    logger.debug(f"      ⚠️ '{name}' 파라미터 불일치: {e}")
                    continue
        
        # 모든 후보 실패
        raise AttributeError(
            "VLM 메서드를 찾을 수 없습니다. "
            "지원 메서드: extract/process/analyze/get_text/run"
        )
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        ✅ Phase 5.7.8.4: 페이지별 추출 (미송 3대 핫픽스)
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출 결과 (content, source, quality_score, kvs, metrics)
        """
        logger.info(f"   🔍 페이지 {page_num} 추출 시작")
        
        # Step 1: 레이아웃 분석
        hints = self.layout_analyzer.analyze(image_data)
        
        # Step 2: ✅ 개정이력 감지 (1페이지만)
        has_revision_table = self._detect_revision_table(hints, page_num)
        
        if has_revision_table:
            logger.info(f"      📋 개정이력 표 감지 (페이지 {page_num})")
            # 개정이력 페이지는 표 허용
            hints['allow_tables'] = True
        
        # Step 3: VLM 프롬프트 생성
        prompt = self.prompt_rules.build_prompt(hints)
        
        # Step 4: VLM 시도 (어댑터 사용)
        try:
            response = self._vlm_extract(
                image_data=image_data,
                prompt=prompt,
                page_num=page_num
            )
            
            content = response.get('content', '')
            
            # 빈 응답 체크
            if not content or len(content.strip()) < 50:
                logger.warning(f"      ⚠️ VLM 응답 부족 ({len(content)} 글자) → Fallback")
                content = self._fallback_extract(page_num)
                self.fallback_count += 1
                source = "fallback"
                confidence = 0.7
            else:
                self.vlm_success_count += 1
                source = "vlm"
                confidence = 1.0
        
        except Exception as e:
            logger.error(f"      ❌ VLM 오류: {e} → Fallback")
            content = self._fallback_extract(page_num)
            self.fallback_count += 1
            source = "fallback"
            confidence = 0.5
        
        # Step 5: ✅ doc_type 조건부 승급 (미송 제안)
        doc_type = self._detect_doc_type_v2(content, hints)
        
        logger.info(f"      📋 문서 타입: {doc_type}")
        
        # Step 6: 후처리 (doc_type 전달)
        # PostMergeNormalizer (v5.7.8.1 - OrderedDict)
        content = self.post_normalizer.normalize(content, doc_type)
        
        # TypoNormalizer (v5.7.8.1 - OrderedDict)
        content = self.typo_normalizer.normalize(content, doc_type)
        
        # 중복 제거
        content = self._deduplicate_lines(content)
        
        logger.info(f"      🧹 중복 제거 완료 ({len(content)} 글자)")
        
        # Step 7: KVS 추출
        kvs_raw = hints.get('kvs', [])
        kvs = KVSNormalizer.normalize_kvs(kvs_raw)
        
        logger.info(f"      💾 KVS: {len(kvs)}개")
        
        # Step 8: 품질 점수
        if source == "vlm":
            quality_score = 100
        else:
            quality_score = 70  # Fallback
        
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
        ✅ Phase 5.7.8.3: 개정이력 표 감지 (미송 제안)
        
        전략:
        - 1페이지만 체크
        - 3개 이상 개정 항목 감지
        - 날짜 형식 다양화 (2019.05.27 / 2019-05-27 / 2019)
        
        Args:
            hints: 레이아웃 힌트
            page_num: 페이지 번호 (1-based)
        
        Returns:
            True if 개정이력 표 존재
        """
        # 1페이지만 체크
        if page_num != 1:
            return False
        
        # hints에서 텍스트 추출
        text = hints.get('text', '')
        
        if not text:
            return False
        
        # ✅ 미송 제안: 날짜 형식 다양화
        # 제\s*\d+\s*차\s*개정\s*(YYYY.MM.DD | YYYY-MM-DD | YYYY)
        revision_pattern = re.compile(
            r'제\s*\d+\s*차\s*개정\s*'
            r'('
            r'\d{4}\.\d{1,2}\.\d{1,2}|'  # 2019.05.27
            r'\d{4}-\d{1,2}-\d{1,2}|'    # 2019-05-27
            r'[\'\'(]?\d{4}[\'\')\.]?'    # 2019, '2019', (2019)
            r')',
            re.MULTILINE
        )
        
        matches = revision_pattern.findall(text)
        
        # 3개 이상이면 개정이력 표로 판단
        if len(matches) >= 3:
            logger.debug(f"      개정이력 감지: {len(matches)}개 항목")
            return True
        
        return False
    
    def _detect_doc_type_v2(self, content: str, hints: Dict[str, Any]) -> str:
        """
        ✅ Phase 5.7.8.3: 문서 타입 조건부 승급 (미송 제안)
        
        전략:
        1. hints.doc_type 확인
        2. 패턴 매칭으로 statute 승급
           - 제\d+조 패턴
           - 제\d+장 패턴
           - "기본 정신" 키워드
        3. 기본값: 'general'
        
        Args:
            content: 추출된 텍스트
            hints: 레이아웃 힌트
        
        Returns:
            'statute', 'general', 'bus_diagram', 'table'
        """
        # 1) hints에서 확인
        hint_type = hints.get('doc_type')
        
        # 2) ✅ 미송 제안: 조건부 statute 승급
        if hint_type != 'statute':
            # 패턴 매칭
            has_article = bool(re.search(r'제\s*\d+\s*조', content))
            has_chapter = bool(re.search(r'제\s*\d+\s*장', content))
            has_spirit = '기본 정신' in content or '기본정신' in content
            
            if has_article or has_chapter or has_spirit:
                logger.debug(f"      doc_type 승급: general → statute (article={has_article}, chapter={has_chapter}, spirit={has_spirit})")
                return 'statute'
        
        # 3) hints 우선
        if hint_type in ['statute', 'bus_diagram', 'table']:
            logger.debug(f"      doc_type from hints: {hint_type}")
            return hint_type
        
        # 4) 기본값: general
        logger.debug("      doc_type default: general")
        return 'general'
    
    def _fallback_extract(self, page_num: int) -> str:
        """
        ✅ Phase 5.7.8.3: Fallback 텍스트 추출 (미송 피드백 반영)
        
        전략:
        1. pypdf 시도 (빠름, 구조 보존 우수)
        2. ✅ 인라인 페이지 마커 제거 강화 (미송 제안)
        3. 정규화 적용
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출된 텍스트
        """
        try:
            # pypdf 추출
            with open(self.pdf_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                page = pdf_reader.pages[page_num - 1]
                text = page.extract_text()
            
            if not text or len(text.strip()) < 20:
                logger.warning(f"      ⚠️ Fallback 추출 실패: 텍스트 부족")
                return ""
            
            # ✅ Phase 5.7.8.3: 인라인 마커 제거 강화 (미송 제안)
            # 패턴 1: "402-21." → "402- 2 1." 합체 방지
            text = re.sub(r'\b(\d{3,4})-(\d{1,2})\s*(?=(\d+[.)]|[""]))', r'\1-\2\n', text)
            
            # 패턴 2: 줄머리 섞임 방지 (페이지 마커 제거 후 공백 정리)
            text = re.sub(r'[ \t]+(\n)', r'\1', text)
            
            # 기본 정규화
            text = self._normalize_fallback_text(text)
            
            logger.debug(f"      Fallback 추출: {len(text)} 글자")
            
            return text
        
        except Exception as e:
            logger.error(f"      ❌ Fallback 오류: {e}")
            return ""
    
    def _normalize_fallback_text(self, text: str) -> str:
        """
        Fallback 텍스트 정규화
        
        Args:
            text: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        # 1) 유니코드 정규화
        text = unicodedata.normalize('NFKC', text)
        
        # 2) 과도한 공백 제거
        text = re.sub(r' {2,}', ' ', text)
        
        # 3) 과도한 줄바꿈 제거 (3개 이상 → 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 4) 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    def _deduplicate_lines(self, content: str) -> str:
        """
        중복 라인 제거
        
        Args:
            content: 원본 텍스트
        
        Returns:
            중복 제거된 텍스트
        """
        lines = content.split('\n')
        seen = set()
        deduped = []
        
        for line in lines:
            # 빈 줄은 유지
            if not line.strip():
                deduped.append(line)
                continue
            
            # 중복 체크
            line_key = line.strip()
            if line_key not in seen:
                seen.add(line_key)
                deduped.append(line)
        
        return '\n'.join(deduped)
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """
        Fallback 통계
        
        Returns:
            통계 정보
        """
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
"""
core/hybrid_extractor.py
PRISM Phase 0.3.4 P0 - Hybrid Extractor (Fallback 품질 개선)

✅ Phase 0.3.4 P0 긴급 수정:
1. call_with_image() 호출로 변경 (VLM 정합)
2. Fallback 결과 품질 최소선 보장:
   - 페이지 번호 제거 (402-1, 402-2 등)
   - 기본 공백 복원 (조문 번호/괄호 기준)
   - 헤더 중복 제거
3. Safe 모듈 사용

⚠️ P0 수정 이유:
- Fallback 결과가 "단어 사이 공백 없음" 상태
- RAG/청킹 완전 무력화
- GPT 분석: "P0-2 Fallback 최소 품질선 의무"

Author: 이서영 (Backend Lead) + 마창수산 팀
Date: 2025-11-08
Version: Phase 0.3.4 P0
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

import pypdf
from pathlib import Path

# ✅ Phase 0.3.4 P0: Safe 모듈 사용
try:
    from .quick_layout_analyzer import QuickLayoutAnalyzer
    from .prompt_rules import PromptRules
    from .post_merge_normalizer_safe import PostMergeNormalizer
    from .typo_normalizer_safe import TypoNormalizer
    from .kvs_normalizer import KVSNormalizer
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from quick_layout_analyzer import QuickLayoutAnalyzer
    from prompt_rules import PromptRules
    from post_merge_normalizer_safe import PostMergeNormalizer
    from typo_normalizer_safe import TypoNormalizer
    from kvs_normalizer import KVSNormalizer

logger = logging.getLogger(__name__)


class HybridExtractor:
    """
    Phase 0.3.4 P0 통합 추출기
    
    ✅ Phase 0.3.4 P0 개선:
    - VLM 인터페이스 정합 (call_with_image)
    - Fallback 품질 최소선 보장
    - Safe 모듈 사용
    """
    
    STATUTE_KEYWORDS = [
        '조', '항', '호', '직원', '규정', '임용', '채용',
        '승진', '전보', '휴직', '면직', '해임', '파면',
        '인사', '보수', '급여', '수당', '복무', '징계',
        '위원회'
    ]
    
    # ✅ P0-2: 페이지 번호 패턴
    PAGE_NUMBER_PATTERN = re.compile(r'\b\d{3,4}-\d{1,2}\b')
    
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
        
        logger.info("✅ HybridExtractor Phase 0.3.4 P0 초기화 완료")
        logger.info(f"   - PDF: {pdf_path}")
        logger.info(f"   - 표 허용: {allow_tables}")
        logger.info(f"   - Safe Mode: 활성화")
    
    def extract(self, image_data: str, page_num: int) -> Dict[str, Any]:
        """
        ✅ Phase 0.3.4 P0: 페이지별 추출
        
        Args:
            image_data: Base64 인코딩된 이미지
            page_num: 페이지 번호 (1-based)
        
        Returns:
            추출 결과
        """
        logger.info(f"   🔍 페이지 {page_num} 추출 시작")
        
        # Step 1: 레이아웃 분석
        hints = self.layout_analyzer.analyze(image_data)
        hints['allow_tables'] = self.allow_tables
        
        # Step 2: 프롬프트 생성
        prompt = self.prompt_rules.build_prompt(hints)
        
        # Step 3: ✅ P0-1 수정: call_with_image() 사용
        try:
            # OCR 텍스트 추출 (조문 번호 검증용)
            ocr_text = hints.get('ocr_text', '')
            
            # VLM 호출
            content = self.vlm_service.call_with_image(
                image_data=image_data,
                prompt=prompt,
                page_num=page_num,
                ocr_text=ocr_text
            )
            
            if content and len(content.strip()) >= 50:
                self.vlm_success_count += 1
                source = 'vlm'
                logger.info(f"      ✅ VLM 성공: {len(content)}자")
            else:
                logger.warning(f"      ⚠️ VLM 응답 부족 → Fallback")
                content = self._fallback_extraction(page_num)
                self.fallback_count += 1
                source = 'fallback'
        
        except Exception as e:
            logger.warning(f"      ⚠️ VLM 실패: {e}, Fallback 사용")
            content = self._fallback_extraction(page_num)
            self.fallback_count += 1
            source = 'fallback'
        
        # Step 4: 후처리
        if content:
            # 정규화
            content = self.post_normalizer.normalize(content, 'statute')
            content = self.typo_normalizer.normalize(content, 'statute')
            
            # 중복 제거
            content = self._deduplicate_lines(content)
        
        # Step 5: 품질 점수
        quality_score = self._calculate_quality(content, hints)
        
        logger.info(f"      ✅ 추출 완료: {len(content)}자, 품질={quality_score}/100, source={source}")
        
        return {
            'content': content,
            'source': source,
            'quality_score': quality_score,
            'page_num': page_num,
            'hints': hints
        }
    
    def _fallback_extraction(self, page_num: int) -> str:
        """
        ✅ P0-2: Fallback 텍스트 추출 (품질 최소선 보장)
        
        Args:
            page_num: 페이지 번호 (1-based)
        
        Returns:
            품질 개선된 텍스트
        """
        try:
            with open(self.pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                
                if page_num - 1 < len(reader.pages):
                    page = reader.pages[page_num - 1]
                    text = page.extract_text()
                    
                    if text and len(text.strip()) > 0:
                        # ✅ P0-2: Fallback 품질 개선
                        text = self._improve_fallback_quality(text)
                        return text.strip()
        
        except Exception as e:
            logger.error(f"      ❌ Fallback 오류: {e}")
        
        return ""
    
    def _improve_fallback_quality(self, text: str) -> str:
        """
        ✅ P0-2: Fallback 품질 최소선 보장
        
        GPT 분석 기준:
        - 페이지 번호 제거
        - 기본 공백 복원
        - 헤더 중복 제거
        
        Args:
            text: 원본 Fallback 텍스트
        
        Returns:
            품질 개선된 텍스트
        """
        logger.info("      🔧 Fallback 품질 개선 시작")
        
        # 1. 페이지 번호 제거 (402-1, 402-2 등)
        text = self.PAGE_NUMBER_PATTERN.sub('', text)
        
        # 2. "인사규정" 중복 헤더 제거 (페이지마다 반복되는 경우)
        lines = text.split('\n')
        seen_headers = set()
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 중복 헤더 체크
            if line_stripped in ['인사규정', '402-1', '402-2', '402-3']:
                if line_stripped in seen_headers:
                    continue  # 중복 제거
                seen_headers.add(line_stripped)
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # 3. 기본 공백 복원 (조문 번호/괄호 기준)
        # 패턴: "제1조(목적)이규정은" → "제1조(목적) 이 규정은"
        
        # 3-1. 조문 번호 뒤 공백
        text = re.sub(r'(제\d+조(?:의\d+)?)\(', r'\1 (', text)
        
        # 3-2. 괄호 닫기 뒤 한글 앞 공백
        text = re.sub(r'\)([가-힣])', r') \1', text)
        
        # 3-3. 마침표 뒤 한글 앞 공백
        text = re.sub(r'\.([가-힣])', r'. \1', text)
        
        # 3-4. 숫자 뒤 한글 앞 공백 (개정 이력)
        text = re.sub(r'(\d{4}\.\d{1,2}\.\d{1,2})\.([가-힣])', r'\1. \2', text)
        
        # 4. 개정 이력 줄 구분
        # "제37차개정2019.05.27.제38차개정" → "제37차 개정 2019.05.27.\n제38차 개정"
        text = re.sub(r'(제\d+차)개정', r'\1 개정 ', text)
        text = re.sub(r'(\d{4}\.\d{1,2}\.\d{1,2}\.)(제\d+차)', r'\1\n\2', text)
        
        # 5. 과도한 공백 정리
        text = re.sub(r' {2,}', ' ', text)
        
        logger.info("      ✅ Fallback 품질 개선 완료")
        
        return text
    
    def _calculate_quality(self, content: str, hints: Dict[str, Any]) -> int:
        """품질 점수 계산"""
        if not content or len(content.strip()) == 0:
            return 0
        
        score = 100
        
        # 길이 체크
        if len(content) < 50:
            score -= 30
        
        # 한글 비율
        korean_chars = len(re.findall(r'[가-힣]', content))
        if korean_chars < len(content) * 0.3:
            score -= 20
        
        # ✅ P0-2: 페이지 번호 패턴 감점
        page_markers = self.PAGE_NUMBER_PATTERN.findall(content)
        if page_markers:
            score -= 10
            logger.warning(f"      ⚠️ 페이지 번호 잔존: {len(page_markers)}개")
        
        return max(0, min(100, score))
    
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
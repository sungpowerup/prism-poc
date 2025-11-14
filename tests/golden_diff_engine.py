"""
golden_diff_engine.py - PRISM Phase 0.8 Golden Diff Engine
GPT 권장 3축 비교 시스템

✅ GPT 권장:
"하나의 점수로 찍기보단 세 축으로 보는 게 디버깅에 훨씬 좋아"

Level 1: 구조 비교 (장수, 조문수, 메타 존재)
Level 2: 헤더 비교 (제N조, 제목 정확도)
Level 3: 본문 비교 (정규화 후 텍스트 일치)

Author: 마창수산팀 (박준호 AI/ML Lead)
Date: 2025-11-14
Version: Phase 0.8
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import logging
import json
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ComparisonScore:
    """개별 비교 점수"""
    score: float          # 0.0 ~ 1.0
    pass_threshold: float # 통과 기준
    is_pass: bool         # 통과 여부
    details: str          # 상세 내용


@dataclass
class ComparisonReport:
    """
    ✅ GPT 권장: 3축 비교 리포트
    
    - 구조: 100%
    - 헤더: 98%
    - 본문: 95%
    
    이렇게 세 축으로 보면 "무슨 변경이 뭘 깨뜨렸는지" 한눈에
    """
    # 3축 점수
    structure_score: ComparisonScore
    header_score: ComparisonScore
    content_score: ComparisonScore
    
    # 전체 평가
    overall_pass: bool
    overall_score: float  # 가중 평균
    
    # 상세 정보
    broken_items: List[str]
    warnings: List[str]
    
    # 메타
    golden_version: str
    test_version: str
    comparison_date: str
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'structure_score': asdict(self.structure_score),
            'header_score': asdict(self.header_score),
            'content_score': asdict(self.content_score),
            'overall_pass': self.overall_pass,
            'overall_score': self.overall_score,
            'broken_items': self.broken_items,
            'warnings': self.warnings,
            'golden_version': self.golden_version,
            'test_version': self.test_version,
            'comparison_date': self.comparison_date
        }
    
    def to_json(self, filepath: str) -> None:
        """JSON 리포트 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def print_summary(self) -> None:
        """요약 출력"""
        print("\n" + "="*60)
        print("📊 Golden Diff Report (Phase 0.8)")
        print("="*60)
        print(f"Golden Version: {self.golden_version}")
        print(f"Test Version:   {self.test_version}")
        print(f"Comparison Date: {self.comparison_date}")
        print()
        print(f"Level 1 - Structure: {self.structure_score.score*100:.1f}% "
              f"({'✅ PASS' if self.structure_score.is_pass else '❌ FAIL'})")
        print(f"Level 2 - Headers:   {self.header_score.score*100:.1f}% "
              f"({'✅ PASS' if self.header_score.is_pass else '❌ FAIL'})")
        print(f"Level 3 - Content:   {self.content_score.score*100:.1f}% "
              f"({'✅ PASS' if self.content_score.is_pass else '❌ FAIL'})")
        print()
        print(f"Overall Score: {self.overall_score*100:.1f}%")
        print(f"Overall Result: {'✅ PASS' if self.overall_pass else '❌ FAIL'}")
        
        if self.broken_items:
            print("\n❌ Broken Items:")
            for item in self.broken_items:
                print(f"   - {item}")
        
        if self.warnings:
            print("\n⚠️ Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        print("="*60)


class GoldenDiffEngine:
    """
    ✅ Phase 0.8: Golden File 비교 엔진
    
    3축 비교 시스템으로 정밀 분석
    """
    
    def __init__(
        self,
        structure_threshold: float = 1.0,   # 구조는 100% 일치 요구
        header_threshold: float = 0.95,     # 헤더는 95% 이상
        content_threshold: float = 0.90      # 본문은 90% 이상
    ):
        """
        초기화
        
        Args:
            structure_threshold: 구조 비교 통과 기준
            header_threshold: 헤더 비교 통과 기준
            content_threshold: 본문 비교 통과 기준
        """
        self.structure_threshold = structure_threshold
        self.header_threshold = header_threshold
        self.content_threshold = content_threshold
        
        logger.info("✅ GoldenDiffEngine 초기화 (Phase 0.8)")
        logger.info(f"   - 구조 기준: {structure_threshold*100:.0f}%")
        logger.info(f"   - 헤더 기준: {header_threshold*100:.0f}%")
        logger.info(f"   - 본문 기준: {content_threshold*100:.0f}%")
    
    def compare(
        self,
        golden: Dict[str, Any],
        result: Dict[str, Any]
    ) -> ComparisonReport:
        """
        Golden File과 Parser 결과 비교
        
        Args:
            golden: Golden File (dict)
            result: Parser 결과 (dict)
        
        Returns:
            ComparisonReport
        """
        from datetime import datetime
        
        logger.info("🔬 Golden Diff 시작...")
        
        # Level 1: 구조 비교
        structure_score = self._compare_structure(
            golden['structure'],
            result
        )
        
        # Level 2: 헤더 비교
        header_score = self._compare_headers(
            golden['headers'],
            result
        )
        
        # Level 3: 본문 비교
        content_score = self._compare_content(
            golden['content'],
            result
        )
        
        # 전체 평가
        overall_score = (
            structure_score.score * 0.4 +
            header_score.score * 0.3 +
            content_score.score * 0.3
        )
        
        overall_pass = (
            structure_score.is_pass and
            header_score.is_pass and
            content_score.is_pass
        )
        
        # Broken items 수집
        broken_items = []
        if not structure_score.is_pass:
            broken_items.append(f"구조 불일치: {structure_score.details}")
        if not header_score.is_pass:
            broken_items.append(f"헤더 불일치: {header_score.details}")
        if not content_score.is_pass:
            broken_items.append(f"본문 불일치: {content_score.details}")
        
        # 경고 수집
        warnings = []
        if structure_score.score < 1.0:
            warnings.append("구조 변경 감지")
        if header_score.score < 0.98:
            warnings.append("헤더 변경 감지")
        
        report = ComparisonReport(
            structure_score=structure_score,
            header_score=header_score,
            content_score=content_score,
            overall_pass=overall_pass,
            overall_score=overall_score,
            broken_items=broken_items,
            warnings=warnings,
            golden_version=golden['metadata']['parser_version'],
            test_version=result.get('parser_version', 'unknown'),
            comparison_date=datetime.now().isoformat()
        )
        
        logger.info(f"✅ Golden Diff 완료:")
        logger.info(f"   - 구조: {structure_score.score*100:.1f}%")
        logger.info(f"   - 헤더: {header_score.score*100:.1f}%")
        logger.info(f"   - 본문: {content_score.score*100:.1f}%")
        logger.info(f"   - 전체: {overall_score*100:.1f}% ({'✅ PASS' if overall_pass else '❌ FAIL'})")
        
        return report
    
    def _compare_structure(
        self,
        golden_structure: Dict[str, Any],
        result: Dict[str, Any]
    ) -> ComparisonScore:
        """
        ✅ Level 1: 구조 비교
        
        장수, 조문수, 메타 존재 여부
        """
        checks = []
        details = []
        
        # 장 수
        golden_chapters = golden_structure['total_chapters']
        result_chapters = result.get('total_chapters', 0)
        if golden_chapters == result_chapters:
            checks.append(1.0)
        else:
            checks.append(0.0)
            details.append(f"장 수 불일치 (Golden: {golden_chapters}, Result: {result_chapters})")
        
        # 조문 수
        golden_articles = golden_structure['total_articles']
        result_articles = result.get('total_articles', 0)
        if golden_articles == result_articles:
            checks.append(1.0)
        else:
            checks.append(0.0)
            details.append(f"조문 수 불일치 (Golden: {golden_articles}, Result: {result_articles})")
        
        # 타이틀 존재
        has_title = golden_structure['has_title']
        result_has_title = bool(result.get('document_title'))
        if has_title == result_has_title:
            checks.append(1.0)
        else:
            checks.append(0.0)
            details.append(f"타이틀 존재 여부 불일치")
        
        # 개정이력 존재
        has_amendment = golden_structure['has_amendment_history']
        result_has_amendment = bool(result.get('amendment_history'))
        if has_amendment == result_has_amendment:
            checks.append(1.0)
        else:
            checks.append(0.0)
            details.append(f"개정이력 존재 여부 불일치")
        
        # 기본정신 존재
        has_basic = golden_structure['has_basic_spirit']
        result_has_basic = bool(result.get('basic_spirit'))
        if has_basic == result_has_basic:
            checks.append(1.0)
        else:
            checks.append(0.0)
            details.append(f"기본정신 존재 여부 불일치")
        
        score = sum(checks) / len(checks) if checks else 0.0
        is_pass = score >= self.structure_threshold
        
        return ComparisonScore(
            score=score,
            pass_threshold=self.structure_threshold,
            is_pass=is_pass,
            details="; ".join(details) if details else "모든 구조 일치"
        )
    
    def _compare_headers(
        self,
        golden_headers: Dict[str, Any],
        result: Dict[str, Any]
    ) -> ComparisonScore:
        """
        ✅ Level 2: 헤더 비교
        
        제N조, 제목, 장명 같은 헤더 문자열
        """
        checks = []
        details = []
        
        # 타이틀
        golden_title = golden_headers.get('title', '')
        result_title = result.get('document_title', '')
        if golden_title == result_title:
            checks.append(1.0)
        else:
            checks.append(0.8)  # 타이틀 불일치는 -20%
            details.append(f"타이틀 불일치 (Golden: {golden_title}, Result: {result_title})")
        
        # 장 헤더
        golden_chapter_headers = set(golden_headers.get('chapter_headers', []))
        result_chapters = result.get('chapters', [])
        result_chapter_headers = set([f"{ch.number} {ch.title}" for ch in result_chapters])
        
        if golden_chapter_headers == result_chapter_headers:
            checks.append(1.0)
        else:
            missing = golden_chapter_headers - result_chapter_headers
            extra = result_chapter_headers - golden_chapter_headers
            match_rate = len(golden_chapter_headers & result_chapter_headers) / max(len(golden_chapter_headers), 1)
            checks.append(match_rate)
            if missing:
                details.append(f"누락된 장: {missing}")
            if extra:
                details.append(f"추가된 장: {extra}")
        
        # 조문 헤더
        golden_article_headers = set(golden_headers.get('article_headers', []))
        result_articles = result.get('articles', [])
        result_article_headers = set([f"{art.number}({art.title})" for art in result_articles])
        
        if golden_article_headers == result_article_headers:
            checks.append(1.0)
        else:
            missing = golden_article_headers - result_article_headers
            extra = result_article_headers - golden_article_headers
            match_rate = len(golden_article_headers & result_article_headers) / max(len(golden_article_headers), 1)
            checks.append(match_rate)
            if missing:
                details.append(f"누락된 조문: {missing}")
            if extra:
                details.append(f"추가된 조문: {extra}")
        
        score = sum(checks) / len(checks) if checks else 0.0
        is_pass = score >= self.header_threshold
        
        return ComparisonScore(
            score=score,
            pass_threshold=self.header_threshold,
            is_pass=is_pass,
            details="; ".join(details) if details else "모든 헤더 일치"
        )
    
    def _compare_content(
        self,
        golden_content: Dict[str, Any],
        result: Dict[str, Any]
    ) -> ComparisonScore:
        """
        ✅ Level 3: 본문 비교
        
        정규화 후 텍스트 일치율
        """
        from golden_schema import normalize_text
        
        # 전체 텍스트 재구성
        result_text = result.get('document_title', '') or ""
        result_text += result.get('amendment_history', '') or ""
        result_text += result.get('basic_spirit', '') or ""
        for art in result.get('articles', []):
            result_text += f"{art.number}({art.title})\n{art.body}\n"
        
        result_normalized = normalize_text(result_text)
        golden_normalized = golden_content['normalized_text']
        
        # SequenceMatcher로 유사도 계산
        matcher = SequenceMatcher(None, golden_normalized, result_normalized)
        similarity = matcher.ratio()
        
        details = []
        if similarity < 1.0:
            # 차이 나는 부분 찾기
            opcodes = matcher.get_opcodes()
            for tag, i1, i2, j1, j2 in opcodes[:5]:  # 처음 5개만
                if tag != 'equal':
                    golden_part = golden_normalized[i1:i2]
                    result_part = result_normalized[j1:j2]
                    details.append(f"{tag}: Golden[{i1}:{i2}] vs Result[{j1}:{j2}]")
        
        is_pass = similarity >= self.content_threshold
        
        return ComparisonScore(
            score=similarity,
            pass_threshold=self.content_threshold,
            is_pass=is_pass,
            details="; ".join(details) if details else "본문 완전 일치"
        )


# ============================================
# 사용 예시
# ============================================

if __name__ == '__main__':
    print("✅ GoldenDiffEngine 정의 완료 (Phase 0.8)")
    print("   - Level 1: 구조 비교 (장수, 조문수, 메타)")
    print("   - Level 2: 헤더 비교 (제N조, 제목)")
    print("   - Level 3: 본문 비교 (정규화 후 텍스트)")

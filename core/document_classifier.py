"""
core/document_classifier.py
PRISM Phase 0.9.8.4 - 문서 타입 분류기 개선

GPT 미송님 설계 기반
목표: 타입 분류 정확도 25% → 80% 이상

개선 사항:
1. 서식(form) 우선 감지
2. 이미지 중심 문서 감지 (text density < 300)
3. 통계 문서 숫자 밀도 threshold 완화 (15% → 10%)
4. 표 구조 + 짧은 줄 비율 조합 분류
5. 조문 오감지 방지 ("제N조"보다 "서식" 우선)

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-28
Version: Phase 0.9.8.4
"""

import re
import logging
from typing import Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Phase 0.9.8.4 문서 타입 분류기
    
    GPT 미송님 개선안:
    - 우선 순위 조정 (서식 → 법령 → 이미지 → 통계)
    - 텍스트 밀도 기반 이미지 문서 감지
    - 통계 문서 기준 완화
    - 조문 오감지 방지
    """
    
    # 패턴 정의
    ARTICLE_PATTERN = re.compile(r'제\s*\d+\s*조')
    ANNEX_PATTERN = re.compile(r'별표|별지')
    FORM_PATTERN = re.compile(r'별지\s*[제]?\s*\d+\s*호\s*서식')
    
    # Phase 0.9.8.4: 개선된 Threshold
    THRESHOLDS = {
        'text_density_image': 300,      # 페이지당 300자 미만 → image_heavy
        'digit_density_stats': 0.10,    # 10% 이상 → stats_chart (기존 15% → 완화)
        'table_score_threshold': 0.50,  # 표 감지 기준
        'short_line_stats': 0.70,       # 짧은 줄 비율 70% 이상
    }
    
    def __init__(self):
        """초기화"""
        logger.info("✅ DocumentClassifier Phase 0.9.8.4 초기화")
        logger.info("   🎯 목표: 타입 분류 정확도 25% → 80% 이상")
    
    def classify(
        self,
        text: str,
        page_count: int,
        metadata: Dict[str, Any] = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        ✅ Phase 0.9.8.4: 개선된 문서 타입 분류
        
        우선 순위:
        1. 양식 문서 (서식 키워드 우선)
        2. 법령 문서 (조문 + 별표)
        3. 이미지 중심 (텍스트 밀도 극저)
        4. 통계/차트 (숫자 밀도 OR 표 구조)
        5. 일반 문서
        
        Args:
            text: 문서 텍스트
            page_count: 페이지 수
            metadata: 추가 메타데이터 (table_score 등)
        
        Returns:
            (문서타입, 신뢰도, 특징dict)
        """
        metadata = metadata or {}
        
        logger.info(f"🔍 Phase 0.9.8.4: 문서 타입 분류 시작")
        logger.info(f"   📊 텍스트: {len(text):,}자, 페이지: {page_count}개")
        
        # 특징 추출
        features = self._extract_features(text, page_count, metadata)
        
        # ============================================
        # ✅ Phase 0.9.8.4: 개선된 우선 순위 분류
        # ============================================
        
        # 1순위: 양식 문서 (서식 키워드 우선)
        if self._is_form(features):
            doc_type = 'form'
            confidence = 0.9
            reason = "서식 키워드 감지"
            logger.info(f"   🏷️ 1순위 매칭: {doc_type} ({confidence:.0%}) - {reason}")
            return doc_type, confidence, features
        
        # 2순위: 법령 문서 (조문 + 별표)
        if self._is_law_annex(features):
            doc_type = 'law_annex'
            confidence = 0.9
            reason = "조문 구조 + 별표 감지"
            logger.info(f"   🏷️ 2순위 매칭: {doc_type} ({confidence:.0%}) - {reason}")
            return doc_type, confidence, features
        
        # 3순위: 이미지 중심 (텍스트 밀도 극저)
        if self._is_image_heavy(features):
            doc_type = 'image_heavy'
            confidence = 0.8
            reason = f"텍스트 밀도 극저 ({features['avg_text_per_page']:.0f}자/페이지)"
            logger.info(f"   🏷️ 3순위 매칭: {doc_type} ({confidence:.0%}) - {reason}")
            return doc_type, confidence, features
        
        # 4순위: 통계/차트 (숫자 밀도 OR 표 구조)
        if self._is_stats_chart(features):
            doc_type = 'stats_chart'
            confidence = 0.7
            reason = self._get_stats_reason(features)
            logger.info(f"   🏷️ 4순위 매칭: {doc_type} ({confidence:.0%}) - {reason}")
            return doc_type, confidence, features
        
        # 5순위: 일반 문서
        doc_type = 'general'
        confidence = 0.5
        reason = "기본값"
        logger.info(f"   🏷️ 기본 분류: {doc_type} ({confidence:.0%}) - {reason}")
        
        return doc_type, confidence, features
    
    def _extract_features(
        self,
        text: str,
        page_count: int,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """특징 추출"""
        
        # 기본 특징
        char_count = len(text)
        avg_text_per_page = char_count / max(page_count, 1)
        
        # 패턴 감지
        has_articles = bool(self.ARTICLE_PATTERN.search(text))
        has_annex = bool(self.ANNEX_PATTERN.search(text))
        has_form_keyword = bool(self.FORM_PATTERN.search(text))
        
        # 숫자 밀도 (첫 1000자 기준)
        sample_text = text[:1000]
        if sample_text:
            digit_density = sum(c.isdigit() for c in sample_text) / len(sample_text)
        else:
            digit_density = 0.0
        
        # 라인 분석
        lines = text.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        if non_empty_lines:
            short_lines = sum(1 for line in non_empty_lines if 0 < len(line.strip()) < 50)
            short_line_ratio = short_lines / len(non_empty_lines)
        else:
            short_line_ratio = 0.0
        
        # 메타데이터에서 추가 정보
        table_score = metadata.get('table_score', 0.0)
        
        features = {
            'char_count': char_count,
            'page_count': page_count,
            'avg_text_per_page': avg_text_per_page,
            'has_articles': has_articles,
            'has_annex': has_annex,
            'has_form_keyword': has_form_keyword,
            'digit_density': round(digit_density, 3),
            'short_line_ratio': round(short_line_ratio, 2),
            'table_score': table_score,
        }
        
        logger.debug(f"   📈 특징 추출 완료:")
        logger.debug(f"      - 텍스트 밀도: {avg_text_per_page:.0f}자/페이지")
        logger.debug(f"      - 조문 구조: {has_articles}")
        logger.debug(f"      - 별표/별지: {has_annex}")
        logger.debug(f"      - 서식 키워드: {has_form_keyword}")
        logger.debug(f"      - 숫자 밀도: {digit_density:.1%}")
        logger.debug(f"      - 짧은 줄 비율: {short_line_ratio:.1%}")
        logger.debug(f"      - Table Score: {table_score:.2f}")
        
        return features
    
    def _is_form(self, features: Dict[str, Any]) -> bool:
        """
        ✅ Phase 0.9.8.4: 양식 문서 감지
        
        조건:
        - "별지 N호 서식" 키워드 존재
        - 별표/별지 키워드 존재
        """
        return features['has_form_keyword'] and features['has_annex']
    
    def _is_law_annex(self, features: Dict[str, Any]) -> bool:
        """
        ✅ Phase 0.9.8.4: 법령 문서 감지
        
        조건:
        - 조문 구조 존재 ("제N조")
        - 별표/별지 키워드 존재
        - 서식 키워드 없음 (우선 순위 분리)
        """
        return (
            features['has_articles'] and 
            features['has_annex'] and 
            not features['has_form_keyword']  # ✅ 서식 제외
        )
    
    def _is_image_heavy(self, features: Dict[str, Any]) -> bool:
        """
        ✅ Phase 0.9.8.4: 이미지 중심 문서 감지
        
        조건:
        - 페이지당 평균 텍스트 < 300자
        """
        return features['avg_text_per_page'] < self.THRESHOLDS['text_density_image']
    
    def _is_stats_chart(self, features: Dict[str, Any]) -> bool:
        """
        ✅ Phase 0.9.8.4: 통계/차트 문서 감지
        
        조건 (OR):
        - 숫자 밀도 >= 10% (기존 15% → 완화)
        - (표 감지 AND 짧은 줄 비율 >= 70%)
        """
        # 조건 1: 숫자 밀도
        digit_condition = features['digit_density'] >= self.THRESHOLDS['digit_density_stats']
        
        # 조건 2: 표 구조 + 짧은 줄
        table_condition = (
            features['table_score'] >= self.THRESHOLDS['table_score_threshold'] and
            features['short_line_ratio'] >= self.THRESHOLDS['short_line_stats']
        )
        
        return digit_condition or table_condition
    
    def _get_stats_reason(self, features: Dict[str, Any]) -> str:
        """통계/차트 분류 이유 설명"""
        reasons = []
        
        if features['digit_density'] >= self.THRESHOLDS['digit_density_stats']:
            reasons.append(f"숫자 밀도 {features['digit_density']:.1%}")
        
        if (features['table_score'] >= self.THRESHOLDS['table_score_threshold'] and
            features['short_line_ratio'] >= self.THRESHOLDS['short_line_stats']):
            reasons.append(f"표 구조 (score={features['table_score']:.2f}, short_line={features['short_line_ratio']:.0%})")
        
        return " OR ".join(reasons) if reasons else "기준 미달"


# ============================================
# 테스트/검증 함수
# ============================================

def test_classifier():
    """분류기 테스트"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    classifier = DocumentClassifier()
    
    # 테스트 케이스
    test_cases = [
        {
            'name': '조문_표 (법령)',
            'text': '제1조(목적) 이 규정은...\n별표1 임용하고자하는인원수\n1 2 3 4 5',
            'page_count': 6,
            'metadata': {'table_score': 0.80},
            'expected': 'law_annex'
        },
        {
            'name': '통계표_차트',
            'text': '2024년 정보공개 접수 현황\n2,323,664건\n중앙행정기관 983,045건',
            'page_count': 3,
            'metadata': {'table_score': 0.60},
            'expected': 'stats_chart'
        },
        {
            'name': '이미지 중심',
            'text': 'LOTTE GIMPO NIKE\nSITE MAP',
            'page_count': 6,
            'metadata': {'table_score': 0.30},
            'expected': 'image_heavy'
        },
        {
            'name': '양식 (Form)',
            'text': '[별지 제1호 서식]\n일반현황 및 연혁\n회사명:',
            'page_count': 4,
            'metadata': {'table_score': 0.50},
            'expected': 'form'
        },
    ]
    
    print("\n" + "="*60)
    print("DocumentClassifier Phase 0.9.8.4 테스트")
    print("="*60)
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}] {test['name']}")
        
        doc_type, confidence, features = classifier.classify(
            test['text'],
            test['page_count'],
            test['metadata']
        )
        
        status = "✅" if doc_type == test['expected'] else "❌"
        print(f"   {status} 결과: {doc_type} (신뢰도: {confidence:.0%})")
        print(f"      예상: {test['expected']}")
        
        if doc_type == test['expected']:
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"테스트 결과: {passed}/{len(test_cases)} 통과 ({passed/len(test_cases):.0%})")
    print(f"{'='*60}\n")
    
    return passed == len(test_cases)


if __name__ == '__main__':
    success = test_classifier()
    exit(0 if success else 1)
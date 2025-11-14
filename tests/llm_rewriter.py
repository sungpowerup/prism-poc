"""
llm_rewriter.py - PRISM Phase 0.9 LLM Rewriting Engine
GPT 권장 안전장치 3종 + Sanity Check 포함

✅ GPT 핵심 원칙:
1. 엔진 JSON은 절대 안 건드림
2. 리라이팅은 뷰 전용
3. 조문 단위 + 캐시 구조

⚠️ GPT 경고:
"의미 한 글자도 바꾸지 말 것"은 목표지, 보장은 아님
→ Sanity Check 자동 검증 필수

Author: 마창수산팀 (박준호 AI/ML Lead + GPT 피드백)
Date: 2025-11-14
Version: Phase 0.9
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RewriteValidation:
    """
    ✅ GPT 권장: Sanity Check 검증 결과
    
    "개판 난 결과를 UI로 올리는 사고는 꽤 줄일 수 있어"
    """
    is_valid: bool
    warnings: List[str]
    
    # 4가지 체크
    header_preserved: bool
    numbers_intact: bool
    legal_terms_intact: bool
    structure_preserved: bool


class LLMRewriter:
    """
    ✅ Phase 0.9: LLM 리라이팅 엔진
    
    GPT 권장 구조:
    - 조문 단위 처리
    - 캐시 구조
    - Sanity Check 자동 검증
    """
    
    # ✅ GPT 권장: 강화된 프롬프트 (금지 사항 명시)
    REWRITE_PROMPT_V2 = """당신은 법령 문서 전문가입니다. 아래 조문을 읽기 쉽게 개선하되, 다음을 엄격히 준수하세요:

✅ 필수 준수:
1. 조문 번호/제목은 절대 변경 금지 (예: "제1조(목적)")
2. 법률 용어는 원문 그대로 유지 (예: "정직", "해임", "파면", "임용", "승진")
3. 숫자/날짜/기간은 절대 변경 금지 (예: "3년", "2025.01.01", "5일")
4. 의미/내용은 한 글자도 바꾸지 말 것

❌ 절대 금지:
1. 부정문 ↔ 긍정문 변환 금지 ("~하지 아니한다" 그대로)
2. 예외 규정 강도 변경 금지 ("다만" → "하지만" 같은 변경 금지)
3. 법률 용어 순화 금지 ("해고" 같은 일반 용어로 바꾸지 말 것)
4. 조문 구조 재배치 금지 (①②③ 순서 유지)

✅ 허용되는 것 (오직 이것만):
1. 띄어쓰기만 자연스럽게 개선
2. 문장 부호 최소한 개선 (쉼표, 마침표)
3. "개정YYYY.MM.DD" 같은 메타정보는 그대로

입력 조문:
{article_text}

출력 형식 (헤더 포함):
### {article_number}({article_title})
[띄어쓰기만 개선된 본문]
"""
    
    def __init__(
        self,
        provider: str = "azure_openai",
        cache_enabled: bool = True,
        sanity_check_enabled: bool = True
    ):
        """
        초기화
        
        Args:
            provider: LLM 제공자 (azure_openai, anthropic, local)
            cache_enabled: 캐시 활성화
            sanity_check_enabled: Sanity Check 활성화
        """
        self.provider = provider
        self.cache_enabled = cache_enabled
        self.sanity_check_enabled = sanity_check_enabled
        
        # 캐시 저장소 (메모리)
        self._cache: Dict[str, str] = {}
        
        logger.info(f"✅ LLMRewriter 초기화 (Phase 0.9)")
        logger.info(f"   - Provider: {provider}")
        logger.info(f"   - Cache: {'ON' if cache_enabled else 'OFF'}")
        logger.info(f"   - Sanity Check: {'ON' if sanity_check_enabled else 'OFF'}")
    
    def rewrite_article(
        self,
        article_number: str,
        article_title: str,
        article_body: str,
        document_id: str = "default",
        parser_version: str = "0.8.0"
    ) -> Tuple[str, RewriteValidation]:
        """
        단일 조문 리라이팅
        
        Args:
            article_number: 조문 번호 (예: "제1조")
            article_title: 조문 제목 (예: "목적")
            article_body: 조문 본문
            document_id: 문서 ID (캐시 키용)
            parser_version: 파서 버전 (캐시 키용)
        
        Returns:
            (리라이팅된 텍스트, 검증 결과)
        """
        
        # ✅ GPT 권장: 조문 단위 + 캐시
        cache_key = self._generate_cache_key(
            document_id, article_number, parser_version
        )
        
        # 캐시 확인
        if self.cache_enabled and cache_key in self._cache:
            logger.info(f"💾 캐시 히트: {article_number}")
            cached_text = self._cache[cache_key]
            validation = self._validate_rewrite(
                original=article_body,
                rewritten=cached_text,
                article_number=article_number,
                article_title=article_title
            )
            return cached_text, validation
        
        # 원본 조문 전체
        original_text = f"### {article_number}({article_title})\n{article_body}"
        
        logger.info(f"✨ 리라이팅 시작: {article_number}({article_title})")
        
        # LLM 호출
        try:
            rewritten_text = self._call_llm(
                article_number=article_number,
                article_title=article_title,
                article_body=article_body
            )
            
            logger.info(f"   ✅ LLM 응답 수신 ({len(rewritten_text)}자)")
        
        except Exception as e:
            logger.error(f"   ❌ LLM 호출 실패: {e}")
            # Fallback: 원본 반환
            rewritten_text = original_text
        
        # ✅ GPT 필수: Sanity Check
        validation = self._validate_rewrite(
            original=article_body,
            rewritten=rewritten_text,
            article_number=article_number,
            article_title=article_title
        )
        
        if not validation.is_valid:
            logger.warning(f"⚠️ Sanity Check 실패: {article_number}")
            for warning in validation.warnings:
                logger.warning(f"   - {warning}")
            
            # 실패 시 원본 반환
            rewritten_text = original_text
            logger.info(f"   🔄 원본으로 폴백")
        
        # 캐시 저장
        if self.cache_enabled:
            self._cache[cache_key] = rewritten_text
        
        return rewritten_text, validation
    
    def _call_llm(
        self,
        article_number: str,
        article_title: str,
        article_body: str
    ) -> str:
        """
        LLM API 호출
        
        Provider별 구현 분기
        """
        
        prompt = self.REWRITE_PROMPT_V2.format(
            article_text=article_body,
            article_number=article_number,
            article_title=article_title
        )
        
        if self.provider == "azure_openai":
            return self._call_azure_openai(prompt)
        
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        
        elif self.provider == "local":
            return self._call_local_model(prompt)
        
        else:
            raise ValueError(f"지원하지 않는 provider: {self.provider}")
    
    def _call_azure_openai(self, prompt: str) -> str:
        """Azure OpenAI API 호출"""
        import os
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
            messages=[
                {"role": "system", "content": "당신은 법령 문서 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 낮은 온도로 일관성 확보
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_anthropic(self, prompt: str) -> str:
        """Anthropic Claude API 호출"""
        import os
        from anthropic import Anthropic
        
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text.strip()
    
    def _call_local_model(self, prompt: str) -> str:
        """로컬 모델 호출 (향후 구현)"""
        # TODO: 온프레미스 모델 연동
        raise NotImplementedError("로컬 모델은 향후 구현 예정")
    
    def _validate_rewrite(
        self,
        original: str,
        rewritten: str,
        article_number: str,
        article_title: str
    ) -> RewriteValidation:
        """
        ✅ GPT 필수: Sanity Check 자동 검증
        
        4가지 체크:
        1. 조문 헤더 보존 확인
        2. 숫자/날짜 변경 감지
        3. 법률 용어 누락 감지
        4. 조문 구조 보존 확인
        """
        
        if not self.sanity_check_enabled:
            return RewriteValidation(
                is_valid=True,
                warnings=[],
                header_preserved=True,
                numbers_intact=True,
                legal_terms_intact=True,
                structure_preserved=True
            )
        
        warnings = []
        
        # 1. 헤더 보존 확인
        expected_header = f"{article_number}({article_title})"
        header_preserved = expected_header in rewritten
        
        if not header_preserved:
            warnings.append(f"조문 헤더 누락: {expected_header}")
        
        # 2. 숫자/날짜 변경 감지
        original_numbers = set(re.findall(r'\d+(?:\.\d+)?', original))
        rewritten_numbers = set(re.findall(r'\d+(?:\.\d+)?', rewritten))
        
        numbers_intact = original_numbers == rewritten_numbers
        
        if not numbers_intact:
            missing = original_numbers - rewritten_numbers
            extra = rewritten_numbers - original_numbers
            if missing:
                warnings.append(f"숫자 누락: {missing}")
            if extra:
                warnings.append(f"숫자 추가: {extra}")
        
        # 3. 법률 용어 누락 감지
        legal_terms = [
            '정직', '해임', '파면', '임용', '승진', '전보', '겸임',
            '휴직', '복직', '면직', '강등', '징계', '채용', '결격',
            '부칙', '개정', '시행', '제정'
        ]
        
        original_legal_terms = set([
            term for term in legal_terms if term in original
        ])
        rewritten_legal_terms = set([
            term for term in legal_terms if term in rewritten
        ])
        
        legal_terms_intact = original_legal_terms.issubset(rewritten_legal_terms)
        
        if not legal_terms_intact:
            missing_terms = original_legal_terms - rewritten_legal_terms
            warnings.append(f"법률 용어 누락: {missing_terms}")
        
        # 4. 조문 구조 보존 (①②③ or 1.2.3.)
        original_clauses = len(re.findall(r'[①-⑳]|^\d+\.', original, re.MULTILINE))
        rewritten_clauses = len(re.findall(r'[①-⑳]|^\d+\.', rewritten, re.MULTILINE))
        
        structure_preserved = original_clauses == rewritten_clauses
        
        if not structure_preserved:
            warnings.append(f"항 구조 변경: {original_clauses}개 → {rewritten_clauses}개")
        
        # 최종 판정
        is_valid = (
            header_preserved and
            numbers_intact and
            legal_terms_intact and
            structure_preserved
        )
        
        return RewriteValidation(
            is_valid=is_valid,
            warnings=warnings,
            header_preserved=header_preserved,
            numbers_intact=numbers_intact,
            legal_terms_intact=legal_terms_intact,
            structure_preserved=structure_preserved
        )
    
    def _generate_cache_key(
        self,
        document_id: str,
        article_number: str,
        parser_version: str
    ) -> str:
        """
        캐시 키 생성
        
        Format: {document_id}_{article_number}_{parser_version}
        """
        key = f"{document_id}_{article_number}_{parser_version}"
        # MD5 해시로 짧게
        return hashlib.md5(key.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """캐시 통계"""
        return {
            'total_cached': len(self._cache),
            'cache_size_bytes': sum(len(v.encode('utf-8')) for v in self._cache.values())
        }
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        logger.info("🗑️ 캐시 초기화 완료")


# ============================================
# 사용 예시
# ============================================

if __name__ == '__main__':
    # LLM Rewriter 초기화
    rewriter = LLMRewriter(
        provider="azure_openai",
        cache_enabled=True,
        sanity_check_enabled=True
    )
    
    # 테스트 조문
    article_number = "제1조"
    article_title = "목적"
    article_body = "이규정은한국농어촌공사직원에게적용할인사관리의기준을정하여합리적이고적정한인사관리를기하게하는것을목적으로한다."
    
    # 리라이팅
    rewritten, validation = rewriter.rewrite_article(
        article_number=article_number,
        article_title=article_title,
        article_body=article_body,
        document_id="인사규정",
        parser_version="0.9.0"
    )
    
    print("✅ LLMRewriter 테스트 완료 (Phase 0.9)")
    print(f"   - Sanity Check: {'✅ PASS' if validation.is_valid else '❌ FAIL'}")
    print(f"   - 캐시: {rewriter.get_cache_stats()}")

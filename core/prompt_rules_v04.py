"""
Prompt Rules v0.4
Phase 0.4.0 "Quality Assurance Release"

Enhanced prompt generation with mandatory section extraction
Forces VLM to extract critical sections like "기본정신"

Author: 박준호 (AI/ML Lead)
Date: 2025-11-10
Version: 0.4.0
"""

from typing import Dict, Optional
import logging

# Version check
try:
    from .version import PRISM_VERSION, check_version
    VERSION = "0.4.0"
    check_version(__name__, VERSION)
except ImportError:
    VERSION = "0.4.0"
    print(f"⚠️ Version module not found, using VERSION={VERSION}")

logger = logging.getLogger(__name__)

# ============================================
# Prompt Rules v0.4
# ============================================

class PromptRules:
    """
    Phase 0.4.0 Prompt Rules
    
    Key improvements:
    - Mandatory extraction of critical sections
    - Enhanced for Golden Diff compatibility
    - Strict output format enforcement
    """
    
    # Critical sections that MUST be extracted
    CRITICAL_SECTIONS = [
        '기본정신',
        '기본 정신',
        '제1조',
        '개정이력'
    ]
    
    def __init__(self):
        """Initialize Prompt Rules v0.4"""
        logger.info("✅ PromptRules Phase 0.4.0 초기화")
    
    def build_prompt(
        self,
        layout_hints: Dict,
        doc_type: str = "unknown",
        allow_tables: bool = True
    ) -> str:
        """
        Build VLM prompt with Phase 0.4 enhancements
        
        Args:
            layout_hints: Layout analysis results
            doc_type: Document type (statute/form/general)
            allow_tables: Whether to allow table extraction
        
        Returns:
            Complete prompt string
        """
        
        # Base system prompt
        system_prompt = """당신은 한국어 법령·규정 문서 추출 전문가입니다.

# 핵심 원칙
1. 원본 텍스트를 100% 정확히 추출하세요
2. 추가 설명이나 해석을 절대 포함하지 마세요
3. 추출만 하고, 요약·분석·번역은 금지입니다

# 필수 추출 섹션 (Phase 0.4 강화)
다음 섹션들은 반드시 추출해야 합니다:
- "기본정신" 또는 "기본 정신" 섹션
- "제1조" (목적 조항)
- 개정이력 (있는 경우)
- 모든 조문 (제N조)

⚠️ 주의: "기본정신" 섹션이 있다면 절대 빠뜨리지 마세요!

# 출력 형식
"""
        
        # Add document type specific rules
        if doc_type == "statute":
            system_prompt += """
## 법령·규정 문서 형식

### 구조
```
# 문서 제목

## 기본정신 (있으면 반드시 포함)
내용...

## 제N장 장 제목 (있으면)

### 제N조(조 제목)
조문 내용...
```

### 조문 번호 표기
- 원본 그대로: 제1조, 제2조, 제3조의2 등
- 괄호 안 제목도 정확히 보존
"""
        
        # Add table rules if allowed
        if allow_tables and layout_hints.get('has_table'):
            system_prompt += """
### 표 처리
- 표가 명확하면 마크다운 표로 변환
- 불분명하면 텍스트로 추출
- 표 내용도 원본 그대로 유지
"""
        
        # Add final instructions
        system_prompt += """
## 금지사항
❌ 추가 설명 금지
❌ 요약 금지
❌ 분석·평가 금지
❌ 번역 금지
❌ 해석 금지

## 최종 확인
출력 전에 다음을 확인하세요:
✅ "기본정신" 섹션 포함 여부 (있으면 필수)
✅ 제1조 포함 여부
✅ 모든 조문 순서대로 포함
✅ 개정이력 포함 (있으면)
✅ 원본과 100% 일치

지금부터 이미지 속 문서를 위 규칙대로 추출하세요.
"""
        
        logger.info(f"   🎨 PromptRules Phase 0.4.0 프롬프트 생성")
        logger.info(f"      📊 문서 타입: {doc_type}")
        logger.info(f"      📋 표 허용: {allow_tables}")
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(system_prompt)} 글자)")
        logger.info(f"      ⚠️ 원문 추출 전용 모드 (해설 금지)")
        logger.info(f"      🔴 필수 섹션: {', '.join(self.CRITICAL_SECTIONS)}")
        
        return system_prompt

# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    rules = PromptRules()
    
    layout_hints = {
        'has_table': True,
        'statute_confidence': 0.8
    }
    
    prompt = rules.build_prompt(
        layout_hints=layout_hints,
        doc_type="statute",
        allow_tables=True
    )
    
    print("=" * 60)
    print("Prompt Rules v0.4 Example")
    print("=" * 60)
    print(prompt)

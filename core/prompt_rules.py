"""
core/prompt_rules.py
PRISM Phase 0.2 Hotfix - Prompt Rules with Critical Instructions

✅ Phase 0.2 긴급 수정:
1. "기본 정신" 필수 추출 규칙 추가
2. 조문 번호 정확성 CRITICAL 강조
3. 페이지 번호 오인식 방지 명시
4. 개정이력 표 추출 규칙 강화

Author: 최동현 (Frontend Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 0.2 동적 프롬프트 생성 엔진 (Critical 규칙 강화)
    
    ✅ Phase 0.2 개선:
    - "기본 정신" 필수 추출 규칙
    - 조문 번호 정확성 CRITICAL
    - 페이지 번호 오인식 방지
    - 개정이력 표 추출 강화
    """
    
    # 기본 규칙
    BASE_RULES = """이 페이지의 내용을 Markdown으로 정확히 추출하세요.

**규칙:**
1. 원본 텍스트를 정확히 추출
2. 레이아웃과 구조 보존
3. 제목/소제목을 # ## ### 사용

**절대 금지:**
- 메타 설명 ("이 이미지는", "다음과 같습니다")
- 안내 문구 ("필요하신", "말씀해 주세요")
- 요약 섹션 ("**요약:**", "**구조 요약:**")
"""
    
    # ✅ Phase 0.2: 규정 모드 기본 규칙 (CRITICAL 강화)
    STATUTE_BASE_RULES = """
[규정/법령 문서 처리]

**CRITICAL: Article Number Accuracy**
- Extract EXACT article numbers from the document
- DO NOT confuse page numbers (e.g., 402-3, 402-2) with article numbers
- Article numbers are typically in the range 1~200
- Format: 제1조, 제2조, ..., 제9조, 제10조, ...
- Format with sub-articles: 제7조의2, 제8조의3, ...
- Example page numbers to IGNORE: 402-1, 402-2, 402-3

**조항 구조 보존:**
- 제○조, 제○항, 제○호 번호 유지
- 계층 구조 유지 (# ## ### 사용)
- 삭제 조항: "삭제 <날짜>" 형태 유지

**출력 형식:**
```
### 제1조(제목)
본문 내용...

1. 항목 내용
2. 항목 내용
```

**절대 금지:**
- 조문 재배열 금지
- 요약/설명 추가 금지
- 메타 설명 금지
"""
    
    # ✅ Phase 0.2: "기본 정신" 필수 추출 규칙
    PREAMBLE_RULES = """
**CRITICAL: Preamble Extraction ("기본 정신")**

If the page contains ANY of these headers:
- "기본 정신", "기본정신"
- "제정이유", "입법취지"
- "전문", "서문"
- Text appearing BEFORE "제1장" or "제1조"

YOU MUST extract the COMPLETE paragraph(s) under these headers.

**Example:**
```
### 기본 정신
이 규정은 한국농어촌공사 직원의 보직, 승진, 신분보장, 상벌, 인사고과 등에 관한 사항을
규정함으로써 공정하고 투명한 인사관리 구현을 통하여 설립목적을 달성하고...
```

**This is ESSENTIAL content - do not skip!**
"""
    
    # ✅ Phase 0.2: 개정이력 표 추출 규칙 (강화)
    REVISION_TABLE_RULES = """
[개정 이력 표 추출]

**CRITICAL**: Extract the revision history table.

**Output as a Markdown table with these columns:**
| 차수 | 날짜 |
| --- | --- |
| 제37차 개정 | 2019.05.27 |
| 제38차 개정 | 2019.07.01 |

**Requirements:**
- Extract ALL rows (all 개정 entries)
- Keep original order
- Preserve dates in original format (YYYY.MM.DD)
- Text only - NO commentary or explanations
- If multiple tables exist, extract ONLY the first occurrence

**DO NOT:**
- Skip any 개정 rows
- Add explanations
- Change date formats
- Duplicate the table
"""
    
    # 표 금지 규칙
    TABLE_FORBIDDEN = """
[중요: 표 생성 금지]

- 이 페이지에는 표가 없습니다
- Markdown 표 (|, ---) 사용 금지
- 대신 문단과 불릿 목록으로만 작성

**올바른 예시:**
```
**항목:**
- 첫 번째: 값1
- 두 번째: 값2
```
"""
    
    # 표 허용 규칙 (일반)
    TABLE_RULES = """
[표 처리]

**표 변환:**
- 표는 Markdown 표 형식으로 변환
- 열 구분: | (파이프)
- 헤더 구분선: | --- | --- |

**예시:**
```
| 항목 | 값 |
| --- | --- |
| 이름 | 홍길동 |
```

**주의:**
- 표가 명확히 보이는 경우에만 사용
- 불확실하면 문단으로 작성
"""
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        ✅ Phase 0.2: 힌트 기반 동적 프롬프트 생성 (CRITICAL 규칙 강화)
        
        전략:
        1. OCR 텍스트 추출
        2. table_confidence 계산
        3. is_statute_mode 감지
        4. allow_tables 확인
        5. ✅ "기본 정신" 규칙 추가
        6. ✅ 조문 번호 정확성 강조
        
        Args:
            hints: QuickLayoutAnalyzer 결과
        
        Returns:
            프롬프트 문자열
        """
        logger.info("   🎨 PromptRules Phase 0.2 프롬프트 생성")
        
        # Step 1: 표 신뢰도 계산
        table_confidence = cls._calculate_table_confidence(hints)
        logger.info(f"      📊 표 신뢰도: {table_confidence}/3")
        
        # Step 2: 규정 모드 감지
        is_statute = cls._is_statute_mode(hints)
        logger.info(f"      📜 규정 모드: {is_statute}")
        
        # Step 3: 표 허용 여부
        allow_tables = hints.get('allow_tables', False)
        logger.info(f"      📋 표 허용: {allow_tables}")
        
        # Step 4: 프롬프트 조립
        prompt_parts = [cls.BASE_RULES]
        
        # 규정 모드
        if is_statute:
            prompt_parts.append(cls.STATUTE_BASE_RULES)
            
            # ✅ Phase 0.2: "기본 정신" 규칙 추가
            prompt_parts.append(cls.PREAMBLE_RULES)
        
        # 표 규칙 분기
        if is_statute and allow_tables:
            # ✅ Phase 0.2: 개정이력 - 표 허용
            logger.info("      ✅ 개정이력 - 표 허용")
            prompt_parts.append(cls.REVISION_TABLE_RULES)
        elif is_statute and not allow_tables:
            # 규정 모드 + 표 금지
            logger.info("      🚫 표 금지 (규정 모드)")
            prompt_parts.append(cls.TABLE_FORBIDDEN)
        elif table_confidence >= 2:
            # 일반 모드 + 표 감지
            prompt_parts.append(cls.TABLE_RULES)
        else:
            # 일반 모드 + 표 없음
            prompt_parts.append(cls.TABLE_FORBIDDEN)
        
        # 최종 프롬프트
        final_prompt = '\n\n'.join(prompt_parts)
        
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(final_prompt)} 글자)")
        
        return final_prompt
    
    @classmethod
    def _calculate_table_confidence(cls, hints: Dict[str, Any]) -> int:
        """
        표 신뢰도 계산 (0~3점)
        
        Args:
            hints: 레이아웃 힌트
        
        Returns:
            신뢰도 점수
        """
        score = 0
        
        # 1) 표 구조 감지
        if hints.get('has_table', False):
            score += 1
        
        # 2) 교차점 밀도
        if hints.get('intersection_count', 0) > 5:
            score += 1
        
        # 3) 선 밀도
        if hints.get('line_density', 0) > 0.01:
            score += 1
        
        return score
    
    @classmethod
    def _is_statute_mode(cls, hints: Dict[str, Any]) -> bool:
        """
        규정 모드 감지
        
        Args:
            hints: 레이아웃 힌트
        
        Returns:
            True if 규정 문서
        """
        # OCR 텍스트에서 규정 키워드 감지
        ocr_text = hints.get('ocr_text', '')
        
        statute_keywords = [
            '조', '항', '호', '직원', '규정', '임용', '채용',
            '승진', '전보', '휴직', '면직', '해임', '파면',
            '인사', '보수', '급여', '수당', '복무', '징계',
            '위원회', '법률', '제정', '개정'
        ]
        
        keyword_count = sum(1 for kw in statute_keywords if kw in ocr_text)
        
        # 키워드 5개 이상 → 규정 모드
        return keyword_count >= 5
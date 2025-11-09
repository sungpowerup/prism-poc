"""
core/prompt_rules.py
PRISM Phase 0.3.4 P1 - Prompt Rules (GPT 피드백 반영)

✅ Phase 0.3.4 P1 긴급 수정:
1. **CRITICAL: 원문만 추출, 해설/요약 절대 금지**
2. 조문 번호 정확성 강화
3. 페이지 번호 오인식 방지

⚠️ GPT 피드백 핵심:
"VLM이 '해설' 생성하는 문제 → 신뢰도 훼손"

Author: 최동현 (Frontend Lead) + 마창수산 팀
Date: 2025-11-08
Version: Phase 0.3.4 P1
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 0.3.4 P1 동적 프롬프트 생성 엔진
    
    ✅ Phase 0.3.4 P1 개선:
    - **원문 추출 전용** 프롬프트
    - 해설/요약/설명 절대 금지
    - 조문 번호 정확성 CRITICAL
    """
    
    # ✅ P1: 기본 규칙 (원문 추출 강조)
    BASE_RULES = """Extract ONLY the original text from this image.

**CRITICAL RULES:**
1. **NO explanations** - Do NOT add any explanations like "This document defines..."
2. **NO summaries** - Do NOT add any summaries
3. **NO interpretations** - Do NOT add any interpretations
4. **NO meta-commentary** - Do NOT add phrases like "The structure is...", "This section contains..."
5. **ONLY reproduce the exact text you see**

**Output Format:**
- Use Markdown headers (# ## ###) for titles
- Preserve original text exactly as shown
- Keep layout and structure

**FORBIDDEN Phrases:**
- "This document..."
- "The regulation defines..."
- "This section contains..."
- "The structure clearly shows..."
- "세부사항의 정의를 명확히 규정하고 있다"
- Any sentence that is NOT in the original image

**Examples:**

❌ BAD (Adding explanations):
"이 규정은 인사관리의 기준을 정의하고 있으며, 세부사항을 명확히 규정하고 있다."

✅ GOOD (Original text only):
"이 규정은 한국농어촌공사 직원에게 적용할 인사관리의 기준을 정하여 합리적이고 적정한 인사관리를 기하게 하는 것을 목적으로 한다."
"""
    
    # ✅ P1: 규정 모드 (원문 정확성 극대화)
    STATUTE_BASE_RULES = """
[Legal/Regulatory Document Processing]

**CRITICAL: Extract ONLY Original Text**
- Reproduce the EXACT text from the document
- DO NOT add any explanations or interpretations
- DO NOT summarize or paraphrase
- If you see text, copy it exactly

**CRITICAL: Article Number Accuracy**
- Extract EXACT article numbers from the document
- DO NOT confuse page numbers (e.g., 402-3, 402-2) with article numbers
- Article numbers are typically in the range 1~200
- Format: 제1조, 제2조, ..., 제9조, 제10조, ...
- Format with sub-articles: 제7조의2, 제8조의3, ...
- Example page numbers to IGNORE: 402-1, 402-2, 402-3

**Article Structure Preservation:**
- Keep article numbers: 제○조, 제○항, 제○호
- Maintain hierarchy with Markdown headers (# ## ###)
- Keep deleted articles: "삭제 <date>"

**Output Format:**
```markdown
### 제1조(제목)
본문 내용...

① 항목 내용
1. 세부 항목
```

**ABSOLUTELY FORBIDDEN:**
- Rearranging articles
- Adding summaries or explanations
- Adding meta-descriptions
- Generating text not in the original
"""
    
    # ✅ P1: "기본 정신" 추출 (원문 그대로)
    PREAMBLE_RULES = """
**CRITICAL: Preamble Extraction ("기본 정신")**

If the page contains ANY of these headers:
- "기본 정신", "기본정신"
- "제정이유", "입법취지"
- "전문", "서문"
- Text appearing BEFORE "제1장" or "제1조"

YOU MUST extract the COMPLETE paragraph(s) under these headers **EXACTLY AS SHOWN**.

**DO NOT:**
- Summarize the preamble
- Explain the preamble
- Add your interpretation

**DO:**
- Copy the exact text from the image
- Preserve all formatting

**Example:**
```markdown
## 기본정신
이 규정은 한국농어촌공사 직원의 보직, 승진, 신분보장, 상벌, 인사고과 등에 관한 사항을
규정함으로써 공정하고 투명한 인사관리 구현을 통하여 설립목적을 달성하고...
```
"""
    
    # ✅ P1: 개정이력 표 추출 (원문 그대로)
    REVISION_TABLE_RULES = """
[Revision History Table Extraction]

**CRITICAL**: Extract the revision history table EXACTLY AS SHOWN.

**Output as a Markdown table:**
| 차수 | 날짜 |
| --- | --- |
| 제37차 개정 | 2019.05.27 |
| 제38차 개정 | 2019.07.01 |

**Requirements:**
- Extract ALL rows (all 개정 entries)
- Keep original order
- Preserve dates in original format (YYYY.MM.DD)
- **NO commentary or explanations**
- If multiple tables exist, extract ONLY the first occurrence

**FORBIDDEN:**
- Skipping any rows
- Adding explanations like "This table shows..."
- Changing date formats
- Duplicating the table
"""
    
    # 표 금지 규칙
    TABLE_FORBIDDEN = """
[Important: No Tables]

- This page has NO tables
- Do NOT use Markdown table syntax (|, ---)
- Use paragraphs and bullet lists instead

**Correct Example:**
```markdown
**항목:**
- 첫 번째: 값1
- 두 번째: 값2
```
"""
    
    # 표 허용 규칙
    TABLE_RULES = """
[Table Processing]

**Table Conversion:**
- Convert tables to Markdown format
- Column separator: | (pipe)
- Header separator: | --- | --- |

**Example:**
```markdown
| 항목 | 값 |
| --- | --- |
| 이름 | 홍길동 |
```

**Important:**
- Only use tables if clearly visible
- When uncertain, use paragraphs instead
"""
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        ✅ P1: 원문 추출 전용 프롬프트 생성
        
        GPT 피드백 핵심:
        - "요약/해설 금지, 원문만 재현하라" 강제
        
        Args:
            hints: QuickLayoutAnalyzer 결과
        
        Returns:
            프롬프트 문자열
        """
        logger.info("   🎨 PromptRules Phase 0.3.4 P1 프롬프트 생성")
        
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
            prompt_parts.append(cls.PREAMBLE_RULES)
        
        # 표 규칙 분기
        if is_statute and allow_tables:
            logger.info("      ✅ 개정이력 - 표 허용")
            prompt_parts.append(cls.REVISION_TABLE_RULES)
        elif is_statute and not allow_tables:
            logger.info("      🚫 표 금지 (규정 모드)")
            prompt_parts.append(cls.TABLE_FORBIDDEN)
        elif table_confidence >= 2:
            prompt_parts.append(cls.TABLE_RULES)
        else:
            prompt_parts.append(cls.TABLE_FORBIDDEN)
        
        # 최종 프롬프트
        final_prompt = '\n\n'.join(prompt_parts)
        
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(final_prompt)} 글자)")
        logger.info("      ⚠️ 원문 추출 전용 모드 (해설 금지)")
        
        return final_prompt
    
    @classmethod
    def _calculate_table_confidence(cls, hints: Dict[str, Any]) -> int:
        """표 신뢰도 계산 (0~3점)"""
        score = 0
        
        if hints.get('has_table', False):
            score += 1
        
        if hints.get('intersection_count', 0) > 5:
            score += 1
        
        if hints.get('line_density', 0) > 0.01:
            score += 1
        
        return score
    
    @classmethod
    def _is_statute_mode(cls, hints: Dict[str, Any]) -> bool:
        """규정 모드 감지"""
        ocr_text = hints.get('ocr_text', '')
        
        statute_keywords = [
            '조', '항', '호', '직원', '규정', '임용', '채용',
            '승진', '전보', '휴직', '면직', '해임', '파면',
            '인사', '보수', '급여', '수당', '복무', '징계',
            '위원회', '법률', '제정', '개정'
        ]
        
        keyword_count = sum(1 for kw in statute_keywords if kw in ocr_text)
        
        return keyword_count >= 5
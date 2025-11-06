"""
core/prompt_rules.py
PRISM Phase 0 Hotfix - Prompt Rules with Revision Table Support

✅ Phase 0 긴급 수정:
1. statute 모드에서도 allow_tables=True면 표 허용
2. 명시적 형식 가이드 제공
3. 표 금지 모순 제거

Author: 최동현 (Frontend Lead) + 미송 제안
Date: 2025-11-06
Version: Phase 0 Hotfix
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 0 동적 프롬프트 생성 엔진 (개정이력 표 지원)
    
    ✅ Phase 0 개선:
    - statute 모드 + allow_tables → 표 허용 분기
    - 명시적 표 형식 가이드
    - 금지 모순 제거
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
    
    # 규정 모드 기본 규칙
    STATUTE_BASE_RULES = """
[규정/법령 문서 처리]

**조항 구조 보존:**
- 제○조, 제○항, 제○호 번호 유지
- 계층 구조 유지 (# ## ### 사용)
- 삭제 조항: "삭제 <날짜>" 형태 유지

**출력 형식:**
```
### 제○조(제목)
본문 내용...

1. 항목 내용
2. 항목 내용
```

**절대 금지:**
- 조문 재배열 금지
- 요약/설명 추가 금지
- 메타 설명 금지
"""
    
    # ✅ Phase 0: 개정이력 표 허용 규칙
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

**DO NOT:**
- Skip any 개정 rows
- Add explanations
- Change date formats
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
        ✅ Phase 0: 힌트 기반 동적 프롬프트 생성 (개정이력 지원)
        
        전략:
        1. OCR 텍스트 추출
        2. table_confidence 계산
        3. is_statute_mode 감지
        4. allow_tables 확인 (Phase 0 신규)
        5. 조건부 프롬프트 조합
        
        Args:
            hints: QuickLayoutAnalyzer 결과 + allow_tables
        
        Returns:
            최종 프롬프트
        """
        logger.info("   🎨 PromptRules Phase 0 프롬프트 생성")
        
        # 1️⃣ OCR 텍스트
        ocr_text = hints.get('ocr_text', '')
        
        # 2️⃣ table_confidence
        table_confidence = cls._calculate_table_confidence(hints, ocr_text)
        logger.info(f"      📊 표 신뢰도: {table_confidence}/3")
        
        # 3️⃣ is_statute_mode
        is_statute_mode = cls._detect_statute_mode(hints, ocr_text)
        logger.info(f"      📜 규정 모드: {is_statute_mode}")
        
        # 4️⃣ ✅ Phase 0: allow_tables 확인
        allow_tables = hints.get('allow_tables', False)
        logger.info(f"      📋 표 허용: {allow_tables}")
        
        # 5️⃣ 프롬프트 섹션 조합
        sections = []
        
        if is_statute_mode:
            # 규정 모드
            sections.append(cls.STATUTE_BASE_RULES)
            
            # ✅ Phase 0: allow_tables 분기
            if allow_tables:
                logger.info(f"      ✅ 개정이력 - 표 허용")
                sections.append(cls.REVISION_TABLE_RULES)
            else:
                logger.info(f"      🚫 표 금지 (규정 모드)")
                sections.append(cls.TABLE_FORBIDDEN)
        
        else:
            # 일반 모드
            sections.append(cls.BASE_RULES)
            
            if table_confidence >= 2:
                logger.info(f"      ✅ 표 규칙 적용")
                sections.append(cls.TABLE_RULES)
            else:
                logger.info(f"      🚫 표 금지")
                sections.append(cls.TABLE_FORBIDDEN)
        
        # 6️⃣ 최종 프롬프트
        prompt = "\n\n".join(sections)
        
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(prompt)} 글자)")
        return prompt
    
    @classmethod
    def _calculate_table_confidence(cls, hints: Dict[str, Any], ocr_text: str) -> int:
        """
        표 신뢰도 계산 (0~3)
        
        가산: CV 교차점, 선밀도, OCR 키워드
        감산: 조항 패턴, 번호 목록
        """
        score = 0
        
        # 가산 요소
        grid_intersections = hints.get('grid_intersections', 0)
        if grid_intersections > 80:
            score += 1
        
        h_v_line_density = hints.get('h_v_line_density', 0)
        if h_v_line_density > 0.02:
            score += 1
        
        table_keywords = ['단위', '사례수', '비율', '항목', '합계', '%']
        keyword_count = sum(1 for kw in table_keywords if kw in ocr_text)
        if keyword_count >= 2:
            score += 1
        
        # 감산 요소
        penalties = 0
        
        article_ratio = hints.get('article_token_ratio', 0)
        if article_ratio > 0.3:
            penalties += 1
        
        numbered_density = hints.get('numbered_list_density', 0)
        if numbered_density > 0.2:
            penalties += 1
        
        final_score = max(0, min(3, score - min(2, penalties)))
        return final_score
    
    @classmethod
    def _detect_statute_mode(cls, hints: Dict[str, Any], ocr_text: str) -> bool:
        """
        규정 모드 감지
        
        전략: 패턴 2종 이상 매칭
        """
        score = 0
        
        patterns = [
            r'제\s?\d+조',
            r'부칙',
            r'시행일',
            r'정의',
            r'목적',
            r'제\s?\d+항',
            r'\(\d+\)',
            r'개정'
        ]
        
        for pattern in patterns:
            if re.search(pattern, ocr_text):
                score += 1
        
        numbered_density = hints.get('numbered_list_density', 0)
        if numbered_density > 0.2:
            score += 1
        
        return score >= 2
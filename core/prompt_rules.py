"""
core/prompt_rules.py
PRISM Phase 5.5.0 - Prompt Rules

✅ Phase 5.5.0 핵심 개선 (GPT 보강 반영):
- 가감형 table_confidence 계산 (0~3)
- 규정/법령 모드 자동 감지 (견고)
- 표 금지 규칙 상단 배치 (ABSOLUTE RULE)
- 규정 모드 하드 게이트 (confidence >= 3만 표 허용)
- 버스 도메인 하드 게이트 유지

Author: 최동현 (Frontend Lead)
Date: 2025-10-27
Version: 5.5.0
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 5.5.0 동적 프롬프트 생성 엔진
    
    전략:
    - QuickLayoutAnalyzer 힌트 기반
    - 규정 모드 자동 감지
    - 표 신뢰도 게이트 (가감형)
    - 도메인별 프롬프트 조합
    """
    
    # ==========================================
    # ✅ Phase 5.5.0: 표 금지 절대 규칙 (상단 배치)
    # ==========================================
    
    STATUTE_ABSOLUTE_FORBID = """**ABSOLUTE RULE (규정/법령 모드):**

1. Markdown 표 (|, ---) 사용 절대 금지
2. 조문을 표로 변환 절대 금지
3. 제·항·호 계층을 # ## ### + 번호목록으로 보존

위 규칙을 반드시 준수하세요.
"""
    
    # ==========================================
    # Phase 5.5.0: 규정/법령 모드 프롬프트
    # ==========================================
    
    STATUTE_RULES = """
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
- 표 형식 (|, ---) 사용 금지
- 조문 재배열 금지
- 요약/설명 추가 금지
"""
    
    # ==========================================
    # Phase 5.0: 기본 규칙
    # ==========================================
    
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
    
    # ==========================================
    # Phase 5.3.0: 표 규칙
    # ==========================================
    
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
    
    # ==========================================
    # Phase 5.5.0: 표 금지 규칙
    # ==========================================
    
    TABLE_FORBIDDEN = """
[중요: 표 생성 금지]

- 이 페이지에는 표가 없습니다
- Markdown 표 (|, ---) 사용 금지
- 대신 문단과 불릿 목록으로만 작성

**올바른 예시:**
```
**개정 이력:**
- 제37차 개정: 2019.05.27
- 제38차 개정: 2019.07.01
```
"""
    
    # ==========================================
    # Phase 5.4.0: 버스 다이어그램 규칙
    # ==========================================
    
    BUS_DIAGRAM_RULES = """
[버스 노선도 처리]

**노선 정보 추출:**
```
## 버스 노선 정보

**노선번호:** [번호]
**운행구간:** [출발지] → [도착지]

### 경유 정류장
1. [정류장 1]
2. [정류장 2]
...
```

**운행 정보:**
- 배차간격, 첫차, 막차 등은 Key-Value로 명시

**절대 금지:**
- 경로 반복/루프 제거
- 불필요한 설명 제외
"""
    
    # ==========================================
    # Phase 5.5.0: 메인 함수
    # ==========================================
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        ✅ Phase 5.5.0: 힌트 기반 동적 프롬프트 생성
        
        전략:
        1. OCR 텍스트 추출
        2. table_confidence 계산 (가감형)
        3. is_statute_mode 감지 (견고)
        4. 규정 모드 하드 게이트
        5. 버스 도메인 하드 게이트
        
        Args:
            hints: QuickLayoutAnalyzer 결과
        
        Returns:
            최종 프롬프트
        """
        logger.info("   🎨 PromptRules v5.5.0 프롬프트 생성")
        
        # 1️⃣ OCR 텍스트 추출
        ocr_text = hints.get('ocr_text', '')
        
        # 2️⃣ table_confidence 계산 (가감형)
        table_confidence = cls._calculate_table_confidence(hints, ocr_text)
        logger.info(f"      📊 표 신뢰도: {table_confidence}/3")
        
        # 3️⃣ is_statute_mode 감지 (견고)
        is_statute_mode = cls._detect_statute_mode(hints, ocr_text)
        logger.info(f"      📜 규정 모드: {is_statute_mode}")
        
        # 4️⃣ 프롬프트 섹션 조합
        sections = []
        
        # ✅ Phase 5.5.0: 규정 모드 하드 게이트
        if is_statute_mode:
            logger.info(f"      🚫 규정 모드 활성화 - 표 금지")
            
            # 표 금지 절대 규칙 (맨 위)
            sections.append(cls.STATUTE_ABSOLUTE_FORBID)
            
            # 규정 프롬프트
            sections.append(cls.STATUTE_RULES)
            
            # ✅ 진짜 표일 때만 허용 (confidence >= 3)
            if table_confidence >= 3 and cls._looks_like_revision_table(ocr_text):
                logger.info(f"      ✅ 개정 이력 표 허용 (confidence: {table_confidence})")
                sections.append(cls.TABLE_RULES)
        
        else:
            # 일반 모드
            sections.append(cls.BASE_RULES)
            
            # ✅ Phase 5.5.0: 표 신뢰도 게이트 (>= 2)
            if table_confidence >= 2:
                logger.info(f"      ✅ 표 규칙 적용 (confidence: {table_confidence})")
                sections.append(cls.TABLE_RULES)
            else:
                logger.info(f"      🚫 표 금지 규칙 적용 (confidence: {table_confidence})")
                sections.append(cls.TABLE_FORBIDDEN)
        
        # 5️⃣ 버스 도메인 하드 게이트
        bus_keywords = hints.get('bus_keywords', [])
        has_map = hints.get('has_map', False)
        
        if has_map and len(bus_keywords) >= 2:
            logger.info(f"      🚌 버스 다이어그램 규칙 적용 (키워드: {bus_keywords})")
            sections.append(cls.BUS_DIAGRAM_RULES)
        
        # 6️⃣ 최종 프롬프트 조합
        prompt = "\n\n".join(sections)
        
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(prompt)} 글자)")
        return prompt
    
    # ==========================================
    # ✅ Phase 5.5.0: 보조 함수
    # ==========================================
    
    @classmethod
    def _calculate_table_confidence(cls, hints: Dict[str, Any], ocr_text: str) -> int:
        """
        ✅ Phase 5.5.0: 표 신뢰도 계산 (가감형 0~3)
        
        전략:
        - 가산 요소 (+1씩): CV 교차점, 선밀도, OCR 키워드
        - 감산 요소 (-1씩): 조항 패턴, 번호 목록
        
        Args:
            hints: QuickLayoutAnalyzer 결과
            ocr_text: OCR 텍스트
        
        Returns:
            표 신뢰도 (0~3)
        """
        score = 0
        
        # ✅ 가산 요소 (+1씩)
        
        # CV: 교차점 80개 이상
        grid_intersections = hints.get('grid_intersections', 0)
        if grid_intersections > 80:
            score += 1
            logger.debug(f"         [+1] 교차점 {grid_intersections}개 > 80")
        
        # CV: 선밀도 0.02 이상
        h_v_line_density = hints.get('h_v_line_density', 0)
        if h_v_line_density > 0.02:
            score += 1
            logger.debug(f"         [+1] 선밀도 {h_v_line_density:.4f} > 0.02")
        
        # OCR: 표 키워드 2개 이상
        table_keywords = ['단위', '사례수', '비율', '항목', '합계', '%']
        keyword_count = sum(1 for kw in table_keywords if kw in ocr_text)
        if keyword_count >= 2:
            score += 1
            logger.debug(f"         [+1] 표 키워드 {keyword_count}개 >= 2")
        
        # ✅ 감산 요소 (-1씩, 최대 -2)
        penalties = 0
        
        # 조항 패턴 비율 높음 (> 0.3)
        article_ratio = hints.get('article_token_ratio', 0)
        if article_ratio > 0.3:
            penalties += 1
            logger.debug(f"         [-1] 조항 비율 {article_ratio:.2f} > 0.3")
        
        # 번호 목록 밀도 높음 (> 0.2)
        numbered_density = hints.get('numbered_list_density', 0)
        if numbered_density > 0.2:
            penalties += 1
            logger.debug(f"         [-1] 번호 밀도 {numbered_density:.2f} > 0.2")
        
        # ✅ 최종 점수 (0~3)
        final_score = max(0, min(3, score - min(2, penalties)))
        
        logger.debug(f"         최종: {score}(가산) - {min(2, penalties)}(감산) = {final_score}")
        return final_score
    
    @classmethod
    def _detect_statute_mode(cls, hints: Dict[str, Any], ocr_text: str) -> bool:
        """
        ✅ Phase 5.5.0: 규정/법령 모드 감지 (견고)
        
        전략:
        - 패턴 2종 이상 매칭
        - OCR 실패 시 번호 목록 밀도로 추정
        
        Args:
            hints: QuickLayoutAnalyzer 결과
            ocr_text: OCR 텍스트
        
        Returns:
            규정 모드 여부
        """
        score = 0
        
        # ✅ 패턴 매칭 (2종 이상)
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
                logger.debug(f"         규정 키워드: '{pattern}' 매칭")
        
        # ✅ 번호 목록 밀도 가중 (> 0.2)
        numbered_density = hints.get('numbered_list_density', 0)
        if numbered_density > 0.2:
            score += 1
            logger.debug(f"         번호 밀도 가중: {numbered_density:.2f}")
        
        # ✅ 2종 이상이면 규정 모드
        is_statute = score >= 2
        logger.debug(f"         규정 모드 점수: {score} (임계: 2)")
        
        return is_statute
    
    @classmethod
    def _looks_like_revision_table(cls, ocr_text: str) -> bool:
        """
        ✅ Phase 5.5.0: 개정 이력 표 감지
        
        목적: 규정 모드에서도 개정 이력 표는 허용
        
        Args:
            ocr_text: OCR 텍스트
        
        Returns:
            개정 이력 표 여부
        """
        revision_keywords = ['개정', '차수', '차 개정', '시행일']
        keyword_count = sum(1 for kw in revision_keywords if kw in ocr_text)
        
        is_revision = keyword_count >= 2
        if is_revision:
            logger.debug(f"         개정 이력 표 감지 (키워드: {keyword_count}개)")
        
        return is_revision
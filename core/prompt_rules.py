"""
core/prompt_rules.py
PRISM Phase 5.3.1 - Prompt Rules (긴급 패치)

✅ Phase 5.3.1 수정:
1. 재추출 프롬프트 강화 (map/table/diagram 필수 조건 명시)
2. 신호 기반 검증 (길이 대신 키워드·체인 기반)
3. 표 2단 검증 (Markdown 표 또는 CSV-like)
4. 다이어그램 환각 패턴 검출

Author: 박준호 (AI/ML Lead) + GPT 제안 반영
Date: 2025-10-27
Version: 5.3.1
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 5.3.1 프롬프트 생성·검증 엔진
    
    GPT 제안 반영:
    - 재추출 프롬프트에 필수 조건 명시
    - 검증을 신호 기반으로 전환 (길이 대신 키워드)
    - 표 2단 검증 (Markdown 표 또는 CSV-like 2행↑)
    - 다이어그램 환각 패턴 검출
    """
    
    # 공통 금지 규칙
    COMMON_RULES = """
**절대 금지:**
- 메타 설명 ("이 이미지는", "아래와 같이", "다음과 같습니다")
- 안내 문구 ("필요하신", "말씀해 주세요", "재구성 가능")
- 요약 섹션 ("**요약:**", "**구조 요약:**")
- 코드 블록 중첩 (```markdown```)

**오직 원본 내용만 출력하세요.**
"""
    
    # 타입별 규칙
    TEXT_RULES = """
[텍스트 문서 규칙]
- 원본 텍스트를 정확히 추출
- 조항/항 번호 정확히 보존
- 표는 Markdown 표로 변환
"""
    
    MAP_RULES = """
[지도 규칙]
- 주요 지명 2개 이상 명시 (예: 동구청, 대왕암공원)
- 경로는 화살표(→)로 표시
- 북쪽/남쪽/동쪽/서쪽 방향 명시 (선택)
"""
    
    TABLE_RULES = """
[표 규칙]
- 헤더 1행 + 데이터 1행 이상 필수
- Markdown 표 형식 (| 헤더 | 헤더 |)
- 각 행의 파이프(|) 개수 동일
- 셀은 명확히 구분
"""
    
    DIAGRAM_RULES = """
[다이어그램 규칙]
- 흐름을 화살표(→)로 1~3개 체인으로 표현
- 체인은 최대 30 노드까지 (초과 시 "…(중간 생략)…")
- 노드는 구체적 명칭 사용
- "노선" 또는 "흐름" 단어 1개 이상 포함
"""
    
    NUMBERS_RULES = """
[숫자 데이터 규칙]
- 시간: "05:30" 형식 (HH:MM)
- 분: "27분" 형식
- 금액: "10,000원" 형식 (천단위 구분)
"""
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        CV 힌트 기반 동적 프롬프트 생성
        
        Args:
            hints: QuickLayoutAnalyzer의 힌트
                {
                    'has_text': bool,
                    'has_map': bool,
                    'has_table': bool,
                    'has_numbers': bool,
                    'diagram_count': int
                }
        
        Returns:
            DSL 기반 프롬프트
        """
        sections = ["이 문서의 내용을 Markdown으로 추출하세요.\n"]
        
        # 타입별 규칙 추가
        if hints.get('has_text'):
            sections.append(cls.TEXT_RULES)
        
        if hints.get('has_map'):
            sections.append(cls.MAP_RULES)
        
        if hints.get('has_table'):
            sections.append(cls.TABLE_RULES)
        
        if hints.get('diagram_count', 0) > 0:
            sections.append(cls.DIAGRAM_RULES)
        
        if hints.get('has_numbers'):
            sections.append(cls.NUMBERS_RULES)
        
        # 공통 금지 규칙
        sections.append(cls.COMMON_RULES)
        
        prompt = "\n".join(sections)
        logger.debug(f"   📝 DSL 프롬프트 생성: {len(prompt)} 글자")
        return prompt
    
    @classmethod
    def build_retry_prompt(
        cls,
        hints: Dict[str, Any],
        missing: List[str],
        prev_content: str
    ) -> str:
        """
        ✅ Phase 5.3.1: 재추출 프롬프트 강화 (GPT 제안)
        
        전략: 누락 요소별 필수 조건을 명시
        
        Args:
            hints: CV 힌트
            missing: 누락된 요소 리스트 (예: ['map', 'table'])
            prev_content: 이전 추출 내용
        
        Returns:
            재추출 프롬프트
        """
        focused_sections = [
            "이전 추출에서 일부 요소가 누락되었습니다.",
            "아래 [필수] 조건을 만족하는 내용을 [RETRY] 헤더 아래에 추가하세요.\n"
        ]
        
        # ✅ GPT 제안: 필수 조건 명시
        if 'map' in missing:
            focused_sections.append("""
## [RETRY] 지도 정보

[필수 조건]
- '지도', '경로', '위치', '노선도' 중 최소 1개 단어 포함
- 고유 지명(예: 동구청, 대왕암공원) 1개 이상 포함
- 경로/연결 1개 이상 언급 (화살표 → 사용)

예시:
### 주요 위치
- 북쪽: 울산대학교병원, 현대중공업
- 남쪽: 화암중학교, 금강아파트

### 경로
꽃바위 → 화암 → 한마음회관 → 동구청
""")
        
        if 'table' in missing:
            focused_sections.append("""
## [RETRY] 표 데이터

[필수 조건]
- 헤더 1행 + 데이터 1행 이상 (최소 2행)
- 각 행의 파이프(|) 개수는 동일
- 숫자 데이터는 정확히 추출

예시:
| 항목 | 값 |
|---|---|
| 총 응답자 | 35,000명 |
| 남성 | 37.4% |
""")
        
        if 'diagram' in missing:
            focused_sections.append("""
## [RETRY] 다이어그램

[필수 조건]
- 흐름을 화살표(→)로 1~3개 체인 표현
- 체인은 최대 30 노드 이내 (초과 시 "…(중간 생략)…")
- '노선' 또는 '흐름' 단어 1개 이상 포함

예시:
### 다이어그램 1
- 흐름: 꽃바위 → 화암 → 일산해수욕장 → 대왕암공원 → 꽃바위
""")
        
        # 공통 금지 규칙
        focused_sections.append(cls.COMMON_RULES)
        
        return "\n".join(focused_sections)
    
    @classmethod
    def validate_extraction(
        cls,
        content: str,
        hints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ Phase 5.3.1: 신호 기반 검증 (GPT 제안)
        
        변경:
        - 길이 기준 완화 (300 → 100)
        - 키워드·체인 기반 검증으로 전환
        - 표 2단 검증 (Markdown 표 또는 CSV-like)
        - 다이어그램 환각 패턴 검출
        
        Args:
            content: 추출된 Markdown
            hints: CV 힌트
        
        Returns:
            {
                'passed': bool,
                'scores': Dict[str, float],
                'missing': List[str],
                'warnings': List[str]
            }
        """
        scores = {}
        missing = []
        warnings = []
        
        # ✅ 1. 지도 검증 (신호 기반)
        if hints.get('has_map'):
            MAP_WORDS = ['지도', '노선도', '경로', 'route', 'path', '위치', 'location']
            has_kw = any(w in content for w in MAP_WORDS)
            has_place = bool(re.search(r'[가-힣A-Za-z]{2,10}(구|동|타운|공원|역|관|병원)', content))
            has_chain = '→' in content or '->' in content
            
            if has_kw and (has_place or has_chain):
                scores['map'] = 100
                logger.debug("   ✅ 지도 검증 통과")
            else:
                scores['map'] = 0
                missing.append('map')
                logger.warning(f"   ⚠️ 지도 검증 실패 (키워드:{has_kw}, 지명:{has_place}, 체인:{has_chain})")
        
        # ✅ 2. 표 검증 (2단: Markdown 표 또는 CSV-like)
        if hints.get('has_table'):
            # Markdown 표 검증
            md_table = bool(re.search(r'^\|.+\|\s*$', content, re.MULTILINE)) and '---' in content
            
            # CSV-like 2행 이상 검증
            csv_like = len(re.findall(r'^[^\n,]+(,|\t|\|)[^\n]+$', content, re.MULTILINE)) >= 2
            
            if md_table or csv_like:
                scores['table'] = 100
                logger.debug("   ✅ 표 검증 통과 (Markdown 또는 CSV-like)")
            else:
                scores['table'] = 0
                missing.append('table')
                logger.warning("   ⚠️ 표 검증 실패 (Markdown 표 없음)")
        
        # ✅ 3. 다이어그램 검증 + 환각 패턴 검출 (GPT 제안)
        if hints.get('diagram_count', 0) > 0:
            diagram_mentions = len(re.findall(r'다이어그램|흐름|노선', content))
            
            # 기본 검증
            if diagram_mentions >= hints['diagram_count']:
                # ✅ 환각 패턴 검출 (10회 이상 반복)
                repetition_pattern = r'(\b[가-힣A-Za-z0-9]{2,15}\b(?:\s*(?:→|->)\s*\b[가-힣A-Za-z0-9]{2,15}\b)){10,}'
                
                if re.search(repetition_pattern, content):
                    scores['diagrams'] = 0
                    missing.append('diagram_hallucination')
                    warnings.append('다이어그램 반복 패턴 감지 - 환각 의심')
                    logger.warning("   ⚠️ 다이어그램 환각 패턴 감지!")
                else:
                    scores['diagrams'] = 100
                    logger.debug("   ✅ 다이어그램 검증 통과")
            else:
                scores['diagrams'] = 0
                missing.append('diagram')
                logger.warning(f"   ⚠️ 다이어그램 누락 ({diagram_mentions}/{hints['diagram_count']})")
        
        # ✅ 4. 숫자 검증
        if hints.get('has_numbers'):
            number_patterns = [
                r'\d{1,2}:\d{2}',  # 시간
                r'\d+분',          # 분
                r'\d+원',          # 금액
                r'\d+%'            # 퍼센트
            ]
            
            found_numbers = sum(1 for pattern in number_patterns if re.search(pattern, content))
            
            if found_numbers > 0:
                scores['numbers'] = min(100, found_numbers * 33)
                logger.debug(f"   ✅ 숫자 검증: {found_numbers}개 패턴")
            else:
                scores['numbers'] = 0
                warnings.append('숫자 데이터 미발견')
        
        # 종합 판정
        passed = len(missing) == 0
        
        return {
            'passed': passed,
            'scores': scores,
            'missing': missing,
            'warnings': warnings
        }
    
    @classmethod
    def correct_typos(cls, content: str) -> str:
        """
        간단한 오탈자 교정
        
        Args:
            content: 추출된 Markdown
        
        Returns:
            교정된 Markdown
        """
        # 1. 중복 공백 제거
        content = re.sub(r' {2,}', ' ', content)
        
        # 2. 중복 줄바꿈 제거 (4개 이상 → 2개)
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # 3. 화살표 정규화
        content = re.sub(r'[-=]>', '→', content)
        
        # 4. Markdown 표 정리 (파이프 앞뒤 공백)
        content = re.sub(r'\s*\|\s*', ' | ', content)
        
        return content.strip()


# 사용 예시
if __name__ == "__main__":
    # 테스트
    hints = {
        'has_text': True,
        'has_map': True,
        'has_table': True,
        'has_numbers': True,
        'diagram_count': 2
    }
    
    prompt = PromptRules.build_prompt(hints)
    print("=== 생성된 프롬프트 ===")
    print(prompt[:500])
    
    # 검증 테스트
    test_content = """
## 지도 정보

### 주요 위치
- 북쪽: 울산대학교병원
- 남쪽: 화암중학교

### 경로
꽃바위 → 화암 → 동구청

## 표

| 항목 | 값 |
|---|---|
| 배차간격 | 27분 |

## 다이어그램

### 다이어그램 1
- 흐름: A → B → C

### 다이어그램 2
- 흐름: X → Y → Z
"""
    
    result = PromptRules.validate_extraction(test_content, hints)
    print("\n=== 검증 결과 ===")
    print(f"통과: {result['passed']}")
    print(f"점수: {result['scores']}")
    print(f"누락: {result['missing']}")
    print(f"경고: {result['warnings']}")
"""
core/prompt_rules.py
PRISM Phase 5.3.2 - Prompt Rules (도메인 가드 + 표 시리얼라이저)

✅ Phase 5.3.2 긴급 패치:
1. ✅ 도메인 가드 ('노선 흐름' 조건부 활성화)
2. ✅ 표 시리얼라이저 2단계 (Markdown 표 변환)
3. ✅ 신호 기반 검증 유지 (Phase 5.3.1)
4. ✅ 재추출 프롬프트 강화 유지

GPT 제안 100% 반영

Author: 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.3.2
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PromptRules:
    """
    Phase 5.3.2 프롬프트 생성·검증 엔진
    
    GPT 제안 100% 반영:
    - 도메인 가드: '노선 흐름' 문구 조건부 활성화
    - 표 시리얼라이저: CSV-like → Markdown 변환
    - 신호 기반 검증 (Phase 5.3.1 유지)
    - 재추출 프롬프트 강화 (Phase 5.3.1 유지)
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
- 빈 셀은 공백으로 표시
"""
    
    # ✅ 도메인 가드: 버스/지도 전용 규칙
    DIAGRAM_RULES_BUS = """
[다이어그램 규칙 - 버스/지도 문서 전용]
- 버스 노선은 "노선" 또는 "흐름" 단어 사용 가능
- 화살표(→)로 1~3개 체인 표현
- 체인은 최대 30 노드까지 (초과 시 "…(중간 생략)…")
- 노드는 구체적 명칭 사용 (정류장명)
"""
    
    # ✅ 도메인 가드: 일반 문서 규칙
    DIAGRAM_RULES_GENERAL = """
[다이어그램 규칙 - 일반 문서]
- 흐름을 화살표(→)로 표현
- 체인은 최대 10 노드까지
- "노선", "흐름" 단어 사용 금지 (버스 문서 아님)
- 대신 "프로세스", "단계", "구조" 등 사용
"""
    
    NUMBERS_RULES = """
[숫자 데이터 규칙]
- 시간: "05:30" 형식 (HH:MM)
- 분: "27분" 형식
- 금액: "10,000원" 형식 (천단위 구분)
- 백분율: "45.2%" 형식
"""
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        ✅ Phase 5.3.2: CV 힌트 기반 동적 프롬프트 (도메인 가드 적용)
        
        변경:
        - 버스/지도 문서와 일반 문서를 구분
        - '노선 흐름' 문구는 버스/지도 문서에만 허용
        
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
        
        # ✅ 도메인 가드: 지도 규칙은 has_map일 때만
        if hints.get('has_map'):
            sections.append(cls.MAP_RULES)
        
        if hints.get('has_table'):
            sections.append(cls.TABLE_RULES)
        
        # ✅ 도메인 가드: 다이어그램 규칙 선택
        if hints.get('diagram_count', 0) > 0:
            # 버스/지도 문서 판별
            is_bus_doc = hints.get('has_map') and hints.get('diagram_count') > 0
            
            if is_bus_doc:
                sections.append(cls.DIAGRAM_RULES_BUS)
                logger.debug("   📍 버스/지도 다이어그램 규칙 적용")
            else:
                sections.append(cls.DIAGRAM_RULES_GENERAL)
                logger.debug("   📍 일반 다이어그램 규칙 적용")
        
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
        ✅ Phase 5.3.2: 재추출 프롬프트 강화 (Phase 5.3.1 유지)
        
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
- 빈 셀은 공백으로 표시

예시:
| 항목 | 값 |
|---|---|
| 총 응답자 | 35,000명 |
| 남성 | 37.4% |
""")
        
        if 'diagram' in missing:
            # ✅ 도메인 가드: 버스/지도 여부 확인
            is_bus_doc = hints.get('has_map') and hints.get('diagram_count', 0) > 0
            
            if is_bus_doc:
                focused_sections.append("""
## [RETRY] 다이어그램 (버스 노선)

[필수 조건]
- 버스 노선을 화살표(→)로 1~3개 체인 표현
- 체인은 최대 30 노드 이내
- '노선' 또는 '흐름' 단어 1개 이상 포함
- 정류장명은 구체적으로 명시

예시:
### 다이어그램 1
- 노선: 꽃바위 → 화암 → 일산해수욕장 → 대왕암공원 → 꽃바위
""")
            else:
                focused_sections.append("""
## [RETRY] 다이어그램 (일반)

[필수 조건]
- 흐름을 화살표(→)로 표현 (최대 10 노드)
- "프로세스", "단계", "구조" 등 사용
- "노선", "흐름" 단어 사용 금지

예시:
### 프로세스
- 단계: 신규유입 → 지속관람 → 이탈위험
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
        ✅ Phase 5.3.2: 신호 기반 검증 (Phase 5.3.1 유지)
        
        변경:
        - 표 시리얼라이저 2단 검증 추가
        - 도메인 가드 적용 ('노선 흐름' 검증)
        
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
        
        # ✅ 2. 표 검증 (2단: Markdown 표 또는 CSV-like 또는 시리얼라이즈)
        if hints.get('has_table'):
            # 1단: Markdown 표 검증
            md_table = bool(re.search(r'^\|.+\|\s*$', content, re.MULTILINE)) and '---' in content
            
            # 2단: CSV-like 2행 이상 검증
            csv_like = len(re.findall(r'^[^\n,]+(,|\t|\|)[^\n]+$', content, re.MULTILINE)) >= 2
            
            # 3단: 단일행 플랫 테이블 시리얼라이즈
            flat_table_serialized = False
            if not md_table and not csv_like:
                # 플랫 테이블 감지 및 변환 시도
                serialized_content = cls._serialize_flat_table(content)
                if serialized_content != content:
                    content = serialized_content
                    flat_table_serialized = True
                    logger.info("   🔧 플랫 테이블 → Markdown 표 변환 성공")
            
            if md_table or csv_like or flat_table_serialized:
                scores['table'] = 100
                logger.debug("   ✅ 표 검증 통과")
            else:
                scores['table'] = 0
                missing.append('table')
                logger.warning("   ⚠️ 표 검증 실패")
        
        # ✅ 3. 다이어그램 검증 + 환각 패턴 검출 + 도메인 가드
        if hints.get('diagram_count', 0) > 0:
            # 버스/지도 문서 여부
            is_bus_doc = hints.get('has_map') and hints.get('diagram_count') > 0
            
            if is_bus_doc:
                # 버스 문서: '노선' 또는 '흐름' 허용
                diagram_mentions = len(re.findall(r'다이어그램|노선|흐름', content))
            else:
                # ✅ 도메인 가드: 일반 문서에서 '노선', '흐름' 사용 시 경고
                if '노선' in content or (re.search(r'(?<!버스\s)흐름', content)):
                    warnings.append("일반 문서에서 '노선', '흐름' 단어 사용 - 버스 템플릿 오염")
                    logger.warning("   ⚠️ 도메인 가드: 버스 템플릿 오염 감지")
                
                diagram_mentions = len(re.findall(r'다이어그램|프로세스|단계|구조', content))
            
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
    def _serialize_flat_table(cls, content: str) -> str:
        """
        ✅ Phase 5.3.2: 표 시리얼라이저 2단계 (GPT 제안)
        
        전략:
        - 단일행 플랫 테이블 감지
        - 키워드 앵커로 열 헤더 추정
        - Markdown 표로 변환
        
        Args:
            content: Markdown 내용
        
        Returns:
            변환된 Markdown (실패 시 원본)
        """
        # 플랫 테이블 패턴: "키: 값 키: 값 ..."
        flat_pattern = r'([\w가-힣]+):\s*([0-9.%원명대초]+)'
        
        matches = re.findall(flat_pattern, content)
        
        if len(matches) < 2:
            return content
        
        # Markdown 표 생성
        table_lines = [
            "| 항목 | 값 |",
            "|---|---|"
        ]
        
        for key, value in matches:
            table_lines.append(f"| {key} | {value} |")
        
        # 원본에서 플랫 테이블 부분 찾아 교체
        flat_section = re.search(
            r'((?:[\w가-힣]+:\s*[0-9.%원명대초]+\s*){2,})',
            content
        )
        
        if flat_section:
            table_md = '\n'.join(table_lines)
            content = content.replace(flat_section.group(1), table_md)
            logger.info(f"   🔧 플랫 테이블 변환: {len(matches)}개 항목")
        
        return content
    
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
    
    @classmethod
    def sanitize_domain_leak(cls, content: str, hints: Dict) -> str:
        """
        ✅ Phase 5.3.2: 도메인 가드 - 템플릿 오염 제거
        
        전략:
        - 비버스 문서에서 '노선 흐름' 문구 제거
        - 버스 문서는 허용
        
        Args:
            content: Markdown 내용
            hints: CV 힌트
        
        Returns:
            정화된 Markdown
        """
        # 버스/지도 문서면 스킵
        if hints.get('has_map') and hints.get('diagram_count', 0) > 0:
            return content
        
        # 비버스 문서: '노선 흐름' 문구 제거
        content = re.sub(r'노선\s*흐름\s*→', '단계 →', content)
        content = re.sub(r'(?<!버스\s)흐름\s*→', '프로세스 →', content)
        
        if '노선' in content or '흐름' in content:
            logger.info("   🔧 도메인 가드: 버스 템플릿 문구 제거")
        
        return content


# 사용 예시
if __name__ == "__main__":
    # 테스트
    hints = {
        'has_text': True,
        'has_map': False,  # 비버스 문서
        'has_table': True,
        'has_numbers': True,
        'diagram_count': 2
    }
    
    prompt = PromptRules.build_prompt(hints)
    print("=== 생성된 프롬프트 ===")
    print(prompt[:500])
    
    # 검증 테스트
    test_content = """
## 표

성별: 남성 45.2% 여성: 54.8% 연령대: 14~19세 11.2% 20대: 25.9%

## 다이어그램

### 다이어그램 1
- 프로세스: 신규유입 → 지속관람 → 이탈위험

### 다이어그램 2
- 단계: A → B → C
"""
    
    result = PromptRules.validate_extraction(test_content, hints)
    print("\n=== 검증 결과 ===")
    print(f"통과: {result['passed']}")
    print(f"점수: {result['scores']}")
    print(f"누락: {result['missing']}")
    print(f"경고: {result['warnings']}")
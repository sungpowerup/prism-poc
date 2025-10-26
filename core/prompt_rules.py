"""
core/prompt_rules.py
PRISM Phase 5.3.0 - Prompt DSL Rules

목적: 힌트→프롬프트 매핑을 명시적 DSL로 관리
GPT 제안 반영: 프롬프트 튜닝을 코드 변경 없이 룰만 교체
"""

import os
from typing import Dict, List, Any


class PromptRules:
    """
    프롬프트 생성 규칙 DSL
    
    GPT 피드백:
    - 문자열 조립이 아닌 dict 기반 테이블화
    - 모델이 바뀌어도 안정적
    - 룰만 교체로 프롬프트 튜닝 가능
    """
    
    # 환경 변수로 파라미터화 (GPT 제안 #3)
    MAP_MIN_LENGTH = int(os.getenv('PRISM_MAP_MIN_LENGTH', '40'))  # 50 → 40
    TABLE_MIN_ROWS = int(os.getenv('PRISM_TABLE_MIN_ROWS', '3'))
    DIAGRAM_MIN_SCORE = int(os.getenv('PRISM_DIAGRAM_MIN_SCORE', '60'))
    
    # 섹션 규칙 테이블
    SECTION_RULES = {
        "numbers": {
            "title": "## 숫자 정보",
            "priority": 3,  # 높을수록 우선
            "lines": [
                "페이지의 숫자 데이터(시간, 금액, 통계 등)를 모두 추출하세요.",
                "- 원본 포맷 유지 (예: 05:30, 27분, 35,000명)",
                "- 모든 숫자 주변의 단위·설명을 함께 추출",
                "- Key-Value 형식으로 구조화:",
                "  * 배차간격: XX분",
                "  * 첫차: XX:XX",
                "  * 막차: XX:XX"
            ],
            "format": "kvs"  # key-value-structured
        },
        
        "text": {
            "title": "## 텍스트 내용",
            "priority": 1,
            "lines": [
                "본문 텍스트를 정확히 추출하세요.",
                "- 제목은 ## 또는 ### 헤더로",
                "- 문단은 자연스럽게",
                "- 원본 순서 유지"
            ],
            "format": "markdown"
        },
        
        "table": {
            "title": "## 표 데이터",
            "priority": 2,
            "lines": [
                "표를 Markdown 표 형식으로 변환하세요.",
                "",
                "| 열1 | 열2 | 열3 |",
                "|-----|-----|-----|",
                "| 값1 | 값2 | 값3 |",
                "",
                "**규칙:**",
                "- 헤더 행 정확히 추출",
                "- 모든 셀 데이터 포함 (빈 칸도 '-'로 표시)",
                "- 숫자는 천단위 구분자 유지"
            ],
            "format": "markdown_table_strict"
        },
        
        "map": {
            "title": "## 지도 정보",
            "priority": 2,
            "lines": [
                "지도의 내용을 설명하세요.",
                "- 지역/위치명",
                "- 주요 랜드마크 (위치와 함께)",
                "- 경로 또는 연결 관계",
                "",
                "**포맷:**",
                "### 주요 위치",
                "- 북쪽: XXX, YYY",
                "- 중앙: ZZZ",
                "",
                "### 경로",
                "AAA → BBB → CCC"
            ],
            "format": "structured_description",
            "keywords": ["지역명", "랜드마크", "경로 연결"]
        },
        
        "diagram": {
            "title": "## 다이어그램 구조",
            "priority": 2,
            "lines": [
                "{count}개의 다이어그램이 있습니다. 각각 설명하세요.",
                "",
                "### 다이어그램 1",
                "- 시작점:",
                "- 흐름/연결: A → B → C",
                "- 종점:",
                "",
                "(각 다이어그램마다 반복)",
                "",
                "**중요**: 정류장/노드 이름을 정확히 추출하세요."
            ],
            "format": "structured_flow",
            "repeat_count_from_hint": "diagram_count"
        }
    }
    
    # 검증 규칙 (GPT 제안 #2: 약한 신호 대체)
    VALIDATION_KEYWORDS = {
        "numbers": {
            "patterns": [
                r'\d{1,2}:\d{2}',  # 시간 (05:30)
                r'\d+분',           # 분 단위
                r'\d+원',           # 금액
                r'\d+명',           # 인원
                r'\d+%',            # 퍼센트
                r'\d+대'            # 대수
            ],
            "units": ["분", "원", "%", "명", "대", "초", "시간"]
        },
        
        "map": {
            "keywords": [
                "지도", "노선도", "route", "map",
                "경로", "위치", "지점", "장소",
                "정류장", "station", "stop",
                "지역", "구역", "area"
            ],
            "min_length": None  # 런타임에 MAP_MIN_LENGTH 사용
        },
        
        "table": {
            "patterns": [
                r'\|.*\|.*\|',  # Markdown 표
                r'\n\|[-:]+\|'  # 구분선
            ],
            "min_rows": None  # 런타임에 TABLE_MIN_ROWS 사용
        },
        
        "diagram": {
            "keywords": [
                "다이어그램", "diagram",
                "노선", "route", "flow",
                "흐름", "연결", "구조"
            ],
            "arrow_patterns": ["→", "->", "▶", "►"]
        }
    }
    
    # 오탈자 교정 사전 (GPT 제안)
    TYPO_CORRECTIONS = {
        "일산": ["임산", "일싼"],
        "화암": ["화악", "하암"],
        "꽃바위": ["꽃비위", "꼿바위"],
        "배차간격": ["배차 간격", "배차간경"],
        # 추가 가능...
    }
    
    @classmethod
    def build_prompt(cls, hints: Dict[str, Any]) -> str:
        """
        힌트 기반 동적 프롬프트 생성
        
        Args:
            hints: QuickLayoutAnalyzer의 CV 힌트
            
        Returns:
            완전한 프롬프트 문자열
        """
        sections = []
        
        # 헤더
        sections.append("# 페이지 내용 완전 추출\n")
        
        # 복잡도 경고
        if hints.get('layout_complexity') == 'complex':
            sections.append("""
**⚠️ 복잡한 레이아웃 페이지**
모든 영역을 빠짐없이 추출하세요. 누락 시 품질이 크게 저하됩니다.
""")
        
        # 우선순위 순으로 섹션 추가
        enabled_sections = cls._get_enabled_sections(hints)
        enabled_sections.sort(key=lambda x: x['priority'], reverse=True)
        
        for section in enabled_sections:
            sections.append(cls._format_section(section, hints))
        
        # 공통 규칙
        sections.append(cls._get_common_rules())
        
        return "\n".join(sections)
    
    @classmethod
    def _get_enabled_sections(cls, hints: Dict) -> List[Dict]:
        """힌트에서 활성화된 섹션 추출"""
        enabled = []
        
        if hints.get('has_numbers'):
            enabled.append({
                **cls.SECTION_RULES['numbers'],
                'type': 'numbers'
            })
        
        if hints.get('has_text'):
            enabled.append({
                **cls.SECTION_RULES['text'],
                'type': 'text'
            })
        
        if hints.get('has_table'):
            enabled.append({
                **cls.SECTION_RULES['table'],
                'type': 'table'
            })
        
        if hints.get('has_map'):
            enabled.append({
                **cls.SECTION_RULES['map'],
                'type': 'map'
            })
        
        if hints.get('diagram_count', 0) > 0:
            enabled.append({
                **cls.SECTION_RULES['diagram'],
                'type': 'diagram'
            })
        
        return enabled
    
    @classmethod
    def _format_section(cls, section: Dict, hints: Dict) -> str:
        """섹션을 프롬프트 텍스트로 변환"""
        lines = [section['title'], ""]
        
        for line in section['lines']:
            # 동적 값 치환 (예: {count})
            if '{count}' in line:
                count = hints.get(section.get('repeat_count_from_hint'), 1)
                line = line.format(count=count)
            
            lines.append(line)
        
        lines.append("")  # 빈 줄
        return "\n".join(lines)
    
    @classmethod
    def _get_common_rules(cls) -> str:
        """공통 규칙"""
        return """
---

**🚫 절대 금지:**
- 메타 설명 ("이 페이지는...", "아래와 같이...", "다음과 같습니다")
- 추측/해석 (원본에 없는 내용)
- 요약 (모든 내용을 완전히 추출)

**✅ 필수:**
- 원본 내용만 출력
- Markdown 형식 사용
- 누락 없이 완전히 추출
- Key-Value는 명확히 구분
"""
    
    @classmethod
    def build_retry_prompt(cls, hints: Dict, missing: List[str], 
                          prev_content: str) -> str:
        """
        재추출 프롬프트 (GPT 제안: 누락 섹션만 강제)
        
        Args:
            hints: CV 힌트
            missing: 누락된 섹션 타입 리스트
            prev_content: 이전 추출 내용
            
        Returns:
            재추출 프롬프트
        """
        sections = [
            "# ♻️ 누락 요소 재추출\n",
            "**⚠️ 이전 추출에서 다음 요소가 누락되었습니다:**\n"
        ]
        
        # 누락 항목 나열
        for miss_type in missing:
            if miss_type in cls.SECTION_RULES:
                rule = cls.SECTION_RULES[miss_type]
                sections.append(f"- {rule['title']}")
        
        sections.append("\n---\n")
        
        # 누락 섹션만 추출 지시
        for miss_type in missing:
            if miss_type in cls.SECTION_RULES:
                rule = cls.SECTION_RULES[miss_type]
                sections.append(f"\n### [RETRY] {rule['title']}\n")
                sections.append(cls._format_section(rule, hints))
        
        # 기존 내용 참고 (축약)
        sections.append("\n---\n")
        sections.append("**기존 추출 내용 (참고용, 중복 금지):**\n")
        sections.append(f"```\n{prev_content[:500]}...\n```\n")
        
        # 강조
        sections.append("""
**🔴 중요:**
- 위 누락 항목만 추출
- 기존 내용 중복 금지
- 섹션 헤더 `[RETRY]` 유지
""")
        
        return "\n".join(sections)
    
    @classmethod
    def correct_typos(cls, text: str) -> str:
        """오탈자 교정"""
        for correct, typos in cls.TYPO_CORRECTIONS.items():
            for typo in typos:
                text = text.replace(typo, correct)
        return text
    
    @classmethod
    def validate_extraction(cls, content: str, hints: Dict) -> Dict:
        """
        추출 결과 검증 (GPT 제안: 강화된 검증)
        
        Returns:
            {
                'passed': bool,
                'missing': List[str],
                'scores': Dict[str, float],
                'warnings': List[str]
            }
        """
        import re
        
        missing = []
        scores = {}
        warnings = []
        
        # 1. 숫자 정보 검증
        if hints.get('has_numbers'):
            val_rule = cls.VALIDATION_KEYWORDS['numbers']
            
            found_patterns = sum(
                1 for pattern in val_rule['patterns']
                if re.search(pattern, content)
            )
            
            # 패턴 또는 단위 존재 여부
            has_units = any(unit in content for unit in val_rule['units'])
            
            if found_patterns == 0 and not has_units:
                missing.append('numbers')
                scores['numbers'] = 0
            else:
                scores['numbers'] = min(100, found_patterns * 30 + (30 if has_units else 0))
        
        # 2. 지도 검증 (GPT 제안: 파라미터화)
        if hints.get('has_map'):
            val_rule = cls.VALIDATION_KEYWORDS['map']
            min_length = cls.MAP_MIN_LENGTH  # 환경변수 사용
            
            keyword_count = sum(
                1 for kw in val_rule['keywords']
                if kw in content.lower()
            )
            
            map_section_length = 0
            for line in content.split('\n'):
                if any(kw in line.lower() for kw in ['지도', 'map', '위치']):
                    map_section_length += len(line)
            
            if keyword_count == 0:
                missing.append('map')
                scores['map'] = 0
                warnings.append("지도 키워드 미발견")
            elif map_section_length < min_length:
                missing.append('map')
                scores['map'] = 50
                warnings.append(f"지도 설명 부족 ({map_section_length}자 < {min_length}자)")
            else:
                scores['map'] = min(100, keyword_count * 25)
        
        # 3. 표 검증 (GPT 제안: 파라미터화)
        if hints.get('has_table'):
            val_rule = cls.VALIDATION_KEYWORDS['table']
            min_rows = cls.TABLE_MIN_ROWS  # 환경변수 사용
            
            table_lines = [
                line for line in content.split('\n')
                if re.match(val_rule['patterns'][0], line)
            ]
            
            if len(table_lines) < min_rows:
                missing.append('table')
                scores['table'] = (len(table_lines) / min_rows) * 100
                warnings.append(f"표 데이터 부족 ({len(table_lines)}행 < {min_rows}행)")
            else:
                scores['table'] = 100
        
        # 4. 다이어그램 검증 (GPT 제안: 탄력적)
        if hints.get('diagram_count', 0) > 0:
            val_rule = cls.VALIDATION_KEYWORDS['diagram']
            expected_count = hints['diagram_count']
            min_score = cls.DIAGRAM_MIN_SCORE  # 환경변수 사용
            
            # 1차: '다이어그램' 문자열
            diagram_mentions = content.lower().count('다이어그램')
            
            # 2차: 대체 신호 (GPT 제안)
            flow_keywords = ['노선', 'flow', '연결', '흐름', '경로']
            flow_score = sum(content.lower().count(kw) for kw in flow_keywords)
            
            # 3차: 화살표 패턴
            arrow_count = sum(
                content.count(arrow) for arrow in val_rule['arrow_patterns']
            )
            
            # 4차: 정류장명 시퀀스 (A → B → C)
            station_pattern = r'[가-힣]{2,5}\s*→\s*[가-힣]{2,5}'
            station_chains = len(re.findall(station_pattern, content))
            
            # 종합 점수 (GPT 제안)
            total_score = (
                diagram_mentions * 30 +
                min(flow_score * 10, 30) +
                min(arrow_count * 5, 20) +
                min(station_chains * 20, 20)
            )
            
            if total_score < min_score and diagram_mentions < expected_count:
                missing.append('diagram')
                scores['diagram'] = total_score
                warnings.append(
                    f"다이어그램 누락/부족 (점수: {total_score}/{min_score}, "
                    f"멘션: {diagram_mentions}/{expected_count})"
                )
            else:
                scores['diagram'] = min(100, total_score)
                if diagram_mentions < expected_count:
                    warnings.append(
                        f"다이어그램 대체 표현 사용 (점수: {total_score}, "
                        f"화살표: {arrow_count}, 연결: {station_chains})"
                    )
        
        # 5. 최소 길이 검증
        if len(content) < 100:
            missing.append('content_length')
            scores['length'] = len(content)
            warnings.append(f"내용 너무 짧음 ({len(content)}자)")
        else:
            scores['length'] = 100
        
        passed = len(missing) == 0
        
        return {
            'passed': passed,
            'missing': missing,
            'scores': scores,
            'warnings': warnings
        }

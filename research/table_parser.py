# research/table_parser.py
"""
research/table_parser.py - PRISM Phase 0.9 연구용
Annex 표 구조화 파서 (실험 코드)

⚠️ 이 파일은 연구/실험용입니다.
⚠️ core/ 제품 라인에 직접 연결하지 마세요.
⚠️ Golden Set 100% 정확도 달성 전까지 제품에 편입 금지.

역할:
- annex_table_rows 텍스트 청크 → 행 단위 구조화 실험
- Golden Set 기반 정확도 검증

Author: 마창수산팀 (박준호 AI/ML Lead)
Date: 2025-11-18
Version: Phase 0.9.0 (연구용 스켈레톤)
"""

import re
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================
# Dataclasses (CHUNK_SCHEMA 반영)
# ==============================

@dataclass
class TableOverviewChunk:
    """표 전체 설명 청크"""
    chunk_type: str
    table_id: str
    title: str
    description: str
    column_names: List[str]
    row_count: int
    metadata: Dict[str, Any]


@dataclass
class TableRowChunk:
    """행 단위 청크 - LLM이 답을 찾는 최소 단위"""
    chunk_type: str
    table_id: str
    row_index: int
    columns: Dict[str, Any]
    content: str
    metadata: Dict[str, Any]


@dataclass
class TableNoteChunk:
    """표 주석 청크"""
    chunk_type: str
    table_id: str
    note_index: int
    content: str
    note_type: str
    metadata: Dict[str, Any]


class TableParser:
    """
    Phase 0.9 - Annex 표 구조화 파서
    
    책임:
    - annex_table_rows 텍스트 청크 -> 행 단위 구조화
    - chunks.json / review.md / engine.md 생성용 데이터 반환
    
    ✅ GPT 피드백 반영:
    - 스펙/스키마/역할 범위 확정
    - 알고리즘은 Week 1~2에서 구현
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TableParser v0.9.0 초기화 완료")
    
    # ---------- public API ----------
    
    def parse_annex_table(self, annex_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        AnnexSubChunker가 만들어낸 annex_table_rows 청크를 구조화한다.
        
        Args:
            annex_chunk: {
                "content": "...",
                "metadata": {
                    "type": "annex_table_rows",
                    "table_title": "3급승진제외",
                    "section_id": "annex_1_table_1",
                    ...
                }
            }
        
        Returns:
            {
                "table_overview": TableOverviewChunk,
                "table_rows": List[TableRowChunk],
                "table_notes": List[TableNoteChunk]
            }
        """
        raw_text = annex_chunk.get("content", "")
        meta = annex_chunk.get("metadata", {})
        
        logger.info("📊 TableParser.parse_annex_table 시작")
        logger.info(f"   - section_id: {meta.get('section_id')}")
        logger.info(f"   - table_title: {meta.get('table_title')}")
        logger.info(f"   - 원본 텍스트 길이: {len(raw_text)}자")
        
        # 전처리
        cleaned = self._preprocess_text(raw_text)
        
        # 1) 숫자/범위 토큰 추출
        people_list, rank_list = self._extract_columns(cleaned)
        
        logger.info(f"   - 추출된 people: {len(people_list)}개")
        logger.info(f"   - 추출된 rank: {len(rank_list)}개")
        
        # 2) 페어링 (people ↔ rank_max)
        rows = self._pair_rows(people_list, rank_list)
        
        # 3) overview / row chunks / note chunks 생성
        table_id = f"annex1_promotion_range_{meta.get('table_title', 'unknown')}"
        overview = self._build_overview_chunk(table_id, meta, rows)
        row_chunks = self._build_row_chunks(table_id, meta, rows)
        note_chunks = self._build_note_chunks(table_id, cleaned, meta)
        
        logger.info(f"✅ TableParser.parse_annex_table 완료: rows={len(row_chunks)}, notes={len(note_chunks)}")
        
        return {
            "table_overview": overview,
            "table_rows": row_chunks,
            "table_notes": note_chunks,
        }
    
    def to_markdown_table(self, parsed: Dict[str, Any]) -> str:
        """
        파싱 결과를 마크다운 표로 변환 (review.md용)
        
        Args:
            parsed: parse_annex_table() 반환값
        
        Returns:
            마크다운 표 문자열
        """
        overview = parsed["table_overview"]
        rows = parsed["table_rows"]
        notes = parsed["table_notes"]
        
        lines = []
        
        # 제목
        lines.append(f"## {overview.title}")
        lines.append("")
        
        # 설명
        lines.append(f"> {overview.description}")
        lines.append("")
        
        # 표 헤더
        col_names = overview.column_names
        lines.append(f"| {col_names[0]} | {col_names[1]} |")
        lines.append("|------------|----------------|")
        
        # 표 본문
        for row in rows:
            people = row.columns["people"]
            rank_max = row.columns["rank_max"]
            lines.append(f"| {people} | {rank_max}번까지 |")
        
        lines.append("")
        
        # 주석
        for note in notes:
            lines.append(f"※ {note.content}")
        
        return "\n".join(lines)
    
    # ---------- 내부 단계: 전처리 ----------
    
    def _preprocess_text(self, text: str) -> str:
        """
        1) 페이지 decorative 문자 제거
        2) 불필요한 공백/중복 개행 정리
        """
        # 특수 문자 제거
        text = text.replace("", "")
        text = text.replace("\uf0d8", "")
        
        # 중복 개행 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 페이지 번호 패턴 제거 (예: 402-26)
        text = re.sub(r'\d{3}-\d{1,2}', '', text)
        
        return text
    
    # ---------- 내부 단계: 열 추출 ----------
    
    def _extract_columns(self, text: str) -> Tuple[List[int], List[int]]:
        """
        people(임용 인원수) / rank_max("n번까지") 두 열을 분리해서 추출한다.
        
        Phase 0.9.1: 2열 숫자+범위 패턴에만 집중
        
        Returns:
            people_list: [1,2,3,...,75]
            rank_list: [5,10,15,...,235]
        """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        # 숫자만 있는 라인 (임용 인원수)
        number_lines = [l for l in lines if re.fullmatch(r"\d+", l)]
        
        # "n번까지" 패턴 라인 (서열 상한)
        range_lines = [l for l in lines if re.fullmatch(r"\d+번까지", l)]
        
        # 숫자 추출
        people = []
        for x in number_lines:
            try:
                num = int(x)
                # 1~100 범위의 숫자만 people로 간주 (서열 숫자와 구분)
                if 1 <= num <= 100:
                    people.append(num)
            except ValueError:
                continue
        
        # 범위 숫자 추출
        ranks = []
        for x in range_lines:
            match = re.match(r"(\d+)", x)
            if match:
                ranks.append(int(match.group(1)))
        
        # TODO Phase 0.9 Week 2: 깨진 토큰 보정 로직
        # ex) "385번까지" → "38" + "5번까지" 분리
        # ex) Golden Set과 비교하여 자동 보정
        
        return people, ranks
    
    # ---------- 내부 단계: 행 페어링 ----------
    
    def _pair_rows(self, people_list: List[int], rank_list: List[int]) -> List[Dict[str, int]]:
        """
        people_list[i] <-> rank_list[i] 로 매핑
        
        길이 불일치 시 로깅 + 최소 길이로 처리
        """
        if len(people_list) != len(rank_list):
            logger.warning(f"⚠️ 열 길이 불일치: people={len(people_list)}, rank={len(rank_list)}")
            # TODO Phase 0.9 Week 2: 보정 로직 구현
            min_len = min(len(people_list), len(rank_list))
        else:
            min_len = len(people_list)
        
        rows = []
        for i in range(min_len):
            rows.append({
                "row_index": i + 1,
                "people": people_list[i],
                "rank_max": rank_list[i],
            })
        
        return rows
    
    # ---------- 내부 단계: 청크 생성 ----------
    
    def _build_overview_chunk(
        self, 
        table_id: str, 
        meta: Dict[str, Any], 
        rows: List[Dict[str, Any]]
    ) -> TableOverviewChunk:
        """표 전체 설명 청크 생성"""
        
        table_title = meta.get('table_title', '')
        title = f"[별표1] 임용 인원수에 대한 승진후보자 범위 ({table_title})"
        description = "이 표는 임용 인원수에 따라 승진후보자에 포함되는 서열명부 순위의 상한을 정의한 것이다."
        
        return TableOverviewChunk(
            chunk_type="table_overview",
            table_id=table_id,
            title=title,
            description=description,
            column_names=["임용 인원수", "서열명부 순위 상한"],
            row_count=len(rows),
            metadata={
                "annex_no": 1,
                "section_type": meta.get("boundary", "annex"),
                "section_id": meta.get("section_id"),
                "table_title": table_title,
                "related_article": "제20조제2항",
            },
        )
    
    def _build_row_chunks(
        self, 
        table_id: str, 
        meta: Dict[str, Any], 
        rows: List[Dict[str, Any]]
    ) -> List[TableRowChunk]:
        """행 단위 청크 생성 - LLM이 답을 찾는 최소 단위"""
        
        result = []
        table_title = meta.get("table_title", "")
        
        for r in rows:
            people = r["people"]
            rank_max = r["rank_max"]
            idx = r["row_index"]
            
            # 자연어 문장 생성
            content = f"임용 인원 {people}명일 경우 승진후보자 범위는 서열 {rank_max}번까지이다."
            
            chunk = TableRowChunk(
                chunk_type="table_row",
                table_id=table_id,
                row_index=idx,
                columns={
                    "people": people,
                    "rank_max": rank_max,
                },
                content=content,
                metadata={
                    "annex_no": 1,
                    "table_title": table_title,
                    "column_names": ["임용 인원수", "서열명부 상한"],
                },
            )
            result.append(chunk)
        
        return result
    
    def _build_note_chunks(
        self, 
        table_id: str, 
        text: str, 
        meta: Dict[str, Any]
    ) -> List[TableNoteChunk]:
        """표 주석 청크 생성"""
        
        notes: List[TableNoteChunk] = []
        
        # 계산 규칙 감지
        # "5명까지는 서열명부순위의 5배수, 5명을 초과하는 경우에는 초과인원의 3배수"
        if "3배수" in text or "5배수" in text:
            notes.append(
                TableNoteChunk(
                    chunk_type="table_note",
                    table_id=table_id,
                    note_index=1,
                    content="임용하고자하는 인원수가 5명까지는 서열명부순위의 5배수, "
                            "5명을 초과하는 경우에는 초과인원의 3배수를 심사대상에 포함.",
                    note_type="calculation_rule",
                    metadata={"annex_no": 1},
                )
            )
        
        # ※ 주석 패턴 탐지
        note_pattern = re.compile(r'※\s*(.+?)(?:\n|$)')
        for i, match in enumerate(note_pattern.finditer(text), start=len(notes) + 1):
            note_text = match.group(1).strip()
            if note_text and len(note_text) > 10:
                notes.append(
                    TableNoteChunk(
                        chunk_type="table_note",
                        table_id=table_id,
                        note_index=i,
                        content=note_text,
                        note_type="general",
                        metadata={"annex_no": 1},
                    )
                )
        
        return notes


# ==============================
# 헬퍼 함수
# ==============================

def serialize_table_chunks(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    파싱 결과를 dict로 변환 (chunks.json 저장용)
    
    Args:
        parsed: parse_annex_table() 반환값
    
    Returns:
        JSON 직렬화 가능한 dict
    """
    return {
        "table_overview": asdict(parsed["table_overview"]),
        "table_rows": [asdict(r) for r in parsed["table_rows"]],
        "table_notes": [asdict(n) for n in parsed["table_notes"]],
    }


def validate_with_golden(
    parsed_rows: List[TableRowChunk],
    golden_data: List[Dict[str, int]]
) -> Dict[str, Any]:
    """
    Golden Set과 비교하여 정확도 검증
    
    Args:
        parsed_rows: TableParser가 생성한 row chunks
        golden_data: Golden Set 데이터 [{people: 1, rank_max: 5}, ...]
    
    Returns:
        검증 결과 {accuracy: float, mismatches: [...]}
    """
    mismatches = []
    matched = 0
    
    for golden in golden_data:
        people = golden["people"]
        rank_max = golden["rank_max"]
        
        # 매칭되는 row 찾기
        found = False
        for row in parsed_rows:
            if row.columns["people"] == people:
                found = True
                if row.columns["rank_max"] == rank_max:
                    matched += 1
                else:
                    mismatches.append({
                        "people": people,
                        "expected": rank_max,
                        "actual": row.columns["rank_max"]
                    })
                break
        
        if not found:
            mismatches.append({
                "people": people,
                "expected": rank_max,
                "actual": None,
                "error": "not_found"
            })
    
    total = len(golden_data)
    accuracy = matched / total if total > 0 else 0.0
    
    return {
        "accuracy": accuracy,
        "matched": matched,
        "total": total,
        "mismatches": mismatches
    }


# ==============================
# 테스트용 메인
# ==============================

if __name__ == "__main__":
    # 테스트 데이터
    test_chunk = {
        "content": """1
2
3
4
5
5번까지
10번까지
15번까지
20번까지
25번까지
※ 임용하고자하는인원수가 5명까지는 서열명부순위의 5배수""",
        "metadata": {
            "type": "annex_table_rows",
            "table_title": "3급승진제외",
            "section_id": "annex_1_table_1"
        }
    }
    
    # 파싱 테스트
    parser = TableParser()
    result = parser.parse_annex_table(test_chunk)
    
    # 결과 출력
    print("\n=== 파싱 결과 ===")
    print(f"Overview: {result['table_overview'].title}")
    print(f"Rows: {len(result['table_rows'])}개")
    print(f"Notes: {len(result['table_notes'])}개")
    
    # 직렬화 테스트
    serialized = serialize_table_chunks(result)
    print("\n=== JSON 출력 ===")
    import json
    print(json.dumps(serialized, ensure_ascii=False, indent=2))
    
    # 마크다운 표 테스트
    print("\n=== 마크다운 표 ===")
    md_table = parser.to_markdown_table(result)
    print(md_table)
"""
core/annex_subchunker.py - PRISM Phase 0.8
Annex 서브청킹 엔진

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-11-17
Version: Phase 0.8
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SubChunk:
    """서브청크 데이터 클래스"""
    section_id: str
    section_type: str  # 'header' | 'table_rows' | 'note' | 'exception'
    content: str
    metadata: Dict
    char_count: int
    order: int  # GPT 피드백: 순서 메타데이터


class AnnexSubChunker:
    """
    Annex 서브청킹 엔진
    
    GPT 핵심 피드백 반영:
    1. Row 완벽 파싱 목표 제거 (→ Phase 0.9)
    2. 의미 단위 분리에 집중
    3. section_type 명확화
    4. order 메타데이터 추가
    """
    
    def __init__(self):
        self.patterns = {
            'header': r'\[별표\s*(\d+)\]\s*([^\n]+)',
            'related_article': r'<(제\d+조.*?)관련>',
            'amendment': r'\(개정([0-9.,\s]+)\)',
            'note_marker': r'^\*',
            'table_separator': r'^임용하고자하는인원수에대한승진후보자범위\((\d+급.*?)\)'
        }
        logger.info("✅ AnnexSubChunker 초기화 (Phase 0.8)")
    
    def chunk(self, annex_content: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청크 리스트
        
        Args:
            annex_content: Annex 원문
            annex_no: 별표 번호
        
        Returns:
            서브청크 리스트 (의미 단위 분리)
        """
        if not annex_content or len(annex_content) < 50:
            logger.warning("⚠️ Annex 내용이 너무 짧음 - 서브청킹 스킵")
            return []
        
        logger.info(f"📋 Annex 서브청킹 시작: {len(annex_content)}자")
        
        chunks = []
        order = 0
        
        # 1. Header 청크
        header_chunk = self._extract_header(annex_content, annex_no, order)
        if header_chunk:
            chunks.append(header_chunk)
            order += 1
        
        # 2. Table 영역 분리 (3급제외 / 3급승진 등)
        table_chunks = self._extract_table_sections(annex_content, annex_no, order)
        chunks.extend(table_chunks)
        order += len(table_chunks)
        
        # 3. Note 청크
        note_chunks = self._extract_notes(annex_content, annex_no, order)
        chunks.extend(note_chunks)
        
        # 4. 텍스트 손실 검증 (GPT 필수 요구사항)
        total_chars = sum(c.char_count for c in chunks)
        loss_rate = abs(total_chars - len(annex_content)) / len(annex_content)
        
        if loss_rate > 0.05:  # 5% 초과 손실
            logger.error(f"❌ 텍스트 손실 {loss_rate:.1%} - 기준 초과!")
        else:
            logger.info(f"✅ 텍스트 손실 {loss_rate:.1%} (허용 범위)")
        
        logger.info(f"✅ Annex 서브청킹 완료: {len(chunks)}개")
        self._log_chunk_types(chunks)
        
        return chunks
    
    def _extract_header(
        self, 
        text: str, 
        annex_no: str, 
        order: int
    ) -> Optional[SubChunk]:
        """헤더 청크 추출"""
        
        # [별표N] 패턴 찾기
        match = re.search(self.patterns['header'], text)
        if not match:
            return None
        
        annex_num = match.group(1)
        title = match.group(2).strip()
        
        # 관련 조문 추출
        related_article = ""
        article_match = re.search(self.patterns['related_article'], text)
        if article_match:
            related_article = article_match.group(1)
        
        # 개정이력 추출
        amendments = []
        for m in re.finditer(self.patterns['amendment'], text):
            amendments.append(m.group(1).strip())
        
        # 헤더 영역 텍스트 (첫 100자 정도)
        header_text = text[:min(200, len(text))]
        header_text = re.sub(r'\n+', '\n', header_text)
        
        return SubChunk(
            section_id=f"annex_{annex_no}_header",
            section_type="header",
            content=header_text,
            metadata={
                "annex_no": annex_num,
                "title": title,
                "related_article": related_article,
                "amendments": amendments
            },
            char_count=len(header_text),
            order=order
        )
    
    def _extract_table_sections(
        self, 
        text: str, 
        annex_no: str, 
        start_order: int
    ) -> List[SubChunk]:
        """
        Table 섹션 분리
        
        GPT 피드백: Row별 파싱이 아닌 "섹션 분리"
        예: 3급제외, 3급승진
        """
        chunks = []
        order = start_order
        
        # 표 구분 패턴 찾기
        separators = list(re.finditer(
            self.patterns['table_separator'], 
            text, 
            re.MULTILINE
        ))
        
        if not separators:
            # 구분자 없으면 전체를 하나의 테이블로
            table_text = self._extract_table_body(text)
            if table_text:
                chunks.append(SubChunk(
                    section_id=f"annex_{annex_no}_table_main",
                    section_type="table_rows",
                    content=table_text,
                    metadata={
                        "table_title": "main",
                        "row_count_estimate": self._estimate_row_count(table_text)
                    },
                    char_count=len(table_text),
                    order=order
                ))
            return chunks
        
        # 구분자 기준으로 섹션 분리
        for i, sep_match in enumerate(separators):
            section_title = sep_match.group(1)
            
            # 섹션 시작/끝 위치
            start_pos = sep_match.start()
            end_pos = (separators[i+1].start() 
                      if i+1 < len(separators) 
                      else len(text))
            
            section_text = text[start_pos:end_pos]
            
            # Note 분리
            section_text_no_notes = re.sub(
                r'^\*.*$', 
                '', 
                section_text, 
                flags=re.MULTILINE
            )
            
            if len(section_text_no_notes.strip()) > 20:
                chunks.append(SubChunk(
                    section_id=f"annex_{annex_no}_table_{i+1}",
                    section_type="table_rows",
                    content=section_text_no_notes.strip(),
                    metadata={
                        "table_title": section_title,
                        "row_count_estimate": self._estimate_row_count(section_text_no_notes)
                    },
                    char_count=len(section_text_no_notes.strip()),
                    order=order
                ))
                order += 1
        
        return chunks
    
    def _extract_table_body(self, text: str) -> str:
        """표 본문 영역 추출 (헤더 제외)"""
        
        # 첫 번째 숫자 행이 시작되는 지점부터
        lines = text.split('\n')
        table_start = 0
        
        for i, line in enumerate(lines):
            if re.match(r'^\d+\s', line):
                table_start = i
                break
        
        if table_start == 0:
            return ""
        
        # Note 시작 전까지
        table_lines = []
        for line in lines[table_start:]:
            if line.startswith('*'):
                break
            if line.strip():
                table_lines.append(line)
        
        return '\n'.join(table_lines)
    
    def _extract_notes(
        self, 
        text: str, 
        annex_no: str, 
        start_order: int
    ) -> List[SubChunk]:
        """Note 청크 추출 (* 시작)"""
        
        chunks = []
        order = start_order
        
        # * 시작하는 모든 줄
        note_lines = []
        for line in text.split('\n'):
            if line.strip().startswith('*'):
                note_lines.append(line.strip())
        
        # 각 Note를 개별 청크로
        for i, note in enumerate(note_lines):
            # 노이즈 제거 (GPT 요구사항)
            note_clean = self._clean_note(note)
            
            chunks.append(SubChunk(
                section_id=f"annex_{annex_no}_note_{i+1}",
                section_type="note",
                content=note_clean,
                metadata={
                    "note_type": self._classify_note(note_clean)
                },
                char_count=len(note_clean),
                order=order
            ))
            order += 1
        
        return chunks
    
    def _clean_note(self, note: str) -> str:
        """
        Note 노이즈 제거
        
        GPT 요구사항: 꾸밈선, 장식 문자 제거
        """
        # 연속된 특수문자 제거 (─, ═, ━ 등)
        note = re.sub(r'[─═━]{2,}', '', note)
        
        # 연속 공백 정리
        note = re.sub(r'\s{2,}', ' ', note)
        
        return note.strip()
    
    def _classify_note(self, note: str) -> str:
        """Note 유형 분류"""
        note_lower = note.lower()
        
        if '예외' in note or '단,' in note or '다만' in note:
            return "exception"
        elif '포함' in note or '범위' in note:
            return "rule"
        else:
            return "general"
    
    def _estimate_row_count(self, text: str) -> int:
        """Row 개수 추정 (완벽한 파싱 아님)"""
        # 숫자로 시작하는 줄 개수
        lines = text.split('\n')
        count = sum(1 for line in lines if re.match(r'^\d+\s', line))
        return count
    
    def _log_chunk_types(self, chunks: List[SubChunk]):
        """청크 타입 통계 로깅"""
        type_counts = {}
        for chunk in chunks:
            type_counts[chunk.section_type] = type_counts.get(chunk.section_type, 0) + 1
        
        logger.info(f"   📊 청크 타입 분포:")
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"      - {ctype}: {count}개")


# ============================================
# 유틸리티
# ============================================

def validate_subchunks(chunks: List[SubChunk], original_length: int) -> Dict:
    """
    서브청크 검증 (GPT 필수 요구사항)
    
    Returns:
        검증 결과 딕셔너리
    """
    total_chars = sum(c.char_count for c in chunks)
    loss_rate = abs(total_chars - original_length) / original_length
    
    type_counts = {}
    for chunk in chunks:
        type_counts[chunk.section_type] = type_counts.get(chunk.section_type, 0) + 1
    
    # GPT 요구: 의미 단위 검증
    has_header = 'header' in type_counts
    has_table = 'table_rows' in type_counts
    has_note = 'note' in type_counts
    has_multiple_types = len(type_counts) >= 2
    
    is_valid = (
        loss_rate < 0.05 and
        has_multiple_types and
        len(chunks) >= 3
    )
    
    return {
        'is_valid': is_valid,
        'loss_rate': loss_rate,
        'chunk_count': len(chunks),
        'type_counts': type_counts,
        'has_header': has_header,
        'has_table': has_table,
        'has_note': has_note
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 간단 테스트
    sample = """
[별표 1] 승진후보자범위(3급승진제외)
<제20조제2항관련>(개정2003.3.29)

1 5번까지
2 10번까지
*임용하고자하는인원수가5명까지는서열명부순위의5배수
"""
    
    chunker = AnnexSubChunker()
    chunks = chunker.chunk(sample)
    
    print(f"\n✅ 청크 {len(chunks)}개 생성")
    for c in chunks:
        print(f"   - {c.section_type}: {c.char_count}자")

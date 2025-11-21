# annex_subchunker.py - Phase 0.9.2
#
# Phase 0.9.2 수정사항:
# - ✅ Private Use Area 문자 제거 강화 (U+F000~U+F8FF)
# - ✅ Box drawing 문자 제거 강화

"""
annex_subchunker.py - PRISM Annex SubChunker

Annex 섹션을 의미 단위로 분할

Author: 마창수산팀
Date: 2025-11-20  
Version: Phase 0.9.2
"""

import re
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SubChunk:
    """서브청크 데이터 클래스"""
    section_id: str
    section_type: str
    content: str
    metadata: Dict[str, Any]
    char_count: int
    order: int


class AnnexSubChunker:
    """
    Annex 서브청킹
    
    Phase 0.9.2:
    - ✅ 노이즈 문자 제거 강화
    """
    
    def __init__(self):
        """초기화"""
        
        self.patterns = {
            'header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'table_separator': r'^([①-⑳■▪●◆◇]?\s*[가-힣\s]+(?:명칭|급별|범위|대상|구분))',
            'note': r'^\*\s*(.+)$'
        }
        
        logger.info("✅ AnnexSubChunker v0.9.2 초기화 (Noise Removal Enhanced)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청크 변환
        """
        logger.info(f"🔧 Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Phase 0.9.2: 노이즈 제거 강화
        cleaned_content = self._clean_annex_text(annex_text)
        
        chunks = []
        order = 0
        
        # 1. Header 청크
        header_chunk = self._extract_header(cleaned_content, annex_no, order)
        if header_chunk:
            chunks.append(header_chunk)
            order += 1
        
        # 2. Table 영역 분리 (3급제외 / 3급승진 등)
        table_chunks = self._extract_table_sections(cleaned_content, annex_no, order)
        chunks.extend(table_chunks)
        order += len(table_chunks)
        
        # 3. Note 청크
        note_chunks = self._extract_notes(cleaned_content, annex_no, order)
        chunks.extend(note_chunks)
        
        # 4. 텍스트 손실 검증
        total_chars = sum(c.char_count for c in chunks)
        loss_rate = abs(total_chars - len(cleaned_content)) / len(cleaned_content) if len(cleaned_content) > 0 else 0
        
        if loss_rate > 0.05:
            logger.error(f"❌ 텍스트 손실 {loss_rate:.1%} - 기준 초과!")
        else:
            logger.info(f"✅ 텍스트 손실 {loss_rate:.1%} (허용 범위)")
        
        logger.info(f"✅ Annex 서브청킹 완료: {len(chunks)}개")
        self._log_chunk_types(chunks)
        
        return chunks
    
    def _clean_annex_text(self, text: str) -> str:
        """
        Annex 텍스트 노이즈 제거 (Phase 0.9.2 강화)
        
        ✅ Private Use Area 문자 제거
        ✅ Box drawing 문자 제거
        """
        
        # 1. Private Use Area (U+F000 ~ U+F8FF) 제거
        text = re.sub(r'[\uF000-\uF8FF]', '', text)
        
        # 2. Box drawing characters 제거
        box_chars = '─━│┃┌┐└┘├┤┬┴┼╋═║╔╗╚╝╠╣╦╩╬■□▪▫'
        for char in box_chars:
            text = text.replace(char, '')
        
        # 3. 기타 특수 공백 문자 정리
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)  # Zero-width spaces
        
        # 4. 연속 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 5. 연속 개행 정리 (3줄 이상 → 2줄)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 6. 각 줄의 앞뒤 공백 제거
        lines = []
        for line in text.split('\n'):
            cleaned_line = line.strip()
            lines.append(cleaned_line)
        
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _extract_header(
        self, 
        text: str, 
        annex_no: str, 
        order: int
    ) -> Optional[SubChunk]:
        """헤더 청크 추출"""
        
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
        
        # 헤더 영역 텍스트 (첫 200자 정도)
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
        """Table 섹션 분리"""
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
                # Phase 0.9.2: 노이즈 제거
                table_text = self._clean_annex_text(table_text)
                
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
                # Phase 0.9.2: 섹션 텍스트 노이즈 제거
                cleaned_section = self._clean_annex_text(section_text_no_notes.strip())
                
                chunks.append(SubChunk(
                    section_id=f"annex_{annex_no}_table_{i+1}",
                    section_type="table_rows",
                    content=cleaned_section,
                    metadata={
                        "table_title": section_title,
                        "row_count_estimate": self._estimate_row_count(cleaned_section)
                    },
                    char_count=len(cleaned_section),
                    order=order
                ))
                order += 1
        
        return chunks
    
    def _extract_table_body(self, text: str) -> str:
        """표 본문 영역 추출 (헤더 제외)"""
        
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
        
        # * 시작 라인들 수집
        note_lines = []
        for line in text.split('\n'):
            if line.strip().startswith('*'):
                note_lines.append(line.strip())
        
        if note_lines:
            note_content = '\n'.join(note_lines)
            
            chunks.append(SubChunk(
                section_id=f"annex_{annex_no}_notes",
                section_type="note",
                content=note_content,
                metadata={
                    "note_count": len(note_lines)
                },
                char_count=len(note_content),
                order=order
            ))
        
        return chunks
    
    def _estimate_row_count(self, text: str) -> int:
        """행 개수 추정"""
        
        lines = [line for line in text.split('\n') if line.strip()]
        
        # 숫자로 시작하는 라인 개수
        numbered_lines = [
            line for line in lines 
            if re.match(r'^\d+\s', line.strip())
        ]
        
        return len(numbered_lines)
    
    def _log_chunk_types(self, chunks: List[SubChunk]):
        """청크 타입별 통계"""
        
        type_counts = {}
        for chunk in chunks:
            ctype = chunk.section_type
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")


def validate_subchunks(chunks: List[SubChunk], original_len: int) -> Dict[str, Any]:
    """서브청크 검증"""
    
    total_chars = sum(c.char_count for c in chunks)
    loss_rate = abs(total_chars - original_len) / original_len if original_len > 0 else 0
    
    is_valid = loss_rate <= 0.05
    
    return {
        'is_valid': is_valid,
        'chunk_count': len(chunks),
        'total_chars': total_chars,
        'original_len': original_len,
        'loss_rate': loss_rate
    }
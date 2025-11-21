"""
core/annex_subchunker.py - Phase 0.9.3 Critical Hotfix

Phase 0.9.3 수정사항:
- ✅ 별표 분리 로직 추가 (re.finditer → 모든 별표 찾기)
- ✅ 각 별표를 독립적으로 서브청킹
- ✅ 노이즈 제거 순서 개선 (별표 인식 먼저)
- ✅ QA 강화 (별표 개수 검증)

근본 원인 해결:
- BEFORE: 단일 별표 가정 (첫 번째만 처리)
- AFTER:  다중 별표 지원 (N개 모두 처리)

Author: 마창수산팀
Date: 2025-11-21
Version: Phase 0.9.3
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
    Annex 서브청킹 (Phase 0.9.3 Critical Hotfix)
    
    다중 별표 지원:
    - ✅ [별표1], [별표2], [별표3] ... 모두 처리
    - ✅ 각 별표를 독립적으로 청킹
    - ✅ 별표 개수 검증
    """
    
    def __init__(self):
        """초기화"""
        
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'table_separator': r'^([①-⑳■▪●◆◇]?\s*[가-힣\s]+(?:명칭|급별|범위|대상|구분))',
            'note': r'^\*\s*(.+)$'
        }
        
        logger.info("✅ AnnexSubChunker v0.9.3 초기화 (Multi-Annex Support)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청크 변환 (Phase 0.9.3)
        
        ✅ 다중 별표 지원:
        1. 모든 [별표N] 위치 찾기
        2. 각 별표를 독립 영역으로 분리
        3. 각 영역마다 서브청킹 수행
        """
        logger.info(f"🔧 Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Phase 0.9.3: 별표 분리
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ 별표 분리 완료: {len(annex_sections)}개")
        
        # 각 별표마다 청킹
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            annex_content = annex_sec['content']
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(annex_content)}자)")
            
            # 노이즈 제거 (별표 분리 후)
            cleaned_content = self._clean_annex_text(annex_content)
            
            # 서브청킹
            section_chunks = self._process_single_annex(
                cleaned_content,
                annex_num,
                global_order
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Phase 0.9.3: QA 검증
        self._validate_multi_annex(annex_sections, all_chunks, annex_text)
        
        logger.info(f"✅ Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        self._log_chunk_types(all_chunks)
        
        return all_chunks
    
    def _split_by_annex(self, text: str) -> List[Dict[str, Any]]:
        """
        Phase 0.9.3: 별표별로 텍스트 분리
        
        Returns:
            [
                {
                    'annex_no': '1',
                    'title': '...',
                    'content': '...',
                    'start_pos': 0,
                    'end_pos': 100
                },
                ...
            ]
        """
        # 모든 [별표N] 위치 찾기
        matches = list(re.finditer(self.patterns['annex_header'], text))
        
        if not matches:
            return []
        
        sections = []
        
        for i, match in enumerate(matches):
            annex_no = match.group(1)
            annex_title = match.group(2).strip()
            start_pos = match.start()
            
            # 다음 별표까지 or 끝까지
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            content = text[start_pos:end_pos]
            
            sections.append({
                'annex_no': annex_no,
                'title': annex_title,
                'content': content,
                'start_pos': start_pos,
                'end_pos': end_pos
            })
        
        return sections
    
    def _process_single_annex(
        self,
        content: str,
        annex_no: str,
        start_order: int
    ) -> List[SubChunk]:
        """
        단일 별표 처리 (Phase 0.9.3)
        
        Args:
            content: 별표 영역 텍스트
            annex_no: 별표 번호
            start_order: 시작 순서
        
        Returns:
            서브청크 리스트
        """
        chunks = []
        order = start_order
        
        # 1. Header 청크
        header_chunk = self._extract_header_from_content(content, annex_no, order)
        if header_chunk:
            chunks.append(header_chunk)
            order += 1
        
        # 2. Table 영역 분리
        table_chunks = self._extract_table_sections(content, annex_no, order)
        chunks.extend(table_chunks)
        order += len(table_chunks)
        
        # 3. Note 청크
        note_chunks = self._extract_notes(content, annex_no, order)
        chunks.extend(note_chunks)
        
        return chunks
    
    def _extract_header_from_content(
        self,
        content: str,
        annex_no: str,
        order: int
    ) -> Optional[SubChunk]:
        """별표 헤더 청크 생성"""
        
        match = re.search(self.patterns['annex_header'], content)
        if not match:
            return None
        
        annex_num = match.group(1)
        title = match.group(2).strip()
        
        # 관련 조문 추출
        related_article = ""
        article_match = re.search(self.patterns['related_article'], content)
        if article_match:
            related_article = article_match.group(1)
        
        # 개정이력 추출
        amendments = []
        for m in re.finditer(self.patterns['amendment'], content):
            amendments.append(m.group(1).strip())
        
        # 헤더 영역 텍스트 (첫 200자 정도)
        header_text = content[:min(200, len(content))]
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
    
    def _clean_annex_text(self, text: str) -> str:
        """
        Annex 텍스트 노이즈 제거
        
        ✅ Phase 0.9.3: 별표 분리 후 실행
        """
        
        # 1. Private Use Area (U+F000 ~ U+F8FF) 제거
        text = re.sub(r'[\uF000-\uF8FF]', '', text)
        
        # 2. Box drawing characters 제거
        box_chars = '─━│┃┌┐└┘├┤┬┴┼╋═║╔╗╚╝╠╣╦╩╬■□▪▫'
        for char in box_chars:
            text = text.replace(char, '')
        
        # 3. 기타 특수 공백 문자 정리
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
        
        # 4. 연속 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 5. 연속 개행 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 6. 각 줄의 앞뒤 공백 제거
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _extract_table_sections(
        self,
        text: str,
        annex_no: str,
        start_order: int
    ) -> List[SubChunk]:
        """Table 섹션 분리"""
        chunks = []
        order = start_order
        
        separators = list(re.finditer(
            self.patterns['table_separator'],
            text,
            re.MULTILINE
        ))
        
        if not separators:
            # 구분자 없으면 전체를 하나의 테이블로
            table_text = self._extract_table_body(text)
            if table_text and len(table_text.strip()) > 20:
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
            start_pos = sep_match.start()
            end_pos = (separators[i+1].start()
                      if i+1 < len(separators)
                      else len(text))
            
            section_text = text[start_pos:end_pos]
            
            # Note 제외
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
        """표 본문 영역 추출"""
        lines = text.split('\n')
        table_start = 0
        
        for i, line in enumerate(lines):
            if re.match(r'^\d+\s', line):
                table_start = i
                break
        
        if table_start == 0:
            return ""
        
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
        """Note 청크 추출"""
        chunks = []
        order = start_order
        
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
                metadata={"note_count": len(note_lines)},
                char_count=len(note_content),
                order=order
            ))
        
        return chunks
    
    def _estimate_row_count(self, text: str) -> int:
        """행 개수 추정"""
        lines = [l for l in text.split('\n') if l.strip()]
        digit_lines = [l for l in lines if re.match(r'^\d+\s', l)]
        return len(digit_lines)
    
    def _fallback_chunk(self, text: str, annex_no: str) -> List[SubChunk]:
        """
        Fallback: 별표 패턴 없을 때
        """
        logger.warning("   ⚠️ Fallback 모드: 전체를 단일 청크로 처리")
        
        cleaned = self._clean_annex_text(text)
        
        return [SubChunk(
            section_id=f"annex_{annex_no}_fallback",
            section_type="unknown",
            content=cleaned,
            metadata={"fallback": True},
            char_count=len(cleaned),
            order=0
        )]
    
    def _validate_multi_annex(
        self,
        annex_sections: List[Dict],
        chunks: List[SubChunk],
        original_text: str
    ):
        """
        Phase 0.9.3: 다중 별표 QA 검증
        
        1. 별표 개수 vs 헤더 청크 개수
        2. 각 별표의 최소 문자 수
        3. 전체 텍스트 손실률
        """
        # 1. 별표 개수 검증
        header_chunks = [c for c in chunks if 'header' in c.section_type]
        annex_count = len(annex_sections)
        header_count = len(header_chunks)
        
        if header_count != annex_count:
            logger.error(
                f"❌ 별표 개수 불일치! "
                f"입력: {annex_count}개, 출력: {header_count}개"
            )
        else:
            logger.info(f"✅ 별표 개수 일치: {annex_count}개")
        
        # 2. 각 별표 최소 문자 수 검증
        for annex_sec in annex_sections:
            annex_no = annex_sec['annex_no']
            annex_chunks = [
                c for c in chunks
                if c.section_id.startswith(f"annex_{annex_no}")
            ]
            
            total_chars = sum(c.char_count for c in annex_chunks)
            
            if total_chars < 50:
                logger.warning(
                    f"⚠️ 별표{annex_no} 문자 수 부족: {total_chars}자"
                )
            else:
                logger.info(f"   별표{annex_no}: {total_chars}자, {len(annex_chunks)}개 청크")
        
        # 3. 전체 텍스트 손실률
        total_output = sum(c.char_count for c in chunks)
        loss_rate = abs(total_output - len(original_text)) / len(original_text)
        
        if loss_rate > 0.10:
            logger.warning(f"⚠️ 텍스트 손실률 {loss_rate:.1%}")
        else:
            logger.info(f"✅ 텍스트 손실률 {loss_rate:.1%} (허용 범위)")
    
    def _log_chunk_types(self, chunks: List[SubChunk]):
        """청크 타입 통계"""
        type_counts = {}
        for chunk in chunks:
            ctype = chunk.section_type
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        logger.info(f"   타입 분포: {dict(type_counts)}")


def validate_subchunks(chunks: List[SubChunk], original_length: int) -> Dict[str, Any]:
    """
    서브청크 검증
    
    Phase 0.9.3: 다중 별표 검증 추가
    """
    if not chunks:
        return {
            'is_valid': False,
            'reason': '청크 없음',
            'chunk_count': 0,
            'type_counts': {},
            'loss_rate': 1.0,
            'has_header': False
        }
    
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    total_chars = sum(c.char_count for c in chunks)
    loss_rate = abs(total_chars - original_length) / original_length if original_length > 0 else 0
    
    has_header = any('header' in c.section_type for c in chunks)
    
    is_valid = (
        len(chunks) >= 1 and
        loss_rate < 0.15 and
        has_header
    )
    
    return {
        'is_valid': is_valid,
        'reason': 'OK' if is_valid else '검증 실패',
        'chunk_count': len(chunks),
        'type_counts': type_counts,
        'loss_rate': loss_rate,
        'has_header': has_header
    }
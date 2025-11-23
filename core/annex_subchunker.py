"""
core/annex_subchunker.py - Phase 0.9.5 Complete Restructure

Phase 0.9.5 핵심 수정사항 (미송님 가이드):
1. ✅ Annex 완전 분리 (raw 단위)
2. ✅ 문단 단위 구조화 (annex_paragraph 신설)
3. ✅ 표 우선 처리 금지 → 문단 기준 재설계
4. ✅ note는 가장 마지막 문단에서만 추출
5. ✅ Annex Loss Check는 마지막에만 수행 (±3% 이하)
6. ✅ DualQA 조문 비교 로직은 절대 변경 금지

가드레일 준수:
- 🛑 기존 기능 절대 수정 금지 (TableParser, spacing, DualQA 보존)
- 🛑 spacing은 review 단계에서만 적용
- 🛑 Loss Check는 최종 단계에만

Author: 마창수산팀
Date: 2025-11-22
Version: Phase 0.9.5
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
    Annex 서브청킹 (Phase 0.9.5 Complete Restructure)
    
    미송님 원칙:
    - 표 없는 별표: header + paragraph×N + note
    - 표 있는 별표: header + paragraph + table_rows + paragraph + note
    - 텍스트 손실 ±3% 이하 보장
    """
    
    def __init__(self):
        """초기화"""
        
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'note_marker': r'^\*\s*(.+)$',  # Note 판정용
            'table_start': r'^\d+\s+',  # 표 시작 판정용
        }
        
        logger.info("✅ AnnexSubChunker v0.9.5 초기화 (Complete Restructure)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청킹 (Phase 0.9.5)
        
        미송님 6단계:
        1. Annex 완전 분리
        2. 문단 단위 구조화
        3. 표 위/아래 문단 보존
        4. note는 마지막 문단에서만
        5. Loss Check 최종 단계
        6. DualQA 영향 없음
        """
        logger.info(f"🔧 Phase 0.9.5: Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Step 1: Annex 완전 분리 (raw 단위)
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ Step 1: 별표 분리 완료: {len(annex_sections)}개")
        
        # ✅ Phase 0.9.5.1: Canonical text 생성 (Loss Check 기준)
        canonical_text = self._clean_annex_text(annex_text)
        
        # Step 2-4: 각 별표마다 문단 단위 구조화
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            raw_content = annex_sec['content']
            header_end_pos = annex_sec['header_end_pos']  # ✅ Phase 0.9.5.1
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(raw_content)}자)")
            
            # 노이즈 제거 (별표 분리 후)
            cleaned_content = self._clean_annex_text(raw_content)
            
            # 문단 단위 구조화
            section_chunks = self._process_single_annex_v095(
                cleaned_content,
                annex_num,
                global_order,
                header_end_pos  # ✅ Phase 0.9.5.1: Header 끝 위치 전달
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Step 5: Annex Loss Check (최종 단계만!)
        # ✅ Phase 0.9.5.1: Canonical text 기준으로 검증
        self._validate_annex_loss(annex_sections, all_chunks, canonical_text)
        
        logger.info(f"✅ Phase 0.9.5.1: Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        self._log_chunk_types(all_chunks)
        
        return all_chunks
    
    def _split_by_annex(self, text: str) -> List[Dict[str, Any]]:
        """
        Step 1: 별표별로 텍스트 완전 분리 (raw 단위)
        
        ✅ Phase 0.9.5.1 Hotfix: Header end position 정확히 계산
        
        Returns:
            [
                {
                    'annex_no': '1',
                    'title': '...',
                    'content': '...',  ← RAW 텍스트 (구조화 전)
                    'header_end_pos': 100,  ← 신규: Header 끝 위치
                    'start_pos': 0,
                    'end_pos': 100
                },
                ...
            ]
        """
        matches = list(re.finditer(self.patterns['annex_header'], text))
        
        if not matches:
            return []
        
        sections = []
        
        for i, match in enumerate(matches):
            annex_no = match.group(1)
            annex_title = match.group(2).strip()
            start_pos = match.start()
            header_end_pos = match.end()  # ✅ Phase 0.9.5.1: Header 끝 = Body 시작
            
            # 다음 별표까지 or 끝까지
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            content = text[start_pos:end_pos]
            
            sections.append({
                'annex_no': annex_no,
                'title': annex_title,
                'content': content,  # RAW 텍스트
                'header_end_pos': header_end_pos - start_pos,  # ✅ 상대 위치
                'start_pos': start_pos,
                'end_pos': end_pos
            })
        
        return sections
    
    def _process_single_annex_v095(
        self,
        content: str,
        annex_no: str,
        start_order: int,
        header_end_pos: int  # ✅ Phase 0.9.5.1: Header 끝 위치
    ) -> List[SubChunk]:
        """
        Step 2-4: 단일 별표 문단 단위 구조화 (Phase 0.9.5.1 Hotfix)
        
        ✅ Phase 0.9.5.1 변경사항:
        - header_end_pos를 정규식 기준으로 받아 정확히 분리
        - Header는 매치된 라인만 포함
        - Body는 header_end_pos부터 시작
        
        미송님 원칙:
        - 문단 기준으로 먼저 자름
        - 표가 있는 문단만 table_rows로 변환
        - 나머지는 모두 paragraph
        - note는 가장 마지막 문단에서만
        
        Args:
            content: 별표 영역 텍스트 (cleaned)
            annex_no: 별표 번호
            start_order: 시작 순서
            header_end_pos: Header 끝 위치 (정규식 match.end())
        
        Returns:
            서브청크 리스트 [header, paragraph×N, table_rows, note]
        """
        chunks = []
        order = start_order
        
        # ✅ Phase 0.9.5.1: Header/Body 정확히 분리
        header_text = content[:header_end_pos].strip()
        body_text = content[header_end_pos:].strip()
        
        # Step 2-1: Header 청크 (정규식 매치 라인만)
        if header_text:
            # 관련 조문, 개정이력 추가 추출
            header_chunk = self._extract_header_chunk(header_text, annex_no, order)
            if header_chunk:
                chunks.append(header_chunk)
                order += 1
        
        # Step 3: 문단 기준으로 먼저 분리 (빈 줄 기준)
        paragraphs = self._split_into_paragraphs(body_text)
        
        logger.info(f"      문단 분리: {len(paragraphs)}개")
        
        # Step 3-4: 각 문단 처리
        for i, para_text in enumerate(paragraphs):
            is_last_paragraph = (i == len(paragraphs) - 1)
            
            # Step 4: 마지막 문단에서만 note 추출
            if is_last_paragraph:
                note_chunk, remaining_text = self._extract_note_from_paragraph(
                    para_text, annex_no, order
                )
                
                if remaining_text and remaining_text.strip():
                    # Note 제외한 나머지가 있으면 paragraph로
                    para_chunk = self._create_paragraph_or_table(
                        remaining_text, annex_no, order, i
                    )
                    if para_chunk:
                        chunks.append(para_chunk)
                        order += 1
                
                if note_chunk:
                    chunks.append(note_chunk)
                    order += 1
            else:
                # 중간 문단: paragraph 또는 table_rows로 변환
                para_chunk = self._create_paragraph_or_table(
                    para_text, annex_no, order, i
                )
                if para_chunk:
                    chunks.append(para_chunk)
                    order += 1
        
        return chunks
    
    def _extract_header_chunk(
        self,
        header_text: str,
        annex_no: str,
        order: int
    ) -> Optional[SubChunk]:
        """
        ✅ Phase 0.9.5.1: Header 청크 생성 (정규식 매치 라인만)
        
        Args:
            header_text: Header 영역 텍스트 (정규식 매치 끝까지)
            annex_no: 별표 번호
            order: 순서
        
        Returns:
            Header 청크
        """
        # 제목 추출
        match = re.search(self.patterns['annex_header'], header_text)
        if not match:
            return None
        
        annex_num = match.group(1)
        title = match.group(2).strip()
        
        # 관련 조문 추출 (header_text 내에서만)
        related_article = ""
        article_match = re.search(self.patterns['related_article'], header_text)
        if article_match:
            related_article = article_match.group(1)
        
        # 개정이력 추출 (header_text 내에서만)
        amendments = []
        for m in re.finditer(self.patterns['amendment'], header_text):
            amendments.append(m.group(1).strip())
        
        # ✅ Phase 0.9.5.1: header_text 그대로 사용 (중복 없음)
        
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
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Step 3: 문단 단위로 텍스트 분리 (빈 줄 기준)
        
        Args:
            text: 본문 텍스트
        
        Returns:
            문단 리스트
        """
        # 빈 줄(2개 이상 개행)을 기준으로 분리
        paragraphs = re.split(r'\n\s*\n', text)
        
        # 빈 문단 제거 + strip
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _create_paragraph_or_table(
        self,
        para_text: str,
        annex_no: str,
        order: int,
        para_index: int
    ) -> Optional[SubChunk]:
        """
        Step 3: 문단을 paragraph 또는 table_rows로 변환
        
        미송님 원칙:
        - 표 패턴이 있으면 table_rows
        - 없으면 paragraph
        - 둘 다 보존 (손실 없음)
        
        Args:
            para_text: 문단 텍스트
            annex_no: 별표 번호
            order: 순서
            para_index: 문단 인덱스
        
        Returns:
            SubChunk (paragraph 또는 table_rows)
        """
        if not para_text or len(para_text.strip()) < 10:
            return None
        
        # 표 판정: 숫자로 시작하는 라인이 3개 이상
        lines = para_text.split('\n')
        digit_lines = [l for l in lines if re.match(self.patterns['table_start'], l)]
        
        has_table = len(digit_lines) >= 3
        
        if has_table:
            # table_rows 청크
            return SubChunk(
                section_id=f"annex_{annex_no}_table_{para_index+1}",
                section_type="table_rows",
                content=para_text.strip(),
                metadata={
                    "para_index": para_index,
                    "row_count_estimate": len(digit_lines),
                    "has_table": True
                },
                char_count=len(para_text.strip()),
                order=order
            )
        else:
            # paragraph 청크 (신규!)
            return SubChunk(
                section_id=f"annex_{annex_no}_paragraph_{para_index+1}",
                section_type="paragraph",
                content=para_text.strip(),
                metadata={
                    "para_index": para_index,
                    "has_table": False
                },
                char_count=len(para_text.strip()),
                order=order
            )
    
    def _extract_note_from_paragraph(
        self,
        para_text: str,
        annex_no: str,
        order: int
    ) -> tuple[Optional[SubChunk], str]:
        """
        Step 4: 마지막 문단에서만 note 추출
        
        Args:
            para_text: 문단 텍스트
            annex_no: 별표 번호
            order: 순서
        
        Returns:
            (note_chunk, remaining_text)
            - note_chunk: Note 청크 (없으면 None)
            - remaining_text: Note 제외한 나머지 텍스트
        """
        lines = para_text.split('\n')
        
        # * 시작하는 줄 찾기
        note_start_idx = -1
        for i, line in enumerate(lines):
            if re.match(self.patterns['note_marker'], line):
                note_start_idx = i
                break
        
        if note_start_idx == -1:
            # Note 없음
            return None, para_text
        
        # Note 라인들
        note_lines = lines[note_start_idx:]
        note_content = '\n'.join(note_lines).strip()
        
        # Note 제외한 나머지
        remaining_lines = lines[:note_start_idx]
        remaining_text = '\n'.join(remaining_lines).strip()
        
        # Note 청크 생성
        note_chunk = SubChunk(
            section_id=f"annex_{annex_no}_notes",
            section_type="note",
            content=note_content,
            metadata={
                "note_count": len(note_lines)
            },
            char_count=len(note_content),
            order=order
        )
        
        return note_chunk, remaining_text
    
    def _clean_annex_text(self, text: str) -> str:
        """
        Annex 텍스트 노이즈 제거
        
        ✅ Phase 0.9.5: 별표 분리 후 실행 (변경 없음)
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
        
        # 5. 연속 개행 정리 (3개 이상 → 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 6. 각 줄의 앞뒤 공백 제거
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _validate_annex_loss(
        self,
        annex_sections: List[Dict],
        chunks: List[SubChunk],
        canonical_text: str  # ✅ Phase 0.9.5.1: Cleaned text 기준
    ):
        """
        Step 5: Annex Loss Check (최종 단계만!)
        
        ✅ Phase 0.9.5.1 변경사항:
        - original_text 대신 canonical_text (정제 후) 기준
        - SubChunker가 정제한 텍스트와 동일 기준으로 비교
        - 허용 오차: ±3% 이하
        
        Args:
            annex_sections: 별표 섹션 리스트
            chunks: 최종 청크 리스트
            canonical_text: 정제된 Annex 텍스트 (기준)
        """
        logger.info("🔍 Step 5: Annex Loss Check")
        
        # ✅ Phase 0.9.5.1: Canonical text 길이 (동일 정제 기준)
        canonical_len = len(canonical_text)
        
        # 청크 합계 길이
        chunk_total_len = sum(c.char_count for c in chunks)
        
        # 손실률 계산
        loss_rate = abs(canonical_len - chunk_total_len) / canonical_len if canonical_len > 0 else 0
        loss_pct = loss_rate * 100
        
        logger.info(f"   Canonical 텍스트: {canonical_len:,}자")
        logger.info(f"   청크 합계: {chunk_total_len:,}자")
        logger.info(f"   손실률: {loss_pct:.1f}%")
        
        # 허용 오차: ±3%
        if loss_rate > 0.03:
            logger.warning(f"⚠️ 텍스트 손실 {loss_pct:.1f}% - 허용치(3%) 초과!")
        else:
            logger.info(f"✅ 텍스트 손실 허용 범위 내 ({loss_pct:.1f}% < 3%)")
        
        # 별표별 검증 (per-annex check)
        for annex_sec in annex_sections:
            annex_no = annex_sec['annex_no']
            
            # ✅ Phase 0.9.5.1: 정제된 길이로 계산
            annex_raw = annex_sec['content']
            annex_cleaned = self._clean_annex_text(annex_raw)
            annex_len = len(annex_cleaned)
            
            # 해당 별표 청크들
            annex_chunks = [
                c for c in chunks
                if c.section_id.startswith(f"annex_{annex_no}")
            ]
            
            annex_chunk_len = sum(c.char_count for c in annex_chunks)
            annex_loss = abs(annex_len - annex_chunk_len) / annex_len if annex_len > 0 else 0
            
            logger.info(
                f"   별표{annex_no}: {annex_len}자 → {annex_chunk_len}자 "
                f"({len(annex_chunks)}개 청크, 손실 {annex_loss*100:.1f}%)"
            )
    
    def _fallback_chunk(self, text: str, annex_no: str) -> List[SubChunk]:
        """
        Fallback: 별표 패턴 없을 때
        """
        logger.warning("   ⚠️ Fallback 모드: 전체를 단일 청크로 처리")
        
        cleaned = self._clean_annex_text(text)
        
        return [SubChunk(
            section_id=f"annex_{annex_no}_fallback",
            section_type="paragraph",  # Phase 0.9.5: paragraph로 변경
            content=cleaned,
            metadata={"fallback": True},
            char_count=len(cleaned),
            order=0
        )]
    
    def _log_chunk_types(self, chunks: List[SubChunk]):
        """청크 타입별 통계 로깅"""
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.section_type
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        logger.info("📊 청크 타입 분포:")
        for chunk_type, count in sorted(type_counts.items()):
            logger.info(f"   - {chunk_type}: {count}개")


def validate_subchunks(chunks: List[SubChunk], original_length: int) -> dict:
    """
    서브청킹 결과 검증
    
    Phase 0.9.5: paragraph 타입 추가
    """
    if not chunks:
        return {
            'is_valid': False,
            'reason': '청크 없음',
            'chunk_count': 0,
            'loss_rate': 1.0
        }
    
    # 타입별 카운트
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk.section_type
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
    
    # 총 문자 수
    total_chars = sum(c.char_count for c in chunks)
    
    # 손실률
    loss_rate = abs(original_length - total_chars) / original_length if original_length > 0 else 0
    
    # 검증 기준
    has_header = 'header' in type_counts
    has_content = 'table_rows' in type_counts or 'paragraph' in type_counts
    
    is_valid = has_header and has_content and loss_rate < 0.05
    
    return {
        'is_valid': is_valid,
        'chunk_count': len(chunks),
        'type_counts': type_counts,
        'total_chars': total_chars,
        'loss_rate': loss_rate,
        'has_header': has_header,
        'has_content': has_content
    }
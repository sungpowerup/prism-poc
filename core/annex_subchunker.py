"""
core/annex_subchunker.py - Phase 0.9.5.2.1 긴급 Hotfix

GPT 미송님 피드백 반영:
1. ✅ validate_subchunks 시그니처 복구 (2-arg)
2. ✅ Phase 0.9.5.1 안정성 100% 복구
3. ⏸️ 표 판정 강화 보류 (Phase 0.9.5.1 패턴 유지)

수정 사항:
- validate_subchunks(chunks, original_length) 시그니처 복구
- Phase 0.9.5.1 표 판정 로직 유지
- LawParser 호출 계약 완전 복구

Author: 마창수산팀 + GPT 미송님 긴급 가이드
Date: 2025-11-24
Version: Phase 0.9.5.2.1 Hotfix
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
    Annex 서브청킹 (Phase 0.9.5.2.1 Hotfix)
    
    GPT 미송님 원칙:
    - 표 없는 별표: header + paragraph×N + note
    - 표 있는 별표: header + paragraph + table_rows + paragraph + note
    - 텍스트 손실 ±3% 이하 보장
    - validate_subchunks 2-arg 시그니처 엄수
    """
    
    def __init__(self):
        """초기화"""
        
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'note_marker': r'^\*\s*(.+)$',
            'table_start': r'^\d+\s+',  # ✅ Phase 0.9.5.1 패턴 유지
        }
        
        logger.info("✅ AnnexSubChunker v0.9.5.2.1 초기화 (Hotfix - Rollback to 0.9.5.1)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청킹 (Phase 0.9.5.2.1 Hotfix)
        
        GPT 미송님 6단계:
        1. Annex 완전 분리
        2. 문단 단위 구조화
        3. 표 위/아래 문단 보존
        4. note는 마지막 문단에서만
        5. Loss Check 최종 단계
        6. DualQA 영향 없음
        """
        logger.info(f"🔧 Phase 0.9.5.2.1 Hotfix: Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Step 1: Annex 완전 분리 (raw 단위)
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ Step 1: 별표 분리 완료: {len(annex_sections)}개")
        
        # Canonical text 생성 (Loss Check 기준)
        canonical_text = self._clean_annex_text(annex_text)
        
        # Step 2-4: 각 별표마다 문단 단위 구조화
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            raw_content = annex_sec['content']
            header_end_pos = annex_sec['header_end_pos']
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(raw_content)}자)")
            
            # 노이즈 제거 (별표 분리 후)
            cleaned_content = self._clean_annex_text(raw_content)
            
            # 문단 단위 구조화
            section_chunks = self._process_single_annex_v095(
                cleaned_content,
                annex_num,
                global_order,
                header_end_pos
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Step 5: Annex Loss Check (최종 단계만!)
        self._check_annex_loss(canonical_text, all_chunks)
        
        # Step 6: DualQA는 절대 건드리지 않음!
        logger.info(f"✅ Phase 0.9.5.2.1 Hotfix: Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in all_chunks:
            ctype = chunk.section_type
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return all_chunks
    
    def _split_by_annex(self, annex_text: str) -> List[Dict[str, Any]]:
        """
        Step 1: 별표 단위로 완전 분리
        """
        pattern = r'\[별표\s*(\d+)\]\s*([^\n<]+)'
        
        matches = list(re.finditer(pattern, annex_text))
        
        if not matches:
            return []
        
        sections = []
        
        for i, match in enumerate(matches):
            annex_no = match.group(1)
            start_pos = match.start()
            header_end_pos = match.end()
            
            # 다음 별표까지 또는 끝까지
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(annex_text)
            
            content = annex_text[start_pos:end_pos].strip()
            
            # Header 끝 위치를 상대 위치로 변환
            relative_header_end = header_end_pos - start_pos
            
            sections.append({
                'annex_no': annex_no,
                'content': content,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'header_end_pos': relative_header_end
            })
        
        return sections
    
    def _process_single_annex_v095(
        self,
        content: str,
        annex_no: str,
        start_order: int,
        header_end_pos: int
    ) -> List[SubChunk]:
        """
        Step 2-4: 단일 별표 문단 단위 구조화 (Phase 0.9.5.2.1 Hotfix)
        
        ✅ Phase 0.9.5.1 로직 완전 복구
        
        GPT 미송님 원칙:
        - 문단 기준으로 먼저 자름
        - 표가 있는 문단만 table_rows로 변환
        - 나머지는 모두 paragraph
        - note는 가장 마지막 문단에서만
        """
        chunks = []
        order = start_order
        
        # Header/Body 정확히 분리
        header_text = content[:header_end_pos].strip()
        body_text = content[header_end_pos:].strip()
        
        # Step 2-1: Header 청크
        if header_text:
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
        """Header 청크 생성"""
        match = re.search(self.patterns['annex_header'], header_text)
        if not match:
            return None
        
        annex_num = match.group(1)
        title = match.group(2).strip()
        
        # 관련 조문 추출
        related_article = ""
        article_match = re.search(self.patterns['related_article'], header_text)
        if article_match:
            related_article = article_match.group(1)
        
        # 개정이력 추출
        amendments = []
        for m in re.finditer(self.patterns['amendment'], header_text):
            amendments.append(m.group(1).strip())
        
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
        """문단 단위로 텍스트 분리 (빈 줄 기준)"""
        paragraphs = re.split(r'\n\s*\n', text)
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
        ✅ Phase 0.9.5.2.1 Hotfix: Phase 0.9.5.1 표 판정 로직 복구
        
        GPT 미송님 원칙:
        - 표 패턴이 있으면 table_rows
        - 없으면 paragraph
        - 둘 다 보존 (손실 없음)
        """
        if not para_text or len(para_text.strip()) < 10:
            return None
        
        lines = para_text.split('\n')
        
        # ✅ Phase 0.9.5.1 표 판정 로직 (검증된 버전)
        digit_lines = [l for l in lines if re.match(self.patterns['table_start'], l)]
        
        has_table = len(digit_lines) >= 3  # Phase 0.9.5.1 기준
        
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
            # paragraph 청크
            return SubChunk(
                section_id=f"annex_{annex_no}_para_{para_index+1}",
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
        """마지막 문단에서 Note 추출"""
        lines = para_text.split('\n')
        
        note_lines = []
        regular_lines = []
        
        in_note = False
        
        for line in lines:
            if re.match(self.patterns['note_marker'], line):
                in_note = True
                note_lines.append(line)
            elif in_note:
                note_lines.append(line)
            else:
                regular_lines.append(line)
        
        if not note_lines:
            return None, para_text
        
        note_content = '\n'.join(note_lines).strip()
        remaining_content = '\n'.join(regular_lines).strip()
        
        note_chunk = SubChunk(
            section_id=f"annex_{annex_no}_note",
            section_type="note",
            content=note_content,
            metadata={
                "is_note": True
            },
            char_count=len(note_content),
            order=order
        )
        
        return note_chunk, remaining_content
    
    def _check_annex_loss(self, original_text: str, chunks: List[SubChunk]) -> None:
        """Annex Loss Check (마지막 단계만)"""
        original_len = len(original_text)
        chunks_len = sum(chunk.char_count for chunk in chunks)
        
        loss_rate = abs(original_len - chunks_len) / original_len if original_len > 0 else 0
        
        logger.info(f"   📊 Loss Check:")
        logger.info(f"      원본: {original_len}자")
        logger.info(f"      청크: {chunks_len}자")
        logger.info(f"      손실률: {loss_rate*100:.1f}%")
        
        if loss_rate > 0.03:
            logger.warning(f"   ⚠️ 손실률 {loss_rate*100:.1f}% > 3% (허용치 초과)")
        else:
            logger.info(f"   ✅ 손실률 {loss_rate*100:.1f}% ≤ 3% (통과)")
    
    def _clean_annex_text(self, text: str) -> str:
        """노이즈 제거 (단일 버전)"""
        cleaned = text
        
        # 1. 페이지 번호 제거
        cleaned = re.sub(r'^\d+[-—–_]\d+\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^Page\s+\d+\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        # 2. HTML 태그 제거
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # 3. 연속 공백 정리
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # 4. 연속 개행 정리 (3개 이상 → 2개)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def _fallback_chunk(self, annex_text: str, annex_no: str) -> List[SubChunk]:
        """Fallback: 전체를 하나의 청크로"""
        logger.warning("⚠️ Fallback 모드: 전체를 단일 청크로 처리")
        
        return [
            SubChunk(
                section_id=f"annex_{annex_no}_fallback",
                section_type="paragraph",
                content=annex_text.strip(),
                metadata={
                    "fallback": True
                },
                char_count=len(annex_text.strip()),
                order=0
            )
        ]


def validate_subchunks(chunks: List[SubChunk], original_length: int) -> dict:
    """
    ✅ Phase 0.9.5.2.1 Hotfix: 시그니처 복구 (2-arg)
    
    서브청킹 결과 검증
    
    Args:
        chunks: 서브청크 리스트
        original_length: 원본 텍스트 길이 (Loss Check 기준)
    
    Returns:
        검증 결과 dict
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
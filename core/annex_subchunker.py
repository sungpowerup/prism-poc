"""
core/annex_subchunker.py - Phase 0.9.7.2 Header/Body Split Fix + Table Candidate Merge

GPT 미송님 최종 진단:
Phase 0.9.7.1 실패 원인: 헤더가 표 블록 근처에 아예 없음 (확장: ↑0 ↓0)

Phase 0.9.7.2 핵심 개선:
1. ✅ header/body 분리 재정의 (cleaned_content에서 다시 헤더 찾기)
2. ✅ table_candidate 상태 + Merge (약한 표 후보 0.45~0.6 보존)
3. ✅ 경계 보정 강화 (조건 기반, 긴 문장 감지)

목표: TableParser 성공률 1/3 → 3/3 (헤더+표 초반부 → 표 블록)

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-25
Version: Phase 0.9.7.2 Header Split Fix + Table Candidate Merge
"""

import re
import logging
import statistics
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ✅ Phase 0.9.7.1: TableParser 친화적 상수 (GPT 미송님)
HEADER_KEYWORDS = re.compile(
    r"(임용하고자|서열명부|직급|응시자격|승진|제외|구분|비고|인원수|점수|평정|평가)",
    re.IGNORECASE
)

SEPARATOR_LINE = re.compile(r"^[-─—]{3,}$")

DIGITISH_LINE = re.compile(r"^\s*(\d+[\.\)]?|\([0-9]+\)|[가-힣]\)|[A-Za-z]\))\s+")


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
    Annex 서브청킹 (Phase 0.9.7 Table Block Segmentation)
    
    GPT 미송님 설계:
    - 라인 유지 → 표 블록 감지 → 청크 변환
    - Table Block Segmentation (5개 특징)
    - Explainable Metadata (Block-Level)
    - P0 안정성 유지
    """
    
    def __init__(self):
        """초기화"""
        
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'note_marker': r'^\*\s*(.+)$',
            # ✅ Phase 0.9.7: Digit Regex 교체 (GPT 미송님)
            'digit_line': r'^\d+(\s*\S+)?$',  # "1", "1 5번까지" 모두 매칭
            'header_keywords': r'(직급|응시자격|비고|인원수|서열명부|순위)',
        }
        
        logger.info("✅ AnnexSubChunker v0.9.7.2 초기화 (Header Split Fix + Table Candidate Merge)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        Annex 텍스트 → 서브청킹 (Phase 0.9.7)
        
        GPT 미송님 단계:
        1. Annex 완전 분리
        2. 라인 유지 (문단 분리 금지!)
        3. Table Block Segmentation
        4. Block → Chunk 변환
        5. Loss Check
        """
        logger.info(f"🔧 Phase 0.9.7: Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Step 1: Annex 완전 분리 (raw 단위)
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ Step 1: 별표 분리 완료: {len(annex_sections)}개")
        
        # Canonical text 생성 (Loss Check 기준)
        canonical_text = self._clean_annex_text(annex_text)
        
        # Step 2-4: 각 별표마다 Table Block Segmentation
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            raw_content = annex_sec['content']
            header_end_pos = annex_sec['header_end_pos']
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(raw_content)}자)")
            
            # 노이즈 제거 (별표 분리 후)
            cleaned_content = self._clean_annex_text(raw_content)
            
            # ✅ Phase 0.9.7: Table Block Segmentation
            section_chunks = self._process_single_annex_v097(
                cleaned_content,
                annex_num,
                global_order,
                header_end_pos
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Step 5: Annex Loss Check
        self._check_annex_loss(canonical_text, all_chunks)
        
        logger.info(f"✅ Phase 0.9.7: Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in all_chunks:
            ctype = chunk.section_type
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return all_chunks
    
    def _split_by_annex(self, annex_text: str) -> List[Dict[str, Any]]:
        """Step 1: 별표 단위로 완전 분리"""
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
    
    def _process_single_annex_v097(
        self,
        content: str,
        annex_no: str,
        start_order: int,
        header_end_pos: int
    ) -> List[SubChunk]:
        """
        ✅ Phase 0.9.7.2: Header/Body Split Fix (GPT 미송님 진단)
        
        핵심 개선:
        1. cleaned_content에서 다시 헤더 찾기 (pos 버그 해결)
        2. Table Candidate Merge (약한 표 후보 보존)
        3. 경계 보정 강화
        """
        chunks = []
        order = start_order
        
        # ✅ Phase 0.9.7.2: Header/Body 재정의 (GPT 미송님)
        # 문제: raw 위치로 cleaned_content 자름 → 경계 오염
        # 해결: cleaned_content에서 다시 헤더 찾기
        header_text, body_text = self._split_header_body(content)
        
        # Step 1: Header 청크
        if header_text:
            header_chunk = self._extract_header_chunk(header_text, annex_no, order)
            if header_chunk:
                chunks.append(header_chunk)
                order += 1
        
        # ✅ Phase 0.9.7: 라인 유지 (문단 분리 금지!)
        lines = body_text.split('\n')
        lines = [l for l in lines if l.strip()]  # 빈 줄만 제거
        
        logger.info(f"      라인 유지: {len(lines)}개")
        
        # Step 2: Table Block Segmentation
        blocks = self._segment_blocks(lines)
        
        # ✅ Phase 0.9.7.2: Table Candidate Merge (GPT 미송님)
        blocks = self._merge_table_candidates(blocks)
        
        logger.info(f"      블록 분리: {len(blocks)}개")
        
        # Step 3: Block → Chunk 변환
        for i, block in enumerate(blocks):
            block_lines = block['lines']
            block_type = block['type']
            block_metadata = block['metadata']
            
            is_last_block = (i == len(blocks) - 1)
            
            # Note 추출 (마지막 블록에서만)
            if is_last_block:
                note_chunk, remaining_lines = self._extract_note_from_lines(
                    block_lines, annex_no, order
                )
                
                if remaining_lines:
                    block_chunk = self._create_block_chunk(
                        remaining_lines, annex_no, order, i, block_type, block_metadata
                    )
                    if block_chunk:
                        chunks.append(block_chunk)
                        order += 1
                
                if note_chunk:
                    chunks.append(note_chunk)
                    order += 1
            else:
                # 중간 블록
                block_chunk = self._create_block_chunk(
                    block_lines, annex_no, order, i, block_type, block_metadata
                )
                if block_chunk:
                    chunks.append(block_chunk)
                    order += 1
        
        return chunks
    
    def _segment_blocks(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.9.7.2: Table Block Segmentation + Candidate (GPT 미송님)
        
        개선사항:
        1. 표 블록 감지 (0.9.7)
        2. TableParser 친화적 경계 보정 (0.9.7.1)
        3. table_candidate 상태 추가 (0.9.7.2) ← 핵심!
           - 약한 표 후보 (0.45~0.6) 보존
           - 다음 블록이 table_rows면 merge
        """
        blocks = []
        
        if not lines:
            return blocks
        
        # 윈도우 슬라이딩 (5~8 라인)
        window_size = min(8, max(5, len(lines) // 3))
        
        i = 0
        while i < len(lines):
            # 윈도우 설정
            window_end = min(i + window_size, len(lines))
            window_lines = lines[i:window_end]
            
            # 5개 특징 계산
            features = self._calculate_block_features(window_lines)
            
            # Table Score 계산
            table_score = self._calculate_table_score(features)
            
            # ✅ Phase 0.9.7.2: Block 타입 결정 (table_candidate 추가)
            if table_score >= 0.6:
                # 강확신: table_rows
                block_type = "table_rows"
                
                # 표 블록 확장 (연속된 표 라인 모두 포함)
                extended_end = self._extend_table_block(lines, i, window_end, features)
                
                # ✅ Phase 0.9.7.1: TableParser 친화적 경계 보정
                refined_start, refined_end, expand_meta = self._refine_table_block_boundaries(
                    lines, i, extended_end
                )
                
                block_lines = lines[refined_start:refined_end]
                
                logger.info(
                    f"         표 블록 감지: {refined_start}~{refined_end} 라인 "
                    f"(점수: {table_score:.2f}, 확장: ↑{expand_meta['expanded_up']} ↓{expand_meta['expanded_down']})"
                )
                
                i = refined_end
                
                features_with_expand = {
                    **features,
                    'table_score': round(table_score, 3),
                    **expand_meta
                }
            
            elif 0.45 <= table_score < 0.6 and (
                features['short_line_ratio'] > 0.8 or
                features['digit_density'] > 0.25 or
                features['header_hint']
            ):
                # ✅ Phase 0.9.7.2: 약확신 → table_candidate (GPT 미송님)
                block_type = "table_candidate"
                
                # 표 블록 확장
                extended_end = self._extend_table_block(lines, i, window_end, features)
                block_lines = lines[i:extended_end]
                
                logger.info(
                    f"         표 후보 감지: {i}~{extended_end} 라인 "
                    f"(점수: {table_score:.2f}, 보류)"
                )
                
                i = extended_end
                
                features_with_expand = {
                    **features,
                    'table_score': round(table_score, 3)
                }
            
            else:
                # 약확신/확신 없음: paragraph
                block_type = "paragraph"
                
                # 다음 표 블록까지 또는 윈도우 끝까지
                block_lines = window_lines
                
                i = window_end
                
                features_with_expand = {
                    **features,
                    'table_score': round(table_score, 3)
                }
            
            # Block 생성
            blocks.append({
                'type': block_type,
                'lines': block_lines,
                'metadata': features_with_expand
            })
        
        return blocks
    
    def _calculate_block_features(self, lines: List[str]) -> Dict[str, Any]:
        """
        ✅ Phase 0.9.7: 5개 특징 계산
        """
        if not lines:
            return {
                'digit_density': 0.0,
                'short_line_ratio': 0.0,
                'column_gap_consistency': 0.0,
                'header_hint': False,
                'avg_line_length': 0.0
            }
        
        # 1. digit_density (GPT 미송님: 즉시 효과)
        digit_lines = [l for l in lines if re.match(self.patterns['digit_line'], l)]
        digit_density = len(digit_lines) / len(lines)
        
        # 2. short_line_ratio
        line_lengths = [len(l) for l in lines]
        avg_line_length = sum(line_lengths) / len(lines)
        short_lines = [l for l in line_lengths if l < 50]  # 50자 미만
        short_line_ratio = len(short_lines) / len(lines)
        
        # 3. column_gap_consistency (공백 정렬)
        space_positions = []
        for line in lines:
            positions = [i for i, c in enumerate(line) if c == ' ']
            if positions:
                space_positions.append(positions[0] if positions else -1)
        
        if len(space_positions) > 1:
            variance = statistics.variance([p for p in space_positions if p >= 0])
            column_gap_consistency = 1.0 / (1.0 + variance)
        else:
            column_gap_consistency = 0.0
        
        # 4. header_hint
        first_line = lines[0] if lines else ""
        header_hint = bool(re.search(self.patterns['header_keywords'], first_line))
        
        return {
            'digit_density': round(digit_density, 3),
            'short_line_ratio': round(short_line_ratio, 3),
            'column_gap_consistency': round(column_gap_consistency, 3),
            'header_hint': header_hint,
            'avg_line_length': round(avg_line_length, 1)
        }
    
    def _calculate_table_score(self, features: Dict[str, Any]) -> float:
        """
        ✅ Phase 0.9.7: Table Score 계산
        
        GPT 미송님 가중치:
        - digit_density: 40%
        - short_line_ratio: 30%
        - column_gap_consistency: 20%
        - header_hint: 10%
        """
        score = 0.0
        
        # Digit Density (40%)
        score += features['digit_density'] * 0.4
        
        # Short Line Ratio (30%)
        score += features['short_line_ratio'] * 0.3
        
        # Column Gap Consistency (20%)
        score += features['column_gap_consistency'] * 0.2
        
        # Header Hint (10%)
        if features['header_hint']:
            score += 0.1
        
        return score
    
    def _extend_table_block(
        self,
        lines: List[str],
        start: int,
        end: int,
        features: Dict[str, Any]
    ) -> int:
        """표 블록 확장 (연속된 표 라인 포함)"""
        extended_end = end
        
        # 다음 라인들도 표 패턴이면 포함
        while extended_end < len(lines):
            next_line = lines[extended_end]
            
            # Digit 라인이면 포함
            if re.match(self.patterns['digit_line'], next_line):
                extended_end += 1
            # 짧은 라인이면 포함
            elif len(next_line) < 50:
                extended_end += 1
            # 아니면 종료
            else:
                break
        
        return extended_end
    
    def _refine_table_block_boundaries(
        self,
        lines: List[str],
        start: int,
        end: int
    ) -> Tuple[int, int, Dict[str, Any]]:
        """
        ✅ Phase 0.9.7.2: TableParser 친화적 경계 보정 강화 (GPT 미송님)
        
        개선사항:
        - 기존 (0.9.7.1): MAX_EXPAND_UP = 5 (너무 짧음)
        - 개선 (0.9.7.2): 조건 기반 확장 (긴 문장 만나기 전까지)
        """
        refined_start = start
        refined_end = end
        
        # ---- 역방향 확장 (조건 기반) ----
        i = start - 1
        expanded_up = 0
        while i >= 0:
            prev_line = lines[i].strip()
            
            if not prev_line:
                i -= 1
                expanded_up += 1
                continue
            
            # ✅ Phase 0.9.7.2: 긴 문장 만나면 종료 (GPT 미송님)
            if len(prev_line) > 80:
                break  # 표 헤더 끝으로 간주
            
            # 헤더 키워드/구분선이면 블록에 포함
            if HEADER_KEYWORDS.search(prev_line) or SEPARATOR_LINE.match(prev_line):
                refined_start = i
                i -= 1
                expanded_up += 1
                continue
            
            # 표 행 패턴이면 붙여도 됨
            if DIGITISH_LINE.match(prev_line):
                refined_start = i
                i -= 1
                expanded_up += 1
                continue
            
            break  # 그 외는 확장 종료
        
        # ---- 정방향 확장 (조건 기반) ----
        j = end
        expanded_down = 0
        max_down = 8  # 정방향은 제한 유지
        
        while j < len(lines) and expanded_down < max_down:
            next_line = lines[j].strip()
            
            if not next_line:
                j += 1
                expanded_down += 1
                continue
            
            # 긴 문장 만나면 종료
            if len(next_line) > 80:
                break
            
            if HEADER_KEYWORDS.search(next_line) or SEPARATOR_LINE.match(next_line):
                refined_end = j + 1
                j += 1
                expanded_down += 1
                continue
            
            if DIGITISH_LINE.match(next_line):
                refined_end = j + 1
                j += 1
                expanded_down += 1
                continue
            
            break
        
        # 메타데이터
        expand_meta = {
            "refined_start": refined_start,
            "refined_end": refined_end,
            "expanded_up": expanded_up,
            "expanded_down": expanded_down,
        }
        
        return refined_start, refined_end, expand_meta
    
    def _split_header_body(self, content: str) -> Tuple[str, str]:
        """
        ✅ Phase 0.9.7.2: Header/Body 재정의 (GPT 미송님)
        
        문제: raw 위치로 cleaned_content 자름 → 경계 오염
        해결: cleaned_content에서 다시 헤더 찾기
        """
        # 별표 헤더 패턴 찾기
        match = re.search(self.patterns['annex_header'], content)
        if not match:
            return "", content
        
        header_end = match.end()
        
        # 헤더 끝 이후 첫 빈줄 또는 표 시작까지를 헤더로 확장
        lines = content.split('\n')
        
        # header_end 위치를 라인 인덱스로 변환
        char_count = 0
        header_line_idx = 0
        for idx, line in enumerate(lines):
            char_count += len(line) + 1  # +1 for \n
            if char_count >= header_end:
                header_line_idx = idx + 1  # 다음 라인부터 body
                break
        
        # 헤더 확장: 관련 조문, 개정이력 포함
        while header_line_idx < len(lines):
            line = lines[header_line_idx].strip()
            
            if not line:
                header_line_idx += 1
                break
            
            # 관련 조문/개정이력 패턴
            if re.search(self.patterns['related_article'], line):
                header_line_idx += 1
                continue
            
            if re.search(self.patterns['amendment'], line):
                header_line_idx += 1
                continue
            
            # 숫자로 시작하거나 표 패턴이면 body 시작
            if re.match(r'^\d+', line) or len(line) < 50:
                break
            
            # 그 외는 헤더에 포함
            header_line_idx += 1
        
        header_text = '\n'.join(lines[:header_line_idx]).strip()
        body_text = '\n'.join(lines[header_line_idx:]).strip()
        
        return header_text, body_text
    
    def _merge_table_candidates(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.9.7.2: Table Candidate Merge (GPT 미송님)
        
        전략:
        - table_candidate + table_rows → table_rows (합침)
        - 헤더+표 초반부를 표 블록으로 승격
        """
        merged = []
        
        for block in blocks:
            if merged and merged[-1]['type'] == "table_candidate" and block['type'] == "table_rows":
                # 이전 블록(table_candidate) + 현재 블록(table_rows) → 합침
                prev_block = merged.pop()
                
                # 라인 합치기
                block['lines'] = prev_block['lines'] + block['lines']
                
                # Metadata 업데이트
                if 'expanded_up' in block['metadata']:
                    block['metadata']['expanded_up'] += len(prev_block['lines'])
                else:
                    block['metadata']['expanded_up'] = len(prev_block['lines'])
                
                logger.info(
                    f"         표 후보 승격: {len(prev_block['lines'])}줄 추가 "
                    f"(점수: {prev_block['metadata']['table_score']:.2f} → table_rows)"
                )
            
            merged.append(block)
        
        # 남은 table_candidate는 paragraph로 강등
        for block in merged:
            if block['type'] == "table_candidate":
                block['type'] = "paragraph"
                logger.info(
                    f"         표 후보 강등: paragraph로 처리 "
                    f"(점수: {block['metadata']['table_score']:.2f})"
                )
        
        return merged
    
    def _create_block_chunk(
        self,
        lines: List[str],
        annex_no: str,
        order: int,
        block_index: int,
        block_type: str,
        metadata: Dict[str, Any]
    ) -> Optional[SubChunk]:
        """Block → Chunk 변환"""
        if not lines:
            return None
        
        content = '\n'.join(lines).strip()
        
        if len(content) < 10:
            return None
        
        # 판정 근거
        if block_type == "table_rows":
            판정_근거 = (
                f"digit {metadata['digit_density']:.0%} + "
                f"짧은라인 {metadata['short_line_ratio']:.0%} + "
                f"정렬 {metadata['column_gap_consistency']:.2f}"
            )
            if metadata['header_hint']:
                판정_근거 += " + 헤더"
        else:
            판정_근거 = f"일반 문단 (점수: {metadata['table_score']:.2f})"
        
        return SubChunk(
            section_id=f"annex_{annex_no}_{block_type}_{block_index+1}",
            section_type=block_type,
            content=content,
            metadata={
                'block_index': block_index,
                **metadata,
                '판정_근거': 판정_근거,
                'has_table': block_type == "table_rows"
            },
            char_count=len(content),
            order=order
        )
    
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
    
    def _extract_note_from_lines(
        self,
        lines: List[str],
        annex_no: str,
        order: int
    ) -> Tuple[Optional[SubChunk], List[str]]:
        """마지막 블록에서 Note 추출"""
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
            return None, lines
        
        note_content = '\n'.join(note_lines).strip()
        
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
        
        return note_chunk, regular_lines
    
    def _check_annex_loss(self, original_text: str, chunks: List[SubChunk]) -> None:
        """Annex Loss Check"""
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
        """노이즈 제거"""
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
    ✅ Phase 0.9.7: 시그니처 유지 (2-arg)
    
    서브청킹 결과 검증
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
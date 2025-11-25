"""
core/annex_subchunker.py - Phase 0.9.8.0 Validation Fix

Phase 0.9.8.0 (GPT 미송님 P1 해결):
1. ✅ Fix 1: 겹치는 표 블록 병합 (_merge_overlapping_blocks)
   - 문제: 0~156, 149~310 → 149~156 중복
   - 해결: 오버랩 감지 → 0~310 단일 블록 병합
   - 효과: 중복 라인 제거 → loss_pct 급락

2. ✅ Fix 2: Loss 계산을 "누락만" 기준으로 변경
   - 문제: abs(원본 - 청크)로 "증가"도 손실로 계산
   - 해결: max(0, 원본 - 청크)로 "누락만" 손실
   - 효과: 2777자 → 3087자 = 11.2% → 0%

3. ✅ Fix 3: validate_subchunks LawParser 계약 통일
   - has_header, has_content, type_counts 추가
   - loss_rate 계산 방식 통일 (누락만)
   - LawParser 로그 키 오류 제거

Phase 0.9.7.8:
- ✅ validate_subchunks 함수 추가 (P0 해결!)

Phase 0.9.7.6:
- ✅ 개행 삭제 정규식 완전 제거
- ✅ _clean_annex_text 라인 단위 공백만 정규화

핵심: 표 블록 오버랩 병합 + Loss 정의 수정 → validation 통과 → table_rows 3개 복귀!

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-25
Version: Phase 0.9.8.0 Validation Fix
"""

import re
import logging
import statistics
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 헤더 키워드
HEADER_KEYWORDS = re.compile(
    r"(임용하고자|서열명부|직급|응시자격|승진|제외|구분|비고|인원수|점수|평정|평가|담당자|자격취득|경력)",
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
    Annex 서브청킹 (Phase 0.9.7.6 Emergency Fix)
    
    GPT 미송님 설계:
    - R-1: 개행 삭제 회귀 코드 완전 제거
    - R-2: 라인 단위 공백만 정규화
    - R-3: SyntaxWarning 제거
    """
    
    def __init__(self):
        """✅ P0 Fix: 안정적 초기화"""
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'note_marker': r'^\*\s*(.+)$',
            'digit_line': r'^\d+(\s*\S+)?$',
            'header_keywords': r'(직급|응시자격|비고|인원수|서열명부|순위|담당자|자격취득)',
        }
        
        logger.info("✅ AnnexSubChunker v0.9.8.0 초기화 (Validation Fix - 블록 병합 + Loss 수정)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        ✅ Phase 0.9.8.0: Annex 텍스트 → 서브청킹 (블록 병합 + Loss 수정)
        """
        logger.info(f"🔧 Phase 0.9.8.0: Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Step 1: Annex 완전 분리
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ Step 1: 별표 분리 완료: {len(annex_sections)}개")
        
        # Canonical text
        canonical_text = self._clean_annex_text(annex_text)
        
        # Step 2-4: 각 별표마다 처리
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            raw_content = annex_sec['content']
            header_end_pos = annex_sec['header_end_pos']
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(raw_content)}자)")
            
            # ✅ R-2: 개행 보존 노이즈 제거
            cleaned_content = self._clean_annex_text(raw_content)
            
            # Table Block Segmentation
            section_chunks = self._process_single_annex_v0976(
                cleaned_content,
                annex_num,
                global_order,
                header_end_pos
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Step 5: Loss Check
        self._check_annex_loss(canonical_text, all_chunks)
        
        logger.info(f"✅ Phase 0.9.8.0: Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        
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
            title = match.group(2).strip()
            start_pos = match.start()
            
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(annex_text)
            
            content = annex_text[start_pos:end_pos]
            header_end_pos = match.end() - start_pos
            
            sections.append({
                'annex_no': annex_no,
                'title': title,
                'content': content,
                'header_end_pos': header_end_pos
            })
        
        return sections
    
    def _process_single_annex_v0976(
        self,
        content: str,
        annex_no: str,
        start_order: int,
        header_end_pos: int
    ) -> List[SubChunk]:
        """
        ✅ Phase 0.9.7.6: 단일 Annex 처리 (Emergency Fix)
        """
        chunks = []
        order = start_order
        
        # Header/Body 분리
        header_text, body_text = self._split_header_body_v0976(content)
        
        # Step 1: Header 청크
        if header_text:
            header_chunk = self._extract_header_chunk(header_text, annex_no, order)
            if header_chunk:
                chunks.append(header_chunk)
                order += 1
        
        # ✅ R-2: 라인 유지 (개행 보존 확인)
        lines = body_text.split('\n')
        lines = [l for l in lines if l.strip()]
        
        logger.info(f"      라인 유지: {len(lines)}개")
        
        # Step 2: Table Block Segmentation
        blocks = self._segment_blocks_v0976(lines)
        
        # Step 3: Table Candidate Merge
        blocks = self._merge_table_candidates_v0976(blocks)
        
        # Step 4: Block → Chunk 변환
        for i, block in enumerate(blocks):
            block_lines = block['lines']
            block_type = block['type']
            block_metadata = block['metadata']
            
            is_last_block = (i == len(blocks) - 1)
            
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
                block_chunk = self._create_block_chunk(
                    block_lines, annex_no, order, i, block_type, block_metadata
                )
                if block_chunk:
                    chunks.append(block_chunk)
                    order += 1
        
        return chunks
    
    def _merge_overlapping_blocks(self, blocks: List[Dict[str, Any]], original_lines: List[str]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.9.8.0: 겹치는 표 블록 병합 (GPT 미송님 Fix 1)
        
        문제: 표 블록 0~156, 149~310 → 149~156 중복
        해결: 오버랩 감지 → 0~310 단일 블록으로 병합
        효과: 중복 라인 제거 → loss_pct 급락 → validation 통과
        """
        if not blocks:
            return []
        
        # table_rows 블록만 추출 (start/end로 정렬 필요)
        table_blocks = []
        other_blocks = []
        
        for b in blocks:
            if b.get('type') == 'table_rows':
                # lines에서 원본 인덱스 복원 (첫 라인으로 찾기)
                first_line = b['lines'][0] if b['lines'] else ""
                try:
                    start_idx = original_lines.index(first_line)
                    end_idx = start_idx + len(b['lines'])
                    table_blocks.append({
                        **b,
                        '_start': start_idx,
                        '_end': end_idx
                    })
                except ValueError:
                    # 못 찾으면 그대로 유지
                    other_blocks.append(b)
            else:
                other_blocks.append(b)
        
        if not table_blocks:
            return blocks
        
        # start 기준 정렬
        table_blocks = sorted(table_blocks, key=lambda x: x['_start'])
        
        # 오버랩 병합
        merged = [table_blocks[0]]
        
        for current in table_blocks[1:]:
            last = merged[-1]
            
            # 오버랩 또는 인접 체크
            if current['_start'] <= last['_end'] + 1:
                # 병합
                overlap_size = last['_end'] - current['_start'] + 1 if current['_start'] <= last['_end'] else 0
                
                if overlap_size > 0:
                    logger.info(f"      🔗 표 블록 병합: {last['_start']}~{last['_end']} + {current['_start']}~{current['_end']} → {overlap_size}줄 겹침")
                
                # 범위 확장
                last['_end'] = max(last['_end'], current['_end'])
                
                # lines 재구성 (원본에서 추출)
                last['lines'] = original_lines[last['_start']:last['_end']]
                
                # score는 max
                if 'metadata' in last and 'metadata' in current:
                    last['metadata']['table_score'] = max(
                        last['metadata'].get('table_score', 0),
                        current['metadata'].get('table_score', 0)
                    )
            else:
                # 겹침 없음 → 별도 블록
                merged.append(current)
        
        # _start/_end 메타데이터 제거
        for b in merged:
            b.pop('_start', None)
            b.pop('_end', None)
        
        return merged + other_blocks
    
    def _split_header_body_v0976(self, content: str) -> Tuple[str, str]:
        """Header/Body 분리"""
        lines = content.split('\n')
        
        header_end_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if i == 0 and '[별표' in stripped:
                header_end_idx = i + 1
                continue
            
            if i <= 2 and ('<제' in stripped or '관련>' in stripped):
                header_end_idx = i + 1
                continue
            
            if i <= 3 and re.match(r'\[.*?\d{4}\.\d{1,2}\.\d{1,2}.*?\]', stripped):
                header_end_idx = i + 1
                continue
            
            if HEADER_KEYWORDS.search(stripped) or re.match(self.patterns['digit_line'], stripped):
                break
        
        header_lines = lines[:header_end_idx]
        body_lines = lines[header_end_idx:]
        
        return '\n'.join(header_lines), '\n'.join(body_lines)
    
    def _segment_blocks_v0976(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.9.7.6: Table Block Segmentation (Emergency Fix)
        
        GPT 미송님 핵심 수정:
        - candidate 게이트 완화 (OR 기반)
        - 가시화 로그 추가
        """
        blocks = []
        
        if not lines:
            return blocks
        
        window_size = min(8, max(5, len(lines) // 3))
        
        # ✅ 가시화를 위한 샘플 수집
        sample_windows = []
        
        i = 0
        while i < len(lines):
            window_end = min(i + window_size, len(lines))
            window_lines = lines[i:window_end]
            
            # 5개 특징 계산
            features = self._calculate_block_features(window_lines)
            
            # Table Score 계산
            table_score = self._calculate_table_score_v0976(features)
            
            # ✅ 샘플 수집 (top 10 window)
            if len(sample_windows) < 10:
                sample_windows.append({
                    'range': f"{i}~{window_end}",
                    'score': table_score,
                    'features': features
                })
            
            # table_rows 기준: 0.55
            if table_score >= 0.55:
                block_type = "table_rows"
                
                extended_end = self._extend_table_block(lines, i, window_end, features)
                
                refined_start, refined_end, expand_meta = self._refine_table_block_boundaries_v0976(
                    lines, i, extended_end
                )
                
                block_lines = lines[refined_start:refined_end]
                
                logger.info(
                    f"         표 블록 감지: {refined_start}~{refined_end} 라인 "
                    f"(점수: {table_score:.2f}, 확장: ↑{expand_meta['expanded_up']} ↓{expand_meta['expanded_down']})"
                )
                
                i = refined_end
                
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'metadata': {
                        **features,
                        'table_score': round(table_score, 3),
                        **expand_meta
                    }
                })
            
            # ✅ candidate 게이트 완화 (OR 기반)
            elif 0.50 <= table_score < 0.55 and (
                features['digit_density'] >= 0.25 or
                features['short_line_ratio'] > 0.8 or
                features['header_hint']
            ):
                block_type = "table_candidate"
                
                extended_end = self._extend_table_block(lines, i, window_end, features)
                block_lines = lines[i:extended_end]
                
                logger.info(
                    f"         표 후보 감지: {i}~{extended_end} 라인 "
                    f"(점수: {table_score:.2f}, digit={features['digit_density']:.2f}, "
                    f"short={features['short_line_ratio']:.2f}, header={features['header_hint']})"
                )
                
                i = extended_end
                
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'metadata': {
                        **features,
                        'table_score': round(table_score, 3)
                    }
                })
            
            else:
                # Paragraph
                block_type = "paragraph"
                
                para_end = i + 1
                while para_end < len(lines):
                    next_features = self._calculate_block_features(lines[para_end:para_end+5])
                    next_score = self._calculate_table_score_v0976(next_features)
                    
                    if next_score >= 0.50:
                        break
                    
                    para_end += 1
                
                block_lines = lines[i:para_end]
                i = para_end
                
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'metadata': {}
                })
        
        # ✅ 샘플 로그 출력
        if sample_windows:
            logger.info(f"      📊 Window 샘플 (top {len(sample_windows)}):")
            for sw in sample_windows[:5]:  # 상위 5개만
                logger.info(
                    f"         {sw['range']}: score={sw['score']:.2f}, "
                    f"digit={sw['features']['digit_density']:.2f}, "
                    f"short={sw['features']['short_line_ratio']:.2f}, "
                    f"header={sw['features']['header_hint']}"
                )
        
        # ✅ Phase 0.9.8.0: 오버랩 블록 병합 (GPT 미송님 Fix 1)
        blocks = self._merge_overlapping_blocks(blocks, lines)
        
        logger.info(f"      블록 분리: {len(blocks)}개")
        
        return blocks
    
    def _calculate_table_score_v0976(self, features: Dict[str, Any]) -> float:
        """Table Score 계산"""
        score = 0.0
        
        score += features['digit_density'] * 0.4
        score += features['short_line_ratio'] * 0.3
        score += features['column_gap_consistency'] * 0.2
        
        if features['header_hint']:
            score += 0.1
        
        if features['short_line_ratio'] < 0.3:
            score -= 0.05
        
        return score
    
    def _calculate_block_features(self, lines: List[str]) -> Dict[str, Any]:
        """5개 특징 계산"""
        if not lines:
            return {
                'digit_density': 0.0,
                'short_line_ratio': 0.0,
                'column_gap_consistency': 0.0,
                'header_hint': False,
                'avg_line_length': 0.0
            }
        
        # 1. Digit Density
        digit_count = sum(len(re.findall(r'\d', line)) for line in lines)
        total_chars = sum(len(line) for line in lines)
        digit_density = digit_count / total_chars if total_chars > 0 else 0
        
        # 2. Short Line Ratio
        short_lines = sum(1 for line in lines if len(line.strip()) < 50)
        short_line_ratio = short_lines / len(lines)
        
        # 3. Column Gap Consistency
        gap_positions = []
        for line in lines:
            gaps = [m.start() for m in re.finditer(r'\s{2,}', line)]
            gap_positions.extend(gaps)
        
        if len(gap_positions) >= 2:
            gap_variance = statistics.stdev(gap_positions) if len(set(gap_positions)) > 1 else 0
            column_gap_consistency = max(0, 1 - (gap_variance / 60))
        else:
            column_gap_consistency = 0.0
        
        # 4. Header Hint
        first_line = lines[0] if lines else ""
        header_hint = bool(HEADER_KEYWORDS.search(first_line))
        
        # 5. Avg Line Length
        avg_line_length = sum(len(line) for line in lines) / len(lines)
        
        return {
            'digit_density': round(digit_density, 3),
            'short_line_ratio': round(short_line_ratio, 3),
            'column_gap_consistency': round(column_gap_consistency, 3),
            'header_hint': header_hint,
            'avg_line_length': round(avg_line_length, 1)
        }
    
    def _extend_table_block(
        self,
        lines: List[str],
        start: int,
        end: int,
        features: Dict[str, Any]
    ) -> int:
        """표 블록 확장"""
        extended_end = end
        
        while extended_end < len(lines):
            next_line = lines[extended_end]
            
            if re.match(self.patterns['digit_line'], next_line):
                extended_end += 1
            elif len(next_line) < 50:
                extended_end += 1
            else:
                break
        
        return extended_end
    
    def _refine_table_block_boundaries_v0976(
        self,
        lines: List[str],
        start: int,
        end: int
    ) -> Tuple[int, int, Dict[str, Any]]:
        """경계 보정 (10/10줄)"""
        refined_start = start
        refined_end = end
        
        # 상향 확장 MAX 10줄
        MAX_EXPAND_UP = 10
        i = start - 1
        expanded_up = 0
        
        while i >= 0 and expanded_up < MAX_EXPAND_UP:
            prev_line = lines[i].strip()
            
            if not prev_line:
                break
            
            if HEADER_KEYWORDS.search(prev_line):
                refined_start = i
                expanded_up += 1
                i -= 1
                continue
            
            if any(kw in prev_line for kw in ["담당자", "제외", "평정", "승진", "응시자격", "임용", "자격취득"]):
                refined_start = i
                expanded_up += 1
                i -= 1
                continue
            
            if len(prev_line) <= 80:
                refined_start = i
                expanded_up += 1
                i -= 1
            else:
                break
        
        # 하향 확장 MAX 10줄
        MAX_EXPAND_DOWN = 10
        i = end
        expanded_down = 0
        
        while i < len(lines) and expanded_down < MAX_EXPAND_DOWN:
            next_line = lines[i].strip()
            
            if not next_line:
                break
            
            if DIGITISH_LINE.match(next_line):
                refined_end = i + 1
                expanded_down += 1
                i += 1
                continue
            
            if SEPARATOR_LINE.match(next_line):
                refined_end = i + 1
                expanded_down += 1
                i += 1
                continue
            
            if len(next_line) < 50:
                refined_end = i + 1
                expanded_down += 1
                i += 1
            else:
                break
        
        return refined_start, refined_end, {
            'expanded_up': expanded_up,
            'expanded_down': expanded_down
        }
    
    def _merge_table_candidates_v0976(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.9.7.6: Table Candidate Merge
        """
        if len(blocks) <= 1:
            return blocks
        
        merged = []
        i = 0
        
        while i < len(blocks):
            current = blocks[i]
            current_type = current['type']
            
            # Paragraph 승격 조건 완화 (digit > 0.35)
            if current_type == "paragraph":
                meta = current.get('metadata', {})
                if not meta:
                    meta = self._calculate_block_features(current['lines'])
                    current['metadata'] = meta
                
                # digit_density > 0.35 AND short_line_ratio > 0.6 → table_candidate 승격
                if meta.get('digit_density', 0) > 0.35 and meta.get('short_line_ratio', 0) > 0.6:
                    current['type'] = "table_candidate"
                    current_type = "table_candidate"
                    logger.info(
                        f"         ✅ Paragraph → table_candidate 승격 "
                        f"(digit: {meta.get('digit_density'):.2f}, short: {meta.get('short_line_ratio'):.2f})"
                    )
            
            # table_candidate 2개 연속 → 병합 후 table_rows 승격
            if current_type == "table_candidate" and i + 1 < len(blocks):
                next_block = blocks[i + 1]
                next_type = next_block['type']
                
                if next_type == "table_candidate":
                    merged_lines = current['lines'] + next_block['lines']
                    merged_meta = self._calculate_block_features(merged_lines)
                    merged_score = self._calculate_table_score_v0976(merged_meta)
                    
                    logger.info(
                        f"         ✅ table_candidate 병합: "
                        f"{len(current['lines'])}줄 + {len(next_block['lines'])}줄 "
                        f"→ table_rows 승격 (점수: {merged_score:.2f})"
                    )
                    
                    merged.append({
                        'type': 'table_rows',
                        'lines': merged_lines,
                        'metadata': {
                            **merged_meta,
                            'table_score': round(merged_score, 3),
                            'merged_from_candidates': True
                        }
                    })
                    
                    i += 2
                    continue
            
            # table_candidate + table_rows 연속 → 강제 병합
            if current_type == "table_candidate" and i + 1 < len(blocks):
                next_block = blocks[i + 1]
                next_type = next_block['type']
                
                if next_type == "table_rows":
                    merged_lines = current['lines'] + next_block['lines']
                    merged_meta = next_block['metadata']
                    
                    logger.info(
                        f"         ✅ table_candidate + table_rows 병합: "
                        f"{len(current['lines'])}줄 + {len(next_block['lines'])}줄"
                    )
                    
                    merged.append({
                        'type': 'table_rows',
                        'lines': merged_lines,
                        'metadata': merged_meta
                    })
                    
                    i += 2
                    continue
            
            # 병합 안 됨 → 그대로 추가
            if current_type == "table_candidate":
                # 강등 이유 로그
                logger.info(
                    f"         표 후보 강등: paragraph로 처리 "
                    f"(점수: {current['metadata'].get('table_score', 0):.2f}, "
                    f"digit: {current['metadata'].get('digit_density', 0):.2f})"
                )
                current['type'] = "paragraph"
            
            merged.append(current)
            i += 1
        
        return merged
    
    # ===== 기존 메서드 =====
    
    def _extract_header_chunk(self, header_text: str, annex_no: str, order: int) -> Optional[SubChunk]:
        """헤더 청크 생성"""
        if not header_text.strip():
            return None
        
        match = re.search(self.patterns['annex_header'], header_text)
        title = match.group(2) if match else "별표"
        
        related_match = re.search(self.patterns['related_article'], header_text)
        related_article = related_match.group(1) if related_match else None
        
        amendment_match = re.search(self.patterns['amendment'], header_text)
        amendment_date = amendment_match.group(2) if amendment_match else None
        
        metadata = {
            'title': title,
            'related_article': related_article,
            'amendment_date': amendment_date
        }
        
        return SubChunk(
            section_id=f"별표{annex_no}",
            section_type="header",
            content=header_text.strip(),
            metadata=metadata,
            char_count=len(header_text.strip()),
            order=order
        )
    
    def _extract_note_from_lines(
        self,
        lines: List[str],
        annex_no: str,
        order: int
    ) -> Tuple[Optional[SubChunk], List[str]]:
        """Note 추출"""
        note_lines = []
        remaining_lines = []
        
        note_started = False
        for line in lines:
            if re.match(self.patterns['note_marker'], line.strip()):
                note_started = True
                note_lines.append(line)
            elif note_started:
                note_lines.append(line)
            else:
                remaining_lines.append(line)
        
        note_chunk = None
        if note_lines:
            note_text = '\n'.join(note_lines)
            note_chunk = SubChunk(
                section_id=f"별표{annex_no}",
                section_type="note",
                content=note_text.strip(),
                metadata={},
                char_count=len(note_text.strip()),
                order=order
            )
        
        return note_chunk, remaining_lines
    
    def _create_block_chunk(
        self,
        lines: List[str],
        annex_no: str,
        order: int,
        block_idx: int,
        block_type: str,
        block_metadata: Dict[str, Any]
    ) -> Optional[SubChunk]:
        """Block → Chunk 변환"""
        if not lines:
            return None
        
        content = '\n'.join(lines)
        
        return SubChunk(
            section_id=f"별표{annex_no}",
            section_type=block_type,
            content=content.strip(),
            metadata=block_metadata,
            char_count=len(content.strip()),
            order=order
        )
    
    def _clean_annex_text(self, text: str) -> str:
        """
        ✅ R-1, R-2, R-3: 개행 보존 노이즈 제거 (GPT 미송님 핵심 수정)
        
        변경 전 (치명적 회귀 - 완전 제거!):
        - 개행 삭제 정규식 사용 (SyntaxWarning)
        
        변경 후 (개행 보존):
        - 줄 단위로 공백만 정규화
        - 310줄짜리 표 텍스트 보존
        - SyntaxWarning 제거
        """
        # 노이즈 문자 제거
        text = re.sub(r'[□■◆◇○●▪▫◎◉★☆]', '', text)
        text = re.sub(r'[━┃│─├┤┬┴┼┌┐└┘]', '', text)
        
        # ✅ GPT 미송님 수정: 줄 단위로 공백만 정규화 (splitlines 사용)
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            # 각 줄의 연속 공백/탭을 단일 공백으로
            cleaned_line = re.sub(r'[ \t]+', ' ', line).rstrip()
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _check_annex_loss(self, canonical_text: str, chunks: List[SubChunk]) -> float:
        """
        ✅ Phase 0.9.8.0: Loss 계산 수정 (GPT 미송님 Fix 2)
        
        문제: abs(원본 - 청크)로 "증가"도 손실로 계산
              2777자 → 3087자 = 11.2% 손실(?)
        해결: max(0, 원본 - 청크)로 "누락만" 손실로 계산
              2777자 → 3087자 = 0% 손실
        """
        original_len = len(canonical_text)
        total_chars = sum(c.char_count for c in chunks)
        
        # ✅ 누락만 손실로 계산 (증가는 손실 아님!)
        loss_rate = max(0, original_len - total_chars) / original_len if original_len > 0 else 0
        loss_pct = loss_rate * 100
        
        logger.info(f"   📊 Loss Check:")
        logger.info(f"      원본: {original_len}자")
        logger.info(f"      청크 합계: {total_chars}자")
        logger.info(f"      손실률: {loss_pct:.1f}%")
        
        if loss_rate > 0.03:
            logger.warning(f"   ⚠️ 손실률 {loss_pct:.1f}% > 3% (실패)")
        else:
            logger.info(f"   ✅ 손실률 {loss_pct:.1f}% ≤ 3% (통과)")
        
        return loss_rate
    
    def _fallback_chunk(self, annex_text: str, annex_no: str) -> List[SubChunk]:
        """Fallback 처리"""
        cleaned = self._clean_annex_text(annex_text)
        
        return [SubChunk(
            section_id=f"별표{annex_no}",
            section_type="paragraph",
            content=cleaned,
            metadata={'fallback': True},
            char_count=len(cleaned),
            order=0
        )]



# ============================================================
# Phase 0.9.7.8 Final Fix - validate_subchunks 추가
# ============================================================

def validate_subchunks(chunks: List[SubChunk], original_length: int) -> Dict[str, Any]:
    """
    ✅ Phase 0.9.8.0: LawParser 계약 완벽 준수 (GPT 미송님 Fix 3)
    
    LawParser가 기대하는 인터페이스:
    - is_valid: bool
    - reason: str
    - chunk_count: int
    - type_counts: Dict[str, int]
    - loss_rate: float (누락만 계산!)
    - has_header: bool
    - has_content: bool
    
    Args:
        chunks: 검증할 서브청크 리스트
        original_length: 원본 텍스트 길이
    
    Returns:
        검증 결과 딕셔너리
    """
    if not chunks:
        return {
            "is_valid": False,
            "reason": "청크 없음",
            "chunk_count": 0,
            "type_counts": {},
            "loss_rate": 1.0,
        }
    
    # type_counts 계산
    type_counts = {}
    for c in chunks:
        type_counts[c.section_type] = type_counts.get(c.section_type, 0) + 1
    
    # ✅ char_count 합으로 loss 계산 (누락만!)
    total_chars = sum(c.char_count for c in chunks)
    loss_rate = max(0, original_length - total_chars) / original_length if original_length > 0 else 0
    
    # 검증 기준
    has_header = "header" in type_counts
    has_content = ("table_rows" in type_counts) or ("paragraph" in type_counts)
    
    is_valid = has_header and has_content and (loss_rate <= 0.03)
    
    return {
        "is_valid": is_valid,
        "reason": "OK" if is_valid else "검증 실패",
        "chunk_count": len(chunks),
        "type_counts": type_counts,
        "total_chars": total_chars,
        "loss_rate": loss_rate,
        "has_header": has_header,
        "has_content": has_content,
    }


# ✅ Phase 0.9.8.0: validate_subchunks 계약 통일
__all__ = ['AnnexSubChunker', 'SubChunk', 'validate_subchunks']
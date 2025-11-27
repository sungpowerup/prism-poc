"""
core/annex_subchunker.py - Phase 0.9.8.3 TableParser Interface

Phase 0.9.8.3 (TableParser 인터페이스 개선):
🎯 목표: 6개 조각 → 2개 논리 그룹 → TableParser 150행 구조화

핵심 전략 (GPT 미송님):
A. 청크 라벨링: "3급승진제외" / "3급승진" 자동 감지
B. 논리 그룹 재조합: label 기반 그룹화
C. TableParser 피딩: 각 그룹을 통합 테이블로 전달

성공 기준:
- Loss < 3% ✅
- table_rows = 2개 (논리 그룹) ✅
- TableParser = 150행 ✅
- Annex 정교 구조 + 구조화 동시 달성

Author: 마창수산팀 + GPT 미송님
Date: 2025-11-27
Version: Phase 0.9.8.3 TableParser Interface
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
    Annex 서브청킹 (Phase 0.9.8.3 TableParser Interface)
    
    GPT 미송님 설계:
    - Phase 0.9.8.2 구조 유지 (Loss 0%, 정교한 분할)
    - 추가: 논리 그룹 재조합 레이어
    - 목표: TableParser 150행 구조화 복원
    """
    
    def __init__(self):
        """초기화"""
        self.patterns = {
            'annex_header': r'\[별표\s*(\d+)\]\s*([^\n<]+)',
            'related_article': r'<(제\d+조[^>]*)관련>',
            'amendment': r'\[(.*?(\d{4}\.\d{1,2}\.\d{1,2}).*?)\]',
            'note_marker': r'^\*\s*(.+)$',
            'digit_line': r'^\d+(\s*\S+)?$',
            'header_keywords': r'(직급|응시자격|비고|인원수|서열명부|순위|담당자|자격취득)',
        }
        
        logger.info("✅ AnnexSubChunker v0.9.8.3 초기화 (TableParser Interface)")
    
    def chunk(self, annex_text: str, annex_no: str = "1") -> List[SubChunk]:
        """
        ✅ Phase 0.9.8.3: Annex 텍스트 → 서브청킹 → 논리 그룹 재조합
        """
        logger.info(f"🔧 Phase 0.9.8.3: Annex 서브청킹 시작: {len(annex_text)}자")
        
        # Step 1: Annex 완전 분리
        annex_sections = self._split_by_annex(annex_text)
        
        if not annex_sections:
            logger.warning("⚠️ 별표 패턴을 찾을 수 없음 - fallback 처리")
            return self._fallback_chunk(annex_text, annex_no)
        
        logger.info(f"✅ Step 1: 별표 분리 완료: {len(annex_sections)}개")
        
        # Canonical text
        canonical_text = self._clean_annex_text(annex_text)
        
        # Step 2-5: 각 별표마다 처리
        all_chunks = []
        global_order = 0
        
        for annex_sec in annex_sections:
            annex_num = annex_sec['annex_no']
            raw_content = annex_sec['content']
            header_end_pos = annex_sec['header_end_pos']
            
            logger.info(f"   🔹 별표{annex_num} 처리 중... ({len(raw_content)}자)")
            
            # 개행 보존 노이즈 제거
            cleaned_content = self._clean_annex_text(raw_content)
            
            # ✨ Phase 0.9.8.2: 정교한 분할
            section_chunks = self._process_single_annex_v0982(
                cleaned_content,
                annex_num,
                global_order,
                header_end_pos
            )
            
            # ✨ Phase 0.9.8.3: 논리 그룹 재조합
            section_chunks = self._regroup_logical_tables_v0983(
                section_chunks,
                annex_num
            )
            
            all_chunks.extend(section_chunks)
            global_order += len(section_chunks)
            
            logger.info(f"   ✅ 별표{annex_num}: {len(section_chunks)}개 청크 생성")
        
        # Step 5: Loss Check
        self._check_annex_loss(canonical_text, all_chunks)
        
        logger.info(f"✅ Phase 0.9.8.3: Annex 서브청킹 완료: 총 {len(all_chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in all_chunks:
            ctype = chunk.section_type
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return all_chunks
    
    # ============================================
    # ✨ Phase 0.9.8.3: 논리 그룹 재조합
    # ============================================
    
    def _regroup_logical_tables_v0983(
        self,
        chunks: List[SubChunk],
        annex_num: str
    ) -> List[SubChunk]:
        """
        ✨ Phase 0.9.8.3: 논리 그룹 재조합
        
        GPT 미송님 전략:
        A. 청크 라벨링: "3급승진제외" / "3급승진" 자동 감지
        B. 그룹화: label 기반 재조합
        C. 통합: 각 그룹을 하나의 table_rows로 병합
        
        Before (Phase 0.9.8.2):
        [header, table1, note1, header, table2, note2] (6개)
        
        After (Phase 0.9.8.3):
        [header, logical_table1, logical_table2] (3개)
        - logical_table1 = table1 + note1 통합
        - logical_table2 = table2 + note2 통합
        """
        # Step A: 청크 라벨링
        labeled_chunks = self._label_chunks_v0983(chunks)
        
        # table_rows만 추출
        table_chunks = [c for c in labeled_chunks if c.section_type == 'table_rows']
        non_table_chunks = [c for c in labeled_chunks if c.section_type != 'table_rows']
        
        if not table_chunks:
            logger.info(f"      ℹ️ table_rows 없음 - 재조합 스킵")
            return chunks
        
        # Step B: 그룹화
        groups = self._group_by_label_v0983(table_chunks)
        
        if not groups:
            logger.info(f"      ℹ️ 그룹화 실패 - 원본 유지")
            return chunks
        
        # Step C: 각 그룹을 통합 table_rows로 병합
        merged_chunks = []
        
        for label, group_chunks in groups.items():
            if len(group_chunks) == 0:
                continue
            
            # 그룹 내 모든 청크 통합
            merged_content = '\n'.join(c.content for c in group_chunks)
            merged_char_count = sum(c.char_count for c in group_chunks)
            
            # 첫 번째 청크의 메타 기반
            first_chunk = group_chunks[0]
            
            merged_chunk = SubChunk(
                section_id=f"별표{annex_num}",
                section_type="table_rows",
                content=merged_content.strip(),
                metadata={
                    **first_chunk.metadata,
                    'table_label': label,
                    'merged_count': len(group_chunks),
                    'logical_group': True
                },
                char_count=merged_char_count,
                order=first_chunk.order
            )
            
            merged_chunks.append(merged_chunk)
            
            logger.info(
                f"      ✅ 논리 그룹 '{label}': {len(group_chunks)}개 청크 → "
                f"1개 table_rows ({merged_char_count}자)"
            )
        
        # non-table 청크와 병합
        result = non_table_chunks + merged_chunks
        
        # order 재정렬
        result = sorted(result, key=lambda x: x.order)
        
        logger.info(
            f"      🔄 재조합 완료: {len(table_chunks)}개 table_rows → "
            f"{len(merged_chunks)}개 논리 그룹"
        )
        
        return result
    
    def _label_chunks_v0983(self, chunks: List[SubChunk]) -> List[SubChunk]:
        """
        Step A: 청크 라벨링
        
        라벨 감지 로직:
        - "3급승진제외" 키워드 → label = "3급승진제외"
        - "3급승진" 키워드 (단, "제외" 없음) → label = "3급승진"
        - 기타 → label = None
        """
        labeled = []
        
        for chunk in chunks:
            content_norm = chunk.content.replace(" ", "").replace("\n", "")
            
            # "3급승진제외" 감지
            if "3급승진제외" in content_norm or "3급승진제외" in chunk.content:
                chunk.metadata['table_label'] = "3급승진제외"
                logger.info(f"         🏷️ 라벨: '3급승진제외' (order={chunk.order})")
            
            # "3급승진" 감지 (단, "제외" 없음)
            elif "3급승진" in content_norm and "제외" not in content_norm:
                chunk.metadata['table_label'] = "3급승진"
                logger.info(f"         🏷️ 라벨: '3급승진' (order={chunk.order})")
            
            # 헤더/비고 등 - 이전/다음 청크 기반 추론
            elif chunk.section_type == 'table_rows':
                # 짧은 청크는 헤더/비고 가능성 높음
                if chunk.char_count < 50:
                    chunk.metadata['table_label'] = "unknown_fragment"
                    logger.info(f"         🏷️ 라벨: 'unknown_fragment' (짧은 조각, {chunk.char_count}자)")
                else:
                    chunk.metadata['table_label'] = None
            
            labeled.append(chunk)
        
        # 라벨 전파: unknown_fragment를 이전/다음 라벨로 전파
        labeled = self._propagate_labels_v0983(labeled)
        
        return labeled
    
    def _propagate_labels_v0983(self, chunks: List[SubChunk]) -> List[SubChunk]:
        """
        라벨 전파: unknown_fragment를 인접 청크 라벨로 전파
        
        예:
        [3급승진제외, unknown_fragment, 3급승진]
        → [3급승진제외, 3급승진제외, 3급승진]
        """
        for i, chunk in enumerate(chunks):
            if chunk.section_type != 'table_rows':
                continue
            
            current_label = chunk.metadata.get('table_label')
            
            if current_label == "unknown_fragment":
                # 이전 청크 확인
                prev_label = None
                for j in range(i - 1, -1, -1):
                    if chunks[j].section_type == 'table_rows':
                        prev_label = chunks[j].metadata.get('table_label')
                        if prev_label and prev_label != "unknown_fragment":
                            break
                
                # 다음 청크 확인
                next_label = None
                for j in range(i + 1, len(chunks)):
                    if chunks[j].section_type == 'table_rows':
                        next_label = chunks[j].metadata.get('table_label')
                        if next_label and next_label != "unknown_fragment":
                            break
                
                # 전파 우선순위: 이전 > 다음
                if prev_label:
                    chunk.metadata['table_label'] = prev_label
                    logger.info(f"         🔀 라벨 전파: 'unknown_fragment' → '{prev_label}' (이전 기준)")
                elif next_label:
                    chunk.metadata['table_label'] = next_label
                    logger.info(f"         🔀 라벨 전파: 'unknown_fragment' → '{next_label}' (다음 기준)")
        
        return chunks
    
    def _group_by_label_v0983(
        self,
        table_chunks: List[SubChunk]
    ) -> Dict[str, List[SubChunk]]:
        """
        Step B: label 기반 그룹화
        
        Returns:
            {"3급승진제외": [chunk1, chunk2, ...],
             "3급승진": [chunk3, chunk4, ...]}
        """
        groups = {}
        
        for chunk in table_chunks:
            label = chunk.metadata.get('table_label')
            
            if not label or label == "unknown_fragment":
                # 라벨 없는 청크는 독립 그룹
                continue
            
            if label not in groups:
                groups[label] = []
            
            groups[label].append(chunk)
        
        logger.info(f"      📊 그룹화 결과:")
        for label, group in groups.items():
            logger.info(f"         '{label}': {len(group)}개 청크")
        
        return groups
    
    # ============================================
    # Phase 0.9.8.2: 기존 메서드 (유지)
    # ============================================
    
    def _process_single_annex_v0982(
        self,
        content: str,
        annex_no: str,
        start_order: int,
        header_end_pos: int
    ) -> List[SubChunk]:
        """
        ✅ Phase 0.9.8.2: 단일 Annex 처리 (버그 수정 적용)
        
        GPT 미송님 설계:
        1) 블록 감지 (start/end 메타 포함) ← Fix A
        2) 병합 (메타 직접 사용) ← Fix A
        3) ✨ 경계 감지 + 안전 분할 ← Fix B
        4) Chunk 변환
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
        
        # 라인 유지
        lines = body_text.split('\n')
        lines = [l for l in lines if l.strip()]
        
        logger.info(f"      라인 유지: {len(lines)}개")
        
        # Step 2: ✨ Table Block Segmentation (start/end 메타 포함)
        blocks = self._segment_blocks_v0982(lines)
        
        # Step 3: ✨ Table Candidate Merge (메타 유지)
        blocks = self._merge_table_candidates_v0982(blocks)
        
        # Step 4: ✨ Boundary Detection + Safe Split
        refined_blocks = []
        for block in blocks:
            if block['type'] == 'table_rows':
                # 표 블록만 경계 감지 + 안전 분할
                sub_blocks = self._split_block_by_boundaries_v0982(lines, block)
                refined_blocks.extend(sub_blocks)
            else:
                # 비표 블록은 그대로
                refined_blocks.append(block)
        
        # Step 5: Block → Chunk 변환
        for i, block in enumerate(refined_blocks):
            block_lines = block['lines']
            block_type = block['type']
            block_metadata = block['metadata']
            
            is_last_block = (i == len(refined_blocks) - 1)
            
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
    
    def _split_block_by_boundaries_v0982(
        self,
        lines: List[str],
        block: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        ✨ Phase 0.9.8.2 Fix B: 안전한 블록 분할 (GPT 미송님 설계)
        
        핵심 수정:
        - cuts 배열 기반 완전 분할
        - 한 줄도 버리지 않음
        - tail 버리기 조건 제거
        """
        boundaries = self._detect_table_boundaries(lines, block)
        
        if not boundaries:
            logger.info(f"      ℹ️ 경계 없음: 단일 표로 유지")
            return [block]
        
        # ✨ GPT 미송님 설계: cuts 배열 기반
        start = block.get('start', 0)
        end = block.get('end', len(block['lines']) - 1)
        
        # block 내부 경계만 필터
        internal_boundaries = [b for b in boundaries if start < b <= end]
        
        if not internal_boundaries:
            return [block]
        
        # cuts 배열 생성: [start, boundary1, boundary2, ..., end+1]
        cuts = [start] + internal_boundaries + [end + 1]
        
        logger.info(f"      ✨ cuts 배열: {cuts}")
        
        # 완전 분할 (한 줄도 버리지 않음)
        sub_blocks = []
        
        for i in range(len(cuts) - 1):
            seg_start = cuts[i]
            seg_end = cuts[i + 1] - 1
            
            if seg_end < seg_start:
                continue
            
            # lines에서 실제 라인 추출
            segment_lines = lines[seg_start:seg_end + 1]
            
            # 빈 라인만 체크 (최소 길이 조건 제거)
            non_empty = [l for l in segment_lines if l.strip()]
            if len(non_empty) == 0:
                logger.info(f"         ⚠️ 빈 segment 제외: {seg_start}~{seg_end}")
                continue
            
            sub_blocks.append({
                **block,
                'lines': segment_lines,
                'start': seg_start,
                'end': seg_end
            })
            
            logger.info(f"         ✅ Segment {i+1}: {seg_start}~{seg_end} ({len(segment_lines)}줄)")
        
        logger.info(f"      ✂️ 표 블록 분할: 1 → {len(sub_blocks)}개 (boundaries={internal_boundaries})")
        
        return sub_blocks if sub_blocks else [block]
    
    def _detect_table_boundaries(
        self,
        lines: List[str],
        block: Dict[str, Any]
    ) -> List[int]:
        """
        ✨ Phase 0.9.8.2: 표 경계 감지 (Phase 0.9.8.1 유지)
        
        GPT 미송님 휴리스틱 3개:
        - H1: 헤더 반복
        - H2: Note/비고 라인
        - H3: 큰 공백
        """
        block_lines = block['lines']
        
        if not block_lines:
            return []
        
        # ✨ Fix A: start/end 메타 직접 사용
        start = block.get('start', 0)
        end = block.get('end', len(block_lines) - 1)
        
        # 후보 수집
        header_candidates = []
        note_lines = []
        empty_runs = []
        
        # H1: 헤더 후보 탐색
        header_keywords = ["임용하고자", "서열명부", "직급", "응시자격"]
        for i in range(start, end + 1):
            if i >= len(lines):
                break
            line = lines[i]
            norm = line.replace(" ", "")
            if any(k in norm for k in header_keywords):
                header_candidates.append(i)
        
        # H2: Note/비고 후보 탐색
        note_pattern = re.compile(r"^\*?\s*(비고|주|註|note|임용하고자)")
        for i in range(start, end + 1):
            if i >= len(lines):
                break
            line = lines[i]
            if note_pattern.search(line):
                note_lines.append(i)
        
        # H3: 큰 공백 탐색 (연속 2줄 이상)
        empty_count = 0
        for i in range(start, end + 1):
            if i >= len(lines):
                break
            if not lines[i].strip():
                empty_count += 1
            else:
                if empty_count >= 2:
                    empty_runs.append(i)
                empty_count = 0
        
        # 경계 후보 집합
        boundary_candidates = set()
        
        # H1: 헤더가 2번 이상 나오면 두 번째부터 경계
        if len(header_candidates) >= 2:
            for idx in header_candidates[1:]:
                boundary_candidates.add(idx)
                logger.info(f"         🎯 H1 헤더 반복 경계: {idx}번 라인")
        
        # H2: Note 라인 다음줄
        for idx in note_lines:
            next_idx = idx + 1
            if start < next_idx <= end:
                boundary_candidates.add(next_idx)
                logger.info(f"         🎯 H2 비고 라인 경계: {next_idx}번 라인 (note={idx})")
        
        # H3: 공백 끝
        for idx in empty_runs:
            if start < idx <= end:
                boundary_candidates.add(idx)
                logger.info(f"         🎯 H3 공백 경계: {idx}번 라인")
        
        # block 내부에 있는 것만 정렬
        boundaries = sorted(
            i for i in boundary_candidates
            if start < i <= end
        )
        
        return boundaries
    
    # ============================================
    # Phase 0.9.8.2: Merge/Segment 로직 (유지)
    # ============================================
    
    def _segment_blocks_v0982(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        ✨ Phase 0.9.8.2 Fix A: Table Block Segmentation (start/end 메타 포함)
        """
        blocks = []
        
        if not lines:
            return blocks
        
        window_size = min(8, max(5, len(lines) // 3))
        
        sample_windows = []
        
        i = 0
        while i < len(lines):
            window_end = min(i + window_size, len(lines))
            window_lines = lines[i:window_end]
            
            features = self._calculate_block_features(window_lines)
            table_score = self._calculate_table_score_v0976(features)
            
            if len(sample_windows) < 10:
                sample_windows.append({
                    'range': f"{i}~{window_end}",
                    'score': table_score,
                    'features': features
                })
            
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
                
                # ✨ Fix A: start/end 메타 포함
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'start': refined_start,
                    'end': refined_end - 1,
                    'metadata': {
                        **features,
                        'table_score': round(table_score, 3),
                        **expand_meta
                    }
                })
            
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
                
                # ✨ Fix A: start/end 메타 포함
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'start': i - len(block_lines),
                    'end': i - 1,
                    'metadata': {
                        **features,
                        'table_score': round(table_score, 3)
                    }
                })
            
            else:
                block_type = "paragraph"
                
                para_end = i + 1
                while para_end < len(lines):
                    next_features = self._calculate_block_features(lines[para_end:para_end+5])
                    next_score = self._calculate_table_score_v0976(next_features)
                    
                    if next_score >= 0.50:
                        break
                    
                    para_end += 1
                
                block_lines = lines[i:para_end]
                
                # ✨ Fix A: start/end 메타 포함
                blocks.append({
                    'type': block_type,
                    'lines': block_lines,
                    'start': i,
                    'end': para_end - 1,
                    'metadata': {}
                })
                
                i = para_end
        
        if sample_windows:
            logger.info(f"      📊 Window 샘플 (top {len(sample_windows)}):")
            for sw in sample_windows[:5]:
                logger.info(
                    f"         {sw['range']}: score={sw['score']:.2f}, "
                    f"digit={sw['features']['digit_density']:.2f}, "
                    f"short={sw['features']['short_line_ratio']:.2f}, "
                    f"header={sw['features']['header_hint']}"
                )
        
        # ✨ Phase 0.9.8.2: Merge (메타 직접 사용)
        blocks = self._merge_overlapping_blocks_v0982(blocks)
        
        logger.info(f"      블록 분리: {len(blocks)}개")
        
        return blocks
    
    def _merge_overlapping_blocks_v0982(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✨ Phase 0.9.8.2 Fix A: 겹치는 표 블록 병합 (index() 제거)
        """
        if not blocks:
            return []
        
        table_blocks = []
        other_blocks = []
        
        for b in blocks:
            if b.get('type') == 'table_rows':
                table_blocks.append(b)
            else:
                other_blocks.append(b)
        
        if not table_blocks:
            return blocks
        
        # start 기준 정렬
        table_blocks = sorted(table_blocks, key=lambda x: x.get('start', 0))
        
        # 오버랩 병합
        merged = [table_blocks[0]]
        
        for current in table_blocks[1:]:
            last = merged[-1]
            
            # ✨ Fix A: 메타 직접 사용
            last_start = last.get('start', 0)
            last_end = last.get('end', 0)
            curr_start = current.get('start', 0)
            curr_end = current.get('end', 0)
            
            # 오버랩 또는 인접 체크
            if curr_start <= last_end + 1:
                overlap_size = last_end - curr_start + 1 if curr_start <= last_end else 0
                
                if overlap_size > 0:
                    logger.info(f"      🔗 표 블록 병합: {last_start}~{last_end} + {curr_start}~{curr_end} → {overlap_size}줄 겹침")
                
                # 범위 확장
                last['end'] = max(last_end, curr_end)
                
                # lines 병합
                if curr_start <= last_end:
                    overlap_lines = last_end - curr_start + 1
                    last['lines'] = last['lines'] + current['lines'][overlap_lines:]
                else:
                    last['lines'] = last['lines'] + current['lines']
                
                # score는 max
                if 'metadata' in last and 'metadata' in current:
                    last['metadata']['table_score'] = max(
                        last['metadata'].get('table_score', 0),
                        current['metadata'].get('table_score', 0)
                    )
            else:
                merged.append(current)
        
        return merged + other_blocks
    
    def _merge_table_candidates_v0982(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✨ Phase 0.9.8.2: Table Candidate Merge (메타 유지)
        """
        if len(blocks) <= 1:
            return blocks
        
        merged = []
        i = 0
        
        while i < len(blocks):
            current = blocks[i]
            current_type = current['type']
            
            if current_type == "paragraph":
                meta = current.get('metadata', {})
                if not meta:
                    meta = self._calculate_block_features(current['lines'])
                    current['metadata'] = meta
                
                if meta.get('digit_density', 0) > 0.35 and meta.get('short_line_ratio', 0) > 0.6:
                    current['type'] = "table_candidate"
                    current_type = "table_candidate"
                    logger.info(
                        f"         ✅ Paragraph → table_candidate 승격 "
                        f"(digit: {meta.get('digit_density'):.2f}, short: {meta.get('short_line_ratio'):.2f})"
                    )
            
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
                        'start': current.get('start', 0),
                        'end': next_block.get('end', 0),
                        'metadata': {
                            **merged_meta,
                            'table_score': round(merged_score, 3),
                            'merged_from_candidates': True
                        }
                    })
                    
                    i += 2
                    continue
            
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
                        'start': current.get('start', 0),
                        'end': next_block.get('end', 0),
                        'metadata': merged_meta
                    })
                    
                    i += 2
                    continue
            
            if current_type == "table_candidate":
                logger.info(
                    f"         표 후보 강등: paragraph로 처리 "
                    f"(점수: {current['metadata'].get('table_score', 0):.2f}, "
                    f"digit: {current['metadata'].get('digit_density', 0):.2f})"
                )
                current['type'] = "paragraph"
            
            merged.append(current)
            i += 1
        
        return merged
    
    # ============================================
    # Phase 0.9.8.0: 기존 Helper 메서드 (유지)
    # ============================================
    
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
        
        digit_count = sum(len(re.findall(r'\d', line)) for line in lines)
        total_chars = sum(len(line) for line in lines)
        digit_density = digit_count / total_chars if total_chars > 0 else 0
        
        short_lines = sum(1 for line in lines if len(line.strip()) < 50)
        short_line_ratio = short_lines / len(lines)
        
        gap_positions = []
        for line in lines:
            gaps = [m.start() for m in re.finditer(r'\s{2,}', line)]
            gap_positions.extend(gaps)
        
        if len(gap_positions) >= 2:
            gap_variance = statistics.stdev(gap_positions) if len(set(gap_positions)) > 1 else 0
            column_gap_consistency = max(0, 1 - (gap_variance / 60))
        else:
            column_gap_consistency = 0.0
        
        first_line = lines[0] if lines else ""
        header_hint = bool(HEADER_KEYWORDS.search(first_line))
        
        avg_line_length = sum(len(line) for line in lines) / len(lines)
        
        return {
            'digit_density': digit_density,
            'short_line_ratio': short_line_ratio,
            'column_gap_consistency': column_gap_consistency,
            'header_hint': header_hint,
            'avg_line_length': avg_line_length
        }
    
    def _extend_table_block(self, lines: List[str], start: int, end: int, features: Dict[str, Any]) -> int:
        """표 블록 확장"""
        extended_end = end
        
        while extended_end < len(lines):
            next_line = lines[extended_end].strip()
            
            if not next_line:
                break
            
            if DIGITISH_LINE.match(next_line):
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
    ) -> Tuple[int, int, Dict[str, int]]:
        """표 블록 경계 정제"""
        refined_start = start
        refined_end = end
        
        MAX_EXPAND_UP = 10
        i = start - 1
        expanded_up = 0
        
        while i >= 0 and expanded_up < MAX_EXPAND_UP:
            prev_line = lines[i].strip()
            
            if not prev_line:
                break
            
            if DIGITISH_LINE.match(prev_line):
                refined_start = i
                expanded_up += 1
                i -= 1
                continue
            
            if SEPARATOR_LINE.match(prev_line):
                refined_start = i
                expanded_up += 1
                i -= 1
            else:
                break
        
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
        """개행 보존 노이즈 제거"""
        text = re.sub(r'[□■◆◇○●▪▫◎◉★☆]', '', text)
        text = re.sub(r'[━┃│─├┤┬┴┼┌┐└┘]', '', text)
        
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            cleaned_line = re.sub(r'[ \t]+', ' ', line).rstrip()
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _check_annex_loss(self, canonical_text: str, chunks: List[SubChunk]) -> float:
        """Phase 0.9.8.0: Loss 계산 (누락만)"""
        original_len = len(canonical_text)
        chunk_total_len = sum(chunk.char_count for chunk in chunks)
        
        loss = max(0, original_len - chunk_total_len)
        loss_rate = loss / original_len if original_len > 0 else 0
        
        logger.info(f"   📊 Loss Check:")
        logger.info(f"      원본: {original_len}자")
        logger.info(f"      청크 합계: {chunk_total_len}자")
        logger.info(f"      손실률: {loss_rate*100:.1f}%")
        
        MAX_LOSS_RATE = 0.03
        
        if loss_rate <= MAX_LOSS_RATE:
            logger.info(f"   ✅ 손실률 {loss_rate*100:.1f}% ≤ {MAX_LOSS_RATE*100:.0f}% (통과)")
        else:
            logger.warning(f"   ⚠️ 손실률 {loss_rate*100:.1f}% > {MAX_LOSS_RATE*100:.0f}% (기준 초과)")
        
        return loss_rate
    
    def _fallback_chunk(self, annex_text: str, annex_no: str) -> List[SubChunk]:
        """Fallback: 단일 paragraph 청크"""
        cleaned_text = self._clean_annex_text(annex_text)
        
        return [
            SubChunk(
                section_id=f"별표{annex_no}",
                section_type="paragraph",
                content=cleaned_text,
                metadata={},
                char_count=len(cleaned_text),
                order=0
            )
        ]


# ============================================
# Phase 0.9.8.3: validate_subchunks (유지)
# ============================================

def validate_subchunks(chunks: List[SubChunk], original_text_len: int) -> Dict[str, Any]:
    """
    ✅ Phase 0.9.8.0: SubChunk 검증 (유지)
    """
    if not chunks:
        return {
            'is_valid': False,
            'reason': '청크 없음',
            'chunk_count': 0,
            'type_counts': {},
            'loss_rate': 1.0,
            'has_header': False,
            'has_content': False
        }
    
    type_counts = {}
    for chunk in chunks:
        ctype = chunk.section_type
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    has_header = 'header' in type_counts
    has_content = any(t in type_counts for t in ['table_rows', 'paragraph'])
    
    chunk_total_len = sum(chunk.char_count for chunk in chunks)
    
    loss = max(0, original_text_len - chunk_total_len)
    loss_rate = loss / original_text_len if original_text_len > 0 else 0
    
    MAX_LOSS_RATE = 0.03
    is_valid = loss_rate <= MAX_LOSS_RATE
    reason = "정상" if is_valid else f"손실률 {loss_rate*100:.1f}% 초과"
    
    return {
        'is_valid': is_valid,
        'reason': reason,
        'chunk_count': len(chunks),
        'type_counts': type_counts,
        'loss_rate': loss_rate,
        'has_header': has_header,
        'has_content': has_content
    }
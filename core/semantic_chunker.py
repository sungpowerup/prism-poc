"""
core/semantic_chunker.py
PRISM Phase 5.2.0 - Semantic Chunker

목적: 의미 단위 기반 지능형 청킹
- 페이지 경계가 아닌 의미 단위로 분할
- 표/다이어그램 무결성 보존
- RAG 검색 최적화

Author: 박준호 (AI/ML Lead)
Date: 2025-10-25
Version: 5.2.0
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    의미 단위 기반 청킹 엔진
    
    전략:
    1. 헤더 기준 섹션 분할 (##, ###)
    2. 표/다이어그램 무결성 보존
    3. 목표 청크 크기 유지 (800-1000자)
    4. 청크 메타데이터 추가
    """
    
    def __init__(
        self,
        min_chunk_size: int = 600,
        max_chunk_size: int = 1200,
        target_chunk_size: int = 900
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기
            max_chunk_size: 최대 청크 크기
            target_chunk_size: 목표 청크 크기
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.target_chunk_size = target_chunk_size
        
        logger.info(f"✅ SemanticChunker 초기화")
        logger.info(f"   청크 크기: {min_chunk_size}-{max_chunk_size} (목표: {target_chunk_size})")
    
    def chunk(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Markdown을 의미 단위로 청킹
        
        Args:
            markdown: 전체 Markdown 문자열
        
        Returns:
            청크 리스트: [
                {
                    'chunk_id': str,
                    'content': str,
                    'char_count': int,
                    'type': 'section' | 'table' | 'mixed',
                    'headers': List[str],
                    'page_hint': int  # 페이지 번호 힌트
                },
                ...
            ]
        """
        logger.info(f"🔗 SemanticChunking 시작: {len(markdown)} 글자")
        
        # Step 1: 섹션 분할
        sections = self._split_by_headers(markdown)
        logger.info(f"   섹션 분할: {len(sections)}개")
        
        # Step 2: 청크 생성
        chunks = []
        for i, section in enumerate(sections):
            section_chunks = self._chunk_section(section, start_id=len(chunks))
            chunks.extend(section_chunks)
        
        logger.info(f"   ✅ {len(chunks)}개 청크 생성")
        
        # Step 3: 메타데이터 추가
        for chunk in chunks:
            self._add_metadata(chunk, markdown)
        
        return chunks
    
    def _split_by_headers(self, markdown: str) -> List[Dict[str, Any]]:
        """
        헤더 기준으로 섹션 분할
        
        Returns:
            [
                {
                    'header': str,
                    'level': int,  # 1, 2, 3
                    'content': str,
                    'has_table': bool
                },
                ...
            ]
        """
        sections = []
        
        # 헤더 패턴 (##, ###)
        header_pattern = r'^(#{1,3})\s+(.+)$'
        
        lines = markdown.split('\n')
        current_section = None
        
        for line in lines:
            match = re.match(header_pattern, line)
            
            if match:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)
                
                # 새 섹션 시작
                level = len(match.group(1))
                header = match.group(2).strip()
                
                current_section = {
                    'header': header,
                    'level': level,
                    'content': line + '\n',
                    'has_table': False
                }
            else:
                if current_section:
                    current_section['content'] += line + '\n'
                    
                    # 표 감지
                    if '|' in line and '---' not in line:
                        current_section['has_table'] = True
                else:
                    # 헤더 없는 첫 부분
                    if not sections:
                        current_section = {
                            'header': '(Intro)',
                            'level': 1,
                            'content': line + '\n',
                            'has_table': False
                        }
        
        # 마지막 섹션
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _chunk_section(
        self,
        section: Dict[str, Any],
        start_id: int
    ) -> List[Dict[str, Any]]:
        """
        섹션을 적절한 크기로 청킹
        
        전략:
        - 표가 있으면 무조건 1개 청크 (무결성 보존)
        - 표 없으면 목표 크기로 분할
        """
        content = section['content']
        char_count = len(content)
        
        # 표가 있으면 무조건 1개 청크
        if section['has_table']:
            return [{
                'chunk_id': f'chunk_{start_id}',
                'content': content,
                'char_count': char_count,
                'type': 'table',
                'headers': [section['header']],
                'page_hint': self._extract_page_hint(content)
            }]
        
        # 표 없고 목표 크기 이하면 1개 청크
        if char_count <= self.max_chunk_size:
            return [{
                'chunk_id': f'chunk_{start_id}',
                'content': content,
                'char_count': char_count,
                'type': 'section',
                'headers': [section['header']],
                'page_hint': self._extract_page_hint(content)
            }]
        
        # 표 없고 목표 크기 초과 → 분할
        return self._split_long_section(section, start_id)
    
    def _split_long_section(
        self,
        section: Dict[str, Any],
        start_id: int
    ) -> List[Dict[str, Any]]:
        """
        긴 섹션을 여러 청크로 분할
        
        전략:
        - 문단 단위로 분할 (\n\n)
        - 목표 크기 유지
        """
        content = section['content']
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = ''
        chunk_headers = [section['header']]
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # 현재 청크 + 문단
            test_chunk = current_chunk + '\n\n' + para if current_chunk else para
            
            if len(test_chunk) > self.max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunks.append({
                    'chunk_id': f'chunk_{start_id + len(chunks)}',
                    'content': current_chunk.strip(),
                    'char_count': len(current_chunk),
                    'type': 'section',
                    'headers': chunk_headers.copy(),
                    'page_hint': self._extract_page_hint(current_chunk)
                })
                
                # 새 청크 시작
                current_chunk = para
            else:
                current_chunk = test_chunk
        
        # 마지막 청크
        if current_chunk.strip():
            chunks.append({
                'chunk_id': f'chunk_{start_id + len(chunks)}',
                'content': current_chunk.strip(),
                'char_count': len(current_chunk),
                'type': 'section',
                'headers': chunk_headers.copy(),
                'page_hint': self._extract_page_hint(current_chunk)
            })
        
        return chunks
    
    def _extract_page_hint(self, content: str) -> int:
        """
        내용에서 페이지 번호 힌트 추출
        
        패턴: "# Page 3" → 3
        """
        match = re.search(r'#\s+Page\s+(\d+)', content)
        if match:
            return int(match.group(1))
        return 0
    
    def _add_metadata(self, chunk: Dict[str, Any], full_markdown: str):
        """
        청크에 추가 메타데이터 추가
        
        메타데이터:
        - position: 전체 문서 내 위치 (0~1)
        - contains_numbers: 숫자 데이터 포함 여부
        """
        # 위치 계산
        chunk_start = full_markdown.find(chunk['content'])
        if chunk_start >= 0:
            chunk['position'] = chunk_start / len(full_markdown)
        else:
            chunk['position'] = 0.0
        
        # 숫자 데이터 검출
        content = chunk['content']
        number_patterns = [
            r'\d{1,2}:\d{2}',  # 시간
            r'\d+분',          # 분
            r'\d+원',          # 금액
            r'\d+%'            # 퍼센트
        ]
        
        chunk['contains_numbers'] = any(
            re.search(pattern, content) for pattern in number_patterns
        )
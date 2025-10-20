"""
PRISM Phase 2.7 - Intelligent Chunker
의미 기반 청킹 시스템 (RAG 최적화)

Author: 이서영 (Backend Lead)
Date: 2025-10-20
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    chunk_id: str
    content: str
    type: str  # 'text', 'table', 'chart', 'image'
    page_num: int
    section_path: str
    metadata: Dict = field(default_factory=dict)
    token_count: int = 0
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'chunk_id': self.chunk_id,
            'page_num': self.page_num,
            'content': self.content,
            'type': self.type,
            'metadata': {
                'section_path': self.section_path,
                'token_count': self.token_count,
                **self.metadata
            }
        }


class IntelligentChunker:
    """
    지능형 청킹 시스템
    
    전략:
    1. 섹션 기반 분할 (제목/소제목 감지)
    2. 크기 제약 (100-500 토큰)
    3. 의미 단위 유지
    4. 컨텍스트 보존
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap_size: int = 50
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기 (토큰)
            max_chunk_size: 최대 청크 크기 (토큰)
            overlap_size: 청크 간 오버랩 크기 (토큰)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        
        print(f"✅ IntelligentChunker initialized")
        print(f"   Chunk size: {min_chunk_size}-{max_chunk_size} tokens")
        print(f"   Overlap: {overlap_size} tokens")
    
    def chunk_content(
        self,
        content: str,
        content_type: str,
        page_num: int,
        base_section: str = "",
        metadata: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        컨텐츠를 청크로 분할
        
        Args:
            content: 원본 컨텐츠
            content_type: 'text', 'table', 'chart', 'image'
            page_num: 페이지 번호
            base_section: 기본 섹션 경로
            metadata: 추가 메타데이터
            
        Returns:
            Chunk 리스트
        """
        
        if not content or not content.strip():
            return []
        
        # 타입별 청킹 전략
        if content_type == 'text':
            return self._chunk_text(content, page_num, base_section, metadata)
        elif content_type == 'table':
            return self._chunk_table(content, page_num, base_section, metadata)
        elif content_type == 'chart':
            return self._chunk_chart(content, page_num, base_section, metadata)
        elif content_type == 'image':
            return self._chunk_image(content, page_num, base_section, metadata)
        else:
            # 기본: 텍스트로 처리
            return self._chunk_text(content, page_num, base_section, metadata)
    
    def _chunk_text(
        self,
        text: str,
        page_num: int,
        base_section: str,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """텍스트 컨텐츠 청킹"""
        
        chunks = []
        
        # 1. 섹션 감지
        sections = self._detect_sections(text)
        
        if not sections:
            # 섹션이 없으면 전체를 하나의 섹션으로
            sections = [{'level': 0, 'title': base_section or 'Content', 'content': text}]
        
        # 2. 섹션별 청킹
        for i, section in enumerate(sections):
            section_title = section.get('title', f'Section {i+1}')
            section_content = section.get('content', '')
            section_level = section.get('level', 0)
            
            # 섹션 경로 생성
            if base_section:
                section_path = f"{base_section} > {section_title}"
            else:
                section_path = section_title
            
            # 토큰 수 계산
            token_count = self._estimate_tokens(section_content)
            
            # 크기 확인
            if token_count <= self.max_chunk_size:
                # 적절한 크기: 하나의 청크로
                chunk_id = f"chunk_{page_num:03d}_{len(chunks)+1:03d}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    content=section_content.strip(),
                    type='text',
                    page_num=page_num,
                    section_path=section_path,
                    metadata=metadata or {},
                    token_count=token_count
                ))
            else:
                # 너무 큼: 문단 단위로 분할
                sub_chunks = self._split_by_paragraphs(
                    section_content,
                    page_num,
                    section_path,
                    metadata,
                    start_index=len(chunks)
                )
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _chunk_table(
        self,
        table_content: str,
        page_num: int,
        base_section: str,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """표 컨텐츠 청킹 (보통 하나의 청크로)"""
        
        chunk_id = f"chunk_{page_num:03d}_table_001"
        token_count = self._estimate_tokens(table_content)
        
        # 표 제목 추출 시도
        table_title = self._extract_table_title(table_content)
        section_path = f"{base_section} > {table_title}" if base_section else table_title
        
        return [Chunk(
            chunk_id=chunk_id,
            content=table_content.strip(),
            type='table',
            page_num=page_num,
            section_path=section_path,
            metadata=metadata or {},
            token_count=token_count
        )]
    
    def _chunk_chart(
        self,
        chart_content: str,
        page_num: int,
        base_section: str,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """차트 컨텐츠 청킹 (보통 하나의 청크로)"""
        
        chunk_id = f"chunk_{page_num:03d}_chart_001"
        token_count = self._estimate_tokens(chart_content)
        
        # 차트 제목 추출 시도
        chart_title = self._extract_chart_title(chart_content)
        section_path = f"{base_section} > {chart_title}" if base_section else chart_title
        
        return [Chunk(
            chunk_id=chunk_id,
            content=chart_content.strip(),
            type='chart',
            page_num=page_num,
            section_path=section_path,
            metadata=metadata or {},
            token_count=token_count
        )]
    
    def _chunk_image(
        self,
        image_description: str,
        page_num: int,
        base_section: str,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """이미지 설명 청킹 (보통 하나의 청크로)"""
        
        chunk_id = f"chunk_{page_num:03d}_image_001"
        token_count = self._estimate_tokens(image_description)
        
        section_path = f"{base_section} > Image" if base_section else "Image"
        
        return [Chunk(
            chunk_id=chunk_id,
            content=image_description.strip(),
            type='image',
            page_num=page_num,
            section_path=section_path,
            metadata=metadata or {},
            token_count=token_count
        )]
    
    def _detect_sections(self, text: str) -> List[Dict]:
        """
        텍스트에서 섹션 감지
        
        Returns:
            [{'level': 1, 'title': '제목', 'content': '내용'}, ...]
        """
        sections = []
        
        # 제목 패턴 (다양한 형식 지원)
        patterns = [
            # "## 제목" 형식
            r'^(#{1,6})\s+(.+),
            # "1. 제목", "1.1 제목" 형식
            r'^(\d+\.(?:\d+\.)*)\s+(.+),
            # "【제목】" 형식
            r'^【(.+)】,
            # "☉ 제목" 형식
            r'^[☉◆●■▶]\s+(.+),
            # 대문자로만 된 제목
            r'^([A-Z][A-Z\s]{2,})
        ]
        
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 제목 매칭 시도
            is_heading = False
            heading_level = 0
            heading_title = None
            
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    is_heading = True
                    if len(match.groups()) == 2:
                        # 레벨과 제목
                        level_str = match.group(1)
                        heading_title = match.group(2).strip()
                        heading_level = level_str.count('#') or level_str.count('.')
                    else:
                        # 제목만
                        heading_title = match.group(1).strip()
                        heading_level = 1
                    break
            
            if is_heading and heading_title:
                # 이전 섹션 저장
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # 새 섹션 시작
                current_section = {
                    'level': heading_level,
                    'title': heading_title,
                    'content': ''
                }
                current_content = []
            else:
                # 컨텐츠 누적
                current_content.append(line)
        
        # 마지막 섹션 저장
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections
    
    def _split_by_paragraphs(
        self,
        text: str,
        page_num: int,
        section_path: str,
        metadata: Optional[Dict],
        start_index: int = 0
    ) -> List[Chunk]:
        """문단 단위로 텍스트 분할"""
        
        chunks = []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            if current_tokens + para_tokens <= self.max_chunk_size:
                # 현재 청크에 추가
                current_chunk.append(para)
                current_tokens += para_tokens
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunk_id = f"chunk_{page_num:03d}_{start_index + len(chunks) + 1:03d}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        content='\n\n'.join(current_chunk),
                        type='text',
                        page_num=page_num,
                        section_path=section_path,
                        metadata=metadata or {},
                        token_count=current_tokens
                    ))
                
                # 새 청크 시작
                current_chunk = [para]
                current_tokens = para_tokens
        
        # 마지막 청크 저장
        if current_chunk:
            chunk_id = f"chunk_{page_num:03d}_{start_index + len(chunks) + 1:03d}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                content='\n\n'.join(current_chunk),
                type='text',
                page_num=page_num,
                section_path=section_path,
                metadata=metadata or {},
                token_count=current_tokens
            ))
        
        return chunks
    
    def _extract_table_title(self, table_content: str) -> str:
        """표 제목 추출"""
        lines = table_content.split('\n')
        
        # 첫 줄이 제목일 가능성 높음
        if lines and not lines[0].startswith('|'):
            return lines[0].strip()
        
        return "Table"
    
    def _extract_chart_title(self, chart_content: str) -> str:
        """차트 제목 추출"""
        lines = chart_content.split('\n')
        
        # "Title: ..." 패턴 찾기
        for line in lines[:5]:  # 처음 5줄만 확인
            if line.lower().startswith('title:'):
                return line.split(':', 1)[1].strip()
        
        return "Chart"
    
    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (간단한 휴리스틱)"""
        if not text:
            return 0
        
        # 한글: 문자당 ~1.5 토큰
        # 영문: 단어당 ~1.3 토큰
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        numbers = len(re.findall(r'\d+', text))
        
        estimated = int(korean_chars * 1.5 + english_words * 1.3 + numbers * 0.5)
        
        return max(estimated, len(text.split()) // 2)  # 최소값 보장


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Intelligent Chunker Test")
    print("="*60 + "\n")
    
    chunker = IntelligentChunker()
    
    # 테스트 텍스트
    test_text = """
## 응답자 특성

### 전체 응답자 개요
2023년 조사에 참여한 전체 응답자는 총 35,000명이며 이 중 프로스포츠 팬은 25,000명, 일반국민은 10,000명입니다.

### 성별 분포
남성: 45.2%
여성: 54.8%

### 연령 분포
14-19세: 11.2%
20대: 25.9%
30대: 22.3%
40대: 19.9%
50대 이상: 20.7%
"""
    
    chunks = chunker.chunk_content(
        content=test_text,
        content_type='text',
        page_num=1,
        base_section="조사 개요"
    )
    
    print(f"✅ Generated {len(chunks)} chunks:\n")
    for chunk in chunks:
        print(f"  {chunk.chunk_id}")
        print(f"  Type: {chunk.type}")
        print(f"  Section: {chunk.section_path}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Content preview: {chunk.content[:100]}...")
        print()
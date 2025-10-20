"""
PRISM Phase 2.7 - Intelligent Chunker (간단 버전)
텍스트 기반 간단한 청킹

Author: 이서영 (Backend Lead)
Date: 2025-10-20
Fix: 간단한 길이 기반 청킹
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    content: str
    type: str
    page_num: int
    metadata: Dict


class IntelligentChunker:
    """
    간단한 청킹 클래스
    
    전략: 길이 기반 텍스트 분할
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 500,
        overlap: int = 50
    ):
        """
        초기화
        
        Args:
            min_chunk_size: 최소 청크 크기
            max_chunk_size: 최대 청크 크기
            overlap: 청크 간 중복
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        print(f"✅ IntelligentChunker initialized (size: {min_chunk_size}-{max_chunk_size})")
    
    def chunk_region(
        self,
        content: str,
        region_type: str,
        page_num: int,
        section_path: str = "",
        source: str = "unknown"
    ) -> List[Chunk]:
        """
        영역을 청크로 분할
        
        Args:
            content: 추출된 내용
            region_type: 영역 타입
            page_num: 페이지 번호
            section_path: 섹션 경로
            source: 추출 소스
            
        Returns:
            청크 리스트
        """
        
        # 내용이 비어있으면 빈 리스트
        if not content or len(content.strip()) == 0:
            return []
        
        chunks = []
        
        # 내용이 max_chunk_size보다 작으면 하나의 청크로
        if len(content) <= self.max_chunk_size:
            chunk = Chunk(
                content=content,
                type=region_type,
                page_num=page_num,
                metadata={
                    'section_path': section_path,
                    'source': source,
                    'chunk_index': 0,
                    'total_chunks': 1
                }
            )
            chunks.append(chunk)
            return chunks
        
        # 내용이 크면 여러 청크로 분할
        start = 0
        chunk_index = 0
        max_iterations = 1000  # 무한 루프 방지
        
        while start < len(content) and chunk_index < max_iterations:
            end = min(start + self.max_chunk_size, len(content))
            
            # 청크 생성
            chunk_content = content[start:end]
            
            chunk = Chunk(
                content=chunk_content,
                type=region_type,
                page_num=page_num,
                metadata={
                    'section_path': section_path,
                    'source': source,
                    'chunk_index': chunk_index,
                    'start_pos': start,
                    'end_pos': end
                }
            )
            chunks.append(chunk)
            
            # 다음 청크로 (overlap 고려)
            if end >= len(content):
                break  # 끝에 도달
            
            start = end - self.overlap
            if start >= len(content) - self.min_chunk_size:
                break  # 남은 내용이 min_chunk_size보다 작으면 종료
            
            chunk_index += 1
        
        # total_chunks 업데이트
        for chunk in chunks:
            chunk.metadata['total_chunks'] = len(chunks)
        
        return chunks


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Intelligent Chunker Test")
    print("="*60 + "\n")
    
    chunker = IntelligentChunker(
        min_chunk_size=100,
        max_chunk_size=500,
        overlap=50
    )
    
    # 테스트 텍스트
    test_content = "이것은 테스트 문서입니다. " * 100  # 충분히 긴 텍스트
    
    chunks = chunker.chunk_region(
        content=test_content,
        region_type='text',
        page_num=1,
        section_path='Test section'
    )
    
    print(f"✅ Generated {len(chunks)} chunk(s)")
    for i, chunk in enumerate(chunks, 1):
        print(f"   Chunk {i}: {len(chunk.content)} chars")
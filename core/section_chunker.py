"""
PRISM Phase 3.0 - Section-aware Chunker
구조를 보존하는 지능형 청킹
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SectionChunker:
    """
    섹션 인식 청커
    문서의 구조를 보존하면서 RAG 최적화 청크 생성
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        overlap: int = 50
    ):
        """
        청커 초기화
        
        Args:
            min_chunk_size: 최소 청크 크기 (문자)
            max_chunk_size: 최대 청크 크기 (문자)
            overlap: 청크 간 중복 문자 수
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_extractions(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        추출 결과를 청크로 변환
        
        Args:
            extractions: VLM 추출 결과 리스트
            
        Returns:
            청크 리스트
        """
        logger.info(f"\n섹션 인식 청킹 시작 (입력: {len(extractions)}개 영역)")
        
        chunks = []
        current_section = ""
        
        for i, extraction in enumerate(extractions, 1):
            logger.info(f"[{i}/{len(extractions)}] {extraction['region_type']} 처리 중...")
            
            content = extraction['content']
            region_type = extraction['region_type']
            page_number = extraction['page_number']
            
            # 헤더인 경우 섹션 경로 업데이트
            if region_type == "header":
                current_section = content.strip()
                logger.info(f"   → 섹션 변경: {current_section}")
            
            # 청크 생성
            chunk = self._create_chunk(
                content=content,
                region_type=region_type,
                page_number=page_number,
                section_path=current_section,
                chunk_index=i
            )
            
            chunks.append(chunk)
            
            logger.info(f"   → {region_type} 청크 (분할 안함): {len(content)}자")
        
        logger.info(f"\n✅ 청킹 완료: {len(chunks)}개 청크 생성\n")
        
        return chunks
    
    def _create_chunk(
        self,
        content: str,
        region_type: str,
        page_number: int,
        section_path: str,
        chunk_index: int
    ) -> Dict[str, Any]:
        """
        단일 청크 생성
        
        Args:
            content: 콘텐츠
            region_type: 영역 타입
            page_number: 페이지 번호
            section_path: 섹션 경로
            chunk_index: 청크 인덱스
            
        Returns:
            청크 딕셔너리
        """
        # 차트/표는 분할하지 않음 (의미 보존)
        if region_type in ["pie_chart", "bar_chart", "table", "map"]:
            return {
                'chunk_id': f"chunk_{chunk_index:03d}",
                'content': content,
                'metadata': {
                    'page_number': page_number,
                    'chunk_type': region_type,
                    'section_path': section_path,
                    'chart_number': None,
                    'preserves_structure': True,
                    'char_count': len(content)
                }
            }
        
        # 텍스트는 필요 시 분할
        elif region_type == "header":
            return {
                'chunk_id': f"chunk_{chunk_index:03d}",
                'content': content,
                'metadata': {
                    'page_number': page_number,
                    'chunk_type': 'header',
                    'section_path': section_path,
                    'chart_number': None,
                    'preserves_structure': True,
                    'char_count': len(content)
                }
            }
        
        # 기본 텍스트
        else:
            return {
                'chunk_id': f"chunk_{chunk_index:03d}",
                'content': content,
                'metadata': {
                    'page_number': page_number,
                    'chunk_type': 'text',
                    'section_path': section_path,
                    'chart_number': None,
                    'preserves_structure': True,
                    'char_count': len(content)
                }
            }
    
    def _split_long_text(self, text: str, max_size: int) -> List[str]:
        """
        긴 텍스트를 청크로 분할
        
        Args:
            text: 입력 텍스트
            max_size: 최대 크기
            
        Returns:
            분할된 텍스트 리스트
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        
        # 문장 단위 분할
        sentences = text.split('. ')
        
        current_chunk = ""
        
        for sentence in sentences:
            # 문장 추가 시 크기 초과하면 새 청크 시작
            if len(current_chunk) + len(sentence) > max_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                current_chunk += sentence + ". "
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        청크 간 중복 추가
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            중복이 추가된 청크 리스트
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped = []
        
        for i, chunk in enumerate(chunks):
            if i > 0:
                # 이전 청크의 끝부분을 현재 청크에 추가
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.overlap:]
                chunk = overlap_text + " " + chunk
            
            overlapped.append(chunk)
        
        return overlapped
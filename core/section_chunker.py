"""
core/section_chunker.py
PRISM Phase 3.0 - 섹션 인식 청킹 엔진

특징:
- 섹션 헤더 보존
- 차트/표는 분할 안함
- 100-500 토큰 유지
- section_path 메타데이터
"""

from typing import List, Dict
from dataclasses import dataclass, asdict
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """청크 데이터"""
    chunk_id: str
    content: str
    metadata: Dict
    
    def to_dict(self):
        """딕셔너리 변환"""
        return asdict(self)


class SectionAwareChunker:
    """
    구조 인식 청킹 엔진
    
    전략:
    1. 헤더는 section_path 업데이트 + 별도 청크
    2. 차트/표/지도는 분할 없이 통째로
    3. 텍스트는 문장 단위로 분할 (100-500자)
    4. 모든 청크에 section_path 메타데이터 추가
    """
    
    def __init__(self, min_size=100, max_size=500, preserve_structure=True):
        """
        Args:
            min_size: 최소 청크 크기 (문자 수)
            max_size: 최대 청크 크기 (문자 수)
            preserve_structure: 구조 보존 여부
        """
        self.min_size = min_size
        self.max_size = max_size
        self.preserve_structure = preserve_structure
        self.current_section_path = []
    
    def chunk_extractions(self, extractions: List[Dict]) -> List[Chunk]:
        """
        추출 결과를 청킹
        
        Args:
            extractions: [
                {'region_type': 'header', 'content': '☉ 응답자 특성', ...},
                {'region_type': 'chart', 'content': '성별 분포...', ...},
                ...
            ]
        
        Returns:
            [Chunk(...), Chunk(...), ...]
        """
        logger.info(f"\n섹션 인식 청킹 시작 (입력: {len(extractions)}개 영역)")
        
        chunks = []
        chunk_counter = 0
        chart_counter = 0
        
        for i, extraction in enumerate(extractions, 1):
            region_type = extraction['region_type']
            content = extraction['content']
            page_num = extraction['page_number']
            
            logger.info(f"[{i}/{len(extractions)}] {region_type} 처리 중...")
            
            # 1. 헤더: section_path 업데이트 + 청크 생성
            if region_type == 'header':
                self._update_section_path(content)
                
                chunk = Chunk(
                    chunk_id=f"chunk_{chunk_counter:03d}",
                    content=f"[섹션] {content}",
                    metadata={
                        'page_number': page_num,
                        'chunk_type': 'section_header',
                        'section_path': ' > '.join(self.current_section_path),
                        'char_count': len(content)
                    }
                )
                chunks.append(chunk)
                chunk_counter += 1
                
                logger.info(f"   → 헤더 청크: {' > '.join(self.current_section_path)}")
            
            # 2. 차트/표/지도: 분할 없이 통째로
            elif region_type in ['chart', 'table', 'map']:
                chart_counter += 1
                
                chunk = Chunk(
                    chunk_id=f"chunk_{chunk_counter:03d}",
                    content=content,
                    metadata={
                        'page_number': page_num,
                        'chunk_type': region_type,
                        'section_path': ' > '.join(self.current_section_path),
                        'chart_number': chart_counter if region_type == 'chart' else None,
                        'preserves_structure': True,
                        'char_count': len(content)
                    }
                )
                chunks.append(chunk)
                chunk_counter += 1
                
                logger.info(f"   → {region_type} 청크 (분할 안함): {len(content)}자")
            
            # 3. 텍스트: 의미 단위로 분할
            else:
                text_chunks = self._chunk_text(content)
                
                logger.info(f"   → 텍스트 분할: {len(text_chunks)}개 청크")
                
                for j, text_chunk in enumerate(text_chunks):
                    chunk = Chunk(
                        chunk_id=f"chunk_{chunk_counter:03d}",
                        content=text_chunk,
                        metadata={
                            'page_number': page_num,
                            'chunk_type': 'text',
                            'section_path': ' > '.join(self.current_section_path),
                            'sub_index': j,
                            'total_sub_chunks': len(text_chunks),
                            'char_count': len(text_chunk)
                        }
                    )
                    chunks.append(chunk)
                    chunk_counter += 1
        
        logger.info(f"\n✅ 청킹 완료: {len(chunks)}개 청크 생성\n")
        
        return chunks
    
    def _update_section_path(self, header_text: str):
        """
        섹션 경로 업데이트
        
        예시:
        - "06 응답자 특성" → ["06 응답자 특성"]
        - "☉ 응답자 성별 및 연령" → ["06 응답자 특성", "응답자 성별 및 연령"]
        """
        # 기호 제거
        clean_text = header_text.replace('☉', '').strip()
        
        # 계층 구조 추론
        if clean_text and clean_text[0].isdigit():
            # 숫자로 시작 → 최상위 섹션
            self.current_section_path = [clean_text]
        else:
            # 기호로 시작 → 하위 섹션
            if len(self.current_section_path) == 0:
                # 상위 섹션 없으면 최상위로
                self.current_section_path = [clean_text]
            elif len(self.current_section_path) == 1:
                # 2단계
                self.current_section_path.append(clean_text)
            else:
                # 3단계 이상 → 마지막 요소 교체
                self.current_section_path[-1] = clean_text
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        텍스트를 의미 단위로 분할
        
        전략:
        1. 문장 단위로 분할
        2. min_size ~ max_size 범위 유지
        3. 문장 경계에서만 분할
        """
        if len(text) <= self.max_size:
            return [text]
        
        # 간단한 문장 분할 (마침표, 느낌표, 물음표 기준)
        sentence_pattern = r'[.!?]\s+'
        sentences = re.split(sentence_pattern, text)
        
        # 빈 문장 제거
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 청크 생성
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 현재 청크에 추가했을 때 크기 확인
            if current_chunk:
                potential_chunk = current_chunk + ". " + sentence
            else:
                potential_chunk = sentence
            
            if len(potential_chunk) <= self.max_size:
                current_chunk = potential_chunk
            else:
                # 최대 크기 초과
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 문장 자체가 max_size보다 크면 강제 분할
                if len(sentence) > self.max_size:
                    # 문자 단위로 분할
                    for i in range(0, len(sentence), self.max_size):
                        chunks.append(sentence[i:i+self.max_size])
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # 마지막 청크
        if current_chunk:
            # 너무 작으면 이전 청크에 병합
            if len(current_chunk) < self.min_size and chunks:
                chunks[-1] = chunks[-1] + ". " + current_chunk
            else:
                chunks.append(current_chunk)
        
        return chunks if chunks else [text]


# 테스트 코드
if __name__ == '__main__':
    # 샘플 데이터
    sample_extractions = [
        {
            'region_type': 'header',
            'content': '06 응답자 특성',
            'page_number': 1
        },
        {
            'region_type': 'header',
            'content': '☉ 응답자 성별 및 연령',
            'page_number': 1
        },
        {
            'region_type': 'chart',
            'content': '이 원그래프는 응답자의 성별 분포를 나타냅니다. 남성 45.2%, 여성 54.8%.',
            'page_number': 1
        },
        {
            'region_type': 'text',
            'content': '2023년 조사에 참여한 전체 응답자는 총 35,000명이며 이 중 프로스포츠 팬은 25,000명, 일반국민은 10,000명으로 응답자 주요 특성은 아래와 같습니다. ' * 5,
            'page_number': 1
        }
    ]
    
    chunker = SectionAwareChunker(min_size=100, max_size=300)
    chunks = chunker.chunk_extractions(sample_extractions)
    
    print(f"\n생성된 청크: {len(chunks)}개\n")
    
    for chunk in chunks:
        print(f"{'='*60}")
        print(f"ID: {chunk.chunk_id}")
        print(f"Type: {chunk.metadata['chunk_type']}")
        print(f"Section: {chunk.metadata['section_path']}")
        print(f"Content: {chunk.content[:100]}...")
        print()
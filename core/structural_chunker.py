"""
core/structural_chunker.py
PRISM Phase 2.9 - 구조화된 청킹 로직

개선 사항:
1. 섹션 기반 청킹 (의미 단위 보존)
2. 차트별 독립 청크
3. 문장 경계 보존
4. 메타데이터 풍부화
5. RAG 최적화

Author: 이서영 (Backend Lead)
Date: 2025-10-21
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """구조화된 청크"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': self.metadata
        }


class StructuralChunker:
    """
    구조 기반 지능형 청킹
    
    Features:
    - 섹션 경계 인식
    - 차트별 분할
    - 문장 단위 보장
    - 의미 연결 유지
    """
    
    # 섹션 헤더 패턴
    SECTION_PATTERNS = [
        r'^###\s+(.+)$',           # ### 제목
        r'^####\s+(.+)$',          # #### 소제목
        r'^\d+\.\s+(.+)$',         # 1. 제목
        r'^[☉⊙●○■□▪▫]\s+(.+)$',   # 기호 제목
    ]
    
    # 차트 구분 패턴
    CHART_MARKERS = [
        r'\*\*첫 번째',
        r'\*\*두 번째',
        r'\*\*세 번째',
        r'\*\*[0-9]+번째',
        r'원그래프',
        r'막대그래프',
        r'선그래프',
        r'파이 차트',
        r'표',
    ]
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 800,
        overlap: int = 50,
        preserve_structure: bool = True
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기 (자)
            max_chunk_size: 최대 청크 크기 (자)
            overlap: 청크 간 오버랩 (자)
            preserve_structure: 구조 보존 여부
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_structure = preserve_structure
    
    def chunk_document(
        self,
        content: str,
        page_number: int,
        element_type: str = 'text'
    ) -> List[Chunk]:
        """
        문서 청킹 (메인 메소드)
        
        Args:
            content: 청킹할 내용
            page_number: 페이지 번호
            element_type: 요소 타입
            
        Returns:
            Chunk 객체 리스트
        """
        if not content or not content.strip():
            return []
        
        # 1. 구조 파싱
        structure = self._parse_structure(content)
        
        # 2. 섹션/차트별 분할
        sections = self._split_by_structure(content, structure)
        
        # 3. 각 섹션을 청킹
        chunks = []
        for i, section in enumerate(sections):
            section_chunks = self._chunk_section(
                section=section,
                page_number=page_number,
                element_type=element_type,
                section_index=i
            )
            chunks.extend(section_chunks)
        
        logger.info(f"페이지 {page_number}: {len(sections)}개 섹션 → {len(chunks)}개 청크")
        
        return chunks
    
    def _parse_structure(self, content: str) -> Dict[str, Any]:
        """
        문서 구조 파싱
        
        Returns:
            {
                'sections': [{'type': '###', 'title': '...', 'start': 0}],
                'charts': [{'type': 'pie', 'start': 100}]
            }
        """
        structure = {
            'sections': [],
            'charts': []
        }
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 섹션 헤더 감지
            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    structure['sections'].append({
                        'type': pattern,
                        'title': match.group(1) if match.lastindex else line,
                        'line': i,
                        'content_start': self._get_char_position(lines, i)
                    })
                    break
            
            # 차트 마커 감지
            for marker in self.CHART_MARKERS:
                if re.search(marker, line):
                    structure['charts'].append({
                        'type': self._infer_chart_type(line),
                        'line': i,
                        'content_start': self._get_char_position(lines, i)
                    })
                    break
        
        return structure
    
    def _split_by_structure(
        self,
        content: str,
        structure: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        구조를 기반으로 섹션 분할
        
        Returns:
            [
                {
                    'type': 'section',
                    'title': '...',
                    'content': '...',
                    'chart_type': 'pie' (optional)
                }
            ]
        """
        if not structure['sections'] and not structure['charts']:
            # 구조 없음 → 전체를 하나의 섹션으로
            return [{
                'type': 'text',
                'title': '',
                'content': content,
                'chart_type': None
            }]
        
        sections = []
        split_points = []
        
        # 섹션 시작점
        for section in structure['sections']:
            split_points.append(('section', section['content_start'], section['title']))
        
        # 차트 시작점
        for chart in structure['charts']:
            split_points.append(('chart', chart['content_start'], chart['type']))
        
        # 정렬
        split_points.sort(key=lambda x: x[1])
        
        # 분할
        for i, (stype, start, info) in enumerate(split_points):
            end = split_points[i + 1][1] if i + 1 < len(split_points) else len(content)
            
            section_content = content[start:end].strip()
            
            if not section_content:
                continue
            
            sections.append({
                'type': stype,
                'title': info if stype == 'section' else '',
                'content': section_content,
                'chart_type': info if stype == 'chart' else None
            })
        
        return sections
    
    def _chunk_section(
        self,
        section: Dict[str, Any],
        page_number: int,
        element_type: str,
        section_index: int
    ) -> List[Chunk]:
        """
        단일 섹션 청킹
        
        Strategy:
        1. 짧으면 그대로 유지
        2. 길면 문장 단위로 분할
        3. 각 청크에 섹션 메타데이터 포함
        """
        content = section['content']
        
        # 짧으면 그대로
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                content=content,
                page_number=page_number,
                element_type=element_type,
                section_title=section['title'],
                chart_type=section.get('chart_type'),
                chunk_index=0,
                total_chunks=1
            )]
        
        # 문장 단위로 분할
        sentences = self._split_sentences(content)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # 청크 크기 초과 체크
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_content = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    page_number=page_number,
                    element_type=element_type,
                    section_title=section['title'],
                    chart_type=section.get('chart_type'),
                    chunk_index=len(chunks),
                    total_chunks=-1  # 나중에 업데이트
                ))
                
                # 오버랩 처리
                if self.overlap > 0 and current_chunk:
                    overlap_text = ' '.join(current_chunk[-2:])  # 마지막 2문장
                    if len(overlap_text) <= self.overlap:
                        current_chunk = current_chunk[-2:]
                        current_length = len(overlap_text)
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # 마지막 청크
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            if len(chunk_content) >= self.min_chunk_size or not chunks:
                chunks.append(self._create_chunk(
                    content=chunk_content,
                    page_number=page_number,
                    element_type=element_type,
                    section_title=section['title'],
                    chart_type=section.get('chart_type'),
                    chunk_index=len(chunks),
                    total_chunks=-1
                ))
        
        # total_chunks 업데이트
        total = len(chunks)
        for chunk in chunks:
            chunk.metadata['total_chunks'] = total
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        문장 분할 (한글 지원)
        
        Rules:
        - 온점(.), 느낌표(!), 물음표(?) 뒤
        - 단, 숫자 뒤 온점은 무시 (예: 1.5)
        - 괄호 안은 무시
        """
        # 간단한 정규식 기반 분할
        # 더 정교한 분할이 필요하면 kss 라이브러리 사용 고려
        
        # 문장 종결 패턴
        pattern = r'([.!?])\s+'
        
        sentences = []
        last_end = 0
        
        for match in re.finditer(pattern, text):
            end = match.end()
            sentence = text[last_end:end].strip()
            
            if sentence:
                sentences.append(sentence)
            
            last_end = end
        
        # 마지막 문장
        if last_end < len(text):
            sentence = text[last_end:].strip()
            if sentence:
                sentences.append(sentence)
        
        return sentences if sentences else [text]
    
    def _create_chunk(
        self,
        content: str,
        page_number: int,
        element_type: str,
        section_title: str,
        chart_type: Optional[str],
        chunk_index: int,
        total_chunks: int
    ) -> Chunk:
        """청크 객체 생성"""
        
        chunk_id = f"chunk_p{page_number}_{chunk_index}_{id(content) % 10000}"
        
        metadata = {
            'page_number': page_number,
            'element_type': element_type,
            'section_title': section_title,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'char_count': len(content),
            'source': 'vlm'
        }
        
        if chart_type:
            metadata['chart_type'] = chart_type
        
        return Chunk(
            chunk_id=chunk_id,
            content=content,
            metadata=metadata
        )
    
    def _get_char_position(self, lines: List[str], line_number: int) -> int:
        """라인 번호를 문자 위치로 변환"""
        return sum(len(line) + 1 for line in lines[:line_number])
    
    def _infer_chart_type(self, text: str) -> str:
        """텍스트로부터 차트 타입 추론"""
        text_lower = text.lower()
        
        if '원그래프' in text or '파이' in text_lower:
            return 'pie'
        elif '막대' in text:
            return 'bar'
        elif '선그래프' in text or '꺾은선' in text:
            return 'line'
        elif '표' in text or '테이블' in text_lower:
            return 'table'
        elif '지도' in text:
            return 'map'
        else:
            return 'unknown'


class RAGOptimizedChunker(StructuralChunker):
    """
    RAG 최적화 청킹
    
    Additional features:
    - 질의응답 최적화
    - 컨텍스트 풍부화
    - 검색 키워드 추출
    """
    
    def chunk_document(
        self,
        content: str,
        page_number: int,
        element_type: str = 'text'
    ) -> List[Chunk]:
        """RAG 최적화 청킹"""
        
        # 기본 청킹
        chunks = super().chunk_document(content, page_number, element_type)
        
        # 메타데이터 풍부화
        for chunk in chunks:
            self._enrich_metadata(chunk)
        
        return chunks
    
    def _enrich_metadata(self, chunk: Chunk):
        """
        메타데이터 풍부화
        
        Add:
        - keywords: 주요 키워드
        - entities: 개체명 (숫자, 지역명 등)
        - summary: 요약
        """
        content = chunk.content
        
        # 키워드 추출 (간단한 휴리스틱)
        keywords = self._extract_keywords(content)
        chunk.metadata['keywords'] = keywords
        
        # 숫자 엔티티 추출
        numbers = re.findall(r'\d+\.?\d*%?', content)
        chunk.metadata['numbers'] = numbers[:10]  # 최대 10개
        
        # 요약 (첫 100자)
        summary = content[:100] + '...' if len(content) > 100 else content
        chunk.metadata['summary'] = summary
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        간단한 키워드 추출
        
        Strategy:
        - 명사 추출 (휴리스틱)
        - 빈도 기반
        """
        # 간단한 버전: 2글자 이상 한글 단어
        words = re.findall(r'[가-힣]{2,}', text)
        
        # 불용어 제거
        stopwords = {'이다', '있다', '하다', '되다', '없다', '같다', '의', '를', '을', '에', '가', '이', '은', '는'}
        words = [w for w in words if w not in stopwords]
        
        # 빈도 계산
        from collections import Counter
        counter = Counter(words)
        
        # 상위 N개
        keywords = [word for word, count in counter.most_common(top_n)]
        
        return keywords


# 사용 예시
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 텍스트
    test_content = """### 06. 응답자 특성

#### ☉ 응답자 성별 및 연령

**첫 번째 원그래프 - 성별 분포**

이 차트는 응답자의 성별 분포를 나타냅니다.

**데이터:**
- 남성: 45.2%
- 여성: 54.8%

**인사이트:**
여성 응답자가 더 많습니다.

---

**두 번째 막대그래프 - 연령 분포**

이 차트는 연령대별 분포를 나타냅니다.

**데이터:**
- 14~19세: 11.2%
- 20대: 25.9%
- 30대: 22.3%
- 40대: 19.9%
- 50대 이상: 20.7%

**인사이트:**
20대가 가장 많습니다."""
    
    print("=== StructuralChunker 테스트 ===\n")
    
    chunker = StructuralChunker(
        min_chunk_size=100,
        max_chunk_size=300,
        overlap=50
    )
    
    chunks = chunker.chunk_document(test_content, page_number=1, element_type='table')
    
    print(f"총 {len(chunks)}개 청크 생성\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- 청크 #{i} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"길이: {len(chunk.content)}자")
        print(f"섹션: {chunk.metadata.get('section_title', 'N/A')}")
        print(f"차트: {chunk.metadata.get('chart_type', 'N/A')}")
        print(f"내용: {chunk.content[:100]}...")
        print()
    
    print("\n=== RAGOptimizedChunker 테스트 ===\n")
    
    rag_chunker = RAGOptimizedChunker(max_chunk_size=300)
    
    rag_chunks = rag_chunker.chunk_document(test_content, page_number=1)
    
    for i, chunk in enumerate(rag_chunks, 1):
        print(f"--- 청크 #{i} ---")
        print(f"키워드: {chunk.metadata.get('keywords', [])}")
        print(f"숫자: {chunk.metadata.get('numbers', [])}")
        print(f"요약: {chunk.metadata.get('summary', '')}")
        print()
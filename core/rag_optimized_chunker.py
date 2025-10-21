"""
core/rag_optimized_chunker.py
RAG 최적화 청킹 엔진

특징:
1. 섹션 기반 지능형 청킹
2. 문장 경계 존중
3. 메타데이터 풍부화 (키워드, 요약)
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    chunk_id: str
    text: str
    page_number: int
    section_title: Optional[str]
    chunk_type: str  # 'section', 'paragraph', 'list'
    keywords: List[str]
    summary: str
    char_count: int
    
    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return asdict(self)


class RAGOptimizedChunker:
    """
    RAG 최적화 청킹 엔진
    
    청킹 전략:
    1. 섹션 기반 분할
    2. 문장 경계 유지
    3. 의미 단위 보존
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 800,
        overlap: int = 50,
        preserve_structure: bool = True
    ):
        """
        Args:
            min_chunk_size: 최소 청크 크기 (글자)
            max_chunk_size: 최대 청크 크기 (글자)
            overlap: 청크 간 겹침 (글자)
            preserve_structure: 구조 보존 여부
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_structure = preserve_structure
        
        # 섹션 헤더 패턴
        self.section_patterns = [
            r'^#{1,3}\s+.*$',           # Markdown 헤더
            r'^\d+\.\s+.*$',            # 숫자 섹션 (1. 제목)
            r'^[☉○●]\s+.*$',           # 기호 섹션
            r'^\*\*.*\*\*$',            # 볼드 제목
        ]
    
    def chunk_with_structure(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        구조 기반 청킹
        
        Args:
            text: 전체 텍스트
            metadata: 추가 메타데이터
            
        Returns:
            청크 리스트
        """
        # 1. 섹션 분할
        sections = self._split_into_sections(text)
        
        # 2. 각 섹션을 청크로 변환
        chunks = []
        chunk_idx = 0
        
        for section in sections:
            section_chunks = self._chunk_section(
                section=section,
                start_idx=chunk_idx,
                metadata=metadata
            )
            chunks.extend(section_chunks)
            chunk_idx += len(section_chunks)
        
        logger.info(f"청킹 완료: {len(chunks)}개 청크 생성")
        
        return chunks
    
    def _split_into_sections(self, text: str) -> List[Dict]:
        """
        텍스트를 섹션으로 분할
        
        Returns:
            [
                {
                    'title': 섹션 제목,
                    'content': 섹션 내용,
                    'level': 섹션 레벨
                },
                ...
            ]
        """
        lines = text.split('\n')
        sections = []
        current_section = {'title': None, 'content': [], 'level': 0}
        
        for line in lines:
            # 섹션 헤더 감지
            is_header, level = self._is_section_header(line)
            
            if is_header:
                # 이전 섹션 저장
                if current_section['content']:
                    sections.append({
                        'title': current_section['title'],
                        'content': '\n'.join(current_section['content']),
                        'level': current_section['level']
                    })
                
                # 새 섹션 시작
                current_section = {
                    'title': line.strip(),
                    'content': [],
                    'level': level
                }
            else:
                # 내용 추가
                if line.strip():
                    current_section['content'].append(line)
        
        # 마지막 섹션
        if current_section['content']:
            sections.append({
                'title': current_section['title'],
                'content': '\n'.join(current_section['content']),
                'level': current_section['level']
            })
        
        return sections
    
    def _is_section_header(self, line: str) -> tuple:
        """
        섹션 헤더 여부 판단
        
        Returns:
            (is_header: bool, level: int)
        """
        line = line.strip()
        
        # Markdown 헤더
        if re.match(r'^#{1,3}\s+', line):
            level = len(re.match(r'^#+', line).group())
            return True, level
        
        # 숫자 섹션
        if re.match(r'^\d+\.\s+', line):
            return True, 1
        
        # 기호 섹션
        if re.match(r'^[☉○●]\s+', line):
            return True, 2
        
        # 볼드 제목
        if re.match(r'^\*\*.*\*\*$', line):
            return True, 2
        
        return False, 0
    
    def _chunk_section(
        self,
        section: Dict,
        start_idx: int,
        metadata: Optional[Dict]
    ) -> List[Chunk]:
        """
        섹션을 청크로 분할
        """
        content = section['content']
        title = section['title']
        
        # 짧은 섹션은 하나의 청크로
        if len(content) <= self.max_chunk_size:
            return [self._create_chunk(
                chunk_id=f"chunk_{start_idx:03d}",
                text=content,
                section_title=title,
                page_number=1,  # 페이지 정보는 metadata에서
                chunk_type='section'
            )]
        
        # 긴 섹션은 문장 단위로 분할
        sentences = self._split_into_sentences(content)
        chunks = []
        current_text = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # 크기 초과 시 청크 생성
            if current_length + sentence_length > self.max_chunk_size:
                if current_text:
                    chunk = self._create_chunk(
                        chunk_id=f"chunk_{start_idx + len(chunks):03d}",
                        text='\n'.join(current_text),
                        section_title=title,
                        page_number=1,
                        chunk_type='paragraph'
                    )
                    chunks.append(chunk)
                    
                    # 겹침 처리
                    if self.overlap > 0:
                        overlap_text = current_text[-1] if current_text else ''
                        current_text = [overlap_text]
                        current_length = len(overlap_text)
                    else:
                        current_text = []
                        current_length = 0
            
            current_text.append(sentence)
            current_length += sentence_length
        
        # 마지막 청크
        if current_text:
            chunk = self._create_chunk(
                chunk_id=f"chunk_{start_idx + len(chunks):03d}",
                text='\n'.join(current_text),
                section_title=title,
                page_number=1,
                chunk_type='paragraph'
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장으로 분할
        
        한글 문장 종결: . ! ? 
        """
        # 문장 종결 부호로 분할
        sentences = re.split(r'([.!?]\s+)', text)
        
        # 문장 + 종결부호 결합
        result = []
        for i in range(0, len(sentences)-1, 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
            if sentence.strip():
                result.append(sentence.strip())
        
        # 마지막 문장 (종결부호 없을 수 있음)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return result
    
    def _create_chunk(
        self,
        chunk_id: str,
        text: str,
        section_title: Optional[str],
        page_number: int,
        chunk_type: str
    ) -> Chunk:
        """청크 객체 생성"""
        
        # 키워드 추출 (간단한 버전)
        keywords = self._extract_keywords(text)
        
        # 요약 생성 (첫 50자)
        summary = text[:50] + ('...' if len(text) > 50 else '')
        
        return Chunk(
            chunk_id=chunk_id,
            text=text,
            page_number=page_number,
            section_title=section_title,
            chunk_type=chunk_type,
            keywords=keywords,
            summary=summary,
            char_count=len(text)
        )
    
    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """
        키워드 추출 (간단한 빈도 기반)
        
        실제로는 TF-IDF나 BERT 사용 권장
        """
        # 한글 단어 추출
        words = re.findall(r'[가-힣]{2,}', text)
        
        # 불용어 제거 (간단한 버전)
        stopwords = {'이', '그', '저', '것', '수', '등', '및', '또한'}
        words = [w for w in words if w not in stopwords]
        
        # 빈도 계산
        from collections import Counter
        word_counts = Counter(words)
        
        # 상위 N개
        top_words = [word for word, _ in word_counts.most_common(top_n)]
        
        return top_words


# 테스트
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 텍스트
    test_text = """### 06. 응답자 특성

#### ☉ 응답자 성별 및 연령

**원그래프 - 성별 분포**

이 차트는 응답자의 성별 분포를 나타냅니다.

**데이터:**
- 남성: 45.2%
- 여성: 54.8%

**인사이트:**
여성 응답자가 더 많습니다.

---

**막대그래프 - 연령 분포**

이 차트는 연령대별 분포를 나타냅니다.

**데이터:**
- 20대: 25.3%
- 30대: 28.7%
- 40대: 23.1%
- 50대 이상: 22.9%
"""
    
    chunker = RAGOptimizedChunker(
        min_chunk_size=100,
        max_chunk_size=500,
        overlap=50
    )
    
    chunks = chunker.chunk_with_structure(test_text)
    
    print(f"=== 생성된 청크: {len(chunks)}개 ===\n")
    
    for chunk in chunks:
        print(f"ID: {chunk.chunk_id}")
        print(f"섹션: {chunk.section_title}")
        print(f"타입: {chunk.chunk_type}")
        print(f"길이: {chunk.char_count}자")
        print(f"키워드: {', '.join(chunk.keywords)}")
        print(f"내용: {chunk.text[:100]}...")
        print()
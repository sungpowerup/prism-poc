"""
semantic_chunker_v033.py
PRISM Phase 0.3.3 - Semantic Chunker with Boundary Validation

✅ Phase 0.3.3 개선:
1. 한국어 문장 경계 패턴 강화
2. 청크 유효성 자동 검사
3. 불완전 청크 자동 병합
4. 조문 순서 자동 정렬

설치: 기존 semantic_chunker.py 대체

Author: 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.3
"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 0.3.3 의미 기반 청킹 엔진
    
    ✅ 핵심 개선:
    - 한국어 문장 경계 강화
    - 불완전 청크 자동 병합
    - 조문 순서 자동 정렬
    """
    
    VERSION = "Phase 0.3.3"
    
    # ✅ 한국어 문장 종결 패턴
    KOREAN_SENTENCE_ENDINGS = [
        r'다\.',  # ~하다.
        r'다\)',  # ~한다)
        r'다\s*$',  # ~한다
        r'함\.',  # ~함.
        r'됨\.',  # ~됨.
        r'임\.',  # ~임.
        r'<\d{4}\.\s*\d{1,2}\.\s*\d{1,2}>',  # <2024.1.1>
        r'\d+\.\)',  # 1.)
        r'호\s*$',  # ~호
        r'한다\.',  # ~한다.
    ]
    
    #⚠️ 불완전 종결 패턴
    INCOMPLETE_ENDINGS = [
        r'의\s*$', r'를\s*$', r'을\s*$', r'가\s*$',
        r'에\s*$', r'와\s*$', r'로\s*$', r'채\s*$',
        r'형\s+또는\s+치료감\s*$',  # 문장 중간 절단
    ]
    
    def __init__(self, target_size: int = 800, min_size: int = 300):
        """초기화"""
        self.target_size = target_size
        self.min_size = min_size
        
        self.sentence_patterns = [re.compile(p) for p in self.KOREAN_SENTENCE_ENDINGS]
        self.incomplete_patterns = [re.compile(p) for p in self.INCOMPLETE_ENDINGS]
        
        logger.info(f"✅ SemanticChunker {self.VERSION} 초기화")
        logger.info(f"   🎯 목표: {target_size}자, 최소: {min_size}자")
    
    def chunk(self, text: str, doc_type: str = 'statute') -> List[Dict[str, Any]]:
        """
        텍스트를 의미 단위로 청킹
        
        Args:
            text: 입력 텍스트
            doc_type: 문서 타입
        
        Returns:
            청크 리스트
        """
        logger.info(f"   ✂️ SemanticChunker {self.VERSION} 시작")
        
        # 1. 기본 청킹
        chunks = self._basic_chunk(text, doc_type)
        logger.info(f"      기본 청킹: {len(chunks)}개")
        
        # 2. 경계 검증 + 병합
        validated = self._validate_boundaries(chunks)
        logger.info(f"      경계 검증: {len(validated)}개")
        
        # 3. 조문 정렬
        sorted_chunks = self._sort_by_article(validated)
        logger.info(f"   ✅ 청킹 완료: {len(sorted_chunks)}개")
        
        return sorted_chunks
    
    def _basic_chunk(self, text: str, doc_type: str) -> List[Dict[str, Any]]:
        """기본 청킹"""
        chunks = []
        
        if doc_type == 'statute':
            # 조문 기준 분할
            article_pattern = re.compile(r'(#{1,4}\s*제\d+조[^#]*?)(?=#{1,4}\s*제\d+조|$)', re.DOTALL)
            matches = article_pattern.findall(text)
            
            for match in matches:
                article_match = re.search(r'제(\d+)조(?:의(\d+))?', match)
                article_no = article_match.group(0) if article_match else ''
                
                title_match = re.search(r'제\d+조(?:의\d+)?\s*\(([^)]+)\)', match)
                article_title = title_match.group(1) if title_match else ''
                
                chunks.append({
                    'content': match.strip(),
                    'metadata': {
                        'article_no': article_no,
                        'article_title': article_title,
                        'char_count': len(match.strip()),
                        'chunk_index': len(chunks) + 1
                    }
                })
        else:
            # 일반 문서: 문장 단위
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current_chunk = []
            current_size = 0
            
            for sentence in sentences:
                if current_size + len(sentence) > self.target_size and current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'content': chunk_text,
                        'metadata': {
                            'article_no': '',
                            'article_title': '',
                            'char_count': len(chunk_text),
                            'chunk_index': len(chunks) + 1
                        }
                    })
                    current_chunk = []
                    current_size = 0
                
                current_chunk.append(sentence)
                current_size += len(sentence)
            
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'article_no': '',
                        'article_title': '',
                        'char_count': len(chunk_text),
                        'chunk_index': len(chunks) + 1
                    }
                })
        
        return chunks
    
    def _validate_boundaries(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """경계 검증 + 자동 병합"""
        validated = []
        i = 0
        
        while i < len(chunks):
            chunk = chunks[i]
            content = chunk['content']
            
            is_complete = self._is_sentence_boundary(content)
            
            if not is_complete and i + 1 < len(chunks):
                # 불완전 → 병합
                logger.warning(f"      ⚠️ 불완전 청크: '{content[-50:]}'")
                next_chunk = chunks[i + 1]
                
                merged_content = content + '\n\n' + next_chunk['content']
                merged_chunk = {
                    'content': merged_content,
                    'metadata': {
                        'article_no': chunk['metadata']['article_no'] or next_chunk['metadata']['article_no'],
                        'article_title': chunk['metadata']['article_title'] or next_chunk['metadata']['article_title'],
                        'char_count': len(merged_content),
                        'chunk_index': len(validated) + 1,
                        'merged': True
                    }
                }
                
                validated.append(merged_chunk)
                logger.info(f"      ✅ 자동 병합: Chunk {i+1} + {i+2}")
                i += 2
            else:
                validated.append(chunk)
                i += 1
        
        return validated
    
    def _is_sentence_boundary(self, text: str) -> bool:
        """문장 경계 검사"""
        text_end = text.strip()[-100:]
        
        # 완전한 종결 확인
        for pattern in self.sentence_patterns:
            if pattern.search(text_end):
                return True
        
        # 불완전 종결 확인
        for pattern in self.incomplete_patterns:
            if pattern.search(text_end):
                return False
        
        return True
    
    def _sort_by_article(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """조문 번호 기준 정렬"""
        def extract_article_number(chunk: Dict[str, Any]) -> Tuple[int, int]:
            article_no = chunk['metadata'].get('article_no', '')
            
            if not article_no:
                return (999, 0)
            
            main_match = re.search(r'제(\d+)조', article_no)
            sub_match = re.search(r'제\d+조의(\d+)', article_no)
            
            main_num = int(main_match.group(1)) if main_match else 999
            sub_num = int(sub_match.group(1)) if sub_match else 0
            
            return (main_num, sub_num)
        
        sorted_chunks = sorted(chunks, key=extract_article_number)
        
        # chunk_index 재부여
        for i, chunk in enumerate(sorted_chunks, 1):
            chunk['metadata']['chunk_index'] = i
        
        return sorted_chunks
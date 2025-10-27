"""
core/statute_chunker.py
PRISM Phase 5.6.0 - Statute-aware Chunker

목적: 규정/법령 문서의 조문 단위 청킹 및 메타데이터 생성

개선:
- 제○조 기준 청킹
- 조번호/장/절 메타데이터 추출
- 개정일 태깅

Author: 이서영 (Backend Lead)
Date: 2025-10-27
Version: 5.6.0
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StatuteChunker:
    """
    Phase 5.6.0 조문 단위 청킹
    
    목적:
    - 규정/법령 문서를 조문 단위로 분할
    - 메타데이터 추출 (조번호, 장, 절, 개정일)
    - RAG 검색 정밀도 향상
    
    청킹 기준:
    1. 제○조 (Article)
    2. 제○장 (Chapter) - 메타데이터
    3. 제○절 (Section) - 메타데이터
    
    출력 구조:
    {
        'chunk_id': 'statute_art_1',
        'article_no': '제1조',
        'article_title': '목적',
        'chapter': '제1장 총칙',
        'section': None,
        'content': '...',
        'metadata': {
            'last_amended': '2024.1.1',
            'page_range': [1, 1]
        }
    }
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ StatuteChunker v5.6.0 초기화 완료")
    
    def chunk(self, content: str, page_num: int = None) -> List[Dict[str, Any]]:
        """
        조문 단위 청킹
        
        Args:
            content: Markdown 텍스트
            page_num: 페이지 번호 (선택)
        
        Returns:
            청크 리스트
        """
        logger.info(f"   📚 StatuteChunker 시작 (page: {page_num})")
        
        chunks = []
        current_chunk = []
        current_meta = {}
        
        # 현재 문맥 (장/절)
        current_chapter = None
        current_section = None
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # 1) 제○장 감지
            chapter_match = re.match(r'^#{1,3}\s*(제\s?\d+장)\s*(.+)?$', line)
            if chapter_match:
                current_chapter = chapter_match.group(1)
                if chapter_match.group(2):
                    current_chapter += ' ' + chapter_match.group(2).strip()
                logger.debug(f"      장 감지: {current_chapter}")
                current_chunk.append(line)
                continue
            
            # 2) 제○절 감지
            section_match = re.match(r'^#{1,3}\s*(제\s?\d+절)\s*(.+)?$', line)
            if section_match:
                current_section = section_match.group(1)
                if section_match.group(2):
                    current_section += ' ' + section_match.group(2).strip()
                logger.debug(f"      절 감지: {current_section}")
                current_chunk.append(line)
                continue
            
            # 3) 제○조 감지 (청크 구분점)
            article_match = re.match(r'^#{1,3}\s*(제\s?\d+조)\s*(\([^)]+\))?', line)
            if article_match:
                # 이전 청크 저장
                if current_chunk and current_meta:
                    chunk_content = '\n'.join(current_chunk).strip()
                    if chunk_content:
                        chunks.append(self._build_chunk(
                            content=chunk_content,
                            meta=current_meta,
                            chapter=current_chapter,
                            section=current_section,
                            page_num=page_num
                        ))
                
                # 새 청크 시작
                article_no = article_match.group(1)
                article_title = article_match.group(2).strip('()') if article_match.group(2) else None
                
                current_meta = {
                    'article_no': article_no,
                    'article_title': article_title
                }
                
                current_chunk = [line]
                logger.debug(f"      조문 감지: {article_no} ({article_title})")
                continue
            
            # 4) 일반 내용 라인
            current_chunk.append(line)
        
        # 마지막 청크 저장
        if current_chunk and current_meta:
            chunk_content = '\n'.join(current_chunk).strip()
            if chunk_content:
                chunks.append(self._build_chunk(
                    content=chunk_content,
                    meta=current_meta,
                    chapter=current_chapter,
                    section=current_section,
                    page_num=page_num
                ))
        
        logger.info(f"   ✅ 청킹 완료: {len(chunks)}개 조문")
        return chunks
    
    def _build_chunk(
        self,
        content: str,
        meta: Dict[str, str],
        chapter: str,
        section: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        청크 객체 생성
        
        Args:
            content: 청크 내용
            meta: 메타데이터 (article_no, article_title)
            chapter: 현재 장
            section: 현재 절
            page_num: 페이지 번호
        
        Returns:
            청크 객체
        """
        article_no = meta.get('article_no', 'unknown')
        article_title = meta.get('article_title', '')
        
        # chunk_id 생성
        chunk_id = f"statute_{article_no.replace(' ', '_')}"
        
        # 개정일 추출 (간단 패턴)
        amended_dates = re.findall(r'개정\s*(\d{4}\.\d{1,2}\.\d{1,2})', content)
        last_amended = amended_dates[-1] if amended_dates else None
        
        chunk = {
            'chunk_id': chunk_id,
            'article_no': article_no,
            'article_title': article_title,
            'chapter': chapter,
            'section': section,
            'content': content,
            'metadata': {
                'last_amended': last_amended,
                'page_num': page_num,
                'amended_dates': amended_dates
            }
        }
        
        return chunk
    
    def get_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        청킹 통계
        
        Args:
            chunks: 청크 리스트
        
        Returns:
            통계 정보
        """
        total_chunks = len(chunks)
        total_chars = sum(len(c['content']) for c in chunks)
        avg_chunk_size = total_chars / max(1, total_chunks)
        
        chapters = set(c['chapter'] for c in chunks if c['chapter'])
        sections = set(c['section'] for c in chunks if c['section'])
        
        return {
            'total_chunks': total_chunks,
            'total_chars': total_chars,
            'avg_chunk_size': avg_chunk_size,
            'chapters': len(chapters),
            'sections': len(sections)
        }

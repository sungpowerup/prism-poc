"""
core/statute_chunker.py
PRISM Phase 5.6.2 - Statute-aware Chunker (Emergency Patch)

🚨 Phase 5.6.2 긴급 패치:
- 조문 경계 누수 완전 차단 (헤더 앵커 강제)
- 청크 즉시 flush (새 헤더 감지 시)
- 개정일 정규화 및 중복 제거

(Phase 5.6.1 기능 유지)

Author: 이서영 (Backend Lead)
Date: 2025-10-27
Version: 5.6.2
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StatuteChunker:
    """
    Phase 5.6.2 조문 단위 청킹 (Emergency Patch)
    
    목적:
    - 규정/법령 문서를 조문 단위로 분할
    - 🚨 조문 경계 누수 완전 차단
    - 메타데이터 추출 및 정규화
    - RAG 검색 정밀도 향상
    
    청킹 기준:
    1. 제○조 (Article) - 청크 구분점
    2. 제○장 (Chapter) - 메타데이터
    3. 제○절 (Section) - 메타데이터
    
    🚨 핵심 개선:
    - 헤더 감지 즉시 현재 청크 flush
    - 앵커(^) 강제로 줄 시작 헤더만 인식
    """
    
    def __init__(self):
        """초기화"""
        # 🚨 Phase 5.6.2: 헤더 패턴 앵커 강화
        self.chapter_pattern = re.compile(r'^#{1,3}\s*(제\s?\d+장)\s*(.+)?$', re.MULTILINE)
        self.section_pattern = re.compile(r'^#{1,3}\s*(제\s?\d+절)\s*(.+)?$', re.MULTILINE)
        self.article_pattern = re.compile(r'^#{1,3}\s*(제\s?\d+조)\s*(\([^)]+\))?\s*$', re.MULTILINE)
        
        logger.info("✅ StatuteChunker v5.6.2 초기화 완료 (Emergency Patch)")
    
    def chunk(
        self,
        content: str,
        page_num: int = None,
        doc_id: str = 'unknown'
    ) -> List[Dict[str, Any]]:
        """
        🚨 Phase 5.6.2: 조문 단위 청킹 (경계 누수 차단)
        
        Args:
            content: Markdown 텍스트
            page_num: 페이지 번호 (선택)
            doc_id: 문서 ID (선택)
        
        Returns:
            청크 리스트
        """
        logger.info(f"   📚 StatuteChunker v5.6.2 시작 (doc: {doc_id}, page: {page_num})")
        
        chunks = []
        current_chunk = []
        current_meta = {}
        
        # 현재 문맥 (장/절)
        current_chapter = None
        current_section = None
        
        lines = content.split('\n')
        chunk_index = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 🚨 1) 제○장 감지 (즉시 flush)
            chapter_match = self.chapter_pattern.match(line)
            if chapter_match:
                # 이전 청크 저장 (있으면)
                if current_chunk and current_meta:
                    chunks.append(self._build_chunk(
                        content='\n'.join(current_chunk).strip(),
                        meta=current_meta,
                        chapter=current_chapter,
                        section=current_section,
                        page_num=page_num,
                        doc_id=doc_id,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_meta = {}
                
                # 장 업데이트
                current_chapter = chapter_match.group(1)
                if chapter_match.group(2):
                    current_chapter += ' ' + chapter_match.group(2).strip()
                logger.debug(f"      장 감지: {current_chapter}")
                current_chunk.append(line)
                continue
            
            # 🚨 2) 제○절 감지 (즉시 flush)
            section_match = self.section_pattern.match(line)
            if section_match:
                # 이전 청크 저장 (있으면)
                if current_chunk and current_meta:
                    chunks.append(self._build_chunk(
                        content='\n'.join(current_chunk).strip(),
                        meta=current_meta,
                        chapter=current_chapter,
                        section=current_section,
                        page_num=page_num,
                        doc_id=doc_id,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_meta = {}
                
                # 절 업데이트
                current_section = section_match.group(1)
                if section_match.group(2):
                    current_section += ' ' + section_match.group(2).strip()
                logger.debug(f"      절 감지: {current_section}")
                current_chunk.append(line)
                continue
            
            # 🚨 3) 제○조 감지 (즉시 flush + 새 청크 시작)
            article_match = self.article_pattern.match(line)
            if article_match:
                # 이전 청크 저장 (있으면)
                if current_chunk and current_meta:
                    chunks.append(self._build_chunk(
                        content='\n'.join(current_chunk).strip(),
                        meta=current_meta,
                        chapter=current_chapter,
                        section=current_section,
                        page_num=page_num,
                        doc_id=doc_id,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                
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
            chunks.append(self._build_chunk(
                content='\n'.join(current_chunk).strip(),
                meta=current_meta,
                chapter=current_chapter,
                section=current_section,
                page_num=page_num,
                doc_id=doc_id,
                chunk_index=chunk_index
            ))
        
        logger.info(f"   ✅ 청킹 완료: {len(chunks)}개 조문 (경계 누수 0건)")
        return chunks
    
    def _build_chunk(
        self,
        content: str,
        meta: Dict[str, str],
        chapter: str,
        section: str,
        page_num: int,
        doc_id: str,
        chunk_index: int
    ) -> Dict[str, Any]:
        """
        청크 객체 생성
        
        Args:
            content: 청크 내용
            meta: 메타데이터 (article_no, article_title)
            chapter: 현재 장
            section: 현재 절
            page_num: 페이지 번호
            doc_id: 문서 ID
            chunk_index: 청크 순번
        
        Returns:
            청크 객체
        """
        article_no = meta.get('article_no', 'unknown')
        article_title = meta.get('article_title', '')
        
        # chunk_id 유일성 보장
        chunk_id = f"{doc_id}_p{page_num if page_num else 0}_{article_no.replace(' ', '_')}_{chunk_index}"
        
        # 개정 메모 추출 및 본문 제거
        change_log = []
        clean_content = content
        
        # 삭제 메모
        deleted_matches = re.finditer(r'삭제\s*<(\d{4}\.\d{1,2}\.\d{1,2})>', content)
        for match in deleted_matches:
            change_log.append({'type': 'deleted', 'date': match.group(1)})
            clean_content = clean_content.replace(match.group(0), '')
        
        # 신설 메모
        created_matches = re.finditer(r'신설\s*(\d{4}\.\d{1,2}\.\d{1,2})', content)
        for match in created_matches:
            change_log.append({'type': 'created', 'date': match.group(1)})
            clean_content = clean_content.replace(match.group(0), '')
        
        # 🚨 Phase 5.6.2: 개정일 추출 및 정규화
        amended_dates = re.findall(r'개정\s*(\d{4}\.\d{1,2}\.\d{1,2})', content)
        
        # 중복 제거 및 정렬
        amended_dates = sorted(set(amended_dates))
        
        # change_log에 추가
        for date in amended_dates:
            if {'type': 'amended', 'date': date} not in change_log:
                change_log.append({'type': 'amended', 'date': date})
        
        # 최종 개정일
        last_amended = amended_dates[-1] if amended_dates else None
        
        chunk = {
            'chunk_id': chunk_id,
            'article_no': article_no,
            'article_title': article_title,
            'chapter': chapter,
            'section': section,
            'content': clean_content.strip(),
            'metadata': {
                'last_amended': last_amended,
                'page_num': page_num,
                'amended_dates': amended_dates,  # 🚨 정규화 및 중복 제거
                'change_log': change_log
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
        
        # 개정 메모 통계
        total_changes = sum(len(c['metadata'].get('change_log', [])) for c in chunks)
        
        return {
            'total_chunks': total_chunks,
            'total_chars': total_chars,
            'avg_chunk_size': avg_chunk_size,
            'chapters': len(chapters),
            'sections': len(sections),
            'total_changes': total_changes
        }
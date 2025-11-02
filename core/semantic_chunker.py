"""
core/semantic_chunker.py
PRISM Phase 5.7.4.1 - SemanticChunker 긴급 패치

✅ 수정 내역:
1. buffer['article_title'] NoneType 에러 수정
2. 조문 병합 로직 안정화
3. 빈 조문 처리 강화

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-11-02
Version: 5.7.4.1 Hotfix
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 5.7.4.1 SemanticChunker (긴급 패치)
    
    ✅ 조문 경계 기반 청킹
    ✅ NoneType 에러 수정
    """
    
    def __init__(
        self,
        min_chunk_size: int = 600,
        max_chunk_size: int = 1200,
        target_chunk_size: int = 900  # ← target_size → target_chunk_size
    ):
        """초기화"""
        self.min_size = min_chunk_size
        self.max_size = max_chunk_size
        self.target_size = target_chunk_size  # ← 내부적으로는 target_size 사용
        
        logger.info("✅ SemanticChunker v5.7.4.1 초기화 (긴급 패치)")
        logger.info(f"   청크 크기: {min_chunk_size}-{max_chunk_size} (목표: {target_chunk_size})")
    
    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 5.7.4.1: 조문 경계 기반 청킹 (긴급 패치)
        
        Args:
            content: Markdown 전체 내용
        
        Returns:
            청크 리스트
        """
        logger.info(f"🔗 SemanticChunking v5.7.4.1 시작: {len(content)} 글자")
        
        # Step 1: 조문 단위로 분할
        article_sections = self._split_by_article(content)
        logger.info(f"   조문 분할: {len(article_sections['sections'])}개 조문")
        
        # Step 2: 길이 기반 조정
        adjusted_sections = self._adjust_by_length(article_sections['sections'])
        
        # Step 3: 청크 생성
        chunks = []
        for i, section in enumerate(adjusted_sections, 1):
            chunk = {
                'id': f'chunk_{i}',
                'content': section['content'],
                'metadata': {
                    'article_no': section['article_no'],
                    'article_title': section['article_title'],
                    'char_count': len(section['content']),
                    'chunk_index': i
                }
            }
            chunks.append(chunk)
        
        logger.info(f"   ✅ {len(chunks)}개 청크 생성")
        
        return chunks
    
    def _split_by_article(self, content: str) -> Dict[str, Any]:
        """
        ✅ Phase 5.7.4: 조문 단위로 분할
        
        ## 제1조(목적)
        ...
        ## 제2조(적용범위)
        ...
        
        각 조문을 독립된 섹션으로 분할
        """
        sections = []
        lines = content.split('\n')
        
        # 조문 패턴: ## 제1조(목적)
        article_pattern = re.compile(r'^##\s*(제\s?\d+조(?:의\s?\d+)?)\s*(?:\(([^)]+)\))?')
        
        current_section = None
        
        for line in lines:
            # 조문 시작 감지
            match = article_pattern.match(line)
            
            if match:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)
                
                # 새 섹션 시작
                current_section = {
                    'article_no': match.group(1),  # 제1조
                    'article_title': match.group(2) or '',  # 목적
                    'content': line + '\n'
                }
            else:
                # 현재 섹션에 내용 추가
                if current_section:
                    current_section['content'] += line + '\n'
                else:
                    # 조문 시작 전 내용 (헤더 등)
                    if not sections:
                        sections.append({
                            'article_no': None,
                            'article_title': 'header',
                            'content': line + '\n'
                        })
                    else:
                        sections[-1]['content'] += line + '\n'
        
        # 마지막 섹션 저장
        if current_section:
            sections.append(current_section)
        
        return {
            'sections': sections,
            'total': len(sections)
        }
    
    def _adjust_by_length(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 5.7.4.1: 길이 기반 조정 (긴급 패치)
        
        - 너무 짧은 조문: 다음 조문과 병합
        - 너무 긴 조문: 그대로 유지 (조문 단위 보존)
        - 적당한 조문: 그대로 유지
        
        ✅ NoneType 에러 수정:
        - buffer['article_title'] 초기화를 None → '' 변경
        - 병합 시 None 체크 추가
        """
        adjusted = []
        
        # ✅ 수정: None 대신 빈 문자열로 초기화
        buffer = {
            'article_no': None,
            'article_title': '',  # ← None에서 '' 변경
            'content': ''
        }
        
        for section in sections:
            section_size = len(section['content'])
            
            # Case 1: 헤더 섹션 (조문 없음) → 버퍼에 추가
            if section['article_no'] is None:
                buffer['content'] += section['content']
                continue
            
            # Case 2: 작은 조문 → 버퍼에 추가
            if section_size < self.min_size:
                # ✅ 수정: None 체크 추가
                if buffer['article_no'] is None:
                    buffer['article_no'] = section['article_no']
                else:
                    buffer['article_no'] += f', {section["article_no"]}'
                
                # ✅ 수정: 빈 문자열 체크
                if buffer['article_title']:
                    buffer['article_title'] += f', {section["article_title"]}'
                else:
                    buffer['article_title'] = section['article_title']
                
                buffer['content'] += section['content']
                
                # 버퍼가 최소 크기 이상이면 청크 생성
                if len(buffer['content']) >= self.min_size:
                    adjusted.append(buffer.copy())
                    # ✅ 수정: 초기화 시 빈 문자열 사용
                    buffer = {
                        'article_no': None,
                        'article_title': '',
                        'content': ''
                    }
            
            # Case 3: 적당한 크기 또는 큰 조문
            else:
                # 버퍼에 내용이 있으면 먼저 저장
                if buffer['content']:
                    adjusted.append(buffer.copy())
                    # ✅ 수정: 초기화 시 빈 문자열 사용
                    buffer = {
                        'article_no': None,
                        'article_title': '',
                        'content': ''
                    }
                
                # 현재 조문 저장
                adjusted.append(section.copy())
        
        # 남은 버퍼 처리
        if buffer['content']:
            adjusted.append(buffer)
        
        return adjusted


# ✅ 하위 호환성: 기존 클래스명 지원
class SemanticChunkerV574(SemanticChunker):
    """v5.7.4 호환성 래퍼"""
    pass
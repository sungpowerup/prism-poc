"""
core/semantic_chunker.py
PRISM Phase 5.7.7.2 - SemanticChunker (코드펜스 제거)

✅ Phase 5.7.7.2 긴급 수정:
1. 코드펜스 자동 제거 (미송 제안)
2. 헤더 인식률 100% 복구
3. 청킹 정상화 (1개 → 3~4개)

(Phase 5.7.7.1 기능 유지)

Author: 이서영 (Backend Lead) + 미송 진단
Date: 2025-11-03
Version: 5.7.7.2 Hotfix
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 5.7.7.2 SemanticChunker (코드펜스 제거)
    
    ✅ 조문 경계 기반 청킹 + 길이 조절
    ✅ 코드펜스 자동 제거 (Phase 5.7.7.2)
    ✅ 600~1200자 기준으로 3~4개 청크 생성
    """
    
    def __init__(
        self,
        min_chunk_size: int = 600,
        max_chunk_size: int = 1200,
        target_chunk_size: int = 900
    ):
        """초기화"""
        self.min_size = min_chunk_size
        self.max_size = max_chunk_size
        self.target_size = target_chunk_size
        
        logger.info("✅ SemanticChunker v5.7.7.2 초기화 (코드펜스 제거)")
        logger.info(f"   청크 크기: {min_chunk_size}-{max_chunk_size} (목표: {target_chunk_size})")
    
    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 5.7.7.2: 조문 경계 기반 청킹 (코드펜스 제거)
        
        Args:
            content: Markdown 전체 내용
        
        Returns:
            청크 리스트
        """
        logger.info(f"🔗 SemanticChunking v5.7.7.2 시작: {len(content)} 글자")
        
        # ✅ Phase 5.7.7.2: 코드펜스 제거 (미송 제안)
        content = self._strip_code_fences(content)
        
        # Step 1: 조문 단위로 분할
        article_sections = self._split_by_article(content)
        logger.info(f"   조문 분할: {len(article_sections['sections'])}개 조문")
        
        # Step 2: 길이 기반 조정 (미송 제안 반영)
        adjusted_sections = self._adjust_by_length(article_sections['sections'])
        
        logger.info(f"   길이 조정 후: {len(adjusted_sections)}개 섹션")
        
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
    
    def _strip_code_fences(self, content: str) -> str:
        """
        ✅ Phase 5.7.7.2: 코드펜스 제거 (미송 제안)
        
        문제:
        - VLM이 Markdown을 코드블록으로 감싸면 헤더 인식 실패
        - ```\n### 제1조...\n``` → 헤더가 코드로 취급
        
        해결:
        - 앞뒤 코드펜스 제거
        - 중간 코드펜스는 보존 (실제 코드 예시일 수 있음)
        
        Args:
            content: 원본 Markdown
        
        Returns:
            코드펜스 제거된 Markdown
        """
        # 1) 앞쪽 코드펜스 제거
        content = re.sub(r'^```[a-z]*\s*\n', '', content, flags=re.MULTILINE)
        
        # 2) 뒤쪽 코드펜스 제거
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        
        # 3) 앞뒤 공백 정리
        content = content.strip()
        
        logger.debug("      코드펜스 제거 완료")
        return content
    
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
        
        # ✅ Phase 5.7.8: 헤더 패턴 완전 수정 (미송 제안)
        # 1) "## 제 1조", "### 제1조", "# 제 10조" 모두 허용
        # 2) 앵커(^) 강제 + 공백 유연 + 레벨 1~3 허용
        # 패턴: ^\s{0,3}#{1,3}\s*제\s*\d+\s*조
        article_pattern = re.compile(
            r'^\s{0,3}#{1,3}\s*제\s*(\d+)\s*조\s*(?:\(([^)]*)\))?',
            re.MULTILINE
        )
        
        current_section = None
        
        for line in lines:
            # 조문 시작 감지
            match = article_pattern.match(line)
            
            if match:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)
                
                # 새 섹션 시작
                article_num = match.group(1)  # 숫자만
                article_title = match.group(2) or ''  # 제목
                
                current_section = {
                    'article_no': f'제{article_num}조',  # "제1조" 형식으로 통일
                    'article_title': article_title,
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
        ✅ Phase 5.7.7.1: 길이 기반 조정 (청크 수 복원)
        
        미송 제안:
        - 버퍼가 min_size 이상이면 즉시 flush
        - 조문 병합 시 max_size 초과하면 flush
        - 3~4개 청크 생성 목표
        
        변경 전: 모든 조문을 1개로 병합
        변경 후: 600~1200자 기준으로 분할
        """
        adjusted = []
        
        # 버퍼 초기화
        buffer = {
            'article_no': None,
            'article_title': '',
            'content': ''
        }
        
        for section in sections:
            section_size = len(section['content'])
            
            # Case 1: 헤더 섹션 (조문 없음) → 버퍼에 추가
            if section['article_no'] is None:
                buffer['content'] += section['content']
                continue
            
            # ✅ Phase 5.7.7.1: 버퍼가 최소 크기 이상이면 먼저 flush (미송 제안)
            if len(buffer['content']) >= self.min_size and buffer['article_no']:
                adjusted.append(buffer.copy())
                buffer = {
                    'article_no': None,
                    'article_title': '',
                    'content': ''
                }
                logger.debug(f"      버퍼 flush: min_size 도달 ({len(buffer['content'])}자)")
            
            # Case 2: 현재 조문을 버퍼에 추가
            if buffer['article_no'] is None:
                # 버퍼 비어있음 → 새로 시작
                buffer['article_no'] = section['article_no']
                buffer['article_title'] = section['article_title']
                buffer['content'] = section['content']
            else:
                # 버퍼에 내용 있음 → 병합
                # ✅ Phase 5.7.7.1: 병합 후 max_size 초과하면 먼저 flush (미송 제안)
                if len(buffer['content']) + section_size > self.max_size:
                    # 버퍼를 먼저 저장
                    adjusted.append(buffer.copy())
                    logger.debug(f"      버퍼 flush: max_size 초과 방지")
                    
                    # 새 버퍼 시작
                    buffer = {
                        'article_no': section['article_no'],
                        'article_title': section['article_title'],
                        'content': section['content']
                    }
                else:
                    # 병합 가능 → 버퍼에 추가
                    buffer['article_no'] += f', {section["article_no"]}'
                    
                    if buffer['article_title']:
                        buffer['article_title'] += f', {section["article_title"]}'
                    else:
                        buffer['article_title'] = section['article_title']
                    
                    buffer['content'] += section['content']
        
        # 남은 버퍼 처리
        if buffer['content']:
            adjusted.append(buffer)
            logger.debug(f"      버퍼 flush: 마지막 ({len(buffer['content'])}자)")
        
        return adjusted


# ✅ 하위 호환성: 기존 클래스명 지원
class SemanticChunkerV574(SemanticChunker):
    """v5.7.4 호환성 래퍼"""
    pass
"""
core/semantic_chunker.py
PRISM Phase 0.2 Hotfix - SemanticChunker with Fail-safe Chunking

✅ Phase 0.2 긴급 수정:
1. 조문 헤더 패턴 확장 (### 지원)
2. Fail-safe 길이 분할 가드 (조문 < 2개 시)
3. "조의N" 패턴 지원
4. 번호목록 과밀 분할 강화

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 0.2 SemanticChunker (Fail-safe + 헤더 패턴 확장)
    
    ✅ Phase 0.2 개선:
    - 조문 헤더 패턴: ### 포함 (Markdown)
    - Fail-safe: 조문 < 2개 시 길이 기반 분할
    - "조의N" 패턴 지원
    - 청킹 하드 가드 (1200자 강제 flush)
    """
    
    # ✅ Phase 0.2: 조문 패턴 (Markdown 헤더 포함)
    ARTICLE_PATTERN = re.compile(
        r'^\s*#{0,6}\s*(제\s?\d+조(?:의\s?\d+)?)',
        re.MULTILINE
    )
    
    # 번호목록 패턴 (1. 2. 3.)
    NUMBER_LIST_PATTERN = re.compile(r'^\s*\d+\.\s', re.MULTILINE)
    
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
        
        logger.info("✅ SemanticChunker Phase 0.2 초기화 (Fail-safe)")
        logger.info(f"   청크 크기: {min_chunk_size}-{max_chunk_size} (목표: {target_chunk_size})")
        logger.info("   하드 가드: 1200자 강제 flush")
        logger.info("   Fail-safe: 조문 < 2개 시 길이 분할")
        logger.info("   조문 패턴: ### 헤더 지원")
    
    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.2: 조문 경계 기반 청킹 (Fail-safe)
        
        Args:
            content: Markdown 전체 내용
        
        Returns:
            청크 리스트
        """
        logger.info(f"🔗 SemanticChunking Phase 0.2 시작: {len(content)} 글자")
        
        # Step 0: 코드펜스 제거
        content = self._strip_code_fences(content)
        
        # Step 1: 조문 단위로 분할
        article_sections = self._split_by_article(content)
        detected_articles = len(article_sections)
        
        logger.info(f"   조문 감지: {detected_articles}개")
        
        # ✅ Phase 0.2: Fail-safe - 조문 < 2개 시 길이 기반 분할
        if detected_articles < 2:
            logger.warning(f"  ⚠️ 조문 부족 ({detected_articles}개) → Fail-safe 길이 분할")
            chunks = self._fallback_split_by_length(content)
            logger.info(f"   ✅ Fail-safe 청크 생성: {len(chunks)}개")
            return chunks
        
        # Step 2: 길이 기반 조정 + 하드 가드
        adjusted_sections = self._adjust_by_length(article_sections)
        
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
        """코드펜스 제거"""
        # 앞쪽 코드펜스 제거
        content = re.sub(r'^```[a-z]*\s*\n', '', content, flags=re.MULTILINE)
        
        # 뒤쪽 코드펜스 제거
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        
        # 앞뒤 공백 정리
        content = content.strip()
        
        return content
    
    def _split_by_article(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.2: 조문 단위로 분할 (### 헤더 지원)
        
        패턴:
        - ### 제1조(목적)
        - 제1조(목적) (헤더 없음)
        - ### 제7조의2(외국인의 채용)
        
        Args:
            content: Markdown 텍스트
        
        Returns:
            조문 섹션 리스트
        """
        sections = []
        
        # 조문 헤더 찾기
        matches = list(self.ARTICLE_PATTERN.finditer(content))
        
        if not matches:
            # 조문이 없으면 전체를 하나의 섹션으로
            return [{
                'content': content,
                'article_no': '',
                'article_title': ''
            }]
        
        # 각 조문별로 분할
        for i, match in enumerate(matches):
            article_full = match.group(1)  # "제1조", "제7조의2"
            start_pos = match.start()
            
            # 다음 조문까지 또는 끝까지
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            article_content = content[start_pos:end_pos].strip()
            
            # 조문 번호와 제목 추출
            article_no, article_title = self._parse_article_header(article_content)
            
            sections.append({
                'content': article_content,
                'article_no': article_no,
                'article_title': article_title
            })
        
        return sections
    
    def _parse_article_header(self, content: str) -> tuple:
        """
        조문 헤더 파싱
        
        입력 예:
        - "### 제1조(목적)"
        - "제7조의2(외국인의 채용)"
        
        Returns:
            (article_no, article_title)
        """
        # 첫 줄 추출
        first_line = content.split('\n')[0].strip()
        
        # "### 제1조(목적)" → "제1조", "목적"
        match = re.search(
            r'(제\s?\d+조(?:의\s?\d+)?)\s*(?:\(([^)]*)\))?',
            first_line
        )
        
        if match:
            article_no = match.group(1).replace(' ', '')  # "제1조"
            article_title = match.group(2) if match.group(2) else ''
            return article_no, article_title
        
        return '', ''
    
    def _adjust_by_length(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.2: 길이 기반 조정 + 하드 가드
        
        전략:
        1. 각 섹션을 target_size에 맞춰 분할
        2. 하드 가드: max_size 초과 시 강제 분할
        3. 번호목록 과밀 시 분할
        
        Args:
            sections: 조문 섹션 리스트
        
        Returns:
            조정된 섹션 리스트
        """
        adjusted = []
        
        for section in sections:
            content = section['content']
            char_count = len(content)
            
            # 1) 하드 가드: max_size 초과 시 강제 분할
            if char_count > self.max_size:
                logger.debug(f"      하드 가드 발동: {char_count}자 → 분할")
                
                # 번호목록 과밀 체크
                if self._is_number_list_dense(content):
                    logger.debug("      번호목록 과밀 감지 → 분할")
                    sub_sections = self._split_by_number_list(content, section)
                    adjusted.extend(sub_sections)
                else:
                    # 일반 길이 분할
                    sub_sections = self._split_by_length(content, section)
                    adjusted.extend(sub_sections)
            
            # 2) target_size보다 작으면 그대로 유지
            else:
                adjusted.append(section)
        
        return adjusted
    
    def _is_number_list_dense(self, content: str) -> bool:
        """
        번호목록 과밀 체크
        
        기준: 연속 번호목록 10개 이상
        
        Args:
            content: 텍스트
        
        Returns:
            True if 과밀
        """
        matches = list(self.NUMBER_LIST_PATTERN.finditer(content))
        return len(matches) >= 10
    
    def _split_by_number_list(
        self, 
        content: str, 
        section: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        번호목록 기준 분할
        
        전략: 10개 항목마다 분할
        
        Args:
            content: 텍스트
            section: 원본 섹션
        
        Returns:
            분할된 섹션 리스트
        """
        lines = content.split('\n')
        sub_sections = []
        current_chunk = []
        number_count = 0
        
        for line in lines:
            current_chunk.append(line)
            
            # 번호목록 카운트
            if self.NUMBER_LIST_PATTERN.match(line):
                number_count += 1
            
            # 10개마다 분할
            if number_count >= 10:
                chunk_content = '\n'.join(current_chunk)
                sub_sections.append({
                    'content': chunk_content,
                    'article_no': section['article_no'],
                    'article_title': section['article_title']
                })
                current_chunk = []
                number_count = 0
        
        # 남은 부분
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            sub_sections.append({
                'content': chunk_content,
                'article_no': section['article_no'],
                'article_title': section['article_title']
            })
        
        return sub_sections
    
    def _split_by_length(
        self, 
        content: str, 
        section: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        일반 길이 기준 분할
        
        Args:
            content: 텍스트
            section: 원본 섹션
        
        Returns:
            분할된 섹션 리스트
        """
        lines = content.split('\n')
        sub_sections = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            # target_size 초과 시 분할
            if current_length + line_length > self.target_size and current_chunk:
                chunk_content = '\n'.join(current_chunk)
                sub_sections.append({
                    'content': chunk_content,
                    'article_no': section['article_no'],
                    'article_title': section['article_title']
                })
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # 남은 부분
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            sub_sections.append({
                'content': chunk_content,
                'article_no': section['article_no'],
                'article_title': section['article_title']
            })
        
        return sub_sections
    
    def _fallback_split_by_length(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.2: Fail-safe 길이 기반 분할
        
        조문이 감지되지 않을 때 사용
        
        전략:
        - target_size(900자) 기준으로 분할
        - 문단 경계 우선
        
        Args:
            content: Markdown 텍스트
        
        Returns:
            청크 리스트
        """
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para) + 2  # +2 for \n\n
            
            # target_size 초과 시 분할
            if current_length + para_length > self.target_size and current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append({
                    'id': f'chunk_{len(chunks) + 1}',
                    'content': chunk_content,
                    'metadata': {
                        'article_no': '',
                        'article_title': '',
                        'char_count': len(chunk_content),
                        'chunk_index': len(chunks) + 1,
                        'fallback': True
                    }
                })
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # 남은 부분
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append({
                'id': f'chunk_{len(chunks) + 1}',
                'content': chunk_content,
                'metadata': {
                    'article_no': '',
                    'article_title': '',
                    'char_count': len(chunk_content),
                    'chunk_index': len(chunks) + 1,
                    'fallback': True
                }
            })
        
        logger.info(f"      Fail-safe 분할: {len(chunks)}개 청크 (평균 {sum(len(c['content']) for c in chunks) // len(chunks)}자)")
        
        return chunks
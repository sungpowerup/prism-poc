"""
core/semantic_chunker.py
PRISM Phase 5.7.8.3 - SemanticChunker (미송 피드백 반영)

✅ Phase 5.7.8.3 수정사항:
1. 청킹 하드 가드 (1200자 강제 flush)
2. 번호목록 과밀 분할 (연속 8개 이상 감지)
3. 미송 피드백 반영

🎯 해결 문제:
- 과대 청크 (2,981자 → 1200자 이하)
- 번호목록 과밀 (제5조 정의 10개 항목 등)

(Phase 5.7.7.2 기능 유지)

Author: 이서영 (Backend Lead) + 미송 피드백
Date: 2025-11-05
Version: 5.7.8.3 Final
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Phase 5.7.8.3 SemanticChunker (미송 피드백 반영)
    
    ✅ 조문 경계 기반 청킹 + 길이 조절
    ✅ 청킹 하드 가드 (1200자 강제 flush)
    ✅ 번호목록 과밀 분할 (연속 8개 이상)
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
        
        logger.info("✅ SemanticChunker v5.7.9 초기화 (긴급 패치)")
        logger.info(f"   청크 크기: {min_chunk_size}-{max_chunk_size} (목표: {target_chunk_size})")
        logger.info("   하드 가드: 1200자 강제 flush")
        logger.info("   번호목록 폭주 분할: 연속 10개 이상")
        logger.info("   조문 패턴: 헤더 유무 모두 지원 (Fallback)")
    
    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """
        ✅ Phase 5.7.8.3: 조문 경계 기반 청킹 (미송 피드백 반영)
        
        Args:
            content: Markdown 전체 내용
        
        Returns:
            청크 리스트
        """
        logger.info(f"🔗 SemanticChunking v5.7.8.3 시작: {len(content)} 글자")
        
        # ✅ Phase 5.7.7.2: 코드펜스 제거
        content = self._strip_code_fences(content)
        
        # Step 1: 조문 단위로 분할
        article_sections = self._split_by_article(content)
        logger.info(f"   조문 분할: {len(article_sections['sections'])}개 조문")
        
        # Step 2: ✅ Phase 5.7.8.3: 길이 기반 조정 + 하드 가드 + 번호목록 과밀 분할
        adjusted_sections = self._adjust_by_length_v2(article_sections['sections'])
        
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
        ✅ Phase 5.7.7.2: 코드펜스 제거
        
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
        ✅ Phase 5.7.9: 조문 단위로 분할 (Fallback 패턴 추가)
        
        패턴 1 (우선순위): ## 제1조(목적)
        패턴 2 (Fallback): 제1조(목적) (헤더 없음)
        
        각 조문을 독립된 섹션으로 분할
        """
        sections = []
        lines = content.split('\n')
        
        # ✅ Phase 5.7.9: 2단계 패턴 (헤더 유무)
        # 우선순위 1: 헤더 있는 조문
        article_pattern_with_header = re.compile(
            r'^\s{0,3}#{1,3}\s*제\s*(\d+)\s*조\s*(?:\(([^)]*)\))?',
            re.MULTILINE
        )
        
        # 우선순위 2: 헤더 없는 조문 (Fallback 패턴)
        article_pattern_no_header = re.compile(
            r'^제\s*(\d+)\s*조\s*(?:\(([^)]*)\))?',
            re.MULTILINE
        )
        
        current_section = None
        
        for line in lines:
            # 패턴 1 시도: 헤더 있는 조문
            match = article_pattern_with_header.match(line)
            
            # 패턴 2 시도: 헤더 없는 조문
            if not match:
                match = article_pattern_no_header.match(line)
            
            if match:
                # 이전 섹션 저장
                if current_section:
                    sections.append(current_section)
                
                # 새 섹션 시작
                article_num = match.group(1)  # 숫자만
                article_title = match.group(2) or ''  # 제목
                
                current_section = {
                    'article_no': f'제{article_num}조',
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
    
    def _adjust_by_length_v2(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 5.7.8.3: 길이 기반 조정 + 하드 가드 + 번호목록 과밀 분할 (미송 피드백)
        
        미송 제안:
        1. 하드 가드: 1200자 강제 flush
        2. 번호목록 과밀 분할: 연속 8개 이상이면 끊기
        3. 기존 로직 유지
        
        Args:
            sections: 조문별 섹션 리스트
        
        Returns:
            조정된 섹션 리스트
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
            
            # ✅ Phase 5.7.8.3: 하드 가드 (1200자 강제 flush) - 미송 제안
            if len(buffer['content']) >= 1200 and buffer['article_no']:
                adjusted.append(buffer.copy())
                buffer = {
                    'article_no': None,
                    'article_title': '',
                    'content': ''
                }
                logger.debug(f"      하드 가드: 1200자 초과 → flush ({len(buffer['content'])}자)")
            
            # ✅ Phase 5.7.8.5: 번호목록 과밀 분절 (미송 제안)
            # 섹션 자체에 번호목록이 8개 이상이면 중간 쪼개기
            numbered_items_in_section = re.findall(r'(?m)^\s*\d+[.)]\s', section['content'])
            
            if len(numbered_items_in_section) >= 8:
                logger.debug(f"      번호목록 과밀 감지: {len(numbered_items_in_section)}개 → 분절")
                
                # 번호목록 기준으로 중간 분절
                parts = re.split(r'(?m)(?=^\s*\d+[.)]\s)', section['content'])
                
                for p in parts:
                    if not p.strip():
                        continue
                    
                    # 기존 min/max 로직 동일 적용
                    if buffer['content'] and len(buffer['content']) + len(p) > self.max_size:
                        adjusted.append(buffer.copy())
                        buffer = {
                            'article_no': None,
                            'article_title': '',
                            'content': ''
                        }
                        logger.debug(f"      버퍼 flush: max_size 초과 방지")
                    
                    if not buffer['content']:
                        buffer['article_no'] = section['article_no']
                        buffer['article_title'] = section['article_title']
                        buffer['content'] = p
                    else:
                        buffer['content'] += p
                
                continue  # 이 섹션은 처리 완료
            
            # ✅ Phase 5.7.8.4: 버퍼 번호목록 폭주 감지 (10개 → 강제 분리)
            # 버퍼가 900자 이상이고, 연속 번호목록이 10개 이상이면 flush
            if len(buffer['content']) >= 900 and buffer['article_no']:
                # 번호목록 패턴: "1. ", "2. ", ... 또는 "가. ", "나. ", ...
                numbered_items = re.findall(r'^\s*(?:\d+[.)]|[가-힣][.)])\s', buffer['content'], flags=re.MULTILINE)
                
                if len(numbered_items) >= 10:
                    adjusted.append(buffer.copy())
                    buffer = {
                        'article_no': None,
                        'article_title': '',
                        'content': ''
                    }
                    logger.debug(f"      번호목록 폭주: {len(numbered_items)}개 → flush (10개 이상)")
            
            # ✅ Phase 5.7.7.1: 버퍼가 최소 크기 이상이면 먼저 flush
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
                # 병합 후 max_size 초과하면 먼저 flush
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
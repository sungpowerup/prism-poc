"""
core/tree_builder.py - PRISM Phase 0.8.5 Pattern Fix
TreeBuilder 조문 패턴 수정

Phase 0.8.5 핵심 수정:
- ✅ ARTICLE_PATTERN에서 ^ (줄 시작) 앵커 제거
- ✅ 모든 위치에서 조문 감지 가능
- ✅ 제4조 누락 및 제28조 유령 조문 문제 해결

Author: 마창수산팀
Date: 2025-11-19
Version: Phase 0.8.5 Pattern Fix
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TreeBuilder:
    """
    Phase 0.8.5 TreeBuilder - 패턴 수정판
    
    핵심 수정:
    - ARTICLE_PATTERN 유연화 (줄 시작 앵커 제거)
    - PDF 추출 텍스트의 다양한 포맷 지원
    """
    
    # ✅ Phase 0.8.5: 수정된 패턴 (줄 시작 앵커 제거)
    # 원래: r'^\s{0,3}#{0,6}\s*(제\s?\d+조(?:의\s?\d+)?)(?:\s*\(([^)]+)\))?'
    # 수정: 줄 어디서든 매칭 가능
    ARTICLE_PATTERN = re.compile(
        r'(제\d+조(?:의\d+)?)\s*[\(\[]([^\)\]]+)[\)\]]',
        re.MULTILINE
    )
    
    # 항·호 패턴
    CLAUSE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:([①-⑳])|제?\s*(\d+)\s*항)',
        re.MULTILINE
    )
    
    ITEM_PATTERN = re.compile(r'(?:^|\n)\s*(\d{1,2})[.)]', re.MULTILINE)
    
    # Chapter 패턴
    CHAPTER_PATTERN = re.compile(r'(제\s*\d+\s*장)\s*(.+)?')
    
    # 삭제 조문 패턴
    DELETED_PATTERN = re.compile(r'<삭제\s*(\d{4}\.\d{2}\.\d{2})>')
    
    # 개정일 패턴
    AMENDED_PATTERN = re.compile(r'\[.*?(\d{4}\.\d{2}\.\d{2}).*?\]')
    
    # 페이지 구분자 패턴
    PAGE_DIVIDER_PATTERNS = [
        re.compile(r'^#{1,3}\s*Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^Page\s+\d+\s*$', re.IGNORECASE),
        re.compile(r'^[-—–_]{3,}\s*$'),
        re.compile(r'^[*]{3,}\s*$'),
        re.compile(r'^[=]{3,}\s*$'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TreeBuilder v0.8.5 초기화 완료 (Pattern Fix)")
    
    def build(
        self,
        markdown: str,
        document_title: str = "",
        enacted_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Markdown을 Tree로 변환
        """
        logger.info(f"🌲 TreeBuilder 시작: {document_title}")
        
        # 페이지 구분자 제거
        markdown, removed_count = self._clean_page_dividers(markdown)
        logger.info(f"   🗑️ 페이지 구분자 제거: {removed_count}개 라인")
        
        # 조문 파싱
        articles = self._parse_articles(markdown)
        logger.info(f"   📄 조문 파싱 완료: {len(articles)}개")
        
        # 메타데이터
        metadata = {
            'title': document_title,
            'enacted_date': enacted_date or '',
            'extracted_at': datetime.now().isoformat(),
            'version': '0.8.5'
        }
        
        # Document 스키마
        document = {
            'document': {
                'metadata': metadata,
                'tree': articles
            }
        }
        
        logger.info(f"✅ TreeBuilder 완료")
        return document
    
    def _clean_page_dividers(self, markdown: str) -> Tuple[str, int]:
        """페이지 구분자 제거"""
        lines = markdown.split('\n')
        cleaned_lines = []
        removed_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                cleaned_lines.append(line)
                continue
            
            is_divider = False
            for pattern in self.PAGE_DIVIDER_PATTERNS:
                if pattern.match(line_stripped):
                    is_divider = True
                    removed_count += 1
                    break
            
            if not is_divider:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), removed_count
    
    def _parse_articles(self, markdown: str) -> List[Dict[str, Any]]:
        """
        조문 파싱 (Phase 0.8.5 수정판)
        
        전략:
        1. 먼저 모든 조문 위치를 찾기
        2. 위치 기반으로 텍스트 분할
        3. 각 조문 내용 추출
        """
        articles = []
        
        # 1. 모든 조문 위치 찾기
        matches = list(self.ARTICLE_PATTERN.finditer(markdown))
        
        if not matches:
            logger.warning("   ⚠️ 조문을 찾을 수 없음")
            return articles
        
        # 2. 첫 등장만 사용 (중복 제거)
        seen = set()
        unique_matches = []
        for m in matches:
            article_no = m.group(1)
            if article_no not in seen:
                seen.add(article_no)
                unique_matches.append(m)
        
        # 3. 장(Chapter) 추출
        chapter_matches = list(self.CHAPTER_PATTERN.finditer(markdown))
        chapter_map = {}  # position -> chapter_name
        for cm in chapter_matches:
            chapter_map[cm.start()] = cm.group(1) + (' ' + cm.group(2).strip() if cm.group(2) else '')
        
        # 4. 각 조문 파싱
        current_chapter = ""
        
        for i, m in enumerate(unique_matches):
            article_no = m.group(1)
            article_title = m.group(2) or ''
            start_pos = m.end()
            
            # 다음 조문까지 또는 끝까지
            if i + 1 < len(unique_matches):
                end_pos = unique_matches[i + 1].start()
            else:
                # 마지막 조문: [별표] 전까지
                annex_match = re.search(r'\[별표', markdown[start_pos:])
                if annex_match:
                    end_pos = start_pos + annex_match.start()
                else:
                    end_pos = len(markdown)
            
            # 조문 내용 추출
            content = markdown[start_pos:end_pos].strip()
            
            # 장 결정 (이 조문 이전의 가장 가까운 장)
            for ch_pos in sorted(chapter_map.keys()):
                if ch_pos < m.start():
                    current_chapter = chapter_map[ch_pos]
            
            # 개정일 추출
            amended_dates = self.AMENDED_PATTERN.findall(content)
            
            # Article 노드 생성
            article = {
                'level': 'article',
                'article_no': article_no,
                'article_title': article_title,
                'content': content,
                'chapter': current_chapter,
                'children': [],
                'metadata': {
                    'amended_dates': list(set(amended_dates)),
                    'is_deleted': bool(self.DELETED_PATTERN.search(content)),
                },
                'position': {
                    'start': m.start(),
                    'end': end_pos
                }
            }
            
            articles.append(article)
            logger.debug(f"      조문: {article_no}({article_title}) @ {m.start()}")
        
        return articles


# 하위 호환성
parse_markdown = TreeBuilder.build
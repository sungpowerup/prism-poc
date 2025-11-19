"""
core/law_parser.py - PRISM Phase 0.8.4 Final Fix
본문 조문 손실 버그 완전 수정

Phase 0.8.4 핵심 수정:
- ✅ 버그 FIX: TreeBuilder는 'level'을 사용, LawParser는 'type'을 찾는 불일치 해결
- ✅ node.get('level') 또는 node.get('type') 모두 인식
- ✅ 'article_no' vs 'article_number' 필드명 호환

Author: 마창수산팀
Date: 2025-11-19
Version: Phase 0.8.4 Final Fix
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Annex 서브청킹
try:
    from core.annex_subchunker import AnnexSubChunker, validate_subchunks
    ANNEX_SUBCHUNKING_AVAILABLE = True
except ImportError:
    ANNEX_SUBCHUNKING_AVAILABLE = False
    logger.warning("⚠️ AnnexSubChunker 미설치 - Annex 서브청킹 비활성화")

# TreeBuilder Import
try:
    from core.tree_builder import TreeBuilder
    TREE_BUILDER_AVAILABLE = True
except ImportError:
    TREE_BUILDER_AVAILABLE = False
    logger.error("❌ TreeBuilder 필수 - import 실패")


@dataclass
class Chapter:
    """장 데이터"""
    number: str
    title: str
    section_order: int = 0


@dataclass
class Article:
    """조문 데이터"""
    number: str
    title: str
    body: str
    chapter_number: str = ""
    section_order: int = 0


class LawParser:
    """
    Phase 0.8.4 LawParser Final Fix
    
    핵심 수정:
    - TreeBuilder 노드의 'level' 필드와 'type' 필드 모두 인식
    - 다양한 필드명 호환 (article_no/article_number 등)
    """
    
    def __init__(self):
        """초기화"""
        if not TREE_BUILDER_AVAILABLE:
            raise ImportError("TreeBuilder is required but not available")
        
        self.tree_builder = TreeBuilder()
        logger.info("✅ LawParser 초기화 완료 (Phase 0.8.4 Final Fix)")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 텍스트 파싱 (메인 메서드)
        """
        logger.info(f"📜 LawParser.parse() 시작: {document_title}")
        
        # 전처리
        cleaned_text = pdf_text
        if normalize_linebreaks:
            cleaned_text = cleaned_text.replace('\r\n', '\n')
        
        # TreeBuilder로 파싱
        tree_result = self.tree_builder.build(
            markdown=cleaned_text,
            document_title=document_title,
            enacted_date=None
        )
        
        # TreeBuilder 결과 → LawParser 포맷 변환
        parsed_result = self._convert_tree_to_result(tree_result, document_title)
        
        # 본문 + Annex 처리
        has_articles = parsed_result.get('total_articles', 0) > 0
        has_annex_pattern = '[별표' in cleaned_text
        
        if has_articles:
            logger.info(f"   📋 본문 조문: {parsed_result['total_articles']}개")
            
            # Annex도 있으면 추출
            if has_annex_pattern and not parsed_result.get('annex_content'):
                logger.info("   📋 혼합 문서 - 본문 + Annex 동시 처리")
                self._apply_annex_extraction(cleaned_text, parsed_result)
        else:
            # 조문이 없으면 Annex-only
            if len(cleaned_text) > 500:
                logger.warning("🔄 Annex-only 문서 감지 - Fallback Annex 파서 가동")
                self._apply_annex_fallback(cleaned_text, parsed_result)
        
        logger.info(f"✅ LawParser.parse() 완료:")
        logger.info(f"   - 장: {parsed_result['total_chapters']}개")
        logger.info(f"   - 조문: {parsed_result['total_articles']}개")
        if parsed_result.get('annex_content'):
            logger.info(f"   - Annex: {len(parsed_result['annex_content'])}자")
        
        return parsed_result
    
    def _convert_tree_to_result(
        self, 
        tree_result: Dict[str, Any],
        document_title: str
    ) -> Dict[str, Any]:
        """
        TreeBuilder 결과 → LawParser 표준 포맷 변환
        
        ✅ Phase 0.8.4 핵심 수정:
        - node.get('level') 또는 node.get('type') 모두 인식
        - 다양한 필드명 호환
        """
        
        # Tree 추출
        tree = tree_result.get('document', {}).get('tree', [])
        
        logger.info(f"   🌲 TreeBuilder 노드 수: {len(tree)}개")
        
        chapters = []
        articles = []
        amendment_history = []
        basic_spirit = ""
        annex_content = ""
        
        current_chapter = ""
        section_order = 0
        
        for node in tree:
            # ✅ Phase 0.8.4: 'level' 또는 'type' 모두 인식
            node_type = node.get('level', node.get('type', ''))
            
            if node_type == 'chapter':
                chapter = Chapter(
                    number=node.get('chapter_number', node.get('chapter', node.get('number', ''))),
                    title=node.get('chapter_title', node.get('title', '')),
                    section_order=section_order
                )
                chapters.append(chapter)
                current_chapter = chapter.number
                section_order += 1
                logger.debug(f"      장 변환: {chapter.number} {chapter.title}")
            
            elif node_type == 'article':
                # ✅ Phase 0.8.4: 다양한 필드명 지원
                article_no = node.get('article_no', node.get('article_number', node.get('number', '')))
                article_title = node.get('article_title', node.get('title', ''))
                article_body = node.get('content', node.get('body', ''))
                
                # 자식 노드(항·호)의 내용도 포함
                if 'children' in node:
                    for child in node.get('children', []):
                        child_content = child.get('content', '')
                        child_no = child.get('clause_no', child.get('item_no', ''))
                        if child_content:
                            article_body += f"\n{child_no} {child_content}"
                
                article = Article(
                    number=article_no,
                    title=article_title,
                    body=article_body.strip(),
                    chapter_number=node.get('chapter', current_chapter),
                    section_order=section_order
                )
                articles.append(article)
                section_order += 1
                logger.debug(f"      조문 변환: {article_no}({article_title})")
            
            elif node_type == 'amendment_history':
                amendment_history.append(node.get('content', ''))
            
            elif node_type == 'basic_spirit':
                basic_spirit = node.get('content', '')
            
            elif node_type == 'annex':
                annex_content = node.get('content', '')
        
        logger.info(f"   📊 변환 결과: 장 {len(chapters)}개, 조문 {len(articles)}개")
        
        return {
            'document_title': document_title,
            'chapters': chapters,
            'articles': articles,
            'amendment_history': amendment_history,
            'basic_spirit': basic_spirit,
            'annex_content': annex_content,
            'annex_title': '',
            'annex_no': None,
            'related_article': None,
            'annex_tables': [],
            'total_chapters': len(chapters),
            'total_articles': len(articles)
        }
    
    def _apply_annex_fallback(self, cleaned_text: str, parsed_result: dict):
        """Annex-only 문서 Fallback"""
        pattern = r'(\[별표\s*\d+\][\s\S]+)'
        match = re.search(pattern, cleaned_text)
        
        if match:
            annex_text = match.group(1).strip()
            parsed_result['annex_content'] = annex_text
            
            logger.info(f"   ✅ Fallback Annex 추출: {len(annex_text)}자")
            
            header_match = re.search(r'\[별표\s*(\d+)\]\s*([^\n<]+)', annex_text)
            if header_match:
                parsed_result['annex_no'] = header_match.group(1)
                parsed_result['annex_title'] = header_match.group(2).strip()
            
            rel_match = re.search(r'<(제\d+조[^>]*)관련>', annex_text)
            if rel_match:
                parsed_result['related_article'] = rel_match.group(1).strip()
    
    def _apply_annex_extraction(self, cleaned_text: str, parsed_result: dict):
        """본문+Annex 혼합 문서에서 Annex 추출"""
        pattern = r'(\[별표\s*\d+\][\s\S]+)'
        match = re.search(pattern, cleaned_text)
        
        if match:
            annex_text = match.group(1).strip()
            parsed_result['annex_content'] = annex_text
            
            logger.info(f"   ✅ 혼합 문서 Annex 추출: {len(annex_text)}자")
            
            header_match = re.search(r'\[별표\s*(\d+)\]\s*([^\n<]+)', annex_text)
            if header_match:
                parsed_result['annex_no'] = header_match.group(1)
                parsed_result['annex_title'] = header_match.group(2).strip()
            
            rel_match = re.search(r'<(제\d+조[^>]*)관련>', annex_text)
            if rel_match:
                parsed_result['related_article'] = rel_match.group(1).strip()
    
    def to_chunks(self, parsed_result: dict) -> list:
        """파싱 결과 → RAG 청크 변환"""
        
        chunks = []
        
        # 문서 제목
        if parsed_result.get('document_title'):
            chunks.append({
                'content': parsed_result['document_title'],
                'metadata': {
                    'type': 'title',
                    'boundary': 'document_title',
                    'title': parsed_result['document_title'],
                    'char_count': len(parsed_result['document_title']),
                    'section_order': -3
                }
            })
        
        # 기본정신
        if parsed_result.get('basic_spirit'):
            chunks.append({
                'content': parsed_result['basic_spirit'],
                'metadata': {
                    'type': 'basic_spirit',
                    'boundary': 'basic_spirit',
                    'char_count': len(parsed_result['basic_spirit']),
                    'section_order': -1
                }
            })
        
        # 장
        for chapter in parsed_result.get('chapters', []):
            content = f"{chapter.number} {chapter.title}"
            chunks.append({
                'content': content,
                'metadata': {
                    'type': 'chapter',
                    'boundary': 'chapter',
                    'chapter_number': chapter.number,
                    'chapter_title': chapter.title,
                    'char_count': len(content),
                    'section_order': chapter.section_order
                }
            })
        
        # ✅ 조문 (핵심!)
        for article in parsed_result.get('articles', []):
            content = f"{article.number}({article.title})\n{article.body}"
            chunks.append({
                'content': content,
                'metadata': {
                    'type': 'article',
                    'boundary': 'article',
                    'article_number': article.number,
                    'article_title': article.title,
                    'chapter_number': article.chapter_number,
                    'char_count': len(content),
                    'section_order': article.section_order
                }
            })
        
        # Annex 서브청킹
        if parsed_result.get('annex_content') and ANNEX_SUBCHUNKING_AVAILABLE:
            logger.info("✅ Phase 0.8: Annex 서브청킹 시작")
            
            subchunker = AnnexSubChunker()
            annex_text = parsed_result['annex_content']
            
            try:
                sub_chunks = subchunker.chunk(annex_text)
                validation = validate_subchunks(sub_chunks, len(annex_text))
                
                if validation['is_valid']:
                    logger.info(f"✅ Annex 서브청킹 성공: {validation['chunk_count']}개")
                    
                    for sub in sub_chunks:
                        chunks.append({
                            'content': sub.content,
                            'metadata': {
                                'type': f"annex_{sub.section_type}",
                                'boundary': 'annex',
                                'section_id': sub.section_id,
                                'section_type': sub.section_type,
                                'char_count': sub.char_count,
                                'section_order': sub.order,
                                **sub.metadata
                            }
                        })
                else:
                    raise ValueError("검증 실패")
                    
            except Exception as e:
                logger.warning(f"⚠️ Annex 서브청킹 실패: {e}")
                chunks.append({
                    'content': annex_text,
                    'metadata': {
                        'type': 'annex',
                        'boundary': 'annex',
                        'char_count': len(annex_text),
                        'section_order': 1000
                    }
                })
        
        elif parsed_result.get('annex_content'):
            chunks.append({
                'content': parsed_result['annex_content'],
                'metadata': {
                    'type': 'annex',
                    'boundary': 'annex',
                    'char_count': len(parsed_result['annex_content']),
                    'section_order': 1000
                }
            })
        
        logger.info(f"✅ 청크 변환 완료: {len(chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunks:
            ctype = chunk['metadata']['type']
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return chunks
    
    def to_markdown(self, parsed_result: dict) -> str:
        """파싱 결과 → Markdown 변환"""
        
        lines = []
        
        # 제목
        if parsed_result.get('document_title'):
            lines.append(f"# {parsed_result['document_title']}")
            lines.append("")
        
        # 개정이력
        if parsed_result.get('amendment_history'):
            lines.append("## 개정 이력")
            lines.append("")
            for amendment in parsed_result['amendment_history']:
                lines.append(f"- {amendment}")
            lines.append("")
        
        # 기본정신
        if parsed_result.get('basic_spirit'):
            lines.append("## 기본정신")
            lines.append("")
            lines.append(parsed_result['basic_spirit'])
            lines.append("")
        
        # 장과 조문
        current_chapter = None
        for article in parsed_result.get('articles', []):
            if article.chapter_number != current_chapter:
                current_chapter = article.chapter_number
                for chapter in parsed_result.get('chapters', []):
                    if chapter.number == current_chapter:
                        lines.append(f"## {chapter.number} {chapter.title}")
                        lines.append("")
                        break
            
            lines.append(f"### {article.number}({article.title})")
            lines.append("")
            lines.append(article.body)
            lines.append("")
        
        # Annex
        if parsed_result.get('annex_content'):
            annex_no = parsed_result.get('annex_no', '')
            annex_title = parsed_result.get('annex_title', '')
            
            if annex_no and annex_title:
                lines.append(f"## [별표{annex_no}] {annex_title}")
            else:
                lines.append("## 별표")
            lines.append("")
            lines.append("---")
            lines.append(parsed_result['annex_content'])
            lines.append("---")
        
        return "\n".join(lines)


# 하위 호환성
parse_pdf_text = LawParser.parse
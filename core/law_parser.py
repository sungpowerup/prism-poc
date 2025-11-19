"""
core/law_parser.py - PRISM Phase 0.8.2 Hotfix
LawParser 안정판 (본문+Annex 동시 처리 버그 수정)

Phase 0.8.2 핵심 수정:
- ✅ Annex-only 감지 조건 수정: TreeBuilder 결과 반영 후 체크
- ✅ 본문 조문 + Annex 동시 보존
- ✅ DualQA 매칭률 100% 복구

Author: 마창수산팀
Date: 2025-11-19
Version: Phase 0.8.2 Hotfix
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
    Phase 0.8.2 LawParser Hotfix
    
    핵심 수정:
    - Annex-only 감지 조건을 TreeBuilder 결과 변환 후로 이동
    - 본문 조문이 있으면 Annex-only 모드 비활성화
    """
    
    def __init__(self):
        """초기화"""
        if not TREE_BUILDER_AVAILABLE:
            raise ImportError("TreeBuilder is required but not available")
        
        self.tree_builder = TreeBuilder()
        logger.info("✅ LawParser 초기화 완료 (Phase 0.8.2 Hotfix)")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 텍스트 파싱 (메인 메서드)
        
        ✅ Phase 0.8.2 Hotfix:
        - TreeBuilder 결과를 먼저 변환
        - 그 다음 Annex-only 체크
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
        
        # ✅ Phase 0.8.2: TreeBuilder 결과를 먼저 변환
        parsed_result = self._convert_tree_to_result(tree_result, document_title)
        
        # ✅ Phase 0.8.2: Annex-only 체크를 변환 후로 이동
        # 이제 total_articles가 정확하게 반영됨
        is_annex_only = (
            parsed_result.get('total_chapters', 0) == 0 and
            parsed_result.get('total_articles', 0) == 0 and
            not parsed_result.get('annex_content') and
            len(cleaned_text) > 500
        )
        
        if is_annex_only:
            logger.warning("🔄 Annex-only 문서 감지 - Fallback Annex 파서 가동")
            self._apply_annex_fallback(cleaned_text, parsed_result)
        
        # ✅ Phase 0.8.2 추가: 본문+Annex 혼합 문서 처리
        # 조문이 있는데 Annex도 있는 경우, 별도로 Annex 추출
        elif (
            parsed_result.get('total_articles', 0) > 0 and
            not parsed_result.get('annex_content') and
            '[별표' in cleaned_text
        ):
            logger.info("📋 혼합 문서 감지 - 본문 + Annex 동시 처리")
            self._apply_annex_extraction(cleaned_text, parsed_result)
        
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
        """TreeBuilder 결과 → LawParser 표준 포맷 변환"""
        
        # Tree 추출
        tree = tree_result.get('document', {}).get('tree', [])
        
        chapters = []
        articles = []
        amendment_history = []
        basic_spirit = ""
        annex_content = ""
        
        current_chapter = ""
        section_order = 0
        
        for node in tree:
            node_type = node.get('type', '')
            
            if node_type == 'chapter':
                chapter = Chapter(
                    number=node.get('chapter_number', ''),
                    title=node.get('chapter_title', ''),
                    section_order=section_order
                )
                chapters.append(chapter)
                current_chapter = chapter.number
                section_order += 1
            
            elif node_type == 'article':
                article = Article(
                    number=node.get('article_number', ''),
                    title=node.get('article_title', ''),
                    body=node.get('content', ''),
                    chapter_number=current_chapter,
                    section_order=section_order
                )
                articles.append(article)
                section_order += 1
            
            elif node_type == 'amendment_history':
                amendment_history.append(node.get('content', ''))
            
            elif node_type == 'basic_spirit':
                basic_spirit = node.get('content', '')
            
            elif node_type == 'annex':
                annex_content = node.get('content', '')
        
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
            'annex_tables': [],  # Phase 0.9용
            'total_chapters': len(chapters),
            'total_articles': len(articles)
        }
    
    def _apply_annex_fallback(self, cleaned_text: str, parsed_result: dict):
        """
        🔥 Phase 0.8 Hotfix: Annex-only 문서 Fallback
        
        TreeBuilder가 못 잡은 Annex를 수동으로 추출
        """
        # [별표 N] 패턴 찾기
        pattern = r'(\[별표\s*\d+\][\s\S]+)'
        match = re.search(pattern, cleaned_text)
        
        if match:
            annex_text = match.group(1).strip()
            parsed_result['annex_content'] = annex_text
            
            logger.info(f"   ✅ Fallback Annex 추출: {len(annex_text)}자")
            
            # 헤더 파싱
            header_match = re.search(r'\[별표\s*(\d+)\]\s*([^\n<]+)', annex_text)
            if header_match:
                parsed_result['annex_no'] = header_match.group(1)
                parsed_result['annex_title'] = header_match.group(2).strip()
                logger.info(f"   📋 Annex 제목: [별표{parsed_result['annex_no']}] {parsed_result['annex_title']}")
            
            # 관련 조문 파싱
            rel_match = re.search(r'<(제\d+조[^>]*)관련>', annex_text)
            if rel_match:
                parsed_result['related_article'] = rel_match.group(1).strip()
                logger.info(f"   🔗 관련 조문: {parsed_result['related_article']}")
        else:
            logger.warning("   ⚠️ Fallback: [별표] 패턴을 찾을 수 없음")
    
    def _apply_annex_extraction(self, cleaned_text: str, parsed_result: dict):
        """
        ✅ Phase 0.8.2 신규: 본문+Annex 혼합 문서에서 Annex 추출
        
        조문은 이미 파싱됨, Annex만 추가로 추출
        """
        # [별표 N] 패턴 찾기
        pattern = r'(\[별표\s*\d+\][\s\S]+)'
        match = re.search(pattern, cleaned_text)
        
        if match:
            annex_text = match.group(1).strip()
            parsed_result['annex_content'] = annex_text
            
            logger.info(f"   ✅ 혼합 문서 Annex 추출: {len(annex_text)}자")
            
            # 헤더 파싱
            header_match = re.search(r'\[별표\s*(\d+)\]\s*([^\n<]+)', annex_text)
            if header_match:
                parsed_result['annex_no'] = header_match.group(1)
                parsed_result['annex_title'] = header_match.group(2).strip()
                logger.info(f"   📋 Annex 제목: [별표{parsed_result['annex_no']}] {parsed_result['annex_title']}")
            
            # 관련 조문 파싱
            rel_match = re.search(r'<(제\d+조[^>]*)관련>', annex_text)
            if rel_match:
                parsed_result['related_article'] = rel_match.group(1).strip()
                logger.info(f"   🔗 관련 조문: {parsed_result['related_article']}")
    
    def to_chunks(self, parsed_result: dict) -> list:
        """
        파싱 결과 → RAG 청크 변환
        
        ✅ Phase 0.8.2: 본문 조문 + Annex 동시 청크 생성
        """
        chunks = []
        
        # Title
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
        
        # 개정이력
        if parsed_result.get('amendment_history'):
            for i, amendment in enumerate(parsed_result['amendment_history']):
                chunks.append({
                    'content': amendment,
                    'metadata': {
                        'type': 'amendment_history',
                        'boundary': 'header',
                        'title': '개정 이력',
                        'char_count': len(amendment),
                        'section_order': -2 - i
                    }
                })
        
        # 기본정신
        if parsed_result.get('basic_spirit'):
            chunks.append({
                'content': parsed_result['basic_spirit'],
                'metadata': {
                    'type': 'basic_spirit',
                    'boundary': 'header',
                    'title': '기본정신',
                    'char_count': len(parsed_result['basic_spirit']),
                    'section_order': -1
                }
            })
        
        # 장
        for chapter in parsed_result.get('chapters', []):
            chunks.append({
                'content': f"{chapter.number} {chapter.title}",
                'metadata': {
                    'type': 'chapter',
                    'boundary': 'chapter',
                    'chapter_number': chapter.number,
                    'chapter_title': chapter.title,
                    'char_count': len(chapter.number) + len(chapter.title),
                    'section_order': chapter.section_order
                }
            })
        
        # ✅ Phase 0.8.2: 조문 청크 생성 (핵심!)
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
        
        # ✅ Phase 0.8: Annex 서브청킹
        if parsed_result.get('annex_content') and ANNEX_SUBCHUNKING_AVAILABLE:
            logger.info("✅ Phase 0.8: Annex 서브청킹 시작")
            
            subchunker = AnnexSubChunker()
            annex_text = parsed_result['annex_content']
            
            try:
                # 서브청크 생성
                sub_chunks = subchunker.chunk(annex_text)
                
                # 검증
                validation = validate_subchunks(sub_chunks, len(annex_text))
                
                if validation['is_valid']:
                    logger.info(f"✅ Annex 서브청킹 성공: {validation['chunk_count']}개")
                    logger.info(f"   📊 손실률: {validation['loss_rate']:.2%}")
                    logger.info(f"   📊 타입: {validation['type_counts']}")
                    
                    # 서브청크 → 표준 청크 포맷 변환
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
                    raise ValueError("Annex 서브청킹 검증 실패")
                    
            except Exception as e:
                logger.warning(f"⚠️ Annex 서브청킹 실패: {e} - Fallback")
                # Fallback: 기존 단일 청크
                chunks.append({
                    'content': annex_text,
                    'metadata': {
                        'type': 'annex',
                        'boundary': 'annex',
                        'title': parsed_result.get('annex_title', ''),
                        'char_count': len(annex_text),
                        'section_order': 0
                    }
                })
        
        elif parsed_result.get('annex_content'):
            # Annex 서브청킹 비활성화 - 기존 방식
            chunks.append({
                'content': parsed_result['annex_content'],
                'metadata': {
                    'type': 'annex',
                    'boundary': 'annex',
                    'title': parsed_result.get('annex_title', ''),
                    'char_count': len(parsed_result['annex_content']),
                    'section_order': 0
                }
            })
        
        logger.info(f"✅ 청크 변환 완료 (Phase 0.8.2): {len(chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunks:
            ctype = chunk['metadata']['type']
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return chunks
    
    def to_markdown(self, parsed_result: dict) -> str:
        """
        파싱 결과 → Markdown 변환
        
        ✅ Phase 0.8.2: 본문 조문 + Annex 모두 포함
        """
        
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
            # 새 장이면 추가
            if article.chapter_number != current_chapter:
                current_chapter = article.chapter_number
                for chapter in parsed_result.get('chapters', []):
                    if chapter.number == current_chapter:
                        lines.append(f"## {chapter.number} {chapter.title}")
                        lines.append("")
                        break
            
            # 조문
            lines.append(f"### {article.number}({article.title})")
            lines.append("")
            lines.append(article.body)
            lines.append("")
        
        # ✅ Phase 0.8: Annex 섹션
        if parsed_result.get('annex_content'):
            annex_no = parsed_result.get('annex_no', '')
            annex_title = parsed_result.get('annex_title', '')
            related = parsed_result.get('related_article', '')
            
            # 명확한 섹션 헤더
            if annex_no and annex_title:
                lines.append(f"## [별표{annex_no}] {annex_title}")
            else:
                lines.append("## 별표")
            lines.append("")
            
            # 관련 조문
            if related:
                lines.append(f"**관련 조문**: {related}")
                lines.append("")
            
            # 표 영역 시작 표시
            lines.append("---")
            lines.append("")
            
            # Annex 본문
            lines.append(parsed_result['annex_content'])
            lines.append("")
            
            # 표 영역 종료 표시
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)


# 하위 호환성을 위한 Alias
parse_pdf_text = LawParser.parse
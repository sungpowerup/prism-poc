"""
core/law_parser.py - PRISM Phase 0.8.7 Polishing
출력물 읽기 품질 개선 (파싱 로직 유지)

Phase 0.8.7 핵심 수정:
- ✅ Article 본문 끝의 장 헤더 제거 (제2장채용 중복 제거)
- ✅ Annex 텍스트 노이즈 문자 제거 (□■ 등)
- ✅ QA Summary 포맷 개선 (사람 가독성)

Author: 마창수산팀
Date: 2025-11-20
Version: Phase 0.8.7 Polishing
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
    Phase 0.8.7 LawParser Polishing
    
    핵심 수정:
    - 파싱 로직 유지
    - 출력물 읽기 품질 개선
    """
    
    # ✅ Phase 0.8.6: 페이지 아티팩트 패턴
    PAGE_ARTIFACT_PATTERNS = [
        re.compile(r'\n인사규정\n\d{3}-\d{1,2}', re.MULTILINE),
        re.compile(r'인사규정\s*\d{3}-\d{1,2}', re.IGNORECASE),
        re.compile(r'\b\d{3}-\d{1,2}\b'),
    ]
    
    # ✅ Phase 0.8.7: Article 본문 끝의 장 헤더 패턴
    CHAPTER_TAIL_PATTERN = re.compile(
        r'\n제(?P<num>\d+)장\s*(?P<title>[^\n]*)\s*$'
    )
    
    # ✅ Phase 0.8.7: Annex 노이즈 문자 (PDF에서 온 박스/라인 아티팩트)
    ANNEX_NOISE_CHARS = ''.join([
        '□', '■', '○', '●', '◇', '◆',  # 박스/도형
        '━', '─', '═', '┃', '│',  # 라인
        '', '', '',  # Private Use Area
    ])
    ANNEX_NOISE_PATTERN = re.compile(f'[{re.escape(ANNEX_NOISE_CHARS)}]')
    
    # 개정이력 패턴
    AMENDMENT_PATTERN = re.compile(
        r'(제\d+차\s*개정\s*\d{4}\.\d{1,2}\.\d{1,2})',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        if not TREE_BUILDER_AVAILABLE:
            raise ImportError("TreeBuilder is required but not available")
        
        self.tree_builder = TreeBuilder()
        logger.info("✅ LawParser 초기화 완료 (Phase 0.8.7 Polishing)")
    
    def _clean_page_artifacts(self, text: str) -> str:
        """
        페이지 아티팩트 완전 제거
        """
        if not text:
            return text
        
        result = text
        removed_count = 0
        
        for pattern in self.PAGE_ARTIFACT_PATTERNS:
            matches = pattern.findall(result)
            if matches:
                removed_count += len(matches)
                result = pattern.sub('', result)
        
        result = re.sub(r' {2,}', ' ', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        if removed_count > 0:
            logger.debug(f"   🧹 페이지 아티팩트 {removed_count}개 제거")
        
        return result.strip()
    
    def _clean_article_body(self, body: str) -> str:
        """
        ✅ Phase 0.8.7: Article 본문 정리
        
        1. 본문 끝에 붙은 장 헤더 제거 (제2장채용 등)
        2. 페이지 아티팩트 제거
        """
        if not body:
            return body
        
        # 1. 본문 끝의 장 헤더 제거
        body = self.CHAPTER_TAIL_PATTERN.sub('', body)
        
        # 2. 페이지 아티팩트 제거
        body = self._clean_page_artifacts(body)
        
        return body.strip()
    
    def _clean_annex_text(self, text: str) -> str:
        """
        ✅ Phase 0.8.7: Annex 텍스트 노이즈 제거
        
        1. 박스/라인 문자 제거 (□■━─ 등)
        2. 연속 줄바꿈 정리
        3. 페이지 아티팩트 제거
        """
        if not text:
            return text
        
        # 1. 노이즈 문자 제거
        result = self.ANNEX_NOISE_PATTERN.sub('', text)
        
        # 2. 연속 줄바꿈 정리
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # 3. 연속 공백 정리
        result = re.sub(r' {2,}', ' ', result)
        
        # 4. 페이지 아티팩트 제거
        result = self._clean_page_artifacts(result)
        
        return result.strip()
    
    def _extract_amendment_history(self, text: str) -> List[str]:
        """개정이력 추출"""
        amendments = []
        header_text = text[:2000] if len(text) > 2000 else text
        
        matches = self.AMENDMENT_PATTERN.findall(header_text)
        if matches:
            amendments = list(set(matches))
            amendments.sort(reverse=True)
        
        return amendments
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = True
    ) -> Dict[str, Any]:
        """PDF 텍스트 파싱 (메인 메서드)"""
        logger.info(f"📜 LawParser.parse() 시작: {document_title}")
        
        cleaned_text = pdf_text
        if normalize_linebreaks:
            cleaned_text = cleaned_text.replace('\r\n', '\n')
        
        amendment_history = self._extract_amendment_history(cleaned_text)
        
        tree_result = self.tree_builder.build(
            markdown=cleaned_text,
            document_title=document_title,
            enacted_date=None
        )
        
        parsed_result = self._convert_tree_to_result(tree_result, document_title)
        
        if amendment_history:
            parsed_result['amendment_history'] = amendment_history
            logger.info(f"   📋 개정이력: {len(amendment_history)}건 추출")
        
        has_articles = parsed_result.get('total_articles', 0) > 0
        has_annex_pattern = '[별표' in cleaned_text
        
        if has_articles:
            logger.info(f"   📋 본문 조문: {parsed_result['total_articles']}개")
            
            if has_annex_pattern and not parsed_result.get('annex_content'):
                logger.info("   📋 혼합 문서 - 본문 + Annex 동시 처리")
                self._apply_annex_extraction(cleaned_text, parsed_result)
        else:
            if len(cleaned_text) > 500:
                logger.warning("🔄 Annex-only 문서 감지 - Fallback Annex 파서 가동")
                self._apply_annex_fallback(cleaned_text, parsed_result)
        
        logger.info(f"✅ LawParser.parse() 완료:")
        logger.info(f"   - 장: {parsed_result['total_chapters']}개")
        logger.info(f"   - 조문: {parsed_result['total_articles']}개")
        if parsed_result.get('amendment_history'):
            logger.info(f"   - 개정이력: {len(parsed_result['amendment_history'])}건")
        if parsed_result.get('annex_content'):
            logger.info(f"   - Annex: {len(parsed_result['annex_content'])}자")
        
        return parsed_result
    
    def _convert_tree_to_result(
        self, 
        tree_result: Dict[str, Any],
        document_title: str
    ) -> Dict[str, Any]:
        """TreeBuilder 결과 → LawParser 표준 포맷 변환"""
        
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
            node_type = node.get('level', node.get('type', ''))
            
            if node_type == 'chapter':
                chapter = Chapter(
                    number=node.get('chapter_number', node.get('chapter', node.get('number', ''))),
                    title=node.get('chapter_title', node.get('title', '')),
                    section_order=section_order
                )
                chapters.append(chapter)
                current_chapter = f"{chapter.number} {chapter.title}".strip()
                section_order += 1
                logger.debug(f"      장 변환: {chapter.number} {chapter.title}")
            
            elif node_type == 'article':
                article_no = node.get('article_no', node.get('article_number', node.get('number', '')))
                article_title = node.get('article_title', node.get('title', ''))
                article_body = node.get('content', node.get('body', ''))
                
                chapter_info = node.get('chapter', current_chapter)
                if not chapter_info and current_chapter:
                    chapter_info = current_chapter
                
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
                    chapter_number=chapter_info,
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
        """
        파싱 결과 → RAG 청크 변환
        
        ✅ Phase 0.8.7: Article 본문 정리 적용
        """
        
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
        
        # 개정이력 청크
        if parsed_result.get('amendment_history'):
            history_content = "\n".join(parsed_result['amendment_history'])
            chunks.append({
                'content': history_content,
                'metadata': {
                    'type': 'amendment_history',
                    'boundary': 'amendment_history',
                    'char_count': len(history_content),
                    'amendment_count': len(parsed_result['amendment_history']),
                    'section_order': -2
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
        
        # 장(Chapter) 청크 synthesize
        seen_chapters = set()
        chapter_order = 0
        
        for article in parsed_result.get('articles', []):
            chapter_info = article.chapter_number
            if chapter_info and chapter_info not in seen_chapters:
                seen_chapters.add(chapter_info)
                
                chapter_match = re.match(r'(제\d+장)\s*(.+)?', chapter_info)
                if chapter_match:
                    chapter_num = chapter_match.group(1)
                    chapter_title = chapter_match.group(2) or ""
                else:
                    chapter_num = chapter_info
                    chapter_title = ""
                
                content = f"{chapter_num} {chapter_title}".strip()
                chunks.append({
                    'content': content,
                    'metadata': {
                        'type': 'chapter',
                        'boundary': 'chapter',
                        'chapter_number': chapter_num,
                        'chapter_title': chapter_title,
                        'char_count': len(content),
                        'section_order': chapter_order
                    }
                })
                chapter_order += 1
        
        # 조문 (Phase 0.8.7: 본문 정리 적용)
        for article in parsed_result.get('articles', []):
            # ✅ Phase 0.8.7: 본문 정리 (장 꼬리 + 페이지 아티팩트)
            cleaned_body = self._clean_article_body(article.body)
            
            content = f"{article.number}({article.title})\n{cleaned_body}"
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
            # ✅ Phase 0.8.7: Annex 노이즈 제거
            annex_text = self._clean_annex_text(parsed_result['annex_content'])
            
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
            # ✅ Phase 0.8.7: Annex 노이즈 제거
            cleaned_annex = self._clean_annex_text(parsed_result['annex_content'])
            chunks.append({
                'content': cleaned_annex,
                'metadata': {
                    'type': 'annex',
                    'boundary': 'annex',
                    'char_count': len(cleaned_annex),
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
        """
        파싱 결과 → Markdown 변환
        
        ✅ Phase 0.8.7: 본문/Annex 정리 적용
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
        seen_chapters = set()
        
        for article in parsed_result.get('articles', []):
            # 장이 바뀌면 장 헤더 추가
            if article.chapter_number and article.chapter_number != current_chapter:
                current_chapter = article.chapter_number
                
                if current_chapter not in seen_chapters:
                    seen_chapters.add(current_chapter)
                    lines.append(f"## {current_chapter}")
                    lines.append("")
            
            # ✅ Phase 0.8.7: 조문 본문 정리
            cleaned_body = self._clean_article_body(article.body)
            
            lines.append(f"### {article.number}({article.title})")
            lines.append("")
            lines.append(cleaned_body)
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
            
            # ✅ Phase 0.8.7: Annex 노이즈 제거
            cleaned_annex = self._clean_annex_text(parsed_result['annex_content'])
            lines.append(cleaned_annex)
            lines.append("---")
        
        return "\n".join(lines)


# 하위 호환성
parse_pdf_text = LawParser.parse
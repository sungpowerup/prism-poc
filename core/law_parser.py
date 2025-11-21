# law_parser.py - Phase 0.9.2
# 
# Phase 0.9.2 수정사항:
# 1. ✅ Chapter 위치 재배치 (Critical Fix)
#    - Chapter 청크를 해당 장의 첫 article 앞에 배치
#    - engine.md, chunks.json, review.md 구조 일치
# 2. ✅ 제5조 1항 번호 복구 (Data Loss Fix)
#    - "."직위"란1명 → 1. "직위"란 1명
# 3. ✅ Article 본문 정리 (Phase 0.8.7 유지)

"""
law_parser.py - PRISM LawParser

법률/규정 문서 파싱

Author: 마창수산팀  
Date: 2025-11-20
Version: Phase 0.9.2
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Annex SubChunker Import (Phase 0.8)
try:
    from core.annex_subchunker import AnnexSubChunker, validate_subchunks
    ANNEX_SUBCHUNKING_AVAILABLE = True
    logger.info("✅ AnnexSubChunker 로드 성공 (Phase 0.8)")
except ImportError:
    ANNEX_SUBCHUNKING_AVAILABLE = False
    logger.warning("⚠️ AnnexSubChunker 미설치 - Annex 단일 청크 모드")


@dataclass
class Article:
    """조문 데이터 클래스"""
    number: str
    title: str
    body: str
    chapter_number: str
    section_order: int


@dataclass
class Chapter:
    """장 데이터 클래스"""
    number: str
    title: str
    section_order: int


class LawParser:
    """
    법률/규정 문서 파서
    
    Phase 0.9.2:
    - ✅ Chapter 위치 재배치 (GPT Critical Fix)
    - ✅ 제5조 1항 번호 복구
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ LawParser v0.9.2 초기화 (Chapter Position Fix)")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 텍스트 파싱
        """
        logger.info(f"📜 LawParser 파싱 시작: {document_title}")
        
        # 1. 텍스트 전처리
        cleaned_text = pdf_text
        
        if clean_artifacts:
            cleaned_text = self._clean_page_artifacts(cleaned_text)
            logger.info("   ✅ 페이지 아티팩트 제거 완료")
        
        if normalize_linebreaks:
            cleaned_text = self._normalize_linebreaks(cleaned_text)
            logger.info("   ✅ 개행 정규화 완료")
        
        # 2. 문서 타입 판별
        has_articles = bool(re.search(r'제\d+조', cleaned_text))
        has_annex_only = bool(re.search(r'\[별표', cleaned_text))
        
        if has_articles:
            logger.info("   📋 문서 타입: 법령/규정 (조문 포함)")
            return self._parse_legal_document(cleaned_text, document_title)
        elif has_annex_only:
            logger.info("   📋 문서 타입: Annex 전용")
            return self._parse_annex_only_document(cleaned_text, document_title)
        else:
            logger.warning("   ⚠️ 알 수 없는 문서 타입 - 기본 처리")
            return self._create_empty_result(document_title, cleaned_text)
    
    def _clean_page_artifacts(self, text: str) -> str:
        """페이지 아티팩트 제거 (Phase 0.8.6)"""
        
        # 패턴: "인사규정 402-2" 스타일
        artifact_pattern = r'^[가-힣]{2,10}\s*\d{1,5}-\d{1,3}\s*$'
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if re.match(artifact_pattern, line_stripped):
                logger.debug(f"      제거: {line_stripped}")
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _normalize_linebreaks(self, text: str) -> str:
        """개행 정규화"""
        
        # 3줄 이상 연속 개행 → 2줄로
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 문장 끝 + 단일 개행 → 유지
        # (조문 본문 내 자연스러운 개행 보존)
        
        return text
    
    def _parse_legal_document(self, cleaned_text: str, document_title: str) -> Dict[str, Any]:
        """법령/규정 문서 파싱"""
        
        # 개정이력 추출 (Phase 0.8.6)
        amendment_history = self._extract_amendment_history(cleaned_text)
        logger.info(f"   ✅ 개정이력: {len(amendment_history)}건")
        
        # TreeBuilder 결과를 변환
        from core.tree_builder import TreeBuilder
        
        tree_builder = TreeBuilder()
        tree_doc = tree_builder.build(
            markdown=cleaned_text,
            document_title=document_title
        )
        
        # Tree → Article 변환
        chapters = []
        articles = []
        
        tree_nodes = tree_doc['document']['tree']
        
        # Chapter 추출
        seen_chapters = {}
        for node in tree_nodes:
            if node.get('level') == 'article':
                chapter_info = node.get('chapter', '')
                if chapter_info and chapter_info not in seen_chapters:
                    chapter_match = re.match(r'(제\d+장)\s*(.+)?', chapter_info)
                    if chapter_match:
                        chapter_num = chapter_match.group(1)
                        chapter_title = chapter_match.group(2) or ""
                        
                        chapters.append(Chapter(
                            number=chapter_num,
                            title=chapter_title.strip(),
                            section_order=len(chapters)
                        ))
                        
                        seen_chapters[chapter_info] = chapter_num
        
        # Article 추출
        for node in tree_nodes:
            if node.get('level') == 'article':
                article_no = node.get('article_no', '')
                article_title = node.get('article_title', '')
                article_body = node.get('content', '')
                chapter_info = node.get('chapter', '')
                
                # Chapter number 매핑
                chapter_number = seen_chapters.get(chapter_info, '')
                
                articles.append(Article(
                    number=article_no,
                    title=article_title,
                    body=article_body,
                    chapter_number=chapter_number,
                    section_order=len(articles)
                ))
        
        logger.info(f"   ✅ 조문 파싱: {len(articles)}개")
        logger.info(f"   ✅ 장 파싱: {len(chapters)}개")
        
        # Annex 추출
        parsed_result = {
            'document_title': document_title,
            'chapters': chapters,
            'articles': articles,
            'basic_spirit': '',
            'amendment_history': amendment_history,
            'annex_content': None,
            'annex_no': None,
            'annex_title': None,
            'related_article': None,
            'annex_tables': [],
            'total_chapters': len(chapters),
            'total_articles': len(articles)
        }
        
        self._apply_annex_extraction(cleaned_text, parsed_result)
        
        return parsed_result
    
    def _extract_amendment_history(self, text: str) -> List[str]:
        """개정이력 추출 (Phase 0.8.6)"""
        
        history = []
        
        # 패턴: [전부개정 2017.7.14.], [일부개정 2025.2.1.] 등
        pattern = r'\[(전부개정|일부개정|제정|개정)\s+(\d{4}\.\d{1,2}\.\d{1,2}\.?)\]'
        
        for match in re.finditer(pattern, text):
            amendment_type = match.group(1)
            amendment_date = match.group(2)
            
            # 날짜 정규화 (마지막 마침표 제거)
            amendment_date = amendment_date.rstrip('.')
            
            history_item = f"{amendment_type} {amendment_date}"
            
            if history_item not in history:
                history.append(history_item)
        
        return sorted(history, reverse=True)
    
    def _parse_annex_only_document(self, cleaned_text: str, document_title: str) -> Dict[str, Any]:
        """Annex 전용 문서 파싱"""
        
        parsed_result = {
            'document_title': document_title,
            'chapters': [],
            'articles': [],
            'basic_spirit': '',
            'amendment_history': [],
            'annex_content': None,
            'annex_no': None,
            'annex_title': None,
            'related_article': None,
            'annex_tables': [],
            'total_chapters': 0,
            'total_articles': 0
        }
        
        self._apply_annex_fallback(cleaned_text, parsed_result)
        
        return parsed_result
    
    def _create_empty_result(self, document_title: str, text: str) -> Dict[str, Any]:
        """빈 결과 생성"""
        
        return {
            'document_title': document_title,
            'chapters': [],
            'articles': [],
            'basic_spirit': text[:500],
            'amendment_history': [],
            'annex_content': None,
            'annex_no': None,
            'annex_title': None,
            'related_article': None,
            'annex_tables': [],
            'total_chapters': 0,
            'total_articles': 0
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
    
    def _clean_article_body(self, body: str) -> str:
        """
        조문 본문 정리 (Phase 0.8.7 + 0.9.2)
        
        Phase 0.9.2 추가:
        - ✅ 제5조 1항 번호 복구: "."직위"란 → 1. "직위"란
        """
        
        # 1. 장 꼬리 제거 (Phase 0.8.7)
        chapter_pattern = r'제\d+장\s+[가-힣\s]+$'
        body = re.sub(chapter_pattern, '', body, flags=re.MULTILINE)
        
        # 2. Phase 0.9.2: 항 번호 복구
        # 패턴: ."단어"란 → 1. "단어"란
        # 매칭: 줄 시작 + . + " + 한글 + "
        body = re.sub(
            r'^\.(\s*"[가-힣]+"\s*란)',
            r'1.\1',
            body,
            flags=re.MULTILINE
        )
        
        # 3. 연속 공백 정리
        body = re.sub(r'[ \t]+', ' ', body)
        
        # 4. 연속 개행 정리 (3줄 이상 → 2줄)
        body = re.sub(r'\n{3,}', '\n\n', body)
        
        return body.strip()
    
    def _clean_annex_text(self, text: str) -> str:
        """
        Annex 텍스트 노이즈 제거 (Phase 0.8.7)
        """
        
        # Private Use Area 문자 제거
        text = re.sub(r'[\uF000-\uF8FF]', '', text)
        
        # Box drawing characters
        box_chars = '─━│┃┌┐└┘├┤┬┴┼╋═║╔╗╚╝╠╣╦╩╬■□▪▫'
        for char in box_chars:
            text = text.replace(char, '')
        
        # 연속 공백 정리
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 연속 개행 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def to_chunks(self, parsed_result: dict) -> list:
        """
        파싱 결과 → RAG 청크 변환
        
        ✅ Phase 0.9.2: Chapter 위치 재배치 (GPT Critical Fix)
        - Chapter 청크를 해당 장의 첫 article 앞에 insert
        - engine/chunks/review 구조 일치
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
        
        # ✅ Phase 0.9.2: 조문 먼저 추가, Chapter 나중에 insert
        article_chunks = []
        
        for article in parsed_result.get('articles', []):
            # Phase 0.9.2: 본문 정리 (항 번호 복구 포함)
            cleaned_body = self._clean_article_body(article.body)
            
            content = f"{article.number}({article.title})\n{cleaned_body}"
            article_chunks.append({
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
        
        chunks.extend(article_chunks)
        
        # ✅ Phase 0.9.2 Critical Fix: Chapter 위치 재배치
        # Strategy: 각 chapter의 첫 article index를 찾아서 그 앞에 insert
        
        if parsed_result.get('chapters'):
            chapter_positions = {}  # {chapter_number: first_article_index}
            
            # 1. 각 chapter의 첫 article index 찾기
            for idx, chunk in enumerate(chunks):
                if chunk['metadata']['type'] == 'article':
                    chapter_num = chunk['metadata'].get('chapter_number', '')
                    if chapter_num and chapter_num not in chapter_positions:
                        # title/amendment_history/basic_spirit 이후의 절대 index
                        chapter_positions[chapter_num] = idx
            
            # 2. Chapter 청크를 역순으로 insert (index 변화 방지)
            chapters_sorted = sorted(
                parsed_result['chapters'],
                key=lambda ch: chapter_positions.get(ch.number, 999),
                reverse=True
            )
            
            for chapter in chapters_sorted:
                chapter_num = chapter.number
                insert_idx = chapter_positions.get(chapter_num)
                
                if insert_idx is not None:
                    content = f"{chapter_num} {chapter.title}".strip()
                    chapter_chunk = {
                        'content': content,
                        'metadata': {
                            'type': 'chapter',
                            'boundary': 'chapter',
                            'chapter_number': chapter_num,
                            'chapter_title': chapter.title,
                            'char_count': len(content),
                            'section_order': chapter.section_order
                        }
                    }
                    
                    # Insert at correct position
                    chunks.insert(insert_idx, chapter_chunk)
                    logger.debug(f"      Chapter '{chapter_num}' inserted at index {insert_idx}")
        
        # Annex 서브청킹
        if parsed_result.get('annex_content') and ANNEX_SUBCHUNKING_AVAILABLE:
            logger.info("✅ Phase 0.8: Annex 서브청킹 시작")
            
            subchunker = AnnexSubChunker()
            # Phase 0.8.7: Annex 노이즈 제거
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
            # Phase 0.8.7: Annex 노이즈 제거
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
        
        Phase 0.9.2: 본문/Annex 정리 적용
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
        
        # 장/조문 (자연스러운 문서 흐름)
        current_chapter = ""
        
        for article in parsed_result.get('articles', []):
            # 장 변경 시 장 헤더 출력
            if article.chapter_number and article.chapter_number != current_chapter:
                current_chapter = article.chapter_number
                
                # Chapter 객체 찾기
                for ch in parsed_result.get('chapters', []):
                    if ch.number == current_chapter:
                        lines.append(f"## {ch.number} {ch.title}")
                        lines.append("")
                        break
            
            # 조문
            cleaned_body = self._clean_article_body(article.body)
            lines.append(f"### {article.number}({article.title})")
            lines.append("")
            lines.append(cleaned_body)
            lines.append("")
        
        # Annex
        if parsed_result.get('annex_content'):
            cleaned_annex = self._clean_annex_text(parsed_result['annex_content'])
            lines.append("## 별표")
            lines.append("")
            lines.append(cleaned_annex)
            lines.append("")
        
        return '\n'.join(lines)
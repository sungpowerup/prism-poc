"""
law_parser.py - LawMode 조문 파서
Phase 0.7.5 Annex Fallback (긴급 핫픽스)

✅ Phase 0.7.5 핫픽스:
1. Annex Fallback: 조문 0개 + 텍스트 500자+ → annex 청크 생성
2. [별표 n], <제n조 관련> 헤더 인식
3. 표/부록 텍스트 손실 방지

🎯 목표:
- 법조문 페이지: 기존 로직 유지
- 별표/표 페이지: 최소한 텍스트 복구 (32자 → 2,700자+)
- RAG 검색 가능하도록 키워드 보존

Author: 박준호 (AI/ML Lead) + GPT + CEO 피드백
Date: 2025-11-16
Version: Phase 0.7.5 Annex Fallback
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """장 데이터 클래스"""
    number: str
    title: str
    start_pos: int
    section_order: int


@dataclass
class Article:
    """조문 데이터 클래스"""
    number: str
    title: Optional[str]
    body: str
    start_pos: int
    end_pos: int
    chapter_number: Optional[str] = None
    section_order: int = 0
    article_type: str = 'article'


class LawParser:
    """
    규정/법령 전용 파서 (Phase 0.7.5 Annex Fallback)
    
    ✅ Phase 0.7.5 핫픽스:
    - 조문 0개 + 텍스트 충분 → Annex 모드 자동 전환
    - [별표 n], <제n조 관련> 헤더 인식
    - 표/부록 텍스트 손실 방지
    """
    
    # 기본정신 패턴
    BASIC_SPIRIT_PATTERN = re.compile(
        r'기\s*본\s*정\s*신',
        re.MULTILINE | re.IGNORECASE
    )
    
    # 조문 헤더 패턴
    ARTICLE_HEADER_PATTERN = re.compile(
        r'제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*\(([^)]+)\)',
        re.MULTILINE
    )
    
    # 장 패턴
    CHAPTER_PATTERN = re.compile(
        r'(제\s*\d+\s*장)\s*([^\n제]+)',
        re.MULTILINE
    )
    
    # 타이틀 패턴
    TITLE_PATTERN = re.compile(
        r'^([가-힣]{2,10}규정|[가-힣]{2,10}내규|[가-힣]{2,10}정관)',
        re.MULTILINE
    )
    
    # 개정일 패턴
    AMENDMENT_PATTERN = re.compile(
        r'(제\d+차\s*)?개정\s*\d{4}\.\d{1,2}\.\d{1,2}\.?',
        re.MULTILINE
    )
    
    # ✅ Phase 0.7.5: 별표 헤더 패턴
    ANNEX_HEADER_PATTERN = re.compile(
        r'\[별표\s*(\d+)\]\s*([^\n<]+)',
        re.MULTILINE
    )
    
    # ✅ Phase 0.7.5: 관련 조문 패턴
    RELATED_ARTICLE_PATTERN = re.compile(
        r'<\s*제(\d+)조(?:제(\d+)항)?\s*관련\s*>',
        re.MULTILINE
    )
    
    # 줄바꿈 정리 패턴
    SAFE_NEWLINE_PATTERN = re.compile(
        r'(?<=[가-힣0-9])(?<![.?!])[\r]?\n(?=[가-힣0-9])',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info("✅ LawParser 초기화 (Phase 0.7.5 Annex Fallback)")
        logger.info("   📌 법조문 모드: 기존 로직 유지")
        logger.info("   📌 Annex 모드: 별표/표 페이지 자동 복구")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        enacted_date: Optional[str] = None,
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = False
    ) -> Dict[str, Any]:
        """
        PDF 텍스트를 파싱하여 조문 구조 추출
        
        ✅ Phase 0.7.5: Annex Fallback 추가
        - 조문 0개 + 텍스트 500자+ → annex 모드 자동 전환
        
        Args:
            pdf_text: PDF에서 추출한 원본 텍스트
            document_title: 문서 제목
            enacted_date: 제정일
            clean_artifacts: 페이지 아티팩트 제거 여부
            normalize_linebreaks: 줄바꿈 정리 여부
        
        Returns:
            {
                'document_title': str,
                'enacted_date': str,
                'amendment_history': str,
                'basic_spirit': str,
                'chapters': List[Chapter],
                'articles': List[Article],
                'total_articles': int,
                'total_chapters': int,
                'is_annex_mode': bool,  # ✅ Phase 0.7.5
                'annex_content': str     # ✅ Phase 0.7.5
            }
        """
        logger.info(f"📜 LawParser Phase 0.7.5 시작: {document_title}")
        logger.info(f"   📄 입력 텍스트: {len(pdf_text)}자")
        
        original_text = pdf_text
        
        # 페이지 아티팩트 제거
        if clean_artifacts:
            try:
                from .page_cleaner import clean_page_artifacts
                pdf_text = clean_page_artifacts(pdf_text)
                logger.info(f"   🧹 아티팩트 제거 후: {len(pdf_text)}자")
            except ImportError:
                logger.warning("   ⚠️ PageCleaner 미설치 - 건너뜀")
        
        cleaned_text = pdf_text
        
        # 줄바꿈 정리
        if normalize_linebreaks:
            original_len = len(pdf_text)
            pdf_text = self._normalize_linebreaks(pdf_text)
            logger.info(f"   ✂️ 줄바꿈 정리: {original_len}자 → {len(pdf_text)}자")
        
        # 장/조문 전처리
        pdf_text = self._preprocess_for_chapter_parsing(pdf_text)
        
        # Front Matter 추출
        title, amendment_history, pdf_text = self._extract_front_matter(pdf_text, document_title)
        
        # 1. 기본정신 추출
        basic_spirit = self._extract_basic_spirit(pdf_text)
        logger.info(f"   ✅ 기본정신: {len(basic_spirit)}자")
        
        # 2. 장 추출
        chapters = self._extract_chapters(pdf_text)
        logger.info(f"   ✅ 장: {len(chapters)}개")
        
        # 3. 조문 추출
        articles = self._extract_articles_from_text(pdf_text)
        logger.info(f"   ✅ 조문: {len(articles)}개")
        
        # ✅ Phase 0.7.5: Annex Fallback 체크
        is_annex_mode = False
        annex_content = ""
        
        if len(articles) == 0 and len(cleaned_text) > 500:
            logger.warning(f"   🔄 Annex Fallback 활성화!")
            logger.warning(f"      조건: 조문 0개 + 텍스트 {len(cleaned_text)}자")
            
            is_annex_mode = True
            annex_content = self._extract_annex_content(cleaned_text)
            
            logger.info(f"   ✅ Annex 콘텐츠 추출: {len(annex_content)}자")
        
        # 4. 조문에 chapter_number 할당
        self._assign_chapters_to_articles(chapters, articles)
        
        # 5. section_order 부여
        self._assign_section_order(chapters, articles)
        
        # 6. 기본정신/조문에서 장 헤더 제거
        basic_spirit = self._remove_chapter_headers(basic_spirit)
        for article in articles:
            article.body = self._remove_chapter_headers(article.body)
        
        result = {
            'document_title': title,
            'enacted_date': enacted_date or '',
            'amendment_history': amendment_history,
            'basic_spirit': basic_spirit,
            'chapters': chapters,
            'articles': articles,
            'total_articles': len(articles),
            'total_chapters': len(chapters),
            'is_annex_mode': is_annex_mode,      # ✅ Phase 0.7.5
            'annex_content': annex_content        # ✅ Phase 0.7.5
        }
        
        if is_annex_mode:
            logger.info(f"✅ LawParser Phase 0.7.5 완료 (Annex 모드)")
            logger.info(f"   📊 별표/부록 콘텐츠: {len(annex_content)}자")
        else:
            logger.info(f"✅ LawParser Phase 0.7.5 완료 (법조문 모드)")
            logger.info(f"   📊 {len(chapters)}개 장, {len(articles)}개 조문")
        
        return result
    
    def _extract_annex_content(self, text: str) -> str:
        """
        ✅ Phase 0.7.5: Annex 콘텐츠 추출
        
        [별표 n] ... <제n조 관련> ... 표 본문
        
        Args:
            text: 정제된 텍스트
        
        Returns:
            Annex 콘텐츠 (헤더 + 본문)
        """
        logger.info("   🔍 Annex 헤더 감지 중...")
        
        # 별표 헤더 찾기
        annex_match = self.ANNEX_HEADER_PATTERN.search(text)
        if annex_match:
            annex_no = annex_match.group(1)
            annex_title = annex_match.group(2).strip()
            logger.info(f"      ✅ [별표 {annex_no}] {annex_title}")
        
        # 관련 조문 찾기
        related_match = self.RELATED_ARTICLE_PATTERN.search(text)
        if related_match:
            article_no = related_match.group(1)
            paragraph_no = related_match.group(2) or ""
            related_article = f"제{article_no}조" + (f"제{paragraph_no}항" if paragraph_no else "")
            logger.info(f"      ✅ 관련 조문: {related_article}")
        
        # 전체 텍스트를 annex_content로 반환
        # (나중에 더 정밀하게 분리 가능)
        return text.strip()
    
    def _normalize_linebreaks(self, text: str) -> str:
        """줄바꿈 정리 (Phase 0.5 스타일)"""
        before = text
        after = self.SAFE_NEWLINE_PATTERN.sub(' ', text)
        
        removed_count = before.count('\n') - after.count('\n')
        if removed_count > 0:
            logger.info(f"      ✂️ 단어 중간 줄바꿈 제거: {removed_count}개")
        
        return after
    
    def _preprocess_for_chapter_parsing(self, text: str) -> str:
        """장/조문 파싱 전처리"""
        text = re.sub(r'(제\s*\d+\s*장)', r'\n\1 ', text)
        text = re.sub(r'(제\s*\d+\s*조)', r'\n\1', text)
        return text
    
    def _extract_front_matter(
        self, 
        text: str, 
        fallback_title: str = ""
    ) -> Tuple[str, str, str]:
        """문서 Front Matter 추출"""
        # 타이틀 추출
        title = fallback_title
        title_match = self.TITLE_PATTERN.search(text[:500])
        if title_match:
            title = title_match.group(1)
            logger.info(f"   📌 타이틀 추출: {title}")
        
        # 개정이력 추출
        amendment_history = ""
        amendments = []
        
        spirit_match = self.BASIC_SPIRIT_PATTERN.search(text)
        search_end = spirit_match.start() if spirit_match else 1000
        
        for match in self.AMENDMENT_PATTERN.finditer(text[:search_end]):
            amendments.append(match.group(0))
        
        if amendments:
            amendment_history = ' '.join(amendments)
            logger.info(f"   📅 개정이력: {len(amendments)}건")
        
        return title, amendment_history, text
    
    def _extract_basic_spirit(self, text: str) -> str:
        """기본정신 추출"""
        match = self.BASIC_SPIRIT_PATTERN.search(text)
        if not match:
            return ""
        
        start = match.end()
        
        next_article = self.ARTICLE_HEADER_PATTERN.search(text, start)
        next_chapter = self.CHAPTER_PATTERN.search(text, start)
        
        if next_article and next_chapter:
            end = min(next_article.start(), next_chapter.start())
        elif next_article:
            end = next_article.start()
        elif next_chapter:
            end = next_chapter.start()
        else:
            end = len(text)
        
        spirit_text = text[start:end].strip()
        return spirit_text
    
    def _extract_chapters(self, text: str) -> List[Chapter]:
        """장 추출"""
        chapters = []
        order = 0
        
        for match in self.CHAPTER_PATTERN.finditer(text):
            chapter_num_raw = match.group(1).strip()
            chapter_title_raw = match.group(2).strip()
            
            chapter_num = re.sub(r'\s+', '', chapter_num_raw)
            chapter_title = re.sub(r'제\d+조.*$', '', chapter_title_raw).strip()
            
            if not chapter_title:
                continue
            
            chapters.append(Chapter(
                number=chapter_num,
                title=chapter_title,
                start_pos=match.start(),
                section_order=order
            ))
            
            order += 1
        
        return chapters
    
    def _extract_articles_from_text(self, text: str) -> List[Article]:
        """조문 추출"""
        articles = []
        
        for match in self.ARTICLE_HEADER_PATTERN.finditer(text):
            article_no = match.group(1)
            article_no_sub = match.group(2)
            article_title = match.group(3)
            
            if article_no_sub:
                article_number = f"제{article_no}조의{article_no_sub}"
            else:
                article_number = f"제{article_no}조"
            
            start = match.end()
            
            next_match = self.ARTICLE_HEADER_PATTERN.search(text, start)
            end = next_match.start() if next_match else len(text)
            
            body = text[start:end].strip()
            
            articles.append(Article(
                number=article_number,
                title=article_title,
                body=body,
                start_pos=match.start(),
                end_pos=end,
                section_order=0
            ))
        
        return articles
    
    def _assign_chapters_to_articles(self, chapters: List[Chapter], articles: List[Article]):
        """조문에 chapter_number 할당"""
        for article in articles:
            article.chapter_number = None
            
            for i, chapter in enumerate(chapters):
                next_chapter_pos = chapters[i+1].start_pos if i+1 < len(chapters) else float('inf')
                
                if chapter.start_pos <= article.start_pos < next_chapter_pos:
                    article.chapter_number = chapter.number
                    break
    
    def _assign_section_order(self, chapters: List[Chapter], articles: List[Article]):
        """section_order 부여"""
        all_sections = []
        
        for chapter in chapters:
            all_sections.append(('chapter', chapter))
        
        for article in articles:
            all_sections.append(('article', article))
        
        all_sections.sort(key=lambda x: x[1].start_pos)
        
        for order, (section_type, section) in enumerate(all_sections):
            section.section_order = order
        
        logger.info(f"   🔢 section_order 부여 완료: {len(all_sections)}개 섹션")
    
    def _remove_chapter_headers(self, text: str) -> str:
        """텍스트에서 장 헤더 제거"""
        return self.CHAPTER_PATTERN.sub('', text).strip()
    
    def to_chunks(self, parsed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.7.5: 파싱 결과 → 청크 변환 (Annex 지원)
        """
        chunks = []
        
        # 1. 타이틀 청크
        if parsed_result['document_title']:
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
        
        # 2. 개정이력 청크
        if parsed_result['amendment_history']:
            chunks.append({
                'content': parsed_result['amendment_history'],
                'metadata': {
                    'type': 'amendment_history',
                    'boundary': 'header',
                    'title': '개정 이력',
                    'char_count': len(parsed_result['amendment_history']),
                    'section_order': -2
                }
            })
        
        # ✅ Phase 0.7.5: Annex 모드 체크
        if parsed_result.get('is_annex_mode', False):
            # Annex 청크 생성
            annex_content = parsed_result.get('annex_content', '')
            
            if annex_content:
                # 별표 헤더 감지
                annex_header_match = self.ANNEX_HEADER_PATTERN.search(annex_content)
                related_match = self.RELATED_ARTICLE_PATTERN.search(annex_content)
                
                annex_no = None
                annex_title = "별표/부록"
                related_article = None
                
                if annex_header_match:
                    annex_no = annex_header_match.group(1)
                    annex_title = annex_header_match.group(2).strip()
                
                if related_match:
                    article_no = related_match.group(1)
                    paragraph_no = related_match.group(2) or ""
                    related_article = f"제{article_no}조" + (f"제{paragraph_no}항" if paragraph_no else "")
                
                chunks.append({
                    'content': annex_content,
                    'metadata': {
                        'type': 'annex',
                        'boundary': 'annex',
                        'title': annex_title,
                        'annex_no': annex_no,
                        'related_article': related_article,
                        'char_count': len(annex_content),
                        'section_order': 0
                    }
                })
                
                logger.info(f"   ✅ Annex 청크 생성: [별표 {annex_no}] {annex_title}")
        
        else:
            # 기존 법조문 모드 청크
            # 3. 기본정신 청크
            if parsed_result['basic_spirit']:
                chunks.append({
                    'content': parsed_result['basic_spirit'],
                    'metadata': {
                        'type': 'basic',
                        'boundary': 'basic_spirit',
                        'title': '기본정신',
                        'char_count': len(parsed_result['basic_spirit']),
                        'section_order': -1
                    }
                })
            
            # 4. 장 청크
            for chapter in parsed_result['chapters']:
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
            
            # 5. 조문 청크
            for article in parsed_result['articles']:
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
        
        chunks.sort(key=lambda c: c['metadata'].get('section_order', 999))
        
        logger.info(f"✅ 청크 변환 완료 (Phase 0.7.5): {len(chunks)}개")
        
        if parsed_result.get('is_annex_mode'):
            logger.info(f"   - 타이틀: 1개")
            logger.info(f"   - 개정이력: {1 if parsed_result['amendment_history'] else 0}개")
            logger.info(f"   - Annex: 1개")
        else:
            logger.info(f"   - 타이틀: 1개")
            logger.info(f"   - 개정이력: {1 if parsed_result['amendment_history'] else 0}개")
            logger.info(f"   - 기본정신: {1 if parsed_result['basic_spirit'] else 0}개")
            logger.info(f"   - 장: {parsed_result['total_chapters']}개")
            logger.info(f"   - 조문: {parsed_result['total_articles']}개")
        
        return chunks
    
    def to_markdown(self, parsed_result: Dict[str, Any]) -> str:
        """
        ✅ Phase 0.7.5: 파싱 결과 → Markdown 변환 (Annex 지원)
        """
        lines = []
        
        # 1. 타이틀
        if parsed_result['document_title']:
            lines.append(f"# {parsed_result['document_title']}")
            lines.append("")
        
        # 2. 개정이력
        if parsed_result['amendment_history']:
            lines.append("## 개정 이력")
            lines.append("")
            
            amendments = parsed_result['amendment_history'].split()
            for amendment in amendments:
                lines.append(f"- {amendment}")
            
            lines.append("")
        
        # ✅ Phase 0.7.5: Annex 모드 체크
        if parsed_result.get('is_annex_mode', False):
            annex_content = parsed_result.get('annex_content', '')
            
            if annex_content:
                # 별표 헤더 감지
                annex_header_match = self.ANNEX_HEADER_PATTERN.search(annex_content)
                
                if annex_header_match:
                    annex_no = annex_header_match.group(1)
                    annex_title = annex_header_match.group(2).strip()
                    lines.append(f"## [별표 {annex_no}] {annex_title}")
                    lines.append("")
                
                lines.append(annex_content)
                lines.append("")
        
        else:
            # 기존 법조문 모드
            # 3. 기본정신
            if parsed_result['basic_spirit']:
                lines.append("## 기본정신")
                lines.append("")
                lines.append(parsed_result['basic_spirit'])
                lines.append("")
            
            # 4. 장/조문 (section_order 순)
            all_sections = []
            
            for chapter in parsed_result['chapters']:
                all_sections.append(('chapter', chapter))
            
            for article in parsed_result['articles']:
                all_sections.append(('article', article))
            
            all_sections.sort(key=lambda x: x[1].section_order)
            
            for section_type, section in all_sections:
                if section_type == 'chapter':
                    lines.append(f"## {section.number} {section.title}")
                    lines.append("")
                else:
                    lines.append(f"### {section.number}({section.title})")
                    lines.append("")
                    lines.append(section.body)
                    lines.append("")
        
        markdown = "\n".join(lines)
        
        logger.info(f"✅ Markdown 변환 완료: {len(markdown)}자")
        
        return markdown
    
    def to_review_md(self, parsed_result: Dict[str, Any]) -> str:
        """리뷰용 Markdown (to_markdown과 동일)"""
        return self.to_markdown(parsed_result)
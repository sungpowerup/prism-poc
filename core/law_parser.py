"""
law_parser.py - LawMode 조문 파서
Phase 0.6.3 → Phase 0.5 Rollback (텍스트 품질 복구)

✅ Phase 0.5 복구 핫픽스 (GPT 권장):
1. _normalize_linebreaks(): sub('', text) → sub(' ', text) (공백 보존!)
2. parse() 기본값: normalize_linebreaks=True → False (0.5 스타일)

🎯 목표:
- 구조 메타 = Phase 0.6 유지 (타이틀/장/조문/section_order)
- 텍스트 품질 = Phase 0.5 복구 (띄어쓰기 보존)

Author: 박준호 (AI/ML Lead) + GPT 최종 권장
Date: 2025-11-14
Version: Phase 0.5 Rollback
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
    규정/법령 전용 파서 (Phase 0.5 Rollback)
    
    ✅ Phase 0.5 복구:
    - 텍스트 품질 = Phase 0.5 수준 (띄어쓰기 보존)
    - 구조 메타 = Phase 0.6 유지 (타이틀/장/조문)
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
    
    # ✅ Phase 0.6.3: 장 패턴 (전처리 후 사용)
    # "제1장" + 다음 "제" 나오기 전까지의 한글만
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
    
    # 줄바꿈 정리 패턴
    SAFE_NEWLINE_PATTERN = re.compile(
        r'(?<=[가-힣0-9])(?<![.?!])[\r]?\n(?=[가-힣0-9])',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info("✅ LawParser 초기화 (Phase 0.5 Rollback)")
        logger.info("   📌 텍스트 품질: Phase 0.5 (띄어쓰기 보존)")
        logger.info("   📌 구조 메타: Phase 0.6 (타이틀/장/조문)")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        enacted_date: Optional[str] = None,
        clean_artifacts: bool = True,
        normalize_linebreaks: bool = False  # ✅ Phase 0.5: 기본 OFF
    ) -> Dict[str, Any]:
        """
        PDF 텍스트를 파싱하여 조문 구조 추출
        
        Args:
            pdf_text: PDF에서 추출한 원본 텍스트
            document_title: 문서 제목
            enacted_date: 제정일
            clean_artifacts: 페이지 아티팩트 제거 여부
            normalize_linebreaks: 줄바꿈 정리 여부 (✅ False = Phase 0.5 스타일)
        
        Returns:
            {
                'document_title': str,
                'enacted_date': str,
                'amendment_history': str,
                'basic_spirit': str,
                'chapters': List[Chapter],
                'articles': List[Article],
                'total_articles': int,
                'total_chapters': int
            }
        """
        logger.info(f"📜 LawParser Phase 0.5 Rollback 시작: {document_title}")
        logger.info(f"   📄 입력 텍스트: {len(pdf_text)}자")
        logger.info(f"   🔧 normalize_linebreaks: {normalize_linebreaks} (False = 0.5 스타일)")
        
        # Phase 0.5: 페이지 아티팩트 제거
        if clean_artifacts:
            try:
                from .page_cleaner import clean_page_artifacts
                pdf_text = clean_page_artifacts(pdf_text)
                logger.info(f"   🧹 아티팩트 제거 후: {len(pdf_text)}자")
            except ImportError:
                logger.warning("   ⚠️ PageCleaner 미설치 - 건너뜀")
        
        # Phase 0.5/0.6: 줄바꿈 정리 (선택)
        if normalize_linebreaks:
            original_len = len(pdf_text)
            pdf_text = self._normalize_linebreaks(pdf_text)
            logger.info(f"   ✂️ 줄바꿈 정리: {original_len}자 → {len(pdf_text)}자 ({len(pdf_text)-original_len:+d})")
        else:
            logger.info(f"   ⏸️ 줄바꿈 정리 건너뜀 (Phase 0.5 모드)")
        
        # ✅ Phase 0.6.3: 장/조문 전처리 (GPT 권장)
        pdf_text = self._preprocess_for_chapter_parsing(pdf_text)
        
        # Front Matter 추출
        title, amendment_history, pdf_text = self._extract_front_matter(pdf_text, document_title)
        
        # 1. 기본정신 추출
        basic_spirit = self._extract_basic_spirit(pdf_text)
        logger.info(f"   ✅ 기본정신: {len(basic_spirit)}자")
        
        # 2. 장 추출 (Phase 0.6.3 정밀)
        chapters = self._extract_chapters(pdf_text)
        logger.info(f"   ✅ 장: {len(chapters)}개")
        
        # 3. 조문 추출
        articles = self._extract_articles_from_text(pdf_text)
        logger.info(f"   ✅ 조문: {len(articles)}개")
        
        # 4. 조문에 chapter_number 할당
        self._assign_chapters_to_articles(chapters, articles)
        
        # 5. section_order 부여
        self._assign_section_order(chapters, articles)
        
        # 6. 기본정신/조문에서 장 헤더 제거
        basic_spirit = self._remove_chapter_headers(basic_spirit)
        for article in articles:
            article.body = self._remove_chapter_headers(article.body)
        
        logger.info(f"✅ LawParser Phase 0.5 Rollback 완료: {len(chapters)}개 장, {len(articles)}개 조문")
        
        return {
            'document_title': title,
            'enacted_date': enacted_date or '',
            'amendment_history': amendment_history,
            'basic_spirit': basic_spirit,
            'chapters': chapters,
            'articles': articles,
            'total_articles': len(articles),
            'total_chapters': len(chapters)
        }
    
    def _normalize_linebreaks(self, text: str) -> str:
        """
        ✅ Phase 0.5 Rollback: 안전 모드 줄바꿈 정리
        
        🔥 핵심 수정:
        - sub('', text) → sub(' ', text)
        - 줄바꿈 제거 시 공백(' ') 삽입하여 단어 붙음 방지
        
        Before (Phase 0.6):
            "이 규정은\n한국농어촌공사" → "이규정은한국농어촌공사" ❌
        
        After (Phase 0.5):
            "이 규정은\n한국농어촌공사" → "이 규정은 한국농어촌공사" ✅
        """
        before = text
        
        # ✅ 핵심: 줄바꿈을 공백으로 치환 (공백 보존!)
        after = self.SAFE_NEWLINE_PATTERN.sub(' ', text)  # '' → ' ' (공백 하나!)
        #                                       ^
        #                                  Phase 0.5 핵심 수정!
        
        removed_count = before.count('\n') - after.count('\n')
        
        if removed_count > 0:
            logger.info(f"      ✂️ 단어 중간 줄바꿈 제거: {removed_count}개 (✅ 공백 보존)")
        
        return after
    
    def _preprocess_for_chapter_parsing(self, text: str) -> str:
        """
        ✅ Phase 0.6.3: 장/조문 파싱 전처리 (GPT 권장)
        
        "제1장 총칙제1조(목적)" → "제1장 총칙\n제1조(목적)"
        
        Args:
            text: 원본 텍스트
        
        Returns:
            전처리된 텍스트
        """
        # 1. 제N장 앞뒤 줄바꿈 강제
        text = re.sub(r'(제\s*\d+\s*장)', r'\n\1 ', text)
        
        # 2. 제N조 앞 줄바꿈 강제
        text = re.sub(r'(제\s*\d+\s*조)', r'\n\1', text)
        
        logger.debug("   🔧 장/조문 전처리 완료 (줄바꿈 강제)")
        
        return text
    
    def _extract_front_matter(
        self, 
        text: str, 
        fallback_title: str = ""
    ) -> Tuple[str, str, str]:
        """
        ✅ Phase 0.6.2: 문서 Front Matter 추출
        
        Returns:
            (title, amendment_history, remaining_text)
        """
        # 1. 타이틀 추출
        title = fallback_title
        title_match = self.TITLE_PATTERN.search(text[:500])
        if title_match:
            title = title_match.group(1)
            logger.info(f"   📌 타이틀 추출: {title}")
        
        # 2. 개정이력 추출
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
        """
        ✅ Phase 0.6.3: 장 추출 (정밀 파싱)
        
        "제1장 총칙" → chapter_title="총칙"만
        (전처리로 "제1장 총칙\n제1조..." 형태 보장됨)
        """
        chapters = []
        order = 0
        
        for match in self.CHAPTER_PATTERN.finditer(text):
            chapter_num_raw = match.group(1).strip()  # "제 1 장" → "제 1 장"
            chapter_title_raw = match.group(2).strip()  # "총칙제" → "총칙"
            
            # 공백 정규화
            chapter_num = re.sub(r'\s+', '', chapter_num_raw)  # "제1장"
            
            # ✅ Phase 0.6.3: chapter_title 정제
            # "총칙제1조..." → "총칙"만
            # 이미 전처리로 "\n제1조" 형태라 "제"가 안 붙지만, 만약을 위해
            chapter_title = re.sub(r'제\d+조.*$', '', chapter_title_raw).strip()
            
            chapter = Chapter(
                number=chapter_num,
                title=chapter_title,
                start_pos=match.start(),
                section_order=order
            )
            chapters.append(chapter)
            
            logger.info(f"   📂 {chapter_num} {chapter_title} (순서: {order})")
            order += 1
        
        return chapters
    
    def _extract_articles_from_text(self, text: str) -> List[Article]:
        """조문 추출"""
        articles = []
        matches = list(self.ARTICLE_HEADER_PATTERN.finditer(text))
        
        for i, match in enumerate(matches):
            article_num = match.group(1)
            article_title = match.group(3)
            article_full_num = f"제{article_num}조"
            
            if match.group(2):
                article_full_num += f"의{match.group(2)}"
            
            start_pos = match.start()
            
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            body = text[start_pos:end_pos].strip()
            
            article = Article(
                number=article_full_num,
                title=article_title,
                body=body,
                start_pos=start_pos,
                end_pos=end_pos
            )
            articles.append(article)
        
        return articles
    
    def _assign_chapters_to_articles(self, chapters: List[Chapter], articles: List[Article]) -> None:
        """조문에 chapter_number 할당"""
        if not chapters:
            return
        
        for article in articles:
            assigned_chapter = None
            
            for i, chapter in enumerate(chapters):
                if article.start_pos >= chapter.start_pos:
                    assigned_chapter = chapter.number
                else:
                    break
            
            article.chapter_number = assigned_chapter
            
            if assigned_chapter:
                logger.debug(f"      {article.number} → {assigned_chapter}")
    
    def _assign_section_order(self, chapters: List[Chapter], articles: List[Article]) -> None:
        """section_order 부여"""
        order = 0
        
        all_sections = []
        
        for chapter in chapters:
            all_sections.append(('chapter', chapter))
        
        for article in articles:
            all_sections.append(('article', article))
        
        all_sections.sort(key=lambda x: x[1].start_pos)
        
        for section_type, section in all_sections:
            section.section_order = order
            order += 1
        
        logger.info(f"   🔢 section_order 부여 완료: {order}개 섹션")
    
    def _remove_chapter_headers(self, text: str) -> str:
        """텍스트에서 장 헤더 제거"""
        cleaned = self.CHAPTER_PATTERN.sub('', text)
        return cleaned.strip()
    
    def to_chunks(self, parsed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ✅ Phase 0.6.2: 파싱 결과 → 청크 변환
        
        순서: title → amendment_history → basic → chapter → article
        """
        chunks = []
        
        # 0. 타이틀 청크
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
        
        # 1. 개정이력 청크
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
        
        # 2. 기본정신 청크
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
        
        # 3. 장 청크
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
        
        # 4. 조문 청크
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
        
        logger.info(f"✅ 청크 변환 완료 (Phase 0.5 Rollback): {len(chunks)}개")
        logger.info(f"   - 타이틀: 1개")
        logger.info(f"   - 개정이력: 1개")
        logger.info(f"   - 기본정신: 1개")
        logger.info(f"   - 장: {parsed_result['total_chapters']}개")
        logger.info(f"   - 조문: {parsed_result['total_articles']}개")
        
        return chunks
    
    def to_markdown(self, parsed_result: Dict[str, Any]) -> str:
        """
        ✅ Phase 0.6.2: 파싱 결과 → Markdown 변환
        
        구조:
        # 타이틀
        ## 개정 이력
        - 개정1
        - 개정2
        ## 기본정신
        ...
        ## 제1장 총칙
        ### 제1조(목적)
        ...
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
        """
        ✅ Phase 0.6.2: 리뷰용 Markdown (to_markdown과 동일)
        
        Phase 0.7/0.9에서 추가 뷰 레이어 적용 가능
        """
        return self.to_markdown(parsed_result)
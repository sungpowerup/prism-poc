"""
law_parser.py - LawMode 조문 파서
Phase 0.5 "Polishing & Standardization"

✅ Phase 0.5 개선:
- PageCleaner 통합 (clean_artifacts=True)
- 페이지 번호 완전 제거
- 문서 프로파일 지원 (옵션)

Author: 박준호 (AI/ML Lead) + GPT 설계
Date: 2025-11-14
Version: Phase 0.5
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """조문 데이터 클래스"""
    number: str  # 제1조, 제2조 등
    title: Optional[str]  # 목적, 적용범위 등
    body: str  # 본문
    start_pos: int  # 텍스트 내 시작 위치
    end_pos: int  # 텍스트 내 끝 위치
    article_type: str = 'article'  # 'article', 'deleted' 등


class LawParser:
    """
    규정/법령 전용 파서 (Phase 0.5)
    
    ✅ Phase 0.5 개선:
    - PageCleaner 통합 → 페이지 번호 자동 제거
    - PDF 텍스트 기반 정확한 조문 추출
    """
    
    # 기본정신 패턴
    BASIC_SPIRIT_PATTERN = re.compile(
        r'기\s*본\s*정\s*신',
        re.MULTILINE | re.IGNORECASE
    )
    
    # 조문 헤더 패턴 (제N조 + 제목)
    # 예: "제1조(목적)", "제2조의2(특례)", "제3조 (적용범위)"
    ARTICLE_HEADER_PATTERN = re.compile(
        r'제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*\(([^)]+)\)',
        re.MULTILINE
    )
    
    # 장 패턴
    CHAPTER_PATTERN = re.compile(
        r'제\s*(\d+)\s*장\s+(.+?)(?=\n|$)',
        re.MULTILINE
    )
    
    def __init__(self):
        """초기화"""
        logger.info("✅ LawParser 초기화 (Phase 0.5)")
    
    def parse(
        self,
        pdf_text: str,
        document_title: str = "",
        enacted_date: Optional[str] = None,
        clean_artifacts: bool = True
    ) -> Dict[str, Any]:
        """
        PDF 텍스트를 파싱하여 조문 구조 추출
        
        Args:
            pdf_text: PDF에서 추출한 원본 텍스트
            document_title: 문서 제목
            enacted_date: 제정일 (YYYY.MM.DD)
            clean_artifacts: 페이지 아티팩트 제거 여부 (Phase 0.5)
        
        Returns:
            {
                'document_title': str,
                'enacted_date': str,
                'basic_spirit': str,  # 기본정신 본문
                'chapters': List[Dict],  # 장 정보
                'articles': List[Article],  # 조문 리스트
                'total_articles': int
            }
        """
        logger.info(f"📜 LawParser 시작: {document_title}")
        logger.info(f"   📄 입력 텍스트: {len(pdf_text)}자")
        
        # ✅ Phase 0.5: 페이지 아티팩트 제거
        if clean_artifacts:
            try:
                from .page_cleaner import clean_page_artifacts
                pdf_text = clean_page_artifacts(pdf_text)
                logger.info(f"   🧹 아티팩트 제거 후: {len(pdf_text)}자")
            except ImportError:
                logger.warning("   ⚠️ PageCleaner 미설치 - 건너뜀")
        
        # 1. 기본정신 추출
        basic_spirit = self._extract_basic_spirit(pdf_text)
        logger.info(f"   ✅ 기본정신: {len(basic_spirit)}자")
        
        # 2. 장 추출
        chapters = self._extract_chapters(pdf_text)
        logger.info(f"   ✅ 장: {len(chapters)}개")
        
        # 3. 조문 추출 (핵심!)
        articles = self._extract_articles_from_text(pdf_text)
        logger.info(f"   ✅ 조문: {len(articles)}개")
        
        # 4. 결과 조립
        logger.info(f"✅ LawParser 완료: {len(articles)}개 조문")
        
        return {
            'document_title': document_title,
            'enacted_date': enacted_date or '',
            'basic_spirit': basic_spirit,
            'chapters': chapters,
            'articles': articles,
            'total_articles': len(articles)
        }
    
    def _extract_basic_spirit(self, text: str) -> str:
        """기본정신 추출"""
        match = self.BASIC_SPIRIT_PATTERN.search(text)
        if not match:
            return ""
        
        start = match.end()
        
        # 다음 조문 또는 장까지
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
    
    def _extract_chapters(self, text: str) -> List[Dict[str, Any]]:
        """장 추출"""
        chapters = []
        for match in self.CHAPTER_PATTERN.finditer(text):
            chapters.append({
                'number': f"제{match.group(1)}장",
                'title': match.group(2).strip(),
                'start_pos': match.start()
            })
        return chapters
    
    def _extract_articles_from_text(self, text: str) -> List[Article]:
        """
        조문 추출 (핵심 로직)
        
        제N조(제목) 패턴으로 시작 → 다음 조문까지가 본문
        """
        articles = []
        
        matches = list(self.ARTICLE_HEADER_PATTERN.finditer(text))
        
        if not matches:
            logger.warning("   ⚠️ 조문 헤더 미발견")
            return articles
        
        logger.info(f"   🔍 조문 헤더: {len(matches)}개 발견")
        
        for i, match in enumerate(matches):
            article_num = match.group(1)
            article_sub = match.group(2)  # "의2"
            article_title = match.group(3)
            
            # 조문 번호 조립
            if article_sub:
                number = f"제{article_num}조의{article_sub}"
            else:
                number = f"제{article_num}조"
            
            # 본문 범위
            body_start = match.end()
            
            if i < len(matches) - 1:
                body_end = matches[i + 1].start()
            else:
                body_end = len(text)
            
            body = text[body_start:body_end].strip()
            
            # Article 객체 생성
            article = Article(
                number=number,
                title=article_title,
                body=body,
                start_pos=match.start(),
                end_pos=body_end
            )
            
            articles.append(article)
            logger.info(f"   📄 {number} ({article_title}): {len(body)}자")
        
        return articles
    
    def to_chunks(self, parsed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        파싱 결과 → 청크 변환
        
        Returns:
            List[Chunk] - RAG용 청크
        """
        chunks = []
        
        # 1. 기본정신 청크
        if parsed_result['basic_spirit']:
            chunks.append({
                'content': parsed_result['basic_spirit'],
                'metadata': {
                    'type': 'basic',
                    'boundary': 'basic_spirit',
                    'title': '기본정신',
                    'char_count': len(parsed_result['basic_spirit'])
                }
            })
        
        # 2. 조문 청크
        for article in parsed_result['articles']:
            content = f"{article.number}({article.title})\n{article.body}"
            
            chunks.append({
                'content': content,
                'metadata': {
                    'type': 'article',
                    'boundary': 'article',
                    'article_number': article.number,
                    'article_title': article.title,
                    'char_count': len(content)
                }
            })
        
        logger.info(f"✅ 청크 변환 완료: {len(chunks)}개")
        
        return chunks


# ============================================
# 테스트
# ============================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    sample_text = """
    기본정신
    
    이 규정은 한국농어촌공사 직원의 인사관리에 관한 사항을 정함으로써
    인사의 공정성을 확보하고 직원의 근무의욕을 높임을 목적으로 한다.
    
    인사규정
    402-3
    
    제1장 총칙
    
    제1조(목적) 이 규정은 한국농어촌공사 직원의 인사관리에 관하여
    필요한 사항을 정함을 목적으로 한다.
    
    인사규정
    402-4
    
    제2조(적용범위) 이 규정은 한국농어촌공사(이하 "공사"라 한다)의
    임원 및 직원에게 적용한다.
    """
    
    parser = LawParser()
    result = parser.parse(
        pdf_text=sample_text,
        document_title="인사규정",
        clean_artifacts=True  # ✅ Phase 0.5
    )
    
    print(f"\n총 조문: {result['total_articles']}개")
    print(f"기본정신: {len(result['basic_spirit'])}자")
    print(f"장: {len(result['chapters'])}개")
    
    chunks = parser.to_chunks(result)
    print(f"청크: {len(chunks)}개")
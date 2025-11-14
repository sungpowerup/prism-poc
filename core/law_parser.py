"""
law_parser.py - LawMode 조문 파서
Phase 0.4.0 P0-4 "LawMode"

PDF 텍스트 기반 조문 추출 (VLM 보조)

✅ 핵심 원칙:
1. 조문 구조의 "진실"은 PDF 텍스트
2. VLM은 표/이미지 보완용으로만 사용
3. 제1조~제N조 완전 추출 보장

Author: 박준호 (AI/ML Lead) + GPT 설계
Date: 2025-11-13
Version: Phase 0.4.0 P0-4
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
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
    규정/법령 전용 파서
    
    PDF 텍스트를 직접 파싱하여 조문 구조 추출
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
        logger.info("✅ LawParser 초기화 (Phase 0.4.0 P0-4)")
    
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
            clean_artifacts: 페이지 아티팩트 제거 여부
        
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
            from .page_cleaner import clean_page_artifacts
            pdf_text = clean_page_artifacts(pdf_text)
            logger.info(f"   🧹 아티팩트 제거 후: {len(pdf_text)}자")
        
        # 1. 기본정신 추출
        basic_spirit = self._extract_basic_spirit(pdf_text)
        logger.info(f"   ✅ 기본정신: {len(basic_spirit)}자")
        
        # 2. 장 추출
        chapters = self._extract_chapters(pdf_text)
        logger.info(f"   ✅ 장: {len(chapters)}개")
        
        # 3. 조문 추출 (핵심!)
        articles = self._extract_articles_from_text(pdf_text)
        logger.info(f"   ✅ 조문: {len(articles)}개")
        
        # 4. 조문 번호 정렬 (제1조 → 제2조 → ...)
        articles_sorted = sorted(articles, key=lambda a: self._parse_article_number(a.number))
        
        result = {
            'document_title': document_title,
            'enacted_date': enacted_date or '',
            'basic_spirit': basic_spirit,
            'chapters': chapters,
            'articles': articles_sorted,
            'total_articles': len(articles_sorted)
        }
        
        logger.info(f"✅ LawParser 완료: {len(articles_sorted)}개 조문")
        
        return result
    
    def _extract_basic_spirit(self, text: str) -> str:
        """기본정신 섹션 추출"""
        match = self.BASIC_SPIRIT_PATTERN.search(text)
        
        if not match:
            logger.warning("   ⚠️ 기본정신 미발견")
            return ""
        
        start = match.start()
        
        # 기본정신 끝: 다음 장 또는 제1조까지
        end = len(text)
        
        # 다음 장 찾기
        chapter_match = self.CHAPTER_PATTERN.search(text, start + 10)
        if chapter_match:
            end = min(end, chapter_match.start())
        
        # 제1조 찾기
        article_match = self.ARTICLE_HEADER_PATTERN.search(text, start + 10)
        if article_match:
            end = min(end, article_match.start())
        
        basic_text = text[start:end].strip()
        
        # "기본정신" 헤더 제거
        basic_text = self.BASIC_SPIRIT_PATTERN.sub('', basic_text, count=1).strip()
        
        return basic_text
    
    def _extract_chapters(self, text: str) -> List[Dict[str, Any]]:
        """장(章) 목록 추출"""
        chapters = []
        
        for match in self.CHAPTER_PATTERN.finditer(text):
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip()
            
            chapters.append({
                'number': f'제{chapter_num}장',
                'title': chapter_title,
                'position': match.start()
            })
        
        return chapters
    
    def _extract_articles_from_text(self, text: str) -> List[Article]:
        """
        PDF 텍스트에서 조문 추출 (핵심 메서드)
        
        전략:
        1. 정규식으로 "제N조(제목)" 패턴 찾기
        2. 각 조문의 시작~다음 조문 직전까지를 본문으로 추출
        3. Article 객체 생성
        """
        articles = []
        
        # 1. 모든 조문 헤더 위치 추출
        positions = []
        for match in self.ARTICLE_HEADER_PATTERN.finditer(text):
            article_num = match.group(1)
            article_sub = match.group(2)  # '의2' 같은 부분 (없으면 None)
            title = match.group(3).strip()
            
            # 조문 번호 생성
            if article_sub:
                full_number = f'제{article_num}조의{article_sub}'
            else:
                full_number = f'제{article_num}조'
            
            positions.append((match.start(), full_number, title))
            
            logger.debug(f"      📍 {full_number}({title}) at {match.start()}")
        
        if not positions:
            logger.warning("   ⚠️ 조문 헤더 미발견")
            return []
        
        logger.info(f"   🔍 조문 헤더: {len(positions)}개 발견")
        
        # 2. 각 조문의 본문 추출
        articles = self._extract_articles(text, positions)
        
        return articles
    
    def _extract_articles(
        self, 
        text: str, 
        positions: List[Tuple[int, str, Optional[str]]]
    ) -> List[Article]:
        """
        조문 본문 추출
        
        Args:
            text: 전체 텍스트
            positions: [(position, article_number, title), ...]
        
        Returns:
            [Article 객체들]
        """
        articles = []
        
        for i, (pos, article_num, title) in enumerate(positions):
            # 다음 조문 위치 (없으면 텍스트 끝)
            next_pos = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            
            # 본문 추출
            body = text[pos:next_pos].strip()
            
            # Article 객체 생성
            article = Article(
                number=article_num,
                title=title,
                body=body,
                start_pos=pos,
                end_pos=next_pos,
                article_type='article'
            )
            
            articles.append(article)
            
            logger.info(f"   📄 {article_num} ({title or '제목없음'}): {len(body)}자")
        
        return articles
    
    def to_chunks(self, parsed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        파싱 결과를 청크 형식으로 변환 (SemanticChunker 호환)
        
        Args:
            parsed_result: parse() 결과
        
        Returns:
            [{'content': ..., 'metadata': {...}}, ...]
        """
        chunks = []
        
        # 1. 기본정신 청크
        if parsed_result['basic_spirit']:
            chunks.append({
                'content': parsed_result['basic_spirit'],
                'metadata': {
                    'type': 'basic',
                    'boundary': '기본정신',
                    'title': None,
                    'char_count': len(parsed_result['basic_spirit']),
                    'chunk_index': 1
                }
            })
        
        # 2. 조문 청크
        for article in parsed_result['articles']:
            chunks.append({
                'content': article.body,
                'metadata': {
                    'type': 'article',
                    'boundary': article.number,
                    'title': article.title,
                    'char_count': len(article.body),
                    'chunk_index': len(chunks) + 1
                }
            })
        
        logger.info(f"✅ 청크 변환 완료: {len(chunks)}개")
        
        return chunks
    
    def _parse_article_number(self, article_num: str) -> Tuple[int, int]:
        """
        조문 번호를 정렬 가능한 튜플로 변환
        
        예:
        - "제1조" → (1, 0)
        - "제2조의2" → (2, 2)
        - "제10조" → (10, 0)
        """
        match = re.match(r'제(\d+)조(?:의(\d+))?', article_num)
        
        if not match:
            return (999, 999)  # 파싱 실패 시 맨 뒤로
        
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        
        return (main_num, sub_num)


# ============================================
# 테스트용 함수
# ============================================

def test_law_parser():
    """LawParser 단위 테스트"""
    
    sample_text = """
    인사규정
    
    기 본 정 신
    이 규정은 한국농어촌공사 직원의 보직, 승진, 신분보장, 상벌, 인사고과 등에 관한 사항을
    규정함으로써 공정하고 투명한 인사관리 구현을 통하여 설립목적을 달성한다.
    
    제1장 총 칙
    
    제1조(목적) 이 규정은 한국농어촌공사 직원에게 적용할 인사관리의 기준을 정하여 합리적이고 적정한 인
    사관리를 기하게 하는 것을 목적으로 한다.
    
    제2조(적용범위) 직원의 인사관리는 법령 및 정관에 정한 것을 제외하고는 이 규정에 따른다.
    
    제3조(직원 등의 구분) ① 삭 제 <2024.1.1.>
    ② 직원은 일반직, 별정직, 기사직 및 전문직으로 구분한다.
    """
    
    parser = LawParser()
    result = parser.parse(
        pdf_text=sample_text,
        document_title="인사규정 테스트"
    )
    
    print(f"기본정신: {len(result['basic_spirit'])}자")
    print(f"조문: {result['total_articles']}개")
    
    for article in result['articles']:
        print(f"  - {article.number} ({article.title})")
    
    # 청크 변환
    chunks = parser.to_chunks(result)
    print(f"\n청크: {len(chunks)}개")
    
    for chunk in chunks:
        meta = chunk['metadata']
        print(f"  - {meta['type']}: {meta['boundary']} ({meta['char_count']}자)")


if __name__ == '__main__':
    test_law_parser()
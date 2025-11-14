"""
golden_schema.py - PRISM Phase 0.8 Golden File Schema
GPT 권장 사항 100% 반영

✅ GPT 권장 사항:
1. parser_version, schema_version 메타 필수
2. 3축 비교 시스템 (구조/헤더/본문)
3. Edge cases 대응 (부칙, 개정이력, 비틀린 구조)

Author: 마창수산팀 (박준호 AI/ML Lead)
Date: 2025-11-14
Version: Phase 0.8
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class GoldenMetadata:
    """
    ✅ GPT 필수 요구: 스키마 버전 관리
    
    "두 개만 딱 메타로 들고 가도 미래에 수명 연장 엄청나다"
    """
    parser_version: str          # 파서 버전 (예: "0.8.0")
    schema_version: str          # 스키마 버전 (예: "1.0")
    document_title: str          # 문서 제목
    document_type: str           # 문서 타입 (standard, edge_case)
    golden_verified_date: str    # 검증 완료일 (YYYY-MM-DD)
    golden_verified_by: str      # 검증자 (예: "법무팀 김OO")
    source_file: str             # 원본 PDF 파일명
    page_count: int              # 페이지 수
    notes: Optional[str] = None  # 특이사항


@dataclass
class GoldenChapterStructure:
    """장 구조 검증용"""
    chapter_number: str          # "제1장"
    chapter_title: str           # "총칙"
    article_count: int           # 해당 장의 조문 수
    section_order: int           # 순서


@dataclass
class GoldenArticleStructure:
    """조문 구조 검증용"""
    article_number: str          # "제1조"
    article_title: str           # "목적"
    chapter_number: Optional[str] # "제1장" (장 없는 조문은 None)
    has_clauses: bool            # ①②③ 항 존재 여부
    clause_count: int            # 항 개수
    content_length: int          # 본문 길이 (문자 수)
    section_order: int           # 순서


@dataclass
class GoldenStructure:
    """
    ✅ GPT 권장: Level 1 - 구조 비교
    
    장 수, 조문 수, 메타 존재 여부
    """
    total_chapters: int
    total_articles: int
    has_title: bool
    has_amendment_history: bool
    has_basic_spirit: bool
    chapters: List[GoldenChapterStructure]
    articles: List[GoldenArticleStructure]


@dataclass
class GoldenHeader:
    """
    ✅ GPT 권장: Level 2 - 헤더 비교
    
    제N조, 제목, 장명 같은 헤더 문자열
    """
    title: Optional[str]                    # 문서 타이틀
    amendment_history_count: int            # 개정이력 건수
    basic_spirit_excerpt: Optional[str]     # 기본정신 앞 50자
    chapter_headers: List[str]              # ["제1장 총칙", "제2장 채용"]
    article_headers: List[str]              # ["제1조(목적)", "제2조(적용범위)"]


@dataclass
class GoldenContent:
    """
    ✅ GPT 권장: Level 3 - 본문 비교
    
    공백/개행/특수문자 무시 or 정규화 후 비교
    """
    normalized_text: str         # 정규화된 전체 텍스트
    article_bodies: Dict[str, str]  # {article_number: normalized_body}
    total_char_count: int        # 총 문자 수
    checksum: str                # MD5 체크섬


@dataclass
class GoldenFile:
    """
    최상위 Golden File 구조
    
    Example:
        {
          "metadata": {...},
          "structure": {...},
          "headers": {...},
          "content": {...}
        }
    """
    metadata: GoldenMetadata
    structure: GoldenStructure
    headers: GoldenHeader
    content: GoldenContent
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'metadata': asdict(self.metadata),
            'structure': {
                'total_chapters': self.structure.total_chapters,
                'total_articles': self.structure.total_articles,
                'has_title': self.structure.has_title,
                'has_amendment_history': self.structure.has_amendment_history,
                'has_basic_spirit': self.structure.has_basic_spirit,
                'chapters': [asdict(c) for c in self.structure.chapters],
                'articles': [asdict(a) for a in self.structure.articles]
            },
            'headers': asdict(self.headers),
            'content': asdict(self.content)
        }
    
    def to_json(self, filepath: str, indent: int = 2) -> None:
        """JSON 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoldenFile':
        """딕셔너리에서 로드"""
        metadata = GoldenMetadata(**data['metadata'])
        
        structure = GoldenStructure(
            total_chapters=data['structure']['total_chapters'],
            total_articles=data['structure']['total_articles'],
            has_title=data['structure']['has_title'],
            has_amendment_history=data['structure']['has_amendment_history'],
            has_basic_spirit=data['structure']['has_basic_spirit'],
            chapters=[GoldenChapterStructure(**c) for c in data['structure']['chapters']],
            articles=[GoldenArticleStructure(**a) for a in data['structure']['articles']]
        )
        
        headers = GoldenHeader(**data['headers'])
        content = GoldenContent(**data['content'])
        
        return cls(
            metadata=metadata,
            structure=structure,
            headers=headers,
            content=content
        )
    
    @classmethod
    def from_json(cls, filepath: str) -> 'GoldenFile':
        """JSON 파일에서 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


# ============================================
# 유틸리티 함수
# ============================================

def normalize_text(text: str) -> str:
    """
    텍스트 정규화 (Level 3 비교용)
    
    - 공백/개행 정리
    - 특수문자 무시
    - 대소문자 통일
    """
    import re
    
    # 연속 공백 제거
    normalized = re.sub(r'\s+', ' ', text)
    
    # 특수문자 제거 (법률 필수 기호 제외)
    # 괄호, 쉼표, 마침표는 유지
    normalized = re.sub(r'[^\w\s\(\),.\-①-⑳]', '', normalized)
    
    # 양쪽 공백 제거
    normalized = normalized.strip()
    
    return normalized


def calculate_checksum(text: str) -> str:
    """텍스트 MD5 체크섬"""
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# ============================================
# Golden File 생성 헬퍼
# ============================================

def create_golden_from_parsed_result(
    parsed_result: Dict[str, Any],
    metadata: GoldenMetadata
) -> GoldenFile:
    """
    LawParser 결과로부터 Golden File 생성
    
    Args:
        parsed_result: LawParser.parse() 결과
        metadata: Golden 메타데이터
    
    Returns:
        GoldenFile 객체
    """
    
    # 1. Structure
    chapters_golden = [
        GoldenChapterStructure(
            chapter_number=ch.number,
            chapter_title=ch.title,
            article_count=len([a for a in parsed_result['articles'] 
                              if a.chapter_number == ch.number]),
            section_order=ch.section_order
        )
        for ch in parsed_result['chapters']
    ]
    
    articles_golden = [
        GoldenArticleStructure(
            article_number=art.number,
            article_title=art.title,
            chapter_number=art.chapter_number,
            has_clauses='①' in art.body or '1.' in art.body,
            clause_count=len([line for line in art.body.split('\n') 
                             if line.strip().startswith(('①', '②', '③', '1.', '2.', '3.'))]),
            content_length=len(art.body),
            section_order=art.section_order
        )
        for art in parsed_result['articles']
    ]
    
    structure = GoldenStructure(
        total_chapters=parsed_result['total_chapters'],
        total_articles=parsed_result['total_articles'],
        has_title=bool(parsed_result['document_title']),
        has_amendment_history=bool(parsed_result['amendment_history']),
        has_basic_spirit=bool(parsed_result['basic_spirit']),
        chapters=chapters_golden,
        articles=articles_golden
    )
    
    # 2. Headers
    chapter_headers = [f"{ch.number} {ch.title}" for ch in parsed_result['chapters']]
    article_headers = [f"{art.number}({art.title})" for art in parsed_result['articles']]
    
    headers = GoldenHeader(
        title=parsed_result['document_title'],
        amendment_history_count=len(parsed_result['amendment_history'].split('제')) - 1 
                                if parsed_result['amendment_history'] else 0,
        basic_spirit_excerpt=parsed_result['basic_spirit'][:50] 
                            if parsed_result['basic_spirit'] else None,
        chapter_headers=chapter_headers,
        article_headers=article_headers
    )
    
    # 3. Content
    full_text = parsed_result['document_title'] or ""
    full_text += parsed_result['amendment_history'] or ""
    full_text += parsed_result['basic_spirit'] or ""
    for art in parsed_result['articles']:
        full_text += f"{art.number}({art.title})\n{art.body}\n"
    
    normalized = normalize_text(full_text)
    
    article_bodies = {
        art.number: normalize_text(art.body)
        for art in parsed_result['articles']
    }
    
    content = GoldenContent(
        normalized_text=normalized,
        article_bodies=article_bodies,
        total_char_count=len(full_text),
        checksum=calculate_checksum(normalized)
    )
    
    return GoldenFile(
        metadata=metadata,
        structure=structure,
        headers=headers,
        content=content
    )


# ============================================
# 사용 예시
# ============================================

if __name__ == '__main__':
    # Golden File 생성 예시
    metadata = GoldenMetadata(
        parser_version="0.8.0",
        schema_version="1.0",
        document_title="인사규정",
        document_type="standard",
        golden_verified_date="2025-11-14",
        golden_verified_by="법무팀 김민지",
        source_file="인사규정_일부개정전문-1-3_원본.pdf",
        page_count=3,
        notes="Phase 0.8 초기 Golden File"
    )
    
    print("✅ Golden File Schema 정의 완료 (Phase 0.8)")
    print(f"   - 메타: parser_version, schema_version 포함")
    print(f"   - 구조: 3축 비교 시스템 (Structure/Headers/Content)")
    print(f"   - 검증: Edge cases 대응 가능")

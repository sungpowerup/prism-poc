"""
document_profile.py - 문서 프로파일 시스템
Phase 0.5 "Standardization"

GPT 설계: 문서 타입별 처리 전략 + 패턴 + QA 기준

Author: 박준호 (AI/ML Lead) + GPT 설계
Date: 2025-11-14
Version: Phase 0.5
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Pattern, List, Dict, Any, Literal

logger = logging.getLogger(__name__)

# 모드 타입
Mode = Literal["law", "vlm"]


@dataclass
class DocumentProfile:
    """
    문서 프로파일
    
    문서 타입별 처리 전략 + 패턴 + QA 기준을 하나로 묶음
    """
    
    # 기본 정보
    id: str
    name: str
    mode: Mode
    description: str
    
    # 구조 인식 패턴
    chapter_pattern: Pattern
    article_pattern: Pattern
    article_loose_pattern: Pattern
    basic_spirit_pattern: Pattern | None = None
    
    # 노이즈 제거 패턴
    page_header_patterns: List[Pattern] = field(default_factory=list)
    inline_noise_patterns: List[Pattern] = field(default_factory=list)
    
    # QA 기준
    qa_min_match_ratio: float = 0.95
    allow_extra_articles: bool = True  # 제7조의2 같은 파생 조문 허용
    
    # 처리 전략
    strategy: Dict[str, Any] = field(default_factory=dict)


# ============================================
# 프로파일 정의
# ============================================

# 1. 인사규정 프로파일 (기본)
LAW_HR_PROFILE = DocumentProfile(
    id="law_kor_hr_v1",
    name="국문 인사규정 기본 프로파일",
    mode="law",
    description="한국 공공/공기업 인사규정, 취업규칙 등 조문 구조 문서",
    
    # 패턴
    chapter_pattern=re.compile(r'제\s*\d+\s*장', re.MULTILINE),
    article_pattern=re.compile(r'제\d+조(?:의\d+)?', re.MULTILINE),
    article_loose_pattern=re.compile(r'제\s*\d+\s*조(?:의\s*\d+)?', re.MULTILINE),
    basic_spirit_pattern=re.compile(
        r'[\s⟨<\[]*(기\s*본\s*정\s*신)[\s\]>⟩]*',
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 노이즈 제거
    page_header_patterns=[
        re.compile(r'^\s*\d{3}-\d+\s*$', re.MULTILINE),  # 402-3
        re.compile(r'^\s*인사\s*규정\s*$', re.MULTILINE),
        re.compile(r'^\s*(인사\s*규정)\s*\d{3}-\d+\s*$', re.MULTILINE),
    ],
    inline_noise_patterns=[
        re.compile(r'(인사\s*규정)\s*\d{3}-\d+'),
    ],
    
    # QA
    qa_min_match_ratio=0.95,
    allow_extra_articles=True,
    
    # 전략
    strategy={
        "source_of_truth": "pdf_text",   # PDF 텍스트가 진실
        "vlm_role": "table_only",        # VLM은 표/이미지만
        "chunk_unit": "article",         # 조문 단위 청킹
        "preserve_structure": True,      # 장/절/조 구조 보존
    }
)

# 2. 일반 법령 프로파일
LAW_GENERIC_PROFILE = DocumentProfile(
    id="law_kor_generic_v1",
    name="국문 법령 일반 프로파일",
    mode="law",
    description="법률, 시행령, 시행규칙 등 일반 법령 문서",
    
    chapter_pattern=re.compile(r'제\s*\d+\s*[장절]', re.MULTILINE),
    article_pattern=re.compile(r'제\d+조(?:의\d+)?', re.MULTILINE),
    article_loose_pattern=re.compile(r'제\s*\d+\s*조(?:의\s*\d+)?', re.MULTILINE),
    
    page_header_patterns=[
        re.compile(r'^\s*\d+\s*$', re.MULTILINE),  # 단순 페이지 번호
    ],
    
    qa_min_match_ratio=0.95,
    allow_extra_articles=True,
    
    strategy={
        "source_of_truth": "pdf_text",
        "chunk_unit": "article",
        "preserve_structure": True,
    }
)

# 3. 약관 프로파일
LAW_TERMS_PROFILE = DocumentProfile(
    id="law_kor_terms_v1",
    name="국문 약관 프로파일",
    mode="law",
    description="이용약관, 계약약관 등",
    
    chapter_pattern=re.compile(r'제\s*\d+\s*[장조]', re.MULTILINE),
    article_pattern=re.compile(r'제\d+조', re.MULTILINE),
    article_loose_pattern=re.compile(r'제\s*\d+\s*조', re.MULTILINE),
    
    qa_min_match_ratio=0.90,  # 약관은 조금 느슨하게
    allow_extra_articles=False,
    
    strategy={
        "source_of_truth": "pdf_text",
        "chunk_unit": "article",
    }
)

# 4. VLM 기본 프로파일 (일반 문서용)
VLM_GENERAL_PROFILE = DocumentProfile(
    id="vlm_general_v1",
    name="VLM 일반 문서 프로파일",
    mode="vlm",
    description="보고서, PPT, 자유 형식 문서",
    
    # VLM 모드는 패턴 느슨하게
    chapter_pattern=re.compile(r'#{1,3}\s*.+', re.MULTILINE),
    article_pattern=re.compile(r'제\d+조', re.MULTILINE),
    article_loose_pattern=re.compile(r'제\s*\d+\s*조', re.MULTILINE),
    
    qa_min_match_ratio=0.80,  # VLM은 느슨하게
    
    strategy={
        "source_of_truth": "vlm",
        "vlm_role": "primary",
        "chunk_unit": "semantic",
    }
)


# ============================================
# 프로파일 레지스트리
# ============================================

PROFILES: Dict[str, DocumentProfile] = {
    "law_hr": LAW_HR_PROFILE,
    "law_generic": LAW_GENERIC_PROFILE,
    "law_terms": LAW_TERMS_PROFILE,
    "vlm_general": VLM_GENERAL_PROFILE,
}


def get_profile(profile_id: str) -> DocumentProfile:
    """
    프로파일 조회
    
    Args:
        profile_id: 프로파일 ID
    
    Returns:
        DocumentProfile
    """
    if profile_id not in PROFILES:
        logger.warning(f"⚠️ 프로파일 '{profile_id}' 없음. 기본 프로파일 사용")
        return LAW_HR_PROFILE
    
    profile = PROFILES[profile_id]
    logger.info(f"✅ 프로파일 로드: {profile.name} ({profile.id})")
    
    return profile


def auto_detect_profile(text: str, filename: str = "") -> DocumentProfile:
    """
    문서 타입 자동 감지 → 프로파일 추천
    
    Args:
        text: 문서 텍스트
        filename: 파일명
    
    Returns:
        추천 프로파일
    """
    # 파일명 기반 힌트
    if any(keyword in filename.lower() for keyword in ['인사', 'hr', '규정', '규칙']):
        logger.info("📝 파일명 기반 감지: 인사규정")
        return LAW_HR_PROFILE
    
    if any(keyword in filename.lower() for keyword in ['약관', 'terms']):
        logger.info("📝 파일명 기반 감지: 약관")
        return LAW_TERMS_PROFILE
    
    # 텍스트 기반 힌트
    if '기본정신' in text or '기 본 정 신' in text:
        logger.info("📝 텍스트 기반 감지: 규정/법령 (기본정신 발견)")
        return LAW_HR_PROFILE
    
    # 조문 밀도
    article_count = len(re.findall(r'제\d+조', text))
    if article_count > 5:
        logger.info(f"📝 텍스트 기반 감지: 법령 (조문 {article_count}개)")
        return LAW_GENERIC_PROFILE
    
    # 기본값: VLM 모드
    logger.info("📝 기본 프로파일 선택: VLM 일반 문서")
    return VLM_GENERAL_PROFILE


# ============================================
# 테스트
# ============================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 프로파일 조회
    profile = get_profile("law_hr")
    print(f"\n프로파일: {profile.name}")
    print(f"모드: {profile.mode}")
    print(f"QA 기준: {profile.qa_min_match_ratio * 100}%")
    print(f"전략: {profile.strategy}")
    
    # 자동 감지
    sample_text = """
    기본정신
    이 규정은 한국농어촌공사 직원의 인사관리에 관한 사항을 정한다.
    
    제1조(목적) ...
    제2조(적용범위) ...
    """
    
    detected = auto_detect_profile(sample_text, "인사규정_2025.pdf")
    print(f"\n자동 감지: {detected.name}")
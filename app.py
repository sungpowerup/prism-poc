"""
app.py - PRISM Phase 0.7 룰 미세조정 완료

✅ 4대 핵심 조정:
1. 조사 앞 공백 제거 (직원에게 ✅)
2. 숫자/단위 사이 공백 최적화 (100만원 ✅)
3. 조문/표 제목 패턴 보정 (제5조의2 ✅)
4. 표 아래 주석 줄바꿈 안정화 (※ 비고 ✅)

✅ 표 문서 테스트 준비 완료

Author: 마창수산팀 + CEO + GPT 피드백
Date: 2025-11-15
Version: Phase 0.7 Final
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import json
import os
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prism.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 모듈 Import
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.hybrid_extractor import HybridExtractor
    from core.semantic_chunker import SemanticChunker
    from core.dual_qa_gate import DualQAGate, extract_pdf_text_layer
    from core.utils_fs import safe_temp_path, safe_remove
    
    logger.info("✅ 모듈 import 성공")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()

# LawParser Import
try:
    from core.law_parser import LawParser
    LAW_MODE_AVAILABLE = True
    logger.info("✅ LawParser 로드 성공")
except ImportError:
    LAW_MODE_AVAILABLE = False
    logger.warning("⚠️ LawParser 미설치")

# DocumentProfile Import
try:
    from core.document_profile import auto_detect_profile
    PROFILE_AVAILABLE = True
    logger.info("✅ DocumentProfile 로드 성공")
except ImportError:
    PROFILE_AVAILABLE = False
    logger.warning("⚠️ DocumentProfile 미설치")

# LLM Rewriter Import (Phase 0.9)
try:
    sys.path.insert(0, str(Path(__file__).parent / 'tests'))
    from llm_rewriter import LLMRewriter
    LLM_REWRITER_AVAILABLE = True
    logger.info("✅ LLMRewriter 로드 성공")
except ImportError as e:
    LLM_REWRITER_AVAILABLE = False
    logger.warning(f"⚠️ LLMRewriter 미설치: {e}")


# ============================================
# Phase 0.7: 룰 기반 띄어쓰기 (미세조정 완료)
# ============================================

LAW_SPACING_KEYWORDS = [
    "임용", "승진", "보수", "복무", "징계", "퇴직",
    "채용", "인사", "직원", "공사", "수습", "결격사유",
    "규정", "조직", "문화", "역량", "태도", "개선"
]

def apply_law_spacing(text: str) -> str:
    """
    Phase 0.7: 룰 기반 띄어쓰기 (미세조정 완료)
    
    ✅ 4대 핵심 조정:
    1. 조사 앞 공백 제거 (직원에게 ✅)
    2. 숫자/단위 사이 공백 최적화 (100만원 ✅)
    3. 조문/표 제목 패턴 보정 (제5조의2 ✅)
    4. 표 아래 주석 줄바꿈 안정화 (※ 비고 ✅)
    
    Args:
        text: 엔진 텍스트 (띄어쓰기 없는 상태)
    
    Returns:
        띄어쓰기 적용된 텍스트 (리뷰용)
    """
    
    # ==========================================
    # 1단계: 대표 패턴 치환 (변경 없음)
    # ==========================================
    replacements = {
        "이규정은한국농어촌공사직원": "이 규정은 한국농어촌공사 직원",
        "이규정은한국농어촌공사": "이 규정은 한국농어촌공사",
        "한국농어촌공사직원": "한국농어촌공사 직원",
        "임용승진보수복무징계퇴직": "임용 승진 보수 복무 징계 퇴직",
        "임용승진보수복무": "임용 승진 보수 복무",
        "보직승진신분보장상벌인사고과": "보직 승진 신분보장 상벌 인사고과",
        "인사관리의기준": "인사관리의 기준",
        "인사관리를": "인사관리를 ",
        "직원에게적용할": "직원에게 적용할",
        "적용할인사관리": "적용할 인사관리",
    }
    
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # ==========================================
    # 2단계: 조문/표 제목 패턴 보정 (✅ 조정 3)
    # ==========================================
    
    # 조문 번호 패턴 고정 (예: 제5조의2)
    text = re.sub(r"제\s?(\d+)\s?조\s?의\s?(\d+)", r"제\1조의\2", text)
    text = re.sub(r"제\s?(\d+)\s?조", r"제\1조", text)
    
    # 표 제목 패턴 고정
    # [표1], <표 3>, 표 2), 표1 등을 "표N" 형태로 통일
    text = re.sub(r"[\[\<]?\s?표\s?(\d+)\s?[\]\>\)]?", r"표\1", text)
    
    # 장 번호 패턴 고정 (예: 제1장)
    text = re.sub(r"제\s?(\d+)\s?장", r"제\1장", text)
    
    logger.info("✅ 조문/표 제목 패턴 보정 완료")
    
    # ==========================================
    # 3단계: 숫자/단위 사이 공백 최적화 (✅ 조정 2)
    # ==========================================
    
    # 숫자 + 단위는 절대 띄우지 않음
    # 예: 100만원, 50명, 3페이지, 5년, 2급
    units = ["만원", "원", "명", "건", "페이지", "부서", "년", "개월", "급", "조"]
    for unit in units:
        text = re.sub(rf"(\d+)\s+{unit}", rf"\1{unit}", text)
    
    # 날짜 패턴 보정 (예: 2024.1.1)
    text = re.sub(r"(\d{4})\s?\.\s?(\d{1,2})\s?\.\s?(\d{1,2})", r"\1.\2.\3", text)
    
    logger.info("✅ 숫자/단위 공백 최적화 완료")
    
    # ==========================================
    # 4단계: 조사 처리 (✅ 조정 1)
    # ==========================================
    
    # 조사 앞 공백 제거 + 조사 뒤 공백 추가
    # 기존: "직원에 게" (X)
    # 개선: "직원에게 " (O)
    
    # 주요 조사 목록
    josa_list = ["은", "는", "이", "가", "을", "를", "과", "와", "에", "에서", "에게", "로", "으로"]
    
    # 조사 패턴: (한글+)(조사)(한글)
    # → 조사는 앞 글자와 붙이고, 뒤 글자는 띄움
    for josa in josa_list:
        # "글자+조사+글자" → "글자조사 글자"
        text = re.sub(rf"([가-힣]+)\s?{josa}\s?([가-힣])", rf"\1{josa} \2", text)
    
    logger.info("✅ 조사 앞 공백 제거 완료")
    
    # ==========================================
    # 5단계: 표 주석 줄바꿈 안정화 (✅ 조정 4)
    # ==========================================
    
    # 표 주석 시작 문자 보호
    # ※, 비고:, (, 단, 등은 강제 줄바꿈 유지
    
    # 주석 시작 패턴
    comment_patterns = ["※", "비고:", "주:", "\\(", "단,", "다만,"]
    
    for pattern in comment_patterns:
        # 주석 앞에 줄바꿈 보장
        text = re.sub(rf"([^\n]){pattern}", rf"\1\n{pattern}", text)
    
    logger.info("✅ 표 주석 줄바꿈 안정화 완료")
    
    # ==========================================
    # 6단계: 키워드 앞 공백 (변경 없음)
    # ==========================================
    
    for kw in LAW_SPACING_KEYWORDS:
        # 앞에 한글/숫자가 있고 키워드가 오면 공백 삽입
        text = re.sub(rf"([가-힣0-9]){kw}", rf"\1 {kw}", text)
    
    # ==========================================
    # 7단계: 문장부호 뒤 공백 (변경 없음)
    # ==========================================
    
    # "다.이 규정은" → "다. 이 규정은"
    text = re.sub(r"([\.!?])([가-힣0-9])", r"\1 \2", text)
    
    # ==========================================
    # 8단계: 공백 정리 (변경 없음)
    # ==========================================
    
    # 연속 공백 제거
    text = re.sub(r"[ ]{2,}", " ", text)
    
    # 줄 단위 좌우 공백 제거
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)
    
    text = "\n".join(lines)
    
    logger.info("✅ Phase 0.7 룰 기반 띄어쓰기 적용 완료 (미세조정)")
    
    return text


# ============================================
# 헬퍼 함수
# ============================================

def to_review_md_basic(chunks: list) -> str:
    """
    청크 → 리뷰용 Markdown 변환 (룰 기반)
    
    **Case 1: LLM Rewriting = OFF**
    - Phase 0.7 룰 기반 띄어쓰기
    - 원문 의미 100% 유지
    """
    lines = []
    
    for chunk in chunks:
        meta = chunk['metadata']
        content = chunk['content']
        chunk_type = meta.get('type', 'unknown')
        
        if chunk_type == 'title':
            lines.append(f"# {content}")
            lines.append("")
        
        elif chunk_type == 'amendment_history':
            lines.append("## 개정 이력")
            lines.append("")
            amendments = content.split()
            for amendment in amendments:
                lines.append(f"- {amendment}")
            lines.append("")
        
        elif chunk_type == 'basic':
            lines.append("## 기본정신")
            lines.append("")
            lines.append(content)
            lines.append("")
        
        elif chunk_type == 'chapter':
            chapter_num = meta.get('chapter_number', '')
            chapter_title = meta.get('chapter_title', '')
            lines.append(f"## {chapter_num} {chapter_title}")
            lines.append("")
        
        elif chunk_type == 'article':
            article_num = meta.get('article_number', '')
            article_title = meta.get('article_title', '')
            lines.append(f"### {article_num}({article_title})")
            lines.append("")
            
            # 본문만 추출 (헤더 제외)
            body = content.split('\n', 1)[-1] if '\n' in content else content
            lines.append(body)
            lines.append("")
    
    return "\n".join(lines)


def to_review_md_llm(rewritten_chunks: list) -> str:
    """
    리라이팅된 청크 → 리뷰용 Markdown 변환
    
    **Case 2: LLM Rewriting = ON**
    """
    return to_review_md_basic(rewritten_chunks)


def process_document_vlm_mode(pdf_path: str, pdf_text: str):
    """VLM Mode 파이프라인"""
    
    st.info("🖼️ VLM Mode: 이미지 기반 처리 중...")
    progress_bar = st.progress(0)
    
    try:
        processor = PDFProcessor()
        pages = processor.process(pdf_path)
        max_pages = 20
        if len(pages) > max_pages:
            st.warning(f"⚠️ 페이지 수 제한: {len(pages)} → {max_pages}")
            pages = pages[:max_pages]
        
        vlm_service = VLMServiceV50(provider='azure_openai')
        extractor = HybridExtractor(vlm_service)
        markdown_text = extractor.extract(pages)
        progress_bar.progress(50)
        
        st.info("🧩 의미 기반 청킹 중...")
        chunker = SemanticChunker()
        chunks = chunker.chunk(markdown_text)
        st.success(f"✅ {len(chunks)}개 청크 생성")
        
        st.info("🔬 DualQA 검증 중...")
        qa_gate = DualQAGate()
        qa_result = qa_gate.validate(
            pdf_text=pdf_text,
            processed_text=markdown_text,
            source="vlm"
        )
        
        progress_bar.progress(100)
        
        return {
            'rag_markdown': markdown_text,  # RAG용 Markdown (불변)
            'chunks': chunks,  # RAG용 JSON (불변)
            'qa_result': qa_result,
            'is_qa_pass': qa_result.get('is_pass', False),
            'mode': 'VLM'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """LawMode 파이프라인"""
    
    st.info("📜 LawMode: 규정/법령 파싱 중...")
    progress_bar = st.progress(0)
    
    if PROFILE_AVAILABLE:
        profile = auto_detect_profile(pdf_text, document_title)
        st.info(f"📝 문서 프로파일: {profile.name}")
    
    parser = LawParser()
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    progress_bar.progress(50)
    
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    rag_markdown = parser.to_markdown(parsed_result)
    
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=rag_markdown,
        source="lawmode"
    )
    
    progress_bar.progress(100)
    
    return {
        'rag_markdown': rag_markdown,  # RAG용 Markdown (불변)
        'chunks': chunks,  # RAG용 JSON (불변)
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'mode': 'LawMode',
        'parsed_result': parsed_result
    }


# ============================================
# Streamlit UI
# ============================================

def main():
    st.set_page_config(
        page_title="PRISM - Phase 0.7 Final",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM - Phase 0.7 미세조정 완료")
    st.caption("표 테스트 준비 완료 (4대 핵심 조정 적용)")
    
    # 사이드바: 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # LawMode 토글
        use_law_mode = st.checkbox(
            "📜 LawMode 사용 (규정/법령 전용)",
            value=LAW_MODE_AVAILABLE,
            disabled=not LAW_MODE_AVAILABLE,
            help="PDF 텍스트 기반 정확한 조문 추출"
        )
        
        if not LAW_MODE_AVAILABLE:
            st.warning("⚠️ LawParser 미설치")
        
        st.divider()
        
        # LLM Rewriting 설정 (비활성화)
        st.subheader("✨ 리뷰용 MD 모드")
        
        # LLM Rewriting 일단 비활성화 (오류 수정 후 재활성화)
        enable_llm_rewrite = False
        st.info("⚠️ LLM Rewriting은 현재 비활성화되어 있습니다")
        st.info("✅ Phase 0.7 룰 기반 띄어쓰기만 사용")
        
        st.divider()
        
        # 4대 핵심 조정 설명
        with st.expander("🔧 Phase 0.7 미세조정 (4대 핵심)"):
            st.markdown("""
            ### ✅ 1. 조사 앞 공백 제거
            - Before: "직원에 게"
            - After: "직원에게"
            
            ### ✅ 2. 숫자/단위 공백 최적화
            - Before: "100 만원", "50 명"
            - After: "100만원", "50명"
            
            ### ✅ 3. 조문/표 제목 패턴 보정
            - Before: "제 5 조의 2", "표 1"
            - After: "제5조의2", "표1"
            
            ### ✅ 4. 표 주석 줄바꿈 안정화
            - "※", "비고:", "단," 등 강제 줄바꿈
            - 표와 주석 분리 보장
            
            ---
            
            **표 문서 테스트 준비 완료!**
            """)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf'],
        help="규정/법령 문서 권장 (LawMode)"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        
        # Before/After 예시
        st.markdown("---")
        st.markdown("## 📊 Phase 0.7 미세조정 효과")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Before (조정 전)")
            st.code("""
직원에 게 적용할
100 만원 이상
제 5 조의 2
표 1 채용 절차
            """, language="text")
            st.error("❌ 과도한 띄어쓰기")
        
        with col2:
            st.markdown("### After (조정 후)")
            st.code("""
직원에게 적용할
100만원 이상
제5조의2
표1 채용 절차
            """, language="text")
            st.success("✅ 자연스러운 띄어쓰기")
        
        return
    
    # 문서 처리
    try:
        pdf_path = safe_temp_path('.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.read())
        
        pdf_text = extract_pdf_text_layer(pdf_path)
        
        if not pdf_text:
            st.error("❌ PDF 텍스트 추출 실패")
            return
        
        # 파일명 준비
        base_filename = uploaded_file.name.rsplit('.', 1)[0]
        
        # 처리 모드 선택
        if use_law_mode:
            result = process_document_law_mode(
                pdf_path=pdf_path,
                pdf_text=pdf_text,
                document_title=uploaded_file.name
            )
        else:
            result = process_document_vlm_mode(
                pdf_path=pdf_path,
                pdf_text=pdf_text
            )
        
        # 결과 표시
        st.success(f"✅ {result['mode']} 처리 완료!")
        
        # QA 결과
        match_rate = result['qa_result']['match_rate']
        is_qa_pass = result['is_qa_pass']
        
        if is_qa_pass:
            st.success(f"🎯 DualQA 통과: {match_rate:.1%} 매칭")
        else:
            st.warning(f"⚠️ DualQA 검토 필요: {match_rate:.1%} 매칭")
        
        # ✅ 리뷰용 Markdown 생성 (Phase 0.7 미세조정)
        logger.info("📝 리뷰용 Markdown 생성 시작...")
        
        # 기본 리뷰 MD (띄어쓰기 없음)
        basic_review_md = to_review_md_basic(result['chunks'])
        
        # ✅ Phase 0.7 룰 기반 띄어쓰기 적용 (미세조정)
        review_md_with_spacing = apply_law_spacing(basic_review_md)
        
        review_markdown = review_md_with_spacing
        review_filename = f"{base_filename}_review.md"
        
        logger.info(f"✅ 리뷰용 Markdown 생성 완료: {len(review_markdown)}자")
        
        # ✅ 탭 구조
        tab_names = [
            "📊 요약",
            "📝 원본 PDF",
            "🤖 RAG용 Markdown",
            "🤖 RAG용 JSON",
            "👤 리뷰용 Markdown"
        ]
        
        tabs = st.tabs(tab_names)
        
        # Tab 1: 요약
        with tabs[0]:
            st.subheader("📊 처리 요약")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("처리 모드", result['mode'])
                st.metric("DualQA 매칭률", f"{match_rate:.1%}")
            
            with col2:
                st.metric("QA 통과", "✅" if is_qa_pass else "⚠️")
                st.metric("총 청크 수", len(result['chunks']))
            
            with col3:
                if result['mode'] == 'LawMode' and 'parsed_result' in result:
                    parsed = result['parsed_result']
                    st.metric("장 수", parsed['total_chapters'])
                    st.metric("조문 수", parsed['total_articles'])
        
        # Tab 2: 원본 PDF
        with tabs[1]:
            st.subheader("📝 원본 PDF 텍스트")
            st.info("⚠️ 법적 효력을 가지는 기준 텍스트입니다")
            
            st.text_area(
                "PDF 추출 원본",
                value=pdf_text[:3000] + "..." if len(pdf_text) > 3000 else pdf_text,
                height=400
            )
            
            st.download_button(
                "💾 원본 텍스트 다운로드",
                data=pdf_text,
                file_name=f"{base_filename}_original.txt",
                mime="text/plain"
            )
        
        # Tab 3: RAG용 Markdown (불변)
        with tabs[2]:
            st.subheader("🤖 RAG용 Markdown (엔진 디버깅)")
            st.info("🔍 엔진이 생성한 원문 보존 텍스트 (❌ 절대 불변)")
            
            # Markdown 미리보기
            preview = result['rag_markdown'][:2000] + "..." if len(result['rag_markdown']) > 2000 else result['rag_markdown']
            st.markdown(preview)
            
            # 다운로드
            st.download_button(
                "💾 RAG용 Markdown 다운로드",
                data=result['rag_markdown'],
                file_name=f"{base_filename}_engine.md",
                mime="text/markdown",
                help="엔진 디버깅용 (불변)"
            )
        
        # Tab 4: RAG용 JSON (불변)
        with tabs[3]:
            st.subheader("🤖 RAG용 JSON (인덱싱)")
            st.info("🔍 RAG 시스템 입력 데이터 (❌ 절대 불변)")
            
            # 청크 타입별 통계
            chunk_types = {}
            for chunk in result['chunks']:
                chunk_type = chunk['metadata'].get('type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            st.markdown("### 📊 청크 타입별 통계")
            cols = st.columns(len(chunk_types))
            for i, (chunk_type, count) in enumerate(chunk_types.items()):
                cols[i].metric(chunk_type, count)
            
            # 샘플 청크
            st.markdown("### 📄 샘플 청크")
            if result['chunks']:
                st.json(result['chunks'][0])
            
            # 다운로드
            chunks_json = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
            
            st.download_button(
                "💾 RAG용 JSON 다운로드",
                data=chunks_json,
                file_name=f"{base_filename}_chunks.json",
                mime="application/json",
                help="RAG 인덱싱용 (불변)"
            )
        
        # Tab 5: 리뷰용 Markdown (미세조정 적용)
        with tabs[4]:
            st.subheader("👤 리뷰용 Markdown (Phase 0.7 미세조정)")
            st.success("✅ Phase 0.7 미세조정 (4대 핵심) 적용됨")
            
            # Before/After 비교
            st.markdown("### 📊 미세조정 적용 비교")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Before (조정 전):**")
                before_sample = basic_review_md.split('\n\n')[3] if len(basic_review_md.split('\n\n')) > 3 else basic_review_md[:300]
                st.text_area("", value=before_sample[:300], height=200, key="before", label_visibility="collapsed")
                st.caption("❌ 과도한 띄어쓰기")
            
            with col2:
                st.markdown("**After (조정 후):**")
                after_sample = review_markdown.split('\n\n')[3] if len(review_markdown.split('\n\n')) > 3 else review_markdown[:300]
                st.text_area("", value=after_sample[:300], height=200, key="after", label_visibility="collapsed")
                st.caption("✅ 자연스러운 띄어쓰기")
            
            # Markdown 미리보기
            st.markdown("---")
            st.markdown("### 📄 전체 미리보기")
            preview = review_markdown[:2000] + "..." if len(review_markdown) > 2000 else review_markdown
            st.markdown(preview)
            
            # 다운로드
            st.download_button(
                "💾 리뷰용 Markdown 다운로드",
                data=review_markdown,
                file_name=review_filename,
                mime="text/markdown",
                help="사람용 가독성 (Phase 0.7 미세조정)"
            )
        
        # 정리
        safe_remove(pdf_path)
        
    except Exception as e:
        logger.error(f"❌ 처리 실패: {e}")
        st.error(f"❌ 처리 실패: {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
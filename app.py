"""
app.py - PRISM Phase 0.7.5b Final
Annex Fallback + Review MD 완성

Author: 마창수산팀
Date: 2025-11-16
Version: Phase 0.7.5b
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

# LLM Rewriter Import
try:
    sys.path.insert(0, str(Path(__file__).parent / 'tests'))
    from llm_rewriter import LLMRewriter
    LLM_REWRITER_AVAILABLE = True
    logger.info("✅ LLMRewriter 로드 성공")
except ImportError as e:
    LLM_REWRITER_AVAILABLE = False
    logger.warning(f"⚠️ LLMRewriter 미설치: {e}")


LAW_SPACING_KEYWORDS = [
    "임용", "승진", "보수", "복무", "징계", "퇴직",
    "채용", "인사", "직원", "공사", "수습", "결격사유",
    "규정", "조직", "문화", "역량", "태도", "개선"
]


def apply_law_spacing(text: str) -> str:
    """Phase 0.7 룰 기반 띄어쓰기 (미세조정)"""
    
    logger.info("   ✅ 조문/표 제목 패턴 보정 시작")
    text = re.sub(r"제\s*(\d+)\s*조\s*의\s*(\d+)", r"제\1조의\2", text)
    text = re.sub(r"제\s*(\d+)\s*조", r"제\1조", text)
    text = re.sub(r"표\s*(\d+)", r"표\1", text)
    text = re.sub(r"\[별표\s*(\d+)\]", r"[별표\1]", text)
    logger.info("   ✅ 조문/표 제목 패턴 보정 완료")
    
    logger.info("   ✅ 숫자/단위 공백 최적화 시작")
    text = re.sub(r"(\d+)\s*(만원|억원|천원|원)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*(명|개|건|회|년|월|일)", r"\1\2", text)
    text = re.sub(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", r"\1.\2.\3", text)
    logger.info("   ✅ 숫자/단위 공백 최적화 완료")
    
    logger.info("   ✅ 조사 앞 공백 제거 시작")
    josa_list = ["은", "는", "이", "가", "을", "를", "과", "와", "에", "에서", "에게", "로", "으로"]
    for josa in josa_list:
        text = re.sub(rf"([가-힣]+)\s?{josa}\s?([가-힣])", rf"\1{josa} \2", text)
    logger.info("   ✅ 조사 앞 공백 제거 완료")
    
    logger.info("   ✅ 표 주석 줄바꿈 안정화 시작")
    comment_starters = ["※", "비고:", "주:", "단,", "다만,"]
    for starter in comment_starters:
        escaped = re.escape(starter)
        text = re.sub(rf"([^\n]){escaped}", rf"\1\n{starter}", text)
    logger.info("   ✅ 표 주석 줄바꿈 안정화 완료")
    
    for kw in LAW_SPACING_KEYWORDS:
        text = re.sub(rf"([가-힣0-9]){kw}", rf"\1 {kw}", text)
    
    text = re.sub(r"([\.!?])([가-힣0-9])", r"\1 \2", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)
    
    text = "\n".join(lines)
    
    logger.info("   ✅ Phase 0.7 룰 기반 띄어쓰기 적용 완료")
    
    return text


def to_review_md_basic(
    chunks: list,
    parsed_result: dict = None,
    base_markdown: str = None
) -> str:
    """
    청크/파싱 결과 → 리뷰용 Markdown
    
    ✅ Phase 0.7.5b: LawParser 마크다운 우선
    
    Args:
        chunks: 청크 리스트
        parsed_result: LawParser 파싱 결과
        base_markdown: 이미 생성된 마크다운
    """
    # 1) base_markdown 최우선
    if base_markdown:
        logger.info("   📋 base_markdown 사용")
        return base_markdown
    
    # 2) parsed_result로 LawParser 마크다운 생성
    if parsed_result is not None:
        logger.info("   📋 LawParser 마크다운 생성")
        parser = LawParser()
        return parser.to_markdown(parsed_result)
    
    # 3) 백업: chunks 조합
    logger.info("   📋 chunks 조합 (백업)")
    lines = []
    
    for chunk in chunks:
        content = chunk['content']
        meta = chunk['metadata']
        chunk_type = meta.get('type', '')
        
        if chunk_type == 'title':
            lines.append(f"# {content}")
            lines.append("")
        
        elif chunk_type == 'amendment_history':
            lines.append("## 개정 이력")
            lines.append("")
            lines.append(f"- {content}")
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
            
            body = content.split('\n', 1)[-1] if '\n' in content else content
            lines.append(body)
            lines.append("")
        
        elif chunk_type == 'annex':
            annex_title = meta.get('title', '별표/부록')
            annex_no = meta.get('annex_no')
            
            if annex_no:
                lines.append(f"## [별표 {annex_no}] {annex_title}")
            else:
                lines.append(f"## {annex_title}")
            
            lines.append("")
            lines.append(content)
            lines.append("")
    
    return "\n".join(lines)


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
            'rag_markdown': markdown_text,
            'chunks': chunks,
            'qa_result': qa_result,
            'is_qa_pass': qa_result.get('is_pass', False),
            'mode': 'VLM'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """LawMode 파이프라인 (Phase 0.7.5b)"""
    
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
        'rag_markdown': rag_markdown,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'mode': 'LawMode',
        'parsed_result': parsed_result,
        'base_markdown': rag_markdown
    }


def main():
    st.set_page_config(
        page_title="PRISM - Phase 0.7.5b",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM - Phase 0.7.5b Final")
    st.caption("Annex Fallback + Review MD 완성")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        
        use_law_mode = st.checkbox(
            "📜 LawMode 사용",
            value=LAW_MODE_AVAILABLE,
            disabled=not LAW_MODE_AVAILABLE
        )
        
        if not LAW_MODE_AVAILABLE:
            st.warning("⚠️ LawParser 미설치")
        
        st.divider()
        
        st.subheader("✨ 리뷰용 MD 모드")
        st.info("✅ Phase 0.7 룰 기반 띄어쓰기")
    
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf']
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        return
    
    try:
        pdf_path = safe_temp_path('.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.read())
        
        pdf_text = extract_pdf_text_layer(pdf_path)
        
        if not pdf_text:
            st.error("❌ PDF 텍스트 추출 실패")
            return
        
        base_filename = uploaded_file.name.rsplit('.', 1)[0]
        
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
        
        st.success(f"✅ {result['mode']} 처리 완료!")
        
        match_rate = result['qa_result']['match_rate']
        is_qa_pass = result['is_qa_pass']
        
        if is_qa_pass:
            st.success(f"🎯 DualQA 통과: {match_rate:.1%}")
        else:
            st.warning(f"⚠️ DualQA 검토 필요: {match_rate:.1%}")
        
        # ✅ Phase 0.7.5b: 리뷰용 Markdown 생성
        logger.info("📝 리뷰용 Markdown 생성 시작...")
        
        basic_review_md = to_review_md_basic(
            result.get('chunks', []),
            parsed_result=result.get('parsed_result'),
            base_markdown=result.get('base_markdown')
        )
        
        review_md_with_spacing = apply_law_spacing(basic_review_md)
        
        review_markdown = review_md_with_spacing
        review_filename = f"{base_filename}_review.md"
        
        logger.info(f"✅ 리뷰용 Markdown 생성 완료: {len(review_markdown)}자")
        
        tab_names = [
            "📊 요약",
            "🤖 RAG용 Markdown",
            "🤖 RAG용 JSON",
            "👤 리뷰용 Markdown"
        ]
        
        tabs = st.tabs(tab_names)
        
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
                st.metric("엔진 MD 길이", f"{len(result['rag_markdown'])}자")
                st.metric("리뷰 MD 길이", f"{len(review_markdown)}자")
        
        with tabs[1]:
            st.subheader("🤖 RAG용 Markdown (엔진)")
            st.code(result['rag_markdown'], language="markdown")
            
            st.download_button(
                "💾 RAG용 Markdown 다운로드",
                data=result['rag_markdown'],
                file_name=f"{base_filename}_engine.md",
                mime="text/markdown"
            )
        
        with tabs[2]:
            st.subheader("🤖 RAG용 JSON (청크)")
            st.json(result['chunks'])
            
            st.download_button(
                "💾 청크 JSON 다운로드",
                data=json.dumps(result['chunks'], ensure_ascii=False, indent=2),
                file_name=f"{base_filename}_chunks.json",
                mime="application/json"
            )
        
        with tabs[3]:
            st.subheader("👤 리뷰용 Markdown")
            st.code(review_markdown, language="markdown")
            
            st.download_button(
                "💾 리뷰용 Markdown 다운로드",
                data=review_markdown,
                file_name=review_filename,
                mime="text/markdown"
            )
        
        safe_remove(pdf_path)
        
    except Exception as e:
        logger.error(f"❌ 처리 실패: {e}")
        st.error(f"❌ 처리 실패: {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
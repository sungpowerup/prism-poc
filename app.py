"""
app.py - PRISM Phase 0.8.6 Hotfix
문서 전처리 파이프라인 (다운로드 새로고침 문제 해결)

Phase 0.8.6 핵심 수정:
- ✅ 다운로드 시 새로고침 문제 해결 (st.session_state 활용)
- ✅ 처리 결과를 세션에 저장하여 유지

Author: 마창수산팀
Date: 2025-11-19
Version: Phase 0.8.6 Hotfix
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


LAW_SPACING_KEYWORDS = [
    "임용", "승진", "보수", "복무", "징계", "퇴직",
    "채용", "인사", "직원", "공사", "수습", "결격사유",
    "규정", "조직", "문화", "역량", "태도", "개선"
]


def apply_law_spacing(text: str) -> str:
    """Phase 0.7 룰 기반 띄어쓰기 (미세조정)"""
    
    text = re.sub(r"제\s*(\d+)\s*조\s*의\s*(\d+)", r"제\1조의\2", text)
    text = re.sub(r"제\s*(\d+)\s*조", r"제\1조", text)
    text = re.sub(r"표\s*(\d+)", r"표\1", text)
    text = re.sub(r"\[별표\s*(\d+)\]", r"[별표\1]", text)
    
    text = re.sub(r"(\d+)\s*(만원|억원|천원|원)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*(명|개|건|회|년|월|일)", r"\1\2", text)
    text = re.sub(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", r"\1.\2.\3", text)
    
    josa_list = ["은", "는", "이", "가", "을", "를", "과", "와", "에", "에서", "에게", "로", "으로"]
    for josa in josa_list:
        text = re.sub(rf"([가-힣]+)\s?{josa}\s?([가-힣])", rf"\1{josa} \2", text)
    
    comment_starters = ["※", "비고:", "주:", "단,", "다만,"]
    for starter in comment_starters:
        escaped = re.escape(starter)
        text = re.sub(rf"([^\n]){escaped}", rf"\1\n{starter}", text)
    
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
    
    return text


def to_review_md_basic(
    chunks: list,
    parsed_result: dict = None,
    base_markdown: str = None
) -> str:
    """청크/파싱 결과 → 리뷰용 Markdown"""
    
    if base_markdown:
        return base_markdown
    
    if parsed_result is not None:
        parser = LawParser()
        return parser.to_markdown(parsed_result)
    
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
            lines.append(content)
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
        
        elif chunk_type.startswith('annex'):
            if 'header' in chunk_type:
                lines.append(f"## {content.split(chr(10))[0]}")
            elif 'note' in chunk_type:
                lines.append(content)
            else:
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
            'mode': 'VLM Mode'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """LawMode 파이프라인 (Phase 0.8 Stable)"""
    
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
        source="law"
    )
    
    progress_bar.progress(100)
    
    return {
        'rag_markdown': rag_markdown,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'parsed_result': parsed_result,
        'mode': 'LawMode'
    }


def main():
    """메인 함수"""
    
    st.set_page_config(
        page_title="PRISM Phase 0.8.6",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.8.6")
    st.markdown("**Progressive Reasoning & Intelligence for Structured Materials**")
    st.markdown("**문서 전처리 파이프라인 (Hotfix)**")
    
    # ✅ Phase 0.8.6: 세션 상태 초기화
    if 'processing_result' not in st.session_state:
        st.session_state.processing_result = None
    if 'processed_file_name' not in st.session_state:
        st.session_state.processed_file_name = None
    
    # 메인 영역: 문서 처리
    st.header("📄 문서 처리")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 업로드하세요",
        type=['pdf'],
        help="인사규정, 법령 등 규정 문서"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하면 처리가 시작됩니다.")
        
        # Phase 0.8.6 안내
        st.markdown("---")
        st.subheader("✅ Phase 0.8.6 Hotfix 기능")
        st.success("""
        **개선된 문서 전처리 파이프라인**
        
        - ✅ 페이지 아티팩트 완전 제거 (인사규정 402-2 등)
        - ✅ 개정이력 청크 추가
        - ✅ 장(Chapter) 청크 자동 생성
        - ✅ 다운로드 시 새로고침 문제 해결
        - ✅ DualQA 100% 커버리지 검증
        """)
        
        return
    
    # ✅ Phase 0.8.6: 파일이 바뀌면 결과 초기화
    if st.session_state.processed_file_name != uploaded_file.name:
        st.session_state.processing_result = None
        st.session_state.processed_file_name = uploaded_file.name
    
    # 처리 모드 선택
    mode = st.radio(
        "처리 모드 선택",
        ["LawMode (규정/법령)", "VLM Mode (일반 문서)"],
        help="LawMode: 조문 구조 파싱 | VLM Mode: 이미지 기반 처리"
    )
    
    process_mode = "law" if "LawMode" in mode else "vlm"
    
    # 처리 버튼
    if st.button("🚀 처리 시작", type="primary"):
        try:
            # 임시 파일 저장
            temp_pdf = safe_temp_path(uploaded_file.name)
            with open(temp_pdf, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # PDF 텍스트 추출
            pdf_text = extract_pdf_text_layer(str(temp_pdf))
            
            # 처리 모드 분기
            if process_mode == "law":
                result = process_document_law_mode(
                    str(temp_pdf),
                    pdf_text,
                    uploaded_file.name
                )
            else:
                result = process_document_vlm_mode(
                    str(temp_pdf),
                    pdf_text
                )
            
            # ✅ Phase 0.8.6: 결과를 세션에 저장
            st.session_state.processing_result = result
            
            st.success(f"✅ 처리 완료 ({result['mode']})")
            
        except Exception as e:
            st.error(f"❌ 처리 실패: {e}")
            logger.error(f"❌ 처리 실패: {e}")
            return
    
    # ✅ Phase 0.8.6: 세션에 저장된 결과가 있으면 표시
    if st.session_state.processing_result:
        result = st.session_state.processing_result
        
        # DualQA 결과
        qa_result = result['qa_result']
        if result['is_qa_pass']:
            st.success(f"✅ DualQA 통과 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
        else:
            st.warning(f"⚠️ DualQA 경고 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
        
        # 청크 통계
        st.subheader("📊 청크 통계")
        chunks = result['chunks']
        st.write(f"- 총 청크: {len(chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunks:
            ctype = chunk.get('metadata', {}).get('type', 'unknown')
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            st.write(f"  - {ctype}: {count}개")
        
        # ✅ Phase 0.8.6: 다운로드 버튼 (세션 상태 활용으로 새로고침 방지)
        st.markdown("---")
        st.subheader("📥 결과 다운로드")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📥 engine.md",
                data=result['rag_markdown'],
                file_name="engine.md",
                mime="text/markdown",
                key="download_engine"  # ✅ 고유 키 지정
            )
        
        with col2:
            chunks_json = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 chunks.json",
                data=chunks_json,
                file_name="chunks.json",
                mime="application/json",
                key="download_chunks"  # ✅ 고유 키 지정
            )
        
        with col3:
            # 리뷰용 Markdown 생성
            if 'parsed_result' in result:
                review_md = to_review_md_basic(
                    result['chunks'],
                    parsed_result=result['parsed_result']
                )
            else:
                review_md = to_review_md_basic(
                    result['chunks'],
                    base_markdown=result['rag_markdown']
                )
            
            st.download_button(
                label="📥 review.md",
                data=review_md,
                file_name="review.md",
                mime="text/markdown",
                key="download_review"  # ✅ 고유 키 지정
            )
        
        # 미리보기
        st.markdown("---")
        st.subheader("👀 결과 미리보기")
        
        tab1, tab2, tab3 = st.tabs(["engine.md", "chunks.json", "review.md"])
        
        with tab1:
            st.text_area(
                "engine.md (RAG용)",
                result['rag_markdown'][:3000] + ("..." if len(result['rag_markdown']) > 3000 else ""),
                height=400
            )
        
        with tab2:
            st.json(result['chunks'][:5])  # 처음 5개만 미리보기
            if len(result['chunks']) > 5:
                st.info(f"... 외 {len(result['chunks']) - 5}개 청크")
        
        with tab3:
            if 'parsed_result' in result:
                review_preview = to_review_md_basic(
                    result['chunks'],
                    parsed_result=result['parsed_result']
                )
            else:
                review_preview = result['rag_markdown']
            
            st.text_area(
                "review.md (검토용)",
                review_preview[:3000] + ("..." if len(review_preview) > 3000 else ""),
                height=400
            )


if __name__ == "__main__":
    main()
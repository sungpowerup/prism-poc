"""
PRISM Phase 2 - Streamlit Web App

Phase 2 파이프라인을 위한 웹 인터페이스

Author: 최동현 (Frontend Lead)
Date: 2025-10-12
"""

import streamlit as st
import time
import json
from pathlib import Path
import shutil

# Phase 2 모듈
from core.phase2_pipeline import Phase2Pipeline


# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 2",
    page_icon="🔷",
    layout="wide"
)

# 디렉토리 생성
UPLOAD_DIR = Path("data/uploads")
PROCESSED_DIR = Path("data/processed")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def main():
    """메인 앱"""
    
    # 헤더
    st.title("🔷 PRISM Phase 2")
    st.markdown("**지능형 문서 파싱 및 청킹 플랫폼**")
    
    # 탭
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "⚙️ Process", "📊 Results"])
    
    # Tab 1: 파일 업로드
    with tab1:
        st.header("📤 문서 업로드")
        
        uploaded_file = st.file_uploader(
            "PDF 파일을 선택하세요",
            type=["pdf"],
            help="최대 10MB까지 지원"
        )
        
        if uploaded_file:
            # 파일 저장
            file_path = UPLOAD_DIR / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ 파일 업로드 완료: {uploaded_file.name}")
            st.session_state["uploaded_file"] = str(file_path)
            st.session_state["filename"] = uploaded_file.name
            
            # 파일 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("파일명", uploaded_file.name)
            with col2:
                st.metric("크기", f"{uploaded_file.size / 1024:.1f} KB")
            with col3:
                st.metric("타입", "PDF")
    
    # Tab 2: 처리
    with tab2:
        st.header("⚙️ 문서 처리")
        
        if "uploaded_file" not in st.session_state:
            st.warning("먼저 PDF 파일을 업로드하세요")
            return
        
        # 설정
        col1, col2 = st.columns(2)
        with col1:
            max_pages = st.number_input(
                "처리할 최대 페이지",
                min_value=1,
                max_value=100,
                value=10,
                help="전체 문서를 처리하려면 충분히 큰 값 입력"
            )
        
        with col2:
            vlm_provider = st.selectbox(
                "VLM Provider",
                ["claude", "azure", "ollama"],
                help="이미지 캡션 생성에 사용할 VLM"
            )
        
        # 처리 버튼
        if st.button("🚀 문서 처리 시작", type="primary"):
            process_document(
                st.session_state["uploaded_file"],
                max_pages,
                vlm_provider
            )
    
    # Tab 3: 결과
    with tab3:
        st.header("📊 처리 결과")
        
        if not (PROCESSED_DIR / "chunks.json").exists():
            st.info("처리된 문서가 없습니다")
            return
        
        show_results()


def process_document(pdf_path: str, max_pages: int, vlm_provider: str):
    """문서 처리"""
    
    # 진행 상황
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 파이프라인 초기화
        status_text.text("파이프라인 초기화 중...")
        pipeline = Phase2Pipeline(
            vlm_provider=vlm_provider,
            dpi=200,
            chunk_size=512
        )
        progress_bar.progress(10)
        
        # 문서 처리
        status_text.text("문서 분석 중...")
        result = pipeline.process(pdf_path, max_pages)
        progress_bar.progress(100)
        
        # 결과 저장
        st.session_state["result"] = result
        
        # 성공 메시지
        st.success("✅ 문서 처리 완료!")
        
        # 요약
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("처리 페이지", result["pages_processed"])
        with col2:
            st.metric("텍스트 블록", result["elements"]["text_blocks"])
        with col3:
            st.metric("표", result["elements"]["tables"])
        with col4:
            st.metric("청크", result["chunks"]["total_chunks"])
        
        # 처리 시간
        st.info(f"⏱️ 처리 시간: {result['processing_time']:.1f}초")
        
    except Exception as e:
        st.error(f"❌ 처리 실패: {e}")
        import traceback
        with st.expander("에러 상세"):
            st.code(traceback.format_exc())


def show_results():
    """결과 표시"""
    
    # chunks.json 로드
    chunks_path = PROCESSED_DIR / "chunks.json"
    with open(chunks_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    chunks = data.get("chunks", [])
    statistics = data.get("statistics", {})
    
    # 통계
    st.subheader("📈 통계")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 청크", statistics.get("total_chunks", 0))
    with col2:
        st.metric("텍스트 청크", statistics.get("text_chunks", 0))
    with col3:
        st.metric("표 청크", statistics.get("table_chunks", 0))
    with col4:
        st.metric("이미지 청크", statistics.get("image_chunks", 0))
    
    # 청크 목록
    st.subheader("📄 청크 목록")
    
    # 필터
    chunk_type = st.selectbox(
        "청크 타입",
        ["all", "text", "table", "image"]
    )
    
    # 필터링
    filtered_chunks = chunks
    if chunk_type != "all":
        filtered_chunks = [c for c in chunks if c["type"] == chunk_type]
    
    st.info(f"표시 중: {len(filtered_chunks)} / {len(chunks)} 청크")
    
    # 청크 표시
    for i, chunk in enumerate(filtered_chunks[:50]):  # 최대 50개
        with st.expander(f"[{chunk['type'].upper()}] {chunk['chunk_id']} (Page {chunk['page_num']})"):
            st.markdown("**Content:**")
            st.text_area(
                f"chunk_{i}",
                chunk["content"],
                height=150,
                key=f"chunk_content_{i}",
                label_visibility="collapsed"
            )
            
            st.markdown("**Metadata:**")
            st.json(chunk["metadata"])
            
            if chunk.get("has_embedding"):
                st.info("✅ 임베딩 포함")
    
    if len(filtered_chunks) > 50:
        st.warning(f"⚠️ 처음 50개만 표시됨 ({len(filtered_chunks) - 50}개 더 있음)")
    
    # 다운로드
    st.subheader("💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # chunks.json 다운로드
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks_json = f.read()
        
        st.download_button(
            "📥 chunks.json 다운로드",
            chunks_json,
            file_name="chunks.json",
            mime="application/json"
        )
    
    with col2:
        # report.md 다운로드 (있으면)
        report_path = PROCESSED_DIR / "report.md"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report_md = f.read()
            
            st.download_button(
                "📥 report.md 다운로드",
                report_md,
                file_name="report.md",
                mime="text/markdown"
            )


if __name__ == "__main__":
    main()
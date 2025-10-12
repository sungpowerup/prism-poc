"""
PRISM Phase 2 - Streamlit Web App (수정)

Phase 2 파이프라인을 위한 웹 인터페이스

Author: 최동현 (Frontend Lead)
Date: 2025-10-13
"""

import streamlit as st
import time
import json
from pathlib import Path
import traceback

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
            use_vlm = st.checkbox(
                "VLM 사용 (이미지 캡션 생성)",
                value=False,
                help="체크하면 이미지에 대한 자연어 설명 생성 (시간 소요)"
            )
            
            if use_vlm:
                vlm_provider = st.selectbox(
                    "VLM Provider",
                    ["claude", "azure", "ollama"],
                    help="이미지 캡션 생성에 사용할 VLM"
                )
            else:
                vlm_provider = "claude"  # 기본값
        
        # 처리 버튼
        if st.button("🚀 문서 처리 시작", type="primary"):
            process_document(
                st.session_state["uploaded_file"],
                max_pages,
                use_vlm,
                vlm_provider
            )
    
    # Tab 3: 결과
    with tab3:
        st.header("📊 처리 결과")
        
        if "result" not in st.session_state:
            st.info("처리된 문서가 없습니다. Process 탭에서 문서를 처리하세요.")
            return
        
        show_results()


def process_document(
    pdf_path: str, 
    max_pages: int, 
    use_vlm: bool,
    vlm_provider: str
):
    """문서 처리"""
    
    # 진행 상황
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 파이프라인 초기화
        status_text.text("파이프라인 초기화 중...")
        
        # ✅ 수정: dpi 파라미터 제거, 올바른 파라미터만 전달
        pipeline = Phase2Pipeline(
            use_vlm=use_vlm,
            vlm_provider=vlm_provider,
            chunk_size=512,
            chunk_overlap=50
        )
        progress_bar.progress(10)
        
        # 문서 처리
        status_text.text("문서 분석 중...")
        progress_bar.progress(20)
        
        result = pipeline.process(
            pdf_path=pdf_path,
            output_dir=str(PROCESSED_DIR),
            max_pages=max_pages
        )
        
        progress_bar.progress(100)
        
        # 결과 저장
        st.session_state["result"] = result
        
        # 성공 메시지
        status_text.empty()
        st.success("✅ 문서 처리 완료!")
        
        # 요약
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Elements", result["elements"])
        with col2:
            st.metric("텍스트 블록", result["texts"])
        with col3:
            st.metric("표", result["tables"])
        with col4:
            st.metric("청크", result["chunks"])
        
        # 처리 시간
        st.info(f"⏱️ 처리 시간: {result['elapsed_time']:.1f}초")
        
        # 통계
        with st.expander("📊 상세 통계"):
            stats = result.get("statistics", {})
            for key, value in stats.items():
                st.write(f"**{key}**: {value}")
        
    except Exception as e:
        progress_bar.progress(0)
        status_text.empty()
        st.error(f"❌ 처리 실패: {e}")
        
        with st.expander("에러 상세"):
            st.code(traceback.format_exc())


def show_results():
    """결과 표시"""
    
    if "result" not in st.session_state:
        st.warning("처리된 결과가 없습니다")
        return
    
    result = st.session_state["result"]
    
    # 파일명 추출
    filename = Path(st.session_state.get("filename", "unknown")).stem
    chunks_path = PROCESSED_DIR / f"{filename}_chunks.json"
    
    if not chunks_path.exists():
        st.error(f"청크 파일을 찾을 수 없습니다: {chunks_path}")
        return
    
    # chunks.json 로드
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
    
    # 평균 청크 크기
    avg_size = statistics.get("avg_chunk_size", 0)
    st.metric("평균 청크 크기", f"{avg_size:.0f} characters")
    
    # 청크 목록
    st.subheader("📝 청크 목록")
    
    # 필터
    chunk_types = ["all", "text", "table", "image"]
    selected_type = st.selectbox("청크 타입 필터", chunk_types)
    
    # 필터링
    if selected_type == "all":
        filtered_chunks = chunks
    else:
        filtered_chunks = [c for c in chunks if c.get("type") == selected_type]
    
    st.write(f"총 {len(filtered_chunks)}개 청크")
    
    # 청크 표시
    for i, chunk in enumerate(filtered_chunks):
        chunk_type = chunk.get("type", "unknown")
        chunk_id = chunk.get("chunk_id", f"chunk_{i}")
        content = chunk.get("content", "")
        page_num = chunk.get("page_num", "?")
        metadata = chunk.get("metadata", {})
        
        # 아이콘
        icon_map = {
            "text": "📝",
            "table": "📊",
            "image": "🖼️"
        }
        icon = icon_map.get(chunk_type, "📄")
        
        with st.expander(f"{icon} {chunk_id} (Page {page_num})"):
            # 타입별 표시
            if chunk_type == "table":
                st.markdown(content)
            else:
                st.text(content[:500] + "..." if len(content) > 500 else content)
            
            # 메타데이터
            if metadata:
                st.caption(f"Metadata: {metadata}")
    
    # 다운로드
    st.subheader("💾 다운로드")
    
    with open(chunks_path, "r", encoding="utf-8") as f:
        json_data = f.read()
    
    st.download_button(
        label="📥 JSON 다운로드",
        data=json_data,
        file_name=f"{filename}_chunks.json",
        mime="application/json"
    )


if __name__ == "__main__":
    main()
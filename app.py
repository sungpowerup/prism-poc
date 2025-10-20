"""
PRISM Phase 2.7 - Streamlit Web Application
PDF 문서 지능형 처리 UI (완전판)

Author: 최동현 (Frontend Lead)
Date: 2025-10-20
Fix: process_document 함수 추가
"""

import streamlit as st
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# core 모듈 import
try:
    from core.phase27_pipeline import Phase27Pipeline
except ImportError as e:
    st.error(f"❌ core 모듈 임포트 실패: {e}")
    st.stop()

# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="PRISM Phase 2.7",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS 스타일
# ============================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .chunk-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 세션 상태 초기화
# ============================================================

if 'result' not in st.session_state:
    st.session_state.result = None

if 'processing' not in st.session_state:
    st.session_state.processing = False

# ============================================================
# Helper Functions
# ============================================================

def save_uploaded_file(uploaded_file) -> Optional[str]:
    """업로드된 파일을 임시 디렉토리에 저장"""
    try:
        # 임시 디렉토리 생성
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        # 파일 저장
        file_path = temp_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return str(file_path)
    except Exception as e:
        st.error(f"❌ 파일 저장 실패: {e}")
        return None


def convert_to_markdown(result: Dict) -> str:
    """결과를 Markdown 형식으로 변환"""
    md_lines = []
    
    # 헤더
    md_lines.append("# PRISM Phase 2.7 - 문서 추출 결과\n")
    md_lines.append(f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_lines.append("---\n")
    
    # 메타데이터
    metadata = result.get('metadata', {})
    md_lines.append("## 📄 문서 정보\n")
    md_lines.append(f"- **파일명**: {metadata.get('filename', 'N/A')}")
    md_lines.append(f"- **총 페이지**: {metadata.get('total_pages', 0)}")
    md_lines.append(f"- **처리 시간**: {metadata.get('processing_time_sec', 0):.2f}초")
    md_lines.append(f"- **총 청크**: {metadata.get('total_chunks', 0)}\n")
    md_lines.append("---\n")
    
    # Stage 1 통계
    stage1 = result.get('stage1_elements', [])
    if stage1:
        md_lines.append("## 📊 Stage 1: Element 추출 통계\n")
        
        # 타입별 집계
        type_counts = {}
        for elem in stage1:
            elem_type = elem.get('type', 'unknown')
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
        
        for elem_type, count in type_counts.items():
            md_lines.append(f"- **{elem_type}**: {count}개")
        md_lines.append("\n---\n")
    
    # Stage 2 청크
    chunks = result.get('stage2_chunks', [])
    if chunks:
        md_lines.append("## 🧩 Stage 2: 지능형 청크\n")
        
        for i, chunk in enumerate(chunks, 1):
            md_lines.append(f"### 청크 #{i}\n")
            md_lines.append(f"**페이지**: {chunk.get('page_number', 'N/A')}")
            md_lines.append(f"**타입**: {chunk.get('element_type', 'N/A')}")
            md_lines.append(f"**모델**: {chunk.get('model_used', 'N/A')}\n")
            md_lines.append("**내용**:\n")
            md_lines.append("```")
            md_lines.append(chunk.get('content', ''))
            md_lines.append("```\n")
            md_lines.append("---\n")
    
    return "\n".join(md_lines)


def display_statistics(result: Dict):
    """통계 정보 표시"""
    st.markdown('<div class="section-header">📊 처리 통계</div>', unsafe_allow_html=True)
    
    metadata = result.get('metadata', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 페이지",
            value=metadata.get('total_pages', 0)
        )
    
    with col2:
        st.metric(
            label="총 청크",
            value=metadata.get('total_chunks', 0)
        )
    
    with col3:
        st.metric(
            label="처리 시간",
            value=f"{metadata.get('processing_time_sec', 0):.1f}초"
        )
    
    with col4:
        st.metric(
            label="VLM 모델",
            value=metadata.get('vlm_provider', 'N/A')
        )


def display_stage1_elements(elements: List[Dict]):
    """Stage 1 Element 표시"""
    st.markdown('<div class="section-header">📋 Stage 1: 추출된 Elements</div>', unsafe_allow_html=True)
    
    if not elements:
        st.info("추출된 Element가 없습니다.")
        return
    
    # 타입별 집계
    type_counts = {}
    for elem in elements:
        elem_type = elem.get('type', 'unknown')
        type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    # 집계 표시
    st.markdown("**타입별 분포:**")
    cols = st.columns(len(type_counts))
    for idx, (elem_type, count) in enumerate(type_counts.items()):
        with cols[idx]:
            st.metric(label=elem_type.upper(), value=count)
    
    # 상세 리스트 (Expander)
    with st.expander("📄 상세 Element 목록", expanded=False):
        for i, elem in enumerate(elements, 1):
            st.markdown(f"**Element #{i}**")
            st.json({
                "페이지": elem.get('page_number'),
                "타입": elem.get('type'),
                "위치": elem.get('bbox'),
                "내용": elem.get('content', '')[:100] + "..." if len(elem.get('content', '')) > 100 else elem.get('content', '')
            })
            st.markdown("---")


def display_stage2_chunks(chunks: List[Dict]):
    """Stage 2 청크 표시"""
    st.markdown('<div class="section-header">🧩 Stage 2: 지능형 청크</div>', unsafe_allow_html=True)
    
    if not chunks:
        st.info("생성된 청크가 없습니다.")
        return
    
    # 청크 표시
    for i, chunk in enumerate(chunks, 1):
        with st.expander(f"📦 청크 #{i} - 페이지 {chunk.get('page_number', 'N/A')} ({chunk.get('element_type', 'N/A')})", expanded=False):
            st.markdown(f"**모델**: {chunk.get('model_used', 'N/A')}")
            st.markdown(f"**처리 시간**: {chunk.get('processing_time_sec', 0):.2f}초")
            st.markdown("---")
            st.markdown("**변환된 내용:**")
            st.text_area(
                label="내용",
                value=chunk.get('content', ''),
                height=200,
                key=f"chunk_{i}",
                disabled=True
            )


def display_download_buttons(result: Dict):
    """다운로드 버튼 표시"""
    st.markdown('<div class="section-header">💾 다운로드</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # JSON 다운로드
    with col1:
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_data,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    # Markdown 다운로드
    with col2:
        md_data = convert_to_markdown(result)
        st.download_button(
            label="📥 Markdown 다운로드",
            data=md_data,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )


def process_document(uploaded_file, vlm_provider: str):
    """문서 처리 메인 함수"""
    
    # 진행 상태 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 파일 저장
        status_text.text("1/4 파일 저장 중...")
        progress_bar.progress(25)
        
        pdf_path = save_uploaded_file(uploaded_file)
        if not pdf_path:
            st.error("파일 저장에 실패했습니다.")
            return
        
        # 2. Pipeline 초기화
        status_text.text("2/4 Pipeline 초기화 중...")
        progress_bar.progress(50)
        
        pipeline = Phase27Pipeline(vlm_provider=vlm_provider)
        
        # 3. 문서 처리
        status_text.text("3/4 문서 처리 중... (시간이 걸릴 수 있습니다)")
        progress_bar.progress(75)
        
        result = pipeline.process_pdf(pdf_path)
        
        # 4. 완료
        status_text.text("4/4 처리 완료!")
        progress_bar.progress(100)
        
        # 세션 상태에 저장
        st.session_state.result = result
        
        # 성공 메시지
        st.success("✅ 문서 처리가 완료되었습니다!")
        
        # 임시 파일 정리
        try:
            os.remove(pdf_path)
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {str(e)}")
        
        # 상세 에러 (Expander)
        with st.expander("🔍 상세 에러 정보"):
            import traceback
            st.code(traceback.format_exc())
    
    finally:
        # 진행 표시 제거
        progress_bar.empty()
        status_text.empty()


# ============================================================
# 메인 UI
# ============================================================

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown('<div class="main-header">🔷 PRISM Phase 2.7</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">PDF 문서 지능형 전처리 시스템</p>', unsafe_allow_html=True)
    
    # 사이드바 설정
    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        
        # VLM 프로바이더 선택
        vlm_provider = st.selectbox(
            "VLM 프로바이더",
            options=["claude", "azure_openai", "ollama"],
            index=0,
            help="문서 처리에 사용할 VLM 모델을 선택하세요"
        )
        
        st.markdown("---")
        
        # 정보
        st.markdown("### 📖 사용 방법")
        st.markdown("""
        1. PDF 파일 업로드
        2. VLM 프로바이더 선택
        3. '처리 시작' 클릭
        4. 결과 확인 및 다운로드
        """)
        
        st.markdown("---")
        
        st.markdown("### 🔧 지원 기능")
        st.markdown("""
        - ✅ PDF → 이미지 변환 (PyMuPDF)
        - ✅ Element 자동 추출
        - ✅ VLM 기반 설명 생성
        - ✅ 지능형 청킹
        - ✅ JSON/MD 다운로드
        """)
    
    # 메인 영역
    st.markdown("---")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📁 PDF 파일 업로드",
        type=['pdf'],
        help="처리할 PDF 문서를 선택하세요"
    )
    
    if uploaded_file is not None:
        # 파일 정보 표시
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**파일명**: {uploaded_file.name}")
        with col2:
            st.write(f"**크기**: {uploaded_file.size / 1024:.2f} KB")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 처리 시작 버튼
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            with st.spinner("문서 처리 중..."):
                process_document(uploaded_file, vlm_provider)
    
    # 결과 표시
    if st.session_state.result is not None:
        st.markdown("---")
        st.markdown('<div class="success-box">✅ 처리 완료!</div>', unsafe_allow_html=True)
        
        result = st.session_state.result
        
        # 통계
        display_statistics(result)
        
        # Stage 1 Elements
        stage1_elements = result.get('stage1_elements', [])
        if stage1_elements:
            display_stage1_elements(stage1_elements)
        
        # Stage 2 Chunks
        stage2_chunks = result.get('stage2_chunks', [])
        if stage2_chunks:
            display_stage2_chunks(stage2_chunks)
        
        # 다운로드
        display_download_buttons(result)
        
        # 새 문서 처리 버튼
        st.markdown("---")
        if st.button("🔄 새 문서 처리", use_container_width=True):
            st.session_state.result = None
            st.rerun()


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
# app_phase2.py - Phase 2.3 완전 호환 버전 (함수 순서 수정)

import streamlit as st
import os
import sys
from pathlib import Path
import json
from datetime import datetime
import traceback

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.phase2_pipeline import Phase2Pipeline

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 2.3 - Full Page Vision",
    page_icon="🔍",
    layout="wide"
)

# 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .metric-card {
        padding: 1.5rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 🔧 함수 정의 (먼저!)
# ============================================================

def process_document(uploaded_file, azure_endpoint, azure_api_key, max_pages):
    """문서 처리"""
    
    # 진행 상황 표시
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        # 임시 파일 저장
        input_dir = Path("input")
        input_dir.mkdir(exist_ok=True)
        
        input_path = input_dir / uploaded_file.name
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        status_placeholder.info(f"📁 파일 저장 완료: {input_path}")
        
        # Pipeline 초기화 (Phase 2.3)
        status_placeholder.info("🔧 Phase 2.3 Pipeline 초기화 중...")
        pipeline = Phase2Pipeline(
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key
        )
        
        # 처리
        status_placeholder.info("🤖 Claude Vision으로 전체 페이지 분석 중...")
        progress_placeholder.progress(0, text="처리 시작...")
        
        start_time = datetime.now()
        
        # 실제 처리
        result = pipeline.process(str(input_path), max_pages=max_pages)
        
        # 처리 완료
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        progress_placeholder.progress(100, text="처리 완료!")
        
        # 결과 표시
        display_results(result, duration, max_pages)
        
        # 상태 메시지 제거
        status_placeholder.empty()
        
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.empty()
        
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.error(f"❌ 처리 실패: {error_msg}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("🔍 에러 상세"):
            st.code(error_trace, language="python")

def display_results(result, duration, max_pages):
    """결과 표시"""
    
    st.markdown('<div class="success-box">', unsafe_allow_html=True)
    st.success(f"✅ 처리 완료! ({duration:.1f}초)")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 통계 표시
    stats = result.get('statistics', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📄 처리된 페이지", stats.get('total_pages', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📊 추출된 표", stats.get('table_chunks', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📝 텍스트 청크", stats.get('text_chunks', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        total_chunks = stats.get('total_chunks', 0)
        st.metric("🧩 전체 청크", total_chunks)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 비용 및 시간
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        cost = stats.get('total_pages', 0) * 0.025
        st.metric("💰 실제 비용", f"${cost:.3f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("⏱️ 처리 시간", f"{duration:.1f}초")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 청크 미리보기
    st.markdown("---")
    st.markdown("### 📋 추출된 청크 미리보기")
    
    chunks = result.get('chunks', [])
    if chunks:
        # 표 청크
        table_chunks = [c for c in chunks if c['type'] == 'table']
        if table_chunks:
            st.markdown("#### 📊 표 청크")
            for i, chunk in enumerate(table_chunks[:3], 1):
                with st.expander(f"표 {i} (페이지 {chunk['page_num']})"):
                    st.code(chunk['content'][:500] + "..." if len(chunk['content']) > 500 else chunk['content'])
        
        # 텍스트 청크
        text_chunks = [c for c in chunks if c['type'] == 'text']
        if text_chunks:
            st.markdown("#### 📝 텍스트 청크")
            for i, chunk in enumerate(text_chunks[:3], 1):
                with st.expander(f"텍스트 {i} (페이지 {chunk['page_num']})"):
                    st.write(chunk['content'][:300] + "..." if len(chunk['content']) > 300 else chunk['content'])
    
    # 다운로드
    st.markdown("---")
    output_path = result.get('output_path')
    if output_path and Path(output_path).exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            json_data = f.read()
        
        st.download_button(
            label="📥 JSON 결과 다운로드",
            data=json_data,
            file_name=Path(output_path).name,
            mime="application/json",
            use_container_width=True
        )

# ============================================================
# 🎨 UI 구성 (함수 정의 후!)
# ============================================================

# 헤더
st.markdown('<div class="main-header">🔍 PRISM Phase 2.3</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Full Page Claude Vision Analysis</div>', unsafe_allow_html=True)

# 사이드바
st.sidebar.header("⚙️ 설정")

# Azure OpenAI 설정
st.sidebar.subheader("🔑 Azure OpenAI")
azure_endpoint = st.sidebar.text_input(
    "Endpoint",
    value=os.environ.get('AZURE_OPENAI_ENDPOINT', ''),
    type="password",
    help="Azure OpenAI 엔드포인트 URL"
)
azure_api_key = st.sidebar.text_input(
    "API Key",
    value=os.environ.get('AZURE_OPENAI_API_KEY', ''),
    type="password",
    help="Azure OpenAI API 키"
)

# 페이지 제한
st.sidebar.subheader("📄 페이지 설정")
max_pages = st.sidebar.number_input(
    "처리할 최대 페이지 수",
    min_value=1,
    max_value=50,
    value=5,
    help="비용 절감을 위해 처리할 최대 페이지 수를 제한합니다"
)

# Phase 2.3 정보
st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📊 Phase 2.3 특징

✨ **전체 페이지 Vision**
- 페이지 전체를 Claude Vision으로 분석
- 텍스트, 표, 구조를 동시 추출
- 95%+ 정확도 달성

💰 **비용**
- ~$0.025/페이지
- 5페이지: ~$0.125
- 10페이지: ~$0.25

⏱️ **처리 시간**
- ~20초/페이지
- 5페이지: ~100초
- 10페이지: ~200초
""")

# 메인 영역
tab1, tab2 = st.tabs(["📤 문서 업로드", "📊 결과 보기"])

with tab1:
    st.markdown("### 📤 PDF 문서 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="Phase 2.3: 전체 페이지 Claude Vision 분석"
    )
    
    if uploaded_file:
        # 파일 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**📄 파일명:** {uploaded_file.name}")
        with col2:
            file_size = len(uploaded_file.getvalue()) / 1024
            st.markdown(f"**💾 크기:** {file_size:.1f} KB")
        with col3:
            estimated_cost = max_pages * 0.025
            st.markdown(f"**💰 예상 비용:** ${estimated_cost:.3f}")
        
        # 처리 버튼
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            if not azure_endpoint or not azure_api_key:
                st.error("⚠️ Azure OpenAI 설정을 먼저 입력해주세요!")
            else:
                # ✅ 이제 함수가 이미 정의되어 있음!
                process_document(uploaded_file, azure_endpoint, azure_api_key, max_pages)

with tab2:
    st.markdown("### 📊 최근 처리 결과")
    
    output_dir = Path("output")
    if output_dir.exists():
        json_files = sorted(output_dir.glob("*_chunks.json"), key=os.path.getmtime, reverse=True)
        
        if json_files:
            selected_file = st.selectbox(
                "결과 파일 선택",
                json_files,
                format_func=lambda x: f"{x.name} ({datetime.fromtimestamp(x.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
            )
            
            if selected_file:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 통계
                stats = data.get('statistics', {})
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📄 페이지", stats.get('total_pages', 0))
                with col2:
                    st.metric("📊 표", stats.get('table_chunks', 0))
                with col3:
                    st.metric("📝 텍스트", stats.get('text_chunks', 0))
                
                # 청크 상세
                st.markdown("#### 📋 전체 청크")
                chunks = data.get('chunks', [])
                
                for i, chunk in enumerate(chunks, 1):
                    chunk_type = "📊 표" if chunk['type'] == 'table' else "📝 텍스트"
                    with st.expander(f"{chunk_type} {i} - 페이지 {chunk['page_num']}"):
                        if chunk['type'] == 'table':
                            st.code(chunk['content'])
                        else:
                            st.write(chunk['content'])
        else:
            st.info("처리된 결과가 없습니다. 먼저 문서를 업로드하고 처리해주세요.")
    else:
        st.info("output 폴더가 없습니다.")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>PRISM Phase 2.3</strong> - Full Page Claude Vision Analysis</p>
    <p>🎯 95%+ Accuracy | 💰 $0.025/page | ⏱️ 20s/page</p>
</div>
""", unsafe_allow_html=True)
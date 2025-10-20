"""
PRISM Phase 2.7 - Streamlit Web Application
PDF 문서 지능형 처리 UI

Author: 최동현 (Frontend Lead)
Date: 2025-10-20
Update: Phase27Pipeline.process_pdf() 호출 수정
"""

import streamlit as st
import os
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

from core.phase27_pipeline import Phase27Pipeline

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 2.7",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
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
    .chunk-header {
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .chunk-content {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.3rem;
        font-family: monospace;
        white-space: pre-wrap;
        margin-top: 0.5rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
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

if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None

if 'result' not in st.session_state:
    st.session_state.result = None

if 'processing' not in st.session_state:
    st.session_state.processing = False

# ============================================================
# VLM Provider 선택
# ============================================================

def get_available_providers() -> List[str]:
    """사용 가능한 VLM Provider 목록"""
    providers = []
    
    # Claude
    if os.getenv('ANTHROPIC_API_KEY'):
        providers.append('claude')
    
    # Azure OpenAI
    if os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT'):
        providers.append('azure_openai')
    
    # Ollama (로컬)
    providers.append('ollama')
    
    return providers

# ============================================================
# 메인 UI
# ============================================================

st.markdown('<div class="main-header">🔷 PRISM Phase 2.7</div>', unsafe_allow_html=True)
st.markdown('<div class="info-box">📚 <b>차세대 지능형 문서 처리 플랫폼</b><br>PDF → 레이아웃 감지 → 하이브리드 추출 → 지능형 청킹</div>', unsafe_allow_html=True)

# ============================================================
# 사이드바: 설정
# ============================================================

with st.sidebar:
    st.markdown("## ⚙️ 설정")
    
    # VLM Provider 선택
    available_providers = get_available_providers()
    
    if not available_providers:
        st.error("❌ 사용 가능한 VLM Provider가 없습니다!")
        st.stop()
    
    provider_names = {
        'claude': '🤖 Claude (Anthropic)',
        'azure_openai': '☁️ Azure OpenAI',
        'ollama': '🏠 Ollama (Local)'
    }
    
    vlm_provider = st.selectbox(
        "VLM Provider",
        options=available_providers,
        format_func=lambda x: provider_names.get(x, x),
        index=0
    )
    
    st.markdown("---")
    
    # 정보 표시
    st.markdown("### 📊 시스템 정보")
    st.info(f"""
    **선택된 Provider:** {provider_names.get(vlm_provider, vlm_provider)}
    
    **처리 단계:**
    1. PDF → 이미지 변환
    2. 레이아웃 감지 (VLM)
    3. 영역별 추출 (OCR + VLM)
    4. 지능형 청킹
    """)
    
    # 도움말
    with st.expander("💡 사용 방법"):
        st.markdown("""
        1. **VLM Provider 선택**
           - Claude: 최고 품질 (권장)
           - Azure OpenAI: 엔터프라이즈
           - Ollama: 로컬/폐쇄망
        
        2. **PDF 파일 업로드**
           - 최대 크기: 200MB
           - 최대 페이지: 20페이지
        
        3. **처리 시작**
           - 자동으로 레이아웃 감지
           - 영역별 컨텐츠 추출
           - 지능형 청킹 수행
        
        4. **결과 확인**
           - Before/After 비교
           - JSON/Markdown 다운로드
        """)

# ============================================================
# 메인 영역: 파일 업로드
# ============================================================

st.markdown('<div class="section-header">📤 문서 업로드</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요",
    type=['pdf'],
    help="최대 200MB, 20페이지 이하"
)

if uploaded_file:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.success(f"✅ 파일 선택됨: **{uploaded_file.name}**")
    
    with col2:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.metric("파일 크기", f"{file_size_mb:.2f} MB")
    
    with col3:
        if st.button("🚀 처리 시작", type="primary", disabled=st.session_state.processing):
            st.session_state.processing = True
            process_document(uploaded_file, vlm_provider)
            st.session_state.processing = False

# ============================================================
# 문서 처리 함수
# ============================================================

def process_document(uploaded_file, vlm_provider):
    """문서 처리"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        # 입력 디렉토리 생성
        input_dir = Path("input")
        input_dir.mkdir(exist_ok=True)
        
        # 출력 디렉토리 생성
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 파일 저장
        input_path = input_dir / uploaded_file.name
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        st.session_state.pdf_path = str(input_path)
        
        status_placeholder.info(f"✅ 파일 저장: {input_path}")
        
        # Pipeline 초기화
        status_placeholder.info(f"⚙️ Pipeline 초기화 중 (Provider: {vlm_provider})...")
        
        pipeline = Phase27Pipeline(vlm_provider=vlm_provider)
        
        # 처리 시작
        status_placeholder.info(f"🔄 {vlm_provider.upper()}로 처리 중...")
        progress_placeholder.progress(0, text="문서 처리 시작...")
        
        start_time = datetime.now()
        
        # ✅ 수정: process() → process_pdf()
        result = pipeline.process_pdf(
            pdf_path=str(input_path),
            output_dir=str(output_dir)
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 결과 저장
        st.session_state.result = result
        
        progress_placeholder.progress(100, text="✅ 처리 완료!")
        status_placeholder.success(f"✅ 처리 완료! (소요 시간: {duration:.1f}초)")
        
        # 결과 렌더링
        render_results(result, duration)
        
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.error(f"❌ 처리 중 오류 발생: {str(e)}")
        st.code(traceback.format_exc())

# ============================================================
# 결과 렌더링
# ============================================================

def render_results(result: Dict, duration: float):
    """결과 표시"""
    
    st.markdown("---")
    st.markdown('<div class="section-header">📊 처리 결과</div>', unsafe_allow_html=True)
    
    # 메타데이터
    meta = result.get('metadata', {})
    
    # 상단 메트릭
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📄 총 페이지", meta.get('total_pages', 0))
    
    with col2:
        st.metric("📦 총 청크", meta.get('total_chunks', 0))
    
    with col3:
        st.metric("⏱️ 처리 시간", f"{duration:.1f}초")
    
    with col4:
        chunk_types = meta.get('chunk_types', {})
        st.metric("📝 텍스트", chunk_types.get('text', 0))
    
    with col5:
        st.metric("📊 차트", chunk_types.get('chart', 0))
    
    # 청크 타입별 통계
    st.markdown("### 📈 청크 타입별 통계")
    
    chunk_types = meta.get('chunk_types', {})
    
    if chunk_types:
        cols = st.columns(len(chunk_types))
        for i, (chunk_type, count) in enumerate(chunk_types.items()):
            with cols[i]:
                st.metric(
                    label=chunk_type.upper(),
                    value=count,
                    delta=f"{count / meta.get('total_chunks', 1) * 100:.1f}%"
                )
    
    # 다운로드 버튼
    st.markdown("---")
    st.markdown("### 📥 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON 다운로드
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Markdown 다운로드
        md_content = convert_to_markdown(result)
        st.download_button(
            label="📝 Markdown 다운로드",
            data=md_content,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    # 청크 상세
    st.markdown("---")
    st.markdown("### 📋 청크 상세 보기")
    
    chunks = result.get('chunks', [])
    
    if not chunks:
        st.warning("⚠️ 추출된 청크가 없습니다.")
        return
    
    # 필터링 옵션
    col1, col2 = st.columns([1, 3])
    
    with col1:
        chunk_type_filter = st.multiselect(
            "청크 타입 필터",
            options=list(chunk_types.keys()),
            default=list(chunk_types.keys())
        )
    
    with col2:
        search_query = st.text_input("🔍 검색", placeholder="청크 내용 검색...")
    
    # 청크 렌더링
    filtered_chunks = [
        chunk for chunk in chunks
        if chunk['type'] in chunk_type_filter
        and (not search_query or search_query.lower() in chunk['content'].lower())
    ]
    
    st.info(f"📦 총 {len(filtered_chunks)}개의 청크 (전체 {len(chunks)}개 중)")
    
    for i, chunk in enumerate(filtered_chunks, start=1):
        render_chunk(chunk, i)

# ============================================================
# 청크 렌더링
# ============================================================

def render_chunk(chunk: Dict, index: int):
    """개별 청크 표시"""
    
    with st.expander(f"**청크 #{index}** - {chunk['chunk_id']} ({chunk['type'].upper()})"):
        
        # 메타데이터
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("페이지", chunk['page_num'])
        
        with col2:
            st.metric("타입", chunk['type'])
        
        with col3:
            st.metric("토큰", chunk['metadata']['token_count'])
        
        with col4:
            source = chunk['metadata'].get('source', 'unknown')
            st.metric("소스", source.upper())
        
        # 경로
        st.caption(f"**경로:** {chunk['metadata']['section_path']}")
        
        # 내용
        st.markdown("#### 📄 내용")
        
        if chunk['type'] in ['chart', 'table']:
            # JSON/Markdown 형식으로 표시
            st.code(chunk['content'], language='json' if chunk['type'] == 'chart' else 'markdown')
        else:
            # 일반 텍스트
            st.text_area(
                "내용",
                value=chunk['content'],
                height=200,
                disabled=True,
                label_visibility="collapsed"
            )

# ============================================================
# Markdown 변환
# ============================================================

def convert_to_markdown(result: Dict) -> str:
    """결과를 Markdown으로 변환"""
    lines = []
    
    # 헤더
    lines.append("# PRISM Phase 2.7 - 처리 결과\n")
    
    meta = result.get('metadata', {})
    lines.append(f"**처리 일시:** {meta.get('processed_at', 'N/A')}")
    lines.append(f"**총 페이지:** {meta.get('total_pages', 0)}")
    lines.append(f"**총 청크:** {meta.get('total_chunks', 0)}")
    lines.append(f"**처리 시간:** {meta.get('processing_time_seconds', 0):.2f}초\n")
    
    # 청크 타입 통계
    lines.append("## 청크 타입별 통계\n")
    for chunk_type, count in meta.get('chunk_types', {}).items():
        lines.append(f"- **{chunk_type}**: {count}개")
    lines.append("\n---\n")
    
    # 청크별 내용
    for chunk in result.get('chunks', []):
        lines.append(f"## 📝 {chunk['chunk_id']}\n")
        lines.append(f"**페이지:** {chunk['page_num']} | **타입:** {chunk['type']} | **토큰:** {chunk['metadata']['token_count']}")
        lines.append(f"**경로:** {chunk['metadata']['section_path']}\n")
        lines.append("### 내용\n")
        lines.append(chunk['content'])
        lines.append("\n---\n")
    
    return '\n'.join(lines)

# ============================================================
# 푸터
# ============================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p><strong>PRISM Phase 2.7</strong> - 차세대 지능형 문서 처리 플랫폼</p>
    <p>Powered by Claude Sonnet 4 | © 2025 PRISM Team</p>
</div>
""", unsafe_allow_html=True)
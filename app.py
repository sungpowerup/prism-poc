"""
PRISM Phase 2.7 - Streamlit Application
지능형 청킹 시스템 UI + VLM Provider 선택

Author: 최동현 (Frontend Lead)
Date: 2025-10-20
"""

import streamlit as st
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 먼저 로드 (중요!)
load_dotenv(override=True)

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.phase27_pipeline import Phase27Pipeline

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
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chunk-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .chunk-header {
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .chunk-meta {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .stat-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1976d2;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .provider-card {
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 2px solid #e0e0e0;
    }
    .provider-available {
        background-color: #e8f5e9;
        border-color: #4caf50;
    }
    .provider-unavailable {
        background-color: #ffebee;
        border-color: #f44336;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Helper Functions
# ============================================================

def get_provider_status():
    """VLM Provider 상태 확인"""
    providers = {
        'claude': {
            'name': 'Claude (Anthropic)',
            'icon': '🟣',
            'available': bool(os.getenv('ANTHROPIC_API_KEY')),
            'description': '최고 품질, 클라우드'
        },
        'azure_openai': {
            'name': 'Azure OpenAI',
            'icon': '🔵',
            'available': bool(os.getenv('AZURE_OPENAI_API_KEY') and os.getenv('AZURE_OPENAI_ENDPOINT')),
            'description': '공공기관 호환, 클라우드'
        },
        'ollama': {
            'name': 'Ollama (Local)',
            'icon': '🟢',
            'available': True,  # 로컬이므로 항상 시도 가능
            'description': '폐쇄망 가능, 로컬 GPU'
        }
    }
    return providers

def convert_to_markdown(result: dict) -> str:
    """결과를 마크다운으로 변환"""
    md_lines = []
    
    # 헤더
    md_lines.append("# PRISM Phase 2.7 - 처리 결과")
    md_lines.append("")
    md_lines.append(f"**처리 일시:** {result['metadata']['processed_at']}")
    md_lines.append(f"**총 페이지:** {result['metadata']['total_pages']}")
    md_lines.append(f"**총 청크:** {result['metadata']['total_chunks']}")
    md_lines.append(f"**처리 시간:** {result['metadata']['processing_time_seconds']:.2f}초")
    md_lines.append("")
    
    # 청크 타입별 통계
    md_lines.append("## 청크 타입별 통계")
    md_lines.append("")
    for chunk_type, count in result['metadata']['chunk_types'].items():
        md_lines.append(f"- **{chunk_type}**: {count}개")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 각 청크
    for i, chunk in enumerate(result['chunks'], 1):
        md_lines.append(f"## 📝 {chunk['chunk_id']}")
        md_lines.append("")
        md_lines.append(f"**페이지:** {chunk['page_num']} | **타입:** {chunk['type']} | **토큰:** {chunk['metadata']['token_count']}")
        md_lines.append(f"**경로:** {chunk['metadata']['section_path']}")
        md_lines.append("")
        md_lines.append("### 내용")
        md_lines.append("")
        md_lines.append(chunk['content'])
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    return '\n'.join(md_lines)

# ============================================================
# 세션 상태 초기화
# ============================================================

if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None

if 'result' not in st.session_state:
    st.session_state.result = None

if 'selected_chunk_idx' not in st.session_state:
    st.session_state.selected_chunk_idx = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'selected_provider' not in st.session_state:
    # 기본값: 환경변수에서 또는 첫 번째 사용 가능한 provider
    default_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
    st.session_state.selected_provider = default_provider

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
        result = pipeline.process(str(input_path))
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # 결과 저장
        st.session_state.result = result
        
        progress_placeholder.progress(100, text="✅ 처리 완료!")
        status_placeholder.success(f"✅ 처리 완료! ({duration:.1f}초)")
        
        # 결과 파일 저장
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"prism_result_{timestamp}.json"
        md_path = output_dir / f"prism_result_{timestamp}.md"
        
        # JSON 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Markdown 저장
        md_content = convert_to_markdown(result)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        st.success(f"📁 결과 저장: {json_path}, {md_path}")
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ============================================================
# 사이드바 - VLM Provider 선택
# ============================================================

st.sidebar.markdown("## ⚙️ 설정")

# Provider 상태 확인
providers = get_provider_status()
available_providers = {k: v for k, v in providers.items() if v['available']}

st.sidebar.markdown("### 🤖 VLM Provider")

# Provider 상태 표시
for key, info in providers.items():
    status_class = "provider-available" if info['available'] else "provider-unavailable"
    status_icon = "✅" if info['available'] else "❌"
    
    st.sidebar.markdown(
        f'<div class="{status_class}" style="padding:0.5rem;border-radius:0.3rem;margin:0.3rem 0">'
        f'{info["icon"]} **{info["name"]}** {status_icon}<br/>'
        f'<small>{info["description"]}</small>'
        f'</div>',
        unsafe_allow_html=True
    )

# Provider 선택
if available_providers:
    provider_options = {v['name']: k for k, v in available_providers.items()}
    
    selected_name = st.sidebar.selectbox(
        "사용할 Provider",
        options=list(provider_options.keys()),
        index=0 if st.session_state.selected_provider not in provider_options.values() else 
              list(provider_options.values()).index(st.session_state.selected_provider),
        help="문서 처리에 사용할 VLM Provider를 선택하세요"
    )
    
    st.session_state.selected_provider = provider_options[selected_name]
    
    st.sidebar.success(f"✅ 선택됨: **{selected_name}**")
else:
    st.sidebar.error("❌ 사용 가능한 Provider가 없습니다!")
    st.sidebar.markdown("""
    ### 설정 방법
    
    `.env` 파일에 다음 중 하나를 추가하세요:
    
    **Claude:**
    ```
    ANTHROPIC_API_KEY=sk-ant-xxx
    ```
    
    **Azure OpenAI:**
    ```
    AZURE_OPENAI_API_KEY=xxx
    AZURE_OPENAI_ENDPOINT=https://xxx
    ```
    
    **Ollama:**
    ```
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=llava:7b
    ```
    """)

st.sidebar.markdown("---")

# 처리 옵션
st.sidebar.markdown("### 📋 처리 옵션")
st.sidebar.info(f"""
**청크 크기:** 100-500 토큰  
**오버랩:** 50 토큰  
**OCR 언어:** 한국어  
**최대 페이지:** 20페이지
""")

# ============================================================
# 메인 화면
# ============================================================

# 헤더
st.markdown('<div class="main-header">🔷 PRISM Phase 2.7</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">지능형 청킹 시스템 - 의미 기반 문서 분할</div>', unsafe_allow_html=True)

st.markdown("---")

# 파일 업로드
st.markdown("## 📤 문서 업로드")

uploaded_file = st.file_uploader(
    "PDF 문서를 선택하세요",
    type=['pdf'],
    help="분석할 PDF 문서를 업로드하세요 (최대 200MB, 20페이지)"
)

if uploaded_file:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.metric("파일 크기", f"{file_size_mb:.1f} MB")
    
    with col2:
        st.metric("Provider", st.session_state.selected_provider.upper())
    
    with col3:
        st.metric("상태", "업로드 완료" if uploaded_file else "대기 중")
    
    st.markdown("---")
    
    if st.button("🚀 문서 처리 시작", type="primary", use_container_width=True):
        if not available_providers:
            st.error("❌ 사용 가능한 VLM Provider가 없습니다. 사이드바에서 설정을 확인하세요.")
        else:
            process_document(uploaded_file, st.session_state.selected_provider)
else:
    st.info("👆 PDF 파일을 업로드하세요")

# ============================================================
# 처리 결과 표시
# ============================================================

if st.session_state.result:
    st.markdown("---")
    st.markdown("## 📊 처리 결과")
    
    result = st.session_state.result
    metadata = result['metadata']
    
    # 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{metadata["total_pages"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">총 페이지</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{metadata["total_chunks"]}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">총 청크</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{metadata["processing_time_seconds"]:.1f}s</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">처리 시간</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        avg_tokens = sum(c['metadata']['token_count'] for c in result['chunks']) / len(result['chunks'])
        st.markdown(f'<div class="stat-value">{avg_tokens:.0f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">평균 토큰</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 청크 타입별 통계
    st.markdown("### 📈 청크 타입별 통계")
    
    chunk_type_cols = st.columns(len(metadata['chunk_types']))
    for col, (chunk_type, count) in zip(chunk_type_cols, metadata['chunk_types'].items()):
        col.metric(chunk_type.upper(), count)
    
    st.markdown("---")
    
    # 청크 목록
    st.markdown("### 📝 청크 목록")
    
    # 페이지 필터
    page_filter = st.selectbox(
        "페이지 선택",
        options=["전체"] + [f"페이지 {i}" for i in range(1, metadata['total_pages'] + 1)]
    )
    
    # 필터링
    filtered_chunks = result['chunks']
    if page_filter != "전체":
        page_num = int(page_filter.split()[1])
        filtered_chunks = [c for c in result['chunks'] if c['page_num'] == page_num]
    
    # 청크 표시
    for chunk in filtered_chunks:
        with st.expander(f"**{chunk['chunk_id']}** - {chunk['type']} ({chunk['metadata']['token_count']} 토큰)"):
            st.markdown(f"**페이지:** {chunk['page_num']}")
            st.markdown(f"**섹션 경로:** {chunk['metadata']['section_path']}")
            st.markdown(f"**타입:** {chunk['type']}")
            st.markdown("---")
            st.markdown("**내용:**")
            st.text(chunk['content'])
    
    # 다운로드 버튼
    st.markdown("---")
    st.markdown("### 💾 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        md_content = convert_to_markdown(result)
        st.download_button(
            label="📝 Markdown 다운로드",
            data=md_content,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ============================================================
# Footer
# ============================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>🔷 <strong>PRISM Phase 2.7</strong> - 지능형 청킹 시스템</p>
    <p>Powered by VLM + OCR + Intelligent Chunking</p>
</div>
""", unsafe_allow_html=True)
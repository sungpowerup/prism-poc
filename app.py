"""
PRISM - Final Version with Fixes
- max_pages 파라미터 안전 처리
- API 키 확인 강화
- 에러 메시지 개선
"""

import streamlit as st
import os
from pathlib import Path
import json
from datetime import datetime
from core.pdf_processor import PDFProcessor
from core.multi_vlm_service import MultiVLMService

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="PRISM",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 깔끔한 디자인
# ============================================================
st.markdown("""
<style>
    :root {
        --primary: #1a56db;
        --secondary: #6b7280;
        --success: #059669;
        --border: #e5e7eb;
        --text: #111827;
        --text-secondary: #6b7280;
        --bg-secondary: #f9fafb;
    }
    
    .main {
        background-color: var(--bg-secondary);
        padding-top: 2rem;
    }
    
    .stat-card {
        background: white;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.25rem;
        text-align: center;
    }
    
    .stat-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    
    .stat-value {
        font-size: 1.875rem;
        font-weight: 700;
        color: var(--text);
    }
    
    .panel {
        background: white;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
    }
    
    .panel-header {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border);
    }
    
    .chunk-item {
        background: white;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .chunk-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border);
    }
    
    .chunk-id {
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }
    
    .chunk-type {
        display: inline-block;
        padding: 0.25rem 0.625rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .type-text { background: #e0e7ff; color: #3730a3; }
    .type-chart { background: #fef3c7; color: #92400e; }
    .type-table { background: #dbeafe; color: #1e40af; }
    .type-figure { background: #fce7f3; color: #9f1239; }
    .type-title { background: #d1fae5; color: #065f46; }
    
    .chunk-content {
        font-size: 0.875rem;
        line-height: 1.6;
        color: var(--text);
        white-space: pre-wrap;
        word-break: break-word;
    }
    
    .stButton > button {
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.625rem 1.25rem;
        font-weight: 500;
        font-size: 0.875rem;
    }
    
    .stButton > button:hover {
        background: #1e40af;
    }
    
    .stDownloadButton > button {
        background: white;
        color: var(--primary);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0.625rem 1.25rem;
        font-weight: 500;
        font-size: 0.875rem;
    }
    
    [data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid var(--border);
    }
    
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 0.25rem;
    }
    
    .sidebar-subtitle {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Helper Functions
# ============================================================

def save_json_utf8(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def convert_to_markdown(data):
    md_lines = []
    md_lines.append("# PRISM 문서 추출 결과\n")
    md_lines.append(f"**처리 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    stats = data.get('statistics', {})
    md_lines.append("## 통계\n")
    md_lines.append(f"- 총 페이지: {stats.get('total_pages', 0)}")
    md_lines.append(f"- 총 청크: {stats.get('total_chunks', 0)}")
    md_lines.append(f"- 텍스트: {stats.get('text_chunks', 0)}")
    md_lines.append(f"- 표: {stats.get('table_chunks', 0)}")
    md_lines.append(f"- 차트: {stats.get('chart_chunks', 0)}")
    md_lines.append(f"- 이미지: {stats.get('image_chunks', 0)}\n")
    
    chunks = data.get('chunks', [])
    current_page = None
    
    for chunk in chunks:
        page_num = chunk.get('page_num', 0)
        if page_num != current_page:
            current_page = page_num
            md_lines.append(f"\n## 페이지 {page_num}\n")
        
        chunk_id = chunk.get('chunk_id', '')
        content = chunk.get('content', '')
        md_lines.append(f"### {chunk_id}\n")
        md_lines.append(content)
        md_lines.append("\n---\n")
    
    return "\n".join(md_lines)

# ============================================================
# 세션 초기화
# ============================================================

if 'vlm_service' not in st.session_state:
    try:
        default_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
        st.session_state.vlm_service = MultiVLMService(default_provider=default_provider)
    except Exception as e:
        st.session_state.vlm_service = None

if 'pdf_processor' not in st.session_state:
    try:
        st.session_state.pdf_processor = PDFProcessor()
    except Exception as e:
        st.session_state.pdf_processor = None

# ============================================================
# 메인 UI
# ============================================================

def main():
    # 사이드바
    with st.sidebar:
        st.markdown('<div class="sidebar-title">PRISM</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-subtitle">Document Intelligence Platform</div>', unsafe_allow_html=True)
        
        st.markdown("### 모델 설정")
        
        if st.session_state.vlm_service is not None:
            try:
                vlm_service = st.session_state.vlm_service
                
                # 안전하게 현재 프로바이더 가져오기
                current_provider = getattr(vlm_service, 'current_provider', None)
                if current_provider is None:
                    current_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
                
                # 사용 가능한 프로바이더 목록
                providers_status = vlm_service.get_available_providers()
                
                # 선택 옵션 생성
                provider_options = []
                provider_mapping = {}
                
                for key, info in providers_status.items():
                    if isinstance(info, dict) and info.get('available', False):
                        if key == 'claude':
                            display_name = "Claude Sonnet 4"
                        elif key == 'azure_openai':
                            display_name = "Azure OpenAI GPT-4"
                        elif key == 'local_sllm':
                            display_name = "Ollama"
                        else:
                            display_name = key.replace('_', ' ').title()
                        
                        provider_options.append(display_name)
                        provider_mapping[display_name] = key
                
                if provider_options:
                    # 현재 선택 찾기
                    current_display = None
                    for display, key in provider_mapping.items():
                        if key == current_provider:
                            current_display = display
                            break
                    
                    if current_display is None or current_display not in provider_options:
                        current_display = provider_options[0]
                    
                    selected_display = st.selectbox(
                        "VLM 모델 선택",
                        options=provider_options,
                        index=provider_options.index(current_display),
                        label_visibility="collapsed"
                    )
                    
                    selected_provider = provider_mapping[selected_display]
                    
                    if selected_provider != current_provider:
                        vlm_service.set_provider(selected_provider)
                    
                    provider_info = providers_status.get(selected_provider, {})
                    
                    st.markdown(f"""
                    **제공사:** {provider_info.get('provider', 'N/A')}  
                    **모델:** {provider_info.get('model', 'N/A')}  
                    **속도:** {provider_info.get('speed', 'N/A')}  
                    **품질:** {provider_info.get('quality', 'N/A')}
                    """)
                else:
                    st.warning("사용 가능한 모델이 없습니다.")
                    
                    # API 키 확인 도움말
                    st.info("""
                    **Claude Sonnet 4를 사용하려면:**
                    
                    1. `.env` 파일 생성
                    2. 다음 내용 추가:
                    ```
                    ANTHROPIC_API_KEY=sk-ant-api03-your-key
                    ```
                    3. Streamlit 재시작
                    
                    **현재 상태:**
                    - ANTHROPIC_API_KEY: {}
                    """.format("✅ 설정됨" if os.getenv('ANTHROPIC_API_KEY') else "❌ 없음"))
                    
            except Exception as e:
                st.error(f"모델 로드 오류: {str(e)}")
        else:
            st.error("VLM 서비스 초기화 실패")
        
        st.markdown("---")
        st.markdown("### 처리 설정")
        max_pages = st.slider(
            "최대 페이지 수",
            min_value=1,
            max_value=20,
            value=3
        )
    
    # 메인 영역
    if st.session_state.pdf_processor is None:
        st.error("PDF 프로세서를 사용할 수 없습니다.")
        return
    
    uploaded_file = st.file_uploader(
        "PDF 파일 선택",
        type=['pdf'],
        help="최대 200MB, PDF 형식"
    )
    
    if uploaded_file:
        col1, col2, col3 = st.columns(3)
        
        file_name_short = uploaded_file.name[:30] + "..." if len(uploaded_file.name) > 30 else uploaded_file.name
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">파일명</div>
                <div style="font-size: 0.875rem; font-weight: 600; color: var(--text); margin-top: 0.5rem;">
                    {file_name_short}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">크기</div>
                <div class="stat-value" style="font-size: 1.5rem;">{file_size_mb:.1f} MB</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">최대 페이지</div>
                <div class="stat-value" style="font-size: 1.5rem;">{max_pages}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("처리 시작", use_container_width=True):
            process_pdf(uploaded_file, max_pages)
        
        if 'result_data' in st.session_state:
            display_results(st.session_state['result_data'])

def process_pdf(uploaded_file, max_pages):
    try:
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / uploaded_file.name
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        progress_bar = st.progress(0)
        status = st.empty()
        
        status.info("PDF 분석 중...")
        progress_bar.progress(30)
        
        processor = st.session_state.pdf_processor
        
        # max_pages 파라미터 안전 처리
        import inspect
        sig = inspect.signature(processor.process_pdf)
        
        if 'max_pages' in sig.parameters:
            # max_pages를 지원하는 경우
            result = processor.process_pdf(str(temp_path), max_pages=max_pages)
        else:
            # max_pages를 지원하지 않는 경우 (기본 처리)
            st.warning(f"PDFProcessor가 max_pages를 지원하지 않습니다. 전체 페이지를 처리합니다.")
            result = processor.process_pdf(str(temp_path))
        
        status.info("청킹 완료, 처리 중...")
        progress_bar.progress(70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = Path("results")
        result_dir.mkdir(exist_ok=True)
        
        json_path = result_dir / f"result_{timestamp}.json"
        md_path = result_dir / f"result_{timestamp}.md"
        
        save_json_utf8(result, json_path)
        
        md_content = convert_to_markdown(result)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        progress_bar.progress(100)
        status.success("처리 완료!")
        
        st.session_state['result_data'] = result
        st.session_state['pdf_path'] = str(temp_path)
        st.session_state['json_path'] = str(json_path)
        st.session_state['md_path'] = str(md_path)
        
        st.rerun()
        
    except Exception as e:
        st.error(f"처리 오류: {str(e)}")
        import traceback
        with st.expander("상세 오류 정보"):
            st.code(traceback.format_exc())

def display_results(data):
    st.markdown("## 처리 결과")
    
    stats = data.get('statistics', {})
    
    cols = st.columns(6)
    stats_data = [
        ("페이지", stats.get('total_pages', 0)),
        ("총 청크", stats.get('total_chunks', 0)),
        ("텍스트", stats.get('text_chunks', 0)),
        ("표", stats.get('table_chunks', 0)),
        ("차트", stats.get('chart_chunks', 0)),
        ("이미지", stats.get('image_chunks', 0))
    ]
    
    for col, (label, value) in zip(cols, stats_data):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">{label}</div>
                <div class="stat-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'json_path' in st.session_state:
            with open(st.session_state['json_path'], 'r', encoding='utf-8') as f:
                st.download_button(
                    label="JSON 다운로드",
                    data=f.read(),
                    file_name=Path(st.session_state['json_path']).name,
                    mime="application/json",
                    use_container_width=True
                )
    
    with col2:
        if 'md_path' in st.session_state:
            with open(st.session_state['md_path'], 'r', encoding='utf-8') as f:
                st.download_button(
                    label="Markdown 다운로드",
                    data=f.read(),
                    file_name=Path(st.session_state['md_path']).name,
                    mime="text/markdown",
                    use_container_width=True
                )
    
    total_pages = stats.get('total_pages', 1)
    
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1
    
    st.markdown("---")
    st.markdown("## 상세 결과")
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("← 이전", disabled=st.session_state['current_page'] <= 1):
            st.session_state['current_page'] -= 1
            st.rerun()
    
    with col2:
        page_num = st.select_slider(
            "페이지",
            options=list(range(1, total_pages + 1)),
            value=st.session_state['current_page'],
            label_visibility="collapsed"
        )
        if page_num != st.session_state['current_page']:
            st.session_state['current_page'] = page_num
            st.rerun()
    
    with col3:
        if st.button("다음 →", disabled=st.session_state['current_page'] >= total_pages):
            st.session_state['current_page'] += 1
            st.rerun()
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('<div class="panel"><div class="panel-header">원본 PDF</div></div>', unsafe_allow_html=True)
        if 'pdf_path' in st.session_state:
            render_pdf_page(st.session_state['pdf_path'], st.session_state['current_page'])
    
    with col_right:
        st.markdown('<div class="panel"><div class="panel-header">추출 결과</div></div>', unsafe_allow_html=True)
        display_chunks(data, st.session_state['current_page'])

def render_pdf_page(pdf_path, page_num):
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        
        images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=150)
        
        if images:
            img = images[0]
            max_width = 700
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            st.image(img, use_column_width=True)
        else:
            st.warning("페이지를 표시할 수 없습니다.")
    except Exception as e:
        st.error(f"렌더링 오류: {str(e)}")

def display_chunks(data, page_num):
    chunks = [c for c in data.get('chunks', []) if c.get('page_num') == page_num]
    
    if not chunks:
        st.info("이 페이지에는 추출된 청크가 없습니다.")
        return
    
    for chunk in chunks:
        chunk_id = chunk.get('chunk_id', '')
        chunk_type = chunk.get('type', 'text')
        content = chunk.get('content', '')
        type_class = f"type-{chunk_type}"
        
        st.markdown(f"""
        <div class="chunk-item">
            <div class="chunk-header">
                <span class="chunk-id">{chunk_id}</span>
                <span class="chunk-type {type_class}">{chunk_type}</span>
            </div>
            <div class="chunk-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
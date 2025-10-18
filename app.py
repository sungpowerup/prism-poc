"""
PRISM - Final Version with Fixes
- 모든 프로바이더를 드롭다운에 표시 (사용 가능 여부와 무관)
- 사용 불가능한 프로바이더 선택 시 설정 안내
- 원본 디자인 100% 유지
"""

import streamlit as st
import os
from pathlib import Path
import json
from datetime import datetime
from dotenv import load_dotenv
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 명시적 로드 (CRITICAL!)
load_dotenv()

from core.pdf_processor import PDFProcessor
from core.multi_vlm_service import MultiVLMService

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="PRISM",
    page_icon="📄",
    layout="wide",  # 전체 너비 사용
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
    
    /* 메인 컨테이너 전체 너비 사용 */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
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
        ocr_text = chunk.get('ocr_text', '')
        
        md_lines.append(f"### {chunk_id}\n")
        
        # VLM 분석
        md_lines.append("#### 🤖 VLM 분석\n")
        md_lines.append(content)
        md_lines.append("\n")
        
        # OCR 원문 (있는 경우)
        if ocr_text and len(ocr_text.strip()) > 0:
            md_lines.append("#### 📝 OCR 원문\n")
            md_lines.append("```")
            md_lines.append(ocr_text)
            md_lines.append("```")
            md_lines.append("\n")
        
        md_lines.append("---\n")
    
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

# 처리 결과 세션 상태 추가
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None

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
                current_provider = getattr(vlm_service, 'current_provider_key', None)
                if current_provider is None:
                    current_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
                
                # 모든 프로바이더 상태 가져오기
                providers_status = vlm_service.get_available_providers()
                
                # ===== 수정: 모든 프로바이더를 드롭다운에 표시 =====
                # 프로바이더 이름 매핑
                provider_display_names = {
                    'claude': '🟣 Claude Sonnet 4',
                    'azure_openai': '🔵 Azure OpenAI GPT-4',
                    'ollama': '🟢 Ollama'
                }
                
                # 드롭다운 옵션 생성 (모든 프로바이더)
                provider_options = []
                provider_mapping = {}
                
                for key in ['claude', 'azure_openai', 'ollama']:
                    if key in providers_status:
                        info = providers_status[key]
                        is_available = info.get('available', False)
                        
                        # 표시 이름 생성
                        display_name = provider_display_names.get(key, key)
                        if not is_available:
                            display_name += " (설정 필요)"
                        
                        provider_options.append(display_name)
                        provider_mapping[display_name] = {
                            'key': key,
                            'available': is_available,
                            'info': info
                        }
                
                # 현재 선택 찾기
                current_display = None
                for display, data in provider_mapping.items():
                    if data['key'] == current_provider:
                        current_display = display
                        break
                
                if current_display is None or current_display not in provider_options:
                    current_display = provider_options[0]
                
                # 드롭다운
                selected_display = st.selectbox(
                    "VLM 모델 선택",
                    options=provider_options,
                    index=provider_options.index(current_display),
                    label_visibility="collapsed"
                )
                
                selected_data = provider_mapping[selected_display]
                selected_key = selected_data['key']
                selected_available = selected_data['available']
                selected_info = selected_data['info']
                
                # 프로바이더 변경
                if selected_key != current_provider:
                    vlm_service.set_provider(selected_key)
                
                # 상태 표시
                if selected_available:
                    st.success(f"✅ **{selected_info.get('name', 'Unknown')}** 사용 가능")
                    
                    # 상세 정보
                    st.markdown(f"""
                    **제공사:** {selected_info.get('provider', 'N/A')}  
                    **모델:** {selected_info.get('model', 'N/A')}  
                    **속도:** {selected_info.get('speed', 'N/A')}  
                    **품질:** {selected_info.get('quality', 'N/A')}
                    """)
                else:
                    st.error(f"❌ **{selected_info.get('name', 'Unknown')}** 설정 필요")
                    
                    # 설정 가이드
                    if selected_key == 'claude':
                        st.info("""
                        **Claude 설정 방법:**
                        
                        1. `.env` 파일 열기
                        2. 다음 추가:
                        ```
                        ANTHROPIC_API_KEY=sk-ant-api03-your-key
                        ```
                        3. Streamlit 재시작
                        
                        **현재 상태:**
                        - ANTHROPIC_API_KEY: {}
                        """.format("✅ 있음 (확인 필요)" if os.getenv('ANTHROPIC_API_KEY') else "❌ 없음"))
                    
                    elif selected_key == 'azure_openai':
                        st.info("""
                        **Azure OpenAI 설정 방법:**
                        
                        1. `.env` 파일 열기
                        2. 다음 추가:
                        ```
                        AZURE_OPENAI_API_KEY=your-key
                        AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
                        AZURE_OPENAI_DEPLOYMENT=gpt-4o
                        AZURE_OPENAI_API_VERSION=2024-12-01-preview
                        ```
                        3. Streamlit 재시작
                        
                        **현재 상태:**
                        - API_KEY: {}
                        - ENDPOINT: {}
                        """.format(
                            "✅ 있음" if os.getenv('AZURE_OPENAI_API_KEY') else "❌ 없음",
                            "✅ 있음" if os.getenv('AZURE_OPENAI_ENDPOINT') else "❌ 없음"
                        ))
                    
                    elif selected_key == 'ollama':
                        st.info("""
                        **Ollama 설정 방법:**
                        
                        1. Ollama 설치
                        2. 모델 다운로드:
                        ```bash
                        ollama pull llava:7b
                        ```
                        3. 서버 시작:
                        ```bash
                        ollama serve
                        ```
                        4. `.env` 파일에 추가:
                        ```
                        OLLAMA_BASE_URL=http://localhost:11434
                        OLLAMA_MODEL=llava:7b
                        ```
                        
                        **현재 상태:**
                        - Ollama 서버: 연결 실패
                        """)
                    
            except Exception as e:
                st.error(f"모델 로드 오류: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
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
    
    st.title("📄 PRISM")
    st.caption("지능형 문서 이해 플랫폼")
    
    # 저장된 처리 결과가 있으면 표시
    if st.session_state.processing_results is not None:
        st.success("✅ 이전 처리 결과가 있습니다. 새 문서를 업로드하면 기존 결과가 대체됩니다.")
        display_results(st.session_state.processing_results)
        st.markdown("---")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 업로드하세요",
        type=['pdf'],
        help="최대 200MB, 최대 20페이지"
    )
    
    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.info(f"📄 **{uploaded_file.name}** ({file_size_mb:.1f} MB)")
        with col2:
            use_ocr = st.checkbox("OCR 사용", value=True)
        with col3:
            # 선택된 프로바이더가 사용 가능한지 확인
            vlm_service = st.session_state.vlm_service
            if vlm_service:
                current_provider_key = getattr(vlm_service, 'current_provider_key', None)
                providers_status = vlm_service.get_available_providers()
                
                if current_provider_key and current_provider_key in providers_status:
                    is_available = providers_status[current_provider_key].get('available', False)
                    
                    if is_available:
                        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
                            process_file(uploaded_file, max_pages, use_ocr)
                    else:
                        st.button("⚠️ 모델 설정 필요", disabled=True, use_container_width=True)
                        st.caption("왼쪽 사이드바에서 모델을 설정하세요")
                else:
                    st.button("⚠️ 모델 선택 필요", disabled=True, use_container_width=True)
            else:
                st.button("⚠️ 서비스 오류", disabled=True, use_container_width=True)

def process_file(uploaded_file, max_pages, use_ocr):
    """파일 처리"""
    pdf_processor = st.session_state.pdf_processor
    vlm_service = st.session_state.vlm_service
    
    if vlm_service is None:
        st.error("VLM 서비스를 사용할 수 없습니다.")
        return
    
    # 진행 표시
    progress_bar = st.progress(0)
    status = st.empty()
    
    try:
        # 1. PDF 처리 (로드 + Element 추출)
        status.text("📄 PDF 처리 중...")
        file_bytes = uploaded_file.read()
        
        # PDFProcessor.process_pdf(pdf_data) 사용
        elements = pdf_processor.process_pdf(pdf_data=file_bytes)
        
        logger.info(f"추출된 Elements 수: {len(elements)}")
        
        if not elements:
            st.warning("추출된 Element가 없습니다.")
            return
        
        # 디버깅: 첫 번째 element 구조 출력
        if len(elements) > 0:
            logger.info(f"첫 번째 Element 키: {list(elements[0].keys())}")
            logger.info(f"image_base64 존재: {'image_base64' in elements[0]}")
            if 'image_base64' in elements[0]:
                logger.info(f"image_base64 길이: {len(elements[0]['image_base64']) if elements[0]['image_base64'] else 0}")
        
        # max_pages 제한 적용
        elements = [e for e in elements if e.get('page', 1) <= max_pages]
        
        logger.info(f"max_pages={max_pages} 적용 후: {len(elements)} elements")
        
        progress_bar.progress(20)
        
        progress_bar.progress(50)
        
        # 2. VLM 처리
        status.text(f"🤖 VLM 처리 중... (0/{len(elements)})")
        
        import asyncio
        
        chunks = []
        for idx, elem in enumerate(elements):
            try:
                # Element에서 이미지 데이터 가져오기
                # PDFProcessor는 'image_base64' 필드 사용
                image_base64 = elem.get('image_base64')
                
                if not image_base64:
                    logger.warning(f"Element {idx+1}: image_base64 없음, 건너뜀")
                    continue
                
                # 비동기 호출
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    vlm_service.generate_caption(
                        image_base64=image_base64,
                        element_type=elem.get('type', 'image'),
                        extracted_text=elem.get('ocr_text', '')
                    )
                )
                
                loop.close()
                
                chunks.append({
                    'chunk_id': f"chunk_{idx+1:03d}",
                    'page_num': elem.get('page', 0),
                    'type': elem.get('type', 'unknown'),
                    'content': result.get('caption', ''),
                    'ocr_text': elem.get('ocr_text', ''),  # OCR 원문 추가
                    'confidence': result.get('confidence', 0.0),
                    'provider': result.get('provider', 'unknown')
                })
                
                status.text(f"🤖 VLM 처리 중... ({idx+1}/{len(elements)})")
                progress_bar.progress(50 + int((idx + 1) / len(elements) * 40))
                
            except Exception as e:
                st.error(f"Element {idx+1} 처리 오류: {str(e)}")
        
        progress_bar.progress(100)
        status.text("✅ 처리 완료!")
        
        # 세션 상태에 결과 저장 (다운로드 후에도 유지)
        st.session_state.processing_results = chunks
        
        # 4. 결과 표시
        display_results(chunks)
        
    except Exception as e:
        st.error(f"처리 중 오류 발생: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def display_results(chunks):
    """결과 표시"""
    st.markdown("---")
    st.markdown("## 📊 처리 결과")
    
    # 통계
    stats = {
        'total_chunks': len(chunks),
        'text_chunks': sum(1 for c in chunks if c['type'] == 'text'),
        'chart_chunks': sum(1 for c in chunks if c['type'] == 'chart'),
        'table_chunks': sum(1 for c in chunks if c['type'] == 'table'),
        'image_chunks': sum(1 for c in chunks if c['type'] == 'image'),
        'total_pages': max((c['page_num'] for c in chunks), default=0)
    }
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">총 청크</div>
            <div class="stat-value">{stats['total_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">텍스트</div>
            <div class="stat-value">{stats['text_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">차트</div>
            <div class="stat-value">{stats['chart_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">표</div>
            <div class="stat-value">{stats['table_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">이미지</div>
            <div class="stat-value">{stats['image_chunks']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 다운로드 버튼 먼저 배치 (상단)
    st.markdown("---")
    st.markdown("### 💾 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    result_data = {
        'metadata': {
            'processed_at': datetime.now().isoformat(),
            'total_chunks': len(chunks)
        },
        'statistics': stats,
        'chunks': chunks
    }
    
    with col1:
        json_str = json.dumps(result_data, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        md_str = convert_to_markdown(result_data)
        st.download_button(
            "📥 Markdown 다운로드",
            data=md_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    # 청크 목록 (전체 너비 사용)
    st.markdown("---")
    st.markdown("### 📄 청크 목록")
    
    for chunk in chunks:
        chunk_type = chunk['type']
        chunk_id = chunk['chunk_id']
        content = chunk['content']
        ocr_text = chunk.get('ocr_text', '')
        confidence = chunk['confidence']
        
        # 전체 너비로 표시
        with st.container():
            st.markdown(f"""
            <div class="chunk-item">
                <div class="chunk-header">
                    <span class="chunk-id">{chunk_id}</span>
                    <span class="chunk-type type-{chunk_type}">{chunk_type}</span>
                </div>
                <div style="margin-top: 0.5rem; margin-bottom: 0.75rem; font-size: 0.75rem; color: var(--text-secondary);">
                    📄 페이지: {chunk['page_num']} | 🤖 프로바이더: {chunk['provider']} | 📊 신뢰도: {confidence:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 탭으로 VLM 분석과 OCR 텍스트 구분
            if ocr_text and len(ocr_text.strip()) > 0:
                tab1, tab2 = st.tabs(["🤖 VLM 분석", "📝 OCR 원문"])
                
                with tab1:
                    st.markdown(f"""
                    <div class="chunk-content">
                        {content}
                    </div>
                    """, unsafe_allow_html=True)
                
                with tab2:
                    st.text_area(
                        "OCR 추출 텍스트",
                        value=ocr_text,
                        height=200,
                        key=f"ocr_{chunk_id}",
                        label_visibility="collapsed"
                    )
            else:
                st.markdown(f"""
                <div class="chunk-content">
                    {content}
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
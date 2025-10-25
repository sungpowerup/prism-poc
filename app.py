"""
app_v50.py
PRISM Phase 5.0 - Streamlit App (범용 문서 처리)

✅ Phase 5.0 핵심:
1. 문서 타입 자동 인식 UI
2. 5가지 체크리스트 시각화
3. 실시간 진행 상황 표시

Author: 최동현 (Frontend Lead)
Date: 2025-10-24
Version: 5.0
"""

import streamlit as st
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ✅ core 패키지에서 import
try:
    from core.pdf_processor import PDFProcessor
    from core.document_classifier import DocumentClassifierV50
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase50Pipeline
    PHASE_50_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    PHASE_50_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Storage는 선택적
try:
    from core.storage import Storage
except ImportError:
    Storage = None

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 5.0 - 범용 문서 처리",
    page_icon="🎯",
    layout="wide"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 서비스 초기화
@st.cache_resource
def init_services():
    """서비스 초기화"""
    try:
        provider = "azure_openai"
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not azure_key or not azure_endpoint:
            provider = "claude"
            claude_key = os.getenv("ANTHROPIC_API_KEY")
            if not claude_key:
                raise ValueError("Azure OpenAI 또는 Claude API 키가 필요합니다")
        
        services = {
            'pdf_processor': PDFProcessor(),
            'vlm_service': VLMServiceV50(provider=provider),
            'provider': provider,
            'storage': Storage() if Storage else None
        }
        
        return services
    except Exception as e:
        st.error(f"❌ 서비스 초기화 실패: {e}")
        return None

# 세션 상태
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'processing_result' not in st.session_state:
    st.session_state.processing_result = None

def main():
    """메인"""
    st.markdown('<div class="main-header">🎯 PRISM Phase 5.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">범용 문서 처리 시스템</div>', unsafe_allow_html=True)
    
    if not PHASE_50_AVAILABLE:
        st.markdown(f"""
        <div class="error-box">
            <h3>❌ Phase 5.0 모듈을 찾을 수 없습니다</h3>
            <p><strong>오류:</strong> {IMPORT_ERROR}</p>
            <h4>📂 필요한 구조:</h4>
            <pre>
project/
├── app.py
├── .env
└── core/
    ├── __init__.py          ← 이 파일이 필수!
    ├── document_classifier.py
    ├── vlm_service.py
    ├── pipeline.py
    └── pdf_processor.py
            </pre>
            <h4>🔧 해결:</h4>
            <p>1. <code>core</code> 디렉토리에 <strong>__init__.py</strong> 파일 생성 (빈 파일도 OK)</p>
            <p>2. 모든 .py 파일이 core 안에 있는지 확인</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    services = init_services()
    if not services:
        st.stop()
    
    with st.sidebar:
        st.header("📋 Phase 5.0")
        st.markdown(f"**🤖 VLM**: {services['provider']}")
        st.markdown("**📦 버전**: 5.0")
    
    if st.session_state.step == 1:
        show_upload_step(services)
    elif st.session_state.step == 2:
        show_processing_step(services)
    elif st.session_state.step == 3:
        show_results_step(services)

def show_upload_step(services):
    st.header("📤 Step 1: PDF 업로드")
    uploaded_file = st.file_uploader("PDF 선택", type=['pdf'])
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        col1, col2 = st.columns(2)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("크기", f"{uploaded_file.size/1024/1024:.2f} MB")
        
        max_pages = st.slider("최대 페이지", 1, 50, 20)
        
        if st.button("🚀 처리 시작", type="primary"):
            st.session_state.max_pages = max_pages
            st.session_state.step = 2
            st.rerun()

def show_processing_step(services):
    st.header("⚙️ Step 2: 처리 중")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(msg, pct):
        progress_bar.progress(pct)
        status_text.text(msg)
    
    try:
        temp_path = Path("temp") / st.session_state.uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(st.session_state.uploaded_file.getbuffer())
        
        pipeline = Phase50Pipeline(
            pdf_processor=services['pdf_processor'],
            vlm_service=services['vlm_service'],
            storage=services['storage']
        )
        
        result = pipeline.process_pdf(
            pdf_path=str(temp_path),
            max_pages=st.session_state.max_pages,
            progress_callback=update_progress
        )
        
        if temp_path.exists():
            temp_path.unlink()
        
        if result['status'] == 'success':
            st.session_state.processing_result = result
            st.session_state.step = 3
            st.rerun()
        else:
            st.error(f"실패: {result.get('error')}")
    except Exception as e:
        st.error(f"오류: {e}")

def show_results_step(services):
    result = st.session_state.processing_result
    st.header("✅ Step 3: 결과")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("페이지", f"{result['pages_success']}/{result['pages_total']}")
    with col2:
        st.metric("시간", f"{result['processing_time']:.1f}초")
    with col3:
        st.metric("품질", f"{result['overall_score']:.0f}/100")
    
    tab1, tab2 = st.tabs(["체크리스트", "Markdown"])
    
    with tab1:
        for name, key, target in [
            ("원본 충실도", 'fidelity_score', 95),
            ("청킹 품질", 'chunking_score', 90),
            ("RAG 적합도", 'rag_score', 95),
            ("범용성", 'universality_score', 100),
            ("경쟁사 대비", 'competitive_score', 95)
        ]:
            score = result.get(key, 0)
            st.markdown(f"**{name}**: {score:.0f}/100")
            st.progress(score / 100)
    
    with tab2:
        markdown = result['markdown']
        st.download_button(
            "📥 다운로드",
            markdown,
            f"prism_{result['session_id']}.md",
            "text/markdown"
        )
        st.markdown(markdown)
    
    if st.button("🔙 새 문서"):
        st.session_state.step = 1
        st.rerun()

if __name__ == "__main__":
    main()
"""
app.py
PRISM Phase 5.7.0 - Streamlit Demo

기능:
1. PDF 업로드
2. Phase 5.6.x Pipeline (Markdown 추출)
3. Phase 5.7.0 Tree 생성
4. Tree 시각화
5. JSON/Markdown 다운로드

Author: 최동현 (Frontend Lead)
Date: 2025-10-27
Version: 5.7.0
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import time
import tempfile
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

# Phase 5.7.0 컴포넌트
try:
    from core.tree_builder import TreeBuilder
    from core.hierarchical_parser import HierarchicalParser
    from core.llm_adapter import LLMAdapter
    PHASE_570_AVAILABLE = True
except ImportError as e:
    PHASE_570_AVAILABLE = False
    TREE_IMPORT_ERROR = str(e)

# Phase 5.6.x Pipeline (Markdown 추출용)
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    PIPELINE_IMPORT_ERROR = str(e)

# ==========================================
# Page Config
# ==========================================

st.set_page_config(
    page_title="PRISM Phase 5.7.0",
    page_icon="🌲",
    layout="wide"
)

# ==========================================
# CSS
# ==========================================

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .tree-node {
        background: #ffffff;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .clause-node {
        background: #f8f9fa;
        border-left: 3px solid #4CAF50;
        padding: 0.8rem;
        margin: 0.3rem 0 0.3rem 2rem;
        border-radius: 3px;
    }
    .item-node {
        background: #fafafa;
        border-left: 2px solid #FF9800;
        padding: 0.6rem;
        margin: 0.2rem 0 0.2rem 4rem;
        border-radius: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 서비스 초기화
# ==========================================

@st.cache_resource
def init_services():
    """서비스 초기화"""
    try:
        # VLM 프로바이더
        provider = "azure_openai"
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not azure_key or not azure_endpoint:
            provider = "claude"
        
        services = {
            'pdf_processor': PDFProcessor(),
            'vlm_service': VLMServiceV50(provider=provider),
            'pipeline': Phase53Pipeline(
                pdf_processor=PDFProcessor(),
                vlm_service=VLMServiceV50(provider=provider)
            ),
            'tree_builder': TreeBuilder(),
            'hierarchical_parser': HierarchicalParser(),
            'llm_adapter': LLMAdapter(),
            'provider': provider
        }
        
        return services
    except Exception as e:
        st.error(f"❌ 서비스 초기화 실패: {e}")
        return None

# ==========================================
# Title
# ==========================================

st.markdown('<div class="main-header">🌲 PRISM Phase 5.7.0</div>', unsafe_allow_html=True)
st.markdown("**PDF → Markdown → 법령 트리 (3단 계층 구조)**")

# ==========================================
# 모듈 체크
# ==========================================

if not PHASE_570_AVAILABLE:
    st.error(f"❌ Phase 5.7.0 모듈 로드 실패: {TREE_IMPORT_ERROR}")
    st.info("필수 파일: tree_builder.py, hierarchical_parser.py, llm_adapter.py")
    st.stop()

if not PIPELINE_AVAILABLE:
    st.error(f"❌ Pipeline 모듈 로드 실패: {PIPELINE_IMPORT_ERROR}")
    st.info("필수 파일: pdf_processor.py, vlm_service.py, pipeline.py")
    st.stop()

# ==========================================
# Sidebar
# ==========================================

with st.sidebar:
    st.header("📋 Phase 5.7.0 특징")
    st.markdown("""
    **한 번의 클릭으로 완료:**
    - ✅ PDF → Markdown (Phase 5.6.x)
    - ✅ Markdown → Tree (Phase 5.7.0)
    - ✅ 3단 계층 (조문·항·호)
    - ✅ DoD 자동 검증
    - ✅ 경계 누수 탐지
    - ✅ JSON/Markdown 다운로드
    """)
    
    st.divider()
    
    st.header("⚙️ 설정")
    
    max_pages = st.slider("최대 페이지 수", 1, 50, 20)
    
    services = init_services()
    if services:
        st.success(f"✅ VLM: {services['provider']}")

# ==========================================
# Main Content
# ==========================================

# 세션 상태 초기화
if 'markdown' not in st.session_state:
    st.session_state.markdown = None
if 'tree_document' not in st.session_state:
    st.session_state.tree_document = None

# ==========================================
# Step 1: PDF 업로드
# ==========================================

st.header("📄 Step 1: PDF 업로드")

uploaded_file = st.file_uploader(
    "PDF 파일 선택",
    type=['pdf'],
    help="법령 또는 규정 문서를 업로드하세요"
)

if uploaded_file:
    st.success(f"✅ 파일 업로드: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
    
    # ==========================================
    # Step 2: 처리 시작 (Phase 5.6.x → 5.7.0 통합)
    # ==========================================
    
    st.divider()
    st.header("🚀 Step 2: 처리 시작")
    st.markdown("**PDF → Markdown → Tree (자동 실행)**")
    
    if st.button("🚀 처리 시작", type="primary", use_container_width=True):
        
        if not services:
            st.error("❌ 서비스 초기화 필요")
        else:
            # 임시 파일 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name
            
            try:
                # Progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # ==========================================
                # Phase 5.6.x: Markdown 추출
                # ==========================================
                
                status_text.text("📝 Phase 5.6.x: Markdown 추출 중...")
                progress_bar.progress(10)
                
                def progress_callback(msg, progress):
                    # 0~80% 범위로 매핑
                    mapped_progress = int(10 + (progress * 0.7))
                    status_text.text(f"📝 {msg}")
                    progress_bar.progress(mapped_progress)
                
                result = services['pipeline'].process_pdf(
                    pdf_path=tmp_path,
                    max_pages=max_pages,
                    progress_callback=progress_callback
                )
                
                if result['status'] != 'success':
                    st.error(f"❌ Markdown 추출 실패: {result.get('error', 'Unknown error')}")
                    progress_bar.empty()
                    status_text.empty()
                    st.stop()
                
                markdown = result['markdown']
                doc_title = uploaded_file.name.replace('.pdf', '')
                
                status_text.text(f"✅ Markdown 추출 완료 ({result['pages_success']}/{result['pages_total']} 페이지)")
                progress_bar.progress(80)
                time.sleep(0.5)
                
                # ==========================================
                # Phase 5.7.0: Tree 생성
                # ==========================================
                
                # TreeBuilder
                status_text.text("🌲 Phase 5.7.0: TreeBuilder 실행 중...")
                progress_bar.progress(85)
                time.sleep(0.3)
                
                builder = services['tree_builder']
                document = builder.build(
                    markdown=markdown,
                    document_title=doc_title
                )
                
                # HierarchicalParser
                status_text.text("🔍 Phase 5.7.0: HierarchicalParser 검증 중...")
                progress_bar.progress(90)
                time.sleep(0.3)
                
                parser = services['hierarchical_parser']
                validated = parser.parse(document)
                
                # LLMAdapter
                status_text.text("🤖 Phase 5.7.0: LLMAdapter 프롬프트 생성 중...")
                progress_bar.progress(95)
                time.sleep(0.3)
                
                adapter = services['llm_adapter']
                prompt = adapter.to_prompt(validated)
                json_export = adapter.to_json_export(validated)
                
                # 저장
                st.session_state.markdown = markdown
                st.session_state.doc_title = doc_title
                st.session_state.tree_document = validated
                st.session_state.prompt = prompt
                st.session_state.json_export = json_export
                
                # 완료
                status_text.text("✅ 모든 처리 완료!")
                progress_bar.progress(100)
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"✅ 처리 완료! (Markdown → Tree 변환)")
                
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
            
            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(tmp_path)
                except:
                    pass

# ==========================================
# Step 3: 결과 표시
# ==========================================

if st.session_state.tree_document:
    
    st.divider()
    st.header("📊 Step 3: 결과")
    
    document = st.session_state.tree_document
    metrics = document['document'].get('metrics', {})
    tree = document['document']['tree']
    
    # ==========================================
    # DoD 지표
    # ==========================================
    
    st.subheader("📈 Phase 5.6.3 DoD 지표")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rate = metrics.get('hierarchy_preservation_rate', 0)
        st.metric(
            "계층 보존율",
            f"{rate:.1%}",
            delta="목표 ≥95%",
            delta_color="normal" if rate >= 0.95 else "inverse"
        )
    
    with col2:
        rate = metrics.get('boundary_cross_bleed_rate', 0)
        st.metric(
            "경계 누수율",
            f"{rate:.1%}",
            delta="목표 =0%",
            delta_color="normal" if rate == 0 else "inverse"
        )
    
    with col3:
        rate = metrics.get('empty_article_rate', 0)
        st.metric(
            "빈 조문율",
            f"{rate:.1%}",
            delta="목표 =0%",
            delta_color="normal" if rate == 0 else "inverse"
        )
    
    # DoD 통과
    dod_pass = metrics.get('dod_pass', False)
    
    if dod_pass:
        st.success("✅ **DoD 검증 통과!**")
    else:
        st.error("❌ **DoD 검증 실패!**")
    
    # ==========================================
    # Tree 시각화
    # ==========================================
    
    st.divider()
    st.subheader("🌲 Tree 구조")
    
    # 통계
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("조문 수", len(tree))
    
    with col2:
        clause_count = sum(
            len([c for c in a.get('children', []) if isinstance(c, dict) and c.get('level') == 'clause'])
            for a in tree
        )
        st.metric("항 수", clause_count)
    
    with col3:
        item_count = 0
        for article in tree:
            for child in article.get('children', []):
                if isinstance(child, dict) and child.get('level') == 'clause':
                    item_count += len([
                        i for i in child.get('children', [])
                        if isinstance(i, dict) and i.get('level') == 'item'
                    ])
        st.metric("호 수", item_count)
    
    # Tree 표시
    for i, article in enumerate(tree, 1):
        article_no = article.get('article_no', '')
        article_title = article.get('article_title', '')
        content = article.get('content', '')
        metadata = article.get('metadata', {})
        
        # 조문
        with st.expander(f"📄 {article_no}{article_title}", expanded=(i <= 3)):
            
            # 메타데이터
            if metadata.get('is_deleted'):
                st.error("🗑️ 삭제됨")
            
            if metadata.get('has_cross_bleed'):
                st.warning("⚠️ 경계 누수")
            
            if metadata.get('amended_dates'):
                st.info(f"📅 {', '.join(metadata['amended_dates'])}")
            
            # 본문
            if content:
                st.markdown(f"**본문:** {content}")
            
            # 항
            for child in article.get('children', []):
                if isinstance(child, dict) and child.get('level') == 'clause':
                    st.markdown(f"**{child['clause_no']}** {child.get('content', '')}")
                    
                    # 호
                    for item in child.get('children', []):
                        if isinstance(item, dict) and item.get('level') == 'item':
                            st.markdown(f"  - **{item['item_no']}** {item.get('content', '')}")
    
    # ==========================================
    # 다운로드
    # ==========================================
    
    st.divider()
    st.subheader("💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "📥 JSON 다운로드",
            data=st.session_state.json_export,
            file_name=f"{st.session_state.doc_title}_tree.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            "📥 Markdown 다운로드",
            data=st.session_state.markdown,
            file_name=f"{st.session_state.doc_title}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ==========================================
# Footer
# ==========================================

st.divider()
st.markdown("""
---
**PRISM Phase 5.7.0** | 법령 트리 구조화 완성 🎉
""")
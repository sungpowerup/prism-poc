"""
app.py
PRISM Phase 5.7.2.2 Hotfix - Streamlit Demo

✅ Phase 5.7.2.2 긴급 수정:
1. 버전 정보 표시
2. 빈 페이지 DoD 母数 제외
3. 페이지 처리 로직 개선
4. 캐시 클리어 가이드
5. ✅ VLM 초기화 파라미터 수정

기능:
1. PDF 업로드
2. Phase 5.7.2.2 Pipeline (Markdown 추출 + 페이지 구분자 제거)
3. Phase 5.7.0 Tree 생성
4. Tree 시각화
5. JSON/Markdown 다운로드

Author: 최동현 (Frontend Lead) + GPT(미송) 의견 반영
Date: 2025-10-31
Version: 5.7.2.2 Hotfix
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
    page_title="PRISM Phase 5.7.2.2",
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
    .version-badge {
        background: #667eea;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Header
# ==========================================

st.markdown('<p class="main-header">🌲 PRISM Phase 5.7.2.2</p>', unsafe_allow_html=True)
st.markdown("**차세대 지능형 문서 이해 플랫폼 - Pipeline Hotfix**")

# ✅ 버전 정보 표시
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<span class="version-badge">HybridExtractor v5.7.2.2</span>', unsafe_allow_html=True)
with col2:
    st.markdown('<span class="version-badge">TreeBuilder v5.7.2.1</span>', unsafe_allow_html=True)
with col3:
    st.markdown('<span class="version-badge">DoD 母数 수정</span>', unsafe_allow_html=True)

st.divider()

# ==========================================
# 초기화
# ==========================================

if 'markdown' not in st.session_state:
    st.session_state.markdown = None
if 'tree_document' not in st.session_state:
    st.session_state.tree_document = None
if 'prompt' not in st.session_state:
    st.session_state.prompt = None
if 'json_export' not in st.session_state:
    st.session_state.json_export = None
if 'doc_title' not in st.session_state:
    st.session_state.doc_title = None

# ==========================================
# Sidebar
# ==========================================

with st.sidebar:
    st.header("⚙️ 설정")
    
    # 최대 페이지 수
    max_pages = st.number_input(
        "최대 페이지 수",
        min_value=1,
        max_value=50,
        value=10,
        help="처리할 최대 페이지 수"
    )
    
    st.divider()
    
    # 시스템 상태
    st.subheader("🔍 시스템 상태")
    
    if PHASE_570_AVAILABLE:
        st.success("✅ Phase 5.7.0 컴포넌트")
    else:
        st.error("❌ Phase 5.7.0 컴포넌트")
        with st.expander("오류 상세"):
            st.code(TREE_IMPORT_ERROR)
    
    if PIPELINE_AVAILABLE:
        st.success("✅ Pipeline 컴포넌트")
    else:
        st.error("❌ Pipeline 컴포넌트")
        with st.expander("오류 상세"):
            st.code(PIPELINE_IMPORT_ERROR)
    
    st.divider()
    
    # ✅ 캐시 클리어 가이드
    st.subheader("🧹 캐시 관리")
    st.info("""
    **소스 수정 후 필수!**
    
    1. __pycache__ 삭제:
    ```bash
    find . -type d -name "__pycache__" -exec rm -rf {} +
    ```
    
    2. 앱 재시작:
    ```bash
    streamlit run app.py
    ```
    """)

# ==========================================
# 서비스 초기화
# ==========================================

@st.cache_resource
def initialize_services():
    """서비스 초기화"""
    try:
        # VLM Provider 결정
        provider = os.getenv("VLM_PROVIDER", "azure_openai")
        
        # Azure OpenAI 우선, 없으면 Claude
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not azure_key:
            provider = "claude"
        
        # VLM Service (✅ model 파라미터 제거)
        vlm_service = VLMServiceV50(provider=provider)
        
        # PDF Processor
        pdf_processor = PDFProcessor()
        
        # Pipeline
        pipeline = Phase53Pipeline(
            pdf_processor=pdf_processor,
            vlm_service=vlm_service
        )
        
        # Tree Builder
        tree_builder = TreeBuilder()
        
        # Hierarchical Parser
        hierarchical_parser = HierarchicalParser()
        
        # LLM Adapter
        llm_adapter = LLMAdapter()
        
        return {
            'vlm_service': vlm_service,
            'pdf_processor': pdf_processor,
            'pipeline': pipeline,
            'tree_builder': tree_builder,
            'hierarchical_parser': hierarchical_parser,
            'llm_adapter': llm_adapter,
            'provider': provider
        }
    except Exception as e:
        st.error(f"초기화 실패: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

services = None
if PHASE_570_AVAILABLE and PIPELINE_AVAILABLE:
    services = initialize_services()
    
    if services:
        st.sidebar.success(f"🤖 VLM: {services['provider']}")

# ==========================================
# Step 1: 업로드
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
    # Step 2: 처리 시작 (Phase 5.7.2.2 통합)
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
                # Phase 5.7.2.2: Markdown 추출 (페이지 구분자 제거)
                # ==========================================
                
                status_text.text("📝 Phase 5.7.2.2: Markdown 추출 중...")
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
                
                # ✅ 빈 페이지 카운트 (DoD 母数에서 제외)
                empty_page_count = result.get('empty_page_count', 0)
                valid_page_count = result['pages_success'] - empty_page_count
                
                status_text.text(f"✅ Markdown 추출 완료 ({valid_page_count}/{result['pages_total']} 페이지, {empty_page_count}개 빈 페이지 제외)")
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
    # DoD 지표 (✅ 母数 수정)
    # ==========================================
    
    st.subheader("📈 Phase 5.7.2.2 DoD 지표 (빈 페이지 제외)")
    
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
        st.info("💡 **개선 팁**: 빈 페이지는 이제 DoD 母数에서 자동 제외됩니다.")
    
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
        item_count = sum(
            len([i for c in a.get('children', []) 
                 if isinstance(c, dict) 
                 for i in c.get('children', []) 
                 if isinstance(i, dict) and i.get('level') == 'item'])
            for a in tree
        )
        st.metric("호 수", item_count)
    
    # Tree 렌더링
    for article in tree:
        with st.container():
            st.markdown(f"""
            <div class="tree-node">
                <strong>{article.get('number', 'N/A')}</strong> {article.get('title', '(제목 없음)')}
            </div>
            """, unsafe_allow_html=True)
            
            # Clauses
            for child in article.get('children', []):
                if isinstance(child, dict) and child.get('level') == 'clause':
                    st.markdown(f"""
                    <div class="clause-node">
                        <strong>{child.get('number', '')}</strong> {child.get('content', '')[:100]}...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Items
                    for item in child.get('children', []):
                        if isinstance(item, dict) and item.get('level') == 'item':
                            st.markdown(f"""
                            <div class="item-node">
                                <strong>{item.get('number', '')}</strong> {item.get('content', '')[:80]}...
                            </div>
                            """, unsafe_allow_html=True)
    
    # ==========================================
    # 다운로드
    # ==========================================
    
    st.divider()
    st.subheader("💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.json_export:
            st.download_button(
                label="📥 JSON 다운로드",
                data=json.dumps(st.session_state.json_export, ensure_ascii=False, indent=2),
                file_name=f"{st.session_state.doc_title}_tree.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col2:
        if st.session_state.markdown:
            st.download_button(
                label="📥 Markdown 다운로드",
                data=st.session_state.markdown,
                file_name=f"{st.session_state.doc_title}_markdown.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==========================================
# Footer
# ==========================================

st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>PRISM Phase 5.7.2.2 Hotfix | 마창수산 팀 | 2025-10-31</p>
    <p><strong>✅ 주요 개선:</strong> 페이지 구분자 자동 제거 + 빈 페이지 DoD 母数 제외 + VLM 초기화 수정</p>
</div>
""", unsafe_allow_html=True)
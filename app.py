"""
app_v560.py
PRISM Phase 5.6.0 - Streamlit App (StatuteChunker 통합)

✅ Phase 5.6.0 신규:
1. StatuteChunker UI 통합 (조문 단위 청킹)
2. 조문별 메타데이터 표시 (장, 절, 개정일)
3. 조문 통계 및 JSON 다운로드

(Phase 5.3.1 기능 유지)
- CV-Guided Hybrid Extraction
- KVS 페이로드 지원
- 5가지 체크리스트

Author: 최동현 (Frontend Lead)
Date: 2025-10-27
Version: 5.6.0
"""

import streamlit as st
import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Phase 5.6.0: Pipeline + StatuteChunker import
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline
    from core.statute_chunker import StatuteChunker  # ✅ Phase 5.6.0 신규
    PHASE_56_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    PHASE_56_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Storage는 선택적
try:
    from core.storage import Storage
except ImportError:
    Storage = None

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 5.6.0 - Statute-aware",
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
    .metric-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
        text-align: center;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
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
    .statute-box {
        background: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 3px;
    }
    .statute-header {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1976D2;
        margin-bottom: 0.5rem;
    }
    .statute-meta {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 서비스 초기화
@st.cache_resource
def init_services():
    """서비스 초기화 (Phase 5.6.0)"""
    try:
        # VLM 프로바이더 선택
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
            'pipeline': Phase53Pipeline(
                pdf_processor=PDFProcessor(),
                vlm_service=VLMServiceV50(provider=provider),
                storage=Storage() if Storage else None
            ),
            'statute_chunker': StatuteChunker(),  # ✅ Phase 5.6.0 신규
            'provider': provider
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
if 'statute_chunks' not in st.session_state:  # ✅ Phase 5.6.0 신규
    st.session_state.statute_chunks = None

def main():
    """메인 함수"""
    st.markdown('<div class="main-header">🎯 PRISM Phase 5.6.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Statute-aware Chunking (조문 단위 청킹)</div>', unsafe_allow_html=True)
    
    # Phase 5.6.0 가용성 체크
    if not PHASE_56_AVAILABLE:
        st.markdown(f"""
        <div class="error-box">
            <h3>❌ Phase 5.6.0 모듈을 찾을 수 없습니다</h3>
            <p><strong>오류:</strong> {IMPORT_ERROR}</p>
            <h4>📂 필요한 파일:</h4>
            <pre>
core/
├── __init__.py
├── pdf_processor.py
├── vlm_service.py
├── pipeline.py              ← Phase 5.3.0
├── hybrid_extractor.py      ← Phase 5.6.0 (통합)
├── quick_layout_analyzer.py
├── prompt_rules.py          ← Phase 5.5.1 (Hotfix)
├── kvs_normalizer.py
├── semantic_chunker.py
├── post_merge_normalizer.py ← Phase 5.6.0 (신규)
├── typo_normalizer.py       ← Phase 5.6.0 (신규)
└── statute_chunker.py       ← Phase 5.6.0 (신규)
            </pre>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    services = init_services()
    if not services:
        st.stop()
    
    # 사이드바
    with st.sidebar:
        st.header("📋 Phase 5.6.0")
        st.markdown(f"**🤖 VLM**: {services['provider']}")
        st.markdown("**📦 버전**: 5.6.0")
        st.markdown("**🆕 Phase 5.6.0 신규:**")
        st.markdown("- 📚 조문 단위 청킹")
        st.markdown("- 🔗 문장 결속 정규화")
        st.markdown("- ✍️ 오탈자 교정")
        st.markdown("**🔧 Phase 5.5.1 유지:**")
        st.markdown("- 표 금지 규칙 강화")
        st.markdown("- 개정 이력 표 이중 게이트")
    
    # 스텝별 UI
    if st.session_state.step == 1:
        show_upload_step(services)
    elif st.session_state.step == 2:
        show_processing_step(services)
    elif st.session_state.step == 3:
        show_results_step(services)

def show_upload_step(services):
    """Step 1: PDF 업로드"""
    st.header("📤 Step 1: PDF 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일 선택",
        type=['pdf'],
        label_visibility="visible"
    )
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("크기", f"{uploaded_file.size/1024/1024:.2f} MB")
        
        max_pages = st.slider(
            "최대 처리 페이지",
            min_value=1,
            max_value=50,
            value=20,
            label_visibility="visible"
        )
        
        if st.button("🚀 Phase 5.6.0 처리 시작", type="primary"):
            st.session_state.max_pages = max_pages
            st.session_state.step = 2
            st.rerun()

def show_processing_step(services):
    """Step 2: 처리 중"""
    st.header("⚙️ Step 2: Phase 5.6.0 처리 중")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(msg, pct):
        progress_bar.progress(pct)
        status_text.text(f"🔄 {msg}")
    
    try:
        # 임시 파일 저장
        temp_path = Path("temp") / st.session_state.uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(st.session_state.uploaded_file.getbuffer())
        
        # Phase 5.3.0 Pipeline 실행 (HybridExtractor v5.6.0 내장)
        result = services['pipeline'].process_pdf(
            pdf_path=str(temp_path),
            max_pages=st.session_state.max_pages,
            progress_callback=update_progress
        )
        
        # ✅ Phase 5.6.0: StatuteChunker 실행
        if result['status'] == 'success':
            update_progress("조문 단위 청킹 중...", 0.95)
            
            # Markdown에서 조문 청킹
            statute_chunks = services['statute_chunker'].chunk(
                content=result['markdown'],
                page_num=None  # 전체 문서
            )
            
            st.session_state.statute_chunks = statute_chunks
            result['statute_chunks'] = statute_chunks
            
            # 통계 추가
            if statute_chunks:
                stats = services['statute_chunker'].get_stats(statute_chunks)
                result['statute_stats'] = stats
        
        # 임시 파일 삭제
        if temp_path.exists():
            temp_path.unlink()
        
        if result['status'] == 'success':
            st.session_state.processing_result = result
            st.session_state.step = 3
            st.rerun()
        else:
            st.error(f"❌ 처리 실패: {result.get('error')}")
    
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
        import traceback
        st.code(traceback.format_exc())

def show_results_step(services):
    """Step 3: 결과 표시 (Phase 5.6.0)"""
    result = st.session_state.processing_result
    
    st.header("✅ Step 3: 결과 (Phase 5.6.0)")
    
    # 기본 메트릭
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("페이지", f"{result['pages_success']}/{result['pages_total']}")
    with col2:
        st.metric("처리 시간", f"{result['processing_time']:.1f}초")
    with col3:
        st.metric("종합 품질", f"{result['overall_score']:.0f}/100")
    with col4:
        kvs_count = len(result.get('kvs_payloads', []))
        st.metric("KVS 데이터", f"{kvs_count}개")
    with col5:
        # ✅ Phase 5.6.0: 조문 개수
        statute_count = len(result.get('statute_chunks', []))
        st.metric("조문 개수", f"{statute_count}개")
    
    # ✅ Phase 5.6.0: 탭 추가 (📚 조문 청킹)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 체크리스트",
        "📚 조문 청킹",  # ✅ 신규 탭
        "📝 Markdown",
        "⏱️ 성능 메트릭",
        "📦 KVS 페이로드"
    ])
    
    # Tab 1: 5가지 체크리스트
    with tab1:
        st.subheader("5가지 체크리스트 (Phase 5.6.0)")
        
        checklist = [
            ("원본 충실도", 'fidelity_score', 95),
            ("청킹 품질", 'chunking_score', 95),  # ✅ 목표 상향 (조문 청킹)
            ("RAG 적합도", 'rag_score', 95),
            ("범용성", 'universality_score', 100),
            ("경쟁사 대비", 'competitive_score', 95)
        ]
        
        for name, key, target in checklist:
            score = result.get(key, 0)
            status = "✅" if score >= target else "⚠️" if score >= target - 10 else "❌"
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{status} {name}**: {score:.0f}/100 (목표: {target})")
                st.progress(score / 100)
            with col2:
                delta = score - target
                st.metric("편차", f"{delta:+.0f}", delta_color="normal" if delta >= 0 else "inverse")
    
    # ✅ Tab 2: 조문 청킹 (Phase 5.6.0 신규)
    with tab2:
        show_statute_chunks_tab(result)
    
    # Tab 3: Markdown
    with tab3:
        st.subheader("📝 추출된 Markdown")
        
        markdown = result['markdown']
        
        # 다운로드 버튼
        st.download_button(
            label="📥 Markdown 다운로드",
            data=markdown,
            file_name=f"prism_{result['session_id']}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # 미리보기
        with st.expander("👁️ Markdown 미리보기", expanded=True):
            st.markdown(markdown)
    
    # Tab 4: 성능 메트릭
    with tab4:
        st.subheader("⏱️ 성능 메트릭 (Phase 5.6.0)")
        
        if result.get('metrics'):
            import pandas as pd
            
            metrics_df = pd.DataFrame(result['metrics'])
            
            # 평균 메트릭
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_cv = metrics_df['cv_time'].mean()
                st.metric("평균 CV 시간", f"{avg_cv:.2f}초")
            with col2:
                avg_vlm = metrics_df['vlm_time'].mean()
                st.metric("평균 VLM 시간", f"{avg_vlm:.2f}초")
            with col3:
                avg_total = metrics_df['total_time'].mean()
                st.metric("평균 총 시간", f"{avg_total:.2f}초")
            with col4:
                avg_retry = metrics_df['retry_count'].mean()
                st.metric("평균 재추출", f"{avg_retry:.1f}회")
            
            # 상세 테이블
            st.markdown("**페이지별 상세 메트릭:**")
            st.dataframe(
                metrics_df,
                use_container_width=True,
                column_config={
                    'cv_time': st.column_config.NumberColumn('CV 시간(초)', format="%.2f"),
                    'vlm_time': st.column_config.NumberColumn('VLM 시간(초)', format="%.2f"),
                    'total_time': st.column_config.NumberColumn('총 시간(초)', format="%.2f"),
                    'retry_count': st.column_config.NumberColumn('재추출 횟수', format="%d")
                }
            )
            
            # 시간 분포 차트
            st.markdown("**처리 시간 분포:**")
            import plotly.express as px
            
            fig = px.bar(
                metrics_df,
                x=metrics_df.index + 1,
                y=['cv_time', 'vlm_time'],
                labels={'value': '시간(초)', 'variable': '단계', 'x': '페이지'},
                title='페이지별 처리 시간 분석'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("메트릭 데이터가 없습니다.")
    
    # Tab 5: KVS 페이로드
    with tab5:
        st.subheader("📦 KVS 페이로드 (RAG 최적화)")
        
        if result.get('kvs_payloads'):
            st.markdown(f"**{len(result['kvs_payloads'])}개의 KVS 페이로드가 생성되었습니다.**")
            st.markdown("KVS는 Key-Value Structured 데이터로, RAG 필드 검색을 최적화합니다.")
            
            for kvs_path in result['kvs_payloads']:
                with st.expander(f"📄 {Path(kvs_path).name}"):
                    try:
                        with open(kvs_path, encoding='utf-8') as f:
                            kvs_data = json.load(f)
                        
                        # KVS 데이터 표시
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.json(kvs_data)
                        with col2:
                            st.markdown("**메타 정보:**")
                            st.markdown(f"- 문서 ID: `{kvs_data.get('doc_id')}`")
                            st.markdown(f"- 페이지: `{kvs_data.get('page')}`")
                            st.markdown(f"- 청크 ID: `{kvs_data.get('chunk_id')}`")
                            st.markdown(f"- KVS 개수: `{len(kvs_data.get('kvs', {}))}`")
                        
                        # 다운로드 버튼
                        st.download_button(
                            label=f"📥 다운로드",
                            data=json.dumps(kvs_data, ensure_ascii=False, indent=2),
                            file_name=Path(kvs_path).name,
                            mime="application/json",
                            key=f"download_{kvs_path}"
                        )
                    except Exception as e:
                        st.error(f"KVS 파일 읽기 실패: {e}")
        else:
            st.info("KVS 페이로드가 없습니다. (숫자 데이터가 없는 문서일 수 있습니다)")
    
    # 새 문서 버튼
    if st.button("🔙 새 문서 처리", use_container_width=True):
        st.session_state.step = 1
        st.session_state.uploaded_file = None
        st.session_state.processing_result = None
        st.session_state.statute_chunks = None
        st.rerun()

def show_statute_chunks_tab(result):
    """✅ Phase 5.6.0: 조문 청킹 탭 (신규)"""
    st.subheader("📚 조문 단위 청킹 (Phase 5.6.0)")
    
    statute_chunks = result.get('statute_chunks', [])
    
    if not statute_chunks:
        st.info("조문 청킹 데이터가 없습니다. (일반 문서일 수 있습니다)")
        return
    
    # 통계
    stats = result.get('statute_stats', {})
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 조문", f"{stats.get('total_chunks', 0)}개")
        with col2:
            st.metric("평균 길이", f"{stats.get('avg_chunk_size', 0):.0f}자")
        with col3:
            st.metric("장 개수", f"{stats.get('chapters', 0)}개")
        with col4:
            st.metric("절 개수", f"{stats.get('sections', 0)}개")
    
    # JSON 다운로드 버튼
    st.download_button(
        label="📥 조문 청킹 JSON 다운로드",
        data=json.dumps(statute_chunks, ensure_ascii=False, indent=2),
        file_name=f"statute_chunks_{result['session_id']}.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # 조문 리스트
    st.markdown(f"### 📋 총 {len(statute_chunks)}개 조문")
    
    for i, chunk in enumerate(statute_chunks):
        article_no = chunk.get('article_no', 'unknown')
        article_title = chunk.get('article_title', '')
        chapter = chunk.get('chapter')
        section = chunk.get('section')
        content = chunk.get('content', '')
        metadata = chunk.get('metadata', {})
        
        with st.expander(
            f"{i+1}. {article_no}" + (f" ({article_title})" if article_title else ""),
            expanded=(i < 3)  # 처음 3개만 펼침
        ):
            # 메타데이터
            col1, col2, col3 = st.columns(3)
            with col1:
                if chapter:
                    st.markdown(f"**📖 장:** {chapter}")
            with col2:
                if section:
                    st.markdown(f"**📑 절:** {section}")
            with col3:
                last_amended = metadata.get('last_amended')
                if last_amended:
                    st.markdown(f"**📅 개정일:** {last_amended}")
            
            # 내용
            st.markdown("**📝 내용:**")
            st.markdown(f'<div class="statute-box">{content}</div>', unsafe_allow_html=True)
            
            # 추가 정보
            if metadata.get('amended_dates'):
                st.markdown(f"**📜 개정 이력:** {', '.join(metadata['amended_dates'])}")

if __name__ == "__main__":
    main()
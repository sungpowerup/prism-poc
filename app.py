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

from core.pdf_processor import PDFProcessor
from core.storage import Storage

# Phase 5.0 임포트
try:
    from core.document_classifier import DocumentClassifierV50
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase50Pipeline
    PHASE_50_AVAILABLE = True
except ImportError as e:
    PHASE_50_AVAILABLE = False
    IMPORT_ERROR = str(e)

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
    .metric-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
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
        # VLM 프로바이더 확인
        provider = "azure_openai"
        
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not azure_key or not azure_endpoint:
            provider = "claude"
            claude_key = os.getenv("ANTHROPIC_API_KEY")
            if not claude_key:
                raise ValueError("Azure OpenAI 또는 Claude API 키가 필요합니다")
        
        return {
            'pdf_processor': PDFProcessor(),
            'storage': Storage(),
            'vlm_service': VLMServiceV50(provider=provider),
            'provider': provider
        }
    except Exception as e:
        st.error(f"❌ 서비스 초기화 실패: {e}")
        return None

# 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'processing_result' not in st.session_state:
    st.session_state.processing_result = None
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'progress_text' not in st.session_state:
    st.session_state.progress_text = ""

def main():
    """메인 함수"""
    
    # 헤더
    st.markdown('<div class="main-header">🎯 PRISM Phase 5.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">범용 문서 처리 시스템 - 모든 문서 타입 지원</div>', unsafe_allow_html=True)
    
    # Phase 5.0 체크
    if not PHASE_50_AVAILABLE:
        st.markdown(f"""
        <div class="error-box">
            <h3>❌ Phase 5.0 모듈을 찾을 수 없습니다</h3>
            <p>오류: {IMPORT_ERROR}</p>
            <p>필요한 파일:</p>
            <ul>
                <li>document_classifier.py</li>
                <li>vlm_service.py</li>
                <li>pipeline.py</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # 서비스 초기화
    services = init_services()
    if not services:
        st.stop()
    
    # 사이드바
    with st.sidebar:
        st.header("📋 Phase 5.0 특징")
        
        st.markdown("""
        ### ✅ 지원 문서 타입
        
        1. **텍스트 문서**
           - 공공기관 사규
           - 계약서
           - 보고서
        
        2. **다이어그램**
           - 버스 노선도
           - 플로우차트
           - 조직도
        
        3. **기술 도면**
           - 인테리어 평면도
           - 건축 설계도
        
        4. **이미지 콘텐츠**
           - 패션 사진
           - 제품 사진
        
        5. **차트/통계**
           - 막대/원형/선 차트
           - 표/테이블
        
        6. **복합 문서**
           - 혼합 타입
        """)
        
        st.markdown("---")
        st.markdown(f"**🤖 VLM 프로바이더**: {services['provider']}")
        st.markdown("**📦 버전**: 5.0")
    
    # 메인 영역
    if st.session_state.step == 1:
        show_upload_step(services)
    elif st.session_state.step == 2:
        show_processing_step(services)
    elif st.session_state.step == 3:
        show_results_step()

def show_upload_step(services):
    """Step 1: 파일 업로드"""
    
    st.header("📤 Step 1: PDF 파일 업로드")
    
    # 파일 업로더
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="모든 문서 타입을 지원합니다 (사규, 노선도, 도면, 패션, 통계 등)"
    )
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 파일명", uploaded_file.name)
        with col2:
            file_size = uploaded_file.size / 1024 / 1024
            st.metric("📊 파일 크기", f"{file_size:.2f} MB")
        with col3:
            st.metric("🎯 버전", "Phase 5.0")
        
        st.markdown("---")
        
        # 처리 옵션
        st.subheader("⚙️ 처리 옵션")
        
        max_pages = st.slider(
            "최대 페이지 수",
            min_value=1,
            max_value=50,
            value=20,
            help="처리할 최대 페이지 수"
        )
        
        st.markdown("""
        <div class="success-box">
            <strong>✅ Phase 5.0은 문서 타입을 자동으로 판별합니다</strong><br>
            하드코딩 없이 모든 문서를 지능적으로 처리합니다.
        </div>
        """, unsafe_allow_html=True)
        
        # 처리 시작 버튼
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            st.session_state.max_pages = max_pages
            st.session_state.step = 2
            st.rerun()
    else:
        st.info("👆 PDF 파일을 업로드하세요")
        
        # 예시
        st.markdown("---")
        st.subheader("📝 지원 문서 예시")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **텍스트 문서**
            - 공공기관 사규
            - 계약서
            - 보고서
            """)
        
        with col2:
            st.markdown("""
            **다이어그램**
            - 버스 노선도
            - 플로우차트
            - 조직도
            """)
        
        with col3:
            st.markdown("""
            **기타**
            - 인테리어 도면
            - 패션 사진
            - 통계 차트
            """)

def show_processing_step(services):
    """Step 2: 처리 중"""
    
    st.header("⚙️ Step 2: 문서 처리 중")
    
    # 진행 상황 표시
    progress_placeholder = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(message, progress):
        """진행 상황 업데이트"""
        st.session_state.progress = progress
        st.session_state.progress_text = message
        progress_bar.progress(progress)
        status_text.text(message)
    
    # 처리 시작
    try:
        # 임시 파일 저장
        temp_pdf_path = Path("temp") / st.session_state.uploaded_file.name
        temp_pdf_path.parent.mkdir(exist_ok=True)
        
        with open(temp_pdf_path, "wb") as f:
            f.write(st.session_state.uploaded_file.getbuffer())
        
        # Pipeline 생성
        pipeline = Phase50Pipeline(
            pdf_processor=services['pdf_processor'],
            vlm_service=services['vlm_service'],
            storage=services['storage']
        )
        
        # 처리 시작
        with st.spinner("🎯 Phase 5.0 범용 분석 중..."):
            result = pipeline.process_pdf(
                pdf_path=str(temp_pdf_path),
                max_pages=st.session_state.max_pages,
                progress_callback=update_progress
            )
        
        # 임시 파일 삭제
        if temp_pdf_path.exists():
            temp_pdf_path.unlink()
        
        if result['status'] == 'success':
            st.session_state.processing_result = result
            st.session_state.step = 3
            st.rerun()
        else:
            st.error(f"❌ 처리 실패: {result.get('error', 'Unknown error')}")
            if st.button("🔙 돌아가기"):
                st.session_state.step = 1
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {e}")
        if st.button("🔙 돌아가기"):
            st.session_state.step = 1
            st.rerun()

def show_results_step():
    """Step 3: 결과 표시"""
    
    result = st.session_state.processing_result
    
    st.header("✅ Step 3: 처리 결과")
    
    # 요약 메트릭
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📄 처리 페이지", f"{result['pages_success']}/{result['pages_total']}")
    with col2:
        st.metric("⏱️ 처리 시간", f"{result['processing_time']:.1f}초")
    with col3:
        st.metric("🎯 종합 품질", f"{result['overall_score']:.0f}/100")
    with col4:
        st.metric("📊 총 글자", f"{len(result['markdown']):,}")
    with col5:
        doc_types = result.get('doc_type_counts', {})
        main_type = max(doc_types, key=doc_types.get) if doc_types else 'mixed'
        st.metric("📋 문서 타입", main_type)
    
    st.markdown("---")
    
    # 탭
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 5가지 체크리스트",
        "📝 Markdown 결과",
        "🔍 페이지별 상세",
        "📈 통계"
    ])
    
    # Tab 1: 5가지 체크리스트
    with tab1:
        st.subheader("📊 5가지 체크리스트 점수")
        
        checklist_scores = [
            ("1️⃣ 원본 충실도", result.get('fidelity_score', 0), 95),
            ("2️⃣ 청킹 품질", result.get('chunking_score', 0), 90),
            ("3️⃣ RAG 적합도", result.get('rag_score', 0), 95),
            ("4️⃣ 범용성", result.get('universality_score', 0), 100),
            ("5️⃣ 경쟁사 대비", result.get('competitive_score', 0), 95)
        ]
        
        for name, score, target in checklist_scores:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{name}**")
                st.progress(score / 100)
            
            with col2:
                if score >= target:
                    st.markdown(f"<div style='color: green; font-size: 1.5rem; font-weight: bold;'>{score:.0f}/100 ✅</div>", unsafe_allow_html=True)
                elif score >= target * 0.8:
                    st.markdown(f"<div style='color: orange; font-size: 1.5rem; font-weight: bold;'>{score:.0f}/100 ⚠️</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color: red; font-size: 1.5rem; font-weight: bold;'>{score:.0f}/100 ❌</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 종합 평가
        overall = result.get('overall_score', 0)
        if overall >= 85:
            st.markdown("""
            <div class="success-box">
                <h3>🎉 우수!</h3>
                <p>모든 체크리스트를 만족합니다. 경쟁사 수준 이상의 품질입니다.</p>
            </div>
            """, unsafe_allow_html=True)
        elif overall >= 70:
            st.markdown("""
            <div class="warning-box">
                <h3>⚠️ 양호</h3>
                <p>대부분의 체크리스트를 만족하지만, 일부 개선이 필요합니다.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="error-box">
                <h3>❌ 개선 필요</h3>
                <p>여러 체크리스트에서 개선이 필요합니다.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Tab 2: Markdown 결과
    with tab2:
        st.subheader("📝 Markdown 결과")
        
        markdown = result['markdown']
        
        # 다운로드 버튼
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 Markdown 다운로드",
                data=markdown,
                file_name=f"prism_v50_{result['session_id']}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
            import json
            json_data = json.dumps(result, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSON 다운로드",
                data=json_data,
                file_name=f"prism_v50_{result['session_id']}.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Markdown 미리보기
        with st.expander("👀 Markdown 미리보기", expanded=True):
            st.markdown(markdown)
    
    # Tab 3: 페이지별 상세
    with tab3:
        st.subheader("🔍 페이지별 상세 정보")
        
        page_results = result.get('page_results', [])
        
        for page_result in page_results:
            page_num = page_result['page_num']
            doc_type = page_result.get('doc_type', 'mixed')
            subtype = page_result.get('subtype', 'unknown')
            confidence = page_result.get('confidence', 0.0)
            quality = page_result.get('quality_score', 0.0)
            content_length = len(page_result.get('content', ''))
            
            with st.expander(f"📄 페이지 {page_num} - {doc_type} ({subtype})"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("문서 타입", f"{doc_type}")
                with col2:
                    st.metric("하위 타입", f"{subtype}")
                with col3:
                    st.metric("신뢰도", f"{confidence:.2f}")
                with col4:
                    st.metric("품질", f"{quality:.0f}/100")
                
                st.markdown("**추출 내용:**")
                st.text_area(
                    "내용",
                    page_result.get('content', ''),
                    height=200,
                    key=f"content_{page_num}"
                )
    
    # Tab 4: 통계
    with tab4:
        st.subheader("📈 처리 통계")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**문서 타입 분포**")
            doc_type_counts = result.get('doc_type_counts', {})
            for doc_type, count in doc_type_counts.items():
                st.markdown(f"- **{doc_type}**: {count}개")
        
        with col2:
            st.markdown("**처리 정보**")
            st.markdown(f"- **Session ID**: {result['session_id']}")
            st.markdown(f"- **버전**: {result.get('version', '5.0')}")
            st.markdown(f"- **전략**: {result.get('strategy', 'universal_v50')}")
            st.markdown(f"- **VLM**: {services['provider']}")
    
    st.markdown("---")
    
    # 액션 버튼
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔙 새 문서 처리", use_container_width=True):
            st.session_state.step = 1
            st.session_state.processing_result = None
            st.rerun()
    
    with col2:
        if st.button("🔄 재처리", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

if __name__ == "__main__":
    main()
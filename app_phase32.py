"""
PRISM Phase 3.2 - Streamlit Web Application (Fixed)

✅ 수정사항:
- Phase32Pipeline 초기화 방식 수정
- PDFProcessor, LayoutDetector, VLMService, Storage 직접 전달

Author: 최동현 (Frontend Lead)
Date: 2025-10-22
Version: 3.2 (Fixed)
"""

import streamlit as st
from pathlib import Path
import json
import time
from datetime import datetime
import os

# ✅ 환경 변수 로딩 (최우선)
from dotenv import load_dotenv
load_dotenv()

# 환경 변수 확인
AZURE_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Core 모듈 임포트
try:
    from core.pdf_processor import PDFProcessor
    from core.layout_detector_v3 import LayoutDetectorV32
    from core.vlm_service import VLMService
    from core.storage import Storage
    from core.phase32_pipeline import Phase32Pipeline
    
    MODULES_OK = True
except ImportError as e:
    MODULES_OK = False
    import traceback
    ERROR_MSG = f"모듈 임포트 실패:\n{e}\n\n{traceback.format_exc()}"

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 3.2",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .phase-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        font-size: 0.9rem;
        margin-left: 1rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .improvement-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """메인 애플리케이션"""
    
    # 모듈 체크
    if not MODULES_OK:
        st.error(f"❌ {ERROR_MSG}")
        st.stop()
    
    # 헤더
    st.markdown(
        '<div class="main-header">🎯 PRISM Phase 3.2'
        '<span class="phase-badge">Ultra Filtering</span></div>',
        unsafe_allow_html=True
    )
    
    # Phase 3.2 개선사항
    st.markdown("""
    <div class="improvement-box">
        <h3 style="margin-top:0;">✨ Phase 3.2 Ultra Filtering</h3>
        <ul style="margin-bottom:0;">
            <li><strong>Region 감지 대폭 감소</strong>: 188개 → 6-8개 (목표)</li>
            <li><strong>VLM API 호출 최소화</strong>: 96% 감소</li>
            <li><strong>처리 시간 단축</strong>: 12.5분 → 30초</li>
            <li><strong>비용 절감</strong>: $0.56 → $0.02</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 🤖 VLM 설정")
        
        # VLM 프로바이더 선택
        available_providers = []
        if AZURE_API_KEY and AZURE_ENDPOINT:
            available_providers.append('azure')
        if ANTHROPIC_API_KEY:
            available_providers.append('claude')
        
        if not available_providers:
            st.error("""
            ❌ 사용 가능한 VLM 프로바이더가 없습니다!
            
            .env 파일에 다음 중 하나를 설정하세요:
            - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT
            - ANTHROPIC_API_KEY
            """)
            st.stop()
        
        vlm_provider = st.selectbox(
            "VLM 프로바이더",
            options=available_providers,
            format_func=lambda x: {
                'azure': '🔷 Azure OpenAI',
                'claude': '🟣 Anthropic Claude'
            }.get(x, x)
        )
        
        # 환경 변수 상태
        with st.expander("🔍 환경 변수 상태"):
            st.text(f"Azure API Key: {'✅' if AZURE_API_KEY else '❌'}")
            st.text(f"Azure Endpoint: {'✅' if AZURE_ENDPOINT else '❌'}")
            st.text(f"Azure Deployment: {AZURE_DEPLOYMENT}")
            st.text(f"Claude API Key: {'✅' if ANTHROPIC_API_KEY else '❌'}")
        
        st.markdown("---")
        st.markdown("### ⚙️ 처리 설정")
        
        max_pages = st.number_input(
            "최대 페이지 수",
            min_value=1,
            max_value=50,
            value=20,
            help="처리할 최대 페이지 수"
        )
        
        st.markdown("---")
        st.markdown("### 📖 사용 방법")
        st.markdown("""
        1. PDF 파일 업로드
        2. VLM 프로바이더 선택
        3. '처리 시작' 클릭
        4. 결과 확인
        """)
        
        st.markdown("---")
        st.markdown("### 🎯 Phase 3.2 특징")
        st.markdown("""
        - ✅ 최소 Region 감지 (6-8개/페이지)
        - ✅ 고정밀 필터링
        - ✅ 빠른 처리 속도
        - ✅ 비용 최소화
        """)
    
    # 메인 영역
    st.markdown("## 📤 PDF 문서 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 200MB, 20페이지 권장"
    )
    
    if uploaded_file:
        # 파일 정보
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("크기", f"{file_size_mb:.2f} MB")
        with col3:
            st.metric("VLM", vlm_provider.upper())
        
        # 처리 버튼
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            process_pdf(uploaded_file, vlm_provider, max_pages)
    
    # 결과 표시
    if 'result' in st.session_state:
        display_results(st.session_state.result)


def process_pdf(uploaded_file, vlm_provider, max_pages):
    """PDF 처리"""
    
    # 임시 파일 저장
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    pdf_path = temp_dir / uploaded_file.name
    with open(pdf_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        # 프로그레스 바
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # ==========================================
        # Stage 1: 모듈 초기화
        # ==========================================
        status_text.text("⚙️ Phase 3.2 모듈 초기화 중...")
        progress_bar.progress(10)
        
        # PDFProcessor
        pdf_processor = PDFProcessor()
        
        # LayoutDetectorV32
        layout_detector = LayoutDetectorV32()
        
        # VLMService
        if vlm_provider == 'azure':
            vlm_service = VLMService(
                provider='azure',
                api_key=AZURE_API_KEY,
                endpoint=AZURE_ENDPOINT,
                deployment_name=AZURE_DEPLOYMENT
            )
        else:  # claude
            vlm_service = VLMService(
                provider='claude',
                api_key=ANTHROPIC_API_KEY
            )
        
        # Storage
        storage = Storage('data/prism_poc.db')
        
        # Phase32Pipeline 초기화 (수정된 방식)
        pipeline = Phase32Pipeline(
            pdf_processor=pdf_processor,
            layout_detector=layout_detector,
            vlm_service=vlm_service,
            storage=storage
        )
        
        status_text.text("✅ 모듈 초기화 완료")
        progress_bar.progress(20)
        
        # ==========================================
        # Stage 2: PDF 처리
        # ==========================================
        status_text.text("🔄 문서 처리 중... (1~3분 소요)")
        progress_bar.progress(30)
        
        result = pipeline.process_pdf(str(pdf_path), max_pages=max_pages)
        
        # 완료
        progress_bar.progress(100)
        status_text.text("✅ 처리 완료!")
        
        # 결과 저장
        st.session_state.result = result
        
        st.success(f"""
        ✅ Phase 3.2 처리 완료!
        
        - 📊 감지된 Region: {result['total_regions']}개
        - ✅ 성공: {result['success_count']}개
        - ❌ 실패: {result['failed_count']}개
        - 🔥 VLM API 호출: {result['vlm_calls']}회
        - ⏱️  처리 시간: {result['total_time_sec']:.2f}초
        - 🎯 평균 신뢰도: {result['avg_confidence']:.2%}
        """)
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {e}")
        
        # 상세 에러 정보
        import traceback
        with st.expander("🔍 상세 에러 정보"):
            st.code(traceback.format_exc())


def display_results(result):
    """결과 표시"""
    
    st.markdown("## 📊 처리 결과")
    
    # 메트릭
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("전체 페이지", result['total_pages'])
    
    with col2:
        st.metric("감지된 Region", result['total_regions'])
    
    with col3:
        st.metric("VLM 호출", result['vlm_calls'])
    
    with col4:
        st.metric("처리 시간", f"{result['total_time_sec']:.1f}초")
    
    # Region별 상세 결과
    st.markdown("### 🔍 Region별 결과")
    
    for i, region_result in enumerate(result['results'], start=1):
        with st.expander(
            f"Region {i} - Page {region_result['page']} - "
            f"{region_result['region_type']} "
            f"(신뢰도: {region_result['confidence']:.2%})"
        ):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("**정보**")
                st.text(f"Region ID: {region_result['region_id']}")
                st.text(f"페이지: {region_result['page']}")
                st.text(f"타입: {region_result['region_type']}")
                st.text(f"상태: {region_result['status']}")
                
                if 'bbox' in region_result:
                    bbox = region_result['bbox']
                    st.text(f"위치: ({bbox[0]}, {bbox[1]})")
                    st.text(f"크기: {bbox[2]}x{bbox[3]}")
            
            with col2:
                st.markdown("**VLM 변환 결과**")
                
                if region_result['status'] == 'success':
                    st.success(region_result['caption'])
                else:
                    st.error(f"오류: {region_result.get('error', 'Unknown')}")
    
    # JSON 다운로드
    st.markdown("### 💾 결과 다운로드")
    
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    
    st.download_button(
        label="📥 JSON 다운로드",
        data=json_str,
        file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


if __name__ == '__main__':
    main()
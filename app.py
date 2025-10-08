"""
app.py
PRISM POC - Streamlit 메인 애플리케이션 (Local sLLM)
간단 버전
"""

import streamlit as st
import uuid
from pathlib import Path
from dotenv import load_dotenv
import time
import io

# 환경 변수 로드
load_dotenv()

from core.storage import Storage
from core.model_selector import ModelSelector
from core.pdf_processor import PDFProcessor

# 페이지 설정
st.set_page_config(
    page_title="PRISM POC - Local sLLM",
    page_icon="🔷",
    layout="wide"
)

# CSS 스타일
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 서비스 초기화
@st.cache_resource
def init_services():
    try:
        return {
            'storage': Storage(),
            'model_selector': ModelSelector(),
            'pdf_processor': PDFProcessor()
        }
    except Exception as e:
        st.error(f"초기화 오류: {str(e)}")
        return None

services = init_services()

if not services:
    st.stop()

# VLM 프로바이더 확인
model_selector = services['model_selector']
available_providers = model_selector.get_available_providers()

# 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'elements' not in st.session_state:
    st.session_state.elements = []
if 'results' not in st.session_state:
    st.session_state.results = []

def main():
    """메인 함수"""
    
    # 헤더
    st.title("🔷 PRISM POC")
    st.markdown("**VLM 기반 문서 전처리 - Local sLLM**")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # VLM 상태
        if available_providers:
            provider = model_selector.get_default_provider()
            st.success(f"🟢 {provider.get_provider_name()}")
        else:
            st.error("🔴 Ollama 서버 실행 필요")
            st.code("ollama serve")
            st.stop()
        
        st.divider()
        
        # 통계
        if st.session_state.results:
            st.subheader("📊 처리 통계")
            total = len(st.session_state.results)
            success = sum(1 for r in st.session_state.results if r.get('caption'))
            st.metric("성공", f"{success}/{total}")
    
    # 메인 컨텐츠
    if st.session_state.step == 1:
        show_upload_page()
    elif st.session_state.step == 2:
        show_processing_page()
    elif st.session_state.step == 3:
        show_results_page()

def show_upload_page():
    """1단계: 파일 업로드"""
    
    st.header("📤 STEP 1: PDF 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 10MB"
    )
    
    if uploaded_file:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📄 **파일**: {uploaded_file.name}")
        with col2:
            st.info(f"📦 **크기**: {file_size_mb:.2f} MB")
        
        if st.button("🚀 처리 시작", type="primary"):
            if file_size_mb > 10:
                st.error("❌ 파일이 너무 큽니다 (10MB 제한)")
                return
            
            # 세션 생성
            session_id = str(uuid.uuid4())
            st.session_state.session_id = session_id
            
            # PDF 처리
            try:
                with st.spinner("PDF 페이지 추출 중..."):
                    pdf_bytes = uploaded_file.getvalue()
                    elements = services['pdf_processor'].process_pdf(pdf_bytes, session_id)
                    
                    if len(elements) > 20:
                        st.error("❌ 페이지가 너무 많습니다 (20페이지 제한)")
                        return
                    
                    st.session_state.elements = elements
                    
                    # DB 저장
                    services['storage'].create_session(
                        session_id=session_id,
                        filename=uploaded_file.name,
                        file_size=len(pdf_bytes),
                        page_count=len(elements)
                    )
                    
                    st.success(f"✅ {len(elements)}개 페이지 추출 완료!")
                    time.sleep(1)
                    st.session_state.step = 2
                    st.rerun()
            
            except Exception as e:
                st.error(f"❌ 오류: {str(e)}")
                st.exception(e)

def show_processing_page():
    """2단계: VLM 처리"""
    
    st.header("⚙️ STEP 2: VLM 처리")
    
    elements = st.session_state.elements
    total = len(elements)
    
    st.info(f"총 {total}개 페이지 처리 중... (페이지당 5-10초 소요)")
    
    # 프로그레스바
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 결과 컨테이너
    results = []
    pdf_processor = services['pdf_processor']
    
    start_time = time.time()
    
    for i, element in enumerate(elements):
        # 진행률
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"처리 중... {i+1}/{total} 페이지")
        
        # VLM 처리
        try:
            image_bytes = pdf_processor.image_to_bytes(element['image'])
            
            result = model_selector.generate_caption(
                image_data=image_bytes,
                element_type='image',
                context=f"Page {element['page_number']}"
            )
            
            result['page_number'] = element['page_number']
            result['image'] = element['image']
            results.append(result)
            
        except Exception as e:
            results.append({
                'page_number': element['page_number'],
                'caption': None,
                'confidence': 0.0,
                'error': str(e),
                'image': element['image']
            })
    
    # 완료
    elapsed = time.time() - start_time
    st.session_state.results = results
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ 완료! ({elapsed:.1f}초 소요)")
    
    st.success(f"🎉 {len(results)}개 페이지 처리 완료")
    time.sleep(1)
    
    st.session_state.step = 3
    st.rerun()

def show_results_page():
    """3단계: 결과"""
    
    st.header("📊 STEP 3: 처리 결과")
    
    results = st.session_state.results
    
    # 통계
    total = len(results)
    success = sum(1 for r in results if r.get('caption'))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 페이지", total)
    with col2:
        st.metric("성공", success)
    with col3:
        if success > 0:
            avg_conf = sum(r.get('confidence', 0) for r in results if r.get('caption')) / success
            st.metric("평균 신뢰도", f"{avg_conf:.0%}")
    
    st.divider()
    
    # 결과 표시
    for i, result in enumerate(results):
        with st.expander(f"📄 페이지 {result['page_number']}", expanded=(i==0)):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if 'image' in result:
                    st.image(result['image'], use_container_width=True)
            
            with col2:
                if result.get('caption'):
                    st.success(f"**신뢰도**: {result['confidence']:.0%}")
                    st.markdown("**생성된 캡션**:")
                    st.text_area(
                        "Caption",
                        result['caption'],
                        height=200,
                        key=f"caption_{i}",
                        label_visibility="collapsed"
                    )
                else:
                    st.error("❌ 처리 실패")
                    if result.get('error'):
                        st.code(result['error'])
    
    # 다시 시작
    st.divider()
    if st.button("🔄 새 문서 처리", type="primary"):
        st.session_state.step = 1
        st.session_state.elements = []
        st.session_state.results = []
        st.session_state.session_id = None
        st.rerun()

if __name__ == '__main__':
    main()
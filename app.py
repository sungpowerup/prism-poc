"""
PRISM POC - Beautiful Modern UI
멀티 프로바이더 지원: Claude + Azure OpenAI + Ollama
"""

import streamlit as st
import asyncio
import base64
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Core 모듈
from core.pdf_processor import PDFProcessor
from core.multi_vlm_service import MultiVLMService

# 로깅 설정
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========== Streamlit 설정 ==========
st.set_page_config(
    page_title="PRISM - 지능형 문서 이해",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========== Modern CSS ==========
st.markdown("""
<style>
    /* 전역 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 메인 컨테이너 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* 헤더 */
    .main-header {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        font-size: 1.1rem;
        color: #6b7280;
        font-weight: 400;
    }
    
    /* 카드 스타일 */
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] .element-container {
        color: white;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* 버튼 */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* 메트릭 카드 */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    /* 프로그레스 바 */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* 파일 업로더 */
    [data-testid="stFileUploader"] {
        background: white;
        border: 2px dashed #667eea;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Success/Error/Info boxes */
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background: white;
        color: #667eea;
        border: 2px solid #667eea;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stDownloadButton > button:hover {
        background: #667eea;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ========== 세션 상태 초기화 ==========
if 'vlm_service' not in st.session_state:
    default_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
    st.session_state.vlm_service = MultiVLMService(default_provider=default_provider)

if 'pdf_processor' not in st.session_state:
    st.session_state.pdf_processor = PDFProcessor()

if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None


# ========== 사이드바 - 프로바이더 선택 ==========
def show_provider_selector():
    """프로바이더 선택 UI"""
    st.sidebar.markdown("### 🤖 VLM 모델 선택")
    
    vlm_service = st.session_state.vlm_service
    
    # 사용 가능한 프로바이더 조회
    providers_dict = vlm_service.get_available_providers()
    
    # 사용 가능한 프로바이더만 필터링
    available_providers = []
    provider_keys = []
    
    for key, info in providers_dict.items():
        if info['available']:
            available_providers.append(info)
            provider_keys.append(key)
    
    if not available_providers:
        st.sidebar.error("⚠️ 사용 가능한 프로바이더가 없습니다!")
        st.sidebar.info("""
        **설정 방법:**
        1. `.env` 파일 생성
        2. API 키 입력
        3. 앱 재시작
        """)
        return
    
    # 현재 프로바이더
    current_key = vlm_service.current_provider_key
    
    # 현재 선택된 인덱스 찾기
    try:
        current_index = provider_keys.index(current_key)
    except ValueError:
        current_index = 0
    
    # 프로바이더 이름 리스트
    provider_names = [p['name'] for p in available_providers]
    
    # 선택 UI
    selected_name = st.sidebar.selectbox(
        "VLM 모델",
        provider_names,
        index=current_index,
        help="문서 이미지를 분석할 AI 모델"
    )
    
    # 선택된 프로바이더의 키 찾기
    selected_index = provider_names.index(selected_name)
    selected_key = provider_keys[selected_index]
    selected_info = available_providers[selected_index]
    
    # 프로바이더 변경
    if selected_key != current_key:
        vlm_service.set_provider(selected_key)
        st.sidebar.success(f"✅ {selected_info['name']}")
        st.rerun()
    
    # 선택된 프로바이더 정보
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 📊 모델 정보")
    
    with st.sidebar.expander("상세 정보", expanded=True):
        st.markdown(f"**제공사:** {selected_info['provider']}")
        st.markdown(f"**모델:** {selected_info['model']}")
        st.markdown(f"**속도:** {selected_info['speed']}")
        st.markdown(f"**품질:** {selected_info['quality']}")
        st.markdown(f"**비용:** {selected_info['cost']}")
    
    # 모든 프로바이더 상태
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🔌 전체 상태")
    
    for key, info in providers_dict.items():
        status = "🟢" if info['available'] else "🔴"
        st.sidebar.caption(f"{status} {info['name']}")


# ========== 비동기 PDF 처리 ==========
async def process_pdf_async(pdf_bytes: bytes):
    """PDF를 비동기로 처리"""
    
    vlm_service = st.session_state.vlm_service
    processor = st.session_state.pdf_processor
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"PDF 처리 시작: {session_id}")
    
    # Element 추출
    with st.spinner("📄 PDF 페이지 추출 중..."):
        try:
            elements = processor.process_pdf(pdf_bytes)
        except Exception as e:
            logger.error(f"PDF 처리 실패: {e}", exc_info=True)
            st.error(f"❌ PDF 처리 실패: {str(e)}")
            return None
    
    if not elements:
        st.warning("⚠️ 페이지를 찾을 수 없습니다")
        return None
    
    st.success(f"✅ {len(elements)}개 페이지 추출 완료")
    
    # 진행 상태
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    total_cost = 0.0
    total_time = 0.0
    
    # 각 Element 처리
    for idx, element in enumerate(elements):
        progress = (idx + 1) / len(elements)
        progress_bar.progress(progress)
        status_text.text(f"⚡ 처리 중: {idx + 1}/{len(elements)} ({int(progress * 100)}%)")
        
        try:
            image_base64 = element.get('image_base64', '')
            if not image_base64:
                raise ValueError("이미지 데이터가 없습니다")
            
            ocr_text = element.get('ocr_text', '')
            
            # VLM 처리
            vlm_result = await vlm_service.generate_caption(
                image_base64=image_base64,
                element_type='image',
                extracted_text=ocr_text
            )
            
            result = {
                'page': element['page'],
                'caption': vlm_result['caption'],
                'confidence': vlm_result['confidence'],
                'processing_time': vlm_result['processing_time'],
                'model': vlm_result['model'],
                'provider': vlm_result['provider'],
                'cost_usd': vlm_result['cost_usd'],
                'ocr_text': ocr_text,
                'status': 'success'
            }
            
            total_cost += vlm_result['cost_usd']
            total_time += vlm_result['processing_time']
            results.append(result)
            
        except Exception as e:
            logger.error(f"페이지 {element.get('page', '?')} 처리 실패: {e}", exc_info=True)
            results.append({
                'page': element.get('page', 0),
                'caption': None,
                'error': str(e),
                'status': 'failed'
            })
    
    progress_bar.progress(1.0)
    status_text.text("✅ 처리 완료!")
    
    return {
        'session_id': session_id,
        'total': len(elements),
        'success': sum(1 for r in results if r['status'] == 'success'),
        'failed': sum(1 for r in results if r['status'] == 'failed'),
        'total_cost': total_cost,
        'total_time': total_time,
        'elements': results
    }


# ========== 메인 ==========
def main():
    # 헤더
    st.markdown("""
    <div class="main-header">
        <h1>🔷 PRISM</h1>
        <p>지능형 문서 이해 플랫폼</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    show_provider_selector()
    
    # 메인 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📁 문서 업로드")
        
        uploaded_file = st.file_uploader(
            "PDF 파일을 선택하세요",
            type=['pdf'],
            help="분석할 PDF 문서를 업로드하세요"
        )
        
        if uploaded_file:
            st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
            
            if st.button("🚀 분석 시작", type="primary"):
                pdf_bytes = uploaded_file.read()
                results = asyncio.run(process_pdf_async(pdf_bytes))
                
                if results:
                    st.session_state.processing_results = results
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💡 사용 가이드")
        st.markdown("""
        1. 좌측 사이드바에서 **VLM 모델** 선택
        2. **PDF 파일** 업로드
        3. **분석 시작** 버튼 클릭
        4. 결과 확인 및 다운로드
        
        **권장 사항:**
        - 파일 크기: 10MB 이하
        - 페이지 수: 10페이지 이하
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 결과 표시
    if st.session_state.processing_results:
        results = st.session_state.processing_results
        
        st.markdown("---")
        st.markdown("## 📊 분석 결과")
        
        # 요약 메트릭
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("총 페이지", results['total'])
        
        with col2:
            st.metric("성공", results['success'], delta=None)
        
        with col3:
            st.metric("실패", results['failed'], delta=None)
        
        with col4:
            st.metric("처리 시간", f"{results['total_time']:.1f}초")
        
        with col5:
            st.metric("비용", f"${results['total_cost']:.4f}")
        
        # 상세 결과
        st.markdown("### 📝 페이지별 결과")
        
        for idx, elem in enumerate(results['elements']):
            with st.expander(f"📄 페이지 {elem['page']}", expanded=(idx == 0)):
                if elem['status'] == 'success':
                    st.markdown(f"**🤖 AI 분석:**")
                    st.write(elem['caption'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"⭐ 신뢰도: {elem['confidence']:.2%}")
                        st.caption(f"⏱️ 처리시간: {elem['processing_time']:.2f}초")
                    
                    with col2:
                        st.caption(f"🤖 모델: {elem['provider']} - {elem['model']}")
                        st.caption(f"💰 비용: ${elem['cost_usd']:.4f}")
                    
                    if elem.get('ocr_text'):
                        with st.expander("📝 추출된 텍스트"):
                            st.text(elem['ocr_text'][:500] + "..." if len(elem['ocr_text']) > 500 else elem['ocr_text'])
                else:
                    st.error(f"❌ 처리 실패: {elem.get('error', '알 수 없는 오류')}")
        
        # 다운로드
        st.markdown("---")
        st.markdown("### 💾 결과 다운로드")
        
        import json
        results_json = json.dumps({
            'session_id': results['session_id'],
            'provider': st.session_state.vlm_service.get_current_provider().get_name(),
            'total': results['total'],
            'success': results['success'],
            'failed': results['failed'],
            'total_time': results['total_time'],
            'total_cost': results['total_cost'],
            'elements': results['elements']
        }, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📥 JSON 다운로드",
            data=results_json,
            file_name=f"prism_results_{results['session_id']}.json",
            mime="application/json"
        )


# ========== 실행 ==========
if __name__ == "__main__":
    main()
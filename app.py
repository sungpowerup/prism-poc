"""
PRISM POC - 메인 애플리케이션
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
    page_title="PRISM POC - 지능형 문서 이해",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========== CSS ==========
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .provider-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 2px solid #e0e0e0;
    }
    .provider-available {
        border-color: #4CAF50;
        background-color: #E8F5E9;
    }
    .provider-unavailable {
        border-color: #ccc;
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)


# ========== 세션 상태 초기화 ==========
if 'vlm_service' not in st.session_state:
    st.session_state.vlm_service = MultiVLMService()


# ========== 사이드바 - 프로바이더 선택 ==========
def show_provider_selector():
    """프로바이더 선택 UI"""
    st.sidebar.markdown("### 🤖 VLM 프로바이더 선택")
    
    vlm_service = st.session_state.vlm_service
    providers = vlm_service.get_available_providers()
    
    # 사용 가능한 프로바이더만 필터링
    available_providers = [p for p in providers if p['available']]
    
    if not available_providers:
        st.sidebar.error("⚠️ 사용 가능한 프로바이더가 없습니다!")
        
        with st.sidebar.expander("🔧 설정 가이드"):
            st.markdown("""
            **Claude 설정:**
            ```bash
            # .env
            ANTHROPIC_API_KEY=sk-ant-xxx
            ```
            
            **Azure OpenAI 설정:**
            ```bash
            # .env
            AZURE_OPENAI_API_KEY=xxx
            AZURE_OPENAI_ENDPOINT=https://xxx
            AZURE_OPENAI_DEPLOYMENT=gpt-4-vision
            ```
            
            **Ollama 설정:**
            ```bash
            ollama pull llava:7b
            ollama serve
            ```
            """)
        return
    
    # 현재 프로바이더
    current_key = vlm_service.current_provider_key
    current_idx = next((i for i, p in enumerate(available_providers) if p['key'] == current_key), 0)
    
    # 드롭다운
    provider_names = [p['name'] for p in available_providers]
    selected_name = st.sidebar.selectbox(
        "프로바이더",
        options=provider_names,
        index=current_idx,
        help="VLM 모델 제공자를 선택하세요"
    )
    
    # 선택된 프로바이더 정보
    selected_provider = next(p for p in available_providers if p['name'] == selected_name)
    
    # 프로바이더 변경
    if selected_provider['key'] != current_key:
        vlm_service.set_provider(selected_provider['key'])
        st.rerun()
    
    # 현재 프로바이더 정보 표시
    info = selected_provider['info']
    
    st.sidebar.success(f"**✅ {info['name']}**\n\n사용 중")
    
    # 상세 정보
    st.sidebar.info(
        f"**제공:** {info['provider']}\n\n"
        f"**속도:** {info['speed']}\n\n"
        f"**품질:** {info['quality']}\n\n"
        f"**비용:** {info['cost']}\n\n"
        f"**인터넷:** {info['internet']}\n\n"
        f"**GPU:** {info['gpu']}"
    )
    
    # 특별 정보
    if 'special' in info:
        st.sidebar.warning(f"ℹ️ {info['special']}")
    
    if 'vram' in info:
        st.sidebar.caption(f"💾 **필요 VRAM:** {info['vram']}")
    
    # 모든 프로바이더 상태
    with st.sidebar.expander("📋 전체 프로바이더 상태"):
        for provider in providers:
            icon = "✅" if provider['available'] else "❌"
            status = "사용 가능" if provider['available'] else "설정 필요"
            st.write(f"{icon} **{provider['name']}** - {status}")


# ========== 메인 ==========
def main():
    # 헤더
    st.markdown('<div class="main-header">🔷 PRISM POC - 지능형 문서 이해</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">멀티 프로바이더 지원: Claude + Azure OpenAI + Ollama</div>', unsafe_allow_html=True)
    
    # 사이드바 - 프로바이더 선택
    show_provider_selector()
    
    # 사이드바 - OCR 설정
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📝 처리 옵션")
    use_ocr = st.sidebar.checkbox(
        "OCR 사용",
        value=True,
        help="PDF에서 텍스트를 자동으로 추출하여 VLM 프롬프트에 포함합니다"
    )
    
    # 파일 업로드
    st.markdown("### 📄 PDF 파일 업로드")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "PDF 문서를 선택하세요",
            type=['pdf'],
            help="최대 200MB, 최대 20페이지"
        )
    
    with col2:
        if uploaded_file:
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.metric("파일 크기", f"{file_size:.1f} MB")
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하면 자동으로 처리가 시작됩니다")
        
        # 프로바이더 비교표
        with st.expander("📊 프로바이더 비교"):
            vlm_service = st.session_state.vlm_service
            providers = vlm_service.get_available_providers()
            
            st.markdown("""
            | 프로바이더 | 속도 | 품질 | 비용 | GPU | 인터넷 | 상태 |
            |-----------|------|------|------|-----|--------|------|
            """, unsafe_allow_html=True)
            
            for p in providers:
                info = p['info']
                status = "✅" if p['available'] else "❌"
                st.markdown(
                    f"| **{info['name']}** | {info['speed']} | {info['quality']} | "
                    f"{info['cost']} | {info['gpu']} | {info['internet']} | {status} |"
                )
        
        # 사용 가이드
        with st.expander("📖 사용 가이드"):
            st.markdown("""
            **처리 절차:**
            1. 왼쪽 사이드바에서 VLM 프로바이더 선택
            2. PDF 파일 업로드
            3. 자동으로 페이지별 이미지 추출
            4. OCR로 텍스트 추출 (선택)
            5. 선택한 VLM으로 분석
            6. 결과 확인 및 다운로드
            
            **프로바이더 선택 가이드:**
            - **Claude**: 최고 품질, 빠름, 유료 (일반 기업 권장)
            - **Azure OpenAI**: 우수 품질, 공공기관 승인 가능
            - **Ollama**: 무료, 오프라인, GPU 필요 (테스트용)
            
            **권장 설정:**
            - 파일 크기: 10MB 이하
            - 페이지 수: 10페이지 이하
            - OCR 사용: 텍스트가 많은 문서에 유용
            """)
        return
    
    # 세션 상태 초기화
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'results' not in st.session_state:
        st.session_state.results = None
    
    # 처리 시작 버튼
    if not st.session_state.processing and not st.session_state.results:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 처리 시작", type="primary", use_container_width=True):
                st.session_state.processing = True
                st.rerun()
    
    # 처리 중
    if st.session_state.processing:
        process_pdf(uploaded_file, use_ocr)
    
    # 결과 표시
    if st.session_state.results:
        show_results(st.session_state.results)


# ========== PDF 처리 ==========
async def process_pdf_async(pdf_bytes, use_ocr):
    """비동기 PDF 처리"""
    try:
        # 초기화
        processor = PDFProcessor()
        vlm_service = st.session_state.vlm_service
        
        # 현재 프로바이더 정보
        current_provider = vlm_service.get_current_provider()
        provider_name = current_provider.get_name()
        
        st.info(f"🤖 **{provider_name}** 사용 중...")
        
        # 세션 생성
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # PDF 처리
        logger.info(f"PDF 처리 시작: {session_id}")
        elements = processor.process_pdf(pdf_bytes)
        logger.info(f"추출된 Elements: {len(elements)}개")
        
        # 진행 상황 표시
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            time_text = st.empty()
        
        results = []
        start_time = datetime.now()
        
        for i, element in enumerate(elements):
            try:
                # 진행률 업데이트
                progress = (i + 1) / len(elements)
                progress_bar.progress(progress)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                eta = (elapsed / (i + 1)) * (len(elements) - i - 1) if i > 0 else 0
                
                status_text.text(
                    f"처리 중... ({i+1}/{len(elements)}) - "
                    f"페이지 {element.get('page', 0)} | {provider_name}"
                )
                time_text.caption(
                    f"⏱️ 경과: {elapsed:.0f}초 | "
                    f"예상 남은 시간: {eta:.0f}초"
                )
                
                logger.info(f"Element {i+1}/{len(elements)} 처리 중...")
                
                # OCR 텍스트 추출
                ocr_text = element.get('ocr_text', '') if use_ocr else ''
                
                # VLM 처리
                vlm_result = await vlm_service.generate_caption(
                    image_base64=element['image_base64'],
                    element_type=element.get('type', 'image'),
                    extracted_text=ocr_text
                )
                
                # 결과 저장
                element['vlm_caption'] = vlm_result['caption']
                element['vlm_confidence'] = vlm_result['confidence']
                element['processing_time'] = vlm_result.get('processing_time', 0)
                element['provider'] = vlm_result.get('provider', 'Unknown')
                element['model'] = vlm_result.get('model', 'Unknown')
                element['cost_usd'] = vlm_result.get('cost_usd', 0)
                element['status'] = 'success'
                
                results.append(element)
                
                logger.info(
                    f"Element {i+1} 처리 완료 "
                    f"({element['processing_time']:.1f}초, "
                    f"${element['cost_usd']:.4f})"
                )
                
            except Exception as e:
                logger.error(f"페이지 {element.get('page', 0)} 처리 실패: {e}", exc_info=True)
                element['status'] = 'failed'
                element['error'] = str(e)
                element['provider'] = provider_name
                results.append(element)
        
        total_time = (datetime.now() - start_time).total_seconds()
        total_cost = sum(r.get('cost_usd', 0) for r in results)
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ 처리 완료! (총 {total_time:.0f}초, ${total_cost:.4f})")
        time_text.empty()
        
        return {
            'session_id': session_id,
            'elements': results,
            'success': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') == 'failed']),
            'total': len(results),
            'total_time': total_time,
            'total_cost': total_cost,
            'provider': provider_name
        }
        
    except Exception as e:
        logger.error(f"PDF 처리 중 오류 발생: {e}", exc_info=True)
        st.error(f"❌ 처리 실패: {str(e)}")
        return None


def process_pdf(uploaded_file, use_ocr):
    """PDF 처리 래퍼"""
    try:
        pdf_bytes = uploaded_file.getvalue()
        
        # 비동기 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_pdf_async(pdf_bytes, use_ocr))
        loop.close()
        
        if result:
            st.session_state.results = result
            st.session_state.processing = False
            st.rerun()
        else:
            st.session_state.processing = False
            
    except Exception as e:
        logger.error(f"처리 실패: {e}", exc_info=True)
        st.error(f"❌ 오류 발생: {str(e)}")
        st.session_state.processing = False


# ========== 결과 표시 ==========
def show_results(results):
    """결과 표시"""
    st.markdown("---")
    st.markdown("## 📊 처리 결과")
    
    # 요약 통계
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("프로바이더", results.get('provider', 'N/A'))
    with col2:
        st.metric("전체", results['total'])
    with col3:
        st.metric("성공", results['success'])
    with col4:
        st.metric("실패", results['failed'])
    with col5:
        success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
        st.metric("성공률", f"{success_rate:.1f}%")
    with col6:
        st.metric("총 비용", f"${results.get('total_cost', 0):.4f}")
    
    # 처리 시간
    st.caption(f"⏱️ 총 처리 시간: {results.get('total_time', 0):.0f}초")
    
    # Element별 결과
    st.markdown("### 📋 Element 상세")
    
    for i, element in enumerate(results['elements']):
        status_icon = "✅" if element.get('status') == 'success' else "❌"
        
        with st.expander(
            f"{status_icon} Element {i+1} - Page {element.get('page', 0)} "
            f"({element.get('provider', 'Unknown')})",
            expanded=(i == 0)
        ):
            cols = st.columns([2, 3])
            
            with cols[0]:
                # 이미지 표시
                if element.get('image_base64'):
                    img_data = base64.b64decode(element['image_base64'])
                    st.image(img_data, caption=f"Page {element.get('page', 0)}", use_container_width=True)
            
            with cols[1]:
                # 상태
                if element.get('status') == 'success':
                    st.success(
                        f"✅ 처리 성공\n\n"
                        f"⏱️ {element.get('processing_time', 0):.1f}초 | "
                        f"💰 ${element.get('cost_usd', 0):.4f}"
                    )
                else:
                    st.error(f"❌ 처리 실패")
                    if element.get('error'):
                        st.code(element['error'], language="text")
                
                # VLM 캡션
                if element.get('vlm_caption'):
                    st.markdown("**🤖 AI 분석 결과:**")
                    st.write(element['vlm_caption'])
                    
                    # 메타데이터
                    st.caption(
                        f"🎯 신뢰도: {element.get('vlm_confidence', 0):.2%} | "
                        f"🤖 모델: {element.get('model', 'N/A')}"
                    )
                
                # OCR 텍스트
                if element.get('ocr_text'):
                    with st.expander("📝 OCR 추출 텍스트"):
                        ocr_text = element['ocr_text']
                        st.text(ocr_text[:500] + ("..." if len(ocr_text) > 500 else ""))
    
    # 액션 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 새 문서 처리", use_container_width=True):
            st.session_state.results = None
            st.session_state.processing = False
            st.rerun()
    
    with col2:
        # JSON 다운로드 (전체 캡션 포함)
        import json
        results_json = json.dumps({
            'session_id': results['session_id'],
            'provider': results.get('provider', 'Unknown'),
            'total': results['total'],
            'success': results['success'],
            'failed': results['failed'],
            'total_time': results.get('total_time', 0),
            'total_cost': results.get('total_cost', 0),
            'elements': [
                {
                    'page': e.get('page', 0),
                    'status': e.get('status', 'unknown'),
                    'provider': e.get('provider', 'Unknown'),
                    'model': e.get('model', 'Unknown'),
                    'caption': e.get('vlm_caption', ''),
                    'confidence': e.get('vlm_confidence', 0),
                    'processing_time': e.get('processing_time', 0),
                    'cost_usd': e.get('cost_usd', 0),
                    'ocr_text': e.get('ocr_text', ''),
                    'error': e.get('error', '') if e.get('status') == 'failed' else ''
                }
                for e in results['elements']
            ]
        }, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📥 결과 다운로드 (JSON)",
            data=results_json,
            file_name=f"prism_results_{results['session_id']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        st.link_button(
            label="📊 품질 대시보드",
            url="http://localhost:8502",
            use_container_width=True
        )


# ========== 실행 ==========
if __name__ == "__main__":
    main()
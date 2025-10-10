"""
PRISM POC - 메인 애플리케이션 (Ollama 전용, 안정화)
"""

import streamlit as st
import asyncio
import io
import os
import time
import base64
import logging
from datetime import datetime
from typing import Dict, List, Any

# Core 모듈
from core.pdf_processor import PDFProcessor
from core.vlm_service import VLMService
from core.storage import Storage

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
    .model-info-box {
        padding: 1rem;
        background-color: #f0f7ff;
        border-radius: 0.5rem;
        border: 1px solid #2196F3;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ========== 사이드바 - 모델 정보 ==========
def show_model_info():
    """Ollama 모델 정보 표시"""
    st.sidebar.markdown("### 🤖 VLM 모델 정보")
    
    try:
        vlm = VLMService()
        current = vlm.get_current_model()
        available = vlm.get_available_models()
        stats = vlm.get_stats()
        
        # 현재 모델
        st.sidebar.success(f"**현재 사용 중**\n\n{current}")
        
        # 모델 상세 정보
        model_info = {
            'llava:7b': {
                'vram': '4GB',
                'speed': '⚡ 빠름',
                'quality': '⭐⭐⭐ 보통',
                'timeout': '30초'
            },
            'llama3.2-vision:11b': {
                'vram': '8GB',
                'speed': '⚡⚡ 중간',
                'quality': '⭐⭐⭐⭐ 좋음',
                'timeout': '45초'
            },
            'llama3.2-vision:latest': {
                'vram': '8GB',
                'speed': '⚡⚡ 중간',
                'quality': '⭐⭐⭐⭐ 좋음',
                'timeout': '45초'
            }
        }
        
        if current in model_info:
            info = model_info[current]
            st.sidebar.info(
                f"**VRAM:** {info['vram']}\n\n"
                f"**속도:** {info['speed']}\n\n"
                f"**품질:** {info['quality']}\n\n"
                f"**타임아웃:** {info['timeout']}"
            )
        
        # 사용 가능한 모델 목록
        with st.sidebar.expander("📋 사용 가능한 모델"):
            if available:
                for model in available:
                    icon = "✅" if model == current else "⚪"
                    st.write(f"{icon} {model}")
                
                st.caption(f"총 {len(available)}개 모델 설치됨")
            else:
                st.write("사용 가능한 모델 없음")
        
        # 시스템 정보
        with st.sidebar.expander("⚙️ 시스템 설정"):
            st.code(f"""Provider: Ollama (Local)
Base URL: {stats.get('base_url', 'N/A')}
Timeout: {stats.get('timeout', 'N/A')}초
OCR 통합: ✅ 지원""", language="text")
        
        # 안내
        st.sidebar.markdown("---")
        st.sidebar.caption("💡 **Tip:** .env 파일에서 OLLAMA_MODEL을 변경하여 다른 모델을 사용할 수 있습니다.")
            
    except ConnectionError as e:
        st.sidebar.error(f"⚠️ **Ollama 연결 실패**")
        st.sidebar.code("ollama serve", language="bash")
        st.sidebar.caption("위 명령어로 Ollama를 실행하세요")
        
        with st.sidebar.expander("🔍 문제 해결 가이드"):
            st.markdown("""
            **1. Ollama 실행 확인**
            ```bash
            ollama ps
            ```
            
            **2. 모델 설치 확인**
            ```bash
            ollama list
            ```
            
            **3. 모델 다운로드**
            ```bash
            ollama pull llama3.2-vision:11b
            ```
            """)
            
    except Exception as e:
        st.sidebar.error(f"⚠️ **오류 발생**\n\n{str(e)}")


# ========== 메인 ==========
def main():
    # 헤더
    st.markdown('<div class="main-header">🔷 PRISM POC - 지능형 문서 이해</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">PDF 문서를 업로드하면 자동으로 분석합니다</div>', unsafe_allow_html=True)
    
    # 사이드바 - 모델 정보
    show_model_info()
    
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
        
        # 샘플 안내
        with st.expander("📖 사용 가이드"):
            st.markdown("""
            **처리 절차:**
            1. PDF 파일 업로드
            2. 자동으로 페이지별 이미지 추출
            3. OCR로 텍스트 추출 (선택)
            4. Ollama Vision 모델로 분석
            5. 결과 확인 및 다운로드
            
            **권장사항:**
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
        vlm_service = VLMService()
        
        # 세션 생성
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # PDF 처리
        logger.info(f"PDF 처리 시작: {session_id}")
        
        # ✅ 바이트 데이터 직접 전달
        elements = processor.process_pdf(pdf_bytes)
        
        logger.info(f"추출된 Elements: {len(elements)}개")
        
        # 진행 상황 표시
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            time_text = st.empty()
        
        results = []
        start_time = time.time()
        
        for i, element in enumerate(elements):
            try:
                # 진행률 업데이트
                progress = (i + 1) / len(elements)
                progress_bar.progress(progress)
                
                elapsed = time.time() - start_time
                eta = (elapsed / (i + 1)) * (len(elements) - i - 1) if i > 0 else 0
                
                status_text.text(f"처리 중... ({i+1}/{len(elements)}) - 페이지 {element.get('page', 0)}")
                time_text.caption(f"경과: {elapsed:.0f}초 | 예상 남은 시간: {eta:.0f}초")
                
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
                element['status'] = 'success'
                
                results.append(element)
                
                logger.info(f"Element {i+1} 처리 완료 ({element['processing_time']:.1f}초)")
                
            except Exception as e:
                logger.error(f"페이지 {element.get('page', 0)} 처리 실패: {e}", exc_info=True)
                element['status'] = 'failed'
                element['error'] = str(e)
                results.append(element)
        
        total_time = time.time() - start_time
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ 처리 완료! (총 {total_time:.0f}초)")
        time_text.empty()
        
        return {
            'session_id': session_id,
            'elements': results,
            'success': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') == 'failed']),
            'total': len(results),
            'total_time': total_time
        }
        
    except Exception as e:
        logger.error(f"PDF 처리 중 오류 발생: {e}", exc_info=True)
        st.error(f"❌ 처리 실패: {str(e)}")
        return None


def process_pdf(uploaded_file, use_ocr):
    """PDF 처리 래퍼"""
    try:
        # ✅ 바이트 데이터 읽기
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
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("전체 Elements", results['total'])
    with col2:
        st.metric("처리 성공", results['success'], delta=None, delta_color="normal")
    with col3:
        st.metric("처리 실패", results['failed'], delta=None, delta_color="inverse")
    with col4:
        success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0
        st.metric("성공률", f"{success_rate:.1f}%")
    with col5:
        st.metric("처리 시간", f"{results.get('total_time', 0):.0f}초")
    
    # Element별 결과
    st.markdown("### 📋 Element 상세")
    
    for i, element in enumerate(results['elements']):
        with st.expander(
            f"📄 Element {i+1} - Page {element.get('page', 0)} "
            f"({'✅ 성공' if element.get('status') == 'success' else '❌ 실패'})",
            expanded=(i == 0)  # 첫 번째만 열기
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
                    st.success(f"✅ 처리 성공 ({element.get('processing_time', 0):.1f}초)")
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
                        f"신뢰도: {element.get('vlm_confidence', 0):.2%} | "
                        f"처리시간: {element.get('processing_time', 0):.1f}초"
                    )
                
                # OCR 텍스트 (있는 경우)
                if element.get('ocr_text'):
                    with st.expander("📝 OCR 추출 텍스트"):
                        st.text(element['ocr_text'][:500] + ("..." if len(element['ocr_text']) > 500 else ""))
    
    # 액션 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 새 문서 처리", use_container_width=True):
            st.session_state.results = None
            st.session_state.processing = False
            st.rerun()
    
    with col2:
        # JSON 다운로드 (간소화)
        import json
        results_json = json.dumps({
            'session_id': results['session_id'],
            'total': results['total'],
            'success': results['success'],
            'failed': results['failed']
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
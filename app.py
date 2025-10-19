"""
PRISM POC - 하이브리드 청킹 지원
VLM 이미지 분석 + OCR 원문 청킹
"""

import streamlit as st
import os
import json
import base64
import logging
from datetime import datetime
from typing import Dict, List, Any
from io import BytesIO

# ========== 환경변수 강제 로드 (최우선) ==========
from pathlib import Path
from dotenv import load_dotenv

# 현재 파일 위치 기준으로 .env 로드
current_dir = Path(__file__).parent
env_path = current_dir / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ .env 파일 로드: {env_path}")
else:
    print(f"⚠️ .env 파일 없음: {env_path}")

# API 키 확인
api_key = os.getenv('ANTHROPIC_API_KEY')
if api_key:
    print(f"✅ Claude API 키 로드 성공: {api_key[:20]}...")
else:
    print("❌ Claude API 키 로드 실패!")
# ==================================================

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
    page_title="PRISM - Document Intelligence Platform",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS (전체 너비 사용) ==========
st.markdown("""
<style>
    /* 전체 컨테이너 너비 */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* 사이드바 스타일 */
    .sidebar-title {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-subtitle {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    
    /* 프로바이더 카드 */
    .provider-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 2px solid #e0e0e0;
        background-color: #f9f9f9;
    }
    
    .provider-available {
        border-color: #4CAF50;
        background-color: #E8F5E9;
    }
    
    /* 청크 카드 */
    .chunk-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: white;
    }
    
    .chunk-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .chunk-type-image {
        background: #E3F2FD;
        color: #1976D2;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    
    .chunk-type-text {
        background: #F3E5F5;
        color: #7B1FA2;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    
    /* 다운로드 버튼 영역 */
    .download-section {
        margin-top: 2rem;
        padding: 1.5rem;
        background: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# ========== 유틸리티 함수 ==========

def text_chunking(text: str, min_length: int = 100, max_length: int = 500, overlap: int = 50) -> List[str]:
    """
    텍스트를 의미 단위로 청킹
    
    Args:
        text: 원본 텍스트
        min_length: 최소 청크 길이
        max_length: 최대 청크 길이
        overlap: 청크 간 오버랩 길이
    
    Returns:
        청크 리스트
    """
    if not text or len(text.strip()) == 0:
        return []
    
    # 단락 분리
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # 현재 청크에 추가했을 때 max_length를 초과하면
        if len(current_chunk) + len(para) > max_length:
            if len(current_chunk) >= min_length:
                chunks.append(current_chunk.strip())
                # 오버랩 적용
                current_chunk = current_chunk[-overlap:] + " " + para
            else:
                current_chunk += " " + para
        else:
            current_chunk += " " + para if current_chunk else para
    
    # 마지막 청크
    if current_chunk.strip() and len(current_chunk.strip()) >= min_length:
        chunks.append(current_chunk.strip())
    
    return chunks

def convert_to_json(chunks: List[Dict]) -> Dict:
    """JSON 형식으로 변환"""
    data = {
        'metadata': {
            'processed_at': datetime.now().isoformat(),
            'total_chunks': len(chunks),
            'chunk_types': {
                'image': len([c for c in chunks if c['type'] == 'image']),
                'text': len([c for c in chunks if c['type'] == 'text'])
            }
        },
        'chunks': chunks
    }
    return data

def convert_to_markdown(chunks: List[Dict]) -> str:
    """Markdown 형식으로 변환"""
    md_lines = []
    md_lines.append("# PRISM 문서 추출 결과\n")
    md_lines.append(f"**처리 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 통계
    md_lines.append("## 📊 통계\n")
    md_lines.append(f"- 총 청크: {len(chunks)}")
    md_lines.append(f"- 이미지 청크: {len([c for c in chunks if c['type'] == 'image'])}")
    md_lines.append(f"- 텍스트 청크: {len([c for c in chunks if c['type'] == 'text'])}\n")
    
    # 청크별 내용
    current_page = None
    
    for chunk in chunks:
        page_num = chunk.get('page_num', 0)
        
        # 페이지 헤더
        if page_num != current_page:
            current_page = page_num
            md_lines.append(f"\n## 📄 페이지 {page_num}\n")
        
        chunk_id = chunk.get('chunk_id', '')
        chunk_type = chunk.get('type', 'unknown')
        content = chunk.get('content', '')
        
        # 청크 헤더
        if chunk_type == 'image':
            md_lines.append(f"### 🖼️ {chunk_id} (VLM 분석)\n")
        else:
            md_lines.append(f"### 📝 {chunk_id} (원문)\n")
        
        md_lines.append(content)
        md_lines.append("\n---\n")
    
    return "\n".join(md_lines)

# ========== 세션 초기화 ==========

if 'vlm_service' not in st.session_state:
    try:
        default_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
        st.session_state.vlm_service = MultiVLMService(default_provider=default_provider)
    except Exception as e:
        st.session_state.vlm_service = None

if 'pdf_processor' not in st.session_state:
    try:
        st.session_state.pdf_processor = PDFProcessor()
    except Exception as e:
        st.session_state.pdf_processor = None

if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None

# ========== 메인 UI ==========

def main():
    # 사이드바
    with st.sidebar:
        st.markdown('<div class="sidebar-title">PRISM</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-subtitle">Document Intelligence Platform</div>', unsafe_allow_html=True)
        
        st.markdown("### 🤖 모델 설정")
        
        if st.session_state.vlm_service is not None:
            vlm_service = st.session_state.vlm_service
            
            current_provider = getattr(vlm_service, 'current_provider_key', None)
            if current_provider is None:
                current_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
            
            providers_status = vlm_service.get_available_providers()
            
            provider_display_names = {
                'claude': '🟣 Claude Sonnet 4',
                'azure_openai': '🔵 Azure OpenAI GPT-4',
                'ollama': '🟢 Ollama'
            }
            
            provider_options = []
            provider_mapping = {}
            
            for key in ['claude', 'azure_openai', 'ollama']:
                if key in providers_status:
                    info = providers_status[key]
                    is_available = info.get('available', False)
                    
                    display_name = provider_display_names.get(key, key)
                    if not is_available:
                        display_name += " (설정 필요)"
                    
                    provider_options.append(display_name)
                    provider_mapping[display_name] = {
                        'key': key,
                        'available': is_available
                    }
            
            selected_display = st.selectbox(
                "VLM 프로바이더",
                options=provider_options,
                index=[i for i, opt in enumerate(provider_options) 
                      if provider_mapping[opt]['key'] == current_provider][0] if provider_options else 0
            )
            
            if selected_display and selected_display in provider_mapping:
                selected_key = provider_mapping[selected_display]['key']
                is_available = provider_mapping[selected_display]['available']
                
                if is_available and selected_key != current_provider:
                    vlm_service.set_provider(selected_key)
                    st.rerun()
                
                if is_available:
                    st.success(f"✅ {selected_display.split('(')[0].strip()} 사용 가능")
                else:
                    st.error(f"⚠️ 설정이 필요합니다")
            
            st.divider()
            
            # 처리 설정
            st.markdown("### ⚙️ 처리 설정")
            
            max_pages = st.slider(
                "최대 페이지 수",
                min_value=1,
                max_value=20,
                value=3,
                help="처리할 최대 페이지 수"
            )
            
            use_text_chunking = st.checkbox(
                "원문 청킹 활성화",
                value=True,
                help="OCR 텍스트를 의미 단위로 분할"
            )
            
            if use_text_chunking:
                st.caption("📝 원문을 100-500자 단위로 분할하여 RAG에 최적화")
    
    # 메인 영역
    st.title("📄 PRISM")
    st.caption("지능형 문서 이해 플랫폼")
    
    # 이전 처리 결과 표시
    if st.session_state.processing_results is not None:
        st.success("✅ 이전 처리 결과가 있습니다. 새 문서를 업로드하면 기존 결과가 대체됩니다.")
        display_results(st.session_state.processing_results)
        st.markdown("---")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 업로드하세요",
        type=['pdf'],
        help="최대 200MB, 최대 20페이지"
    )
    
    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.info(f"📄 **{uploaded_file.name}** ({file_size_mb:.1f} MB)")
        with col2:
            use_ocr = st.checkbox("OCR 사용", value=True)
        with col3:
            vlm_service = st.session_state.vlm_service
            if vlm_service:
                current_provider_key = getattr(vlm_service, 'current_provider_key', None)
                
                # 현재 선택된 프로바이더가 사용 가능한지 확인
                if current_provider_key:
                    providers_status = vlm_service.get_available_providers()
                    is_available = providers_status.get(current_provider_key, {}).get('available', False)
                    
                    if is_available:
                        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
                            process_file(uploaded_file, max_pages, use_ocr, use_text_chunking)
                    else:
                        st.button("⚠️ 모델 설정 필요", disabled=True, use_container_width=True)
                        st.caption("왼쪽 사이드바에서 모델을 설정하세요")
                else:
                    st.button("⚠️ 프로바이더 선택 필요", disabled=True, use_container_width=True)
            else:
                st.button("⚠️ 서비스 초기화 실패", disabled=True, use_container_width=True)

def process_file(uploaded_file, max_pages, use_ocr, use_text_chunking):
    """파일 처리"""
    pdf_processor = st.session_state.pdf_processor
    vlm_service = st.session_state.vlm_service
    
    if vlm_service is None:
        st.error("VLM 서비스를 사용할 수 없습니다.")
        return
    
    progress_bar = st.progress(0)
    status = st.empty()
    
    try:
        # PDF 처리
        status.text("📄 PDF 처리 중...")
        file_bytes = uploaded_file.read()
        
        elements = pdf_processor.process_pdf(pdf_data=file_bytes)
        
        logger.info(f"추출된 Elements 수: {len(elements)}")
        
        if not elements:
            st.warning("추출된 Element가 없습니다.")
            return
        
        # 최대 페이지 제한
        elements = [e for e in elements if e['page_num'] <= max_pages]
        
        if not elements:
            st.warning(f"페이지 {max_pages} 이하에 Element가 없습니다.")
            return
        
        total_elements = len(elements)
        st.info(f"총 {total_elements}개 Element 처리 예정 (최대 {max_pages}페이지)")
        
        # 하이브리드 청킹 처리
        all_chunks = []
        chunk_counter = 1
        
        for idx, element in enumerate(elements):
            progress = (idx + 1) / total_elements
            progress_bar.progress(progress)
            status.text(f"처리 중... ({idx + 1}/{total_elements})")
            
            page_num = element['page_num']
            ocr_text = element.get('ocr_text', '')
            image_base64 = element.get('image_base64', '')
            
            # 1. IMAGE 청크 (VLM 분석)
            status.text(f"🤖 페이지 {page_num} VLM 분석 중...")
            
            try:
                if image_base64:
                    vlm_response = vlm_service.analyze_image(
                        image_base64=image_base64,
                        prompt=f"이 문서 페이지의 내용을 한국어로 상세히 설명해주세요. OCR 텍스트: {ocr_text[:200] if ocr_text else '없음'}"
                    )
                    
                    image_chunk = {
                        'chunk_id': f"chunk_{chunk_counter:03d}",
                        'type': 'image',
                        'page_num': page_num,
                        'content': vlm_response,
                        'provider': vlm_service.current_provider_key,
                        'ocr_text_preview': ocr_text[:100] if ocr_text else None
                    }
                    all_chunks.append(image_chunk)
                    chunk_counter += 1
            
            except Exception as e:
                logger.error(f"VLM 처리 오류: {e}")
                st.warning(f"⚠️ 페이지 {page_num} VLM 처리 실패")
            
            # 2. TEXT 청크 (OCR 원문 청킹)
            if use_text_chunking and use_ocr and ocr_text:
                status.text(f"📝 페이지 {page_num} 원문 청킹 중...")
                
                text_chunks = text_chunking(ocr_text)
                
                for sub_idx, text_chunk in enumerate(text_chunks, 1):
                    text_chunk_obj = {
                        'chunk_id': f"chunk_{chunk_counter:03d}",
                        'type': 'text',
                        'page_num': page_num,
                        'sub_index': sub_idx,
                        'content': text_chunk,
                        'length': len(text_chunk)
                    }
                    all_chunks.append(text_chunk_obj)
                    chunk_counter += 1
        
        # 처리 완료
        progress_bar.progress(1.0)
        status.text("✅ 처리 완료!")
        
        st.session_state.processing_results = all_chunks
        
        st.success(f"✨ 총 {len(all_chunks)}개 청크 생성 완료!")
        
        # 결과 표시
        display_results(all_chunks)
        
    except Exception as e:
        logger.error(f"처리 오류: {e}", exc_info=True)
        st.error(f"❌ 처리 실패: {str(e)}")

def display_results(chunks: List[Dict]):
    """처리 결과 표시"""
    
    st.markdown("---")
    st.markdown("## 📊 처리 결과")
    
    # 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 청크", len(chunks))
    
    with col2:
        image_chunks = len([c for c in chunks if c['type'] == 'image'])
        st.metric("이미지 청크", image_chunks)
    
    with col3:
        text_chunks = len([c for c in chunks if c['type'] == 'text'])
        st.metric("텍스트 청크", text_chunks)
    
    with col4:
        pages = len(set(c['page_num'] for c in chunks))
        st.metric("페이지 수", pages)
    
    # 다운로드 버튼
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("### 💾 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        json_data = convert_to_json(chunks)
        json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        md_str = convert_to_markdown(chunks)
        
        st.download_button(
            label="📥 Markdown 다운로드",
            data=md_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 청크 상세 표시
    st.markdown("---")
    st.markdown("### 📋 청크 목록")
    
    # 필터
    col1, col2 = st.columns([1, 3])
    
    with col1:
        filter_type = st.selectbox(
            "청크 타입",
            options=['전체', '이미지', '텍스트'],
            index=0
        )
    
    # 필터링
    filtered_chunks = chunks
    if filter_type == '이미지':
        filtered_chunks = [c for c in chunks if c['type'] == 'image']
    elif filter_type == '텍스트':
        filtered_chunks = [c for c in chunks if c['type'] == 'text']
    
    st.info(f"📋 {len(filtered_chunks)}개 청크 표시 중")
    
    # 청크 카드 표시
    for chunk in filtered_chunks:
        chunk_id = chunk['chunk_id']
        chunk_type = chunk['type']
        page_num = chunk['page_num']
        content = chunk['content']
        
        # 청크 카드
        with st.expander(
            f"{'🖼️' if chunk_type == 'image' else '📝'} {chunk_id} | 페이지 {page_num} | {chunk_type.upper()}",
            expanded=False
        ):
            # 메타데이터
            st.markdown(f"**페이지:** {page_num}")
            st.markdown(f"**타입:** {chunk_type}")
            
            if chunk_type == 'image':
                provider = chunk.get('provider', 'unknown')
                st.markdown(f"**프로바이더:** {provider}")
            elif chunk_type == 'text':
                sub_index = chunk.get('sub_index', 1)
                length = chunk.get('length', 0)
                st.markdown(f"**서브 인덱스:** {sub_index}")
                st.markdown(f"**길이:** {length}자")
            
            st.markdown("---")
            
            # 내용
            st.markdown("**내용:**")
            st.text_area(
                label="",
                value=content,
                height=200,
                key=f"content_{chunk_id}",
                label_visibility="collapsed"
            )

# 실행
if __name__ == "__main__":
    main()
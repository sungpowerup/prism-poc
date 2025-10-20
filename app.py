# app.py

import streamlit as st
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드: {env_path}")
    
    # Claude API 키 확인
    claude_key = os.getenv('ANTHROPIC_API_KEY', '')
    if claude_key:
        print(f"✅ Claude API 키 로드 성공: {claude_key[:20]}...")
    else:
        print("⚠️ Claude API 키가 없습니다")
else:
    print(f"⚠️ .env 파일을 찾을 수 없습니다: {env_path}")

from core.multi_vlm_service import MultiVLMService
from core.pdf_processor import PDFProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="PRISM",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 변수로 서비스 초기화
if 'vlm_service' not in st.session_state:
    default_provider = os.getenv('DEFAULT_VLM_PROVIDER', 'claude')
    st.session_state.vlm_service = MultiVLMService(default_provider=default_provider)

if 'pdf_processor' not in st.session_state:
    st.session_state.pdf_processor = PDFProcessor(vlm_service=st.session_state.vlm_service)

vlm_service = st.session_state.vlm_service
pdf_processor = st.session_state.pdf_processor

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .chunk-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .chunk-header {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .chunk-meta {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 1rem;
    }
    .download-section {
        background-color: #e8f4f8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

def display_results(results):
    """처리 결과 표시"""
    
    # 메타데이터 표시
    st.markdown("### 📊 처리 결과 요약")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("총 청크 수", results['metadata']['total_chunks'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        chunk_types = results['metadata']['chunk_types']
        st.metric("이미지 청크", chunk_types.get('image', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("텍스트 청크", chunk_types.get('text', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 청크별 상세 내용
    st.markdown("### 📄 페이지별 분석 결과")
    
    for chunk in results['chunks']:
        with st.container():
            st.markdown('<div class="chunk-card">', unsafe_allow_html=True)
            
            # 헤더
            st.markdown(
                f'<div class="chunk-header">페이지 {chunk["page_num"]} - {chunk["type"].upper()}</div>',
                unsafe_allow_html=True
            )
            
            # 메타 정보
            meta_info = f"청크 ID: {chunk['chunk_id']}"
            if chunk.get('provider'):
                meta_info += f" | VLM: {chunk['provider']}"
            
            st.markdown(
                f'<div class="chunk-meta">{meta_info}</div>',
                unsafe_allow_html=True
            )
            
            # 내용
            if chunk.get('content'):
                st.markdown(chunk['content'])
            
            # OCR 텍스트 미리보기 (있는 경우)
            if chunk.get('ocr_text_preview'):
                with st.expander("🔍 OCR 추출 텍스트 미리보기"):
                    st.text(chunk['ocr_text_preview'])
            
            st.markdown('</div>', unsafe_allow_html=True)

def create_markdown_export(results):
    """마크다운 형식으로 내보내기"""
    md_lines = []
    
    # 헤더
    md_lines.append("# PRISM 문서 분석 결과\n")
    md_lines.append(f"**처리 시간**: {results['metadata']['processed_at']}\n")
    md_lines.append(f"**총 청크 수**: {results['metadata']['total_chunks']}\n")
    md_lines.append("\n---\n")
    
    # 각 청크
    for chunk in results['chunks']:
        md_lines.append(f"\n## 페이지 {chunk['page_num']}\n")
        md_lines.append(f"**청크 ID**: {chunk['chunk_id']}  ")
        md_lines.append(f"**타입**: {chunk['type']}  ")
        
        if chunk.get('provider'):
            md_lines.append(f"**VLM**: {chunk['provider']}  ")
        
        md_lines.append("\n")
        
        if chunk.get('content'):
            md_lines.append(chunk['content'])
            md_lines.append("\n")
        
        if chunk.get('ocr_text_preview'):
            md_lines.append("\n### OCR 추출 텍스트\n")
            md_lines.append("```")
            md_lines.append(chunk['ocr_text_preview'])
            md_lines.append("```\n")
        
        md_lines.append("\n---\n")
    
    return '\n'.join(md_lines)

def sidebar_settings():
    """사이드바 설정"""
    with st.sidebar:
        st.markdown('<div class="main-header">🎯 모델 설정</div>', unsafe_allow_html=True)
        
        # VLM 프로바이더 선택
        st.markdown("### VLM 프로바이더")
        
        current_provider = vlm_service.get_current_provider()
        provider_options = {
            'claude': '🤖 Claude Sonnet 4',
            'azure_openai': '🔷 Azure OpenAI GPT-4',
            'ollama': '🦙 Ollama (Local)'
        }
        
        selected_provider = st.selectbox(
            "",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            index=list(provider_options.keys()).index(current_provider),
            key="provider_select"
        )
        
        if selected_provider != current_provider:
            vlm_service.set_provider(selected_provider)
            st.success(f"✅ {provider_options[selected_provider]}로 변경되었습니다")
        
        # 프로바이더 상태 표시
        st.markdown("#### 사용 가능한 프로바이더")
        for provider, display_name in provider_options.items():
            status = vlm_service.provider_status.get(provider, {})
            if status.get('available'):
                st.markdown(f"✅ {display_name}")
            else:
                error_msg = status.get('error', '알 수 없는 오류')
                st.markdown(f"❌ {display_name}")
                st.caption(f"   {error_msg}")
        
        st.markdown("---")
        
        # 처리 설정
        st.markdown('<div class="main-header">⚙️ 처리 설정</div>', unsafe_allow_html=True)
        
        max_pages = st.number_input(
            "최대 페이지 수",
            min_value=1,
            max_value=20,
            value=20,
            help="처리할 최대 페이지 수를 설정합니다"
        )
        
        use_ocr = st.checkbox(
            "OCR 사용",
            value=True,
            help="PaddleOCR을 사용하여 텍스트를 추출합니다"
        )
        
        use_text_chunking = st.checkbox(
            "원본 청킹 활성화",
            value=True,
            help="원본을 100-500자 단위로 분할합니다"
        )
        
        st.markdown("---")
        
        # 정보 표시
        st.markdown("### ℹ️ 정보")
        st.info("""
        **PRISM POC**
        
        차세대 지능형 문서 이해 플랫폼
        
        - 다중 VLM 지원
        - OCR 통합
        - 지능형 청킹
        """)
        
        return max_pages, use_ocr, use_text_chunking

def process_file(uploaded_file, max_pages, use_ocr, use_text_chunking):
    """파일 처리 함수"""
    try:
        # 파일 읽기
        file_bytes = uploaded_file.read()
        
        # 진행 상태 표시
        progress_placeholder = st.empty()
        
        def update_progress(message, progress):
            progress_placeholder.info(f"{message} ({progress}%)")
        
        # PDF 처리
        logger.info("PDF 처리 시작")
        elements = pdf_processor.process_pdf(
            pdf_data=file_bytes,
            use_ocr=use_ocr,
            progress_callback=update_progress
        )
        
        logger.info(f"추출된 청크 수: {len(elements)}")
        
        # 페이지 필터링
        if max_pages > 0:
            elements = [e for e in elements if e.get('page_num', 0) <= max_pages]
            logger.info(f"필터링 후 청크 수: {len(elements)}")
        
        # 결과 구성
        results = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "total_chunks": len(elements),
                "chunk_types": {}
            },
            "chunks": elements  # ← 핵심 수정: elements를 chunks에 할당
        }
        
        # 타입별 카운트
        for element in elements:
            elem_type = element.get('type', 'unknown')
            results["metadata"]["chunk_types"][elem_type] = \
                results["metadata"]["chunk_types"].get(elem_type, 0) + 1
        
        # 세션에 저장
        st.session_state.processing_results = results
        st.session_state.processed = True
        
        progress_placeholder.success("✅ 처리 완료!")
        
        # 결과 표시
        display_results(results)
        
    except Exception as e:
        logger.error(f"처리 오류: {e}", exc_info=True)
        st.error(f"❌ 처리 실패: {str(e)}")

def main():
    """메인 함수"""
    
    # 헤더
    st.markdown('<div class="main-header">PRISM</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">차세대 지능형 문서 이해 플랫폼</div>', unsafe_allow_html=True)
    
    # 사이드바 설정
    max_pages, use_ocr, use_text_chunking = sidebar_settings()
    
    # 파일 업로드
    st.markdown("### 📄 PDF 파일을 업로드하세요")
    
    uploaded_file = st.file_uploader(
        "",
        type=['pdf'],
        help="PDF 파일을 드래그하거나 클릭하여 업로드하세요 (최대 200MB)"
    )
    
    if uploaded_file:
        # 파일 정보 표시
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info(f"📎 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        with col2:
            if st.button("🚀 처리 시작", type="primary", use_container_width=True):
                process_file(uploaded_file, max_pages, use_ocr, use_text_chunking)
    
    # 결과가 있으면 다운로드 섹션 표시
    if st.session_state.get('processed', False) and st.session_state.get('processing_results'):
        st.markdown("---")
        st.markdown('<div class="download-section">', unsafe_allow_html=True)
        st.markdown("### 📥 PDF 처리 종료 ...")
        
        results = st.session_state.processing_results
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # JSON 다운로드
            json_str = json.dumps(results, ensure_ascii=False, indent=2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            st.download_button(
                label="📄 JSON 다운로드",
                data=json_str,
                file_name=f"prism_result_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # Markdown 다운로드
            md_content = create_markdown_export(results)
            
            st.download_button(
                label="📝 Markdown 다운로드",
                data=md_content,
                file_name=f"prism_result_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col3:
            # 새로 시작
            if st.button("🔄 새로 시작", use_container_width=True):
                st.session_state.processed = False
                st.session_state.processing_results = None
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
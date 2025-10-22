"""
PRISM Phase 3.2 - Streamlit 앱 (환경 변수 로딩 수정)

✅ 주요 기능:
1. 간결한 VLM 프롬프트 (368자 → 30자)
2. OCR 텍스트 추출 통합
3. RAG 최적화 청킹
4. 실시간 검증 및 피드백

Author: 최동현 (Frontend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-22
Version: 3.2 (Fixed)
"""

import streamlit as st
from pathlib import Path
import json
import time
from datetime import datetime
import os

# ✅ 환경 변수 로딩 (최우선 - Streamlit보다 먼저!)
from dotenv import load_dotenv
load_dotenv()

# 환경 변수 확인 및 로깅
AZURE_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Phase 3.2 모듈
try:
    from core.phase32_pipeline import Phase32Pipeline
    PHASE32_AVAILABLE = True
except ImportError as e:
    PHASE32_AVAILABLE = False
    st.error(f"⚠️ Phase 3.2 모듈 없음: {e}")

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

# 메인 함수
def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown(
        '<div class="main-header">🎯 PRISM Phase 3.2'
        '<span class="phase-badge">Concise + OCR</span></div>',
        unsafe_allow_html=True
    )
    
    # Phase 3.2 개선사항
    st.markdown("""
    <div class="improvement-box">
        <h3 style="margin-top:0;">✨ Phase 3.2 주요 개선사항</h3>
        <ul style="margin-bottom:0;">
            <li><strong>초간결 프롬프트</strong>: "Describe the chart data in 2-3 sentences" (30자)</li>
            <li><strong>OCR 통합</strong>: VLM 실패 시 자동 OCR 텍스트 추출</li>
            <li><strong>빠른 처리</strong>: 프롬프트 단순화로 응답 시간 단축</li>
            <li><strong>검증 강화</strong>: 실시간 VLM 응답 유효성 검증</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 🤖 VLM 설정")
        
        # VLM 프로바이더 선택
        available_providers = []
        if AZURE_API_KEY and AZURE_ENDPOINT and AZURE_DEPLOYMENT:
            available_providers.append('azure_openai')
        if ANTHROPIC_API_KEY:
            available_providers.append('claude')
        
        if not available_providers:
            st.error("""
            ❌ 사용 가능한 VLM 프로바이더가 없습니다!
            
            .env 파일을 확인하세요:
            - AZURE_OPENAI_API_KEY
            - AZURE_OPENAI_ENDPOINT
            - AZURE_OPENAI_DEPLOYMENT
            또는
            - ANTHROPIC_API_KEY
            """)
            st.stop()
        
        vlm_provider = st.selectbox(
            "프로바이더",
            options=available_providers,
            index=0,
            help="Azure OpenAI 권장 (가장 안정적)",
            format_func=lambda x: x.upper()
        )
        
        # 환경 변수 상태 표시
        with st.expander("🔍 환경 변수 상태"):
            st.text(f"Azure API Key: {'✅' if AZURE_API_KEY else '❌'}")
            st.text(f"Azure Endpoint: {'✅' if AZURE_ENDPOINT else '❌'}")
            st.text(f"Azure Deployment: {'✅' if AZURE_DEPLOYMENT else '❌'}")
            st.text(f"Anthropic API Key: {'✅' if ANTHROPIC_API_KEY else '❌'}")
        
        st.markdown("---")
        
        st.markdown("### ⚙️ 처리 옵션")
        
        max_pages = st.number_input(
            "최대 페이지",
            min_value=1,
            max_value=50,
            value=3,
            help="처리할 최대 페이지 수"
        )
        
        use_ocr = st.checkbox(
            "OCR 백업 활성화",
            value=True,
            help="VLM 실패 시 OCR 텍스트 추출"
        )
        
        use_concise = st.checkbox(
            "간결한 프롬프트",
            value=True,
            help="30자 프롬프트 사용 (빠름)"
        )
        
        st.markdown("---")
        
        st.markdown("### 📖 사용 방법")
        st.markdown("""
        1. PDF 파일 업로드
        2. VLM 프로바이더 선택
        3. '처리 시작' 클릭
        4. 결과 확인
           - 📊 감지된 영역
           - 🧩 생성된 청크
        5. JSON/MD 다운로드
        """)
        
        st.markdown("---")
        st.markdown("### 🎯 Phase 3.2 특징")
        st.markdown("""
        - ✅ 초간결 프롬프트 (30자)
        - ✅ OCR 백업 (텍스트 추출)
        - ✅ 빠른 처리 속도
        - ✅ 실시간 검증
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
            process_pdf(uploaded_file, vlm_provider, max_pages, use_ocr, use_concise)
    
    # 결과 표시
    if 'result' in st.session_state:
        display_results(st.session_state.result)


def process_pdf(uploaded_file, vlm_provider, max_pages, use_ocr, use_concise):
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
        
        # 파이프라인 초기화
        status_text.text("⚙️ Phase 3.2 파이프라인 초기화 중...")
        progress_bar.progress(20)
        
        pipeline = Phase32Pipeline(
            vlm_provider=vlm_provider,
            use_ocr=use_ocr,
            use_concise_prompts=use_concise
        )
        
        # 문서 처리
        status_text.text("🔄 문서 처리 중... (2~5분 소요)")
        progress_bar.progress(30)
        
        result = pipeline.process_pdf(str(pdf_path), max_pages=max_pages)
        
        # 완료
        progress_bar.progress(100)
        status_text.text("✅ 처리 완료!")
        
        # 결과 저장
        st.session_state.result = result
        
        st.success(f"""
        ✅ Phase 3.2 처리 완료!
        - 총 페이지: {result['metadata']['total_pages']}개
        - 감지된 영역: {result['metadata']['total_regions']}개
        - 생성된 청크: {result['metadata']['total_chunks']}개
        """)
        
        st.balloons()
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {e}")
        
        with st.expander("🔍 상세 에러 정보"):
            import traceback
            st.code(traceback.format_exc())


def display_results(result):
    """결과 표시"""
    
    st.divider()
    st.header("📊 처리 결과")
    
    metadata = result['metadata']
    
    # 메타데이터
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("페이지", metadata['total_pages'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("영역", metadata['total_regions'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("청크", metadata['total_chunks'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("처리 시간", f"{metadata['processing_time_sec']}초")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Phase", "3.2")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 설정 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**VLM**: {metadata['vlm_provider']}")
    with col2:
        status = "✅ 활성" if metadata.get('ocr_enabled', False) else "❌ 비활성"
        st.info(f"**OCR**: {status}")
    with col3:
        status = "✅ 활성" if metadata.get('concise_prompts', False) else "❌ 비활성"
        st.info(f"**간결 프롬프트**: {status}")
    
    # 청크 표시
    st.divider()
    st.header("🧩 생성된 청크")
    
    chunks = result.get('chunks', [])
    
    for i, chunk in enumerate(chunks, start=1):
        with st.expander(f"청크 #{i} - {chunk.get('chunk_type', 'unknown')}"):
            st.markdown(f"**페이지**: {chunk.get('page_number', 'N/A')}")
            st.markdown(f"**타입**: {chunk.get('chunk_type', 'unknown')}")
            st.markdown(f"**소스**: {chunk.get('source_type', 'N/A')}")
            
            if chunk.get('ocr_extracted'):
                st.warning("⚠️ OCR 텍스트 추출 (VLM 실패)")
            
            st.markdown("**내용:**")
            st.text_area(
                "청크 내용",
                chunk.get('text', ''),
                height=200,
                key=f"chunk_{i}",
                label_visibility="collapsed"
            )
    
    # 다운로드
    st.divider()
    st.header("💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON 다운로드
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 JSON 다운로드",
            data=json_str,
            file_name=f"{metadata['filename']}_phase32.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # MD 다운로드
        md_content = convert_to_markdown(result)
        st.download_button(
            label="📝 Markdown 다운로드",
            data=md_content,
            file_name=f"{metadata['filename']}_phase32.md",
            mime="text/markdown",
            use_container_width=True
        )


def convert_to_markdown(result):
    """JSON to Markdown"""
    
    lines = []
    meta = result['metadata']
    
    # 헤더
    lines.append(f"# {meta['filename']}")
    lines.append("")
    lines.append("## 📊 메타데이터")
    lines.append("")
    lines.append(f"- **처리 날짜**: {meta.get('processed_at', 'N/A')}")
    lines.append(f"- **VLM**: {meta.get('vlm_provider', 'N/A')}")
    lines.append(f"- **총 페이지**: {meta['total_pages']}개")
    lines.append(f"- **총 청크**: {meta['total_chunks']}개")
    lines.append(f"- **처리 시간**: {meta['processing_time_sec']}초")
    lines.append(f"- **Phase**: 3.2")
    lines.append("")
    
    # 청크
    lines.append("## 🧩 청크")
    lines.append("")
    
    chunks = result.get('chunks', [])
    
    for i, chunk in enumerate(chunks, start=1):
        lines.append(f"### 청크 #{i}")
        lines.append("")
        lines.append(f"- **페이지**: {chunk.get('page_number', 'N/A')}")
        lines.append(f"- **타입**: {chunk.get('chunk_type', 'unknown')}")
        lines.append(f"- **소스**: {chunk.get('source_type', 'N/A')}")
        
        if chunk.get('ocr_extracted'):
            lines.append("- **경고**: OCR 추출 (VLM 실패)")
        
        lines.append("")
        lines.append("```")
        lines.append(chunk.get('text', ''))
        lines.append("```")
        lines.append("")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    if not PHASE32_AVAILABLE:
        st.error("Phase 3.2 모듈을 로드할 수 없습니다.")
        st.stop()
    
    main()
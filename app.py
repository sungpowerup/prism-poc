"""
PRISM Phase 2.9 - Streamlit Web Application
구조화된 문서 처리 UI

개선 사항:
1. 구조화된 VLM 프롬프트
2. 한글 인코딩 자동 수정
3. 섹션 기반 청킹
4. RAG 최적화

Author: 최동현 (Frontend Lead) + 전체 팀
Date: 2025-10-21
Version: 2.9
"""

import streamlit as st
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Core 모듈
try:
    from core.phase29_pipeline import Phase29Pipeline
except ImportError as e:
    st.error(f"❌ core 모듈 임포트 실패: {e}")
    st.stop()

# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="PRISM Phase 2.9",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS 스타일
# ============================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #17a2b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .phase-badge {
        display: inline-block;
        background: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.9rem;
        font-weight: bold;
        margin-left: 1rem;
    }
    .improvement-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .chunk-card {
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .section-title {
        color: #1f77b4;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 1rem;
    }
    .stat-box {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 세션 상태 초기화
# ============================================================

if 'result' not in st.session_state:
    st.session_state.result = None

# ============================================================
# Helper Functions
# ============================================================

def save_uploaded_file(uploaded_file) -> str:
    """업로드 파일을 임시 디렉토리에 저장"""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path


def display_metadata(result: Dict):
    """메타데이터 표시"""
    st.markdown("## 📊 처리 결과 요약")
    
    metadata = result['metadata']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("총 페이지", f"{metadata.get('total_pages', 'N/A')}개")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("총 청크", f"{metadata['total_chunks']}개")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("처리 시간", f"{metadata['processing_time_sec']:.1f}초")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        encoding_fixes = metadata.get('encoding_fixes', {})
        fixed_count = encoding_fixes.get('fixed', 0) if isinstance(encoding_fixes, dict) else 0
        st.metric("인코딩 수정", f"{fixed_count}건")
        st.markdown('</div>', unsafe_allow_html=True)


def display_chunks(result: Dict):
    """청크 표시 (Phase 2.9 호환)"""
    st.markdown("## 🧩 구조화된 청크")
    
    # Phase 2.9는 'chunks', Phase 2.8은 'stage3_chunks' 또는 'stage2_chunks'
    chunks = result.get('chunks') or result.get('stage3_chunks') or result.get('stage2_chunks', [])
    
    if not chunks:
        st.warning("청크가 없습니다.")
        return
    
    st.info(f"📄 총 {len(chunks)}개 청크")
    
    # 청크 표시
    for i, chunk in enumerate(chunks, start=1):
        # Phase 2.9 청크 구조
        if 'chunk_id' in chunk:
            chunk_id = chunk['chunk_id']
            text = chunk.get('text', '')
            section_title = chunk.get('section_title', '(없음)')
            chunk_type = chunk.get('chunk_type', 'unknown')
            keywords = chunk.get('keywords', [])
            char_count = chunk.get('char_count', 0)
            
            with st.expander(
                f"📦 {chunk_id} - {section_title} ({chunk_type})",
                expanded=(i == 1)
            ):
                # 메타데이터
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**기본 정보**")
                    st.text(f"청크 ID: {chunk_id}")
                    st.text(f"타입: {chunk_type}")
                    st.text(f"글자 수: {char_count}자")
                
                with col2:
                    st.markdown("**구조 정보**")
                    st.text(f"섹션: {section_title}")
                    if keywords:
                        st.text(f"키워드: {', '.join(keywords[:5])}")
                
                # 내용
                st.markdown("---")
                st.markdown("**📝 내용**")
                st.text_area(
                    label="내용",
                    value=text,
                    height=200,
                    key=f"chunk_{i}",
                    label_visibility="collapsed"
                )
        
        # Phase 2.8 청크 구조 (하위 호환)
        else:
            content = chunk.get('content', '')
            page_number = chunk.get('page_number', 0)
            element_type = chunk.get('element_type', 'unknown')
            
            with st.expander(
                f"📦 청크 #{i} - 페이지 {page_number} ({element_type})",
                expanded=(i == 1)
            ):
                st.text_area(
                    label="내용",
                    value=content,
                    height=200,
                    key=f"chunk_{i}",
                    label_visibility="collapsed"
                )


def display_download_buttons(result: Dict):
    """다운로드 버튼"""
    st.markdown("## 💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    # JSON
    with col1:
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_data,
            file_name=f"prism_phase29_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Markdown
    with col2:
        md_data = generate_markdown(result)
        st.download_button(
            label="📥 Markdown 다운로드",
            data=md_data,
            file_name=f"prism_phase29_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )


def generate_markdown(result: Dict) -> str:
    """Markdown 생성 (Phase 2.9 호환)"""
    lines = []
    
    lines.append("# PRISM Phase 2.9 - 구조화된 문서 추출")
    lines.append("")
    lines.append(f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 메타데이터
    meta = result['metadata']
    lines.append("## 📄 문서 정보")
    lines.append("")
    lines.append(f"- **파일명**: {meta['filename']}")
    lines.append(f"- **총 페이지**: {meta.get('total_pages', 'N/A')}개")
    lines.append(f"- **총 청크**: {meta['total_chunks']}개")
    lines.append(f"- **처리 시간**: {meta['processing_time_sec']}초")
    lines.append(f"- **Phase**: {meta.get('phase', '2.9')}")
    lines.append("")
    
    # 청크
    lines.append("## 🧩 청크")
    lines.append("")
    
    # Phase 2.9 또는 2.8 호환
    chunks = result.get('chunks') or result.get('stage3_chunks') or result.get('stage2_chunks', [])
    
    for i, chunk in enumerate(chunks, start=1):
        lines.append(f"### 청크 #{i}")
        lines.append("")
        
        # Phase 2.9
        if 'chunk_id' in chunk:
            lines.append(f"- **ID**: {chunk['chunk_id']}")
            lines.append(f"- **타입**: {chunk.get('chunk_type', 'unknown')}")
            lines.append(f"- **섹션**: {chunk.get('section_title', '(없음)')}")
            
            if chunk.get('keywords'):
                lines.append(f"- **키워드**: {', '.join(chunk['keywords'][:5])}")
            
            lines.append("")
            lines.append("```")
            lines.append(chunk.get('text', ''))
            lines.append("```")
        
        # Phase 2.8
        else:
            lines.append(f"- **페이지**: {chunk.get('page_number', 'N/A')}")
            lines.append(f"- **타입**: {chunk.get('element_type', 'unknown')}")
            lines.append("")
            lines.append("```")
            lines.append(chunk.get('content', ''))
            lines.append("```")
        
        lines.append("")
    
    return '\n'.join(lines)


def process_document(uploaded_file, vlm_provider: str):
    """문서 처리"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 파일 저장
        status_text.text("📁 파일 저장 중...")
        progress_bar.progress(10)
        
        pdf_path = save_uploaded_file(uploaded_file)
        
        # 2. 파이프라인 초기화
        status_text.text("⚙️ 파이프라인 초기화 중...")
        progress_bar.progress(20)
        
        pipeline = Phase29Pipeline(vlm_provider=vlm_provider)
        
        # 3. 문서 처리
        status_text.text("🔄 문서 처리 중... (1~2분 소요)")
        progress_bar.progress(30)
        
        result = pipeline.process_pdf(pdf_path)
        
        # 4. 완료
        progress_bar.progress(100)
        status_text.text("✅ 처리 완료!")
        
        # 결과 저장
        st.session_state.result = result
        
        st.success(f"✅ 처리 완료! ({result['metadata']['total_chunks']}개 청크 생성)")
        st.balloons()
        
        # 화면 새로고침
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {str(e)}")
        
        # 상세 에러 정보
        with st.expander("🔍 상세 에러 정보"):
            import traceback
            st.code(traceback.format_exc())


# ============================================================
# 메인 애플리케이션
# ============================================================

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown(
        '<div class="main-header">🔷 PRISM Phase 2.9'
        '<span class="phase-badge">Structured</span></div>',
        unsafe_allow_html=True
    )
    
    # Phase 2.9 개선사항
    st.markdown("""
    <div class="improvement-box">
        <h3 style="margin-top:0;">✨ Phase 2.9 주요 개선사항</h3>
        <ul style="margin-bottom:0;">
            <li><strong>구조화된 VLM 프롬프트</strong>: 섹션 헤더 자동 추출, 차트 타입 명시</li>
            <li><strong>스마트 인코딩 수정</strong>: 한글 깨짐 자동 복구</li>
            <li><strong>섹션 기반 청킹</strong>: 문서 구조 보존, 의미 단위 분할</li>
            <li><strong>RAG 최적화</strong>: 키워드 추출, 메타데이터 풍부화</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 🤖 VLM 프로바이더")
        
        vlm_provider = st.selectbox(
            "프로바이더 선택",
            options=['azure_openai', 'claude', 'ollama'],
            index=0,
            help="Azure OpenAI 권장 (가장 안정적)"
        )
        
        st.markdown("---")
        
        st.markdown("### 📖 사용 방법")
        st.markdown("""
        1. PDF 파일 업로드
        2. VLM 프로바이더 선택
        3. '처리 시작' 클릭
        4. 결과 확인 및 다운로드
        """)
        
        st.markdown("---")
        
        st.markdown("### 🆕 Phase 2.9 특징")
        st.markdown("""
        - ✅ 섹션 헤더 자동 추출
        - ✅ 차트 타입 명시
        - ✅ 리스트 형식 데이터
        - ✅ 인사이트 제공
        - ✅ RAG 최적화
        """)
        
        st.markdown("---")
        
        # 시스템 정보
        st.markdown("### 💻 시스템 정보")
        st.text(f"Phase: 2.9")
        st.text(f"VLM: {vlm_provider}")
    
    # 메인 영역
    uploaded_file = st.file_uploader(
        "📄 PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 200MB, 20페이지까지 처리 가능"
    )
    
    if uploaded_file:
        st.info(f"📎 파일: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            process_document(uploaded_file, vlm_provider)
    
    # 결과 표시
    if st.session_state.result:
        st.markdown("---")
        
        result = st.session_state.result
        
        # 메타데이터
        display_metadata(result)
        
        st.markdown("---")
        
        # 청크 표시
        display_chunks(result)
        
        st.markdown("---")
        
        # 다운로드
        display_download_buttons(result)
        
        # 새 문서 처리
        if st.button("🔄 새 문서 처리", use_container_width=True):
            st.session_state.result = None
            st.rerun()


if __name__ == '__main__':
    main()
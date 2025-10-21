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
from typing import Dict, Any
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
        st.metric("총 페이지", f"{metadata['total_pages']}개")
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
        st.metric("인코딩 수정", f"{metadata['encoding_fixes']['fixed']}건")
        st.markdown('</div>', unsafe_allow_html=True)


def display_chunks(result: Dict):
    """청크 표시"""
    st.markdown("## 🧩 구조화된 청크")
    
    chunks = result['stage3_chunks']
    
    if not chunks:
        st.warning("청크가 없습니다.")
        return
    
    # 페이지별 필터
    page_numbers = sorted(set(c['metadata']['page_number'] for c in chunks))
    selected_page = st.selectbox(
        "페이지 선택",
        options=['전체'] + page_numbers,
        index=0
    )
    
    # 필터링
    if selected_page != '전체':
        filtered_chunks = [c for c in chunks if c['metadata']['page_number'] == selected_page]
    else:
        filtered_chunks = chunks
    
    st.info(f"📄 {len(filtered_chunks)}개 청크 표시")
    
    # 청크 표시
    for i, chunk in enumerate(filtered_chunks, start=1):
        metadata = chunk['metadata']
        
        with st.expander(
            f"📦 청크 #{i} - 페이지 {metadata['page_number']} ({metadata['element_type']})",
            expanded=(i == 1)
        ):
            # 메타데이터
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**기본 정보**")
                st.text(f"페이지: {metadata['page_number']}")
                st.text(f"타입: {metadata['element_type']}")
                st.text(f"글자 수: {metadata['char_count']}자")
                st.text(f"청크 순서: {metadata['chunk_index'] + 1}/{metadata['total_chunks']}")
            
            with col2:
                st.markdown("**구조 정보**")
                
                section = metadata.get('section_title', '')
                if section:
                    st.text(f"섹션: {section}")
                else:
                    st.text("섹션: (없음)")
                
                chart_type = metadata.get('chart_type', '')
                if chart_type:
                    st.text(f"차트 타입: {chart_type}")
                
                keywords = metadata.get('keywords', [])
                if keywords:
                    st.text(f"키워드: {', '.join(keywords[:5])}")
            
            # 내용
            st.markdown("---")
            st.markdown("**📝 내용**")
            st.text_area(
                label="내용",
                value=chunk['content'],
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
            mime="application/json"
        )
    
    # Markdown
    with col2:
        md_data = generate_markdown(result)
        st.download_button(
            label="📥 Markdown 다운로드",
            data=md_data,
            file_name=f"prism_phase29_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )


def generate_markdown(result: Dict) -> str:
    """Markdown 생성"""
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
    lines.append(f"- **총 페이지**: {meta['total_pages']}개")
    lines.append(f"- **총 청크**: {meta['total_chunks']}개")
    lines.append(f"- **처리 시간**: {meta['processing_time_sec']}초")
    lines.append("")
    
    # 청크
    lines.append("## 🧩 청크")
    lines.append("")
    
    for i, chunk in enumerate(result['stage3_chunks'], start=1):
        meta = chunk['metadata']
        
        lines.append(f"### 청크 #{i}")
        lines.append("")
        lines.append(f"- 페이지: {meta['page_number']}")
        lines.append(f"- 타입: {meta['element_type']}")
        
        if meta.get('section_title'):
            lines.append(f"- 섹션: {meta['section_title']}")
        
        lines.append("")
        lines.append("```")
        lines.append(chunk['content'])
        lines.append("```")
        lines.append("")
    
    return '\n'.join(lines)


def process_document(uploaded_file, vlm_provider: str):
    """문서 처리"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 파일 저장
        status_text.text("1/4 파일 저장 중...")
        progress_bar.progress(25)
        
        pdf_path = save_uploaded_file(uploaded_file)
        
        # 2. Pipeline 초기화
        status_text.text("2/4 Pipeline 초기화 중...")
        progress_bar.progress(50)
        
        pipeline = Phase29Pipeline(vlm_provider=vlm_provider)
        
        # 3. 문서 처리
        status_text.text("3/4 구조화된 분석 진행 중... (시간이 걸릴 수 있습니다)")
        progress_bar.progress(75)
        
        result = pipeline.process_pdf(pdf_path)
        
        # 4. 완료
        status_text.text("4/4 처리 완료!")
        progress_bar.progress(100)
        
        # 세션 상태 저장
        st.session_state.result = result
        
        # 성공 메시지
        st.success("✅ 구조화된 문서 처리가 완료되었습니다!")
        
        # 임시 파일 정리
        try:
            os.remove(pdf_path)
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {str(e)}")
        
        with st.expander("🔍 상세 에러 정보"):
            import traceback
            st.code(traceback.format_exc())
    
    finally:
        progress_bar.empty()
        status_text.empty()


# ============================================================
# 메인 UI
# ============================================================

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown(
        '<div class="main-header">🔷 PRISM Phase 2.9'
        '<span class="phase-badge">Structured</span></div>',
        unsafe_allow_html=True
    )
    
    st.markdown('<p style="text-align: center; color: #666;">구조화된 문서 처리 시스템</p>', unsafe_allow_html=True)
    
    # 개선사항 박스
    with st.container():
        st.markdown("""
        <div class="improvement-box">
            <h3 style="margin-top: 0;">🎉 Phase 2.9 주요 개선사항</h3>
            <ul style="margin-bottom: 0;">
                <li><strong>구조화된 VLM 프롬프트</strong>: 섹션/차트별 독립 분석</li>
                <li><strong>한글 인코딩 자동 수정</strong>: 완벽한 한글 복원</li>
                <li><strong>섹션 기반 청킹</strong>: 의미 단위 보존</li>
                <li><strong>RAG 최적화</strong>: 검색 효율성 극대화</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 사이드바 설정
    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        
        # VLM 선택
        vlm_provider = st.selectbox(
            "VLM 프로바이더",
            options=["azure_openai", "claude", "ollama"],
            index=0,
            help="문서 분석에 사용할 VLM 모델"
        )
        
        st.markdown("---")
        
        # 정보
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
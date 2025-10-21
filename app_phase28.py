"""
PRISM Phase 2.8 - Streamlit Web Application
VLM 통합 버전

Author: 최동현 (Frontend Lead)
Date: 2025-10-21
Version: 2.8
"""

import streamlit as st
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Core 모듈
try:
    from core.phase28_pipeline import Phase28Pipeline
except ImportError as e:
    st.error(f"❌ core 모듈 임포트 실패: {e}")
    st.stop()


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="PRISM Phase 2.8",
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
        background: #1f77b4;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.9rem;
        font-weight: bold;
        margin-left: 1rem;
    }
    .feature-card {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 세션 상태 초기화
# ============================================================

if 'result' not in st.session_state:
    st.session_state.result = None


# ============================================================
# 메인 UI
# ============================================================

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown(
        '<div class="main-header">🔷 PRISM Phase 2.8'
        '<span class="phase-badge">VLM Integrated</span></div>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 1.1rem;">'
        'Element 분류 + VLM 자연어 변환 + 지능형 청킹'
        '</p>',
        unsafe_allow_html=True
    )
    
    # 사이드바 설정
    with st.sidebar:
        st.markdown("## ⚙️ 설정")
        
        # VLM 프로바이더 선택
        vlm_provider = st.selectbox(
            "VLM 프로바이더",
            options=["claude", "azure_openai", "ollama"],
            index=0,
            help="문서 처리에 사용할 VLM 모델"
        )
        
        # 최대 페이지 설정
        max_pages = st.number_input(
            "최대 처리 페이지",
            min_value=1,
            max_value=50,
            value=10,
            help="처리할 최대 페이지 수 (비용 절감)"
        )
        
        st.markdown("---")
        
        # Phase 2.8 새 기능
        st.markdown("### 🎉 Phase 2.8 새 기능")
        
        st.markdown("""
        <div class="feature-card">
        ✅ <b>Element 자동 분류</b><br>
        CV + VLM 하이브리드 방식
        </div>
        
        <div class="feature-card">
        ✅ <b>VLM 자연어 변환</b><br>
        경쟁사 수준 품질 달성
        </div>
        
        <div class="feature-card">
        ✅ <b>지능형 청킹</b><br>
        의미 기반 문맥 보존
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 정보
        st.markdown("### 📖 사용 방법")
        st.markdown("""
        1. PDF 파일 업로드
        2. VLM 프로바이더 선택
        3. 최대 페이지 설정
        4. '처리 시작' 클릭
        5. 결과 확인 및 다운로드
        """)
    
    # 메인 영역
    st.markdown("## 📄 문서 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 200MB, 50페이지 이하 권장"
    )
    
    if uploaded_file is not None:
        
        # 파일 정보 표시
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("파일명", uploaded_file.name)
        col2.metric("크기", f"{file_size_mb:.2f} MB")
        col3.metric("VLM", vlm_provider.upper())
        
        # 처리 버튼
        if st.button("🚀 처리 시작", type="primary", use_container_width=True):
            process_document(uploaded_file, vlm_provider, max_pages)
    
    # 결과 표시
    if st.session_state.result is not None:
        display_results(st.session_state.result)


# ============================================================
# 문서 처리
# ============================================================

def process_document(uploaded_file, vlm_provider: str, max_pages: int):
    """문서 처리 메인 함수"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 파일 저장
        status_text.info("📥 1/4 파일 저장 중...")
        progress_bar.progress(25)
        
        temp_dir = Path("input")
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / uploaded_file.name
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # 2. Pipeline 초기화
        status_text.info("🔧 2/4 Pipeline 초기화 중...")
        progress_bar.progress(50)
        
        pipeline = Phase28Pipeline(vlm_provider=vlm_provider)
        
        # 3. 문서 처리
        status_text.info("🤖 3/4 VLM 처리 중... (시간이 걸릴 수 있습니다)")
        progress_bar.progress(75)
        
        result = pipeline.process_pdf(
            pdf_path=str(temp_path),
            max_pages=max_pages
        )
        
        # 4. 완료
        status_text.success("✅ 4/4 처리 완료!")
        progress_bar.progress(100)
        
        # 세션 상태에 저장
        st.session_state.result = result
        
        # 성공 메시지
        st.markdown("""
        <div class="success-box">
        <h3 style="margin-top: 0;">✅ 처리 완료!</h3>
        <p>VLM 기반 자연어 변환이 완료되었습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 임시 파일 정리
        try:
            os.remove(temp_path)
        except:
            pass
        
        st.balloons()
        
    except Exception as e:
        status_text.error(f"❌ 처리 중 오류 발생: {str(e)}")
        
        with st.expander("🔍 상세 에러 정보"):
            import traceback
            st.code(traceback.format_exc())
    
    finally:
        progress_bar.empty()
        status_text.empty()


# ============================================================
# 결과 표시
# ============================================================

def display_results(result: Dict):
    """결과 표시"""
    
    st.markdown("---")
    st.markdown("## 📊 처리 결과")
    
    # 메타데이터
    meta = result['metadata']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 페이지", meta['total_pages'])
    col2.metric("총 청크", meta['total_chunks'])
    col3.metric("처리 시간", f"{meta['processing_time_sec']:.1f}초")
    col4.metric("Phase", meta['phase'])
    
    # 청크 타입별 통계
    st.markdown("### 📈 Element 타입별 통계")
    
    chunk_types = meta['chunk_types']
    
    for element_type, count in chunk_types.items():
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"**{element_type.upper()}**")
        col2.markdown(f"`{count}개`")
    
    # Stage 1 통계
    if 'stage1_elements' in result:
        st.markdown("### 🔍 Stage 1: Element 분류 상세")
        
        for stat in result['stage1_elements']:
            with st.expander(
                f"페이지 {stat['page_number']} - "
                f"{stat['element_type'].upper()} "
                f"(신뢰도: {stat['confidence']:.1%})"
            ):
                col1, col2 = st.columns(2)
                
                col1.metric("청크 수", stat['chunks_count'])
                col1.metric("신뢰도", f"{stat['confidence']:.1%}")
                
                col2.metric("토큰 사용", stat['tokens_used'])
                col2.metric("처리 시간", f"{stat['processing_time_sec']:.2f}초")
    
    # Stage 2 청크
    st.markdown("### 🧩 Stage 2: 지능형 청크")
    
    chunks = result.get('stage2_chunks', [])
    
    for i, chunk in enumerate(chunks, 1):
        with st.expander(
            f"청크 #{i} - "
            f"페이지 {chunk['page_number']} "
            f"({chunk['element_type'].upper()})",
            expanded=(i == 1)
        ):
            st.markdown(f"**모델**: {chunk['model_used']}")
            st.markdown(f"**타입**: {chunk['element_type']}")
            st.markdown("---")
            st.markdown("**변환된 내용:**")
            st.text_area(
                label="내용",
                value=chunk['content'],
                height=300,
                key=f"chunk_{i}",
                disabled=True
            )
    
    # 다운로드 버튼
    display_download_buttons(result)


# ============================================================
# 다운로드 버튼
# ============================================================

def display_download_buttons(result: Dict):
    """다운로드 버튼 표시"""
    
    st.markdown("---")
    st.markdown("## 💾 다운로드")
    
    col1, col2 = st.columns(2)
    
    # JSON 다운로드
    with col1:
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_data,
            file_name=f"prism_phase28_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Markdown 다운로드
    with col2:
        md_data = convert_to_markdown(result)
        st.download_button(
            label="📥 Markdown 다운로드",
            data=md_data,
            file_name=f"prism_phase28_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )


def convert_to_markdown(result: Dict) -> str:
    """결과를 Markdown으로 변환"""
    
    md = []
    
    # 헤더
    md.append("# PRISM Phase 2.8 - 문서 추출 결과\n\n")
    md.append(f"**생성일시**: {result['metadata']['processed_at'][:19].replace('T', ' ')}\n\n")
    md.append("---\n\n")
    
    # 메타데이터
    meta = result['metadata']
    md.append("## 📄 문서 정보\n\n")
    md.append(f"- **파일명**: {meta['filename']}\n")
    md.append(f"- **총 페이지**: {meta['total_pages']}\n")
    md.append(f"- **처리 시간**: {meta['processing_time_sec']:.2f}초\n")
    md.append(f"- **총 청크**: {meta['total_chunks']}\n")
    md.append(f"- **Phase**: {meta['phase']}\n\n")
    md.append("---\n\n")
    
    # 청크
    md.append("## 🧩 지능형 청크\n\n")
    
    for i, chunk in enumerate(result.get('stage2_chunks', []), 1):
        md.append(f"### 청크 #{i}\n\n")
        md.append(f"**페이지**: {chunk['page_number']}\n")
        md.append(f"**타입**: {chunk['element_type']}\n")
        md.append(f"**모델**: {chunk['model_used']}\n\n")
        md.append("**내용**:\n\n")
        md.append("```\n")
        md.append(chunk['content'])
        md.append("\n```\n\n")
        md.append("---\n\n")
    
    return ''.join(md)


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
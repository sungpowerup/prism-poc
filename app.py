"""
PRISM Phase 2.7 - Streamlit Application
지능형 청킹 시스템 UI

Author: 최동현 (Frontend Lead)
Date: 2025-10-20
"""

import streamlit as st
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import tempfile

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.phase27_pipeline import Phase27Pipeline

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 2.7",
    page_icon="🔷",
    layout="wide"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chunk-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .chunk-header {
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .chunk-meta {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .stat-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1976d2;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Helper Functions
# ============================================================

def convert_to_markdown(result: dict) -> str:
    """결과를 마크다운으로 변환"""
    md_lines = []
    
    # 헤더
    md_lines.append("# PRISM Phase 2.7 - 처리 결과")
    md_lines.append("")
    md_lines.append(f"**처리 일시:** {result['metadata']['processed_at']}")
    md_lines.append(f"**총 페이지:** {result['metadata']['total_pages']}")
    md_lines.append(f"**총 청크:** {result['metadata']['total_chunks']}")
    md_lines.append(f"**처리 시간:** {result['metadata']['processing_time_seconds']}초")
    md_lines.append("")
    md_lines.append("## 청크 타입별 통계")
    md_lines.append("")
    
    for chunk_type, count in result['metadata']['chunk_types'].items():
        md_lines.append(f"- **{chunk_type}**: {count}개")
    
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 청크별 내용
    for chunk in result['chunks']:
        chunk_id = chunk['chunk_id']
        page_num = chunk['page_num']
        chunk_type = chunk['type']
        content = chunk['content']
        section_path = chunk['metadata'].get('section_path', 'N/A')
        token_count = chunk['metadata'].get('token_count', 0)
        
        # 타입별 아이콘
        type_icons = {
            'text': '📝',
            'table': '📊',
            'chart': '📈',
            'image': '🖼️'
        }
        icon = type_icons.get(chunk_type, '📄')
        
        md_lines.append(f"## {icon} {chunk_id}")
        md_lines.append("")
        md_lines.append(f"**페이지:** {page_num} | **타입:** {chunk_type} | **토큰:** {token_count}")
        md_lines.append(f"**경로:** {section_path}")
        md_lines.append("")
        md_lines.append("### 내용")
        md_lines.append("")
        md_lines.append(content)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    return '\n'.join(md_lines)


def display_chunk(chunk: dict):
    """청크 표시"""
    chunk_id = chunk['chunk_id']
    page_num = chunk['page_num']
    chunk_type = chunk['type']
    content = chunk['content']
    section_path = chunk['metadata'].get('section_path', 'N/A')
    token_count = chunk['metadata'].get('token_count', 0)
    
    # 타입별 아이콘
    type_icons = {
        'text': '📝',
        'table': '📊',
        'chart': '📈',
        'image': '🖼️'
    }
    icon = type_icons.get(chunk_type, '📄')
    
    st.markdown(f'<div class="chunk-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="chunk-header">{icon} {chunk_id}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="chunk-meta">페이지: {page_num} | 타입: {chunk_type} | 토큰: {token_count}<br>경로: {section_path}</div>',
        unsafe_allow_html=True
    )
    
    # 내용 표시
    with st.expander("내용 보기", expanded=False):
        if chunk_type == 'table':
            # 표는 마크다운으로 렌더링
            st.markdown(content)
        else:
            st.text(content)
    
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Main App
# ============================================================

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown('<div class="main-header">🔷 PRISM Phase 2.7</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">지능형 문서 청킹 시스템 - RAG 최적화</div>', unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.subheader("청킹 파라미터")
        min_chunk_size = st.slider("최소 청크 크기 (토큰)", 50, 200, 100)
        max_chunk_size = st.slider("최대 청크 크기 (토큰)", 300, 1000, 500)
        overlap_size = st.slider("오버랩 크기 (토큰)", 0, 100, 50)
        
        st.divider()
        
        st.subheader("처리 옵션")
        max_pages = st.number_input("최대 페이지 수", min_value=1, max_value=50, value=10)
        
        st.divider()
        
        st.markdown("""
        ### 📖 시스템 정보
        
        **Phase 2.7 특징:**
        - 🔍 2-Stage Pipeline
        - 🔄 하이브리드 추출 (OCR + VLM)
        - ✂️ 의미 기반 청킹
        - 🎯 RAG 최적화
        """)
    
    # 파일 업로드
    st.subheader("📄 PDF 파일 업로드")
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="지능형 청킹 시스템으로 처리됩니다"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하여 시작하세요")
        
        st.markdown("""
        ### 🎯 Phase 2.7의 주요 개선사항
        
        **1. 2-Stage Pipeline**
        - Stage 1: Layout Detection (영역 분류)
        - Stage 2: Hybrid Extraction (OCR + VLM)
        - Stage 3: Intelligent Chunking (의미 단위)
        
        **2. 범용 문서 지원**
        - 보고서, 논문, 매뉴얼, 계약서 등
        - 문서 타입에 무관하게 작동
        
        **3. RAG 검색 최적화**
        - 의미 단위 청킹 (100-500 토큰)
        - 섹션 경로 메타데이터
        - 컨텍스트 보존
        
        **4. 정확도 향상**
        - OCR 우선 (텍스트 정확도 95%+)
        - VLM 보조 (표/차트 구조화)
        - 원본 충실도 극대화
        """)
        return
    
    # 처리 버튼
    if st.button("🚀 처리 시작", type="primary", use_container_width=True):
        
        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # 파이프라인 초기화
            with st.spinner("⚙️ 파이프라인 초기화 중..."):
                pipeline = Phase27Pipeline(
                    min_chunk_size=min_chunk_size,
                    max_chunk_size=max_chunk_size,
                    overlap_size=overlap_size
                )
            
            # 처리 실행
            with st.spinner("🔄 문서 처리 중... (시간이 소요될 수 있습니다)"):
                result = pipeline.process_pdf(tmp_path, max_pages=max_pages)
            
            # 세션 상태에 저장
            st.session_state['result'] = result
            st.session_state['processed_filename'] = uploaded_file.name
            
            st.success("✅ 처리 완료!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 처리 중 오류 발생: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    # 결과 표시
    if 'result' in st.session_state:
        result = st.session_state['result']
        filename = st.session_state.get('processed_filename', 'document.pdf')
        
        st.divider()
        
        # 통계 표시
        st.subheader("📊 처리 결과 통계")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{result["metadata"]["total_pages"]}</div>', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">총 페이지</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{result["metadata"]["total_chunks"]}</div>', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">총 청크</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{result["metadata"]["processing_time_seconds"]}s</div>', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">처리 시간</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            avg_time = result["metadata"]["processing_time_seconds"] / result["metadata"]["total_pages"]
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{avg_time:.1f}s</div>', unsafe_allow_html=True)
            st.markdown('<div class="stat-label">페이지당 평균</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 청크 타입별 통계
        st.subheader("📈 청크 타입별 분포")
        
        chunk_types = result['metadata']['chunk_types']
        
        cols = st.columns(len(chunk_types))
        for i, (chunk_type, count) in enumerate(chunk_types.items()):
            with cols[i]:
                type_icons = {
                    'text': '📝',
                    'table': '📊',
                    'chart': '📈',
                    'image': '🖼️'
                }
                icon = type_icons.get(chunk_type, '📄')
                st.metric(f"{icon} {chunk_type.upper()}", count)
        
        st.divider()
        
        # 다운로드 버튼
        st.subheader("💾 결과 다운로드")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON 다운로드
            json_str = json.dumps(result, ensure_ascii=False, indent=2)
            json_filename = f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            st.download_button(
                label="📥 JSON 다운로드",
                data=json_str,
                file_name=json_filename,
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # Markdown 다운로드
            md_str = convert_to_markdown(result)
            md_filename = f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            st.download_button(
                label="📥 Markdown 다운로드",
                data=md_str,
                file_name=md_filename,
                mime="text/markdown",
                use_container_width=True
            )
        
        st.divider()
        
        # 청크 표시
        st.subheader("📋 청크 목록")
        
        # 필터 옵션
        filter_col1, filter_col2 = st.columns([1, 3])
        
        with filter_col1:
            filter_type = st.selectbox(
                "타입 필터",
                ['전체'] + list(chunk_types.keys())
            )
        
        with filter_col2:
            search_query = st.text_input(
                "검색어",
                placeholder="청크 내용 검색..."
            )
        
        # 청크 필터링
        filtered_chunks = result['chunks']
        
        if filter_type != '전체':
            filtered_chunks = [c for c in filtered_chunks if c['type'] == filter_type]
        
        if search_query:
            filtered_chunks = [
                c for c in filtered_chunks 
                if search_query.lower() in c['content'].lower()
            ]
        
        st.write(f"**표시 중:** {len(filtered_chunks)} / {len(result['chunks'])} 청크")
        
        # 청크 표시
        for chunk in filtered_chunks:
            display_chunk(chunk)


if __name__ == "__main__":
    main()
"""
PRISM Phase 2.7 - Final UI with Downloads & Better UX

개선사항:
1. JSON/MD 다운로드 기능
2. Bbox 하이라이팅 수정 (zoom 적용)
3. 탭 방식 UI (청크 목록 / 원본 뷰어)

Author: 최동현 (Frontend Lead)
Date: 2025-10-17
"""

import streamlit as st
import os
import sys
from pathlib import Path
import json
from datetime import datetime
import traceback
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.phase26_pipeline import Phase26Pipeline

# 페이지 설정
st.set_page_config(
    page_title="PRISM Phase 2.7",
    page_icon="🔍",
    layout="wide"
)

# 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chunk-item {
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #ddd;
        border-radius: 5px;
        cursor: pointer;
    }
    .chunk-item:hover {
        background-color: #f8f9fa;
    }
    .chunk-selected {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    .bbox-info {
        font-size: 0.85rem;
        color: #666;
        font-family: monospace;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# PDF 뷰어 유틸리티
# ============================================================

class PDFViewer:
    """PDF 렌더링 및 bbox 하이라이트"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.zoom = 2.0  # 기본 zoom 레벨
    
    def get_page_image(self, page_num: int) -> Image.Image:
        """페이지를 PIL Image로 렌더링"""
        page = self.doc[page_num - 1]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    
    def highlight_bbox(
        self,
        image: Image.Image,
        bbox: dict,
        color: str = 'yellow'
    ) -> Image.Image:
        """Bbox 영역을 하이라이트 (zoom 적용)"""
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy, 'RGBA')
        
        # Bbox 좌표를 zoom에 맞게 스케일링
        x = int(bbox.get('x', 0) * self.zoom)
        y = int(bbox.get('y', 0) * self.zoom)
        w = int(bbox.get('width', 0) * self.zoom)
        h = int(bbox.get('height', 0) * self.zoom)
        
        # 색상 설정
        if color == 'yellow':
            fill_color = (255, 255, 0, 60)
            outline_color = (255, 200, 0, 255)
        elif color == 'red':
            fill_color = (255, 0, 0, 60)
            outline_color = (200, 0, 0, 255)
        else:
            fill_color = (0, 255, 0, 60)
            outline_color = (0, 200, 0, 255)
        
        # 영역 하이라이트
        draw.rectangle(
            [x, y, x + w, y + h],
            fill=fill_color,
            outline=outline_color,
            width=4
        )
        
        return img_copy
    
    def close(self):
        """PDF 닫기"""
        self.doc.close()


# ============================================================
# 유틸리티 함수
# ============================================================

def convert_to_markdown(result: dict) -> str:
    """결과를 Markdown으로 변환"""
    lines = []
    
    # 헤더
    lines.append("# PRISM Phase 2.7 - 문서 추출 결과")
    lines.append("")
    lines.append(f"**처리 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 통계
    stats = result.get('statistics', {})
    lines.append("## 통계")
    lines.append("")
    lines.append(f"- **총 페이지:** {stats.get('total_pages', 0)}")
    lines.append(f"- **총 청크:** {stats.get('total_chunks', 0)}")
    lines.append(f"- **텍스트 청크:** {stats.get('text_chunks', 0)}")
    lines.append(f"- **표 청크:** {stats.get('table_chunks', 0)}")
    lines.append(f"- **차트 청크:** {stats.get('chart_chunks', 0)}")
    lines.append(f"- **이미지 청크:** {stats.get('figure_chunks', 0)}")
    lines.append(f"- **처리 시간:** {stats.get('processing_time', 0):.1f}초")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 청크 목록
    chunks = result.get('chunks', [])
    for chunk in chunks:
        chunk_id = chunk.get('chunk_id', '')
        chunk_type = chunk.get('type', '')
        page_num = chunk.get('page_num', 0)
        content = chunk.get('content', '')
        metadata = chunk.get('metadata', {})
        
        if chunk_type == 'title':
            lines.append(f"## {content}")
            lines.append("")
        elif chunk_type == 'text':
            lines.append(f"### {chunk_id} (Page {page_num})")
            lines.append("")
            lines.append(content)
            lines.append("")
        elif chunk_type == 'chart':
            lines.append(f"### {chunk_id} (Page {page_num})")
            lines.append("")
            lines.append(f"**제목:** {metadata.get('title', '')}")
            lines.append(f"**타입:** {metadata.get('chart_type', '')}")
            lines.append("")
            lines.append("**데이터:**")
            lines.append("")
            data_points = metadata.get('data_points', [])
            for point in data_points:
                if 'category' in point:
                    lines.append(f"**{point['category']}:**")
                    for val in point.get('values', []):
                        lines.append(f"  - {val.get('label', '')}: {val.get('value', '')}{val.get('unit', '')}")
                else:
                    lines.append(f"- {point.get('label', '')}: {point.get('value', '')}{point.get('unit', '')}")
            lines.append("")
        elif chunk_type == 'table':
            lines.append(f"### {chunk_id} (Page {page_num})")
            lines.append("")
            lines.append(f"**제목:** {metadata.get('caption', '')}")
            lines.append("")
            lines.append(content)
            lines.append("")
        elif chunk_type == 'figure':
            lines.append(f"### {chunk_id} (Page {page_num})")
            lines.append("")
            lines.append(content)
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================
# 세션 상태 초기화
# ============================================================

if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None

if 'result' not in st.session_state:
    st.session_state.result = None

if 'selected_chunk_idx' not in st.session_state:
    st.session_state.selected_chunk_idx = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1


# ============================================================
# 문서 처리 함수
# ============================================================

def process_document(uploaded_file, llm_provider, max_pages):
    """문서 처리"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        input_dir = Path("input")
        input_dir.mkdir(exist_ok=True)
        
        input_path = input_dir / uploaded_file.name
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        st.session_state.pdf_path = str(input_path)
        
        status_placeholder.info(f"파일 저장 완료: {input_path}")
        
        status_placeholder.info(f"Pipeline 초기화 중...")
        
        pipeline = Phase26Pipeline(llm_provider=llm_provider)
        
        status_placeholder.info(f"{llm_provider.upper()}로 처리 중...")
        progress_placeholder.progress(0, text="처리 시작...")
        
        start_time = datetime.now()
        result = pipeline.process(str(input_path), max_pages=max_pages)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        st.session_state.result = result
        
        progress_placeholder.progress(100, text="처리 완료!")
        status_placeholder.success(f"처리 완료 (소요 시간: {duration:.1f}초)")
        
        # 결과 저장
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_path = output_dir / f"result_phase27_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # MD 저장
        md_path = output_dir / f"result_phase27_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(convert_to_markdown(result))
        
        st.success(f"결과 저장: {json_path.name}, {md_path.name}")
        
    except Exception as e:
        st.error(f"처리 실패: {str(e)}")
        st.code(traceback.format_exc())


# ============================================================
# Main UI
# ============================================================

st.markdown('<div class="main-header">PRISM Phase 2.7</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">PDF Viewer + Bbox Highlight | RAG Optimized</div>', unsafe_allow_html=True)

st.markdown("---")

# Sidebar
st.sidebar.header("설정")

llm_provider = st.sidebar.selectbox(
    "LLM 모델",
    ["claude"],
    help="문서 분석에 사용할 LLM"
)

max_pages = st.sidebar.number_input(
    "최대 페이지 수",
    min_value=1,
    max_value=100,
    value=3
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Phase 2.7")
st.sidebar.markdown("""
- Bbox 위치 정보
- 중복 제거
- 텍스트 병합
- RAG 최적화
- 원본 PDF 뷰어
""")

# 파일 업로드
st.header("문서 업로드")

uploaded_file = st.file_uploader(
    "PDF 파일 선택",
    type=['pdf']
)

if uploaded_file:
    st.success(f"파일: {uploaded_file.name}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("처리 시작", type="primary", use_container_width=True):
            process_document(uploaded_file, llm_provider, max_pages)
    
    with col2:
        if st.session_state.result:
            if st.button("초기화", use_container_width=True):
                st.session_state.result = None
                st.session_state.selected_chunk_idx = None
                st.session_state.pdf_path = None
                st.rerun()

# ============================================================
# 결과 표시 (탭 방식)
# ============================================================

if st.session_state.result and st.session_state.pdf_path:
    st.markdown("---")
    st.header("분석 결과")
    
    # 통계
    stats = st.session_state.result.get('statistics', {})
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("페이지", stats.get('total_pages', 0))
    with col2:
        st.metric("총 청크", stats.get('total_chunks', 0))
    with col3:
        st.metric("텍스트", stats.get('text_chunks', 0))
    with col4:
        st.metric("표", stats.get('table_chunks', 0))
    with col5:
        st.metric("차트", stats.get('chart_chunks', 0))
    with col6:
        st.metric("이미지", stats.get('figure_chunks', 0))
    
    # 다운로드 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        # JSON 다운로드
        json_str = json.dumps(st.session_state.result, ensure_ascii=False, indent=2)
        st.download_button(
            label="JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # MD 다운로드
        md_str = convert_to_markdown(st.session_state.result)
        st.download_button(
            label="MD 다운로드",
            data=md_str,
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["원본 PDF 뷰어", "청크 목록"])
    
    # ============================================================
    # Tab 1: 원본 PDF 뷰어 (주 화면)
    # ============================================================
    
    with tab1:
        try:
            viewer = PDFViewer(st.session_state.pdf_path)
            total_pages = viewer.doc.page_count
            
            # 페이지 선택
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                current_page = st.number_input(
                    "페이지",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.current_page,
                    key="page_selector"
                )
                st.session_state.current_page = current_page
            
            with col2:
                if st.button("이전", disabled=(current_page <= 1), use_container_width=True):
                    st.session_state.current_page = max(1, current_page - 1)
                    st.rerun()
            
            with col3:
                if st.button("다음", disabled=(current_page >= total_pages), use_container_width=True):
                    st.session_state.current_page = min(total_pages, current_page + 1)
                    st.rerun()
            
            with col4:
                if st.button("하이라이트 해제", use_container_width=True):
                    st.session_state.selected_chunk_idx = None
                    st.rerun()
            
            st.markdown("---")
            
            # 페이지 렌더링
            page_image = viewer.get_page_image(current_page)
            
            # 선택된 청크의 bbox 하이라이트
            if st.session_state.selected_chunk_idx is not None:
                chunks = st.session_state.result.get('chunks', [])
                if 0 <= st.session_state.selected_chunk_idx < len(chunks):
                    selected_chunk = chunks[st.session_state.selected_chunk_idx]
                    
                    if selected_chunk.get('page_num') == current_page:
                        bbox = selected_chunk.get('metadata', {}).get('bbox')
                        if bbox:
                            page_image = viewer.highlight_bbox(page_image, bbox, color='yellow')
                            st.info(f"선택된 청크: {selected_chunk.get('chunk_id', 'N/A')} | 페이지 {current_page}")
            
            # 이미지 표시 (크게)
            st.image(page_image, use_column_width=True)
            
            viewer.close()
            
        except Exception as e:
            st.error(f"PDF 렌더링 오류: {e}")
    
    # ============================================================
    # Tab 2: 청크 목록
    # ============================================================
    
    with tab2:
        chunks = st.session_state.result.get('chunks', [])
        
        if not chunks:
            st.warning("추출된 청크가 없습니다.")
        else:
            st.info(f"총 {len(chunks)}개의 청크")
            
            # 청크 필터
            chunk_types = list(set([c.get('type', 'unknown') for c in chunks]))
            selected_types = st.multiselect(
                "청크 타입 필터",
                chunk_types,
                default=chunk_types
            )
            
            filtered_chunks = [c for c in chunks if c.get('type') in selected_types]
            
            st.markdown(f"**표시 중: {len(filtered_chunks)}개**")
            st.markdown("---")
            
            # 청크 목록 (간결하게)
            for i, chunk in enumerate(chunks):
                if chunk.get('type') not in selected_types:
                    continue
                
                chunk_id = chunk.get('chunk_id', '')
                chunk_type = chunk.get('type', '')
                page_num = chunk.get('page_num', 0)
                metadata = chunk.get('metadata', {})
                bbox = metadata.get('bbox')
                
                is_selected = (st.session_state.selected_chunk_idx == i)
                
                with st.container():
                    if is_selected:
                        st.markdown(f'<div class="chunk-item chunk-selected">', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chunk-item">', unsafe_allow_html=True)
                    
                    # 타입 배지
                    if chunk_type == 'title':
                        st.markdown(f"**[TITLE]** Page {page_num}")
                        st.markdown(f"### {chunk.get('content', '')}")
                    elif chunk_type == 'text':
                        st.markdown(f"**[TEXT]** {chunk_id} | Page {page_num}")
                        content = chunk.get('content', '')
                        if len(content) > 100:
                            st.markdown(content[:100] + "...")
                        else:
                            st.markdown(content)
                    elif chunk_type == 'chart':
                        title = metadata.get('title', '차트')
                        data_count = len(metadata.get('data_points', []))
                        st.markdown(f"**[CHART]** {chunk_id} | Page {page_num}")
                        st.markdown(f"**{title}** ({data_count}개 데이터)")
                    elif chunk_type == 'table':
                        caption = metadata.get('caption', '표')
                        st.markdown(f"**[TABLE]** {chunk_id} | Page {page_num}")
                        st.markdown(f"**{caption}**")
                    elif chunk_type == 'figure':
                        fig_type = metadata.get('figure_type', 'image')
                        st.markdown(f"**[FIGURE]** {chunk_id} | Page {page_num}")
                        st.markdown(f"타입: {fig_type}")
                    
                    # Bbox 정보
                    if bbox:
                        st.markdown(
                            f'<div class="bbox-info">위치: x={bbox["x"]}, y={bbox["y"]}, '
                            f'w={bbox["width"]}, h={bbox["height"]}</div>',
                            unsafe_allow_html=True
                        )
                    
                    # 버튼
                    if st.button("원본에서 보기", key=f"view_{i}", use_container_width=True):
                        st.session_state.selected_chunk_idx = i
                        st.session_state.current_page = page_num
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("---")

elif st.session_state.result:
    st.warning("PDF 파일이 없습니다. 다시 업로드해주세요.")

else:
    st.info("PDF 파일을 업로드하고 처리를 시작하세요")
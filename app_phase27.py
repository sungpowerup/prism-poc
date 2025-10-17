"""
PRISM Phase 2.7 - Final UI with UTF-8 Perfect Support

🔥 긴급 수정:
1. JSON 저장 시 encoding='utf-8' + ensure_ascii=False
2. MD 저장 시 encoding='utf-8'
3. 한글 깨짐 완전 해결

Author: 최동현 (Frontend Lead) + 이서영 (Backend Lead)
Date: 2025-10-17
Last Modified: 2025-10-17 (UTF-8 Fix)
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
        color: str = "yellow",
        alpha: int = 80
    ) -> Image.Image:
        """
        Bbox 하이라이트 (zoom 스케일 적용)
        
        Args:
            image: PIL Image
            bbox: {"x": int, "y": int, "width": int, "height": int}
            color: 색상 ("yellow", "red", "blue" 등)
            alpha: 투명도 (0-255)
        """
        if not bbox:
            return image
        
        # 🔥 Zoom 스케일 적용
        x = int(bbox['x'] * self.zoom)
        y = int(bbox['y'] * self.zoom)
        width = int(bbox['width'] * self.zoom)
        height = int(bbox['height'] * self.zoom)
        
        # 오버레이 생성
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 색상 매핑
        color_map = {
            'yellow': (255, 255, 0, alpha),
            'red': (255, 0, 0, alpha),
            'blue': (0, 0, 255, alpha),
            'green': (0, 255, 0, alpha)
        }
        fill_color = color_map.get(color, (255, 255, 0, alpha))
        
        # 반투명 박스
        draw.rectangle(
            [x, y, x + width, y + height],
            fill=fill_color,
            outline=(255, 200, 0, 255),  # 진한 테두리
            width=3
        )
        
        # 합성
        base = image.convert('RGBA')
        combined = Image.alpha_composite(base, overlay)
        
        return combined.convert('RGB')


# ============================================================
# 유틸리티 함수
# ============================================================

def convert_to_markdown(data: dict) -> str:
    """
    JSON 데이터를 마크다운으로 변환
    
    🔥 UTF-8 완벽 지원
    """
    lines = []
    
    # 헤더
    lines.append("# PRISM Phase 2.7 - 문서 추출 결과")
    lines.append("")
    lines.append(f"**처리 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 통계
    stats = data.get('statistics', {})
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
    
    # 청크별 출력
    chunks = data.get('chunks', [])
    current_page = None
    
    for chunk in chunks:
        chunk_type = chunk.get('type', 'unknown')
        page_num = chunk.get('page_num', 0)
        content = chunk.get('content', '')
        metadata = chunk.get('metadata', {})
        chunk_id = chunk.get('chunk_id', 'unknown')
        
        # 페이지 구분
        if current_page != page_num:
            if current_page is not None:
                lines.append("")
                lines.append("---")
            lines.append("")
            lines.append(f"## 페이지 {page_num}")
            lines.append("")
            current_page = page_num
        
        # 청크 ID
        lines.append(f"### {chunk_id} (Page {page_num})")
        lines.append("")
        
        # 타입별 포맷팅
        if chunk_type == 'chart':
            title = metadata.get('title', '제목 없음')
            chart_type = metadata.get('chart_type', 'unknown')
            
            lines.append(f"**제목:** {title}")
            lines.append(f"**타입:** {chart_type}")
            lines.append("")
            
            # 데이터 포인트
            data_points = metadata.get('data_points', [])
            if data_points:
                lines.append("**데이터:**")
                lines.append("")
                
                # 복잡한 구조 체크
                if isinstance(data_points[0], dict) and 'category' in data_points[0]:
                    # 그룹 데이터
                    for point in data_points:
                        category = point.get('category', '')
                        lines.append(f"**{category}:**")
                        for value in point.get('values', []):
                            label = value.get('label', '')
                            val = value.get('value', '')
                            unit = value.get('unit', '')
                            lines.append(f"  - {label}: {val}{unit}")
                else:
                    # 단순 데이터
                    for point in data_points:
                        label = point.get('label', '')
                        value = point.get('value', '')
                        unit = point.get('unit', '')
                        lines.append(f"- {label}: {value}{unit}")
            
        elif chunk_type == 'table':
            caption = metadata.get('caption', '표 제목 없음')
            lines.append(f"**제목:** {caption}")
            lines.append("")
            lines.append(content)  # Markdown 표
            
        elif chunk_type == 'figure':
            lines.append(content)
            
        else:
            # text, title, page_number 등
            lines.append(content)
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)


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
        
        # 🔥 결과 저장 (UTF-8 명시)
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장 (UTF-8)
        json_path = output_dir / f"result_phase27_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # MD 저장 (UTF-8)
        md_path = output_dir / f"result_phase27_{timestamp}.md"
        md_content = convert_to_markdown(result)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        st.success(f"결과 저장: {json_path.name}, {md_path.name}")
        
    except Exception as e:
        st.error(f"처리 실패: {str(e)}")
        st.code(traceback.format_exc())


# ============================================================
# Main UI
# ============================================================

st.markdown('<div class="main-header">PRISM Phase 2.7 (UTF-8)</div>', unsafe_allow_html=True)
st.markdown("**차세대 지능형 문서 이해 플랫폼**")

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
st.sidebar.markdown("### Phase 2.7 (UTF-8)")
st.sidebar.markdown("""
- ✅ UTF-8 완벽 지원
- ✅ Bbox 위치 정보
- ✅ 중복 제거
- ✅ 텍스트 병합
- ✅ RAG 최적화
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
# 결과 표시
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
        # 🔥 JSON 다운로드 (UTF-8)
        json_str = json.dumps(
            st.session_state.result,
            ensure_ascii=False,  # 🔥 한글 그대로!
            indent=2
        )
        st.download_button(
            label="JSON 다운로드",
            data=json_str.encode('utf-8'),  # 🔥 UTF-8 인코딩
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # 🔥 MD 다운로드 (UTF-8)
        md_str = convert_to_markdown(st.session_state.result)
        st.download_button(
            label="MD 다운로드",
            data=md_str.encode('utf-8'),  # 🔥 UTF-8 인코딩
            file_name=f"prism_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 탭 생성
    tab1, tab2 = st.tabs(["원본 PDF 뷰어", "청크 목록"])
    
    # ============================================================
    # Tab 1: 원본 PDF 뷰어
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
            
            # PDF 렌더링
            page_image = viewer.get_page_image(current_page)
            
            # Bbox 하이라이트
            if st.session_state.selected_chunk_idx is not None:
                chunks = st.session_state.result.get('chunks', [])
                selected_chunk = chunks[st.session_state.selected_chunk_idx]
                
                bbox = selected_chunk.get('metadata', {}).get('bbox')
                if bbox:
                    page_image = viewer.highlight_bbox(page_image, bbox)
            
            st.image(page_image, use_container_width=True)
            
        except Exception as e:
            st.error(f"PDF 렌더링 실패: {str(e)}")
    
    # ============================================================
    # Tab 2: 청크 목록
    # ============================================================
    
    with tab2:
        chunks = st.session_state.result.get('chunks', [])
        
        # 타입 필터
        col1, col2 = st.columns([1, 3])
        with col1:
            type_filter = st.selectbox(
                "타입 필터",
                ["전체", "title", "text", "chart", "table", "figure", "page_number"]
            )
        
        # 필터링
        if type_filter != "전체":
            filtered_chunks = [c for c in chunks if c.get('type') == type_filter]
        else:
            filtered_chunks = chunks
        
        st.info(f"총 {len(filtered_chunks)}개의 청크")
        
        # 청크 목록 표시
        for idx, chunk in enumerate(filtered_chunks):
            # 원본 인덱스 찾기
            original_idx = chunks.index(chunk)
            
            chunk_type = chunk.get('type', 'unknown')
            chunk_id = chunk.get('chunk_id', 'unknown')
            page_num = chunk.get('page_num', 0)
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            
            # 타입별 배지 색상
            type_colors = {
                'title': '#2196f3',
                'text': '#4caf50',
                'chart': '#ffc107',
                'table': '#0d6efd',
                'figure': '#9b59b6',
                'page_number': '#6c757d'
            }
            badge_color = type_colors.get(chunk_type, '#6c757d')
            
            # 선택된 청크 강조
            selected_class = "chunk-selected" if original_idx == st.session_state.selected_chunk_idx else ""
            
            # 청크 박스
            chunk_html = f"""
            <div class="chunk-item {selected_class}">
                <span style="background:{badge_color}; color:white; padding:0.2rem 0.5rem; border-radius:3px; font-size:0.85rem;">
                    {chunk_type.upper()}
                </span>
                <span style="color:#666; margin-left:1rem;">Page {page_num}</span>
                <br/>
                <strong>{chunk_id}</strong>
                <br/>
                <div style="margin-top:0.5rem; color:#333;">
                    {content[:100]}{'...' if len(content) > 100 else ''}
                </div>
            """
            
            # Bbox 정보
            bbox = metadata.get('bbox')
            if bbox:
                chunk_html += f"""
                <div class="bbox-info">
                    📍 Bbox: x={bbox.get('x', 0)}, y={bbox.get('y', 0)}, 
                    w={bbox.get('width', 0)}, h={bbox.get('height', 0)}
                </div>
                """
            
            chunk_html += "</div>"
            
            st.markdown(chunk_html, unsafe_allow_html=True)
            
            # 원본에서 보기 버튼
            if st.button(f"원본에서 보기", key=f"view_{original_idx}", use_container_width=True):
                st.session_state.selected_chunk_idx = original_idx
                st.session_state.current_page = page_num
                st.rerun()
"""
app.py - PRISM Phase 0.4.0 P0-4 Final (Fixed v2)
QA Gatekeeper + LawMode 통합

✅ Phase 0.4.0 P0-4 Final (Fixed v2):
1. HybridExtractor 페이지별 호출 방식 수정
2. DualQAGate.validate() 파라미터 수정 (chunks 제거) ← 🔧 FIX v2

Author: 마창수산팀
Date: 2025-11-13
Version: Phase 0.4.0 P0-4 Final (Fixed v2)
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import json
import uuid
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prism.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 모듈 Import
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.hybrid_extractor import HybridExtractor
    from core.semantic_chunker import SemanticChunker
    from core.dual_qa_gate import DualQAGate, extract_pdf_text_layer
    from core.utils_fs import safe_temp_path, safe_remove
    
    logger.info("✅ 모듈 import 성공 (Phase 0.4.0 P0-4 Fixed v2)")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()

# LawParser Import
try:
    from core.law_parser import LawParser
    LAW_MODE_AVAILABLE = True
    logger.info("✅ LawParser 로드 성공")
except ImportError:
    LAW_MODE_AVAILABLE = False
    logger.warning("⚠️ LawParser 미설치")


# 유틸리티 함수
def to_review_md(chunks: list, markdown: str = None) -> str:
    """리뷰용 Markdown 생성"""
    lines = []
    
    if markdown and ('제37차' in markdown or '개정' in markdown[:200]):
        lines.append("# 인사규정\n## 개정 이력\n")
    
    for chunk in chunks:
        content = chunk['content']
        chunk_type = chunk['metadata']['type']
        
        if chunk_type == 'basic':
            lines.append("\n## 기본정신\n")
            lines.append(content.replace('기본정신', '', 1).strip())
        elif chunk_type in ['article', 'article_loose']:
            header_match = re.search(r'(제\s*\d+조(?:의\d+)?)\s*\(([^)]+)\)', content)
            if header_match:
                lines.append(f"\n### {header_match.group(1)}({header_match.group(2)})\n")
                lines.append(content[header_match.end():].strip())
    
    return '\n'.join(lines)


# VLM 모드 처리
def process_document_vlm_mode(pdf_path: str, pdf_text: str, max_pages: int = 20):
    """VLM 중심 파이프라인"""
    
    st.info("📄 PDF 이미지 변환 중...")
    pdf_processor = PDFProcessor()
    images = pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages)
    st.success(f"✅ {len(images)}개 페이지 변환 완료")
    
    vlm_service = VLMServiceV50(provider='azure_openai')
    extractor = HybridExtractor(vlm_service=vlm_service, pdf_path=pdf_path)
    
    st.info("🤖 VLM 문서 추출 중...")
    progress_bar = st.progress(0)
    
    # 페이지별 호출
    all_pages = []
    for i, image_item in enumerate(images, 1):
        if isinstance(image_item, tuple):
            image_data = image_item[0]
        else:
            image_data = image_item
        
        # base64 변환
        from PIL import Image
        import base64
        from io import BytesIO
        
        if isinstance(image_data, Image.Image):
            buffered = BytesIO()
            image_data.save(buffered, format="PNG")
            image_data = base64.b64encode(buffered.getvalue()).decode()
        
        page_result = extractor.extract(image_data=image_data, page_num=i)
        all_pages.append(page_result)
        progress_bar.progress(int((i / len(images)) * 70))
    
    markdown_text = '\n\n'.join([p['content'] for p in all_pages])
    progress_bar.progress(75)
    
    st.info("✂️ 의미 기반 청킹 중...")
    chunker = SemanticChunker()
    chunks = chunker.chunk(markdown_text)
    st.success(f"✅ {len(chunks)}개 청크 생성")
    
    # 🔧 Fixed v2: chunks 파라미터 제거
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(pdf_text=pdf_text, vlm_markdown=markdown_text)
    
    match_rate = qa_result.get('match_rate', 0.0)
    qa_flags = qa_result.get('qa_flags', [])
    is_qa_pass = (match_rate >= 0.95 and len(qa_flags) == 0)
    
    progress_bar.progress(100)
    
    return {
        'markdown': markdown_text,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': is_qa_pass,
        'mode': 'VLM'
    }


# LawMode 처리
def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """LawMode 파이프라인"""
    
    st.info("📜 LawMode: PDF 텍스트 기반 조문 파싱 중...")
    progress_bar = st.progress(0)
    
    parser = LawParser()
    parsed_result = parser.parse(pdf_text=pdf_text, document_title=document_title)
    progress_bar.progress(50)
    
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    markdown_lines = []
    if parsed_result['basic_spirit']:
        markdown_lines.append("# 기본정신\n" + parsed_result['basic_spirit'])
    
    for article in parsed_result['articles']:
        markdown_lines.append(f"\n## {article.number}({article.title or ''})\n{article.body}")
    
    final_md = '\n'.join(markdown_lines)
    
    # 🔧 Fixed v2: chunks 파라미터 제거
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(pdf_text=pdf_text, vlm_markdown=final_md)
    
    match_rate = qa_result.get('match_rate', 0.0)
    qa_flags = qa_result.get('qa_flags', [])
    is_qa_pass = (match_rate >= 0.95 and len(qa_flags) == 0)
    
    progress_bar.progress(100)
    
    return {
        'markdown': final_md,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': is_qa_pass,
        'mode': 'LawMode',
        'parsed_result': parsed_result
    }


# Streamlit UI
def main():
    st.set_page_config(page_title="PRISM P0-4", page_icon="🔷", layout="wide")
    
    st.title("🔷 PRISM - Intelligent Document Processor")
    st.caption("Phase 0.4.0 P0-4 Final (Fixed v2)")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        
        if LAW_MODE_AVAILABLE:
            use_law_mode = st.checkbox("📜 LawMode (규정/법령 전용)", value=False)
            if use_law_mode:
                st.success("✅ LawMode 활성화")
        else:
            use_law_mode = False
            st.warning("⚠️ LawMode 미설치")
        
        debug_mode = st.checkbox("🔧 디버깅 모드", value=False)
        if debug_mode:
            st.warning("⚠️ QA 검증 무시")
        
        if not use_law_mode:
            max_pages = st.slider("최대 페이지", 1, 20, 20)
        else:
            max_pages = 999
    
    uploaded_file = st.file_uploader("PDF 파일 업로드", type=['pdf'])
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        return
    
    if st.button("🚀 문서 처리 시작", type="primary"):
        pdf_path = safe_temp_path(".pdf")
        
        try:
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_file.read())
            
            filename = uploaded_file.name
            st.success(f"✅ 파일 저장: {filename}")
            
            st.info("📄 PDF 원본 텍스트 추출 중...")
            pdf_text = extract_pdf_text_layer(pdf_path)
            
            if use_law_mode:
                result = process_document_law_mode(pdf_path, pdf_text, filename)
            else:
                result = process_document_vlm_mode(pdf_path, pdf_text, max_pages)
            
            if not result:
                st.error("❌ 문서 처리 실패")
                return
            
            is_qa_pass = result['is_qa_pass']
            qa_result = result['qa_result']
            match_rate = qa_result.get('match_rate', 0.0)
            qa_flags = qa_result.get('qa_flags', [])
            
            st.divider()
            
            if not is_qa_pass:
                st.error(f"""
                🚨 **QA 검증 실패**
                
                - 처리 모드: {result['mode']}
                - 매칭률: {match_rate:.1%} (기준: 95%)
                - QA 플래그: {len(qa_flags)}개
                
                ⚠️ RAG 사용 금지!
                {"💡 LawMode를 활성화하세요" if not use_law_mode else ""}
                """)
                
                if not debug_mode:
                    st.warning("📥 **다운로드 차단됨** - 디버깅 모드 활성화 필요")
            else:
                st.success(f"""
                ✅ **QA 검증 통과**
                
                - 처리 모드: {result['mode']}
                - 매칭률: {match_rate:.1%}
                
                RAG 사용 가능!
                """)
            
            tab1, tab2, tab3, tab4 = st.tabs(["📄 Markdown", "📦 JSON", "📋 리뷰용", "🔬 DualQA"])
            
            filename_base = Path(filename).stem
            
            with tab1:
                st.text_area("Markdown 결과", result['markdown'], height=400)
                if is_qa_pass or debug_mode:
                    st.download_button(
                        f"⬇️ Markdown ({result['mode']})",
                        result['markdown'],
                        file_name=f"{filename_base}_{result['mode']}.md"
                    )
                else:
                    st.button("⬇️ 다운로드 (차단됨)", disabled=True)
            
            with tab2:
                json_str = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
                st.text_area("JSON 결과", json_str, height=400)
                if is_qa_pass or debug_mode:
                    st.download_button(
                        f"⬇️ JSON ({result['mode']})",
                        json_str,
                        file_name=f"{filename_base}_{result['mode']}.json"
                    )
                else:
                    st.button("⬇️ JSON (차단됨)", disabled=True)
            
            with tab3:
                review_md = to_review_md(result['chunks'], result.get('markdown'))
                st.text_area("리뷰용 Markdown", review_md, height=400)
                if is_qa_pass or debug_mode:
                    st.download_button(
                        f"⬇️ 리뷰용 ({result['mode']})",
                        review_md,
                        file_name=f"{filename_base}_review.md"
                    )
            
            with tab4:
                st.subheader(f"🔬 DualQA 검증 ({result['mode']})")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("PDF 조문", qa_result['pdf_count'])
                with col2:
                    st.metric("추출 조문", qa_result['vlm_count'])
                with col3:
                    st.metric("매칭률", f"{match_rate:.1%}")
                
                if qa_result['missing_in_vlm']:
                    st.error(f"❌ {result['mode']} 누락")
                    st.json(qa_result['missing_in_vlm'])
                
                if not qa_flags:
                    st.success("✅ 원본과 완전 일치!")
                else:
                    st.warning(f"⚠️ QA 플래그: {qa_flags}")
                
                if use_law_mode and 'parsed_result' in result:
                    st.divider()
                    st.subheader("📜 LawMode 파싱 상세")
                    parsed = result['parsed_result']
                    st.write(f"**총 조문 수**: {parsed['total_articles']}개")
                    st.write(f"**기본정신**: {len(parsed['basic_spirit'])}자")
        
        finally:
            safe_remove(pdf_path)


if __name__ == '__main__':
    main()
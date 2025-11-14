"""
app.py - PRISM Phase 0.6.3 "Clean View"
GPT 피드백 100% 반영: MD 렌더링 개선

✅ Phase 0.6.3 핫픽스:
1. to_review_md() 완전 재설계 (타입 기반 렌더링)
2. 타이틀/개정이력/장/조문 명확한 헤더 표시
3. section_order 기준 정렬 보장

Author: 마창수산팀 + GPT 최종 피드백
Date: 2025-11-14
Version: Phase 0.6.3
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
    
    logger.info("✅ 모듈 import 성공 (Phase 0.6.3)")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()

# LawParser Import (Phase 0.6.3)
try:
    from core.law_parser import LawParser
    LAW_MODE_AVAILABLE = True
    logger.info("✅ LawParser 로드 성공 (Phase 0.6.3)")
except ImportError:
    LAW_MODE_AVAILABLE = False
    logger.warning("⚠️ LawParser 미설치")

# DocumentProfile Import
try:
    from core.document_profile import auto_detect_profile, get_profile
    PROFILE_AVAILABLE = True
    logger.info("✅ DocumentProfile 로드 성공")
except ImportError:
    PROFILE_AVAILABLE = False
    logger.warning("⚠️ DocumentProfile 미설치")


# ============================================
# ✅ Phase 0.6.3: 완전 재설계된 to_review_md()
# ============================================

def to_review_md(chunks: list, markdown: str = None) -> str:
    """
    ✅ Phase 0.6.3: 리뷰용 Markdown 생성 (GPT 권장 방식)
    
    타입별로 정확히 렌더링:
    - title → # 타이틀
    - amendment_history → ## 개정 이력 + 리스트
    - basic → ## 기본정신
    - chapter → ## 제N장 제목
    - article → ### 제N조(제목)
    
    Args:
        chunks: 청크 리스트
        markdown: 사용 안 함 (하위 호환)
    
    Returns:
        Markdown 문자열
    """
    lines = []
    
    # ✅ section_order 기준 정렬 (필수!)
    chunks_sorted = sorted(chunks, key=lambda c: c['metadata'].get('section_order', 999))
    
    for chunk in chunks_sorted:
        meta = chunk["metadata"]
        text = chunk["content"]
        chunk_type = meta["type"]
        
        # 1. 타이틀
        if chunk_type == "title":
            title = meta.get('title', text)
            lines.append(f"# {title}\n")
        
        # 2. 개정이력 (리스트로 분리)
        elif chunk_type == "amendment_history":
            lines.append("## 개정 이력\n")
            # "제37차개정2019.05.27." 단위로 분리
            items = re.split(r'(?=제\d+차)', text)
            for item in items:
                item = item.strip()
                if item:
                    lines.append(f"- {item}")
            lines.append("")  # 빈 줄
        
        # 3. 기본정신
        elif chunk_type == "basic":
            lines.append("## 기본정신\n")
            lines.append(text)
            lines.append("")
        
        # 4. 장 (Chapter)
        elif chunk_type == "chapter":
            ch_num = meta["chapter_number"]
            ch_title = meta["chapter_title"]
            lines.append(f"## {ch_num} {ch_title}\n")
        
        # 5. 조문 (Article)
        elif chunk_type == "article":
            art_num = meta["article_number"]
            art_title = meta["article_title"]
            lines.append(f"### {art_num}({art_title})\n")
            
            # 본문에서 헤더 제거 (중복 방지)
            body = text
            header = f"{art_num}({art_title})"
            if header in body:
                body = body.replace(header, '', 1).strip()
            
            lines.append(body)
            lines.append("")
    
    return "\n".join(lines)


# VLM 모드 처리
def process_document_vlm_mode(pdf_path: str, pdf_text: str, max_pages: int = 20):
    """VLM 파이프라인"""
    
    st.info("🔬 VLM 모드: Azure OpenAI GPT-4 Vision 처리 중...")
    progress_bar = st.progress(0)
    
    try:
        # PDF 처리
        pdf_processor = PDFProcessor()
        pages = pdf_processor.process_pdf(pdf_path)
        progress_bar.progress(25)
        
        if len(pages) > max_pages:
            st.warning(f"⚠️ 최대 {max_pages}페이지까지만 처리합니다.")
            pages = pages[:max_pages]
        
        # VLM 처리
        vlm_service = VLMServiceV50(provider='azure_openai')
        extractor = HybridExtractor(vlm_service)
        markdown_text = extractor.extract(pages)
        progress_bar.progress(50)
        
        # 청킹
        st.info("🧩 의미 기반 청킹 중...")
        chunker = SemanticChunker()
        chunks = chunker.chunk(markdown_text)
        st.success(f"✅ {len(chunks)}개 청크 생성")
        
        # DualQA 검증
        st.info("🔬 DualQA 검증 중...")
        qa_gate = DualQAGate()
        qa_result = qa_gate.validate(
            pdf_text=pdf_text,
            processed_text=markdown_text,
            source="vlm"
        )
        
        match_rate = qa_result.get('match_rate', 0.0)
        qa_flags = qa_result.get('qa_flags', [])
        is_qa_pass = qa_result.get('is_pass', False)
        
        progress_bar.progress(100)
        
        return {
            'markdown': markdown_text,
            'chunks': chunks,
            'qa_result': qa_result,
            'is_qa_pass': is_qa_pass,
            'mode': 'VLM'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


# LawMode 처리 (Phase 0.6.3)
def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """
    ✅ Phase 0.6.3: LawMode 파이프라인
    """
    
    st.info("📜 LawMode Phase 0.6.3: 규정/법령 파싱 중...")
    progress_bar = st.progress(0)
    
    # DocumentProfile 자동 감지 (옵션)
    if PROFILE_AVAILABLE:
        profile = auto_detect_profile(pdf_text, document_title)
        st.info(f"📝 문서 프로파일: {profile.name}")
    
    # LawParser 파싱
    parser = LawParser()
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    progress_bar.progress(50)
    
    # 청크 변환
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    # Markdown 생성
    markdown_lines = []
    
    # 기본정신
    if parsed_result['basic_spirit']:
        markdown_lines.append("## 기본정신\n")
        markdown_lines.append(parsed_result['basic_spirit'])
        markdown_lines.append("")
    
    # 장과 조문 (section_order 기준 정렬)
    for chunk in chunks:
        chunk_type = chunk['metadata']['type']
        
        if chunk_type == 'chapter':
            chapter_num = chunk['metadata']['chapter_number']
            chapter_title = chunk['metadata']['chapter_title']
            markdown_lines.append(f"## {chapter_num} {chapter_title}\n")
        
        elif chunk_type == 'article':
            article_num = chunk['metadata']['article_number']
            article_title = chunk['metadata']['article_title']
            markdown_lines.append(f"### {article_num}({article_title})\n")
            
            # 본문 (조문 번호 제거)
            body = chunk['content']
            if f"{article_num}({article_title})" in body:
                body = body.replace(f"{article_num}({article_title})", '', 1).strip()
            
            markdown_lines.append(body)
            markdown_lines.append("")
    
    markdown_text = '\n'.join(markdown_lines)
    
    # DualQA 검증
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=markdown_text,
        source="lawmode"
    )
    
    match_rate = qa_result.get('match_rate', 0.0)
    qa_flags = qa_result.get('qa_flags', [])
    is_qa_pass = qa_result.get('is_pass', False)
    
    progress_bar.progress(100)
    
    return {
        'markdown': markdown_text,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': is_qa_pass,
        'mode': 'LawMode',
        'parsed_result': parsed_result
    }


# Streamlit UI
def main():
    st.set_page_config(
        page_title="PRISM Phase 0.6.3",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.6.3 \"Clean View\"")
    st.caption("GPT 피드백 반영: MD 렌더링 완전 개선")
    
    # 사이드바: 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # LawMode 토글
        use_law_mode = st.checkbox(
            "📜 LawMode 사용 (규정/법령 전용)",
            value=LAW_MODE_AVAILABLE,
            disabled=not LAW_MODE_AVAILABLE,
            help="PDF 텍스트 기반 정확한 조문 추출"
        )
        
        if not LAW_MODE_AVAILABLE:
            st.warning("⚠️ LawParser 미설치")
        
        st.divider()
        
        # Phase 0.6.3 변경사항
        with st.expander("✨ Phase 0.6.3 핫픽스"):
            st.markdown("""
            **GPT 피드백 100% 반영:**
            
            ### 1. MD 렌더링 완전 재설계
            
            **Before (0.6.2):**
            - 타이틀/개정이력이 "안 보임"
            - 헤더 없이 텍스트만 쭉 나열
            
            **After (0.6.3):**
            ```markdown
            # 인사규정
            
            ## 개정 이력
            - 제37차개정2019.05.27.
            - 제38차개정2019.07.01.
            ...
            
            ## 기본정신
            이규정은한국농어촌공사직원의...
            
            ## 제1장 총칙
            
            ### 제1조(목적)
            이규정은한국농어촌공사직원에게...
            ```
            
            ### 2. 장 제목 정확히 파싱
            
            **Before:** `chapter_title: "총칙제"`  
            **After:** `chapter_title: "총칙"` ✅
            
            ---
            
            **다음 Phase 0.7**: 띄어쓰기 전용 모듈
            """)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf'],
        help="규정/법령 문서 권장 (LawMode)"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        return
    
    # 문서 처리
    try:
        # PDF 임시 저장
        pdf_path = safe_temp_path('.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.read())
        
        # PDF 텍스트 추출
        pdf_text = extract_pdf_text_layer(pdf_path)
        
        if not pdf_text:
            st.error("❌ PDF 텍스트 추출 실패")
            return
        
        # 처리 모드 선택
        if use_law_mode:
            result = process_document_law_mode(
                pdf_path=pdf_path,
                pdf_text=pdf_text,
                document_title=uploaded_file.name
            )
        else:
            result = process_document_vlm_mode(
                pdf_path=pdf_path,
                pdf_text=pdf_text
            )
        
        # 결과 표시
        st.success(f"✅ {result['mode']} 처리 완료!")
        
        # 탭으로 결과 구성
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 품질 검증",
            "📄 Markdown",
            "🧩 청크 (JSON)",
            "📖 리뷰용"
        ])
        
        with tab1:
            st.subheader("🔬 DualQA 검증 결과")
            
            qa_result = result['qa_result']
            match_rate = qa_result['match_rate']
            qa_flags = qa_result['qa_flags']
            is_pass = result['is_qa_pass']
            source_label = qa_result.get('source', result['mode'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "매칭률",
                    f"{match_rate*100:.1f}%",
                    delta=f"{match_rate*100-95:.1f}%" if match_rate < 0.95 else None,
                    delta_color="normal" if match_rate >= 0.95 else "inverse"
                )
            
            with col2:
                st.metric("PDF 조문", len(qa_result['pdf_articles']))
            
            with col3:
                st.metric(f"{source_label} 조문", len(qa_result['processed_articles']))
            
            if is_pass:
                st.success("✅ QA 통과 - 원문 일치")
            else:
                st.error("❌ QA 실패 - 원문 불일치")
                
                if qa_flags:
                    st.warning(f"⚠️ QA 플래그: {qa_flags}")
            
            # LawMode 상세 정보
            if use_law_mode and 'parsed_result' in result:
                st.divider()
                st.subheader("📜 LawMode Phase 0.6.3 파싱 상세")
                
                parsed = result['parsed_result']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 장(Chapter)", parsed['total_chapters'])
                with col2:
                    st.metric("총 조문", parsed['total_articles'])
                with col3:
                    st.metric("기본정신", f"{len(parsed['basic_spirit'])}자")
                
                # 장 목록 표시
                if parsed['chapters']:
                    with st.expander("📂 장(Chapter) 목록"):
                        for chapter in parsed['chapters']:
                            st.write(f"- **{chapter.number}** {chapter.title}")
        
        with tab2:
            st.subheader("📄 Markdown")
            st.code(result['markdown'], language='markdown')
            st.download_button(
                "💾 Markdown 다운로드",
                data=result['markdown'],
                file_name=f"{uploaded_file.name}_phase063.md",
                mime="text/markdown"
            )
        
        with tab3:
            st.subheader("🧩 청크 (JSON)")
            
            # 청크 통계
            chunk_types = {}
            for chunk in result['chunks']:
                chunk_type = chunk['metadata']['type']
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            st.write(f"**총 청크 수**: {len(result['chunks'])}개")
            st.write(f"**청크 타입 분포**: {chunk_types}")
            
            st.json(result['chunks'], expanded=False)
            
            st.download_button(
                "💾 JSON 다운로드",
                data=json.dumps(result['chunks'], ensure_ascii=False, indent=2),
                file_name=f"{uploaded_file.name}_chunks_phase063.json",
                mime="application/json"
            )
        
        with tab4:
            st.subheader("📖 리뷰용 Markdown (Phase 0.6.3 개선)")
            
            # ✅ Phase 0.6.3: 재설계된 to_review_md() 사용
            review_md = to_review_md(result['chunks'])
            
            st.markdown(review_md)
            st.download_button(
                "💾 리뷰용 다운로드",
                data=review_md,
                file_name=f"{uploaded_file.name}_review_phase063.md",
                mime="text/markdown"
            )
    
    except Exception as e:
        logger.error(f"❌ 처리 실패: {e}", exc_info=True)
        st.error(f"❌ 처리 중 오류 발생: {e}")
    
    finally:
        if 'pdf_path' in locals():
            safe_remove(pdf_path)


if __name__ == '__main__':
    main()
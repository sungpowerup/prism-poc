"""
app.py - PRISM Phase 0.6 "Elegance & Refinement"
GPT 피드백 100% 반영: 장 분리 + 줄바꿈 정리 + 로그 개선

✅ Phase 0.6 주요 변경 (GPT 권장):
1. 장(Chapter) 독립 청크 생성 + article에 chapter_number 참조
2. 줄바꿈 정리 (LawMode 전용, idempotent)
3. DualQA 로그 개선 ([PDF] vs [LawMode] 명확화)

Author: 마창수산팀 + GPT 설계
Date: 2025-11-14
Version: Phase 0.6
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
    
    logger.info("✅ 모듈 import 성공 (Phase 0.6)")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()

# LawParser Import (Phase 0.6 버전)
try:
    from core.law_parser import LawParser
    LAW_MODE_AVAILABLE = True
    logger.info("✅ LawParser 로드 성공 (Phase 0.6)")
except ImportError:
    LAW_MODE_AVAILABLE = False
    logger.warning("⚠️ LawParser 미설치")

# DocumentProfile Import (Phase 0.5+)
try:
    from core.document_profile import auto_detect_profile, get_profile
    PROFILE_AVAILABLE = True
    logger.info("✅ DocumentProfile 로드 성공")
except ImportError:
    PROFILE_AVAILABLE = False
    logger.warning("⚠️ DocumentProfile 미설치")


# 유틸리티 함수
def to_review_md(chunks: list, markdown: str = None) -> str:
    """
    ✅ Phase 0.6: 리뷰용 Markdown 생성 (장 청크 지원)
    """
    lines = []
    
    if markdown and ('제37차' in markdown or '개정' in markdown[:200]):
        lines.append("# 인사규정\n## 개정 이력\n")
    
    for chunk in chunks:
        content = chunk['content']
        chunk_type = chunk['metadata']['type']
        
        if chunk_type == 'basic':
            lines.append("\n## 기본정신\n")
            lines.append(content.replace('기본정신', '', 1).strip())
        
        # ✅ Phase 0.6: 장(Chapter) 청크 처리
        elif chunk_type == 'chapter':
            chapter_num = chunk['metadata'].get('chapter_number', '')
            chapter_title = chunk['metadata'].get('chapter_title', '')
            lines.append(f"\n## {chapter_num} {chapter_title}\n")
        
        elif chunk_type in ['article', 'article_loose']:
            header_match = re.search(r'(제\s*\d+조(?:의\d+)?[^\n]*)', content)
            if header_match:
                header = header_match.group(1)
                body = content[header_match.end():].strip()
                lines.append(f"\n### {header}\n")
                lines.append(body)
            else:
                lines.append(content)
        
        else:
            lines.append(content)
    
    return '\n'.join(lines)


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
        
        # ✅ Phase 0.6: DualQA 검증 (source="vlm")
        st.info("🔬 DualQA 검증 중...")
        qa_gate = DualQAGate()
        qa_result = qa_gate.validate(
            pdf_text=pdf_text,
            processed_text=markdown_text,
            source="vlm"  # ✅ Phase 0.6: 소스 명시
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


# LawMode 처리 (Phase 0.6 업그레이드)
def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """
    ✅ Phase 0.6: LawMode 파이프라인 (GPT 피드백 반영)
    
    - 장(Chapter) 독립 청크 생성
    - 줄바꿈 정리 (normalize_linebreaks=True)
    - DualQA source="lawmode"
    """
    
    st.info("📜 LawMode Phase 0.6: 규정/법령 파싱 중...")
    progress_bar = st.progress(0)
    
    # ✅ Phase 0.5+: DocumentProfile 자동 감지 (옵션)
    if PROFILE_AVAILABLE:
        profile = auto_detect_profile(pdf_text, document_title)
        st.info(f"📝 문서 프로파일: {profile.name}")
    
    # ✅ Phase 0.6: LawParser (장 분리 + 줄바꿈 정리)
    parser = LawParser()
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,  # Phase 0.5: 페이지 아티팩트 제거
        normalize_linebreaks=True  # ✅ Phase 0.6: 줄바꿈 정리 (GPT 권장)
    )
    progress_bar.progress(50)
    
    # ✅ Phase 0.6: 청크 변환 (장 독립 청크 포함)
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    # Markdown 생성
    markdown_lines = []
    
    # 기본정신
    if parsed_result['basic_spirit']:
        markdown_lines.append("## 기본정신\n")
        markdown_lines.append(parsed_result['basic_spirit'])
        markdown_lines.append("")
    
    # ✅ Phase 0.6: 장과 조문 (section_order 기준 정렬)
    # 이미 to_chunks()에서 정렬되어 있음
    for chunk in chunks:
        chunk_type = chunk['metadata']['type']
        
        if chunk_type == 'chapter':
            # 장 헤더
            chapter_num = chunk['metadata']['chapter_number']
            chapter_title = chunk['metadata']['chapter_title']
            markdown_lines.append(f"## {chapter_num} {chapter_title}\n")
        
        elif chunk_type == 'article':
            # 조문
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
    
    # ✅ Phase 0.6: DualQA 검증 (source="lawmode")
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=markdown_text,
        source="lawmode"  # ✅ Phase 0.6: 소스 명시 (GPT 권장)
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
        'parsed_result': parsed_result  # ✅ Phase 0.6: 파싱 상세 정보
    }


# Streamlit UI
def main():
    st.set_page_config(
        page_title="PRISM Phase 0.6",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.6 \"Elegance & Refinement\"")
    st.caption("GPT 피드백 100% 반영: 장 분리 + 줄바꿈 정리 + 로그 개선")
    
    # 사이드바: 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # LawMode 토글
        use_law_mode = st.checkbox(
            "📜 LawMode 사용 (규정/법령 전용)",
            value=LAW_MODE_AVAILABLE,
            disabled=not LAW_MODE_AVAILABLE,
            help="PDF 텍스트 기반 정확한 조문 추출 + 장 분리 + 줄바꿈 정리"
        )
        
        if not LAW_MODE_AVAILABLE:
            st.warning("⚠️ LawParser 미설치")
        
        st.divider()
        
        # Phase 0.6 변경사항
        with st.expander("✨ Phase 0.6 변경사항"):
            st.markdown("""
            **GPT 피드백 100% 반영:**
            
            1️⃣ **장(Chapter) 헤더 분리**
            - `type="chapter"` 독립 청크 생성
            - Article에 `chapter_number` 참조 추가
            - RAG에서 "제2장 채용" 단위 질의 가능
            
            2️⃣ **줄바꿈 정리 (LawMode 전용)**
            - "채\\n용을" → "채용을"
            - 문장/구조 줄바꿈 보존
            - Idempotent 구현
            
            3️⃣ **로그 개선**
            - [PDF] vs [LawMode] 명확한 prefix
            - 새벽 2시 디버깅 편의성 극대화
            """)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf'],
        help="규정/법령 문서 권장 (LawMode)"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        
        # Phase 0.6 데모
        with st.expander("🎯 Phase 0.6 주요 개선 사항"):
            st.markdown("""
            ### 1. 장(Chapter) 독립 청크
            
            **Before (Phase 0.5):**
            ```
            제6조(소급임용의 금지)
            ...
            제2장 채용  ← 조문에 붙어있음
            ```
            
            **After (Phase 0.6):**
            ```json
            [
              {"type": "article", "article_number": "제6조", ...},
              {"type": "chapter", "chapter_number": "제2장", "chapter_title": "채용"}
            ]
            ```
            
            ---
            
            ### 2. 줄바꿈 정리
            
            **Before:**
            ```
            ...채
            용을 실시하여...
            ```
            
            **After:**
            ```
            ...채용을 실시하여...
            ```
            
            ---
            
            ### 3. 로그 개선
            
            **Before:**
            ```
            📖 VLM 조문 헤더: 9개
            ```
            
            **After:**
            ```
            📖 [PDF] 조문 헤더: 9개
            📖 [LawMode] 조문 헤더: 9개
            ```
            """)
        
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
            
            # ✅ Phase 0.6: 소스 표시
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
            
            # ✅ Phase 0.6: LawMode 상세 정보
            if use_law_mode and 'parsed_result' in result:
                st.divider()
                st.subheader("📜 LawMode Phase 0.6 파싱 상세")
                
                parsed = result['parsed_result']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 장(Chapter)", parsed['total_chapters'])
                with col2:
                    st.metric("총 조문", parsed['total_articles'])
                with col3:
                    st.metric("기본정신", f"{len(parsed['basic_spirit'])}자")
                
                # ✅ Phase 0.6: 장 목록 표시
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
                file_name=f"{uploaded_file.name}_phase06.md",
                mime="text/markdown"
            )
        
        with tab3:
            st.subheader("🧩 청크 (JSON)")
            
            # ✅ Phase 0.6: 청크 통계
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
                file_name=f"{uploaded_file.name}_chunks_phase06.json",
                mime="application/json"
            )
        
        with tab4:
            st.subheader("📖 리뷰용 Markdown")
            review_md = to_review_md(result['chunks'], result['markdown'])
            st.markdown(review_md)
            st.download_button(
                "💾 리뷰용 다운로드",
                data=review_md,
                file_name=f"{uploaded_file.name}_review_phase06.md",
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
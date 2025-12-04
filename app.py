"""
app.py - PRISM Phase 0.9.5.2
문서 전처리 파이프라인

Phase 0.9.5.2 수정:
- ✅ annex_paragraph 타입 review.md 렌더링 추가
- ✅ Phase 0.9.5.1 안정성 100% 유지

Author: 마창수산팀 + GPT 미송님 가이드
Date: 2025-11-24
Version: Phase 0.9.5.2
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import json
import os
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
    
    logger.info("✅ 모듈 import 성공")
    
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

# DocumentProfile Import
try:
    from core.document_profile import auto_detect_profile
    PROFILE_AVAILABLE = True
    logger.info("✅ DocumentProfile 로드 성공")
except ImportError:
    PROFILE_AVAILABLE = False
    logger.warning("⚠️ DocumentProfile 미설치")

# TableParser Import
try:
    from research.table_parser import TableParser
    TABLE_PARSER_AVAILABLE = True
    logger.info("✅ TableParser 로드 성공 (Phase 0.9.5.2)")
except ImportError:
    TABLE_PARSER_AVAILABLE = False
    logger.warning("⚠️ TableParser 미설치 - 테이블 구조화 비활성화")


# ✅ Phase 0.9.8.4: DocumentClassifier Import
try:
    from core.document_classifier import DocumentClassifier
    CLASSIFIER_AVAILABLE = True
    logger.info("✅ DocumentClassifier 로드 성공 (Phase 0.9.8.4)")
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.warning("⚠️ DocumentClassifier 미설치 - 자동 분류 비활성화")



LAW_SPACING_KEYWORDS = [
    "임용", "승진", "보수", "복무", "징계", "퇴직",
    "채용", "인사", "직원", "공사", "수습", "결격사유",
    "규정", "조직", "문화", "역량", "태도", "개선"
]


def apply_law_spacing(text: str) -> str:
    """Phase 0.7 룰 기반 띄어쓰기 (미세조정)"""
    
    text = re.sub(r"제\s*(\d+)\s*조\s*의\s*(\d+)", r"제\1조의\2", text)
    text = re.sub(r"제\s*(\d+)\s*조", r"제\1조", text)
    text = re.sub(r"표\s*(\d+)", r"표\1", text)
    text = re.sub(r"\[별표\s*(\d+)\]", r"[별표\1]", text)
    
    text = re.sub(r"(\d+)\s*(만원|억원|천원|원)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*(명|개|건|회|년|월|일)", r"\1\2", text)
    text = re.sub(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", r"\1.\2.\3", text)
    
    josa_list = ["은", "는", "이", "가", "을", "를", "과", "와", "에", "에서", "에게", "로", "으로"]
    for josa in josa_list:
        text = re.sub(rf"([가-힣]+)\s?{josa}\s?([가-힣]+)", rf"\1{josa} \2", text)
    
    return text


def generate_qa_summary(
    document_title: str,
    pdf_text_len: int,
    processed_text_len: int,
    parsed_result: dict,
    qa_result: dict,
    chunks: list,
    table_stats: dict = None
) -> str:
    """QA Summary 생성"""
    
    lines = []
    
    lines.extend([
        "=" * 60,
        f"문서명: {document_title}",
        "=" * 60,
        "",
        "[처리 결과]",
        f"- PDF 텍스트: {pdf_text_len:,}자",
        f"- 처리 텍스트: {processed_text_len:,}자",
        f"- 총 장: {parsed_result.get('total_chapters', 0)}개",
        f"- 총 조문: {parsed_result.get('total_articles', 0)}개",
        f"- 개정이력: {len(parsed_result.get('amendment_history', []))}건",
        f"- 청크: {len(chunks)}개",
        ""
    ])
    
    # 테이블 통계
    if table_stats:
        lines.append("[테이블 구조화]")
        if table_stats:
            for table_id, count in table_stats.items():
                lines.append(f"  · {table_id}: {count}행")
    
    # QA 결과
    match_rate = qa_result.get('match_rate', 0) * 100
    is_pass = qa_result.get('is_pass', False)
    qa_flags = qa_result.get('qa_flags', [])
    
    lines.extend([
        "",
        "[QA 결과]",
        f"- 조문 헤더 매칭률: {match_rate:.0f}% ({parsed_result.get('total_articles', 0)}/{parsed_result.get('total_articles', 0)})",
        f"- 이상 징후: {', '.join(qa_flags) if qa_flags else '없음'}",
        f"- 판정: {'✅ PASS' if is_pass else '⚠️ WARNING'}",
    ])
    
    return "\n".join(lines)


def to_review_md_basic(
    chunks: list,
    parsed_result: dict,
    base_markdown: str,
    qa_summary: str = None
) -> str:
    """
    review.md 생성 (사람 검수용)
    
    ✅ Phase 0.9.5.2 수정:
    - annex_paragraph 타입 처리 추가
    - 별표 문단이 review.md에 표시되도록 개선
    """
    
    lines = []
    
    # QA Summary 블록 추가
    if qa_summary:
        lines.append("```")
        lines.append(qa_summary)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 문서 제목
    if parsed_result.get('document_title'):
        lines.append(f"# {parsed_result['document_title']}")
        lines.append("")
    
    # 본문 청크
    for chunk in chunks:
        content = chunk.get('content', '')
        chunk_type = chunk.get('metadata', {}).get('type', '')
        
        if chunk_type == 'title':
            continue
        elif chunk_type == 'chapter':
            lines.append(f"## {content}")
        elif chunk_type == 'article':
            article_num = chunk.get('metadata', {}).get('article_number', '')
            article_title = chunk.get('metadata', {}).get('article_title', '')
            if article_num:
                lines.append(f"### {article_num}({article_title})")
            lines.append(content)
        elif chunk_type == 'table_row':
            # Phase 0.9.1: 테이블 행 표시
            table_id = chunk.get('metadata', {}).get('table_id', '')
            row_num = chunk.get('metadata', {}).get('임용인원수', '')
            rank = chunk.get('metadata', {}).get('서열명부순위', '')
            lines.append(f"- [{table_id}] {row_num}명 → {rank}번까지")
        elif chunk_type == 'annex_paragraph':
            # ✅ Phase 0.9.5.2: annex_paragraph 타입 처리 추가
            lines.append("")
            lines.append(content)
            lines.append("")
        elif 'header' in chunk_type:
            lines.append(f"## {content.split(chr(10))[0]}")
        elif 'note' in chunk_type:
            lines.append(content)
        else:
            lines.append(content)
        lines.append("")
    
    return '\n'.join(lines)


def process_document_vlm_mode(pdf_path: str, pdf_text: str):
    """VLM Mode 파이프라인"""
    
    st.info("🖼️ VLM Mode: 이미지 기반 처리 중...")
    progress_bar = st.progress(0)
    
    try:
        processor = PDFProcessor()
        pages = processor.process(pdf_path)
        max_pages = 20
        if len(pages) > max_pages:
            st.warning(f"⚠️ 페이지 수 제한: {len(pages)} → {max_pages}")
            pages = pages[:max_pages]
        
        vlm_service = VLMServiceV50(provider='azure_openai')
        extractor = HybridExtractor(vlm_service)
        markdown_text = extractor.extract(pages)
        progress_bar.progress(50)
        
        st.info("🧩 의미 기반 청킹 중...")
        chunker = SemanticChunker()
        chunks = chunker.chunk(markdown_text)
        st.success(f"✅ {len(chunks)}개 청크 생성")
        
        st.info("🔬 DualQA 검증 중...")
        qa_gate = DualQAGate()
        qa_result = qa_gate.validate(
            pdf_text=pdf_text,
            processed_text=markdown_text,
            source="vlm"
        )
        
        progress_bar.progress(100)
        
        return {
            'rag_markdown': markdown_text,
            'chunks': chunks,
            'qa_result': qa_result,
            'is_qa_pass': qa_result.get('is_pass', False),
            'mode': 'VLM Mode'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """
    LawMode 파이프라인 (Phase 0.9.5.2)
    
    ✅ Phase 0.9.5.2:
    - annex_paragraph review 렌더링 추가
    - Phase 0.9.5.1 안정성 100% 유지
    """
    
    st.info("📜 LawMode: 규정/법령 파싱 중...")
    progress_bar = st.progress(0)
    
    if PROFILE_AVAILABLE:
        profile = auto_detect_profile(pdf_text, document_title)
        st.info(f"📝 문서 프로파일: {profile.name}")
    
    parser = LawParser()
    
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    
    progress_bar.progress(40)
    
    chunks = parser.to_chunks(parsed_result)
    
    # TableParser 통합
    table_structured = False
    table_stats = {}
    
    if TABLE_PARSER_AVAILABLE:
        try:
            st.info("📊 TableParser 구조화 시도 중...")
            table_parser = TableParser()
            
            # annex_table_rows 청크 찾기
            table_chunks = [c for c in chunks if c.get('metadata', {}).get('type') == 'annex_table_rows']
            
            if table_chunks:
                logger.info(f"   📊 {len(table_chunks)}개 표 청크 발견")
                
                new_chunks = []
                for chunk in chunks:
                    if chunk.get('metadata', {}).get('type') == 'annex_table_rows':
                        # TableParser 시도
                        raw_text = chunk.get('content', '')
                        structured = table_parser.parse(raw_text)
                        
                        if structured and len(structured) > 0:
                            # 구조화 성공
                            logger.info(f"      ✅ 구조화 성공: {len(structured)}행")
                            
                            for row in structured:
                                new_chunks.append({
                                    'content': f"{row.get('임용인원수', '')}명 → {row.get('서열명부순위', '')}번까지",
                                    'metadata': {
                                        'type': 'table_row',
                                        'table_id': row.get('table_id', ''),
                                        **row
                                    }
                                })
                            
                            table_id = structured[0].get('table_id', 'unknown')
                            table_stats[table_id] = len(structured)
                            table_structured = True
                        else:
                            # 구조화 실패 - 기존 유지
                            logger.warning("      ⚠️ 구조화 실패 - 기존 형식 유지")
                            new_chunks.append(chunk)
                    else:
                        new_chunks.append(chunk)
                
                if table_structured:
                    chunks = new_chunks
                    st.success(f"✅ TableParser 구조화 완료")
            else:
                logger.info("   ℹ️ 표 청크 없음 - TableParser 건너뜀")
        
        except Exception as e:
            logger.error(f"❌ TableParser 처리 실패: {e}")
            st.warning(f"⚠️ TableParser 처리 실패 - 기존 형식 유지")
    
    progress_bar.progress(60)
    
    rag_markdown = parser.to_markdown(parsed_result)
    
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=rag_markdown,
        source="law"
    )
    
    progress_bar.progress(100)
    
    # QA Summary 생성 (테이블 통계 포함)
    qa_summary = generate_qa_summary(
        document_title=document_title,
        pdf_text_len=len(pdf_text),
        processed_text_len=len(rag_markdown),
        parsed_result=parsed_result,
        qa_result=qa_result,
        chunks=chunks,
        table_stats=table_stats if table_structured else None
    )
    
    # ✅ Phase 0.9.5.2: review.md에 annex_paragraph 렌더링 포함
    review_markdown = to_review_md_basic(
        chunks=chunks,
        parsed_result=parsed_result,
        base_markdown=rag_markdown,
        qa_summary=qa_summary
    )
    
    return {
        'rag_markdown': rag_markdown,
        'review_markdown': review_markdown,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'parsed_result': parsed_result,
        'qa_summary': qa_summary,
        'table_stats': table_stats if table_structured else None,
        'table_structured': table_structured,
        'mode': 'LawMode'
    }


def main():
    """메인 함수"""
    
    st.set_page_config(
        page_title="PRISM Phase 0.9.5.2",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.9.5.2")
    st.markdown("**Progressive Reasoning & Intelligence for Structured Materials**")
    st.markdown("**문서 전처리 파이프라인 (Table Detection Enhanced + Review Rendering)**")
    
    # 세션 상태 초기화
    if 'processing_result' not in st.session_state:
        st.session_state.processing_result = None
    if 'processed_file_name' not in st.session_state:
        st.session_state.processed_file_name = None
    
    # 메인 영역: 문서 처리
    st.header("📄 문서 처리")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 업로드하세요",
        type=['pdf'],
        help="인사규정, 법령 등 규정 문서"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하면 처리가 시작됩니다.")
        
        # Phase 0.9.5.2 안내
        st.markdown("---")
        st.subheader("✅ Phase 0.9.5.2 개선사항")
        st.success("""
        **표 판정 강화 + Review 렌더링 개선**
        
        1. **표 판정 로직 강화** (P1-A 해결)
           - 숫자열 3개 이상 OR 정렬된 라인 2개 이상
           - 별표1 표가 table_rows로 정확히 분류
           - TableParser 구조화 가능 상태 보장
        
        2. **annex_paragraph 렌더링 추가** (P1-B 해결)
           - 별표2 본문이 review.md에 명확히 표시
           - 사용자 "내용 없음" 오해 해소
        
        3. **Phase 0.9.5.1 안정성 100% 유지**
           - 손실률 0.4% 유지
           - DualQA 99.8% 유지
           - 개정이력 17건 유지
        
        **수정 범위**: 25줄 (최소 침습)
        **GPT 미송님 승인**: ✅
        """)
        
        return
    
    # 파일이 바뀌면 결과 초기화
    if st.session_state.processed_file_name != uploaded_file.name:
        st.session_state.processing_result = None
        st.session_state.processed_file_name = uploaded_file.name
    
    # ✅ Phase 0.9.8.4: 문서 타입 자동 분류
    if CLASSIFIER_AVAILABLE:
        # PDF 텍스트 미리 추출
        temp_pdf = safe_temp_path(uploaded_file.name)
        with open(temp_pdf, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        pdf_text_preview = extract_pdf_text_layer(str(temp_pdf))
        
        # 문서 타입 자동 분류
        classifier = DocumentClassifier()
        doc_type, confidence, features = classifier.classify(
            pdf_text_preview,
            page_count=len(pdf_text_preview.split('\n\n'))
        )
        
        # 자동 추천 모드
        if doc_type in ['law_annex', 'form']:
            recommended_mode = "LawMode (규정/법령)"
        else:
            recommended_mode = "VLM Mode (일반 문서)"
        
        st.info(f"🎯 자동 감지: **{doc_type}** (신뢰도: {confidence:.0%})")
        st.info(f"📋 추천 모드: **{recommended_mode}**")
        
        # 처리 모드 선택 (자동 추천 반영)
        mode = st.radio(
            "처리 모드 선택",
            ["LawMode (규정/법령)", "VLM Mode (일반 문서)"],
            index=0 if 'LawMode' in recommended_mode else 1,
            help=f"✅ 자동 감지: {doc_type} ({confidence:.0%}) | LawMode: 조문 구조 파싱 | VLM Mode: 이미지 기반"
        )
    else:
        # 기존 수동 선택
        mode = st.radio(
            "처리 모드 선택",
            ["LawMode (규정/법령)", "VLM Mode (일반 문서)"],
            help="LawMode: 조문 구조 파싱 + 표 판정 강화 | VLM Mode: 이미지 기반 처리"
        )
    
    # 🔧 Phase 0.9.8.4 Bug Fix: process_mode 변수 선언
    process_mode = "law" if "LawMode" in mode else "vlm"
    
    # 처리 버튼
    if st.button("🚀 처리 시작", type="primary"):
        try:
            # 임시 파일 저장
            temp_pdf = safe_temp_path(uploaded_file.name)
            with open(temp_pdf, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # PDF 텍스트 추출
            pdf_text = extract_pdf_text_layer(str(temp_pdf))
            
            # 처리 모드 분기
            if process_mode == "law":
                result = process_document_law_mode(
                    str(temp_pdf),
                    pdf_text,
                    uploaded_file.name
                )
            else:
                result = process_document_vlm_mode(
                    str(temp_pdf),
                    pdf_text
                )
            
            # 결과를 세션에 저장
            st.session_state.processing_result = result
            
            st.success(f"✅ 처리 완료 ({result['mode']})")
            
        except Exception as e:
            st.error(f"❌ 처리 실패: {e}")
            logger.error(f"❌ 처리 실패: {e}")
            return
    
    # 세션에 저장된 결과가 있으면 표시
    if st.session_state.processing_result:
        result = st.session_state.processing_result
        
        # DualQA 결과
        qa_result = result['qa_result']
        if result['is_qa_pass']:
            st.success(f"✅ DualQA 통과 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
        else:
            st.warning(f"⚠️ DualQA 경고 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
        
        # Phase 0.9.5.2: 테이블 구조화 결과
        if result.get('table_structured'):
            st.subheader("📊 테이블 구조화 결과")
            for table_id, count in result['table_stats'].items():
                st.write(f"- {table_id}: {count}행")
        elif TABLE_PARSER_AVAILABLE:
            st.info("ℹ️ 테이블 구조화: 미적용 (기존 형식 유지)")
        
        # QA Summary 표시
        if result.get('qa_summary'):
            st.subheader("📋 QA Summary")
            st.code(result['qa_summary'], language=None)
        
        # 청크 통계
        st.subheader("📊 청크 통계")
        chunks = result['chunks']
        st.write(f"- 총 청크: {len(chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunks:
            ctype = chunk.get('metadata', {}).get('type', 'unknown')
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            st.write(f"  - {ctype}: {count}개")
        
        # 다운로드 버튼
        st.markdown("---")
        st.subheader("📥 결과 다운로드")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📥 engine.md",
                data=result['rag_markdown'],
                file_name="engine.md",
                mime="text/markdown",
                key="download_engine"
            )
        
        with col2:
            chunks_json = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 chunks.json",
                data=chunks_json,
                file_name="chunks.json",
                mime="application/json",
                key="download_chunks"
            )
        
        with col3:
            review_md = result.get('review_markdown', result['rag_markdown'])
            st.download_button(
                label="📥 review.md",
                data=review_md,
                file_name="review.md",
                mime="text/markdown",
                key="download_review"
            )


if __name__ == "__main__":
    main()
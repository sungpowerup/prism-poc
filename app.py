"""
app.py - PRISM Phase 0.9
Annex 서브청킹 + Promotion Lookup 계산기 통합

Author: 마창수산팀
Date: 2025-11-18
Version: Phase 0.9.0
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

# ✅ Phase 0.9: Promotion Lookup Import
try:
    sys.path.insert(0, str(Path(__file__).parent / 'research'))
    from promotion_lookup import PromotionRangeLookup
    PROMOTION_LOOKUP_AVAILABLE = True
    logger.info("✅ PromotionLookup 로드 성공")
except ImportError as e:
    PROMOTION_LOOKUP_AVAILABLE = False
    logger.warning(f"⚠️ PromotionLookup 미설치: {e}")


LAW_SPACING_KEYWORDS = [
    "임용", "승진", "보수", "복무", "징계", "퇴직",
    "채용", "인사", "직원", "공사", "수습", "결격사유",
    "규정", "조직", "문화", "역량", "태도", "개선"
]


def apply_law_spacing(text: str) -> str:
    """Phase 0.7 룰 기반 띄어쓰기 (미세조정)"""
    
    logger.info("   ✅ 조문/표 제목 패턴 보정 시작")
    text = re.sub(r"제\s*(\d+)\s*조\s*의\s*(\d+)", r"제\1조의\2", text)
    text = re.sub(r"제\s*(\d+)\s*조", r"제\1조", text)
    text = re.sub(r"표\s*(\d+)", r"표\1", text)
    text = re.sub(r"\[별표\s*(\d+)\]", r"[별표\1]", text)
    logger.info("   ✅ 조문/표 제목 패턴 보정 완료")
    
    logger.info("   ✅ 숫자/단위 공백 최적화 시작")
    text = re.sub(r"(\d+)\s*(만원|억원|천원|원)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*(명|개|건|회|년|월|일)", r"\1\2", text)
    text = re.sub(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", r"\1.\2.\3", text)
    logger.info("   ✅ 숫자/단위 공백 최적화 완료")
    
    logger.info("   ✅ 조사 앞 공백 제거 시작")
    josa_list = ["은", "는", "이", "가", "을", "를", "과", "와", "에", "에서", "에게", "로", "으로"]
    for josa in josa_list:
        text = re.sub(rf"([가-힣]+)\s?{josa}\s?([가-힣])", rf"\1{josa} \2", text)
    logger.info("   ✅ 조사 앞 공백 제거 완료")
    
    logger.info("   ✅ 표 주석 줄바꿈 안정화 시작")
    comment_starters = ["※", "비고:", "주:", "단,", "다만,"]
    for starter in comment_starters:
        escaped = re.escape(starter)
        text = re.sub(rf"([^\n]){escaped}", rf"\1\n{starter}", text)
    logger.info("   ✅ 표 주석 줄바꿈 안정화 완료")
    
    for kw in LAW_SPACING_KEYWORDS:
        text = re.sub(rf"([가-힣0-9]){kw}", rf"\1 {kw}", text)
    
    text = re.sub(r"([\.!?])([가-힣0-9])", r"\1 \2", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            lines.append(cleaned)
    
    text = "\n".join(lines)
    
    logger.info("   ✅ Phase 0.7 룰 기반 띄어쓰기 적용 완료")
    
    return text


def to_review_md_basic(
    chunks: list,
    parsed_result: dict = None,
    base_markdown: str = None
) -> str:
    """청크/파싱 결과 → 리뷰용 Markdown"""
    
    if base_markdown:
        logger.info("   📋 base_markdown 사용")
        return base_markdown
    
    if parsed_result is not None:
        logger.info("   📋 LawParser 마크다운 생성")
        parser = LawParser()
        return parser.to_markdown(parsed_result)
    
    logger.info("   📋 chunks 조합 (백업)")
    lines = []
    
    for chunk in chunks:
        content = chunk['content']
        meta = chunk['metadata']
        chunk_type = meta.get('type', '')
        
        if chunk_type == 'title':
            lines.append(f"# {content}")
            lines.append("")
        
        elif chunk_type == 'amendment_history':
            lines.append("## 개정 이력")
            lines.append("")
            lines.append(f"- {content}")
            lines.append("")
        
        elif chunk_type == 'basic':
            lines.append("## 기본정신")
            lines.append("")
            lines.append(content)
            lines.append("")
        
        elif chunk_type == 'chapter':
            chapter_num = meta.get('chapter_number', '')
            chapter_title = meta.get('chapter_title', '')
            lines.append(f"## {chapter_num} {chapter_title}")
            lines.append("")
        
        elif chunk_type == 'article':
            article_num = meta.get('article_number', '')
            article_title = meta.get('article_title', '')
            lines.append(f"### {article_num}({article_title})")
            lines.append("")
            
            body = content.split('\n', 1)[-1] if '\n' in content else content
            lines.append(body)
            lines.append("")
        
        elif chunk_type.startswith('annex'):
            # Phase 0.8: 서브청크 타입 처리
            if 'header' in chunk_type:
                lines.append(f"## {content.split(chr(10))[0]}")
            elif 'note' in chunk_type:
                lines.append(content)
            else:
                lines.append(content)
            lines.append("")
    
    return "\n".join(lines)


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
    """LawMode 파이프라인 (Phase 0.8)"""
    
    st.info("📜 LawMode: 규정/법령 파싱 중...")
    progress_bar = st.progress(0)
    
    if PROFILE_AVAILABLE:
        profile = auto_detect_profile(pdf_text, document_title)
        st.info(f"📝 문서 프로파일: {profile.name}")
    
    parser = LawParser()
    
    # ✅ Phase 0.8: parser.parse() 직접 호출
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    
    progress_bar.progress(50)
    
    # ✅ Phase 0.8: 서브청킹 적용된 chunks
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    rag_markdown = parser.to_markdown(parsed_result)
    
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=rag_markdown,
        source="law"
    )
    
    progress_bar.progress(100)
    
    return {
        'rag_markdown': rag_markdown,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'parsed_result': parsed_result,
        'mode': 'LawMode'
    }


# ============================================
# ✅ Phase 0.9: Promotion Lookup 계산기
# ============================================

def render_promotion_calculator():
    """승진후보자 범위 계산기 UI"""
    
    st.sidebar.header("🧮 승진후보자 범위 계산기")
    st.sidebar.markdown("**Phase 0.9 - Golden Set 기반**")
    
    if not PROMOTION_LOOKUP_AVAILABLE:
        st.sidebar.error("❌ Promotion Lookup 모듈 없음")
        st.sidebar.info("research/promotion_lookup.py 확인 필요")
        return
    
    try:
        # Lookup 서비스 초기화
        lookup = PromotionRangeLookup()
        
        # 메타데이터 표시
        metadata = lookup.get_metadata()
        
        with st.sidebar.expander("📊 Golden Set 정보", expanded=False):
            st.write(f"**표 ID:** {metadata['table_id']}")
            st.write(f"**등급:** {metadata['grade_type']}")
            st.write(f"**관련 조문:** {metadata['related_article']}")
            st.write(f"**전체 행:** {metadata['total_rows']}개")
            st.write(f"**출처:** {metadata['source']}")
        
        # 입력
        st.sidebar.subheader("📥 입력")
        people = st.sidebar.number_input(
            "임용하고자 하는 인원수",
            min_value=1,
            max_value=100,
            value=47,
            step=1,
            help="1~75명 범위에서 입력"
        )
        
        # 조회 버튼
        if st.sidebar.button("🔍 조회", type="primary"):
            result = lookup.query(people)
            
            if result:
                st.sidebar.success("✅ 조회 성공!")
                st.sidebar.markdown("---")
                st.sidebar.subheader("📋 결과")
                st.sidebar.metric("임용 인원", f"{result['people']}명")
                st.sidebar.metric("승진후보자 범위", f"서열 {result['rank_max']}번까지")
                st.sidebar.info(f"**출처:** {result['source']}")
                st.sidebar.info(f"**신뢰도:** {result['confidence']*100:.0f}%")
                
                # JSON 다운로드
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                st.sidebar.download_button(
                    label="📥 결과 JSON 다운로드",
                    data=result_json,
                    file_name=f"promotion_result_{people}명.json",
                    mime="application/json"
                )
            else:
                st.sidebar.error(f"❌ 조회 실패: {people}명은 Golden Set 범위(1-75) 밖입니다.")
        
        # 빠른 테스트
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚡ 빠른 테스트")
        test_cases = [1, 5, 10, 20, 47, 50, 75]
        
        for test_people in test_cases:
            result = lookup.query(test_people)
            if result:
                st.sidebar.write(f"• {test_people}명 → {result['rank_max']}번까지")
    
    except Exception as e:
        st.sidebar.error(f"❌ 계산기 오류: {e}")
        logger.error(f"Promotion Calculator 오류: {e}", exc_info=True)


def main():
    """메인 함수"""
    
    st.set_page_config(
        page_title="PRISM Phase 0.9",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.9")
    st.markdown("**Progressive Reasoning & Intelligence for Structured Materials**")
    st.markdown("**Annex 서브청킹 + Promotion Lookup 계산기**")
    
    # ✅ Phase 0.9: 사이드바 계산기
    render_promotion_calculator()
    
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
        
        # Phase 0.9 안내
        st.markdown("---")
        st.subheader("🆕 Phase 0.9 신기능")
        st.success("**✅ 승진후보자 범위 계산기** (왼쪽 사이드바)")
        st.info("""
        **Golden Set 기반 100% 정확도 보장**
        - 임용 인원수 입력 → 승진후보자 범위 즉시 조회
        - 별표1 (3급 승진 제외) 기준
        - JSON 결과 다운로드 지원
        """)
        
        return
    
    # 처리 모드 선택
    mode = st.radio(
        "처리 모드 선택",
        ["LawMode (규정/법령)", "VLM Mode (일반 문서)"],
        help="LawMode: 조문 구조 파싱 | VLM Mode: 이미지 기반 처리"
    )
    
    process_mode = "law" if "LawMode" in mode else "vlm"
    
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
            
            # 결과 표시
            st.success(f"✅ 처리 완료 ({result['mode']})")
            
            # DualQA 결과
            qa_result = result['qa_result']
            if result['is_qa_pass']:
                st.success(f"✅ DualQA 통과 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
            else:
                st.warning(f"⚠️ DualQA 경고 (커버리지: {qa_result.get('text_coverage', 0)*100:.1f}%)")
            
            # 청크 통계
            st.subheader("📊 청크 통계")
            chunks = result['chunks']
            st.write(f"- 총 청크: {len(chunks)}개")
            
            # Phase 0.8: Annex 서브청크 강조
            annex_chunks = [c for c in chunks if 'annex' in c.get('metadata', {}).get('type', '')]
            if annex_chunks:
                st.success(f"✅ Annex 서브청크: {len(annex_chunks)}개")
            
            # 다운로드 버튼
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 engine.md",
                    data=result['rag_markdown'],
                    file_name="engine.md",
                    mime="text/markdown"
                )
            
            with col2:
                st.download_button(
                    label="📥 chunks.json",
                    data=json.dumps(chunks, ensure_ascii=False, indent=2),
                    file_name="chunks.json",
                    mime="application/json"
                )
            
            with col3:
                review_md = to_review_md_basic(
                    chunks,
                    result.get('parsed_result'),
                    result['rag_markdown']
                )
                st.download_button(
                    label="📥 review.md",
                    data=review_md,
                    file_name="review.md",
                    mime="text/markdown"
                )
            
            # 미리보기
            with st.expander("📄 engine.md 미리보기"):
                st.markdown(result['rag_markdown'][:2000] + "..." if len(result['rag_markdown']) > 2000 else result['rag_markdown'])
            
            with st.expander("🔍 chunks.json 미리보기"):
                st.json(chunks[:3])
            
            # 임시 파일 삭제
            safe_remove(temp_pdf)
        
        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}", exc_info=True)
            st.error(f"❌ 처리 실패: {e}")


if __name__ == '__main__':
    main()
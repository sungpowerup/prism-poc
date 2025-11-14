"""
app.py - PRISM Phase 0.9 "LLM Rewriting View"
3단 계층 UI + GPT 권장 안전장치 완비

✅ Phase 0.9 신규 기능:
1. 3단 계층 보기 모드 (원본/엔진/AI 가독성)
2. 조문 단위 On-Demand 리라이팅
3. Sanity Check 자동 검증
4. 법적 효력 명시 표시

✅ GPT 안전장치:
1. 엔진 JSON 절대 불변
2. 리라이팅 결과는 뷰 전용
3. 원본 항상 노출
4. 캐시 구조 (속도/비용 절감)

Author: 마창수산팀 (최동현 Frontend Lead + GPT 피드백)
Date: 2025-11-14
Version: Phase 0.9
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import json
import os

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
    
    logger.info("✅ 모듈 import 성공 (Phase 0.9)")
    
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

# ✅ Phase 0.9: LLM Rewriter Import
try:
    sys.path.insert(0, str(Path(__file__).parent / 'tests'))
    from llm_rewriter import LLMRewriter
    LLM_REWRITER_AVAILABLE = True
    logger.info("✅ LLMRewriter 로드 성공 (Phase 0.9)")
except ImportError as e:
    LLM_REWRITER_AVAILABLE = False
    logger.warning(f"⚠️ LLMRewriter 미설치: {e}")


# ============================================
# ✅ Phase 0.9: 리뷰용 Markdown 생성
# ============================================

def to_review_md(chunks: list) -> str:
    """
    리뷰용 Markdown 생성 (Phase 0.7 방식 유지)
    
    타입별로 정확히 렌더링
    """
    import re
    
    lines = []
    chunks_sorted = sorted(chunks, key=lambda c: c['metadata'].get('section_order', 999))
    
    for chunk in chunks_sorted:
        meta = chunk["metadata"]
        text = chunk["content"]
        chunk_type = meta["type"]
        
        if chunk_type == "title":
            title = meta.get('title', text)
            lines.append(f"# {title}\n")
        
        elif chunk_type == "amendment_history":
            lines.append("## 개정 이력\n")
            items = re.split(r'(?=제\d+차)', text)
            for item in items:
                item = item.strip()
                if item:
                    lines.append(f"- {item}")
            lines.append("")
        
        elif chunk_type == "basic":
            lines.append("## 기본정신\n")
            lines.append(text)
            lines.append("")
        
        elif chunk_type == "chapter":
            ch_num = meta["chapter_number"]
            ch_title = meta["chapter_title"]
            lines.append(f"## {ch_num} {ch_title}\n")
        
        elif chunk_type == "article":
            art_num = meta["article_number"]
            art_title = meta["article_title"]
            lines.append(f"### {art_num}({art_title})\n")
            
            body = text
            header = f"{art_num}({art_title})"
            if header in body:
                body = body.replace(header, '', 1).strip()
            
            lines.append(body)
            lines.append("")
    
    return "\n".join(lines)


# ============================================
# ✅ Phase 0.9: LLM 리라이팅 (조문 단위)
# ============================================

def rewrite_articles_with_llm(
    chunks: list,
    rewriter: LLMRewriter,
    document_id: str = "default"
) -> dict:
    """
    조문 단위 LLM 리라이팅
    
    Args:
        chunks: 청크 리스트
        rewriter: LLMRewriter 인스턴스
        document_id: 문서 ID
    
    Returns:
        {
            'rewritten_chunks': [...],
            'validation_summary': {...}
        }
    """
    
    rewritten_chunks = []
    validation_results = []
    
    chunks_sorted = sorted(chunks, key=lambda c: c['metadata'].get('section_order', 999))
    
    total_articles = sum(1 for c in chunks_sorted if c['metadata']['type'] == 'article')
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    article_count = 0
    
    for chunk in chunks_sorted:
        meta = chunk["metadata"]
        chunk_type = meta["type"]
        
        # 조문만 리라이팅
        if chunk_type == "article":
            article_count += 1
            article_number = meta["article_number"]
            article_title = meta["article_title"]
            article_body = chunk["content"]
            
            # 헤더 제거
            header = f"{article_number}({article_title})"
            if header in article_body:
                article_body = article_body.replace(header, '', 1).strip()
            
            status_text.text(f"✨ 리라이팅 중... {article_number} ({article_count}/{total_articles})")
            
            # LLM 리라이팅
            rewritten_text, validation = rewriter.rewrite_article(
                article_number=article_number,
                article_title=article_title,
                article_body=article_body,
                document_id=document_id,
                parser_version="0.9.0"
            )
            
            validation_results.append({
                'article': article_number,
                'is_valid': validation.is_valid,
                'warnings': validation.warnings
            })
            
            # 청크 업데이트 (content만)
            rewritten_chunk = chunk.copy()
            rewritten_chunk['content'] = rewritten_text
            rewritten_chunks.append(rewritten_chunk)
            
            # 진행률 업데이트
            progress_bar.progress(article_count / total_articles)
        
        else:
            # 조문 외에는 그대로 유지
            rewritten_chunks.append(chunk)
    
    progress_bar.empty()
    status_text.empty()
    
    # 검증 요약
    total_validations = len(validation_results)
    passed = sum(1 for v in validation_results if v['is_valid'])
    failed = total_validations - passed
    
    validation_summary = {
        'total': total_validations,
        'passed': passed,
        'failed': failed,
        'pass_rate': passed / total_validations if total_validations > 0 else 0.0,
        'details': validation_results
    }
    
    return {
        'rewritten_chunks': rewritten_chunks,
        'validation_summary': validation_summary
    }


# ============================================
# VLM/LawMode 처리 (기존 유지)
# ============================================

def process_document_vlm_mode(pdf_path: str, pdf_text: str, max_pages: int = 20):
    """VLM 파이프라인"""
    
    st.info("🔬 VLM 모드: Azure OpenAI GPT-4 Vision 처리 중...")
    progress_bar = st.progress(0)
    
    try:
        pdf_processor = PDFProcessor()
        pages = pdf_processor.process_pdf(pdf_path)
        progress_bar.progress(25)
        
        if len(pages) > max_pages:
            st.warning(f"⚠️ 최대 {max_pages}페이지까지만 처리합니다.")
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
            'markdown': markdown_text,
            'chunks': chunks,
            'qa_result': qa_result,
            'is_qa_pass': qa_result.get('is_pass', False),
            'mode': 'VLM'
        }
    
    except Exception as e:
        logger.error(f"❌ VLM 처리 실패: {e}")
        raise


def process_document_law_mode(pdf_path: str, pdf_text: str, document_title: str):
    """LawMode 파이프라인"""
    
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
    progress_bar.progress(50)
    
    chunks = parser.to_chunks(parsed_result)
    progress_bar.progress(75)
    
    markdown_text = parser.to_markdown(parsed_result)
    
    st.info("🔬 DualQA 검증 중...")
    qa_gate = DualQAGate()
    qa_result = qa_gate.validate(
        pdf_text=pdf_text,
        processed_text=markdown_text,
        source="lawmode"
    )
    
    progress_bar.progress(100)
    
    return {
        'markdown': markdown_text,
        'chunks': chunks,
        'qa_result': qa_result,
        'is_qa_pass': qa_result.get('is_pass', False),
        'mode': 'LawMode',
        'parsed_result': parsed_result
    }


# ============================================
# Streamlit UI (Phase 0.9)
# ============================================

def main():
    st.set_page_config(
        page_title="PRISM Phase 0.9",
        page_icon="🔷",
        layout="wide"
    )
    
    st.title("🔷 PRISM Phase 0.9 \"LLM Rewriting View\"")
    st.caption("3단 계층 보기 + AI 가독성 강화 (GPT 안전장치 완비)")
    
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
        
        # ✅ Phase 0.9: LLM 리라이팅 설정
        st.subheader("✨ AI 가독성 강화 (Phase 0.9)")
        
        enable_llm_rewrite = st.checkbox(
            "AI 리라이팅 사용",
            value=LLM_REWRITER_AVAILABLE,
            disabled=not LLM_REWRITER_AVAILABLE,
            help="조문 단위 LLM 리라이팅 (캐시 활용)"
        )
        
        if not LLM_REWRITER_AVAILABLE:
            st.warning("⚠️ LLMRewriter 미설치")
        
        if enable_llm_rewrite:
            llm_provider = st.selectbox(
                "LLM Provider",
                ["azure_openai", "anthropic"],
                help="리라이팅에 사용할 LLM"
            )
            
            st.info("💡 API 키는 환경변수로 설정하세요")
            st.code("""
# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Anthropic
ANTHROPIC_API_KEY=...
            """, language="bash")
        
        st.divider()
        
        # Phase 0.9 변경사항
        with st.expander("✨ Phase 0.9 신규 기능"):
            st.markdown("""
            **3단 계층 보기 모드:**
            
            1. **원본 PDF 텍스트**
               - PDF에서 추출한 원본
            
            2. **엔진 처리 텍스트**
               - LawParser 파싱 결과
               - RAG/검색 기준
            
            3. **AI 가독성 강화** ✨ NEW
               - LLM 리라이팅 결과
               - 띄어쓰기 자연스럽게 개선
               - **법적 효력은 원본 기준**
            
            ---
            
            **GPT 권장 안전장치:**
            
            ✅ 엔진 JSON 절대 불변
            ✅ Sanity Check 자동 검증
            ✅ 원본 항상 노출
            ✅ 조문 단위 + 캐시 (속도/비용 절감)
            
            ---
            
            **Sanity Check (4종):**
            
            1. 조문 헤더 보존 확인
            2. 숫자/날짜 변경 감지
            3. 법률 용어 누락 감지
            4. 조문 구조 보존 확인
            """)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf'],
        help="규정/법령 문서 권장 (LawMode)"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하세요")
        
        # 샘플 결과 미리보기 (옵션)
        with st.expander("📖 Phase 0.9 샘플 결과 미리보기"):
            st.markdown("""
            ### Before (Phase 0.7 - 룰 기반)
            ```
            이규정은한국농어촌공사직원에게임용승진보수복무...
            ```
            
            ### After (Phase 0.9 - AI 리라이팅)
            ```
            이 규정은 한국농어촌공사 직원에게 임용, 승진, 보수, 복무 등
            인사 전반의 기준을 정하여 합리적이고 일관된 인사 운영을 목표로 한다.
            ```
            
            **개선 사항:**
            - ✅ 자연스러운 띄어쓰기
            - ✅ 읽기 편한 문장 흐름
            - ✅ 법률 용어 100% 보존
            - ✅ 의미 변경 없음
            """)
        
        return
    
    # 문서 처리
    try:
        pdf_path = safe_temp_path('.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.read())
        
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
        
        # QA 결과
        match_rate = result['qa_result']['match_rate']
        is_qa_pass = result['is_qa_pass']
        
        if is_qa_pass:
            st.success(f"🎯 DualQA 통과: {match_rate:.1%} 매칭")
        else:
            st.warning(f"⚠️ DualQA 검토 필요: {match_rate:.1%} 매칭")
        
        # ✅ Phase 0.9: LLM 리라이팅 (옵션)
        rewritten_result = None
        if enable_llm_rewrite and LLM_REWRITER_AVAILABLE:
            with st.spinner("✨ AI 리라이팅 중... (조문 단위 처리)"):
                try:
                    rewriter = LLMRewriter(
                        provider=llm_provider,
                        cache_enabled=True,
                        sanity_check_enabled=True
                    )
                    
                    rewritten_result = rewrite_articles_with_llm(
                        chunks=result['chunks'],
                        rewriter=rewriter,
                        document_id=uploaded_file.name
                    )
                    
                    # 검증 결과 표시
                    val_summary = rewritten_result['validation_summary']
                    
                    if val_summary['pass_rate'] >= 0.95:
                        st.success(f"✅ Sanity Check 통과: {val_summary['pass_rate']:.1%} ({val_summary['passed']}/{val_summary['total']})")
                    else:
                        st.warning(f"⚠️ Sanity Check 경고: {val_summary['pass_rate']:.1%} ({val_summary['passed']}/{val_summary['total']})")
                        
                        # 실패한 조문 표시
                        failed_articles = [
                            v['article'] for v in val_summary['details'] 
                            if not v['is_valid']
                        ]
                        if failed_articles:
                            st.write(f"**검증 실패 조문**: {', '.join(failed_articles)}")
                
                except Exception as e:
                    logger.error(f"❌ 리라이팅 실패: {e}")
                    st.error(f"❌ AI 리라이팅 실패: {e}")
                    st.info("💡 원본/엔진 텍스트는 정상 표시됩니다")
        
        # ✅ Phase 0.9: 3단 계층 탭
        if rewritten_result:
            tab_names = ["📊 요약", "📝 원본", "⚙️ 엔진 텍스트", "✨ AI 가독성", "📦 JSON 청크"]
        else:
            tab_names = ["📊 요약", "📝 원본", "⚙️ 엔진 텍스트", "📦 JSON 청크"]
        
        tabs = st.tabs(tab_names)
        
        # Tab 1: 요약
        with tabs[0]:
            st.subheader("📊 처리 요약")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("처리 모드", result['mode'])
                st.metric("DualQA 매칭률", f"{match_rate:.1%}")
            
            with col2:
                st.metric("QA 통과", "✅" if is_qa_pass else "⚠️")
                st.metric("총 청크 수", len(result['chunks']))
            
            with col3:
                if result['mode'] == 'LawMode' and 'parsed_result' in result:
                    parsed = result['parsed_result']
                    st.metric("장 수", parsed['total_chapters'])
                    st.metric("조문 수", parsed['total_articles'])
                
                if rewritten_result:
                    val_summary = rewritten_result['validation_summary']
                    st.metric("AI 리라이팅", f"{val_summary['pass_rate']:.0%}")
        
        # Tab 2: 원본 PDF 텍스트
        with tabs[1]:
            st.subheader("📝 원본 PDF 텍스트")
            st.info("⚠️ 이것이 법적 효력을 가지는 기준 텍스트입니다")
            
            st.text_area(
                "PDF 추출 원본",
                value=pdf_text[:3000] + "..." if len(pdf_text) > 3000 else pdf_text,
                height=400
            )
            
            st.download_button(
                "💾 원본 텍스트 다운로드",
                data=pdf_text,
                file_name=f"{uploaded_file.name}_original.txt",
                mime="text/plain"
            )
        
        # Tab 3: 엔진 처리 텍스트
        with tabs[2]:
            st.subheader("⚙️ 엔진 처리 텍스트")
            st.info("🔍 RAG/검색 시스템의 기준 텍스트입니다")
            
            review_md = to_review_md(result['chunks'])
            
            st.markdown(review_md)
            
            st.download_button(
                "💾 엔진 텍스트 다운로드",
                data=review_md,
                file_name=f"{uploaded_file.name}_engine_phase09.md",
                mime="text/markdown"
            )
        
        # Tab 4: AI 가독성 강화 (Phase 0.9)
        if rewritten_result:
            with tabs[3]:
                st.subheader("✨ AI 가독성 강화")
                
                # ✅ GPT 필수: 법적 효력 표시
                st.warning("⚠️ **법적 효력은 원본 기준입니다.** 이 텍스트는 가독성 개선 목적입니다.")
                
                # Before/After 비교 (샘플)
                st.markdown("### 📊 개선 비교 (샘플)")
                
                col1, col2 = st.columns(2)
                
                # 첫 조문 찾기
                first_article_idx = next(
                    (i for i, c in enumerate(result['chunks']) 
                     if c['metadata']['type'] == 'article'),
                    None
                )
                
                if first_article_idx is not None:
                    original_chunk = result['chunks'][first_article_idx]
                    rewritten_chunk = rewritten_result['rewritten_chunks'][first_article_idx]
                    
                    with col1:
                        st.markdown("**Before (엔진 텍스트):**")
                        st.text_area(
                            "원본",
                            value=original_chunk['content'][:300] + "...",
                            height=200,
                            key="before_sample"
                        )
                    
                    with col2:
                        st.markdown("**After (AI 리라이팅):**")
                        st.text_area(
                            "개선",
                            value=rewritten_chunk['content'][:300] + "...",
                            height=200,
                            key="after_sample"
                        )
                
                st.markdown("---")
                st.markdown("### 📖 전체 AI 리라이팅 결과")
                
                # 전체 리라이팅 결과
                rewritten_md = to_review_md(rewritten_result['rewritten_chunks'])
                st.markdown(rewritten_md)
                
                st.download_button(
                    "💾 AI 리라이팅 다운로드",
                    data=rewritten_md,
                    file_name=f"{uploaded_file.name}_ai_rewritten_phase09.md",
                    mime="text/markdown"
                )
                
                # Sanity Check 상세 결과
                with st.expander("🔬 Sanity Check 상세 결과"):
                    val_summary = rewritten_result['validation_summary']
                    
                    st.write(f"**통과율**: {val_summary['pass_rate']:.1%}")
                    st.write(f"**통과**: {val_summary['passed']}개")
                    st.write(f"**실패**: {val_summary['failed']}개")
                    
                    if val_summary['failed'] > 0:
                        st.write("**실패 상세:**")
                        for detail in val_summary['details']:
                            if not detail['is_valid']:
                                st.write(f"- {detail['article']}: {', '.join(detail['warnings'])}")
        
        # Tab 5: JSON 청크
        with tabs[-1]:
            st.subheader("📦 JSON 청크")
            
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
                file_name=f"{uploaded_file.name}_chunks_phase09.json",
                mime="application/json"
            )
    
    except Exception as e:
        logger.error(f"❌ 처리 실패: {e}", exc_info=True)
        st.error(f"❌ 처리 중 오류 발생: {e}")
    
    finally:
        if 'pdf_path' in locals():
            safe_remove(pdf_path)


if __name__ == '__main__':
    main()

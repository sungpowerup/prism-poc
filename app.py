"""
app.py
PRISM Phase 5.7.2.2 Hotfix - Streamlit Demo (Module Load Diagnostic)

✅ Phase 5.7.2.3-diag 긴급 진단:
1. 모듈 로드 경로 확인
2. 실행 중인 파일 버전 확인
3. 진단 로그 출력

Author: 최동현 (Frontend Lead) + 마창수산 팀 + GPT(미송) 의견 반영
Date: 2025-11-02
Version: 5.7.2.3-diag
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import time
import tempfile
from dotenv import load_dotenv
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

# 🔴 진단 로그 1: 모듈 로드 경로 확인
logger.warning("=" * 80)
logger.warning("[MODULE-DIAG] 모듈 로드 경로 확인 시작")
logger.warning("=" * 80)

# Phase 5.7.0 컴포넌트
try:
    from core.tree_builder import TreeBuilder
    from core.hierarchical_parser import HierarchicalParser
    from core.llm_adapter import LLMAdapter
    
    # 🔴 진단 로그: TreeBuilder 경로
    import core.tree_builder as tb_module
    logger.warning(f"[MODULE-DIAG] TreeBuilder 로드: {tb_module.__file__}")
    
    PHASE_570_AVAILABLE = True
except ImportError as e:
    PHASE_570_AVAILABLE = False
    TREE_IMPORT_ERROR = str(e)
    logger.error(f"[MODULE-DIAG] TreeBuilder 로드 실패: {e}")

# Phase 5.6.x Pipeline (Markdown 추출용)
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline
    
    # 🔴 진단 로그: 핵심 모듈 경로 확인
    import core.kvs_normalizer as kvs_module
    import core.hybrid_extractor as he_module
    import core.pipeline as pl_module
    
    logger.warning(f"[MODULE-DIAG] kvs_normalizer 로드: {kvs_module.__file__}")
    logger.warning(f"[MODULE-DIAG] hybrid_extractor 로드: {he_module.__file__}")
    logger.warning(f"[MODULE-DIAG] pipeline 로드: {pl_module.__file__}")
    
    # 🔴 진단 로그: 버전 확인
    try:
        # kvs_normalizer 버전
        with open(kvs_module.__file__, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Version:' in line:
                    logger.warning(f"[MODULE-DIAG] kvs_normalizer 버전: {line.strip()}")
                    break
        
        # hybrid_extractor 버전
        with open(he_module.__file__, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Version:' in line:
                    logger.warning(f"[MODULE-DIAG] hybrid_extractor 버전: {line.strip()}")
                    break
        
        # pipeline 버전
        with open(pl_module.__file__, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Version:' in line:
                    logger.warning(f"[MODULE-DIAG] pipeline 버전: {line.strip()}")
                    break
    except Exception as e:
        logger.error(f"[MODULE-DIAG] 버전 확인 실패: {e}")
    
    PHASE_53_AVAILABLE = True
except ImportError as e:
    PHASE_53_AVAILABLE = False
    PIPELINE_IMPORT_ERROR = str(e)
    logger.error(f"[MODULE-DIAG] Pipeline 로드 실패: {e}")

logger.warning("=" * 80)
logger.warning("[MODULE-DIAG] 모듈 로드 경로 확인 완료")
logger.warning("=" * 80)


def main():
    """메인 함수"""
    st.set_page_config(
        page_title="PRISM POC Demo",
        page_icon="🌲",
        layout="wide"
    )
    
    # 🔴 진단 정보 표시
    with st.sidebar:
        st.markdown("### 🔍 모듈 진단 정보")
        st.caption("콘솔 로그에서 [MODULE-DIAG] 확인")
        
        if PHASE_53_AVAILABLE:
            st.success("✅ Pipeline 로드 성공")
        else:
            st.error(f"❌ Pipeline 로드 실패: {PIPELINE_IMPORT_ERROR}")
        
        if PHASE_570_AVAILABLE:
            st.success("✅ TreeBuilder 로드 성공")
        else:
            st.error(f"❌ TreeBuilder 로드 실패: {TREE_IMPORT_ERROR}")
    
    st.title("🌲 PRISM Phase 5.7.2.3-diag")
    st.markdown("**진단 로그 포함 버전** - 콘솔에서 `[MODULE-DIAG]` 및 `[DOD-DIAG]` 로그 확인")
    
    # 버전 정보
    with st.expander("📦 버전 정보", expanded=False):
        st.markdown("""
        **Phase 5.7.2.3-diag (진단 로그 포함)**
        - 🔴 모듈 로드 경로 진단
        - 🔴 실행 중인 파일 버전 확인
        - 🔴 처리 단계별 진단 로그
        
        **주요 개선사항**:
        - KVSNormalizer v5.7.2.3 (List[Dict] 지원)
        - HybridExtractor v5.7.2.2 (페이지 구분자 제거)
        - Pipeline v5.7.2.2 (빈 페이지 분모 제외)
        """)
    
    # 캐시 정리 가이드
    with st.expander("🧹 캐시 정리 가이드", expanded=False):
        st.markdown("""
        **문제 발생 시 캐시 정리:**
        
        ```powershell
        # PowerShell에서 실행
        cd C:\\Users\\misso\\desktop\\prism-poc
        Get-ChildItem -Path . -Filter __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
        Get-ChildItem -Path . -Filter *.pyc -Recurse -Force | Remove-Item -Force
        Remove-Item -Recurse -Force $env:USERPROFILE\\.streamlit -ErrorAction SilentlyContinue
        ```
        """)
    
    # Phase 확인
    if not PHASE_53_AVAILABLE or not PHASE_570_AVAILABLE:
        st.error("❌ 필수 컴포넌트 로드 실패. 콘솔 로그를 확인하세요.")
        if not PHASE_53_AVAILABLE:
            st.code(PIPELINE_IMPORT_ERROR)
        if not PHASE_570_AVAILABLE:
            st.code(TREE_IMPORT_ERROR)
        return
    
    # PDF 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일 업로드",
        type=['pdf'],
        help="처리할 PDF 파일을 업로드하세요"
    )
    
    if not uploaded_file:
        st.info("👆 PDF 파일을 업로드하면 처리가 시작됩니다.")
        return
    
    # 처리 시작
    with st.spinner("처리 중..."):
        try:
            # 임시 파일 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name
            
            # VLM 서비스 초기화
            logger.info("🔧 VLM 서비스 초기화")
            vlm_service = VLMServiceV50(provider="azure_openai")
            
            # PDF 프로세서 초기화
            logger.info("📄 PDF 프로세서 초기화")
            pdf_processor = PDFProcessor()
            
            # Pipeline 초기화
            logger.info("🔧 Pipeline 초기화")
            pipeline = Phase53Pipeline(pdf_processor, vlm_service)
            
            # 진행 상황 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(msg, progress):
                status_text.text(msg)
                progress_bar.progress(progress)
            
            # PDF 처리
            logger.info(f"📄 PDF 처리 시작: {uploaded_file.name}")
            result = pipeline.process_pdf(
                pdf_path=tmp_path,
                max_pages=20,
                progress_callback=update_progress
            )
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
            
            if result['status'] != 'success':
                st.error(f"❌ 처리 실패: {result.get('error', 'Unknown error')}")
                return
            
            # 결과 표시
            st.success(f"✅ 처리 완료! ({result['processing_time']:.1f}초)")
            
            # 통계 정보
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("전체 페이지", result['pages_total'])
            with col2:
                st.metric("유효 페이지", result['pages_success'])
            with col3:
                st.metric("빈 페이지", result['empty_page_count'])
            with col4:
                st.metric("청크 수", len(result['chunks']))
            
            # Markdown 표시
            with st.expander("📝 추출된 Markdown", expanded=False):
                st.text_area(
                    "Markdown",
                    result['markdown'],
                    height=400
                )
                st.download_button(
                    "💾 Markdown 다운로드",
                    result['markdown'],
                    file_name=f"{uploaded_file.name}_markdown.md",
                    mime="text/markdown"
                )
            
            # TreeBuilder 처리
            st.markdown("---")
            st.subheader("🌲 Tree 생성")
            
            with st.spinner("Tree 생성 중..."):
                tree_builder = TreeBuilder()
                tree = tree_builder.build(
                    result['markdown'],
                    document_title=uploaded_file.name
                )
            
            # DoD 평가
            st.markdown("---")
            st.subheader("📊 DoD (Definition of Done) 평가")
            
            parser = HierarchicalParser()
            dod_result = parser.evaluate(tree)
            
            # 🔴 진단 로그: DoD 결과
            logger.warning("=" * 80)
            logger.warning("[DOD-RESULT] DoD 평가 결과")
            logger.warning(f"  - hierarchy_preservation_rate: {dod_result.get('hierarchy_preservation_rate', 0):.2%}")
            logger.warning(f"  - boundary_cross_bleed_rate: {dod_result.get('boundary_cross_bleed_rate', 0):.2%}")
            logger.warning(f"  - empty_article_rate: {dod_result.get('empty_article_rate', 0):.2%}")
            logger.warning(f"  - passed: {dod_result.get('passed', False)}")
            logger.warning("=" * 80)
            
            if dod_result.get('passed', False):
                st.success("✅ DoD 검증 통과")
            else:
                st.error("❌ DoD 검증 실패")
                st.caption("콘솔 로그에서 [DOD-DIAG] 확인")
            
            # DoD 지표
            col1, col2, col3 = st.columns(3)
            with col1:
                rate = dod_result.get('hierarchy_preservation_rate', 0)
                st.metric(
                    "계층 보존율",
                    f"{rate:.1%}",
                    delta=f"{(rate - 0.95):.1%}" if rate < 0.95 else "OK"
                )
            with col2:
                rate = dod_result.get('boundary_cross_bleed_rate', 0)
                st.metric(
                    "경계 누수율",
                    f"{rate:.1%}",
                    delta=f"{(0.05 - rate):.1%}" if rate > 0.05 else "OK"
                )
            with col3:
                rate = dod_result.get('empty_article_rate', 0)
                st.metric(
                    "빈 조문율",
                    f"{rate:.1%}",
                    delta=f"{(0.05 - rate):.1%}" if rate > 0.05 else "OK"
                )
            
            # Tree 시각화
            with st.expander("🌲 Tree 구조", expanded=False):
                st.json(tree)
            
            # JSON 다운로드
            st.download_button(
                "💾 Tree JSON 다운로드",
                json.dumps(tree, ensure_ascii=False, indent=2),
                file_name=f"{uploaded_file.name}_tree.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"❌ 처리 중 오류 발생: {e}")
            logger.error(f"처리 오류: {e}", exc_info=True)


if __name__ == "__main__":
    main()
"""
app.py
PRISM Phase 0.3.3 - Enhanced Application

✅ Phase 0.3.3 지원:
1. 버전 체크 로직 업데이트 (0.3.3 지원)
2. Safe 모듈 자동 로드
3. Fallback 로직 강화

Author: 최동현 (Frontend Lead)
Date: 2025-11-08
Version: Phase 0.3.3
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import os
import time
import importlib
import json

# ✅ 로거 초기화 (최상단)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prism.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ⚠️ 캐시 무효화
importlib.invalidate_caches()

# ✅ core 모듈 import
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline
    
    logger.info("✅ 기본 core 모듈 import 성공")
    
    # ✅ Safe 모듈 체크
    try:
        from core.typo_normalizer_safe import TypoNormalizer
        from core.post_merge_normalizer_safe import PostMergeNormalizer
        from core.semantic_chunker import SemanticChunker
        
        tn_version = getattr(TypoNormalizer, 'VERSION', 'UNKNOWN')
        
        # ✅ Safe/OCR 패턴 개수 확인
        safe_patterns = getattr(TypoNormalizer, 'SAFE_PATTERNS', {})
        ocr_patterns = getattr(TypoNormalizer, 'OCR_PATTERNS', {})
        tn_dict_size = len(safe_patterns) + len(ocr_patterns)
        tn_block_size = len(getattr(TypoNormalizer, 'BLOCKED_REPLACEMENTS', set()))
        
        pm_version = getattr(PostMergeNormalizer, 'VERSION', 'UNKNOWN')
        sc_version = getattr(SemanticChunker, 'VERSION', 'UNKNOWN')
        
        logger.info(f"🔎 TypoNormalizer: {tn_version}")
        logger.info(f"   📖 Safe: {len(safe_patterns)}개")
        logger.info(f"   📖 OCR: {len(ocr_patterns)}개")
        logger.info(f"   📖 합계: {tn_dict_size}개")
        logger.info(f"   🚫 금지: {tn_block_size}개")
        logger.info(f"🔎 PostMergeNormalizer: {pm_version}")
        logger.info(f"🔎 SemanticChunker: {sc_version}")
        
        # ✅ 버전 판정 (0.3.3 우선)
        if "0.3.3" in tn_version:
            logger.info("✅ Phase 0.3.3 확인됨!")
            phase_version = "Phase 0.3.3"
            safe_mode_enabled = True
        elif "0.3.2" in tn_version:
            logger.info("✅ Phase 0.3.2 확인됨")
            phase_version = "Phase 0.3.2"
            safe_mode_enabled = True
        elif "0.3.1" in tn_version:
            logger.info("✅ Phase 0.3.1 확인됨")
            phase_version = "Phase 0.3.1"
            safe_mode_enabled = True
        else:
            logger.warning(f"⚠️ Phase 미확인: version={tn_version}")
            phase_version = "Unknown"
            safe_mode_enabled = False
            
    except ImportError as ie:
        logger.error(f"❌ Safe Normalizers import 실패: {ie}")
        st.error(f"❌ Safe 모듈을 찾을 수 없습니다: {ie}")
        st.error("core/ 폴더에 typo_normalizer_safe.py와 post_merge_normalizer_safe.py가 있는지 확인해주세요.")
        st.stop()
        
except ImportError as e:
    logger.error(f"❌ core 모듈 import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.error("core 폴더의 모든 파일이 올바른 위치에 있는지 확인해주세요.")
    st.stop()


def main():
    # ✅ 제목 (버전별 표시)
    if phase_version == "Phase 0.3.3":
        st.title("🎯 PRISM Phase 0.3.3 - 문서 처리 시스템 ✨")
        st.success("✅ Phase 0.3.3 활성화 (레이어 분리 정규화, 골든 diff 기반)")
        
        with st.expander("✨ Phase 0.3.3 개선사항", expanded=False):
            st.markdown("""
            **🎯 Phase 0.3.3 주요 개선:**
            1. ✅ **레이어 분리 설계**: Safe/OCR/Domain 3단계 분리
            2. ✅ **골든 diff 기반**: 실제 오류만 교정 (29개)
            3. ✅ **의미 변경 제거**: 원본 충실도 최우선
            4. ✅ **리포트-코드 동기화**: 문서와 코드 100% 일치
            
            **🔧 기술 스펙:**
            - Safe Layer: 7개 (공백/전각반각 정규화)
            - OCR Layer: 29개 (골든 diff 추출)
            - Blocked: 3개 (의미 변경 방지)
            - 조문 헤더: 자동 정규화
            """)
    else:
        st.title("🎯 PRISM - 문서 처리 시스템")
        st.warning(f"⚠️ 버전: {phase_version}")
    
    # 버전 정보 표시
    with st.expander("ℹ️ 버전 정보", expanded=False):
        st.write(f"**현재 버전**: {phase_version}")
        st.write(f"**Safe Mode**: {'✅ 활성화' if safe_mode_enabled else '❌ 비활성화'}")
        st.write(f"**TypoNormalizer**: {tn_version}")
        st.write(f"**PostMergeNormalizer**: {pm_version}")
        st.write(f"**SemanticChunker**: {sc_version}")
        st.write(f"**사전 크기**: {tn_dict_size}개")
        st.write(f"**금지 치환**: {tn_block_size}개")
    
    # 초기화
    try:
        pdf_processor = PDFProcessor()
        vlm_service = VLMServiceV50(provider="azure_openai")
        logger.info("✅ 서비스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 서비스 초기화 실패: {e}", exc_info=True)
        st.error(f"❌ 초기화 실패: {str(e)}")
        return
    
    # 파일 업로드
    uploaded_file = st.file_uploader("📄 PDF 파일 업로드", type=['pdf'])
    
    if uploaded_file is not None:
        # session_state를 사용하여 처리 결과 캐싱
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if 'last_processed_file' not in st.session_state or st.session_state['last_processed_file'] != file_key:
            # 새 파일이거나 아직 처리 안 했으면 처리
            status_text = f"🔄 PDF 처리 중... ({phase_version})"
            
            with st.spinner(status_text):
                temp_path = None
                
                try:
                    # 임시 파일 저장
                    temp_filename = f"temp_{int(time.time())}_{uploaded_file.name}"
                    temp_path = Path(temp_filename)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    logger.info(f"✅ 임시 파일 저장: {temp_path}")
                    
                    # Pipeline 초기화 및 처리
                    pipeline = Phase53Pipeline(pdf_processor, vlm_service)
                    result = pipeline.process_pdf(str(temp_path))
                    
                    # 결과를 session_state에 저장
                    st.session_state['last_processed_file'] = file_key
                    st.session_state['result'] = result
                    
                    logger.info("✅ 처리 결과 저장 완료")
                    
                except Exception as e:
                    logger.error(f"❌ 처리 중 오류: {e}", exc_info=True)
                    st.error(f"❌ 오류 발생: {str(e)}")
                    return
                    
                finally:
                    # 임시 파일 삭제
                    if temp_path and temp_path.exists():
                        try:
                            temp_path.unlink()
                            logger.info(f"✅ 임시 파일 삭제: {temp_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ 임시 파일 삭제 실패: {e}")
        
        # session_state에서 결과 가져오기
        result = st.session_state.get('result')
        
        if result and result.get('success'):
            st.success("✅ 처리 완료!")
            
            # 처리 시간 표시
            elapsed = result.get('elapsed_time', 0)
            st.info(f"⏱️ 처리 시간: {elapsed:.1f}초")
            
            # 체크리스트 표시
            st.subheader("📊 품질 체크리스트")
            checklist = result.get('checklist', {})
            
            if checklist:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    fidelity = checklist.get('fidelity', 0)
                    st.metric("📄 원본 충실도", f"{fidelity}/100")
                    
                    chunking = checklist.get('chunking', 0)
                    st.metric("✂️ 청킹 품질", f"{chunking}/100")
                
                with col2:
                    rag = checklist.get('rag_readiness', 0)
                    st.metric("🎯 RAG 적합도", f"{rag}/100")
                    
                    generality = checklist.get('generality', 0)
                    st.metric("🔄 범용성", f"{generality}/100")
                
                with col3:
                    competitive = checklist.get('competitive_edge', 0)
                    st.metric("🏆 경쟁력", f"{competitive}/100")
                    
                    overall = checklist.get('overall', 0)
                    st.metric("🎯 종합", f"{overall}/100")
                
                # Markdown 미리보기
                st.subheader("📝 Markdown 미리보기")
                markdown = result.get('markdown', '')
                
                if markdown:
                    preview = markdown[:1000]
                    if len(markdown) > 1000:
                        preview += "\n\n... (생략) ..."
                    
                    st.text_area("", preview, height=300, disabled=True)
                    
                    with st.expander("📄 전체 Markdown 보기"):
                        st.markdown(markdown)
                
                # 청크 미리보기
                st.subheader("✂️ 청크 미리보기")
                chunks = result.get('chunks', [])
                
                if chunks:
                    for i, chunk in enumerate(chunks[:3], 1):
                        with st.expander(f"청크 {i}: {chunk.get('id', '')}"):
                            st.write("**메타데이터:**")
                            st.json(chunk.get('metadata', {}))
                            st.write("**내용:**")
                            st.text(chunk.get('content', ''))
                    
                    if len(chunks) > 3:
                        st.info(f"📋 총 {len(chunks)}개 청크")
                
                # 다운로드 버튼
                st.subheader("📥 다운로드")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if markdown:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"{uploaded_file.name.replace('.pdf', '')}_{timestamp}_markdown.md"
                        
                        st.download_button(
                            label="📝 Markdown 다운로드",
                            data=markdown,
                            file_name=filename,
                            mime="text/markdown"
                        )
                
                with col2:
                    if chunks:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"{uploaded_file.name.replace('.pdf', '')}_{timestamp}_chunks.json"
                        
                        chunks_json = json.dumps(chunks, ensure_ascii=False, indent=2)
                        
                        st.download_button(
                            label="📦 JSON 다운로드",
                            data=chunks_json,
                            file_name=filename,
                            mime="application/json"
                        )
        
        elif result:
            st.error(f"❌ 처리 실패: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
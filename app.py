"""
app.py
PRISM Phase 0.3.1 - Safe Mode Application

⚠️ Phase 0.3.1 수정:
1. 기존 pipeline.py 사용 (Safe 모듈 자동 로드)
2. 버전 확인 코드 추가
3. 원본 충실도 우선

Author: 마창수산 팀
Date: 2025-11-07
Version: Phase 0.3.1 (Safe Mode)
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

# ⚠️ Phase 0.3.1: 캐시 무효화
importlib.invalidate_caches()

# ✅ core 모듈 import
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline  # ⚠️ 기존 pipeline 사용
    
    logger.info("✅ 모든 core 모듈 import 성공")
    
    # ⚠️ Phase 0.3.1: 버전 확인 (Safe 모듈 체크)
    try:
        from core.typo_normalizer_safe import TypoNormalizer
        from core.post_merge_normalizer_safe import PostMergeNormalizer
        
        tn_version = getattr(TypoNormalizer, 'VERSION', 'UNKNOWN')
        tn_dict_size = len(getattr(TypoNormalizer, 'STATUTE_TERMS', {}))
        tn_block_size = len(getattr(TypoNormalizer, 'BLOCKED_REPLACEMENTS', set()))
        
        logger.info(f"🔎 TypoNormalizer: {tn_version}")
        logger.info(f"   📖 사전: {tn_dict_size}개")
        logger.info(f"   🚫 금지: {tn_block_size}개")
        
        pm_version = getattr(PostMergeNormalizer, 'VERSION', 'UNKNOWN')
        logger.info(f"🔎 PostMergeNormalizer: {pm_version}")
        
        # 버전 확인
        if 'Safe Mode' in tn_version and tn_dict_size >= 20 and tn_block_size >= 10:
            logger.info("✅ Phase 0.3.1 Hotfix 확인됨!")
            safe_mode_enabled = True
        else:
            logger.warning(f"⚠️ Phase 0.3.1 Hotfix 미확인: version={tn_version}, dict={tn_dict_size}, block={tn_block_size}")
            safe_mode_enabled = False
    except ImportError:
        logger.warning("⚠️ Safe Normalizers 없음 - 기본 버전 사용")
        tn_version = "Phase 0.3 (기본)"
        pm_version = "Phase 0.3 (기본)"
        tn_dict_size = 15
        tn_block_size = 0
        safe_mode_enabled = False
        
except ImportError as e:
    logger.error(f"❌ core 모듈 import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()


def main():
    # 제목 (Safe Mode 여부 표시)
    if safe_mode_enabled:
        st.title("🎯 PRISM Phase 0.3.1 - 문서 처리 시스템 (Safe Mode) ✅")
    else:
        st.title("🎯 PRISM Phase 0.3 - 문서 처리 시스템 ⚠️")
        st.warning("⚠️ Safe Mode가 활성화되지 않았습니다. Safe 모듈을 확인하세요.")
    
    # 버전 정보 표시
    with st.expander("ℹ️ 버전 정보", expanded=False):
        st.write(f"**Safe Mode**: {'✅ 활성화' if safe_mode_enabled else '❌ 비활성화'}")
        st.write(f"**TypoNormalizer**: {tn_version}")
        st.write(f"**PostMergeNormalizer**: {pm_version}")
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
            status_text = "🔄 PDF 처리 중... (Phase 0.3.1 Safe Mode)" if safe_mode_enabled else "🔄 PDF 처리 중..."
            
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
                    st.session_state['processing_error'] = None
                    
                    logger.info("✅ 처리 완료 및 결과 저장")
                    
                except Exception as e:
                    logger.error(f"❌ 처리 오류: {str(e)}", exc_info=True)
                    st.session_state['processing_error'] = str(e)
                    st.error(f"❌ 처리 실패: {str(e)}")
                    
                finally:
                    # 임시 파일 안전 삭제
                    if temp_path and temp_path.exists():
                        try:
                            time.sleep(0.1)
                            temp_path.unlink()
                            logger.info(f"✅ 임시 파일 삭제: {temp_path}")
                        except PermissionError:
                            logger.warning(f"⚠️ 임시 파일 삭제 실패 (파일 잠금): {temp_path}")
                            logger.warning(f"   → 시스템이 나중에 자동 정리할 예정")
                        except Exception as e:
                            logger.error(f"❌ 임시 파일 삭제 오류: {e}")
        
        # 결과 표시
        if 'result' in st.session_state and st.session_state['result']:
            result = st.session_state['result']
            
            if result.get('success'):
                st.success("✅ 처리 완료!")
                
                # 통계 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📄 페이지 수", result.get('pages_count', 0))
                with col2:
                    st.metric("✂️ 청크 수", len(result.get('chunks', [])))
                with col3:
                    st.metric("⏱️ 처리 시간", f"{result.get('elapsed_time', 0):.1f}초")
                
                # 체크리스트 표시
                st.subheader("📊 품질 체크리스트")
                
                checklist = result.get('checklist', {})
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    fidelity = checklist.get('fidelity', 0)
                    st.metric("원본 충실도", f"{fidelity}/100", 
                             delta="목표: 95점" if fidelity >= 95 else "개선 필요",
                             delta_color="normal" if fidelity >= 95 else "inverse")
                with col2:
                    chunking = checklist.get('chunking', 0)
                    st.metric("청킹 품질", f"{chunking}/100")
                with col3:
                    rag = checklist.get('rag_readiness', 0)
                    st.metric("RAG 적합도", f"{rag}/100")
                
                col4, col5, col6 = st.columns(3)
                with col4:
                    generality = checklist.get('generality', 0)
                    st.metric("범용성", f"{generality}/100")
                with col5:
                    competitive = checklist.get('competitive_edge', 0)
                    st.metric("경쟁력", f"{competitive}/100")
                with col6:
                    overall = checklist.get('overall', 0)
                    st.metric("🎯 종합", f"{overall}/100",
                             delta="목표: 95점" if overall >= 95 else "개선 필요",
                             delta_color="normal" if overall >= 95 else "inverse")
                
                # Markdown 미리보기
                st.subheader("📝 Markdown 미리보기")
                markdown = result.get('markdown', '')
                
                if markdown:
                    # 처음 1000자만 표시
                    preview = markdown[:1000]
                    if len(markdown) > 1000:
                        preview += "\n\n... (생략) ..."
                    
                    st.text_area("", preview, height=300, disabled=True)
                    
                    # 전체 보기
                    with st.expander("📄 전체 Markdown 보기"):
                        st.markdown(markdown)
                
                # 청크 미리보기
                st.subheader("✂️ 청크 미리보기")
                chunks = result.get('chunks', [])
                
                if chunks:
                    # 처음 3개 청크만 표시
                    for i, chunk in enumerate(chunks[:3], 1):
                        with st.expander(f"청크 {i}: {chunk.get('id', '')}"):
                            st.write("**메타데이터:**")
                            st.json(chunk.get('metadata', {}))
                            st.write("**내용:**")
                            st.text(chunk.get('content', ''))
                    
                    if len(chunks) > 3:
                        st.info(f"📋 총 {len(chunks)}개 청크 (전체는 JSON 다운로드에서 확인)")
                
                # 다운로드 버튼
                st.subheader("📥 다운로드")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if markdown:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        md_filename = f"{uploaded_file.name.replace('.pdf', '')}_{timestamp}_markdown.md"
                        
                        st.download_button(
                            label="📥 Markdown 다운로드",
                            data=markdown,
                            file_name=md_filename,
                            mime="text/markdown",
                            key="download_markdown"
                        )
                
                with col2:
                    if chunks:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        json_filename = f"{uploaded_file.name.replace('.pdf', '')}_{timestamp}_chunks.json"
                        
                        chunks_json = json.dumps(chunks, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="📥 청크 JSON 다운로드",
                            data=chunks_json,
                            file_name=json_filename,
                            mime="application/json",
                            key="download_chunks"
                        )
            else:
                st.error(f"❌ 처리 실패: {result.get('error', '알 수 없는 오류')}")
        
        elif 'processing_error' in st.session_state and st.session_state['processing_error']:
            st.error(f"❌ 처리 실패: {st.session_state['processing_error']}")


if __name__ == "__main__":
    main()
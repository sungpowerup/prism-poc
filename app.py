"""
app.py
PRISM Phase 5.7.6.1 긴급 패치

✅ 수정 사항:
1. 임시 파일 삭제 에러 처리 개선
2. finally 블록 추가
3. 파일 핸들 안전 종료

Author: 마창수산 팀
Date: 2025-11-02
Version: 5.7.6.1 Hotfix
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import os
import time

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

# ✅ core 모듈 import (Phase 5.7.6)
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.pipeline import Phase53Pipeline
    logger.info("✅ 모든 core 모듈 import 성공")
except ImportError as e:
    logger.error(f"❌ core 모듈 import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()


def main():
    st.title("🎯 PRISM Phase 5.7.6.1 - 문서 처리 시스템 (긴급 패치)")
    
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
        # ✅ session_state를 사용하여 처리 결과 캐싱
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if 'last_processed_file' not in st.session_state or st.session_state['last_processed_file'] != file_key:
            # 새 파일이거나 아직 처리 안 했으면 처리
            with st.spinner('🔄 PDF 처리 중...'):
                temp_path = None
                
                try:
                    # ✅ Phase 5.7.6.1: 임시 파일 저장 (타임스탬프 추가)
                    temp_filename = f"temp_{int(time.time())}_{uploaded_file.name}"
                    temp_path = Path(temp_filename)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    logger.info(f"✅ 임시 파일 저장: {temp_path}")
                    
                    # Pipeline 초기화 및 처리
                    pipeline = Phase53Pipeline(pdf_processor, vlm_service)
                    result = pipeline.process_pdf(str(temp_path))
                    
                    # ✅ 결과를 session_state에 저장
                    st.session_state['last_processed_file'] = file_key
                    st.session_state['result'] = result
                    st.session_state['processing_error'] = None
                    
                    logger.info("✅ 처리 완료 및 결과 저장")
                    
                except Exception as e:
                    logger.error(f"❌ 처리 오류: {str(e)}", exc_info=True)
                    st.session_state['processing_error'] = str(e)
                    st.error(f"❌ 처리 중 오류 발생: {str(e)}")
                    return
                
                finally:
                    # ✅ Phase 5.7.6.1: 임시 파일 안전 삭제
                    if temp_path and temp_path.exists():
                        try:
                            # 잠시 대기 (파일 핸들 해제 대기)
                            time.sleep(0.5)
                            
                            # 삭제 시도
                            temp_path.unlink()
                            logger.info(f"✅ 임시 파일 삭제: {temp_path}")
                        
                        except PermissionError as pe:
                            # Windows 파일 잠금 오류 - 무시
                            logger.warning(f"⚠️ 임시 파일 삭제 실패 (파일 잠금): {temp_path}")
                            logger.warning("   → 시스템이 나중에 자동 정리할 예정")
                        
                        except Exception as cleanup_e:
                            logger.error(f"❌ 임시 파일 삭제 오류: {cleanup_e}")
        
        # ✅ 캐시된 결과 사용
        if 'processing_error' in st.session_state and st.session_state['processing_error']:
            st.error(f"❌ 이전 처리 오류: {st.session_state['processing_error']}")
            return
        
        if 'result' not in st.session_state:
            st.warning("⚠️ 처리 결과가 없습니다.")
            return
        
        result = st.session_state['result']
        
        # ✅ 처리 완료 표시
        st.success('✅ 처리 완료!')
        
        # ===== 결과 표시 =====
        
        # 1. 통계
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            valid_pages = result.get('pages_success', 0)
            total_pages = result.get('pages_total', 0)
            st.metric("📄 페이지", f"{valid_pages}/{total_pages}")
        
        with col2:
            markdown_len = len(result.get('markdown', ''))
            st.metric("📝 추출 글자", f"{markdown_len:,}자")
        
        with col3:
            chunk_count = len(result.get('chunks', []))
            st.metric("✂️ 청크", f"{chunk_count}개")
        
        with col4:
            overall_score = result.get('overall_score', 0)
            st.metric("🎯 종합 점수", f"{overall_score:.0f}/100")
        
        # 2. Fallback 통계
        fallback_stats = result.get('fallback_stats', {})
        fallback_count = fallback_stats.get('fallback_count', 0)
        
        if fallback_count > 0:
            fallback_rate = fallback_stats.get('fallback_rate', 0)
            st.info(f"🔄 Fallback 사용: {fallback_count}페이지 ({fallback_rate:.1%})")
        
        # 3. 품질 평가
        with st.expander("📊 품질 평가 상세", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("원본 충실도", f"{result.get('fidelity_score', 0):.0f}/100")
                st.metric("청킹 품질", f"{result.get('chunking_score', 0):.0f}/100")
                st.metric("RAG 적합도", f"{result.get('rag_score', 0):.0f}/100")
            
            with col2:
                st.metric("범용성", f"{result.get('universality_score', 0):.0f}/100")
                st.metric("경쟁력", f"{result.get('competitive_score', 0):.0f}/100")
                st.metric("처리 시간", f"{result.get('processing_time', 0):.1f}초")
        
        # 4. 청크 표시
        st.subheader("✂️ 생성된 청크")
        
        chunks = result.get('chunks', [])
        
        if chunks:
            for i, chunk in enumerate(chunks):
                # metadata 안전하게 접근
                metadata = chunk.get('metadata', {})
                char_count = metadata.get('char_count', len(chunk.get('content', '')))
                article_no = metadata.get('article_no', '?')
                article_title = metadata.get('article_title', '')
                
                # 청크 제목 생성
                if article_title:
                    chunk_title = f"청크 {i+1}: {article_no} ({article_title}) - {char_count}자"
                else:
                    chunk_title = f"청크 {i+1}: {article_no} - {char_count}자"
                
                with st.expander(chunk_title):
                    st.text(chunk.get('content', ''))
                    
                    # metadata 표시
                    if metadata:
                        st.caption(f"📋 메타데이터: {metadata}")
        else:
            st.warning("⚠️ 청크가 생성되지 않았습니다.")
        
        # ===== 다운로드 버튼 =====
        st.subheader("📥 다운로드")
        
        col1, col2 = st.columns(2)
        
        with col1:
            markdown = result.get('markdown', '')
            if markdown:
                st.download_button(
                    label="📥 Markdown 다운로드",
                    data=markdown,
                    file_name=f"{uploaded_file.name}_markdown.md",
                    mime="text/markdown",
                    key="download_markdown"
                )
        
        with col2:
            if chunks:
                import json
                chunks_json = json.dumps(chunks, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 청크 JSON 다운로드",
                    data=chunks_json,
                    file_name=f"{uploaded_file.name}_chunks.json",
                    mime="application/json",
                    key="download_chunks"
                )


if __name__ == "__main__":
    main()
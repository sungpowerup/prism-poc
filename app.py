# app.py Phase 5.7.4.3 완전 패치
# 
# 수정 사항:
# 1. 청크 char_count metadata 접근 수정
# 2. 다운로드 버튼 클릭 시 재처리 방지 (session_state 사용)

import streamlit as st

# ... (기존 코드) ...

def main():
    st.title("🎯 PRISM Phase 5.7.4 - 문서 처리 시스템")
    
    # 파일 업로드
    uploaded_file = st.file_uploader("📄 PDF 파일 업로드", type=['pdf'])
    
    if uploaded_file is not None:
        # ✅ 수정 1: session_state를 사용하여 처리 결과 캐싱
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if 'last_processed_file' not in st.session_state or st.session_state['last_processed_file'] != file_key:
            # 새 파일이거나 아직 처리 안 했으면 처리
            with st.spinner('🔄 PDF 처리 중...'):
                try:
                    # Pipeline 초기화 및 처리
                    pipeline = Phase53Pipeline(pdf_processor, vlm_service)
                    result = pipeline.process_pdf(uploaded_file)
                    
                    # ✅ 결과를 session_state에 저장
                    st.session_state['last_processed_file'] = file_key
                    st.session_state['result'] = result
                    st.session_state['processing_error'] = None
                    
                except Exception as e:
                    logger.error(f"처리 오류: {str(e)}", exc_info=True)
                    st.session_state['processing_error'] = str(e)
                    st.error(f"❌ 처리 중 오류 발생: {str(e)}")
                    return
        
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
            st.metric("📄 페이지", f"{result.get('valid_pages', 0)}/{result.get('total_pages', 0)}")
        with col2:
            st.metric("📝 추출 글자", f"{len(result.get('markdown', ''))}자")
        with col3:
            st.metric("✂️ 청크", f"{len(result.get('chunks', []))}개")
        with col4:
            st.metric("🎯 종합 점수", f"{result.get('quality_score', 0)}/100")
        
        # 2. Fallback 통계
        if result.get('fallback_count', 0) > 0:
            st.info(f"🔄 Fallback 사용: {result['fallback_count']}페이지 ({result.get('fallback_ratio', 0):.1f}%)")
        
        # 3. DoD 검증 결과
        if 'dod_result' in result:
            dod = result['dod_result']
            if dod.get('passed', False):
                st.success("✅ DoD 검증 통과!")
            else:
                st.warning("⚠️ DoD 검증 실패")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("계층 보존율", f"{dod.get('hierarchy_preservation_rate', 0):.1%}")
            with col2:
                st.metric("경계 누수율", f"{dod.get('boundary_cross_bleed_rate', 0):.1%}")
            with col3:
                st.metric("빈 조문율", f"{dod.get('empty_article_rate', 0):.1%}")
        
        # 4. 청크 표시
        st.subheader("✂️ 생성된 청크")
        
        if result.get('chunks'):
            for i, chunk in enumerate(result['chunks']):
                # ✅ 수정 2: metadata 안의 char_count 안전하게 접근
                if 'metadata' in chunk and 'char_count' in chunk['metadata']:
                    char_count = chunk['metadata']['char_count']
                elif 'char_count' in chunk:
                    char_count = chunk['char_count']
                else:
                    char_count = len(chunk.get('content', ''))
                
                with st.expander(f"**청크 {i+1}** ({char_count}자)"):
                    st.text(chunk.get('content', ''))
                    
                    # metadata 표시
                    if 'metadata' in chunk:
                        st.caption(f"메타데이터: {chunk['metadata']}")
        else:
            st.warning("⚠️ 청크가 생성되지 않았습니다.")
        
        # ===== 다운로드 버튼 =====
        st.subheader("📥 다운로드")
        
        # ✅ 수정 3: 다운로드 버튼 (재처리 방지)
        col1, col2 = st.columns(2)
        
        with col1:
            if result.get('markdown'):
                st.download_button(
                    label="📥 Markdown 다운로드",
                    data=result['markdown'],
                    file_name=f"{uploaded_file.name}_markdown.md",
                    mime="text/markdown",
                    key="download_markdown"  # ← key 추가로 재실행 방지
                )
        
        with col2:
            if result.get('tree'):
                import json
                st.download_button(
                    label="📥 Tree JSON 다운로드",
                    data=json.dumps(result['tree'], ensure_ascii=False, indent=2),
                    file_name=f"{uploaded_file.name}_tree.json",
                    mime="application/json",
                    key="download_tree"  # ← key 추가로 재실행 방지
                )

if __name__ == "__main__":
    main()
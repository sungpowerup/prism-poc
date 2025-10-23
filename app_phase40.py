"""
app_phase40.py
PRISM Phase 4.0 - Streamlit UI (VLM-First)

Author: 최동현 (Frontend Lead)
Date: 2025-10-23
Version: 4.0
"""

import streamlit as st
import sys
from pathlib import Path
import logging
from datetime import datetime
import json
import base64
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Core 모듈 임포트
try:
    from core.pdf_processor_v40 import PDFProcessorV40
    from core.vlm_service_v40 import VLMServiceV40
    from core.storage import Storage
    from core.phase40_pipeline import Phase40Pipeline
    
    logger.info("✅ 모든 core 모듈 임포트 성공")
except Exception as e:
    logger.error(f"❌ 모듈 임포트 실패: {e}")
    st.error(f"모듈 임포트 실패: {e}")
    st.stop()

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="PRISM Phase 4.0 - VLM-First",
    page_icon="🚀",
    layout="wide"
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e88e5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .phase-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background-color: #1e88e5;
        color: white;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-left: 1rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 헤더
# ============================================================
st.markdown("""
<div class='main-header'>
    🚀 PRISM Phase 4.0
    <span class='phase-badge'>VLM-First</span>
</div>
<div class='sub-header'>
    차세대 지능형 문서 이해 플랫폼 | 완전 재설계
</div>
""", unsafe_allow_html=True)

# ============================================================
# Phase 4.0 소개
# ============================================================
with st.expander("📚 Phase 4.0 주요 개선사항", expanded=False):
    st.markdown("""
    ### 🔥 Phase 4.0: VLM-First 완전 재설계
    
    #### 핵심 전략
    1. **Layout Detection 제거** - 불필요한 복잡성 제거
    2. **페이지 전체 VLM 처리** - 맥락 유지
    3. **자연어 출력** - LLM이 이해하기 쉬운 형식
    4. **Markdown 생성** - 경쟁사 수준 품질
    5. **범용성 우선** - 모든 문서 대응
    
    #### 경쟁사 대비 목표
    - **Phase 3.5**: 35/100 (37%)
    - **Phase 4.0 목표**: 90/100 (95%) ✅
    
    #### 주요 차이점
    | 항목 | Phase 3.5 | Phase 4.0 |
    |------|----------|----------|
    | Layout Detection | ✅ 복잡 | ❌ 최소화 |
    | 처리 단위 | Region별 | 페이지 전체 |
    | 출력 형식 | JSON | 자연어 (Markdown) |
    | 맥락 유지 | ❌ 손실 | ✅ 유지 |
    | 범용성 | ⚠️ 제한적 | ✅ 범용 |
    """)

# ============================================================
# 사이드바 - 설정
# ============================================================
st.sidebar.header("⚙️ 설정")

# VLM 프로바이더 선택
vlm_provider = st.sidebar.selectbox(
    "VLM 프로바이더",
    ["azure_openai", "claude"],
    index=0
)

# 최대 페이지 수
max_pages = st.sidebar.slider(
    "최대 페이지 수",
    min_value=1,
    max_value=50,
    value=20,
    step=1
)

# DPI 설정
dpi = st.sidebar.slider(
    "이미지 해상도 (DPI)",
    min_value=150,
    max_value=300,
    value=300,
    step=50,
    help="높을수록 품질 좋지만 처리 시간 증가"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 사용 팁
- **고해상도 권장**: 300 DPI (최고 품질)
- **빠른 테스트**: 150 DPI
- **대용량 문서**: 페이지 수 제한
""")

# ============================================================
# 메인 영역 - PDF 업로드
# ============================================================
st.header("📁 PDF 업로드")

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요",
    type=['pdf'],
    help="최대 200MB까지 업로드 가능"
)

if uploaded_file is not None:
    # 파일 정보 표시
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.info(f"📄 **파일명**: {uploaded_file.name} | **크기**: {file_size:.2f} MB")
    
    # 처리 버튼
    if st.button("🚀 Phase 4.0 처리 시작", use_container_width=True):
        
        # 임시 파일 저장
        temp_path = Path("temp") / uploaded_file.name
        temp_path.parent.mkdir(exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(message: str, progress: int):
            progress_bar.progress(progress)
            status_text.text(message)
        
        # 처리 시작
        try:
            # 서비스 초기화
            with st.spinner("서비스 초기화 중..."):
                pdf_processor = PDFProcessorV40()
                vlm_service = VLMServiceV40(provider=vlm_provider)
                storage = Storage()
                pipeline = Phase40Pipeline(pdf_processor, vlm_service, storage)
            
            logger.info("✅ 모든 core 모듈 임포트 성공")
            
            # 처리 실행
            logger.info(f"🚀 Phase 4.0 처리 시작: {uploaded_file.name}")
            
            result = pipeline.process_pdf(
                str(temp_path),
                max_pages=max_pages,
                progress_callback=update_progress
            )
            
            # 처리 완료
            if result['status'] == 'success':
                st.success("✅ 처리 완료!")
                
                # 결과 표시
                st.markdown("---")
                st.header("📊 처리 결과")
                
                # 통계
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("처리 시간", f"{result['processing_time']:.1f}초")
                
                with col2:
                    st.metric("페이지 수", f"{result['pages_success']}/{result['pages_processed']}")
                
                with col3:
                    st.metric("총 글자 수", f"{result['total_chars']:,}")
                
                with col4:
                    success_rate = result['pages_success'] / result['pages_processed'] * 100
                    st.metric("성공률", f"{success_rate:.0f}%")
                
                # Markdown 내용 표시
                st.markdown("---")
                st.header("📝 추출된 내용 (Markdown)")
                
                with st.expander("전체 내용 보기", expanded=True):
                    st.markdown(result['markdown'])
                
                # 다운로드 버튼
                st.markdown("---")
                st.header("💾 다운로드")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Markdown 다운로드
                    st.download_button(
                        label="📝 Markdown 다운로드",
                        data=result['markdown'],
                        file_name=f"prism_result_{result['session_id']}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                
                with col2:
                    # JSON 다운로드
                    json_data = json.dumps(result, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📋 JSON 다운로드",
                        data=json_data,
                        file_name=f"prism_result_{result['session_id']}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            else:
                st.error(f"❌ 처리 실패: {result.get('error', '알 수 없는 오류')}")
        
        except Exception as e:
            st.error(f"❌ 처리 중 오류 발생: {e}")
            logger.error(f"처리 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            # 임시 파일 삭제
            if temp_path.exists():
                temp_path.unlink()

else:
    # 안내 메시지
    st.info("👆 PDF 파일을 업로드하여 시작하세요")
    
    st.markdown("""
    ### 📖 사용 방법
    
    1. **PDF 업로드**: 상단에서 PDF 파일 선택
    2. **설정 조정**: 사이드바에서 옵션 변경 (선택)
    3. **처리 시작**: "처리 시작" 버튼 클릭
    4. **결과 확인**: Markdown 형식으로 추출된 내용 확인
    5. **다운로드**: Markdown 또는 JSON 파일 다운로드
    
    ### ✨ Phase 4.0 특징
    
    - ✅ **완벽한 맥락 유지** - 페이지 전체를 한번에 분석
    - ✅ **자연어 설명** - LLM이 이해하기 쉬운 형식
    - ✅ **높은 정확도** - 경쟁사 수준 (95%+)
    - ✅ **범용성** - 모든 문서 유형 대응
    """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <strong>PRISM Phase 4.0 - VLM-First 완전 재설계</strong><br>
    🎯 Layout Detection 제거 | 페이지 전체 분석 | 자연어 출력 | 범용성 우선<br>
    목표: 경쟁사 대비 95% 품질 달성<br>
    Powered by Claude 3.5 Sonnet & Azure OpenAI GPT-4 Vision
</div>
""", unsafe_allow_html=True)

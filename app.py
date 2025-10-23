"""
app.py
PRISM Phase 4.2 - Streamlit UI (멀티스텝 검증)

✅ Phase 4.2 개선사항:
1. 2-Pass 처리 표시
2. 품질 점수 표시
3. 신뢰도 표시

Author: 최동현 (Frontend Lead)
Date: 2025-10-23
Version: 4.2
"""

import streamlit as st
import sys
from pathlib import Path
import logging
import json
from dotenv import load_dotenv

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
    from core.vlm_service import VLMServiceV42
    from core.storage import Storage
    from core.pipeline import Phase42Pipeline
    
    logger.info("✅ Phase 4.2 모듈 임포트 성공")
except Exception as e:
    logger.error(f"❌ 모듈 임포트 실패: {e}")
    st.error(f"모듈 임포트 실패: {e}")
    st.stop()

# ============================================================
# 세션 상태 초기화
# ============================================================
if 'processing_result' not in st.session_state:
    st.session_state['processing_result'] = None

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="PRISM Phase 4.2 - Multipass VLM",
    page_icon="🎯",
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
    .phase-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background-color: #ff6b35;
        color: white;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-left: 1rem;
    }
    .quality-score {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
    }
    .quality-excellent { color: #28a745; }
    .quality-good { color: #5cb85c; }
    .quality-fair { color: #f0ad4e; }
    .quality-poor { color: #d9534f; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 헤더
# ============================================================
st.markdown("""
<div class='main-header'>
    🎯 PRISM Phase 4.2
    <span class='phase-badge'>Multipass VLM</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Phase 4.2 소개
# ============================================================
with st.expander("📚 Phase 4.2 주요 개선사항", expanded=False):
    st.markdown("""
    ### 🔥 Phase 4.2: VLM 멀티스텝 검증
    
    #### 핵심 전략
    1. **2-Pass Processing** - 구조 파악 → 정밀 추출
    2. **강화된 프롬프팅** - 지도 차트 특수 처리
    3. **자동 품질 검증** - 신뢰도 기반 재시도
    4. **자동 청킹** - RAG 최적화
    5. **범용성 확보** - 하드코딩 제거
    
    #### Phase 4.1 문제점 해결
    - ❌ Phase 4.1: 권역 데이터 33% 정확도 (4개 오류)
    - ✅ Phase 4.2: 100% 정확도 목표
    
    #### 2-Pass 처리 방식
    ```
    Pass 1: 구조 파악
    ├─ 차트 종류 감지
    ├─ 지도 차트 여부 확인
    └─ 복잡도 평가
    
    Pass 2: 정밀 추출
    ├─ Pass 1 정보 활용
    ├─ 맞춤형 프롬프트
    └─ 품질 검증
    ```
    """)

# ============================================================
# 사이드바 - 설정
# ============================================================
st.sidebar.header("⚙️ 설정")

vlm_provider = st.sidebar.selectbox(
    "VLM 프로바이더",
    ["azure_openai", "claude"],
    index=0
)

max_pages = st.sidebar.slider(
    "최대 페이지 수",
    min_value=1,
    max_value=50,
    value=20,
    step=1
)

dpi = st.sidebar.slider(
    "이미지 해상도 (DPI)",
    min_value=150,
    max_value=300,
    value=300,
    step=50
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 Phase 4.2 특징
- **2-Pass 처리**: 구조→추출
- **품질 검증**: 자동 재시도
- **청킹 자동화**: RAG 최적화
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
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.info(f"📄 **파일명**: {uploaded_file.name} | **크기**: {file_size:.2f} MB")
    
    if st.button("🚀 Phase 4.2 처리 시작", use_container_width=True):
        
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
            with st.spinner("Phase 4.2 서비스 초기화 중..."):
                pdf_processor = PDFProcessorV40()
                vlm_service = VLMServiceV42(provider=vlm_provider)
                storage = Storage()
                pipeline = Phase42Pipeline(pdf_processor, vlm_service, storage)
            
            logger.info(f"🚀 Phase 4.2 처리 시작: {uploaded_file.name}")
            
            result = pipeline.process_pdf(
                str(temp_path),
                max_pages=max_pages,
                progress_callback=update_progress
            )
            
            # 세션 상태에 결과 저장
            st.session_state['processing_result'] = result
            
        except Exception as e:
            st.error(f"❌ 처리 중 오류 발생: {e}")
            logger.error(f"처리 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            if temp_path.exists():
                temp_path.unlink()

# ============================================================
# 결과 표시
# ============================================================
if st.session_state['processing_result'] is not None:
    result = st.session_state['processing_result']
    
    if result['status'] == 'success':
        st.success("✅ 처리 완료!")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 품질 점수 (Phase 4.2 신규)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        quality_score = result.get('quality_score', 0)
        avg_confidence = result.get('avg_confidence', 0)
        
        # 품질 등급
        if quality_score >= 90:
            quality_class = "quality-excellent"
            quality_label = "우수"
        elif quality_score >= 75:
            quality_class = "quality-good"
            quality_label = "양호"
        elif quality_score >= 60:
            quality_class = "quality-fair"
            quality_label = "보통"
        else:
            quality_class = "quality-poor"
            quality_label = "개선 필요"
        
        st.markdown("---")
        st.header("🎯 Phase 4.2 품질 평가")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class='quality-score {quality_class}'>
                {quality_score:.1f}/100
            </div>
            <div style='text-align: center; font-size: 1.2rem; color: #666;'>
                품질 등급: <strong>{quality_label}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style='padding: 20px;'>
                <h4>신뢰도 지표</h4>
                <p>평균 신뢰도: <strong>{avg_confidence:.2%}</strong></p>
                <p>낮은 신뢰도 페이지: <strong>{result.get('low_confidence_count', 0)}개</strong></p>
                <p>재시도 횟수: <strong>{result.get('retry_count', 0)}회</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 통계
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📊 처리 결과")
        
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
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Markdown 내용
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📝 추출된 내용")
        
        with st.expander("전체 내용 보기", expanded=True):
            st.markdown(result['markdown'])
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 다운로드
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("💾 다운로드")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📝 Markdown 다운로드",
                data=result['markdown'],
                file_name=f"prism_result_{result['session_id']}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
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

else:
    if uploaded_file is None:
        st.info("👆 PDF 파일을 업로드하여 시작하세요")
        
        st.markdown("""
        ### 📖 Phase 4.2 특징
        
        - ✅ **2-Pass 처리** - 구조 파악 후 정밀 추출
        - ✅ **멀티스텝 검증** - 품질 기반 자동 재시도
        - ✅ **강화된 정확도** - 지도 차트 특수 처리
        - ✅ **자동 청킹** - RAG 최적화
        - ✅ **품질 점수** - 실시간 평가
        """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <strong>PRISM Phase 4.2 - Multipass VLM Verification</strong><br>
    🎯 2-Pass Processing | 품질 기반 검증 | 자동 청킹 | 범용성 확보<br>
    목표: 경쟁사 수준 달성 (90/100점)<br>
    Powered by Claude 3.5 Sonnet & Azure OpenAI GPT-4 Vision
</div>
""", unsafe_allow_html=True)
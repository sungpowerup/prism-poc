"""
app.py
PRISM Phase 4.5 - Streamlit UI (OCR + VLM 하이브리드)

✅ Phase 4.5 개선사항:
1. OCR + VLM 하이브리드 처리
2. 품질 점수 정확 표시
3. 경쟁사 수준 목표 (95/100)

Author: 최동현 (Frontend Lead)
Date: 2025-10-23
Version: 4.5
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
    from core.vlm_service import VLMServiceV45
    from core.storage import Storage
    from core.pipeline import Phase45Pipeline
    
    logger.info("✅ Phase 4.5 모듈 임포트 성공")
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
    page_title="PRISM Phase 4.5 - OCR + VLM Hybrid",
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
    
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 헤더
# ============================================================
st.markdown("""
<div class='main-header'>
    🎯 PRISM Phase 4.5
    <span class='phase-badge'>OCR + VLM Hybrid</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Phase 4.5 소개
# ============================================================
with st.expander("📚 Phase 4.5 주요 개선사항", expanded=False):
    st.markdown("""
    ### 🔥 Phase 4.5: OCR + VLM 하이브리드
    
    #### 핵심 개선
    1. **OCR 텍스트 추출** - 정류장 이름 정확 인식
    2. **VLM 구조 이해** - 다이어그램 개수 정확 감지
    3. **하이브리드 통합** - OCR + VLM 장점 결합
    4. **환각 방지** - OCR 텍스트 기반 검증
    5. **품질 점수 수정** - 정확한 계산 로직
    6. **RAG 최적화** - 불필요 내용 제거
    
    #### Phase 4.4 문제점 해결
    - ❌ Phase 4.4: 다이어그램 1 환각 (30% 정확도)
    - ✅ Phase 4.5: OCR + VLM으로 95% 목표
    
    #### 처리 방식
    ```
    Step 1: OCR 텍스트 추출
    ├─ Tesseract OCR
    ├─ 정류장 이름 추출
    └─ VLM에 전달
    
    Step 2: VLM 구조 분석
    ├─ 다이어그램 개수 정확 감지
    ├─ 복잡도 판단
    └─ 전략 결정
    
    Step 3: OCR + VLM 통합
    ├─ OCR 텍스트 우선 사용
    ├─ VLM으로 구조 이해
    └─ 하이브리드 추출
    
    Step 4: 검증
    ├─ OCR 매칭 확인
    ├─ 환각 탐지
    └─ 품질 평가
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
### 💡 Phase 4.5 특징
- **OCR + VLM**: 하이브리드 처리
- **환각 방지**: OCR 텍스트 검증
- **다이어그램 정확 감지**: 3개 모두 추출
- **품질 점수 수정**: 정확한 계산
- **경쟁사 수준**: 95/100 목표
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
    
    if st.button("🚀 Phase 4.5 처리 시작", use_container_width=True):
        
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
            with st.spinner("Phase 4.5 서비스 초기화 중..."):
                pdf_processor = PDFProcessorV40()
                vlm_service = VLMServiceV45(provider=vlm_provider)
                storage = Storage()
                pipeline = Phase45Pipeline(pdf_processor, vlm_service, storage)
            
            logger.info(f"🚀 Phase 4.5 처리 시작: {uploaded_file.name}")
            
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
        # 종합 평가
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📊 종합 평가")
        
        quality_score = result.get('quality_score', 0)
        fidelity_score = result.get('fidelity_score', 0)
        chunking_score = result.get('chunking_score', 0)
        rag_score = result.get('rag_score', 0)
        avg_confidence = result.get('avg_confidence', 0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 종합 점수
            if quality_score >= 90:
                quality_class = "quality-excellent"
                quality_label = "우수 (경쟁사 수준)"
            elif quality_score >= 75:
                quality_class = "quality-good"
                quality_label = "양호"
            elif quality_score >= 60:
                quality_class = "quality-fair"
                quality_label = "보통"
            else:
                quality_class = "quality-poor"
                quality_label = "개선 필요"
            
            st.markdown(f"""
            <div class='quality-score {quality_class}'>
                {quality_score:.1f}/100
            </div>
            <div style='text-align: center; font-size: 1.2rem; color: #666;'>
                종합 품질: <strong>{quality_label}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            # 경쟁사 대비
            competitor_score = 95.0
            gap = quality_score - competitor_score
            
            if gap >= 0:
                gap_color = "green"
                gap_icon = "✅"
            else:
                gap_color = "red"
                gap_icon = "⚠️"
            
            st.markdown(f"""
            <div style='text-align: center; margin-top: 20px;'>
                {gap_icon} <strong>경쟁사 대비:</strong> 
                <span style='color: {gap_color}; font-size: 1.2rem;'>
                    {gap:+.1f}점
                </span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class='metric-card'>
                <h4>📋 항목별 점수</h4>
            </div>
            """, unsafe_allow_html=True)
            
            st.metric("1️⃣ 원본 충실도", f"{fidelity_score:.1f}/100")
            st.metric("2️⃣ 신뢰도", f"{avg_confidence:.2%}")
            st.metric("3️⃣ 청킹 품질", f"{chunking_score:.1f}/100")
            st.metric("4️⃣ RAG 적합도", f"{rag_score:.1f}/100")
        
        # 상세 메트릭
        st.markdown("---")
        st.subheader("📈 상세 메트릭")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            strategy_simple = result.get('strategy_simple', 0)
            strategy_complex = result.get('strategy_complex_ocr', 0)
            st.metric("Simple 전략", f"{strategy_simple}개")
        
        with col2:
            st.metric("Complex OCR 전략", f"{strategy_complex}개")
        
        with col3:
            validation_issues = result.get('validation_issues', 0)
            st.metric("검증 이슈", f"{validation_issues}개")
        
        with col4:
            processing_time = result.get('processing_time', 0)
            st.metric("처리 시간", f"{processing_time:.1f}초")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 통계
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📊 처리 결과")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pages_success = result.get('pages_success', 0)
            pages_processed = result.get('pages_processed', 0)
            st.metric("페이지 수", f"{pages_success}/{pages_processed}")
        
        with col2:
            total_chars = result.get('total_chars', len(result.get('markdown', '')))
            st.metric("총 글자 수", f"{total_chars:,}")
        
        with col3:
            success_rate = pages_success / pages_processed * 100 if pages_processed > 0 else 0
            st.metric("성공률", f"{success_rate:.0f}%")
        
        with col4:
            pages_error = result.get('pages_error', 0)
            st.metric("오류 페이지", f"{pages_error}개")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Markdown 내용
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📝 추출된 내용")
        
        markdown_content = result.get('markdown', '')
        
        with st.expander("전체 내용 보기", expanded=True):
            st.markdown(markdown_content)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 다운로드
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("💾 다운로드")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📝 Markdown 다운로드",
                data=markdown_content,
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
        ### 📖 Phase 4.5 특징
        
        - ✅ **OCR + VLM** - 하이브리드 처리
        - ✅ **환각 방지** - OCR 텍스트 검증
        - ✅ **다이어그램 정확 감지** - 3개 모두 추출
        - ✅ **품질 점수 수정** - 정확한 계산
        - ✅ **RAG 최적화** - 불필요 내용 제거
        - ✅ **경쟁사 수준** - 95/100 목표
        """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <strong>PRISM Phase 4.5 - OCR + VLM Hybrid</strong><br>
    🎯 OCR 텍스트 추출 | VLM 구조 이해 | 하이브리드 통합 | 환각 방지<br>
    목표: 경쟁사 수준 달성 (95/100점)<br>
    Powered by Tesseract OCR & Azure OpenAI GPT-4 Vision
</div>
""", unsafe_allow_html=True)
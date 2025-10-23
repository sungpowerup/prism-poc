"""
app.py
PRISM Phase 4.3 - Streamlit UI (지능형 분할 처리)

✅ Phase 4.3 개선사항:
1. 3-Step 처리 표시
2. 상세 품질 메트릭
3. 전략별 통계
4. 6개 항목 평가

Author: 최동현 (Frontend Lead)
Date: 2025-10-23
Version: 4.3
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
    from core.vlm_service import VLMServiceV43
    from core.storage import Storage
    from core.pipeline import Phase43Pipeline
    
    logger.info("✅ Phase 4.3 모듈 임포트 성공")
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
    page_title="PRISM Phase 4.3 - Intelligent Processing",
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
    🎯 PRISM Phase 4.3
    <span class='phase-badge'>Intelligent Processing</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Phase 4.3 소개
# ============================================================
with st.expander("📚 Phase 4.3 주요 개선사항", expanded=False):
    st.markdown("""
    ### 🔥 Phase 4.3: 지능형 분할 처리
    
    #### 핵심 전략
    1. **3-Step Processing** - 구조 분석 → 전략 분기 → 검증
    2. **복잡도 기반 전략** - Simple vs Complex
    3. **영역별 독립 처리** - 다이어그램 중복 방지
    4. **환각 방지** - 읽기 불가 명시
    5. **상세 품질 메트릭** - 6개 항목 평가
    
    #### Phase 4.2 문제점 해결
    - ❌ Phase 4.2: 정류장 443개 중복 (환각)
    - ✅ Phase 4.3: 영역별 독립 처리 + 환각 방지
    
    #### 3-Step 처리 방식
    ```
    Step 1: 구조 분석
    ├─ 요소 감지
    ├─ 복잡도 판단
    └─ 전략 결정
    
    Step 2: 전략 실행
    ├─ Simple: 단일 VLM
    └─ Complex: 분할 정복
    
    Step 3: 검증
    ├─ 환각 탐지
    ├─ 품질 평가
    └─ 이슈 명시
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
### 💡 Phase 4.3 특징
- **3-Step 처리**: 분석→전략→검증
- **복잡도 판단**: 자동 전략 분기
- **환각 방지**: 읽기 불가 명시
- **상세 평가**: 6개 항목 메트릭
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
    
    if st.button("🚀 Phase 4.3 처리 시작", use_container_width=True):
        
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
            with st.spinner("Phase 4.3 서비스 초기화 중..."):
                pdf_processor = PDFProcessorV40()
                vlm_service = VLMServiceV43(provider=vlm_provider)
                storage = Storage()
                pipeline = Phase43Pipeline(pdf_processor, vlm_service, storage)
            
            logger.info(f"🚀 Phase 4.3 처리 시작: {uploaded_file.name}")
            
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
        # 6개 항목 종합 평가 (Phase 4.3 신규)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("---")
        st.header("📊 6개 항목 종합 평가")
        
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
            
            st.markdown(f"""
            <div class='quality-score {quality_class}'>
                {quality_score:.1f}/100
            </div>
            <div style='text-align: center; font-size: 1.2rem; color: #666;'>
                종합 품질: <strong>{quality_label}</strong>
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
            strategy_complex = result.get('strategy_complex', 0)
            st.metric("Simple 전략", f"{strategy_simple}개")
        
        with col2:
            st.metric("Complex 전략", f"{strategy_complex}개")
        
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
        ### 📖 Phase 4.3 특징
        
        - ✅ **3-Step 처리** - 구조 분석 → 전략 분기 → 검증
        - ✅ **지능형 전략** - 복잡도 자동 판단
        - ✅ **환각 방지** - 읽기 불가 명시
        - ✅ **영역별 처리** - 다이어그램 독립 추출
        - ✅ **상세 평가** - 6개 항목 메트릭
        - ✅ **경쟁사 수준** - 95/100 목표
        """)

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <strong>PRISM Phase 4.3 - Intelligent Processing</strong><br>
    🎯 3-Step Processing | 복잡도 판단 | 영역별 처리 | 환각 방지 | 상세 평가<br>
    목표: 경쟁사 수준 달성 (95/100점)<br>
    Powered by Claude 3.5 Sonnet & Azure OpenAI GPT-4 Vision
</div>
""", unsafe_allow_html=True)
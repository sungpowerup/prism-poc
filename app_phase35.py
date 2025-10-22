"""
app_phase35.py
PRISM Phase 3.5 - Streamlit UI (대규모 개선)

Author: 최동현 (Frontend Lead)
Date: 2025-10-23
Version: 3.5
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
    from core.pdf_processor import PDFProcessor
    from core.layout_detector_v35 import LayoutDetectorV35
    from core.vlm_service import VLMService
    from core.storage import Storage
    from core.phase35_pipeline import Phase35Pipeline
    
    logger.info("✅ 모든 core 모듈 임포트 성공")
except Exception as e:
    logger.error(f"❌ 모듈 임포트 실패: {e}")
    st.error(f"모듈 임포트 실패: {e}")
    st.stop()

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="PRISM Phase 3.5 - 대규모 개선",
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
    .metric-box {
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 헤더
# ============================================================
st.markdown('<div class="main-header">🎯 PRISM Phase 3.5<span class="phase-badge">대규모 개선</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">표 재설계 | 원그래프 강화 | 막대그래프 완화 | VLM 프롬프트 개선</div>', unsafe_allow_html=True)

# 목표 영역 표시
st.markdown("### 🎯 **개선 목표**")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Phase 3.4.4 문제")
    st.markdown("""
    - ❌ 표 감지: 0%
    - ❌ 막대그래프: 25%
    - ❌ 원그래프 과감지
    - **총 35점 / 100점**
    """)

with col2:
    st.markdown("#### Phase 3.5 개선")
    st.markdown("""
    - ✅ 표: Text Grid 단독
    - ✅ 막대: min_bars=2
    - ✅ 원: minRadius=120
    - ✅ VLM 프롬프트 강화
    """)

with col3:
    st.markdown("#### 목표 품질")
    st.markdown("""
    - 🎯 표 감지: 100%
    - 🎯 막대그래프: 100%
    - 🎯 원그래프 정확도: 95%
    - **목표: 85점 / 100점**
    """)

st.markdown("---")

# ============================================================
# 세션 상태 초기화
# ============================================================
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None
if 'processing_result' not in st.session_state:
    st.session_state.processing_result = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

# ============================================================
# 1. VLM 프로바이더 선택
# ============================================================
st.markdown("### 1️⃣ VLM 프로바이더 선택")

col1, col2 = st.columns([1, 2])

with col1:
    vlm_provider = st.selectbox(
        "VLM 프로바이더",
        ["azure_openai", "claude"],
        index=0,
        help="VLM 서비스 선택"
    )

with col2:
    if vlm_provider == "azure_openai":
        st.info("✅ Azure OpenAI GPT-4 Vision 사용")
    else:
        st.info("✅ Claude 3.5 Sonnet 사용")

# 파이프라인 초기화
try:
    if st.session_state.pipeline is None or st.session_state.get('current_provider') != vlm_provider:
        with st.spinner(f"🔄 {vlm_provider} 초기화 중..."):
            pdf_processor = PDFProcessor()
            layout_detector = LayoutDetectorV35()
            vlm_service = VLMService(provider=vlm_provider)
            storage = Storage()
            
            st.session_state.pipeline = Phase35Pipeline(
                pdf_processor=pdf_processor,
                layout_detector=layout_detector,
                vlm_service=vlm_service,
                storage=storage
            )
            st.session_state.current_provider = vlm_provider
            
            st.success(f"✅ Phase 3.5 파이프라인 초기화 완료: {vlm_provider}")
            
except Exception as e:
    st.error(f"❌ 초기화 실패: {e}")
    st.stop()

st.markdown("---")

# ============================================================
# 2. PDF 파일 업로드
# ============================================================
st.markdown("### 2️⃣ PDF 파일 업로드")

uploaded_file = st.file_uploader(
    "PDF 파일을 선택하세요",
    type=['pdf'],
    help="최대 20 페이지까지 처리됩니다"
)

if uploaded_file is not None:
    st.session_state.uploaded_file_name = uploaded_file.name
    
    # 파일 정보 표시
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 파일명", uploaded_file.name)
    with col2:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.metric("📦 파일 크기", f"{file_size_mb:.2f} MB")
    with col3:
        st.metric("🎯 Phase", "3.5 (대규모 개선)")

st.markdown("---")

# ============================================================
# 3. 처리 시작
# ============================================================
st.markdown("### 3️⃣ 문서 처리")

if uploaded_file is not None:
    if st.button("🚀 Phase 3.5 처리 시작", type="primary", use_container_width=True):
        try:
            # 임시 파일 저장
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            temp_file_path = temp_dir / uploaded_file.name
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # 처리 시작
            progress_container = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(message: str, progress: int):
                status_text.text(message)
                progress_bar.progress(progress)
            
            # Pipeline 실행
            logger.info(f"🚀 Phase 3.5 처리 시작: {uploaded_file.name}")
            
            result = st.session_state.pipeline.process_pdf(
                pdf_path=str(temp_file_path),
                max_pages=20,
                progress_callback=update_progress
            )
            
            st.session_state.processing_result = result
            
            # 임시 파일 삭제
            temp_file_path.unlink()
            
            # 완료 메시지
            st.balloons()
            st.success("✅ Phase 3.5 처리 완료!")
            
        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}")
            st.error(f"처리 중 오류 발생: {e}")
            import traceback
            st.code(traceback.format_exc())

st.markdown("---")

# ============================================================
# 4. 결과 표시
# ============================================================
if st.session_state.processing_result is not None:
    result = st.session_state.processing_result
    
    st.markdown("### 4️⃣ 처리 결과")
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("⏱️ 처리 시간", f"{result['processing_time']:.1f}초")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("📄 페이지 수", result['pages_processed'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        st.metric("🔍 감지 영역", result['regions_detected'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-box">', unsafe_allow_html=True)
        success_rate = (result['vlm_success'] / result['regions_detected'] * 100) if result['regions_detected'] > 0 else 0
        st.metric("✅ VLM 성공률", f"{success_rate:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 타입별 통계
    st.markdown("#### 📊 타입별 통계")
    
    type_counts = {}
    for r in result['results']:
        region_type = r['type']
        type_counts[region_type] = type_counts.get(region_type, 0) + 1
    
    # 차트 표시
    if type_counts:
        import pandas as pd
        df = pd.DataFrame(list(type_counts.items()), columns=['타입', '개수'])
        df = df.sort_values('개수', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df.set_index('타입'))
        
        with col2:
            st.dataframe(df, use_container_width=True)
    
    # 상세 결과 표시
    st.markdown("#### 🔍 상세 결과")
    
    if result['results']:
        for i, region in enumerate(result['results'], 1):
            with st.expander(f"Region {i}: {region['type']} (페이지 {region['page_num']})"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("**메타데이터**")
                    st.json({
                        'region_id': region['region_id'],
                        'type': region['type'],
                        'bbox': region['bbox'],
                        'confidence': region['confidence'],
                        'metadata': region.get('metadata', {})
                    })
                
                with col2:
                    st.markdown("**VLM 결과**")
                    st.text_area(
                        "VLM 응답",
                        value=region['vlm_result'],
                        height=200,
                        key=f"vlm_{i}"
                    )
    else:
        st.warning("⚠️ 감지된 영역이 없습니다.")
    
    # 다운로드 버튼
    st.markdown("#### 💾 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON 다운로드
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        st.download_button(
            label="📄 JSON 다운로드",
            data=json_str,
            file_name=f"prism_result_{result['session_id']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # Markdown 다운로드
        md_content = f"""# PRISM Phase 3.5 처리 결과

## 기본 정보
- **Session ID**: {result['session_id']}
- **처리 시간**: {result['processing_time']:.1f}초
- **페이지 수**: {result['pages_processed']}
- **감지 영역**: {result['regions_detected']}
- **VLM 성공**: {result['vlm_success']} / {result['regions_detected']}

## 타입별 통계
"""
        for region_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            md_content += f"- **{region_type}**: {count}개\n"
        
        md_content += "\n## 상세 결과\n\n"
        
        for i, region in enumerate(result['results'], 1):
            md_content += f"""### Region {i}: {region['type']} (페이지 {region['page_num']})

**메타데이터**:
```json
{json.dumps({
    'region_id': region['region_id'],
    'bbox': region['bbox'],
    'confidence': region['confidence'],
    'metadata': region.get('metadata', {})
}, indent=2, ensure_ascii=False)}
```

**VLM 결과**:
```
{region['vlm_result']}
```

---

"""
        
        st.download_button(
            label="📝 Markdown 다운로드",
            data=md_content,
            file_name=f"prism_result_{result['session_id']}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ============================================================
# 푸터
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    <strong>PRISM Phase 3.5 - 대규모 개선</strong><br>
    🎯 표 재설계 | 원그래프 강화 | 막대그래프 완화 | VLM 프롬프트 개선<br>
    목표: 경쟁사 대비 85% 품질 달성<br>
    Powered by Claude 3.5 Sonnet & Azure OpenAI GPT-4 Vision
</div>
""", unsafe_allow_html=True)

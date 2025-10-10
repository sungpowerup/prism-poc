"""
app.py
PRISM POC - Streamlit UI (최종 버전)
- 멀티 VLM 프로바이더 지원
- 다운로드 기능
- 모델 선택 UI
"""

import streamlit as st
import asyncio
from pathlib import Path
import tempfile
from PIL import Image
import base64
import io
import json
import traceback

# 로컬 모듈
from core.pdf_processor import PDFProcessor
from core.vlm_service import VLMService
from utils.logger import setup_logger

# ElementClassifier는 선택적
try:
    from core.element_classifier import ElementClassifier
except ImportError:
    ElementClassifier = None

logger = setup_logger(__name__)

# ============================================================
# Session State 초기화
# ============================================================

if 'pdf_processor' not in st.session_state:
    st.session_state.pdf_processor = None

if 'vlm_service' not in st.session_state:
    st.session_state.vlm_service = None

if 'classifier' not in st.session_state:
    st.session_state.classifier = None

if 'results' not in st.session_state:
    st.session_state.results = []

if 'available_providers' not in st.session_state:
    st.session_state.available_providers = {}

if 'vlm_service_init' not in st.session_state:
    st.session_state.vlm_service_init = False

# ============================================================
# Helper Functions
# ============================================================

def pil_to_base64(image: Image.Image) -> str:
    """PIL Image → Base64"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def base64_to_pil(base64_str: str) -> Image.Image:
    """Base64 → PIL Image"""
    image_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(image_data))

# ============================================================
# PDF 처리 (비동기)
# ============================================================

async def process_pdf_async(pdf_path: Path, use_ocr: bool = True):
    """PDF 비동기 처리"""
    
    # 선택된 프로바이더 확인
    selected_provider = st.session_state.get('selected_provider', None)
    
    if not selected_provider:
        st.error("❌ VLM 모델이 선택되지 않았습니다!")
        return []
    
    # 초기화
    if st.session_state.pdf_processor is None:
        with st.spinner("🚀 PDF 프로세서 초기화 중..."):
            st.session_state.pdf_processor = PDFProcessor()
    
    if st.session_state.vlm_service is None or \
       st.session_state.get('current_provider_id') != selected_provider:
        with st.spinner(f"🚀 VLM 서비스 초기화 중... ({selected_provider})"):
            st.session_state.vlm_service = VLMService(selected_provider)
            st.session_state.current_provider_id = selected_provider
    
    if st.session_state.classifier is None:
        if ElementClassifier:
            with st.spinner("🚀 분류기 초기화 중..."):
                st.session_state.classifier = ElementClassifier()
        else:
            st.session_state.classifier = None
    
    pdf_processor = st.session_state.pdf_processor
    vlm_service = st.session_state.vlm_service
    classifier = st.session_state.classifier
    
    # 페이지 수 확인
    page_count = pdf_processor.get_page_count(pdf_path)
    
    st.info(f"📄 총 {page_count}페이지 처리 시작...")
    
    # 진행 상태 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    for page_num in range(1, page_count + 1):
        try:
            status_text.text(f"📄 처리 중: {page_num}/{page_count} 페이지...")
            
            # 1) PDF 페이지 처리 (이미지 + OCR)
            page_data = pdf_processor.process_page(pdf_path, page_num, use_ocr)
            
            # 2) Element 타입 분류 (dict 처리)
            element_type_data = page_data.get('element_type', {'element_type': 'image'})
            
            if isinstance(element_type_data, dict):
                element_type = element_type_data.get('element_type', 'image')
                confidence = element_type_data.get('confidence', 0.0)
                reasoning = element_type_data.get('reasoning', 'No reasoning')
            else:
                element_type = element_type_data
                confidence = 0.0
                reasoning = 'Direct classification'
            
            logger.info(f"Element 타입: {element_type} (confidence: {confidence:.2f})")
            
            # 3) VLM 캡션 생성
            vlm_result = await vlm_service.generate_caption(
                image_base64=page_data['image_base64'],
                element_type=element_type,
                extracted_text=page_data.get('ocr_text', '')
            )
            
            # 4) 결과 저장
            result = {
                'page_num': page_num,
                'element_type': element_type,
                'classification_confidence': confidence,
                'classification_reasoning': reasoning,
                'caption': vlm_result['caption'],
                'ocr_text': page_data.get('ocr_text', ''),
                'image_base64': page_data['image_base64'],
                'processing_time': page_data.get('processing_time', 0),
                'model': vlm_result.get('model', 'Unknown'),
                'provider': vlm_result.get('provider', 'Unknown'),
                'confidence': vlm_result.get('confidence', 0.0),
                'usage': vlm_result.get('usage', {})
            }
            
            results.append(result)
            
            # 진행률 업데이트
            progress_bar.progress(page_num / page_count)
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 실패: {e}")
            logger.error(traceback.format_exc())
            
            # 실패해도 계속 진행
            results.append({
                'page_num': page_num,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
            progress_bar.progress(page_num / page_count)
    
    status_text.text("✅ 처리 완료!")
    progress_bar.progress(1.0)
    
    return results

# ============================================================
# Streamlit UI
# ============================================================

def main():
    st.set_page_config(
        page_title="PRISM POC",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 PRISM POC - 지능형 문서 이해")
    st.caption("PDF 문서를 업로드하면 자동으로 분석합니다")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # VLM 모델 선택
        st.subheader("🤖 VLM 모델 선택")
        
        # VLMService 초기화 (사용 가능한 프로바이더 확인용)
        if not st.session_state.vlm_service_init:
            try:
                temp_service = VLMService()
                st.session_state.available_providers = temp_service.get_available_providers()
                st.session_state.vlm_service_init = True
            except Exception as e:
                st.error(f"VLM 서비스 초기화 실패: {e}")
                st.session_state.available_providers = {}
        
        available_providers = st.session_state.available_providers
        
        if not available_providers:
            st.error("❌ 사용 가능한 VLM 모델이 없습니다!")
            st.info(
                "**설정 방법:**\n\n"
                "**Option 1: Claude API** (권장)\n"
                "1. https://console.anthropic.com 가입\n"
                "2. API 키 발급\n"
                "3. .env에 ANTHROPIC_API_KEY 추가\n"
                "4. pip install anthropic\n\n"
                "**Option 2: Azure OpenAI**\n"
                "1. Azure Portal에서 리소스 생성\n"
                "2. .env에 AZURE_OPENAI_* 설정\n"
                "3. pip install openai\n\n"
                "**Option 3: Ollama** (무료)\n"
                "1. ollama pull llama3.2-vision:11b\n"
                "2. ollama serve"
            )
        else:
            # 프로바이더 선택 라디오 버튼
            provider_options = {}
            provider_labels = []
            
            for provider_id, info in available_providers.items():
                label = (
                    f"**{info['name']}**\n"
                    f"{info['speed']} | {info['quality']}\n"
                    f"{info['cost']}"
                )
                provider_options[label] = provider_id
                provider_labels.append(label)
            
            selected_label = st.radio(
                "사용할 모델을 선택하세요:",
                options=provider_labels,
                index=0,
                help="Claude/Azure는 고품질, Ollama는 무료"
            )
            
            selected_provider = provider_options[selected_label]
            
            # 선택된 프로바이더 정보 표시
            with st.expander("ℹ️ 모델 상세 정보", expanded=False):
                info = available_providers[selected_provider]
                st.markdown(f"""
**프로바이더**: {info['provider']}  
**속도**: {info['speed']}  
**품질**: {info['quality']}  
**비용**: {info['cost']}  

**설명**: {info['description']}
                """)
            
            # Session state에 저장
            st.session_state.selected_provider = selected_provider
        
        st.divider()
        
        # OCR 설정
        use_ocr = st.checkbox(
            "OCR 사용",
            value=True,
            help="이미지에서 텍스트 추출 (PaddleOCR)"
        )
        
        st.divider()
        
        st.subheader("📊 시스템 상태")
        
        if st.session_state.pdf_processor:
            st.success("✅ PDF Processor")
        else:
            st.info("⏳ PDF Processor")
        
        if st.session_state.vlm_service:
            current_info = st.session_state.vlm_service.get_current_provider_info()
            st.success(f"✅ VLM: {current_info['name']}")
        else:
            st.info("⏳ VLM Service")
        
        if st.session_state.classifier:
            st.success("✅ Element Classifier")
        else:
            st.warning("⚠️ Classifier 없음")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "📄 PDF 파일 업로드",
        type=['pdf'],
        help="분석할 PDF 파일을 선택하세요"
    )
    
    if uploaded_file:
        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = Path(tmp_file.name)
        
        st.info(f"📄 파일: {uploaded_file.name}")
        
        # 처리 시작
        if st.button("🚀 분석 시작", type="primary"):
            try:
                # 비동기 처리
                results = asyncio.run(
                    process_pdf_async(pdf_path, use_ocr)
                )
                
                st.session_state.results = results
                
            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")
                st.error(traceback.format_exc())
    
    # 결과 표시
    if st.session_state.results:
        st.divider()
        st.header("📊 분석 결과")
        
        # 다운로드 버튼 추가
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"총 {len(st.session_state.results)}페이지 분석 완료")
        with col2:
            # JSON 다운로드
            results_json = json.dumps(st.session_state.results, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 결과 다운로드 (JSON)",
                data=results_json,
                file_name=f"prism_results_{uploaded_file.name if uploaded_file else 'unknown'}.json",
                mime="application/json"
            )
        
        for result in st.session_state.results:
            if 'error' in result:
                # 오류 표시
                with st.expander(f"❌ Page {result['page_num']} (실패)", expanded=False):
                    st.error(result['error'])
                    with st.expander("🔍 상세 오류 정보"):
                        st.code(result['traceback'])
                continue
            
            # 정상 결과 표시
            with st.expander(f"📄 Page {result['page_num']} - {result['element_type'].upper()}", expanded=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("📷 이미지")
                    image = base64_to_pil(result['image_base64'])
                    st.image(image, use_column_width=True)
                    
                    st.caption(f"분류: {result['element_type']}")
                    st.caption(f"신뢰도: {result.get('confidence', 0):.2f}")
                
                with col2:
                    st.subheader("💬 VLM 캡션")
                    st.write(result['caption'])
                    
                    # 모델 정보 표시
                    st.caption(f"🤖 모델: {result.get('model', 'Unknown')}")
                    st.caption(f"🏢 프로바이더: {result.get('provider', 'Unknown')}")
                    
                    # 비용 정보 (있으면)
                    usage = result.get('usage', {})
                    if 'cost_usd' in usage:
                        cost_usd = usage['cost_usd']
                        cost_krw = usage.get('cost_krw', int(cost_usd * 1300))
                        if cost_usd > 0:
                            st.caption(f"💰 비용: ${cost_usd:.4f} (약 {cost_krw}원)")
                        else:
                            st.caption("✅ 비용: 무료")
                    
                    if result.get('ocr_text'):
                        st.subheader("📝 OCR 텍스트")
                        st.text_area(
                            "추출된 텍스트",
                            result['ocr_text'],
                            height=200,
                            key=f"ocr_{result['page_num']}"
                        )
                    
                    st.caption(f"⏱️ 처리 시간: {result.get('processing_time', 0):.2f}초")

if __name__ == "__main__":
    main()
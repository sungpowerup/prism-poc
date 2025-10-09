"""
PRISM POC - Main Application with OCR
PDF + 이미지 처리 및 VLM 변환 (OCR 통합)
"""

import streamlit as st
import asyncio
from pathlib import Path
import json
from datetime import datetime
import logging
import sys

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent))

from core.pdf_processor import PDFProcessor
from core.vlm_service import VLMService

# ElementClassifier는 기존 프로젝트에 있음 (import 유지)
try:
    from core.element_classifier import ElementClassifier
except ImportError:
    logger.warning("⚠️ ElementClassifier를 찾을 수 없습니다. 기본 분류 사용")
    ElementClassifier = None

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="PRISM POC",
    page_icon="🔷",
    layout="wide"
)


def init_session_state():
    """세션 상태 초기화"""
    if 'processed_results' not in st.session_state:
        st.session_state.processed_results = None
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = None
    if 'vlm_service' not in st.session_state:
        st.session_state.vlm_service = None
    if 'classifier' not in st.session_state:
        st.session_state.classifier = None


def display_header():
    """헤더 표시"""
    st.title("🔷 PRISM POC")
    st.markdown("**Progressive Reasoning & Intelligence for Structured Materials**")
    st.markdown("VLM 기반 문서 전처리 시스템 (OCR 통합)")
    st.divider()


def display_file_upload():
    """파일 업로드 UI"""
    st.subheader("📤 Step 1: 문서 업로드")
    
    file_type = st.radio(
        "파일 타입 선택",
        ["PDF 문서", "이미지 파일"],
        horizontal=True
    )
    
    if file_type == "PDF 문서":
        uploaded_file = st.file_uploader(
            "PDF 파일 선택",
            type=['pdf'],
            help="최대 10MB, 20페이지 이하"
        )
    else:
        uploaded_file = st.file_uploader(
            "이미지 파일 선택",
            type=['png', 'jpg', 'jpeg'],
            help="차트, 표, 다이어그램 이미지"
        )
    
    return uploaded_file, file_type


async def process_pdf_async(pdf_path: Path, use_ocr: bool = True):
    """PDF 비동기 처리"""
    
    # 초기화
    if st.session_state.pdf_processor is None:
        with st.spinner("🚀 PDF 프로세서 초기화 중..."):
            st.session_state.pdf_processor = PDFProcessor()
    
    if st.session_state.vlm_service is None:
        with st.spinner("🚀 VLM 서비스 초기화 중..."):
            st.session_state.vlm_service = VLMService()
    
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
            
            # 2) Element 타입 분류
            if classifier:
                try:
                    # ElementClassifier의 실제 메서드명 확인 필요
                    if hasattr(classifier, 'classify_element'):
                        element_type = classifier.classify_element(page_data['image'])
                    elif hasattr(classifier, 'classify'):
                        element_type = classifier.classify(page_data['image'])
                    else:
                        element_type = 'image'  # 기본값
                except Exception as e:
                    logger.warning(f"분류 실패: {e}")
                    element_type = 'image'
            else:
                element_type = 'image'
            
            # 3) VLM 캡션 생성
            vlm_result = await vlm_service.generate_caption(
                page_data['image_base64'],
                element_type,
                page_data.get('extracted_text', '')
            )
            
            # 결과 통합
            result = {
                'page_number': page_num,
                'element_type': element_type,
                'extracted_text': page_data.get('extracted_text', ''),
                'ocr_confidence': page_data.get('ocr_confidence', 0.0),
                'caption': vlm_result['caption'],
                'caption_confidence': vlm_result['confidence'],
                'image': page_data['image'],
                'usage': vlm_result['usage']
            }
            
            results.append(result)
            
            # 진행률 업데이트
            progress = page_num / page_count
            progress_bar.progress(progress)
            
        except Exception as e:
            logger.error(f"❌ 페이지 {page_num} 처리 실패: {e}")
            st.error(f"페이지 {page_num} 처리 실패: {e}")
    
    progress_bar.empty()
    status_text.empty()
    
    return results


def display_results(results: list):
    """결과 표시"""
    if not results:
        return
    
    st.success(f"✅ {len(results)}개 페이지 처리 완료!")
    
    # 요약 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 페이지", len(results))
    
    with col2:
        avg_ocr_conf = sum(r.get('ocr_confidence', 0) for r in results) / len(results)
        st.metric("평균 OCR 신뢰도", f"{avg_ocr_conf:.2f}")
    
    with col3:
        avg_caption_conf = sum(r.get('caption_confidence', 0) for r in results) / len(results)
        st.metric("평균 VLM 신뢰도", f"{avg_caption_conf:.2f}")
    
    with col4:
        total_tokens = sum(
            r.get('usage', {}).get('input_tokens', 0) + 
            r.get('usage', {}).get('output_tokens', 0)
            for r in results
        )
        st.metric("총 토큰", f"{total_tokens:,}")
    
    st.divider()
    
    # 페이지별 상세 결과
    st.subheader("📑 Step 3: 페이지별 결과")
    
    for result in results:
        page_num = result['page_number']
        element_type = result.get('element_type', 'unknown')
        
        # Element 타입 아이콘
        type_icons = {
            'chart': '📊',
            'table': '📋',
            'diagram': '🔷',
            'image': '🖼️'
        }
        icon = type_icons.get(element_type, '📄')
        
        with st.expander(
            f"{icon} Page {page_num} - {element_type.upper()} "
            f"(OCR: {result.get('ocr_confidence', 0):.2f}, "
            f"VLM: {result.get('caption_confidence', 0):.2f})"
        ):
            # 탭으로 구분
            tab1, tab2, tab3, tab4 = st.tabs([
                "📝 OCR 텍스트",
                "🎨 VLM 설명",
                "🖼️ 원본 이미지",
                "ℹ️ 메타데이터"
            ])
            
            with tab1:
                st.markdown("### 📝 OCR 추출 텍스트")
                extracted_text = result.get('extracted_text', '')
                
                if extracted_text:
                    st.text_area(
                        "추출된 텍스트",
                        extracted_text,
                        height=300,
                        key=f"ocr_{page_num}"
                    )
                    st.caption(f"📊 총 {len(extracted_text)}자 추출")
                else:
                    st.warning("⚠️ 추출된 텍스트가 없습니다.")
            
            with tab2:
                st.markdown("### 🎨 VLM 생성 설명")
                st.markdown(result.get('caption', 'N/A'))
                
                # 사용량 정보
                usage = result.get('usage', {})
                if usage:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"📥 Input: {usage.get('input_tokens', 0):,} tokens")
                    with col2:
                        st.caption(f"📤 Output: {usage.get('output_tokens', 0):,} tokens")
            
            with tab3:
                st.markdown("### 🖼️ 원본 이미지")
                if 'image' in result:
                    st.image(result['image'], use_container_width=True)
                else:
                    st.warning("이미지를 표시할 수 없습니다.")
            
            with tab4:
                st.markdown("### ℹ️ 메타데이터")
                metadata = {
                    "페이지 번호": page_num,
                    "Element 타입": element_type,
                    "OCR 신뢰도": f"{result.get('ocr_confidence', 0):.3f}",
                    "VLM 신뢰도": f"{result.get('caption_confidence', 0):.3f}",
                    "OCR 텍스트 길이": f"{len(result.get('extracted_text', ''))} 자",
                    "VLM 캡션 길이": f"{len(result.get('caption', ''))} 자",
                    "Input Tokens": f"{result.get('usage', {}).get('input_tokens', 0):,}",
                    "Output Tokens": f"{result.get('usage', {}).get('output_tokens', 0):,}"
                }
                st.json(metadata)
    
    st.divider()
    
    # 다운로드 버튼
    st.subheader("💾 결과 다운로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON 다운로드
        json_data = prepare_json_export(results)
        st.download_button(
            label="📥 JSON 다운로드",
            data=json_data,
            file_name=f"prism_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Markdown 다운로드
        markdown_data = prepare_markdown_export(results)
        st.download_button(
            label="📥 Markdown 다운로드",
            data=markdown_data,
            file_name=f"prism_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )


def prepare_json_export(results: list) -> str:
    """JSON 형식으로 결과 준비"""
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "total_pages": len(results),
            "version": "PRISM POC v1.0 (OCR)"
        },
        "summary": {
            "total_pages": len(results),
            "avg_ocr_confidence": sum(r.get('ocr_confidence', 0) for r in results) / len(results) if results else 0,
            "avg_vlm_confidence": sum(r.get('caption_confidence', 0) for r in results) / len(results) if results else 0,
            "total_tokens": sum(
                r.get('usage', {}).get('input_tokens', 0) + 
                r.get('usage', {}).get('output_tokens', 0)
                for r in results
            )
        },
        "pages": [
            {
                "page_number": r['page_number'],
                "element_type": r.get('element_type'),
                "extracted_text": r.get('extracted_text'),
                "ocr_confidence": r.get('ocr_confidence'),
                "caption": r.get('caption'),
                "caption_confidence": r.get('caption_confidence'),
                "usage": r.get('usage')
            }
            for r in results
        ]
    }
    
    return json.dumps(export_data, ensure_ascii=False, indent=2)


def prepare_markdown_export(results: list) -> str:
    """Markdown 형식으로 결과 준비"""
    md = f"""# PRISM POC 분석 결과 (OCR 통합)

**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**총 페이지**: {len(results)}  
**평균 OCR 신뢰도**: {sum(r.get('ocr_confidence', 0) for r in results) / len(results):.3f}  
**평균 VLM 신뢰도**: {sum(r.get('caption_confidence', 0) for r in results) / len(results):.3f}  

---

"""
    
    for result in results:
        page_num = result['page_number']
        element_type = result.get('element_type', 'unknown')
        
        md += f"""## 📄 Page {page_num} - {element_type.upper()}

### 📝 OCR 추출 텍스트

```
{result.get('extracted_text', 'N/A')}
```

### 🎨 VLM 생성 설명

{result.get('caption', 'N/A')}

**메타데이터**:
- OCR 신뢰도: {result.get('ocr_confidence', 0):.3f}
- VLM 신뢰도: {result.get('caption_confidence', 0):.3f}
- Input Tokens: {result.get('usage', {}).get('input_tokens', 0):,}
- Output Tokens: {result.get('usage', {}).get('output_tokens', 0):,}

---

"""
    
    return md


def main():
    """메인 함수"""
    init_session_state()
    display_header()
    
    # 파일 업로드
    uploaded_file, file_type = display_file_upload()
    
    if uploaded_file:
        # OCR 사용 여부
        use_ocr = st.checkbox(
            "📝 OCR 텍스트 추출 사용",
            value=True,
            help="PaddleOCR로 문서 텍스트를 추출합니다."
        )
        
        # 처리 시작 버튼
        if st.button("🚀 처리 시작", type="primary"):
            # 임시 파일 저장
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            file_path = temp_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                if file_type == "PDF 문서":
                    # PDF 처리
                    with st.spinner("📄 PDF 처리 중..."):
                        results = asyncio.run(
                            process_pdf_async(file_path, use_ocr)
                        )
                    
                    st.session_state.processed_results = results
                    display_results(results)
                
                else:
                    # 이미지 처리 (단일)
                    st.info("🖼️ 이미지 처리 기능은 곧 추가됩니다.")
            
            except Exception as e:
                st.error(f"❌ 처리 중 오류 발생: {e}")
                logger.exception("Processing failed")
            
            finally:
                # 임시 파일 삭제
                if file_path.exists():
                    file_path.unlink()
    
    # 이전 결과 표시
    elif st.session_state.processed_results:
        st.info("💡 이전 처리 결과를 표시하고 있습니다.")
        display_results(st.session_state.processed_results)


if __name__ == "__main__":
    main()
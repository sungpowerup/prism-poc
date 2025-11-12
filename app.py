"""
app.py - PRISM Final Version (GPT Feedback Applied)
GPT 6가지 핫픽스 반영
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import time
import json
import gc
import base64
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prism.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.hybrid_extractor import HybridExtractor
    from core.typo_normalizer_safe import TypoNormalizer
    from core.post_merge_normalizer_safe import PostMergeNormalizer
    from core.semantic_chunker import SemanticChunker
    
    logger.info("✅ 모듈 import 성공")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()


def image_to_base64(image_data):
    """이미지 데이터를 base64로 변환"""
    if isinstance(image_data, tuple):
        image_data = image_data[0]
    
    if isinstance(image_data, Image.Image):
        from io import BytesIO
        buffered = BytesIO()
        image_data.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    if isinstance(image_data, str):
        return image_data
    
    if isinstance(image_data, bytes):
        return base64.b64encode(image_data).decode()
    
    raise TypeError(f"지원하지 않는 이미지 타입: {type(image_data)}")


def process_pdf_direct(pdf_path, pdf_processor, vlm_service):
    """직접 PDF 처리"""
    
    # 1. PDF → 이미지 변환
    images = pdf_processor.pdf_to_images(pdf_path)
    logger.info(f"✅ {len(images)}개 페이지 추출")
    
    # 2. HybridExtractor 초기화
    extractor = HybridExtractor(vlm_service, pdf_path)
    logger.info(f"✅ HybridExtractor 초기화")
    
    # 3. 페이지별 처리
    all_markdown = []
    
    for page_num, image_data in enumerate(images, 1):
        logger.info(f"🔄 페이지 {page_num}/{len(images)} 처리 중...")
        
        try:
            image_b64 = image_to_base64(image_data)
            result = extractor.extract(image_b64, page_num)
            
            # GPT 피드백: 키는 'content'
            page_md = result.get('content', '').strip()
            
            if page_md:
                all_markdown.append(page_md)
                logger.info(f"   ✅ 페이지 {page_num}: {len(page_md)}자 추가")
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 실패: {e}", exc_info=True)
    
    # 페이지 병합
    markdown = "\n\n".join(all_markdown)
    logger.info(f"✅ 병합 완료: {len(markdown)}자 (페이지 {len(all_markdown)}개)")
    
    if len(markdown) < 100:
        raise ValueError(f"추출된 텍스트가 너무 짧습니다 ({len(markdown)}자)")
    
    # 4. 정규화
    normalizer = TypoNormalizer()
    markdown = normalizer.normalize(markdown)
    
    post_normalizer = PostMergeNormalizer()
    markdown = post_normalizer.normalize(markdown)
    logger.info(f"✅ 정규화 완료: {len(markdown)}자")
    
    # 5. 청킹
    chunker = SemanticChunker()
    chunks = chunker.chunk(markdown)
    logger.info(f"✅ {len(chunks)}개 청크 생성")
    
    # 6. GPT 피드백: 품질 점수 제거 (Golden File 미검증)
    checklist = None  # 품질 점수 없음
    
    return {
        'success': True,
        'markdown': markdown,
        'chunks': chunks,
        'checklist': checklist,
        'elapsed_time': 0
    }


def main():
    st.title("🔷 PRISM - 문서 처리 시스템")
    
    st.warning("""
    ⚠️ **Phase 0.3.4 P0 (실험용 PoC)**
    - Golden File 미검증 상태입니다
    - 품질 점수는 표시되지 않습니다
    """)
    
    try:
        pdf_processor = PDFProcessor()
        vlm_service = VLMServiceV50(provider="azure_openai")
        logger.info("✅ 초기화 완료")
    except Exception as e:
        st.error(f"❌ 초기화 실패: {e}")
        return
    
    uploaded_file = st.file_uploader("📄 PDF 파일 업로드", type=['pdf'])
    
    if uploaded_file:
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if 'last_file' not in st.session_state or st.session_state['last_file'] != file_key:
            with st.spinner("🔄 처리 중... (VLM 호출)"):
                temp_path = None
                try:
                    temp_path = Path(f"temp_{int(time.time())}_{uploaded_file.name}")
                    temp_path.write_bytes(uploaded_file.getvalue())
                    
                    result = process_pdf_direct(str(temp_path), pdf_processor, vlm_service)
                    
                    st.session_state['last_file'] = file_key
                    st.session_state['result'] = result
                    
                except Exception as e:
                    logger.error(f"❌ 처리 오류: {e}", exc_info=True)
                    st.error(f"❌ 오류: {e}")
                    st.session_state['result'] = None
                    
                finally:
                    gc.collect()
                    
                    # GPT 피드백: Windows 파일 락 재시도
                    if temp_path and temp_path.exists():
                        for attempt in range(3):
                            try:
                                time.sleep(0.2)
                                temp_path.unlink()
                                logger.info("✅ 임시 파일 삭제")
                                break
                            except PermissionError as e:
                                if attempt == 2:
                                    logger.warning(f"⚠️ 임시 파일 삭제 실패 (무시): {e}")
        
        result = st.session_state.get('result')
        
        if result and result.get('success'):
            st.success("✅ 처리 완료!")
            
            # GPT 피드백: 품질 점수 제거
            st.info("💡 품질 점수는 Golden File 연동 후 표시됩니다")
            
            # 결과
            markdown = result.get('markdown', '')
            chunks = result.get('chunks', [])
            
            if markdown:
                st.subheader("📝 Markdown 결과")
                preview = markdown[:1000]
                if len(markdown) > 1000:
                    preview += "\n\n... (생략)"
                # GPT 피드백: label 비어있음 경고 제거
                st.text_area(
                    "결과 미리보기",
                    preview,
                    height=300,
                    label_visibility="collapsed"
                )
            
            if chunks:
                st.subheader(f"✂️ 청크 결과 (총 {len(chunks)}개)")
                for i, chunk in enumerate(chunks[:3], 1):
                    with st.expander(f"청크 {i}"):
                        st.json(chunk.get('metadata', {}))
                        st.text(chunk.get('content', ''))
            
            # 다운로드
            st.subheader("📥 다운로드")
            col1, col2 = st.columns(2)
            
            with col1:
                if markdown:
                    st.download_button(
                        "📝 Markdown",
                        markdown,
                        f"{uploaded_file.name.replace('.pdf', '')}_markdown.md",
                        mime="text/markdown"
                    )
            
            with col2:
                if chunks:
                    chunks_json = json.dumps(chunks, ensure_ascii=False, indent=2)
                    st.download_button(
                        "📦 JSON",
                        chunks_json,
                        f"{uploaded_file.name.replace('.pdf', '')}_chunks.json",
                        mime="application/json"
                    )
        
        elif result is not None:
            st.error("❌ 처리 실패")


if __name__ == "__main__":
    main()
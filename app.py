"""
app.py - PRISM Phase 0.3.4 P2.4 최종 완성 버전
GPT 피드백 4가지 개선사항 100% 반영

✅ 개선 사항:
1. 경계 정밀도 강화 (SemanticChunker)
2. 파편 자동 병합 (200자 미만 청크)
3. OCR 오탈자 교정 확대 (13가지 도메인 패턴)
4. 안전 파일 삭제 (utils_fs.py 통합)

Author: 최동현 (Frontend Lead) + 마창수산팀
Date: 2025-11-12
Version: Phase 0.3.4 P2.4
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
from datetime import datetime

# ============================================
# 로깅 설정
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prism.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# 모듈 Import
# ============================================
try:
    from core.pdf_processor import PDFProcessor
    from core.vlm_service import VLMServiceV50
    from core.hybrid_extractor import HybridExtractor
    from core.typo_normalizer_safe import TypoNormalizer
    from core.post_merge_normalizer_safe import PostMergeNormalizer
    from core.semantic_chunker import SemanticChunker
    from core.utils_fs import safe_temp_path, safe_remove  # ✅ 신규 추가
    
    logger.info("✅ 모듈 import 성공 (Phase 0.3.4 P2.4)")
    
except Exception as e:
    logger.error(f"❌ Import 실패: {e}")
    st.error(f"❌ 모듈 로딩 실패: {e}")
    st.stop()


# ============================================
# 유틸리티 함수
# ============================================

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
    """
    PDF 직접 처리 (Phase 0.3.4 P2.4)
    
    플로우:
    1. PDF → 이미지 변환
    2. HybridExtractor로 페이지별 처리
    3. Markdown 병합
    4. 오탈자 정규화 (13가지 도메인 패턴)
    5. 후처리 정규화
    6. 의미 기반 청킹 (파편 병합)
    """
    
    # 1. PDF → 이미지 변환
    st.info("📄 PDF를 이미지로 변환 중...")
    images = pdf_processor.pdf_to_images(pdf_path)
    logger.info(f"✅ {len(images)}개 페이지 추출")
    st.success(f"✅ {len(images)}개 페이지 추출 완료")
    
    # 2. HybridExtractor 초기화
    extractor = HybridExtractor(vlm_service, pdf_path)
    logger.info(f"✅ HybridExtractor 초기화")
    
    # 3. 페이지별 처리
    st.info("🔄 VLM으로 페이지 처리 중...")
    progress_bar = st.progress(0)
    all_markdown = []
    
    for page_num, image_data in enumerate(images, 1):
        logger.info(f"🔄 페이지 {page_num}/{len(images)} 처리 중...")
        progress_bar.progress(page_num / len(images))
        
        try:
            image_b64 = image_to_base64(image_data)
            result = extractor.extract(image_b64, page_num)
            
            # 키는 'content' (GPT 피드백 반영)
            page_md = result.get('content', '').strip()
            
            if page_md:
                all_markdown.append(page_md)
                logger.info(f"   ✅ 페이지 {page_num}: {len(page_md)}자 추가")
            
        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 실패: {e}", exc_info=True)
            st.warning(f"⚠️ 페이지 {page_num} 처리 실패: {str(e)}")
    
    progress_bar.progress(1.0)
    
    # 페이지 병합
    markdown = "\n\n".join(all_markdown)
    logger.info(f"✅ 병합 완료: {len(markdown)}자 (페이지 {len(all_markdown)}개)")
    st.success(f"✅ Markdown 추출: {len(markdown):,}자")
    
    if len(markdown) < 100:
        raise ValueError(f"추출된 텍스트가 너무 짧습니다 ({len(markdown)}자)")
    
    # 4. 오탈자 정규화 (13가지 도메인 패턴)
    st.info("🔧 오탈자 정규화 중...")
    normalizer = TypoNormalizer()
    normalized_md = normalizer.normalize(markdown)
    logger.info(f"✅ 정규화 완료: {len(normalized_md)}자")
    st.success(f"✅ 오탈자 교정 완료")
    
    # 5. 후처리 정규화
    post_normalizer = PostMergeNormalizer()
    final_md = post_normalizer.normalize(normalized_md)
    logger.info(f"✅ 후처리 완료: {len(final_md)}자")
    
    # 6. 의미 기반 청킹 (파편 병합 적용)
    st.info("✂️ 의미 기반 청킹 중...")
    chunker = SemanticChunker()
    chunks = chunker.chunk(final_md)
    logger.info(f"✅ 청킹 완료: {len(chunks)}개")
    st.success(f"✅ 청킹 완료: {len(chunks)}개")
    
    return {
        'markdown': final_md,
        'chunks': chunks,
        'metadata': {
            'total_pages': len(images),
            'total_chars': len(final_md),
            'total_chunks': len(chunks),
            'processing_time': datetime.now().isoformat()
        }
    }


# ============================================
# Streamlit UI
# ============================================

def main():
    """메인 UI"""
    
    # 페이지 설정
    st.set_page_config(
        page_title="PRISM Phase 0.3.4 P2.4",
        page_icon="🔷",
        layout="wide"
    )
    
    # 헤더
    st.title("🔷 PRISM Phase 0.3.4 P2.4")
    st.caption("차세대 지능형 문서 이해 플랫폼 - 최종 완성 버전")
    
    st.markdown("---")
    
    # 사이드바 - 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.subheader("📊 버전 정보")
        st.info("""
**Phase 0.3.4 P2.4**
- ✅ 경계 정밀도 강화
- ✅ 파편 자동 병합
- ✅ OCR 오탈자 교정 확대
- ✅ 안전 파일 삭제
        """)
        
        st.markdown("---")
        
        st.subheader("🔧 VLM 설정")
        provider = st.selectbox(
            "VLM Provider",
            ["azure_openai"],
            index=0
        )
        
        max_pages = st.slider(
            "최대 처리 페이지",
            min_value=1,
            max_value=20,
            value=20,
            help="한 번에 처리할 최대 페이지 수"
        )
        
        st.markdown("---")
        
        st.subheader("📖 사용 방법")
        st.markdown("""
1. PDF 파일 업로드 (최대 10MB)
2. '처리 시작' 버튼 클릭
3. 결과 확인 및 다운로드
        """)
    
    # 메인 영역
    st.header("📄 PDF 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 10MB, 20페이지까지 지원"
    )
    
    if uploaded_file is not None:
        # 파일 정보 표시
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📁 파일명: {uploaded_file.name} ({file_size:.2f} MB)")
        
        # 파일 크기 체크
        if file_size > 10:
            st.error("❌ 파일 크기가 10MB를 초과합니다!")
            return
        
        # 처리 시작 버튼
        if st.button("🚀 처리 시작", type="primary"):
            
            # ✅ 안전한 임시 파일 생성
            pdf_path = safe_temp_path(".pdf")
            
            try:
                # 임시 파일 저장
                with open(pdf_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                logger.info(f"✅ 임시 파일 저장: {pdf_path}")
                
                # 서비스 초기화
                with st.spinner("🔧 서비스 초기화 중..."):
                    pdf_processor = PDFProcessor()
                    vlm_service = VLMServiceV50(provider=provider)
                    logger.info("✅ 서비스 초기화 완료")
                
                # PDF 처리
                start_time = time.time()
                
                with st.spinner("🔄 PDF 처리 중..."):
                    result = process_pdf_direct(pdf_path, pdf_processor, vlm_service)
                
                processing_time = time.time() - start_time
                
                # 성공 메시지
                st.success(f"✅ 처리 완료! ({processing_time:.1f}초)")
                
                # 결과 표시
                st.markdown("---")
                st.header("📊 처리 결과")
                
                # 메타데이터
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("총 페이지", result['metadata']['total_pages'])
                
                with col2:
                    st.metric("추출 문자", f"{result['metadata']['total_chars']:,}자")
                
                with col3:
                    st.metric("생성 청크", result['metadata']['total_chunks'])
                
                with col4:
                    st.metric("처리 시간", f"{processing_time:.1f}초")
                
                # 탭으로 결과 구분
                tab1, tab2, tab3 = st.tabs(["📝 Markdown", "✂️ 청크", "📊 청크 분석"])
                
                with tab1:
                    st.subheader("추출된 Markdown")
                    st.text_area(
                        "Markdown 내용",
                        result['markdown'],
                        height=400,
                        key="markdown_display"
                    )
                    
                    # Markdown 다운로드
                    st.download_button(
                        label="📥 Markdown 다운로드",
                        data=result['markdown'],
                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_markdown.md",
                        mime="text/markdown"
                    )
                
                with tab2:
                    st.subheader(f"생성된 청크 ({len(result['chunks'])}개)")
                    
                    for i, chunk in enumerate(result['chunks'], 1):
                        with st.expander(f"청크 {i} - {chunk['metadata']['type']} ({chunk['metadata']['char_count']}자)"):
                            st.markdown(f"**경계:** `{chunk['metadata']['boundary']}`")
                            if chunk['metadata'].get('title'):
                                st.markdown(f"**제목:** {chunk['metadata']['title']}")
                            st.text_area(
                                "내용",
                                chunk['content'],
                                height=200,
                                key=f"chunk_{i}"
                            )
                    
                    # 청크 JSON 다운로드
                    chunks_json = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📥 청크 JSON 다운로드",
                        data=chunks_json,
                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_chunks.json",
                        mime="application/json"
                    )
                
                with tab3:
                    st.subheader("청크 품질 분석")
                    
                    # 타입별 분포
                    type_counts = {}
                    for chunk in result['chunks']:
                        chunk_type = chunk['metadata']['type']
                        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
                    
                    st.markdown("**타입별 분포**")
                    for chunk_type, count in type_counts.items():
                        percentage = (count / len(result['chunks'])) * 100
                        st.progress(percentage / 100, text=f"{chunk_type}: {count}개 ({percentage:.1f}%)")
                    
                    # 크기 분포
                    st.markdown("---")
                    st.markdown("**크기 분포**")
                    
                    size_ranges = {
                        "50~150자": 0,
                        "150~300자": 0,
                        "300~600자": 0,
                        "600자 이상": 0
                    }
                    
                    for chunk in result['chunks']:
                        size = chunk['metadata']['char_count']
                        if size < 150:
                            size_ranges["50~150자"] += 1
                        elif size < 300:
                            size_ranges["150~300자"] += 1
                        elif size < 600:
                            size_ranges["300~600자"] += 1
                        else:
                            size_ranges["600자 이상"] += 1
                    
                    for range_name, count in size_ranges.items():
                        percentage = (count / len(result['chunks'])) * 100
                        st.progress(percentage / 100, text=f"{range_name}: {count}개 ({percentage:.1f}%)")
                    
                    # 평균 크기
                    avg_size = sum(c['metadata']['char_count'] for c in result['chunks']) / len(result['chunks'])
                    st.metric("평균 청크 크기", f"{avg_size:.0f}자")
                
            except Exception as e:
                logger.error(f"❌ 처리 실패: {e}", exc_info=True)
                st.error(f"❌ 처리 중 오류 발생: {str(e)}")
            
            finally:
                # ✅ 안전한 파일 삭제
                safe_remove(pdf_path)
                gc.collect()
    
    else:
        st.info("👆 PDF 파일을 업로드하여 시작하세요")
        
        # 샘플 결과 표시
        st.markdown("---")
        st.header("📖 Phase 0.3.4 P2.4 주요 개선사항")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 경계 정밀도 강화")
            st.code("""
# Before
'제28조제2항' → 경계로 오인 ❌

# After  
'제28조제2항' → 조문 참조로 인식 ✅
            """, language="python")
            
            st.subheader("🧩 파편 자동 병합")
            st.code("""
# Before
18개 청크 (50~150자: 8개)

# After
12~14개 청크 (200~600자 집중)
            """, language="python")
        
        with col2:
            st.subheader("🔧 OCR 오탈자 교정")
            st.code("""
# 13가지 도메인 패턴 추가
- "기 본 정 신" → "기본정신"
- "용상" → "통상"
- "전족" → "전속"
- "해파군직채용" → "예비군지휘관"
            """, language="python")
            
            st.subheader("🔒 안전 파일 삭제")
            st.code("""
# Before
WinError 32 발생 ❌

# After
재시도 + GC → 안전 삭제 ✅
            """, language="python")
    
    # 푸터
    st.markdown("---")
    st.caption("🔷 PRISM Phase 0.3.4 P2.4 | Developed by 마창수산팀")


if __name__ == "__main__":
    main()
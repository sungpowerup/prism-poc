"""
app.py - PRISM Phase 0.3.4 P2.5.3 최종 완성 (상용 배포 버전)
GPT 피드백 100% 반영 + 마창수산팀 주도 설계

✅ 개선 사항:
1. 제4조 누락 방지 (헤더 절대 보호 + 자동 QA)
2. OCR 오탈자 23개 패턴 (유연한 정규식)
3. 리뷰용 파일 생성 (*_review.md)
4. 정규식 경고 완전 제거 (raw string)
5. 세션 상태 관리 + UUID 캐시 무효화

Author: 마창수산팀 (최동현 Frontend Lead) + GPT 보정
Date: 2025-11-13
Version: Phase 0.3.4 P2.5.3 (Production Ready)
"""

import streamlit as st
import logging
import sys
from pathlib import Path
import time
import json
import gc
import base64
import uuid
import re
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
    from core.utils_fs import safe_temp_path, safe_remove
    
    logger.info("✅ 모듈 import 성공 (Phase 0.3.4 P2.5.3)")
    
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


def to_review_md(chunks: list, markdown: str) -> str:
    """
    ✅ GPT 피드백: 리뷰용 Markdown 생성
    
    목적: 사람이 읽기 좋은 형식으로 변환
    - 조문마다 ### 헤더
    - 항목(①②) 앞에 줄바꿈
    - 80자 소프트 래핑
    """
    lines = []
    
    # 개정 이력 (상단에 유지)
    if '제37차 개정' in markdown or '제정' in markdown:
        header_end = markdown.find('기본정신')
        if header_end > 0:
            header = markdown[:header_end].strip()
            lines.append("# 인사규정")
            lines.append("")
            lines.append("## 개정 이력")
            lines.append(header)
            lines.append("")
    
    for ch in chunks:
        # ✅ None 처리 추가
        t = ch["metadata"].get("title") or ""
        t = t.strip() if t else ""
        
        b = ch["metadata"].get("boundary") or ""
        b = b.strip() if b else ""
        
        btype = ch["metadata"].get("type", "")
        
        # 헤더 생성
        if btype == 'chapter':
            head = f"## {b}"
        elif btype == 'basic':
            head = "## 기본정신"
        elif b:
            if t:
                head = f"### {b}{t})"
            else:
                head = f"### {b}"
        else:
            head = "### 내용"
        
        # 본문 처리
        body = ch.get("content", "")
        body = body.strip() if body else ""
        
        # ✅ 항목 줄바꿈 보정
        body = re.sub(r'\s*(①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩)', r'\n\1', body)
        body = re.sub(r'\s*(?=^\d+\.)', r'\n', body, flags=re.M)
        
        lines += [head, "", body, ""]
    
    return "\n".join(lines).strip()


def process_pdf_direct(pdf_path, pdf_processor, vlm_service):
    """
    PDF 직접 처리 (Phase 0.3.4 P2.5.3)
    
    플로우:
    1. PDF → 이미지 변환
    2. HybridExtractor로 페이지별 처리
    3. Markdown 병합
    4. 오탈자 정규화 (33가지 패턴)
    5. 후처리 정규화
    6. 의미 기반 청킹 (제4조 누락 방지 + 자동 QA)
    """
    
    # 1. PDF → 이미지 변환
    st.info("📄 PDF를 이미지로 변환 중...")
    images = pdf_processor.pdf_to_images(pdf_path)
    logger.info(f"✅ {len(images)}개 페이지 추출")
    st.success(f"✅ {len(images)}개 페이지 추출 완료")
    
    # 2. HybridExtractor 초기화
    extractor = HybridExtractor(vlm_service, pdf_path)
    logger.info(f"✅ HybridExtractor 초기화")
    
    # 3. 페이지별 추출 및 병합
    st.info(f"🔍 {len(images)}개 페이지 추출 중...")
    
    markdown_parts = []
    progress_bar = st.progress(0)
    
    for idx, image_data in enumerate(images, 1):
        try:
            # 이미지 → Base64
            if not isinstance(image_data, str):
                image_base64 = image_to_base64(image_data)
            else:
                image_base64 = image_data
            
            # 페이지 추출
            page_result = extractor.extract(image_base64, idx)
            
            # Markdown 병합
            if page_result and 'content' in page_result:
                markdown_parts.append(page_result['content'])
                logger.info(f"   ✅ 페이지 {idx}: {len(page_result['content'])}자")
            else:
                logger.warning(f"   ⚠️ 페이지 {idx}: 내용 없음")
            
            # 진행률 업데이트
            progress_bar.progress(idx / len(images))
            
        except Exception as e:
            logger.error(f"   ❌ 페이지 {idx} 오류: {e}")
            st.warning(f"⚠️ 페이지 {idx} 처리 실패: {str(e)}")
    
    progress_bar.empty()
    
    # Markdown 병합
    markdown = '\n\n'.join(markdown_parts)
    logger.info(f"✅ Markdown 병합 완료: {len(markdown)}자")
    st.success(f"✅ 추출 완료: {len(markdown):,}자")
    
    # 4. 오탈자 정규화 (33가지 패턴)
    st.info("🔧 오탈자 정규화 중...")
    normalizer = TypoNormalizer()
    normalized_md = normalizer.normalize(markdown)
    logger.info(f"✅ 정규화 완료: {len(normalized_md)}자")
    st.success(f"✅ 오탈자 교정 완료")
    
    # 5. 후처리 정규화
    post_normalizer = PostMergeNormalizer()
    final_md = post_normalizer.normalize(normalized_md)
    logger.info(f"✅ 후처리 완료: {len(final_md)}자")
    
    # 6. 의미 기반 청킹 (제4조 누락 방지 + 자동 QA)
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
        page_title="PRISM Phase 0.3.4 P2.5.3",
        page_icon="🔷",
        layout="wide"
    )
    
    # ✅ 세션 상태 초기화
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    if 'last_filename' not in st.session_state:
        st.session_state.last_filename = None
    
    # 헤더
    st.title("🔷 PRISM Phase 0.3.4 P2.5.3")
    st.caption("차세대 지능형 문서 이해 플랫폼 - 최종 완성 (상용 배포 버전)")
    
    st.markdown("---")
    
    # 사이드바 - 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.subheader("📊 버전 정보")
        st.info("""
**Phase 0.3.4 P2.5.3 (Production Ready)**
- ✅ 제4조 누락 방지 (헤더 절대 보호)
- ✅ OCR 오탈자 23개 패턴
- ✅ 리뷰용 파일 생성 (사람 눈 친화)
- ✅ 자동 QA 게이트 (누락 조문 감지)
- ✅ 정규식 경고 완전 제거

**GPT 보정 + 마창수산팀 주도 설계**
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
   - RAG용: Markdown + JSON
   - 검수용: Review Markdown
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
            
            # 안전한 임시 파일 생성
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
                
                # ✅ 세션 상태에 결과 저장
                st.session_state.last_result = result
                st.session_state.last_filename = uploaded_file.name
                
                # 성공 메시지
                st.success(f"✅ 처리 완료! ({processing_time:.1f}초)")
                
            except Exception as e:
                logger.error(f"❌ 처리 실패: {e}", exc_info=True)
                st.error(f"❌ 처리 중 오류 발생: {str(e)}")
            
            finally:
                # 안전한 파일 삭제
                safe_remove(pdf_path)
                gc.collect()
    
    # ✅ 결과 표시 (세션 상태에서)
    if st.session_state.last_result is not None:
        result = st.session_state.last_result
        filename = st.session_state.last_filename
        base_name = filename.replace('.pdf', '')
        
        # 결과 표시
        st.markdown("---")
        st.header("📊 처리 결과")
        
        # 메타데이터
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 페이지", result['metadata']['total_pages'])
        
        with col2:
            st.metric("추출 문자", f"{result['metadata']['total_chars']:,}자")
        
        with col3:
            st.metric("생성 청크", result['metadata']['total_chunks'])
        
        # 탭으로 결과 구분
        tab1, tab2, tab3, tab4 = st.tabs(["📝 RAG Markdown", "✂️ 청크 JSON", "📄 리뷰용 MD", "📊 분석"])
        
        with tab1:
            st.subheader("RAG용 Markdown (임베딩 최적화)")
            st.text_area(
                "Markdown 내용",
                result['markdown'],
                height=400,
                key="markdown_display"
            )
            
            # ✅ UUID로 캐시 무효화
            download_id = uuid.uuid4().hex[:8]
            st.download_button(
                label="📥 RAG용 Markdown 다운로드",
                data=result['markdown'],
                file_name=f"{base_name}_{download_id}.md",
                mime="text/markdown",
                key=f"md_download_{download_id}"
            )
        
        with tab2:
            st.subheader(f"청크 JSON ({len(result['chunks'])}개)")
            
            # 청크 미리보기
            for i, chunk in enumerate(result['chunks'][:3], 1):
                with st.expander(f"청크 {i} 미리보기 - {chunk['metadata']['type']} ({chunk['metadata']['char_count']}자)"):
                    st.markdown(f"**경계:** `{chunk['metadata']['boundary']}`")
                    if chunk['metadata'].get('title'):
                        st.markdown(f"**제목:** {chunk['metadata']['title']}")
                    st.text_area(
                        "내용",
                        chunk['content'][:200] + "...",
                        height=100,
                        key=f"chunk_preview_{i}"
                    )
            
            if len(result['chunks']) > 3:
                st.info(f"💡 전체 {len(result['chunks'])}개 청크는 JSON 파일에서 확인하세요")
            
            # ✅ UUID로 캐시 무효화
            chunks_json = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
            download_id = uuid.uuid4().hex[:8]
            st.download_button(
                label="📥 청크 JSON 다운로드",
                data=chunks_json,
                file_name=f"{base_name}_{download_id}.json",
                mime="application/json",
                key=f"json_download_{download_id}"
            )
        
        with tab3:
            st.subheader("📄 리뷰용 Markdown (사람 눈 친화)")
            st.info("✅ 조문마다 헤더 + 항목 줄바꿈 + 읽기 좋은 형식")
            
            # ✅ GPT 피드백: 리뷰용 파일 생성
            review_md = to_review_md(result['chunks'], result['markdown'])
            
            st.text_area(
                "리뷰용 내용",
                review_md[:1000] + "\n\n... (하단 생략, 전체는 다운로드에서 확인)",
                height=400,
                key="review_display"
            )
            
            # ✅ UUID로 캐시 무효화
            download_id = uuid.uuid4().hex[:8]
            st.download_button(
                label="📥 리뷰용 Markdown 다운로드",
                data=review_md,
                file_name=f"{base_name}_review_{download_id}.md",
                mime="text/markdown",
                key=f"review_download_{download_id}"
            )
        
        with tab4:
            st.subheader("📊 청크 품질 분석")
            
            # 타입별 분포
            type_counts = {}
            for chunk in result['chunks']:
                chunk_type = chunk['metadata']['type']
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            
            st.markdown("### 타입별 분포")
            for chunk_type, count in sorted(type_counts.items()):
                percentage = (count / len(result['chunks'])) * 100
                st.markdown(f"- **{chunk_type}**: {count}개 ({percentage:.1f}%)")
            
            # 크기 분석
            sizes = [c['metadata']['char_count'] for c in result['chunks']]
            if sizes:
                st.markdown("### 크기 분석")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    avg_size = sum(sizes) / len(sizes)
                    st.metric("평균 청크 크기", f"{avg_size:.0f}자")
                
                with col2:
                    st.metric("최소 크기", f"{min(sizes)}자")
                
                with col3:
                    st.metric("최대 크기", f"{max(sizes)}자")
            
            # ✅ 조문 헤더 목록
            st.markdown("### 감지된 조문 헤더")
            headers = []
            for chunk in result['chunks']:
                boundary = chunk['metadata'].get('boundary', '')
                if boundary and ('조' in boundary or '장' in boundary):
                    headers.append(boundary)
            
            if headers:
                st.markdown(", ".join(headers))
            else:
                st.warning("조문 헤더를 감지하지 못했습니다")
    
    else:
        st.info("👆 PDF 파일을 업로드하여 시작하세요")
        
        # 샘플 결과 표시
        st.markdown("---")
        st.header("📖 Phase 0.3.4 P2.5.3 주요 개선사항")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 제4조 누락 방지")
            st.code("""
# Before
제4조(임용권) → JSON에서 누락 ❌

# After (GPT 보정)
헤더 절대 보호:
- 50자 미만 조문도 헤더로 간주
- 병합 시 양쪽 모두 헤더 아니어야 병합
- 자동 QA: MD vs JSON 헤더 비교

→ 제4조 완전 보존 ✅
            """, language="python")
            
            st.subheader("🔧 OCR 오탈자 23개")
            st.code(r"""
# 유연한 정규식 (실측 기반)
채\s*채\s*규정 → 채용규정
인턴\s*채\s*통상 → 인턴·통상
설\s*차\s*적 → 절차적
직원\s*방식\s*절차 → 직권면직
... 외 19개
            """, language="python")
        
        with col2:
            st.subheader("📄 리뷰용 파일 생성")
            st.code("""
# RAG용 (AI 최적화)
제1조(목적) 이 규정은...

# 리뷰용 (사람 눈 친화)
### 제1조(목적)

이 규정은 한국농어촌공사 직원에게
적용할 인사관리의 기준을 정하여...

① 제1항
② 제2항
            """, language="markdown")
            
            st.subheader("🔍 자동 QA 게이트")
            st.code("""
# 누락 조문 자동 감지
MD 헤더: {제1조, 제2조, ..., 제92조}
JSON 헤더: {제1조, 제2조, ..., 제92조}

⚠️ 누락: 없음
✅ QA 통과
            """, language="python")
    
    # 푸터
    st.markdown("---")
    st.caption("🔷 PRISM Phase 0.3.4 P2.5.3 (상용 배포 버전) | 마창수산팀 + GPT 보정")


if __name__ == "__main__":
    main()
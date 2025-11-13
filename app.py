"""
app.py - PRISM Phase 0.4.0 P0-3 완전판
GPT 피드백 100% 반영 + DualQA 통합

✅ Phase 0.4.0 P0-3 개선 사항:
1. QA 헤더 추출 정교화 (인라인 참조 노이즈 제거)
2. DualQAGate 이중 검증 (PDF vs VLM)
3. 관찰 모드 (하드 fail 금지)
4. UI에 QA 경고 표시

Author: 마창수산팀 + GPT 보정
Date: 2025-11-13
Version: Phase 0.4.0 P0-3
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
    from core.dual_qa_gate import DualQAGate, extract_pdf_text_layer
    from core.utils_fs import safe_temp_path, safe_remove
    
    logger.info("✅ 모듈 import 성공 (Phase 0.4.0 P0-3)")
    
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
    리뷰용 Markdown 생성 (사람이 읽기 좋은 형식)
    """
    lines = []
    
    # 개정 이력 (상단에 유지)
    if '제37차' in markdown or '개정' in markdown[:200]:
        first_section = markdown.split('\n\n')[0]
        lines.append("# 인사규정\n")
        lines.append("## 개정 이력")
        lines.append(first_section + "\n")
    
    # 청크별 변환
    for chunk in chunks:
        content = chunk['content']
        chunk_type = chunk['metadata']['type']
        title = chunk['metadata'].get('title')
        
        # 기본정신
        if chunk_type == 'basic':
            lines.append("\n## 기본정신\n")
            lines.append(content.replace('기본정신', '', 1).strip())
        
        # 장
        elif chunk_type == 'chapter':
            chapter_match = re.search(r'제\s*\d+\s*장', content)
            if chapter_match:
                lines.append(f"\n## {chapter_match.group()}\n")
                rest = content[chapter_match.end():].strip()
                if rest:
                    lines.append(rest)
        
        # 조문
        elif chunk_type in ['article', 'article_loose']:
            header_match = re.search(r'(제\s*\d+조(?:의\d+)?)\s*\(([^)]+)\)', content)
            if header_match:
                article_num = header_match.group(1)
                article_title = header_match.group(2)
                lines.append(f"\n### {article_num}({article_title})\n")
                
                # 본문 (항목 앞에 줄바꿈)
                rest = content[header_match.end():].strip()
                rest = re.sub(r'([。\.])(\s*)(①)', r'\1\n\3', rest)
                rest = re.sub(r'([。\.])(\s*)(②)', r'\1\n\3', rest)
                rest = re.sub(r'([。\.])(\s*)(③)', r'\1\n\3', rest)
                rest = re.sub(r'([。\.])(\s*)(④)', r'\1\n\3', rest)
                
                lines.append(rest)
            else:
                lines.append(f"\n### {content[:30]}...\n")
                lines.append(content)
    
    return '\n'.join(lines)


# ============================================
# 문서 처리 파이프라인
# ============================================

def process_document(pdf_path: str, max_pages: int = 20, provider: str = 'azure_openai'):
    """
    문서 처리 파이프라인
    
    ✅ Phase 0.4.0 P0-3: DualQA 통합
    """
    
    # 0. DualQA 준비: PDF 텍스트 레이어 추출
    st.info("📄 PDF 원본 텍스트 추출 중...")
    pdf_text = extract_pdf_text_layer(pdf_path)
    logger.info(f"✅ PDF 텍스트 추출 완료: {len(pdf_text)}자")
    
    # 1. PDF 처리
    st.info("📄 PDF 이미지 변환 중...")
    pdf_processor = PDFProcessor()
    images = pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages)
    logger.info(f"✅ {len(images)}개 페이지 추출")
    st.success(f"✅ {len(images)}개 페이지 변환 완료")
    
    # 2. VLM 초기화
    vlm_service = VLMServiceV50(provider=provider)
    logger.info("✅ 서비스 초기화 완료")
    
    # 3. Hybrid 추출 (페이지별 처리)
    st.info("🤖 VLM 기반 추출 중...")
    extractor = HybridExtractor(
        vlm_service=vlm_service,
        pdf_path=pdf_path
    )
    logger.info("✅ HybridExtractor 초기화")
    
    # 페이지별 추출
    all_pages = []
    for i, image_item in enumerate(images, 1):
        # 디버깅: 타입 확인
        logger.info(f"   🔍 Page {i} image type: {type(image_item)}")
        
        # 여러 케이스 처리
        if isinstance(image_item, tuple):
            # Case 1: (image_data, metadata) 튜플
            image_data = image_item[0]
            logger.info(f"   📦 튜플에서 이미지 추출 (요소 타입: {type(image_data)})")
        elif isinstance(image_item, dict):
            # Case 2: {'image': ..., 'metadata': ...} 딕셔너리
            image_data = image_item.get('image', image_item)
            logger.info(f"   📦 딕셔너리에서 이미지 추출")
        else:
            # Case 3: 직접 이미지 데이터
            image_data = image_item
            logger.info(f"   📦 직접 이미지 사용")
        
        # 최종 확인: 여전히 튜플이면 재귀적으로 추출
        while isinstance(image_data, tuple):
            logger.warning(f"   ⚠️ 중첩 튜플 감지! 재귀 추출")
            image_data = image_data[0]
        
        logger.info(f"   ✅ 최종 image_data 타입: {type(image_data)}")
        
        page_result = extractor.extract(image_data, page_num=i)
        all_pages.append(page_result)
        
        st.info(f"   ✅ 페이지 {i}: {len(page_result['content'])}자")
        logger.info(f"   ✅ 페이지 {i}: {len(page_result['content'])}자")
    
    # Markdown 병합
    markdown = '\n\n'.join([p['content'] for p in all_pages])
    logger.info(f"✅ Markdown 병합 완료: {len(markdown)}자")
    st.success(f"✅ VLM 추출 완료: {len(markdown)}자")
    
    # 4. 오탈자 정규화
    st.info("🔧 오탈자 정규화 중...")
    normalizer = TypoNormalizer()
    normalized_md = normalizer.normalize(markdown)
    logger.info(f"✅ 정규화 완료: {len(normalized_md)}자")
    st.success(f"✅ 오탈자 교정 완료")
    
    # 5. 후처리 정규화
    post_normalizer = PostMergeNormalizer()
    final_md = post_normalizer.normalize(normalized_md)
    logger.info(f"✅ 후처리 완료: {len(final_md)}자")
    
    # 6. 의미 기반 청킹
    st.info("✂️ 의미 기반 청킹 중...")
    chunker = SemanticChunker()
    chunks = chunker.chunk(final_md)
    logger.info(f"✅ 청킹 완료: {len(chunks)}개")
    st.success(f"✅ 청킹 완료: {len(chunks)}개")
    
    # ✅ 7. DualQA 검증 (Phase 0.4.0 P0-3 신규)
    st.info("🔬 DualQA 이중 검증 중...")
    dual_qa = DualQAGate()
    qa_result = dual_qa.validate(pdf_text, final_md)
    logger.info("✅ DualQA 검증 완료")
    
    # QA 결과 UI 표시
    if qa_result['qa_flags']:
        st.warning(f"⚠️ QA 경고: {', '.join(qa_result['qa_flags'])}")
        
        with st.expander("🔬 DualQA 상세 결과"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("PDF 조문", qa_result['pdf_count'])
            with col2:
                st.metric("VLM 조문", qa_result['vlm_count'])
            with col3:
                st.metric("매칭률", f"{qa_result['match_rate']:.1%}")
            
            if qa_result['missing_in_vlm']:
                st.error(f"❌ VLM 누락: {qa_result['missing_in_vlm']}")
            
            if qa_result['extra_in_vlm']:
                st.warning(f"⚠️ VLM 추가: {qa_result['extra_in_vlm']}")
    else:
        st.success("✅ DualQA 검증 통과 (원본과 일치)")
    
    return {
        'markdown': final_md,
        'chunks': chunks,
        'qa_result': qa_result,
        'metadata': {
            'total_pages': len(images),
            'total_chars': len(final_md),
            'total_chunks': len(chunks),
            'processing_time': datetime.now().isoformat(),
            'qa_flags': qa_result['qa_flags']
        }
    }


# ============================================
# Streamlit UI
# ============================================

def main():
    """메인 UI"""
    
    # 페이지 설정
    st.set_page_config(
        page_title="PRISM Phase 0.4.0 P0-3",
        page_icon="🔷",
        layout="wide"
    )
    
    # 세션 상태 초기화
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    if 'last_filename' not in st.session_state:
        st.session_state.last_filename = None
    
    # 헤더
    st.title("🔷 PRISM Phase 0.4.0 P0-3")
    st.caption("차세대 지능형 문서 이해 플랫폼 - DualQA 완전판")
    
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.subheader("📊 버전 정보")
        st.info("""
**Phase 0.4.0 P0-3 (QA-Stable)**

✅ **P0-3a: QA 헤더 정교화**
- 인라인 참조 노이즈 제거
- 청킹 경계 패턴 통합

✅ **P0-3b: DualQA 이중 검증**
- PDF 원본 vs VLM 결과
- 관찰 모드 (하드 fail 금지)
- 원문 불일치 자동 감지

**GPT 피드백 100% 반영**
**마창수산팀 주도 설계**
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
            value=20
        )
        
        st.markdown("---")
        
        st.subheader("📖 사용 방법")
        st.markdown("""
1. PDF 파일 업로드
2. '처리 시작' 버튼 클릭
3. DualQA 검증 결과 확인
4. 결과 다운로드
        """)
    
    # 메인 영역
    st.header("📄 PDF 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="최대 10MB, 20페이지까지 지원"
    )
    
    if uploaded_file is not None:
        # 파일 정보
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📁 파일명: {uploaded_file.name} ({file_size:.2f} MB)")
        
        if file_size > 10:
            st.error("❌ 파일 크기가 10MB를 초과합니다!")
            return
        
        # 처리 버튼
        if st.button("🚀 처리 시작", type="primary"):
            # 캐시 무효화
            file_id = f"{uploaded_file.name}_{uuid.uuid4().hex[:8]}"
            
            # 임시 파일 저장
            pdf_path = safe_temp_path(".pdf")
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            logger.info(f"✅ 임시 파일 저장: {pdf_path}")
            
            try:
                # 진행 표시
                with st.spinner("⏳ 문서 처리 중... (최대 2분 소요)"):
                    start_time = time.time()
                    
                    # 처리 실행
                    result = process_document(
                        pdf_path=pdf_path,
                        max_pages=max_pages,
                        provider=provider
                    )
                    
                    elapsed = time.time() - start_time
                    logger.info(f"✅ 처리 완료: {elapsed:.1f}초")
                
                # 세션 상태 저장
                st.session_state.last_result = result
                st.session_state.last_filename = uploaded_file.name
                
                st.success(f"✅ 처리 완료! ({elapsed:.1f}초)")
                
            except Exception as e:
                logger.error(f"❌ 처리 실패: {e}", exc_info=True)
                st.error(f"❌ 처리 실패: {str(e)}")
                
            finally:
                # 임시 파일 삭제
                safe_remove(pdf_path)
                gc.collect()
    
    # 결과 표시
    if st.session_state.last_result is not None:
        st.markdown("---")
        st.header("📊 처리 결과")
        
        result = st.session_state.last_result
        filename = st.session_state.last_filename
        
        # 메타데이터
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("전체 문자", f"{result['metadata']['total_chars']:,}")
        with col2:
            st.metric("청크 개수", result['metadata']['total_chunks'])
        with col3:
            qa_status = "⚠️ 경고" if result['metadata']['qa_flags'] else "✅ 통과"
            st.metric("QA 상태", qa_status)
        
        # 탭
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Markdown",
            "📦 JSON",
            "📖 Review",
            "🔬 QA 상세"
        ])
        
        with tab1:
            st.text_area(
                "Markdown 결과",
                result['markdown'],
                height=400
            )
            
            # 다운로드
            filename_base = Path(filename).stem
            st.download_button(
                "⬇️ Markdown 다운로드",
                result['markdown'],
                file_name=f"{filename_base}_{uuid.uuid4().hex[:8]}.md",
                mime="text/markdown"
            )
        
        with tab2:
            json_str = json.dumps(result['chunks'], ensure_ascii=False, indent=2)
            st.text_area(
                "JSON 결과",
                json_str,
                height=400
            )
            
            st.download_button(
                "⬇️ JSON 다운로드",
                json_str,
                file_name=f"{filename_base}_{uuid.uuid4().hex[:8]}.json",
                mime="application/json"
            )
        
        with tab3:
            review_md = to_review_md(result['chunks'], result['markdown'])
            st.text_area(
                "리뷰용 Markdown",
                review_md,
                height=400
            )
            
            st.download_button(
                "⬇️ 리뷰용 다운로드",
                review_md,
                file_name=f"{filename_base}_review_{uuid.uuid4().hex[:8]}.md",
                mime="text/markdown"
            )
        
        with tab4:
            qa_result = result['qa_result']
            
            st.subheader("🔬 DualQA 검증 상세")
            
            # 메트릭
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("PDF 조문", qa_result['pdf_count'])
            with col2:
                st.metric("VLM 조문", qa_result['vlm_count'])
            with col3:
                st.metric("매칭률", f"{qa_result['match_rate']:.1%}")
            
            # 불일치 상세
            if qa_result['missing_in_vlm']:
                st.error("❌ VLM 누락 (PDF에는 있지만 VLM이 못 찾음)")
                st.json(qa_result['missing_in_vlm'])
            
            if qa_result['extra_in_vlm']:
                st.warning("⚠️ VLM 추가 (VLM이 만들어낸 조문)")
                st.json(qa_result['extra_in_vlm'])
            
            if not qa_result['qa_flags']:
                st.success("✅ 원본과 완전 일치!")
            else:
                st.warning(f"⚠️ QA 플래그: {qa_result['qa_flags']}")
                st.info("→ 수동 검수 권장")


if __name__ == '__main__':
    main()
"""
PRISM Phase 3.2 - Integrated Pipeline

✅ 통합 개선:
1. OCR 텍스트 추출 통합
2. 간결한 VLM 프롬프트 (368자 → 30자)
3. CV + OCR 하이브리드
4. RAG 최적화 청킹

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-22
Version: 3.2
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import time

# Core 모듈
from core.pdf_processor import PDFProcessor
from core.vlm_service import VLMService
from core.layout_detector import LayoutDetector

# Phase 3.2 신규 모듈
try:
    from core.ocr_text_extractor import OCRTextExtractor
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  OCR 모듈 없음. OCR 기능 제한됨.")

try:
    from phase32_concise_prompts import Phase32PromptBuilder
    CONCISE_PROMPTS_AVAILABLE = True
except ImportError:
    CONCISE_PROMPTS_AVAILABLE = False
    print("⚠️  간결 프롬프트 모듈 없음. 기본 프롬프트 사용.")

logger = logging.getLogger(__name__)


class Phase32Pipeline:
    """
    Phase 3.2 통합 파이프라인
    
    통합 구성:
    1. Layout Detection (CV) - 차트, 표 감지
    2. OCR Text Extraction - 일반 텍스트 추출
    3. VLM Analysis - 간결한 프롬프트로 분석
    4. RAG-optimized Chunking - 검색 최적화 청킹
    """
    
    def __init__(
        self,
        vlm_provider: str = "azure_openai",
        use_ocr: bool = True,
        use_concise_prompts: bool = True
    ):
        """
        초기화
        
        Args:
            vlm_provider: VLM 제공자 ('azure_openai', 'anthropic')
            use_ocr: OCR 사용 여부
            use_concise_prompts: 간결한 프롬프트 사용 여부
        """
        logger.info("="*60)
        logger.info("PRISM Phase 3.2 Pipeline 초기화")
        logger.info("="*60)
        
        # 1. PDF Processor
        self.pdf_processor = PDFProcessor()
        logger.info("✅ PDF Processor")
        
        # 2. VLM Service
        self.vlm_service = VLMService(provider=vlm_provider)
        logger.info(f"✅ VLM Service ({vlm_provider})")
        
        # 3. Layout Detector (CV)
        self.layout_detector = LayoutDetector()
        logger.info("✅ Layout Detector (CV)")
        
        # 4. OCR Text Extractor (신규)
        if use_ocr and OCR_AVAILABLE:
            self.ocr_extractor = OCRTextExtractor()
            self.use_ocr = True
            logger.info("✅ OCR Text Extractor")
        else:
            self.ocr_extractor = None
            self.use_ocr = False
            logger.warning("⚠️  OCR 비활성화")
        
        # 5. 간결한 프롬프트 빌더 (신규)
        if use_concise_prompts and CONCISE_PROMPTS_AVAILABLE:
            self.prompt_builder = Phase32PromptBuilder()
            self.use_concise = True
            logger.info("✅ Concise Prompt Builder (Phase 3.2)")
        else:
            self.prompt_builder = None
            self.use_concise = False
            logger.warning("⚠️  기본 프롬프트 사용")
        
        logger.info("="*60)
    
    def process_pdf(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 처리 (Phase 3.2 통합)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        
        logger.info("\n" + "="*60)
        logger.info("📄 PRISM Phase 3.2 문서 처리")
        logger.info(f"   파일: {Path(pdf_path).name}")
        logger.info("="*60 + "\n")
        
        # Stage 1: PDF → Images
        logger.info("--- Stage 1: PDF → Base64 Images ---")
        pages = self.pdf_processor.extract_pages_as_base64(pdf_path, max_pages)
        logger.info(f"✅ {len(pages)}개 페이지 변환 완료")
        
        # Stage 2: numpy 변환
        import numpy as np
        from PIL import Image
        import io
        import base64
        
        page_images = []
        for i, page in enumerate(pages, 1):
            img_data = base64.b64decode(page['image'].split(',')[1])
            img = Image.open(io.BytesIO(img_data))
            arr = np.array(img)
            page_images.append(arr)
            logger.info(f"  페이지 {i}: Base64 → numpy array 변환 완료 {arr.shape}")
        
        logger.info(f"✅ {len(page_images)}개 페이지 numpy 변환 완료")
        
        # Stage 3: 페이지별 처리
        all_regions = []
        all_chunks = []
        current_section = "시작"
        
        for page_num, image in enumerate(page_images):
            logger.info("\n" + "="*60)
            logger.info(f"페이지 {page_num + 1}/{len(page_images)} 처리")
            logger.info("="*60 + "\n")
            
            # ⭐ Stage 3.1: Layout Detection (CV)
            logger.info("--- Stage 3.1: Layout Detection (CV) ---")
            cv_regions = self.layout_detector.detect_regions(image, page_num)
            logger.info(f"✅ {len(cv_regions)}개 CV 영역 감지\n")
            
            # ⭐ Stage 3.2: OCR Text Extraction (신규!)
            ocr_regions = []
            section_titles = []
            full_text = ""
            
            if self.use_ocr:
                logger.info("--- Stage 3.2: OCR Text Extraction ---")
                
                # 전체 텍스트 추출
                ocr_result = self.ocr_extractor.extract_full_text(image)
                full_text = ocr_result['full_text']
                logger.info(f"   → {len(ocr_result['lines'])}줄 텍스트 추출")
                logger.info(f"   → 신뢰도: {ocr_result['confidence']:.1f}%")
                
                # 섹션 헤더 감지
                section_titles = self.ocr_extractor.extract_section_titles(image)
                logger.info(f"   → {len(section_titles)}개 섹션 헤더 감지")
                
                # 텍스트 영역 레이아웃
                ocr_regions = self.ocr_extractor.extract_text_regions(image)
                logger.info(f"   → {len(ocr_regions)}개 텍스트 영역 감지\n")
            
            # ⭐ Stage 3.3: 영역 통합
            logger.info("--- Stage 3.3: Region Integration ---")
            
            # 우선순위: section_titles > cv_regions > ocr_regions
            page_regions = section_titles + cv_regions + ocr_regions
            logger.info(f"✅ 총 {len(page_regions)}개 영역 통합\n")
            
            # ⭐ Stage 3.4: VLM Analysis (간결한 프롬프트!)
            logger.info("--- Stage 3.4: VLM Analysis (Concise) ---\n")
            
            for i, region in enumerate(page_regions, 1):
                region_type = region['type']
                
                logger.info(f"[Region {i}/{len(page_regions)}] {region_type}")
                
                # 섹션 헤더 감지
                if region_type == 'section_header':
                    # OCR에서 이미 추출된 텍스트 사용
                    caption = region.get('title', '')
                    current_section = caption
                    logger.info(f"   → 섹션 변경: {current_section}\n")
                
                # 텍스트 영역 (OCR 결과 사용)
                elif region_type == 'text_region':
                    caption = region.get('text', '')
                    logger.info(f"   → OCR 텍스트 사용: {len(caption)}자\n")
                
                # 차트/표 (VLM 분석 필요)
                elif region_type in ['pie_chart', 'bar_chart', 'table', 'map']:
                    # 영역 crop
                    x, y, w, h = region['bbox']
                    cropped = image[y:y+h, x:x+w]
                    
                    # ⭐ 간결한 프롬프트 생성
                    if self.use_concise:
                        prompt = self.prompt_builder.build_prompt(
                            element_type=region_type,
                            context=current_section
                        )
                    else:
                        # 기본 프롬프트 (fallback)
                        prompt = f"이 {region_type}를 분석하세요."
                    
                    # VLM 호출
                    vlm_start = time.time()
                    caption = self.vlm_service.analyze_image(cropped, prompt)
                    vlm_time = time.time() - vlm_start
                    
                    logger.info(f"   ✅ VLM 분석 완료: {vlm_time:.2f}초")
                    logger.info(f"   → {len(caption)}자\n")
                    
                    # ⭐ 출력 검증
                    if self.use_concise:
                        validation = self.prompt_builder.validate_output(
                            caption, region_type
                        )
                        
                        if not validation['valid']:
                            logger.warning(f"   ⚠️  검증 실패: {validation['reason']}")
                
                # 헤더 (VLM 간단 분석)
                elif region_type == 'header':
                    # OCR이 있으면 OCR 사용
                    if self.use_ocr:
                        caption = full_text[:100]  # 상단 100자
                    else:
                        # VLM 간단 분석
                        x, y, w, h = region['bbox']
                        cropped = image[y:y+h, x:x+w]
                        caption = self.vlm_service.analyze_image(
                            cropped,
                            "페이지 헤더 텍스트만 추출하세요. 20자 이내."
                        )
                    
                    current_section = caption.strip()
                    logger.info(f"   → 헤더: {caption}\n")
                
                else:
                    caption = ""
                
                # 영역 메타데이터 추가
                region['caption'] = caption
                region['section'] = current_section
                region['page_number'] = page_num + 1
                
                all_regions.append(region)
            
            # ⭐ Stage 3.5: RAG-optimized Chunking
            logger.info("--- Stage 3.5: RAG-optimized Chunking ---")
            
            for region in page_regions:
                chunk = {
                    'id': f"chunk_{len(all_chunks):03d}",
                    'type': region['type'],
                    'section': region.get('section', ''),
                    'page': region.get('page_number', page_num + 1),
                    'content': region.get('caption', ''),
                    'bbox': region.get('bbox', [0, 0, 0, 0]),
                    'confidence': region.get('confidence', 0.0)
                }
                all_chunks.append(chunk)
            
            logger.info(f"✅ {len(page_regions)}개 청크 생성\n")
        
        # 최종 결과
        processing_time = time.time() - start_time
        
        logger.info("="*60)
        logger.info("✅ Phase 3.2 처리 완료!")
        logger.info(f"   총 페이지: {len(page_images)}개")
        logger.info(f"   감지된 영역: {len(all_regions)}개")
        logger.info(f"   생성된 청크: {len(all_chunks)}개")
        logger.info(f"   처리 시간: {processing_time:.2f}초")
        logger.info("="*60 + "\n")
        
        return {
            'metadata': {
                'filename': Path(pdf_path).name,
                'total_pages': len(page_images),
                'total_regions': len(all_regions),
                'total_chunks': len(all_chunks),
                'processing_time_sec': round(processing_time, 2),
                'vlm_provider': self.vlm_service.provider,
                'ocr_enabled': self.use_ocr,
                'concise_prompts': self.use_concise
            },
            'regions': all_regions,
            'chunks': all_chunks,
            'pages': page_images
        }


# ===========================
# 결과 포맷터 (Phase 3.2)
# ===========================

class Phase32ResultFormatter:
    """
    Phase 3.2 결과 포맷터
    
    개선:
    - 간결한 청크 출력
    - RAG 최적화 형식
    """
    
    @staticmethod
    def format_to_markdown(result: Dict) -> str:
        """마크다운 형식으로 변환"""
        metadata = result['metadata']
        chunks = result['chunks']
        
        md = f"""# PRISM Phase 3.2 - 간결한 문서 추출

**생성일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 📄 문서 정보

- **파일명**: {metadata['filename']}
- **총 페이지**: {metadata['total_pages']}개
- **총 영역**: {metadata['total_regions']}개
- **총 청크**: {metadata['total_chunks']}개
- **처리 시간**: {metadata['processing_time_sec']}초
- **OCR 사용**: {'✅' if metadata['ocr_enabled'] else '❌'}
- **간결 프롬프트**: {'✅' if metadata['concise_prompts'] else '❌'}
- **Phase**: 3.2

"""
        
        # 청크별 출력
        md += "## 🧩 청크\n\n"
        
        current_section = ""
        for i, chunk in enumerate(chunks, 1):
            # 섹션 변경 시 헤더
            if chunk['section'] != current_section:
                current_section = chunk['section']
                md += f"\n### {current_section}\n\n"
            
            md += f"**[{i}] {chunk['type']}** (페이지 {chunk['page']})\n\n"
            md += f"{chunk['content']}\n\n"
            md += "---\n\n"
        
        return md
    
    @staticmethod
    def format_to_json(result: Dict) -> Dict:
        """JSON 형식으로 변환"""
        return {
            'metadata': result['metadata'],
            'chunks': result['chunks']
        }


if __name__ == '__main__':
    # 테스트
    print("="*60)
    print("Phase 3.2 Pipeline 테스트")
    print("="*60)
    
    pipeline = Phase32Pipeline(
        vlm_provider='azure_openai',
        use_ocr=True,
        use_concise_prompts=True
    )
    
    print("\n✅ Pipeline 초기화 완료")
    print(f"   OCR: {pipeline.use_ocr}")
    print(f"   간결 프롬프트: {pipeline.use_concise}")

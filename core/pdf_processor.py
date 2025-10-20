"""
PRISM Phase 2.7 - PDF Processor
HybridExtractor 통합 버전
"""

import logging
from typing import List, Dict, Any
import fitz  # PyMuPDF
from PIL import Image
import io

from .hybrid_extractor import HybridExtractor

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF 문서 처리기 (2-Pass Hybrid 방식)
    
    Stage 1: PDF → 페이지별 이미지 변환
    Stage 2: 2-Pass 하이브리드 추출 (OCR + VLM)
    """
    
    def __init__(self, vlm_service):
        self.vlm_service = vlm_service
        
        # 2-Pass Hybrid Extractor 초기화
        self.extractor = HybridExtractor(vlm_service)
        
        # PyMuPDF 설정
        self.dpi = 300  # 고해상도
    
    def process_pdf(self, pdf_path: str, max_pages: int = 20) -> Dict[str, Any]:
        """
        PDF 문서 전체 처리
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            {
                'stage1_elements': [...],  # 페이지별 요소
                'stage2_chunks': [...],     # 청킹된 텍스트
                'metadata': {...}
            }
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), max_pages)
            
            logger.info(f"📄 PDF 처리 시작: {total_pages}페이지")
            
            stage1_elements = []
            stage2_chunks = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Stage 1: 페이지 → 이미지 변환
                page_image = self._page_to_image(page)
                
                # Stage 2: 2-Pass 하이브리드 추출
                extraction_result = self.extractor.extract(
                    page_image=page_image,
                    page_number=page_num + 1
                )
                
                # Stage 1 메타데이터
                stage1_elements.append({
                    'page_number': page_num + 1,
                    'type': 'text',
                    'count': 1,
                    'method': extraction_result.method
                })
                
                # Stage 2: 청킹
                text = extraction_result.text
                chunks = self._chunk_text(text, page_num + 1)
                stage2_chunks.extend(chunks)
                
                logger.info(f"✅ Page {page_num + 1}: {len(text)} 문자, {len(chunks)} 청크")
            
            doc.close()
            
            return {
                'stage1_elements': stage1_elements,
                'stage2_chunks': stage2_chunks,
                'metadata': {
                    'total_pages': total_pages,
                    'method': 'hybrid_2pass'
                }
            }
            
        except Exception as e:
            logger.error(f"PDF 처리 실패: {e}")
            raise
    
    def _page_to_image(self, page) -> Image.Image:
        """PyMuPDF Page → PIL Image 변환"""
        # 고해상도 렌더링
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # PIL Image로 변환
        img_data = pix.tobytes("png")
        return Image.open(io.BytesIO(img_data))
    
    def _chunk_text(self, text: str, page_number: int, chunk_size: int = 500) -> List[Dict]:
        """
        텍스트를 청크로 분할
        
        Args:
            text: 전체 텍스트
            page_number: 페이지 번호
            chunk_size: 청크 크기 (문자)
            
        Returns:
            List of chunks
        """
        chunks = []
        overlap = 50  # 오버랩
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 청크 추출
            chunk_text = text[start:end]
            
            chunks.append({
                'chunk_id': f"chunk_{page_number}_{id(chunk_text)}",
                'page_number': page_number,
                'element_type': 'text',
                'content': chunk_text,
                'metadata': {
                    'section_path': 'Full page content',
                    'source': 'hybrid_2pass',
                    'chunk_index': chunk_index,
                    'start_pos': start,
                    'end_pos': end,
                    'total_chunks': 0  # 나중에 계산
                },
                'model_used': 'claude',
                'processing_time_sec': 0
            })
            
            start = end - overlap
            chunk_index += 1
        
        # total_chunks 업데이트
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = len(chunks)
        
        return chunks


# ===== 사용 예시 =====
if __name__ == "__main__":
    from core.vlm_service import VLMService
    
    # VLM 서비스 초기화
    vlm = VLMService()
    
    # PDF 프로세서 생성
    processor = PDFProcessor(vlm)
    
    # PDF 처리
    result = processor.process_pdf("test.pdf", max_pages=3)
    
    print(f"✅ 처리 완료:")
    print(f"  - Stage 1: {len(result['stage1_elements'])} elements")
    print(f"  - Stage 2: {len(result['stage2_chunks'])} chunks")
# core/pdf_processor.py

import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
import os
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서 처리 클래스"""
    
    def __init__(self, vlm_service=None):
        """
        Args:
            vlm_service: VLM 서비스 인스턴스 (MultiVLMService)
        """
        logger.info("PDFProcessor 초기화 중...")
        self.vlm_service = vlm_service
        self.ocr_engine = None
        self._initialize_ocr()
        
    def _initialize_ocr(self):
        """PaddleOCR 초기화"""
        try:
            logger.info("PaddleOCR 초기화 중...")
            from paddleocr import PaddleOCR
            
            # 한국어 OCR 초기화
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang='korean'
            )
            logger.info("PaddleOCR 초기화 완료")
            
        except Exception as e:
            logger.error(f"PaddleOCR 초기화 실패: {e}")
            self.ocr_engine = None

    def extract_text_with_ocr(self, image_bytes: bytes) -> str:
        """
        이미지에서 OCR로 텍스트 추출
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            추출된 텍스트
        """
        if not self.ocr_engine:
            return ""
        
        try:
            # 이미지 저장 (PaddleOCR은 파일 경로 필요)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            
            try:
                # OCR 실행
                result = self.ocr_engine.ocr(tmp_path)
                
                # 결과 파싱 - PaddleOCR 반환 구조 처리
                text_lines = []
                
                if result and len(result) > 0:
                    # result는 [page_results] 형태
                    page_result = result[0]
                    
                    if page_result:  # None이 아닌 경우
                        for line in page_result:
                            if line and len(line) >= 2:
                                # line은 [bbox, (text, confidence)] 형태
                                text_info = line[1]
                                if isinstance(text_info, (tuple, list)) and len(text_info) >= 1:
                                    text = text_info[0]
                                    if text:
                                        text_lines.append(str(text))
                
                return '\n'.join(text_lines) if text_lines else ""
                
            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"OCR 추출 오류: {e}")
            return ""

    def pdf_to_images(self, pdf_source, dpi: int = 150) -> List[Tuple[int, bytes]]:
        """
        PDF를 페이지별 이미지로 변환
        
        Args:
            pdf_source: PDF 파일 경로(str) 또는 바이트 데이터(bytes)
            dpi: 이미지 해상도
            
        Returns:
            (페이지 번호, 이미지 바이트) 튜플 리스트
        """
        images = []
        doc = None
        
        try:
            # PDF 소스 타입에 따라 처리
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 페이지를 이미지로 변환
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat)
                
                # PNG 바이트로 변환
                img_bytes = pix.tobytes("png")
                images.append((page_num + 1, img_bytes))
            
            logger.info(f"PDF->이미지 변환 완료: {len(images)}페이지")
            
        except Exception as e:
            logger.error(f"PDF 이미지 변환 오류: {e}")
            
        finally:
            if doc:
                doc.close()
                
        return images

    def image_to_base64(self, image_bytes: bytes) -> str:
        """이미지 바이트를 base64 문자열로 변환"""
        return base64.b64encode(image_bytes).decode('utf-8')

    def analyze_page_with_vlm(
        self, 
        image_bytes: bytes, 
        page_num: int,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        VLM을 사용하여 페이지 분석
        
        Args:
            image_bytes: 페이지 이미지 바이트
            page_num: 페이지 번호
            ocr_text: OCR로 추출한 텍스트 (옵션)
            
        Returns:
            분석 결과 딕셔너리
        """
        if not self.vlm_service:
            return {
                "page_num": page_num,
                "content": "VLM 서비스가 초기화되지 않았습니다.",
                "type": "error"
            }
        
        try:
            # base64 인코딩
            image_base64 = self.image_to_base64(image_bytes)
            
            # VLM 프롬프트 구성
            prompt = self._build_vlm_prompt(page_num, ocr_text)
            
            # VLM 분석 실행
            response = self.vlm_service.analyze_image(
                image_base64=image_base64,
                prompt=prompt
            )
            
            return {
                "page_num": page_num,
                "content": response.get("content", ""),
                "type": "image",
                "provider": response.get("provider", "unknown"),
                "ocr_text_preview": ocr_text[:500] if ocr_text else None
            }
            
        except Exception as e:
            logger.error(f"VLM 페이지 분석 오류 (페이지 {page_num}): {e}")
            return {
                "page_num": page_num,
                "content": f"분석 오류: {str(e)}",
                "type": "error"
            }

    def _build_vlm_prompt(self, page_num: int, ocr_text: Optional[str] = None) -> str:
        """VLM 분석용 프롬프트 생성 (개선된 버전)"""
        
        prompt_parts = []
        
        prompt_parts.append(f"이 문서 이미지(페이지 {page_num})를 분석해주세요.")
        prompt_parts.append("")
        prompt_parts.append("=" * 80)
        prompt_parts.append("**중요: 정확도 최우선 원칙**")
        prompt_parts.append("=" * 80)
        prompt_parts.append("- 이미지에서 보이는 **정확한 숫자와 텍스트**만 사용하세요")
        prompt_parts.append("- 절대 추측하거나 일반화하지 마세요")
        prompt_parts.append("- 차트의 레이블과 값을 매우 신중하게 읽으세요")
        prompt_parts.append("- 숫자가 명확하지 않으면 OCR 텍스트를 참고하세요")
        prompt_parts.append("")
        prompt_parts.append("**검증 체크리스트:**")
        prompt_parts.append("[ ] 모든 숫자가 이미지의 값과 정확히 일치하는가?")
        prompt_parts.append("[ ] 차트 레이블이 이미지의 텍스트와 정확히 일치하는가?")
        prompt_parts.append("[ ] 퍼센트의 합계가 100%인가? (해당되는 경우)")
        prompt_parts.append("[ ] 남성/여성 비율이 올바른가? (성별 데이터의 경우)")
        prompt_parts.append("")
        
        prompt_parts.append("**분석 요구사항:**")
        prompt_parts.append("")
        prompt_parts.append("1. **문서 구조 파악**")
        prompt_parts.append("   - 제목, 섹션, 단락 구조 식별")
        prompt_parts.append("   - 표, 차트, 이미지 등 비텍스트 요소 위치 파악")
        prompt_parts.append("")
        prompt_parts.append("2. **정확한 데이터 추출 (최우선)**")
        prompt_parts.append("   - **숫자는 이미지에 표시된 그대로 정확히 기록**")
        prompt_parts.append("   - **차트 레이블은 이미지의 텍스트 그대로 사용 (추론 금지)**")
        prompt_parts.append("   - 표나 차트의 모든 데이터를 빠짐없이 추출")
        prompt_parts.append("   - 날짜, 통계, 비율은 특히 주의하여 정확히 기록")
        prompt_parts.append("")
        prompt_parts.append("3. **교차 검증 (필수)**")
        prompt_parts.append("   - 이미지와 OCR 텍스트를 교차 검증")
        prompt_parts.append("   - 불일치가 있으면 이미지를 우선하되, 숫자는 OCR도 참고")
        prompt_parts.append("   - 합계/비율 검증 (예: 퍼센트 합 = 100%)")
        prompt_parts.append("")
        prompt_parts.append("4. **맥락 및 의미 분석**")
        prompt_parts.append("   - 문서의 목적과 주요 메시지 파악")
        prompt_parts.append("   - 데이터 간의 관계와 인사이트 도출")
        prompt_parts.append("")
        prompt_parts.append("5. **마크다운 형식으로 출력**")
        prompt_parts.append("   - 계층적 헤딩 구조 사용 (##, ###)")
        prompt_parts.append("   - 표는 마크다운 테이블 형식으로")
        prompt_parts.append("   - 리스트는 불릿(-)이나 번호(1.) 사용")
        prompt_parts.append("   - 중요 정보는 **볼드** 처리")
        prompt_parts.append("")
        prompt_parts.append("**출력 예시:**")
        prompt_parts.append("## [페이지 주제/제목]")
        prompt_parts.append("")
        prompt_parts.append("### 주요 내용")
        prompt_parts.append("- 핵심 포인트 1 (정확한 숫자 포함)")
        prompt_parts.append("- 핵심 포인트 2")
        prompt_parts.append("")
        prompt_parts.append("### 데이터 분석")
        prompt_parts.append("| 항목 | 값 |")
        prompt_parts.append("|------|-----|")
        prompt_parts.append("| 항목1 | XX.X% |")
        prompt_parts.append("")
        prompt_parts.append("### 인사이트")
        prompt_parts.append("- 데이터 기반 인사이트...")
        
        # OCR 텍스트가 있으면 적극 활용
        if ocr_text:
            prompt_parts.append("")
            prompt_parts.append("=" * 80)
            prompt_parts.append("**OCR로 추출한 텍스트 (숫자/레이블 검증용 - 매우 중요)**")
            prompt_parts.append("=" * 80)
            prompt_parts.append("아래 OCR 텍스트를 반드시 참고하여 이미지의 숫자와 레이블을 정확히 확인하세요.")
            prompt_parts.append("특히 숫자가 작거나 불명확한 경우 OCR 텍스트를 우선 참고하세요.")
            prompt_parts.append("")
            prompt_parts.append(ocr_text[:3000])  # 더 많은 텍스트 제공
            prompt_parts.append("")
            prompt_parts.append("=" * 80)
            prompt_parts.append("**중요 알림:**")
            prompt_parts.append("- 이미지와 OCR 텍스트를 함께 보고 가장 정확한 값을 선택하세요")
            prompt_parts.append("- 숫자나 퍼센트는 OCR 텍스트를 적극 활용하세요")
            prompt_parts.append("- 레이블/항목명은 이미지를 우선하되 OCR로 검증하세요")
            prompt_parts.append("=" * 80)
        
        return '\n'.join(prompt_parts)

    def process_pdf(
        self, 
        pdf_data=None,
        pdf_path=None,
        use_ocr: bool = True,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        PDF 문서 전체 처리
        
        Args:
            pdf_data: PDF 바이트 데이터 (우선순위 1)
            pdf_path: PDF 파일 경로 (우선순위 2)
            use_ocr: OCR 사용 여부
            progress_callback: 진행상황 콜백 함수
            
        Returns:
            처리된 페이지 청크 리스트 (각 청크는 딕셔너리)
        """
        # PDF 소스 결정
        pdf_source = pdf_data if pdf_data is not None else pdf_path
        
        if pdf_source is None:
            raise ValueError("pdf_data 또는 pdf_path 중 하나는 반드시 제공되어야 합니다.")
        
        source_type = "바이트 데이터" if pdf_data is not None else f"파일 {pdf_path}"
        logger.info(f"PDF 처리 시작: {source_type}")
        
        chunks = []
        
        try:
            # 1. PDF를 이미지로 변환
            if progress_callback:
                progress_callback("PDF를 이미지로 변환 중...", 0)
                
            page_images = self.pdf_to_images(pdf_source)
            total_pages = len(page_images)
            
            logger.info(f"총 {total_pages}페이지 처리 시작")
            
            # 2. 각 페이지 처리
            for idx, (page_num, image_bytes) in enumerate(page_images):
                if progress_callback:
                    progress = int((idx / total_pages) * 100)
                    progress_callback(f"페이지 {page_num}/{total_pages} 분석 중...", progress)
                
                logger.info(f"페이지 {page_num} 처리 중...")
                
                # OCR 텍스트 추출 (옵션)
                ocr_text = None
                if use_ocr and self.ocr_engine:
                    logger.info(f"페이지 {page_num} OCR 추출 중...")
                    ocr_text = self.extract_text_with_ocr(image_bytes)
                    logger.info(f"페이지 {page_num} OCR 완료: {len(ocr_text) if ocr_text else 0}자")
                
                # VLM 분석
                logger.info(f"페이지 {page_num} VLM 분석 중...")
                chunk = self.analyze_page_with_vlm(image_bytes, page_num, ocr_text)
                chunk["chunk_id"] = f"chunk_{idx+1:03d}"
                
                chunks.append(chunk)
                logger.info(f"페이지 {page_num} 처리 완료")
            
            if progress_callback:
                progress_callback("처리 완료!", 100)
                
            logger.info(f"PDF 처리 완료: {total_pages}페이지, {len(chunks)}개 청크 생성")
            
        except Exception as e:
            logger.error(f"PDF 처리 오류: {e}", exc_info=True)
            raise
        
        return chunks

    def extract_tables(self, pdf_source) -> List[Dict[str, Any]]:
        """
        PDF에서 표 추출
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            추출된 표 리스트
        """
        tables = []
        doc = None
        
        try:
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 표 감지
                page_tables = page.find_tables()
                
                for table in page_tables:
                    tables.append({
                        "page": page_num + 1,
                        "data": table.extract()
                    })
            
        except Exception as e:
            logger.error(f"표 추출 오류: {e}")
            
        finally:
            if doc:
                doc.close()
        
        return tables

    def get_pdf_metadata(self, pdf_source) -> Dict[str, Any]:
        """
        PDF 메타데이터 추출
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            메타데이터 딕셔너리
        """
        doc = None
        
        try:
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)
                
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 추출 오류: {e}")
            return {}
            
        finally:
            if doc:
                doc.close()
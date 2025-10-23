"""
PRISM Phase 2.5 - Enhanced Pipeline (Phase 2.5 Extractor 호환)

개선 사항:
- extract_full_page() → extract() 메서드명 변경 대응
- Phase 2.5 개선 프롬프트 적용

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-17
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import fitz  # PyMuPDF

from models.layout_detector import LayoutDetector, DocumentElement, ElementType, BoundingBox
from core.claude_full_page_extractor import ClaudeFullPageExtractor, PageContent
from core.intelligent_chunker import IntelligentChunker
from core.document_analyzer import DocumentAnalyzer


class Phase2Pipeline:
    """
    PRISM Phase 2.5 파이프라인 (Enhanced Chart Extraction)
    
    처리 단계:
    1. ⭐ Claude Vision으로 전체 페이지 분석 (개선된 프롬프트)
    2. 텍스트, 표, 차트, 그래프, 이미지 동시 추출
    3. Intelligent Chunking
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        use_full_claude_vision: bool = True
    ):
        """
        Args:
            azure_endpoint: Azure OpenAI 엔드포인트 (선택)
            azure_api_key: Azure OpenAI API 키 (선택)
            chunk_size: 청크 크기
            chunk_overlap: 청크 오버랩
            use_full_claude_vision: 전체 페이지 Claude Vision 사용 여부
        """
        print("Initializing PRISM Phase 2.5 Pipeline (Enhanced Chart Extraction)...")
        
        # Azure OpenAI 설정 저장
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        
        # 1. Layout Detector (참고용)
        self.layout_detector = LayoutDetector()
        
        # 2. ⭐ Claude Full Page Extractor (Phase 2.5 개선)
        self.use_full_claude_vision = use_full_claude_vision
        if use_full_claude_vision:
            self.claude_extractor = ClaudeFullPageExtractor(
                azure_endpoint=azure_endpoint,
                azure_api_key=azure_api_key
            )
            if self.claude_extractor.client:
                print("✅ Phase 2.5 Enhanced Claude Vision enabled")
            else:
                print("⚠️  Claude Vision unavailable, falling back to OCR")
                self.use_full_claude_vision = False
        
        # 3. Intelligent Chunker
        self.chunker = IntelligentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # 4. Document Analyzer
        self.analyzer = DocumentAnalyzer()
        
        print("✅ Phase 2.5 Pipeline initialized")

    def _convert_page_to_chunks(
        self,
        page_content: PageContent
    ) -> List[Dict]:
        """
        PageContent를 청크 리스트로 변환
        
        Args:
            page_content: Claude가 추출한 페이지 내용
            
        Returns:
            청크 리스트
        """
        chunks = []
        chunk_counter = 1
        
        page_num = page_content.page_num
        
        # 1. 텍스트 청크
        for text_block in page_content.text_blocks:
            chunk_id = f"chunk_{page_num:03d}_{chunk_counter:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "type": "text",
                "content": text_block.text,
                "page_num": page_num,
                "metadata": {
                    "section_title": "",
                    "section_type": "text",
                    "confidence": text_block.confidence
                }
            })
            chunk_counter += 1
        
        # 2. 표 청크
        for table in page_content.tables:
            chunk_id = f"table_{page_num:03d}_{chunk_counter:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "type": "table",
                "content": table.markdown,
                "page_num": page_num,
                "metadata": {
                    "caption": table.caption,
                    "confidence": table.confidence
                }
            })
            chunk_counter += 1
        
        # 3. ⭐ 차트 청크 (Phase 2.5 - 데이터 포인트 포함)
        for chart in page_content.charts:
            chunk_id = f"chart_{page_num:03d}_{chunk_counter:03d}"
            
            # 차트 내용 포맷팅
            content_lines = [
                f"[차트: {chart.title}]",
                f"타입: {chart.type}",
                f"설명: {chart.description}",
                "데이터:"
            ]
            
            # ⭐ 데이터 포인트 추가
            if chart.data_points:
                # 그룹 데이터 여부 확인
                if chart.data_points and isinstance(chart.data_points[0], dict):
                    first_point = chart.data_points[0]
                    if 'category' in first_point and 'values' in first_point:
                        # 그룹 데이터 (예: 입장료 - 전체/팬/일반)
                        content_lines.append("")
                        for group in chart.data_points:
                            content_lines.append(f"[{group['category']}]")
                            for value in group['values']:
                                unit = value.get('unit', '')
                                content_lines.append(f"  - {value['label']}: {value['value']}{unit}")
                            content_lines.append("")
                    else:
                        # 단순 데이터 (예: 남성 45.2%, 여성 54.8%)
                        for point in chart.data_points:
                            label = point.get('label', '')
                            value = point.get('value', '')
                            unit = point.get('unit', '')
                            content_lines.append(f"  - {label}: {value}{unit}")
            else:
                content_lines.append("  - (데이터 없음)")
            
            content = "\n".join(content_lines)
            
            chunks.append({
                "chunk_id": chunk_id,
                "type": "chart",
                "content": content,
                "page_num": page_num,
                "metadata": {
                    "chart_type": chart.type,
                    "title": chart.title,
                    "description": chart.description,
                    "data_points": chart.data_points,
                    "confidence": chart.confidence
                }
            })
            chunk_counter += 1
        
        # 4. 이미지/다이어그램 청크
        for figure in page_content.figures:
            chunk_id = f"figure_{page_num:03d}_{chunk_counter:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "type": "figure",
                "content": f"[이미지: {figure.type}]\n{figure.description}",
                "page_num": page_num,
                "metadata": {
                    "figure_type": figure.type,
                    "description": figure.description,
                    "confidence": figure.confidence
                }
            })
            chunk_counter += 1
        
        return chunks

    def process(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None
    ) -> Dict:
        """
        PDF 문서 처리 (Phase 2.5)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과 딕셔너리
        """
        print("\n" + "="*60)
        print("PRISM Phase 2.5 - Document Processing")
        print("="*60)
        
        start_time = time.time()
        
        # 1. PDF 열기
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"\n📄 문서: {Path(pdf_path).name}")
        print(f"📊 총 페이지: {total_pages}")
        
        all_chunks = []
        stats = {
            'total_pages': total_pages,
            'text_chunks': 0,
            'table_chunks': 0,
            'chart_chunks': 0,
            'figure_chunks': 0
        }
        
        # 2. 페이지별 처리
        for page_num in range(total_pages):
            print(f"\n{'='*60}")
            print(f"📄 Processing Page {page_num + 1}/{total_pages}")
            print(f"{'='*60}")
            
            # 2.1 페이지를 이미지로 변환
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 2.2 ⭐ Claude Vision으로 전체 페이지 추출 (Phase 2.5 개선)
            if self.use_full_claude_vision:
                # ✅ 수정: extract_full_page() → extract()
                page_content = self.claude_extractor.extract(img, page_num + 1)
                
                if page_content:
                    # PageContent → 청크 변환
                    page_chunks = self._convert_page_to_chunks(page_content)
                    all_chunks.extend(page_chunks)
                    
                    # 통계 업데이트
                    for chunk in page_chunks:
                        chunk_type = chunk['type']
                        if chunk_type == 'text':
                            stats['text_chunks'] += 1
                        elif chunk_type == 'table':
                            stats['table_chunks'] += 1
                        elif chunk_type == 'chart':
                            stats['chart_chunks'] += 1
                        elif chunk_type == 'figure':
                            stats['figure_chunks'] += 1
                else:
                    print(f"⚠️  Page {page_num + 1} extraction failed")
        
        doc.close()
        
        # 3. 통계 계산
        end_time = time.time()
        stats['processing_time'] = end_time - start_time
        stats['total_chunks'] = len(all_chunks)
        
        # 4. 결과 반환
        result = {
            'chunks': all_chunks,
            'statistics': stats
        }
        
        print("\n" + "="*60)
        print("✅ Processing Complete")
        print("="*60)
        print(f"⏱️  총 처리 시간: {stats['processing_time']:.1f}초")
        print(f"📊 총 청크: {stats['total_chunks']}개")
        print(f"   - 텍스트: {stats['text_chunks']}개")
        print(f"   - 표: {stats['table_chunks']}개")
        print(f"   - 차트: {stats['chart_chunks']}개")
        print(f"   - 이미지: {stats['figure_chunks']}개")
        
        return result


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.5 - Pipeline Test")
    print("="*60 + "\n")
    
    pipeline = Phase2Pipeline()
    
    # 테스트 PDF 경로
    test_pdf = "input/test_parser_02.pdf"
    
    if Path(test_pdf).exists():
        print(f"✅ Test PDF found: {test_pdf}")
        result = pipeline.process(test_pdf, max_pages=3)
        
        # 결과 저장
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        import json
        with open(output_dir / "test_phase25_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Results saved to: output/test_phase25_result.json")
    else:
        print(f"❌ Test PDF not found: {test_pdf}")
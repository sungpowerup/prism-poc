"""
PRISM Phase 2 - Main Processing Pipeline

전체 문서 처리 파이프라인을 통합합니다.

Author: 전체 팀
Date: 2025-10-11
"""

import time
from typing import Dict, Optional
from pathlib import Path
import json

from core.document_analyzer import DocumentAnalyzer, DocumentStructure
from core.text_extractor import TextExtractor
from core.table_parser import TableParser
from core.image_captioner import ImageCaptioner
from core.intelligent_chunker import IntelligentChunker, ChunkingResult
from models.layout_detector import ElementType


class Phase2Pipeline:
    """
    PRISM Phase 2 전체 파이프라인
    
    PDF → Layout Detection → Text/Table/Image 추출 → 지능형 청킹
    """
    
    def __init__(
        self,
        vlm_provider: str = "claude",
        dpi: int = 200,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        require_vlm_key: bool = False
    ):
        """
        Args:
            vlm_provider: VLM 프로바이더 ("claude", "azure", "ollama")
            dpi: PDF 이미지 변환 해상도
            chunk_size: 청크 크기 (토큰)
            chunk_overlap: 청크 중복 (토큰)
            require_vlm_key: VLM API 키 필수 여부
        """
        print("Initializing PRISM Phase 2 Pipeline...")
        
        self.analyzer = DocumentAnalyzer(dpi=dpi)
        self.text_extractor = TextExtractor(use_ocr_fallback=True)
        self.table_parser = TableParser()
        self.image_captioner = ImageCaptioner(
            provider=vlm_provider,
            require_key=require_vlm_key
        )
        self.chunker = IntelligentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        print("✅ Pipeline initialized successfully")
    
    def process(
        self, 
        pdf_path: str, 
        max_pages: Optional[int] = None,
        output_dir: str = "data/processed"
    ) -> Dict:
        """
        문서 전체 처리
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지
            output_dir: 출력 디렉토리
            
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"PRISM Phase 2 - Document Processing")
        print(f"{'='*60}")
        print(f"Input: {pdf_path}")
        print(f"Max pages: {max_pages or 'All'}")
        print(f"{'='*60}\n")
        
        # 1. 문서 분석 (Layout Detection)
        print("📄 Step 1/5: Analyzing document structure...")
        structure = self.analyzer.analyze(pdf_path, max_pages)
        print(f"✓ Found {structure.total_pages} pages")
        
        # 2. 텍스트 추출
        print("\n📝 Step 2/5: Extracting text...")
        text_elements = structure.get_all_elements_by_type(ElementType.TEXT)
        title_elements = structure.get_all_elements_by_type(ElementType.TITLE)
        all_text_elements = text_elements + title_elements
        
        texts = self.text_extractor.extract_all_text(pdf_path, all_text_elements)
        print(f"✓ Extracted {len(texts)} text blocks")
        
        # 3. 표 파싱
        print("\n📊 Step 3/5: Parsing tables...")
        table_elements = structure.get_all_elements_by_type(ElementType.TABLE)
        tables = self.table_parser.parse_all_tables(pdf_path, table_elements)
        print(f"✓ Parsed {len(tables)} tables")
        
        # 4. 이미지 캡션
        print("\n🖼️  Step 4/5: Generating image captions...")
        image_elements = structure.get_all_elements_by_type(ElementType.IMAGE)
        chart_elements = structure.get_all_elements_by_type(ElementType.CHART)
        all_visual = image_elements + chart_elements
        
        captions = self.image_captioner.generate_captions_batch(
            pdf_path, 
            all_visual, 
            self.analyzer
        )
        print(f"✓ Generated {len(captions)} captions")
        
        # 5. 지능형 청킹
        print("\n🧩 Step 5/5: Intelligent chunking...")
        chunking_result = self.chunker.chunk(structure, texts, tables, captions)
        print(f"✓ Created {chunking_result.statistics['total_chunks']} chunks")
        
        # 처리 시간
        elapsed_time = time.time() - start_time
        
        # 결과 저장
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        self._save_results(
            output_path,
            structure,
            texts,
            tables,
            captions,
            chunking_result
        )
        
        # 결과 요약
        result = {
            "document": pdf_path,
            "pages_processed": structure.total_pages,
            "processing_time": elapsed_time,
            "elements": {
                "text_blocks": len(texts),
                "tables": len(tables),
                "images": len(captions)
            },
            "chunks": chunking_result.statistics,
            "output_dir": str(output_path)
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Processing complete!")
        print(f"Time: {elapsed_time:.1f}s")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
        return result
    
    def _save_results(
        self,
        output_path: Path,
        structure: DocumentStructure,
        texts: list,
        tables: list,
        captions: list,
        chunking_result: ChunkingResult
    ):
        """결과를 파일로 저장"""
        
        # 1. structure.json
        with open(output_path / "structure.json", "w", encoding="utf-8") as f:
            json.dump(structure.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 2. texts.json
        with open(output_path / "texts.json", "w", encoding="utf-8") as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
        
        # 3. tables (JSON + Markdown)
        for i, table in enumerate(tables):
            # JSON
            with open(output_path / f"table_{i+1}.json", "w", encoding="utf-8") as f:
                json.dump(table.to_json(), f, ensure_ascii=False, indent=2)
            
            # Markdown
            with open(output_path / f"table_{i+1}.md", "w", encoding="utf-8") as f:
                f.write(table.to_markdown())
        
        # 4. captions.json
        captions_dict = [c.to_dict() for c in captions]
        with open(output_path / "captions.json", "w", encoding="utf-8") as f:
            json.dump(captions_dict, f, ensure_ascii=False, indent=2)
        
        # 5. chunks.json (⭐ 가장 중요!)
        with open(output_path / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunking_result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 6. report.md (사람이 읽기 쉬운 리포트)
        self._generate_report(output_path, structure, texts, tables, captions, chunking_result)
    
    def _generate_report(
        self,
        output_path: Path,
        structure: DocumentStructure,
        texts: list,
        tables: list,
        captions: list,
        chunking_result: ChunkingResult
    ):
        """사람이 읽기 쉬운 리포트 생성"""
        
        report_lines = [
            "# PRISM Phase 2 - Processing Report",
            "",
            "## Document Information",
            f"- Total Pages: {structure.total_pages}",
            f"- Text Blocks: {len(texts)}",
            f"- Tables: {len(tables)}",
            f"- Images: {len(captions)}",
            "",
            "## Chunking Statistics",
            f"- Total Chunks: {chunking_result.statistics['total_chunks']}",
            f"- Text Chunks: {chunking_result.statistics['text_chunks']}",
            f"- Table Chunks: {chunking_result.statistics['table_chunks']}",
            f"- Image Chunks: {chunking_result.statistics['image_chunks']}",
            f"- Average Chunk Size: {chunking_result.statistics['avg_chunk_size']:.0f} chars",
            f"- Has Embeddings: {chunking_result.statistics['has_embeddings']}",
            "",
            "## Sample Chunks",
            ""
        ]
        
        # 샘플 청크 (처음 3개)
        for i, chunk in enumerate(chunking_result.chunks[:3]):
            report_lines.extend([
                f"### Chunk {i+1} ({chunk.type.upper()})",
                f"**Page**: {chunk.page_num}",
                f"**ID**: {chunk.chunk_id}",
                "",
                "```",
                chunk.content[:200] + ("..." if len(chunk.content) > 200 else ""),
                "```",
                ""
            ])
        
        # 파일 저장
        with open(output_path / "report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))


# CLI 실행
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python phase2_pipeline.py <pdf_path> [max_pages]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # 파이프라인 실행 (API 키 없어도 OK)
    pipeline = Phase2Pipeline(
        vlm_provider="claude",
        require_vlm_key=False
    )
    
    result = pipeline.process(pdf_path, max_pages)
    
    print("\n✅ Done! Check results in:", result["output_dir"])
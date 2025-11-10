"""
Phase 0.4 Pipeline with Golden Diff Integration
Phase 0.4.0 "Quality Assurance Release"

Integrates Golden Diff Engine for honest quality measurement

Author: 이서영 (Backend Lead) + 박준호 (AI/ML Lead)
Date: 2025-11-10
Version: 0.4.0
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

# Version check
try:
    from .version import PRISM_VERSION, check_version
    VERSION = "0.4.0"
    check_version(__name__, VERSION)
except ImportError:
    VERSION = "0.4.0"
    print(f"⚠️ Version module not found, using VERSION={VERSION}")

# Import core modules
try:
    from .golden_diff_engine import GoldenDiffEngine
    from .semantic_chunker_v04 import SemanticChunker
    GOLDEN_DIFF_AVAILABLE = True
except ImportError:
    GOLDEN_DIFF_AVAILABLE = False
    print("⚠️ Golden Diff Engine not available")

logger = logging.getLogger(__name__)

# ============================================
# Phase 0.4 Pipeline
# ============================================

class Phase04Pipeline:
    """
    Phase 0.4 Pipeline with Golden Diff Integration
    
    Key improvements over Phase 0.3:
    - Golden Diff Engine for honest quality scores
    - No more hardcoded quality=100
    - External validation ready
    """
    
    # Golden Files directory
    GOLDEN_DIR = Path("golden_files")
    
    def __init__(self, pdf_processor, vlm_service):
        """
        Initialize Phase 0.4 Pipeline
        
        Args:
            pdf_processor: PDF processing service
            vlm_service: VLM service
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        
        # Initialize Golden Diff Engine
        if GOLDEN_DIFF_AVAILABLE:
            self.golden_engine = GoldenDiffEngine(threshold_mode='strict')
            logger.info("✅ Golden Diff Engine 초기화 완료")
        else:
            self.golden_engine = None
            logger.warning("⚠️ Golden Diff Engine 사용 불가")
        
        # Initialize Semantic Chunker v0.4
        self.chunker = SemanticChunker()
        
        logger.info(f"✅ Phase {VERSION} Pipeline 초기화 완료")
    
    def process(
        self,
        pdf_path: str,
        doc_id: Optional[str] = None,
        max_pages: int = 20
    ) -> Dict[str, Any]:
        """
        Process PDF document with Golden Diff validation
        
        Args:
            pdf_path: Path to PDF file
            doc_id: Document identifier (for Golden File lookup)
            max_pages: Maximum pages to process
        
        Returns:
            Processing result with honest quality scores
        """
        logger.info(f"🎯 Phase {VERSION} 처리 시작")
        logger.info(f"   파일: {pdf_path}")
        logger.info(f"   문서 ID: {doc_id}")
        
        start_time = datetime.now()
        
        # Step 1: Extract markdown (existing logic)
        # This would call your existing extraction pipeline
        # For now, we'll simulate it
        result_md = self._extract_markdown(pdf_path, max_pages)
        
        # Step 2: Semantic Chunking
        chunks = self.chunker.chunk(result_md)
        logger.info(f"   ✅ {len(chunks)}개 청크 생성")
        
        # Step 3: Golden Diff Validation
        quality_info = self._validate_with_golden(doc_id, result_md)
        
        # Step 4: Compile results
        result = {
            'markdown': result_md,
            'chunks': chunks,
            'quality': quality_info,
            'metadata': {
                'doc_id': doc_id,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'phase': VERSION,
                'golden_validated': quality_info['validated']
            }
        }
        
        logger.info(f"✅ Phase {VERSION} 처리 완료")
        
        return result
    
    def _extract_markdown(self, pdf_path: str, max_pages: int) -> str:
        """
        Extract markdown from PDF
        
        This is a placeholder - in real implementation,
        this would call your existing VLM + OCR pipeline
        
        Args:
            pdf_path: Path to PDF
            max_pages: Max pages
        
        Returns:
            Markdown string
        """
        # TODO: Integrate with existing hybrid_extractor logic
        logger.info("   📝 Markdown 추출 (기존 로직 연동 필요)")
        return ""
    
    def _validate_with_golden(
        self,
        doc_id: Optional[str],
        result_md: str
    ) -> Dict[str, Any]:
        """
        Validate result against Golden File
        
        Args:
            doc_id: Document identifier
            result_md: Processing result markdown
        
        Returns:
            Quality information dict
        """
        if not doc_id:
            return {
                'validated': False,
                'reason': 'No doc_id provided',
                'score': None,
                'pass': None
            }
        
        # Look for Golden File
        golden_path = self.GOLDEN_DIR / f"{doc_id}_golden.md"
        
        if not golden_path.exists():
            logger.warning(f"   ⚠️ Golden File 없음: {golden_path}")
            return {
                'validated': False,
                'reason': f'Golden File not found: {golden_path}',
                'score': None,
                'pass': None,
                'message': '⚠️ Golden File 생성 필요'
            }
        
        # Load Golden File
        golden_md = golden_path.read_text(encoding='utf-8')
        logger.info(f"   📄 Golden File 로드: {golden_path}")
        
        # Compare using Golden Diff Engine
        if not self.golden_engine:
            return {
                'validated': False,
                'reason': 'Golden Diff Engine not available',
                'score': None,
                'pass': None
            }
        
        diff_result = self.golden_engine.compare(golden_md, result_md)
        
        # Generate report
        report = self.golden_engine.generate_report(diff_result)
        logger.info(f"   📊 Golden Diff 결과:")
        logger.info(f"      Match Rate: {diff_result.match_rate * 100:.2f}%")
        logger.info(f"      Pass: {diff_result.pass_status}")
        logger.info(f"      Errors: {len(diff_result.errors)}")
        
        return {
            'validated': True,
            'score': round(diff_result.match_rate * 100, 2),
            'pass': diff_result.pass_status,
            'match_rate': diff_result.match_rate,
            'total_chars': diff_result.total_chars,
            'matched_chars': diff_result.matched_chars,
            'error_count': len(diff_result.errors),
            'errors': [e.to_dict() for e in diff_result.errors[:5]],  # First 5
            'critical_sections_ok': diff_result.critical_sections_ok,
            'report': report
        }

# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    # Example usage
    from .pdf_processor import PDFProcessor
    from .vlm_service import VLMService
    
    pdf_processor = PDFProcessor()
    vlm_service = VLMService(provider="azure_openai")
    
    pipeline = Phase04Pipeline(pdf_processor, vlm_service)
    
    result = pipeline.process(
        pdf_path="test.pdf",
        doc_id="인사규정_3페이지",
        max_pages=3
    )
    
    print("=" * 60)
    print("Phase 0.4 Pipeline Result")
    print("=" * 60)
    print(f"Quality Score: {result['quality']['score']}")
    print(f"Pass: {result['quality']['pass']}")
    print(f"Validated: {result['quality']['validated']}")

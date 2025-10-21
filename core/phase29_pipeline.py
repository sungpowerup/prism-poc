"""
core/phase29_pipeline.py
PRISM Phase 2.9 파이프라인 (간소화 버전)

Phase 2.8 파이프라인을 재사용하여 안정성 확보
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Phase 2.8 파이프라인 재사용
from core.phase28_pipeline import Phase28Pipeline
from core.smart_encoding_fixer import SmartEncodingFixer
from core.rag_optimized_chunker import RAGOptimizedChunker

logger = logging.getLogger(__name__)


class Phase29Pipeline:
    """
    PRISM Phase 2.9 처리 파이프라인
    
    Phase 2.8 기반 + 추가 기능:
    1. 스마트 인코딩 수정
    2. RAG 최적화 청킹
    """
    
    def __init__(self, vlm_provider: str = 'azure_openai'):
        """
        Args:
            vlm_provider: VLM 프로바이더
        """
        logger.info("="*60)
        logger.info("PRISM Phase 2.9 Pipeline 초기화")
        logger.info("="*60)
        
        # Phase 2.8 파이프라인 사용
        self.phase28 = Phase28Pipeline(vlm_provider=vlm_provider)
        logger.info("✅ Phase 2.8 파이프라인 로드")
        
        # Phase 2.9 추가 기능
        self.encoding_fixer = SmartEncodingFixer()
        logger.info("✅ 스마트 인코딩 수정기")
        
        self.chunker = RAGOptimizedChunker(
            min_chunk_size=100,
            max_chunk_size=800,
            overlap=50,
            preserve_structure=True
        )
        logger.info("✅ RAG 최적화 청킹 엔진")
        
        self.vlm_provider = vlm_provider
        
        logger.info("="*60)
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str = 'output',
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        PDF 문서 처리
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과
        """
        logger.info("\n" + "="*60)
        logger.info(f"📄 Phase 2.9 문서 처리: {Path(pdf_path).name}")
        logger.info("="*60)
        
        # Phase 2.8로 기본 처리
        phase28_result = self.phase28.process_pdf(
            pdf_path=pdf_path,
            output_dir=output_dir,
            max_pages=max_pages
        )
        
        # Phase 2.9 추가 처리
        
        # 1. 인코딩 수정
        logger.info("\n--- Phase 2.9: 인코딩 수정 ---")
        fixed_chunks = self._fix_encoding(phase28_result['stage2_chunks'])
        
        # 2. RAG 최적화 청킹
        logger.info("\n--- Phase 2.9: RAG 청킹 ---")
        rag_chunks = self._optimize_for_rag(fixed_chunks)
        
        # 결과 통합
        result = {
            'metadata': {
                'filename': Path(pdf_path).name,
                'phase': '2.9',
                'vlm_provider': self.vlm_provider,
                'processed_at': datetime.now().isoformat(),
                'total_pages': phase28_result['metadata']['total_pages'],
                'total_chunks': len(rag_chunks),
                'processing_time_sec': phase28_result['metadata']['processing_time_sec'],
                'encoding_fixes': self.encoding_fixer.base_fixer.get_stats()
            },
            'chunks': [chunk.to_dict() for chunk in rag_chunks]
        }
        
        # 저장
        self._save_results(result, output_dir)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Phase 2.9 처리 완료")
        logger.info(f"   청크: {len(rag_chunks)}개")
        logger.info(f"   인코딩 수정: {result['metadata']['encoding_fixes']['fixed']}건")
        logger.info("="*60)
        
        return result
    
    def _fix_encoding(self, chunks: List[Dict]) -> List[Dict]:
        """인코딩 수정"""
        fixed_chunks = []
        fix_count = 0
        
        for chunk in chunks:
            content = chunk.get('content', '')
            
            # 인코딩 수정
            fixed_content, confidence = self.encoding_fixer.fix_with_confidence(content)
            
            if fixed_content != content:
                fix_count += 1
                logger.info(f"청크 수정: 신뢰도 {confidence:.2%}")
            
            # 업데이트
            fixed_chunk = chunk.copy()
            fixed_chunk['content'] = fixed_content
            fixed_chunks.append(fixed_chunk)
        
        logger.info(f"인코딩 수정 완료: {fix_count}건")
        
        return fixed_chunks
    
    def _optimize_for_rag(self, chunks: List[Dict]) -> List:
        """RAG 최적화 청킹"""
        
        # 전체 텍스트 결합
        full_text = "\n\n".join([
            f"[페이지 {c.get('page_number', 1)}]\n{c.get('content', '')}"
            for c in chunks
        ])
        
        # RAG 청킹
        rag_chunks = self.chunker.chunk_with_structure(
            text=full_text,
            metadata={'source_chunks': len(chunks)}
        )
        
        logger.info(f"RAG 청킹 완료: {len(chunks)} → {len(rag_chunks)}개")
        
        return rag_chunks
    
    def _save_results(self, result: Dict, output_dir: str):
        """결과 저장"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = result['metadata']['filename']
        base_name = Path(filename).stem
        
        # JSON 저장
        json_path = Path(output_dir) / f"{base_name}_phase29.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 결과 저장: {json_path}")


# 사용 예시
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    pipeline = Phase29Pipeline(vlm_provider='azure_openai')
    
    result = pipeline.process_pdf(
        pdf_path='input/test.pdf',
        output_dir='output',
        max_pages=3
    )
    
    print(f"\n✅ 처리 완료: {result['metadata']['total_chunks']}개 청크")
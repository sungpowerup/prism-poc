"""
core/phase29_pipeline.py
PRISM Phase 2.9 - 구조화된 문서 처리 파이프라인

개선 사항 (vs Phase 2.8):
1. ✅ 구조화된 VLM 프롬프트 적용
2. ✅ 한글 인코딩 자동 수정
3. ✅ 섹션 기반 지능형 청킹
4. ✅ RAG 최적화 메타데이터
5. ✅ 차트별 독립 처리

Author: PRISM 개발팀 전원
Date: 2025-10-21
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from .pdf_processor import PDFProcessor
from .element_classifier import ElementClassifier
from .vlm_service import VLMService
from .structured_prompts import StructuredPrompts
from .encoding_fixer import EncodingFixer, SmartEncodingFixer
from .structural_chunker import RAGOptimizedChunker

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase29.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Phase29Pipeline:
    """
    Phase 2.9 처리 파이프라인
    
    Processing Flow:
    1. PDF → 페이지 이미지
    2. 페이지 이미지 → VLM 구조화 분석
    3. 인코딩 수정
    4. 구조 기반 청킹
    5. 메타데이터 풍부화
    """
    
    def __init__(self, vlm_provider: str = 'azure_openai'):
        """
        Args:
            vlm_provider: 'azure_openai', 'claude', 'ollama'
        """
        logger.info("="*60)
        logger.info("PRISM Phase 2.9 Pipeline 초기화")
        logger.info("="*60)
        
        # 1. VLM 서비스
        self.vlm_service = VLMService(provider=vlm_provider)
        self.vlm_provider = vlm_provider
        logger.info(f"✅ VLM 서비스: {vlm_provider}")
        
        # 2. PDF 프로세서
        try:
            self.pdf_processor = PDFProcessor(vlm_service=self.vlm_service)
        except TypeError:
            self.pdf_processor = PDFProcessor()
        logger.info("✅ PDF 프로세서 초기화")
        
        # 3. Element 분류기
        self.element_classifier = ElementClassifier(use_vlm=False)
        logger.info("✅ Element 분류기 초기화")
        
        # 4. 프롬프트 생성기
        self.prompt_builder = StructuredPrompts()
        logger.info("✅ 구조화된 프롬프트 생성기")
        
        # 5. 인코딩 수정기
        self.encoding_fixer = SmartEncodingFixer()
        logger.info("✅ 스마트 인코딩 수정기")
        
        # 6. 청킹 엔진
        self.chunker = RAGOptimizedChunker(
            min_chunk_size=100,
            max_chunk_size=800,
            overlap=50,
            preserve_structure=True
        )
        logger.info("✅ RAG 최적화 청킹 엔진")
        
        logger.info("="*60)
    
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str = 'output',
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        PDF 문서 전체 처리
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        
        logger.info("\n" + "="*60)
        logger.info(f"📄 문서 처리 시작: {Path(pdf_path).name}")
        logger.info("="*60)
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # Stage 1: PDF → 페이지 이미지 → VLM 분석
        stage1_results = self._stage1_vlm_analysis(pdf_path, max_pages)
        
        # Stage 2: 인코딩 수정
        stage2_results = self._stage2_fix_encoding(stage1_results)
        
        # Stage 3: 구조화된 청킹
        stage3_results = self._stage3_structural_chunking(stage2_results)
        
        # 통계 계산
        processing_time = time.time() - start_time
        stats = self._calculate_statistics(stage1_results, stage3_results, processing_time)
        
        # 결과 취합
        result = {
            'metadata': {
                'filename': Path(pdf_path).name,
                'total_pages': len(stage1_results),
                'total_chunks': len(stage3_results),
                'processing_time_sec': round(processing_time, 2),
                'vlm_provider': self.vlm_provider,
                'processed_at': datetime.now().isoformat(),
                'encoding_fixes': self.encoding_fixer.base_fixer.get_stats(),
                'phase': '2.9'
            },
            'stage1_vlm_analysis': [self._summarize_page(p) for p in stage1_results],
            'stage3_chunks': [chunk.to_dict() for chunk in stage3_results]
        }
        
        # 결과 저장
        self._save_results(result, output_dir)
        
        logger.info("\n" + "="*60)
        logger.info("✅ 문서 처리 완료")
        logger.info(f"   페이지: {result['metadata']['total_pages']}개")
        logger.info(f"   청크: {result['metadata']['total_chunks']}개")
        logger.info(f"   처리 시간: {processing_time:.2f}초")
        logger.info(f"   인코딩 수정: {stats['encoding_fixes']}건")
        logger.info("="*60)
        
        return result
    
    def _stage1_vlm_analysis(
        self,
        pdf_path: str,
        max_pages: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Stage 1: VLM 구조화 분석
        """
        logger.info("\n--- Stage 1: VLM 구조화 분석 ---")
        
        # PDF → 이미지 변환
        page_images = self.pdf_processor.pdf_to_images(pdf_path)
        
        if max_pages:
            page_images = page_images[:max_pages]
        
        logger.info(f"페이지 수: {len(page_images)}")
        
        results = []
        
        for page_num, page_image in enumerate(page_images, start=1):
            logger.info(f"\n[페이지 {page_num}/{len(page_images)}]")
            
            page_start_time = time.time()
            
            # 1. Element 분류 (전체 페이지)
            classification = self.element_classifier.classify_image(page_image)
            element_type = classification['type']
            confidence = classification['confidence']
            
            logger.info(f"  타입: {element_type} (신뢰도: {confidence:.2f})")
            
            # 2. 구조화된 프롬프트 생성
            prompt = self.prompt_builder.build_prompt_with_context(
                element_type=element_type,
                page_number=page_num,
                total_pages=len(page_images),
                detected_regions=1
            )
            
            # 3. VLM 분석
            logger.info(f"  VLM 분석 중... (프롬프트: {len(prompt)}자)")
            
            vlm_result = self.vlm_service.analyze_image(
                image=page_image,
                prompt=prompt
            )
            
            caption = vlm_result.get('text', '')
            tokens = vlm_result.get('tokens_used', 0)
            
            page_time = time.time() - page_start_time
            
            logger.info(f"  완료: {len(caption)}자 (토큰: {tokens}, {page_time:.2f}초)")
            
            results.append({
                'page_number': page_num,
                'element_type': element_type,
                'confidence': confidence,
                'caption': caption,
                'tokens_used': tokens,
                'processing_time_sec': page_time
            })
        
        logger.info(f"\nStage 1 완료: {len(results)}개 페이지 분석")
        
        return results
    
    def _stage2_fix_encoding(
        self,
        stage1_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: 인코딩 수정
        """
        logger.info("\n--- Stage 2: 인코딩 수정 ---")
        
        fixed_results = []
        fix_count = 0
        
        for page_data in stage1_results:
            caption = page_data['caption']
            
            # 인코딩 수정
            fixed_caption, confidence = self.encoding_fixer.fix_with_confidence(caption)
            
            if fixed_caption != caption:
                fix_count += 1
                logger.info(f"페이지 {page_data['page_number']}: 인코딩 수정 (신뢰도: {confidence:.2%})")
            
            # 결과 업데이트
            fixed_data = page_data.copy()
            fixed_data['caption'] = fixed_caption
            fixed_data['encoding_confidence'] = confidence
            
            fixed_results.append(fixed_data)
        
        logger.info(f"Stage 2 완료: {fix_count}개 페이지 인코딩 수정")
        
        return fixed_results
    
    def _stage3_structural_chunking(
        self,
        stage2_results: List[Dict[str, Any]]
    ) -> List:
        """
        Stage 3: 구조화된 청킹
        """
        logger.info("\n--- Stage 3: 구조화된 청킹 ---")
        
        all_chunks = []
        
        for page_data in stage2_results:
            page_num = page_data['page_number']
            caption = page_data['caption']
            element_type = page_data['element_type']
            
            # 구조 기반 청킹
            chunks = self.chunker.chunk_document(
                content=caption,
                page_number=page_num,
                element_type=element_type
            )
            
            # 추가 메타데이터
            for chunk in chunks:
                chunk.metadata['tokens_used'] = page_data['tokens_used']
                chunk.metadata['processing_time_sec'] = page_data['processing_time_sec']
                chunk.metadata['model_used'] = self.vlm_provider
            
            all_chunks.extend(chunks)
            
            logger.info(f"페이지 {page_num}: {len(chunks)}개 청크 생성")
        
        logger.info(f"Stage 3 완료: 총 {len(all_chunks)}개 청크")
        
        return all_chunks
    
    def _calculate_statistics(
        self,
        stage1_results: List[Dict],
        chunks: List,
        processing_time: float
    ) -> Dict[str, Any]:
        """통계 계산"""
        
        # 청크 타입 분포
        chunk_types = {}
        for chunk in chunks:
            etype = chunk.metadata.get('element_type', 'unknown')
            chunk_types[etype] = chunk_types.get(etype, 0) + 1
        
        # 인코딩 수정 통계
        encoding_fixes = self.encoding_fixer.base_fixer.get_stats()
        
        return {
            'total_pages': len(stage1_results),
            'total_chunks': len(chunks),
            'chunk_types': chunk_types,
            'avg_chunks_per_page': len(chunks) / len(stage1_results) if stage1_results else 0,
            'processing_time': processing_time,
            'avg_time_per_page': processing_time / len(stage1_results) if stage1_results else 0,
            'encoding_fixes': encoding_fixes['fixed']
        }
    
    def _summarize_page(self, page_data: Dict) -> Dict:
        """페이지 요약"""
        return {
            'page_number': page_data['page_number'],
            'element_type': page_data['element_type'],
            'confidence': round(page_data['confidence'], 2),
            'caption_length': len(page_data['caption']),
            'tokens_used': page_data['tokens_used'],
            'processing_time_sec': round(page_data['processing_time_sec'], 2)
        }
    
    def _save_results(self, result: Dict, output_dir: str):
        """
        결과 저장 (JSON + Markdown)
        
        Features:
        - UTF-8 BOM으로 저장
        - JSON과 MD 동시 생성
        - 타임스탬프 자동 추가
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = Path(result['metadata']['filename']).stem
        
        # JSON 저장 (UTF-8 BOM)
        json_path = Path(output_dir) / f"{filename}_phase29_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8-sig') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 JSON 저장: {json_path}")
        
        # Markdown 저장
        md_path = Path(output_dir) / f"{filename}_phase29_{timestamp}.md"
        md_content = self._generate_markdown(result)
        
        with open(md_path, 'w', encoding='utf-8-sig') as f:
            f.write(md_content)
        
        logger.info(f"💾 Markdown 저장: {md_path}")
    
    def _generate_markdown(self, result: Dict) -> str:
        """
        Markdown 형식으로 결과 생성
        
        Format:
        - 문서 정보
        - 청크별 섹션
        - 구조화된 레이아웃
        """
        lines = []
        
        # 헤더
        lines.append("# PRISM Phase 2.9 - 구조화된 문서 추출 결과")
        lines.append("")
        lines.append(f"**생성일시**: {result['metadata']['processed_at'][:19]}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 문서 정보
        lines.append("## 📄 문서 정보")
        lines.append("")
        lines.append(f"- **파일명**: {result['metadata']['filename']}")
        lines.append(f"- **총 페이지**: {result['metadata']['total_pages']}개")
        lines.append(f"- **총 청크**: {result['metadata']['total_chunks']}개")
        lines.append(f"- **처리 시간**: {result['metadata']['processing_time_sec']:.2f}초")
        lines.append(f"- **VLM 프로바이더**: {result['metadata']['vlm_provider']}")
        lines.append(f"- **인코딩 수정**: {result['metadata']['encoding_fixes']['fixed']}건")
        lines.append(f"- **Phase**: {result['metadata']['phase']}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 청크
        lines.append("## 🧩 구조화된 청크")
        lines.append("")
        
        for i, chunk_dict in enumerate(result['stage3_chunks'], start=1):
            lines.append(f"### 청크 #{i}")
            lines.append("")
            
            metadata = chunk_dict['metadata']
            
            lines.append(f"**페이지**: {metadata['page_number']}")
            lines.append(f"**타입**: {metadata['element_type']}")
            lines.append(f"**모델**: {metadata.get('model_used', 'N/A')}")
            
            # 섹션 정보
            if metadata.get('section_title'):
                lines.append(f"**섹션**: {metadata['section_title']}")
            
            # 차트 정보
            if metadata.get('chart_type'):
                lines.append(f"**차트 타입**: {metadata['chart_type']}")
            
            # 키워드
            if metadata.get('keywords'):
                keywords = ', '.join(metadata['keywords'][:5])
                lines.append(f"**키워드**: {keywords}")
            
            lines.append("")
            lines.append("**내용**:")
            lines.append("")
            lines.append("```")
            lines.append(chunk_dict['content'])
            lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)


# CLI 실행
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python phase29_pipeline.py <pdf_path> [output_dir] [vlm_provider]")
        print("예시: python phase29_pipeline.py input/test.pdf output azure_openai")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    vlm_provider = sys.argv[3] if len(sys.argv) > 3 else 'azure_openai'
    
    # 파이프라인 실행
    pipeline = Phase29Pipeline(vlm_provider=vlm_provider)
    result = pipeline.process_pdf(pdf_path, output_dir)
    
    print("\n" + "="*60)
    print("🎉 처리 완료!")
    print("="*60)
    print(f"페이지: {result['metadata']['total_pages']}")
    print(f"청크: {result['metadata']['total_chunks']}")
    print(f"시간: {result['metadata']['processing_time_sec']:.2f}초")
    print("="*60)
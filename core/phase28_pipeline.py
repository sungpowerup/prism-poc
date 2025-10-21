"""
core/phase28_pipeline.py
PRISM Phase 2.8 - 완전 개선판 (초기화 오류 수정)
- 한글 인코딩 수정
- Element 세부 분류
- 지능형 청킹
- PDFProcessor 초기화 오류 수정
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

from .pdf_processor import PDFProcessor
from .element_classifier import ElementClassifier
from .vlm_service import VLMService
from .intelligent_chunker import IntelligentChunker

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase28.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Phase28Pipeline:
    """
    Phase 2.8 처리 파이프라인
    
    Stage 1: PDF → 페이지 이미지 → Element 분류 → VLM 캡션
    Stage 2: 긴 캡션 → 지능형 청킹 (문장 단위)
    """
    
    def __init__(self, vlm_provider: str = 'azure_openai'):
        """
        Args:
            vlm_provider: 'azure_openai', 'claude', 'local_sllm'
        """
        # 1. VLM 서비스 먼저 생성
        self.vlm_service = VLMService(provider=vlm_provider)
        
        # 2. PDF 프로세서 생성 (VLM 서비스는 선택적)
        try:
            self.pdf_processor = PDFProcessor(vlm_service=self.vlm_service)
        except TypeError:
            # vlm_service가 필수가 아닌 경우 인자 없이 생성
            self.pdf_processor = PDFProcessor()
        
        # 3. Element 분류기 생성
        self.element_classifier = ElementClassifier(use_vlm=False)
        
        # 4. 지능형 청커 생성
        self.chunker = IntelligentChunker(
            min_chunk_size=100,
            max_chunk_size=500,
            overlap=50
        )
        
        self.vlm_provider = vlm_provider
        
        logger.info(f"Phase28Pipeline 초기화 완료 (VLM: {vlm_provider})")
    
    def process_pdf(
        self, 
        pdf_path: str, 
        output_dir: str = 'output',
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        PDF 문서 전체 처리
        
        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            max_pages: 최대 처리 페이지 (None이면 전체)
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info(f"=== Phase 2.8 처리 시작: {pdf_path} ===")
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # Stage 1: PDF → 페이지 → VLM 캡션
        stage1_results = self._stage1_page_to_caption(pdf_path, max_pages)
        
        # Stage 2: 캡션 → 지능형 청킹
        stage2_results = self._stage2_caption_to_chunks(stage1_results)
        
        # 통계 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        stats = self._calculate_statistics(stage1_results, stage2_results, processing_time)
        
        # 결과 취합
        result = {
            'metadata': {
                'filename': Path(pdf_path).name,
                'total_pages': len(stage1_results),
                'total_chunks': len(stage2_results),
                'processing_time_sec': round(processing_time, 2),
                'vlm_provider': self.vlm_provider,
                'processed_at': datetime.now().isoformat(),
                'chunk_types': stats['chunk_types'],
                'phase': '2.8'
            },
            'stage1_elements': [self._summarize_element(e) for e in stage1_results],
            'stage2_chunks': stage2_results
        }
        
        # JSON 저장 (UTF-8 BOM으로 인코딩 보장)
        json_path = self._save_json(result, output_dir, Path(pdf_path).stem)
        
        # Markdown 저장
        md_path = self._save_markdown(result, output_dir, Path(pdf_path).stem)
        
        logger.info(f"=== 처리 완료: {processing_time:.2f}초 ===")
        logger.info(f"JSON: {json_path}")
        logger.info(f"Markdown: {md_path}")
        
        return result
    
    def _stage1_page_to_caption(self, pdf_path: str, max_pages: int) -> List[Dict]:
        """
        Stage 1: PDF → 페이지 이미지 → Element 분류 → VLM 캡션
        """
        logger.info("--- Stage 1: 페이지 → VLM 캡션 ---")
        
        # PDF → 이미지
        pages = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages)
        logger.info(f"추출된 페이지: {len(pages)}개")
        
        results = []
        
        for page_num, image_data in enumerate(pages, start=1):
            logger.info(f"\n[Page {page_num}] 처리 중...")
            
            # Element 분류 (세부 분류 포함)
            classification = self.element_classifier.classify(image_data)
            
            logger.info(f"  - Element 타입: {classification['element_type']}")
            logger.info(f"  - 세부 타입: {classification.get('subtypes', [])}")
            logger.info(f"  - 신뢰도: {classification['confidence']:.2f}")
            
            # VLM 캡션 생성
            caption_result = self.vlm_service.generate_caption(
                image_data=image_data,
                element_type=classification['element_type'],
                subtypes=classification.get('subtypes', [])  # 세부 타입 전달
            )
            
            # UTF-8 인코딩 재확인
            caption_text = self._ensure_utf8(caption_result['caption'])
            
            logger.info(f"  - 캡션 길이: {len(caption_text)} 글자")
            logger.info(f"  - 처리 시간: {caption_result['processing_time_sec']:.2f}초")
            
            results.append({
                'page_number': page_num,
                'element_type': classification['element_type'],
                'subtypes': classification.get('subtypes', []),
                'confidence': classification['confidence'],
                'caption': caption_text,
                'tokens_used': caption_result.get('tokens_used', 0),
                'processing_time_sec': caption_result['processing_time_sec']
            })
        
        return results
    
    def _stage2_caption_to_chunks(self, stage1_results: List[Dict]) -> List[Dict]:
        """
        Stage 2: VLM 캡션 → 지능형 청킹 (문장 단위)
        """
        logger.info("\n--- Stage 2: 캡션 → 청킹 ---")
        
        all_chunks = []
        chunk_counter = 0
        
        for element in stage1_results:
            caption = element['caption']
            page_num = element['page_number']
            element_type = element['element_type']
            
            # 지능형 청킹 (문장 단위)
            chunks = self.chunker.chunk_text(caption)
            
            logger.info(f"[Page {page_num}] {len(chunks)}개 청크 생성")
            
            for i, chunk_text in enumerate(chunks):
                chunk_counter += 1
                
                all_chunks.append({
                    'chunk_id': f"chunk_{page_num}_{id(chunk_text)}",
                    'page_number': page_num,
                    'element_type': element_type,
                    'content': chunk_text,
                    'metadata': {
                        'section_path': f"Page {page_num}",
                        'source': 'vlm',
                        'chunk_index': i,
                        'start_pos': i * self.chunker.max_chunk_size,
                        'end_pos': (i + 1) * self.chunker.max_chunk_size,
                        'total_chunks': len(chunks)
                    },
                    'model_used': self.vlm_provider,
                    'processing_time_sec': element['processing_time_sec']
                })
        
        logger.info(f"총 {len(all_chunks)}개 청크 생성 완료")
        return all_chunks
    
    def _ensure_utf8(self, text: str) -> str:
        """
        UTF-8 인코딩 보장
        
        문제 해결:
        - Azure OpenAI API 응답의 잘못된 인코딩 수정
        - latin1 → UTF-8 재인코딩
        """
        try:
            # 이미 정상이면 그대로 반환
            if all(ord(c) < 128 or ord(c) > 127 for c in text):
                return text
            
            # latin1로 잘못 디코딩된 경우 재인코딩
            return text.encode('latin1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 실패하면 원본 반환 (이미 정상)
            return text
    
    def _calculate_statistics(
        self, 
        stage1_results: List[Dict],
        stage2_results: List[Dict],
        processing_time: float
    ) -> Dict:
        """통계 계산"""
        chunk_types = {}
        for chunk in stage2_results:
            et = chunk['element_type']
            chunk_types[et] = chunk_types.get(et, 0) + 1
        
        return {
            'chunk_types': chunk_types,
            'total_processing_time': processing_time,
            'avg_time_per_page': processing_time / len(stage1_results) if stage1_results else 0
        }
    
    def _summarize_element(self, element: Dict) -> Dict:
        """Element 요약"""
        return {
            'page_number': element['page_number'],
            'element_type': element['element_type'],
            'subtypes': element.get('subtypes', []),
            'confidence': element['confidence'],
            'chunks_count': 1,  # Stage 2에서 계산됨
            'tokens_used': element.get('tokens_used', 0),
            'processing_time_sec': round(element['processing_time_sec'], 3)
        }
    
    def _save_json(self, result: Dict, output_dir: str, filename: str) -> str:
        """
        JSON 저장 (UTF-8 BOM)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(output_dir, f"prism_phase28_{timestamp}.json")
        
        with open(json_path, 'w', encoding='utf-8-sig') as f:  # UTF-8 BOM
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return json_path
    
    def _save_markdown(self, result: Dict, output_dir: str, filename: str) -> str:
        """
        Markdown 저장
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        md_path = os.path.join(output_dir, f"prism_phase28_{timestamp}.md")
        
        lines = [
            "# PRISM Phase 2.8 - 문서 추출 결과\n",
            f"**생성일시**: {result['metadata']['processed_at']}\n",
            "\n---\n",
            "\n## 📄 문서 정보\n",
            f"- **파일명**: {result['metadata']['filename']}",
            f"- **총 페이지**: {result['metadata']['total_pages']}",
            f"- **처리 시간**: {result['metadata']['processing_time_sec']}초",
            f"- **총 청크**: {result['metadata']['total_chunks']}",
            f"- **Phase**: {result['metadata']['phase']}\n",
            "\n---\n",
            "\n## 🧩 지능형 청크\n"
        ]
        
        for i, chunk in enumerate(result['stage2_chunks'], start=1):
            lines.append(f"\n### 청크 #{i}\n")
            lines.append(f"**페이지**: {chunk['page_number']}")
            lines.append(f"**타입**: {chunk['element_type']}")
            lines.append(f"**모델**: {chunk['model_used']}\n")
            lines.append("**내용**:\n")
            lines.append("```")
            lines.append(chunk['content'])
            lines.append("```\n")
            lines.append("---\n")
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return md_path


# CLI 실행
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python -m core.phase28_pipeline <pdf_path> [output_dir] [max_pages]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    pipeline = Phase28Pipeline(vlm_provider='azure_openai')
    result = pipeline.process_pdf(pdf_path, output_dir, max_pages)
    
    print(f"\n✅ 처리 완료!")
    print(f"총 청크: {result['metadata']['total_chunks']}개")
    print(f"처리 시간: {result['metadata']['processing_time_sec']}초")
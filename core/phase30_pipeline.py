"""
PRISM Phase 3.0 - Main Pipeline (수정)
차트 타입 구분 + UTF-8 처리
"""

import os
import json
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

from core.pdf_processor import PDFProcessor
from core.layout_detector import LayoutDetector
from core.vlm_service import VLMService
from core.section_chunker import SectionChunker
from prompts.chart_prompt import ChartPrompts

logger = logging.getLogger(__name__)


class Phase30Pipeline:
    """
    PRISM Phase 3.0 파이프라인
    - 차트 타입 구분
    - UTF-8 인코딩 처리
    - 타입별 프롬프트
    """
    
    def __init__(self, vlm_provider: str = "azure_openai"):
        """
        Phase 3.0 파이프라인 초기화
        
        Args:
            vlm_provider: VLM 프로바이더
        """
        logger.info("="*60)
        logger.info("PRISM Phase 3.0 Pipeline 초기화")
        logger.info("="*60)
        
        # 컴포넌트 초기화
        self.pdf_processor = PDFProcessor()
        logger.info("✅ PDF Processor")
        
        self.vlm_service = VLMService(provider=vlm_provider)
        logger.info(f"✅ VLM Service ({vlm_provider})")
        
        self.layout_detector = LayoutDetector()
        logger.info("✅ Layout Detector")
        
        self.chunker = SectionChunker()
        logger.info("✅ Section-aware Chunker")
        
        logger.info("="*60 + "\n")
    
    def process_document(
        self,
        pdf_path: str,
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        문서 처리 (전체 파이프라인)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            
        Returns:
            처리 결과
        """
        start_time = time.time()
        
        filename = Path(pdf_path).name
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 PRISM Phase 3.0 문서 처리")
        logger.info(f"   파일: {filename}")
        logger.info(f"{'='*60}")
        
        # Stage 1: PDF → Images
        logger.info(f"\n--- Stage 1: PDF → Page Images ---")
        page_images = self.pdf_processor.pdf_to_images(pdf_path)
        
        if max_pages:
            page_images = page_images[:max_pages]
        
        # PIL Image → numpy array 변환
        import numpy as np
        from PIL import Image
        
        converted_images = []
        for img in page_images:
            if isinstance(img, str):
                # Base64 문자열인 경우
                img_bytes = base64.b64decode(img)
                pil_img = Image.open(io.BytesIO(img_bytes))
                np_img = np.array(pil_img)
            elif hasattr(img, 'convert'):
                # PIL Image인 경우
                np_img = np.array(img.convert('RGB'))
            else:
                # 이미 numpy array인 경우
                np_img = img
            
            converted_images.append(np_img)
        
        page_images = converted_images
        
        logger.info(f"✅ {len(page_images)}개 페이지 변환 완료 (numpy array)\n")
        
        # Stage 2~3: 페이지별 처리
        all_regions = []
        all_extractions = []
        
        for page_num, page_image in enumerate(page_images, 1):
            logger.info(f"{'='*60}")
            logger.info(f"페이지 {page_num}/{len(page_images)} 처리")
            logger.info(f"{'='*60}")
            
            # Stage 2: Layout Detection
            logger.info(f"\n--- Stage 2: Layout Detection ---")
            regions = self.layout_detector.detect_regions(page_image, page_num)
            
            # 각 영역에 page_number 추가
            for region in regions:
                region['page_number'] = page_num
            
            all_regions.extend(regions)
            
            # Stage 3: Region-based Extraction
            logger.info(f"\n--- Stage 3: Region-based Extraction ---")
            
            for i, region in enumerate(regions, 1):
                logger.info(f"\n[Region {i}/{len(regions)}] {region['type']}")
                
                # 영역 크롭
                x, y, w, h = region['bbox']
                roi = page_image[y:y+h, x:x+w]
                
                # Base64 인코딩
                from PIL import Image
                import io
                
                pil_roi = Image.fromarray(roi)
                buffer = io.BytesIO()
                pil_roi.save(buffer, format='PNG')
                roi_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # VLM 분석
                element_type = region['type']
                prompt = ChartPrompts.get_prompt_for_type(element_type)
                
                try:
                    content = self.vlm_service.analyze_image(
                        roi_base64,
                        element_type,
                        prompt
                    )
                    
                    # UTF-8 검증
                    content = self._ensure_utf8(content)
                    
                    # 특수 처리: 지도 타입
                    if element_type == "map":
                        content = self._process_map_content(content)
                    
                    logger.info(f"   추출 완료: {len(content)}자")
                
                except Exception as e:
                    logger.error(f"   추출 실패: {str(e)}")
                    content = f"[{element_type} 추출 실패]"
                
                # 추출 결과 저장
                extraction = {
                    'page_number': page_num,
                    'region_number': i,
                    'region_type': element_type,
                    'bbox': region['bbox'],
                    'content': content,
                    'metadata': region.get('metadata', {})
                }
                
                all_extractions.append(extraction)
        
        # Stage 4: Section-aware Chunking
        logger.info(f"\n{'='*60}")
        logger.info(f"--- Stage 4: Section-aware Chunking ---")
        logger.info(f"{'='*60}")
        
        chunks = self.chunker.chunk_extractions(all_extractions)
        
        logger.info(f"\n✅ {len(chunks)}개 청크 생성 완료")
        
        # 결과 생성
        total_time = time.time() - start_time
        
        result = {
            'metadata': {
                'filename': filename,
                'phase': '3.0',
                'vlm_provider': self.vlm_service.provider,
                'processed_at': datetime.now().isoformat(),
                'total_pages': len(page_images),
                'total_regions': len(all_regions),
                'total_chunks': len(chunks),
                'processing_time_sec': round(total_time, 2)
            },
            'regions': [
                {
                    'region_id': f"page{r['page_number']}_{r['type']}{i}",
                    'bbox': r['bbox'],
                    'type': r['type'],
                    'confidence': r['confidence'],
                    'metadata': r.get('metadata', {})
                }
                for i, r in enumerate(all_regions, 1)
            ],
            'extractions': all_extractions,
            'chunks': chunks
        }
        
        # 결과 저장
        self._save_results(result)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Phase 3.0 처리 완료")
        logger.info(f"   총 처리 시간: {total_time:.2f}초")
        logger.info(f"   감지된 영역: {len(all_regions)}개")
        logger.info(f"   생성된 청크: {len(chunks)}개")
        logger.info(f"{'='*60}")
        
        return result
    
    def _process_map_content(self, content: str) -> str:
        """
        지도 콘텐츠 특수 처리
        
        Args:
            content: VLM 응답
            
        Returns:
            처리된 콘텐츠
        """
        try:
            # JSON 형식 추출 시도
            data = self.vlm_service.extract_map_data(content)
            
            if 'regions' in data and data['regions']:
                # JSON 데이터를 자연어로 변환
                lines = ["[지역별 분포]"]
                for region in data['regions']:
                    name = region.get('name', '')
                    value = region.get('value', '')
                    lines.append(f"- {name}: {value}")
                
                return "\n".join(lines)
            else:
                # JSON이 아닌 자연어 텍스트
                return content
        
        except Exception as e:
            logger.error(f"   지도 데이터 처리 실패: {e}")
            return content
    
    def _ensure_utf8(self, text: str) -> str:
        """
        UTF-8 인코딩 보장
        
        Args:
            text: 입력 텍스트
            
        Returns:
            UTF-8 텍스트
        """
        try:
            text.encode('utf-8').decode('utf-8')
            return text
        except UnicodeDecodeError:
            # Latin-1 → UTF-8 변환
            try:
                return text.encode('latin-1').decode('utf-8')
            except:
                # 강제 변환
                return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    
    def _save_results(self, result: Dict[str, Any]):
        """
        결과 저장 (JSON + Markdown)
        
        Args:
            result: 처리 결과
        """
        # 출력 디렉토리
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 타임스탬프
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"prism_phase30_{timestamp}"
        
        # JSON 저장
        json_path = output_dir / f"{base_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 결과 저장: {json_path}")
        
        # Markdown 저장
        md_path = output_dir / f"{base_name}.md"
        md_content = self._generate_markdown(result)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"💾 마크다운: {md_path}")
    
    def _generate_markdown(self, result: Dict[str, Any]) -> str:
        """
        Markdown 생성
        
        Args:
            result: 처리 결과
            
        Returns:
            Markdown 문자열
        """
        lines = [
            "# PRISM Phase 3.0 - 구조화된 문서 추출\n",
            f"**생성일시**: {result['metadata']['processed_at']}\n",
            "---\n",
            "## 📄 문서 정보\n",
            f"- **파일명**: {result['metadata']['filename']}",
            f"- **총 페이지**: {result['metadata']['total_pages']}개",
            f"- **총 영역**: {result['metadata']['total_regions']}개",
            f"- **총 청크**: {result['metadata']['total_chunks']}개",
            f"- **처리 시간**: {result['metadata']['processing_time_sec']}초",
            f"- **Phase**: {result['metadata']['phase']}\n",
            "## 🎯 감지된 영역\n"
        ]
        
        # 영역 목록
        for i, region in enumerate(result['regions'], 1):
            lines.append(f"### Region #{i}: {region['type']}\n")
            lines.append(f"- **ID**: {region['region_id']}")
            lines.append(f"- **신뢰도**: {region['confidence']*100:.2f}%")
            lines.append(f"- **위치**: {tuple(region['bbox'])}\n")
        
        # 청크 목록
        lines.append("## 🧩 청크\n")
        
        for i, chunk in enumerate(result['chunks'], 1):
            lines.append(f"### 청크 #{i}\n")
            lines.append(f"- **ID**: {chunk['chunk_id']}")
            lines.append(f"- **타입**: {chunk['metadata']['chunk_type']}")
            lines.append(f"- **섹션**: {chunk['metadata']['section_path']}")
            lines.append(f"- **페이지**: {chunk['metadata']['page_number']}\n")
            lines.append("```")
            lines.append(chunk['content'])
            lines.append("```\n")
        
        return "\n".join(lines)
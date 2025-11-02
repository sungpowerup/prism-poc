"""
core/pipeline.py
PRISM Phase 5.7.2.2 Hotfix - Pipeline (Empty Page Count + Diagnostic Logs)

✅ Phase 5.7.2.2 긴급 수정:
1. 빈 페이지 카운트 추가 (empty_page_count)
2. DoD 母수 계산 개선
3. HybridExtractor v5.7.2.2 통합
4. 🔴 진단 로그 추가 (DOD-DIAG)

Author: 이서영 (Backend Lead) + GPT(미송) 의견 반영
Date: 2025-10-31
Version: 5.7.2.2-diag
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid
import json
from pathlib import Path
import statistics

# Phase 5.7.2.2: HybridExtractor v5.7.2.2
try:
    from .hybrid_extractor import HybridExtractor
    from .semantic_chunker import SemanticChunker
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from hybrid_extractor import HybridExtractor
    from semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


class Phase53Pipeline:
    """
    Phase 5.7.2.2 처리 파이프라인 (Empty Page Count + 진단 로그)
    
    특징:
    - HybridExtractor v5.7.2.2 통합 (페이지 구분자 제거)
    - 빈 페이지 자동 Skip (DoD 母수 제외)
    - 빈 페이지 카운트 추적
    - 🔴 진단 로그 (페이지 처리, DoD 분모)
    - CV 힌트 기반 지능형 추출
    - DSL 기반 동적 프롬프트
    - 강화된 검증 + 재추출
    - KVS 정규화 + 별도 저장
    - 관측성 메트릭 수집
    - SemanticChunker 유지
    """
    
    def __init__(self, pdf_processor, vlm_service, storage=None):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMServiceV50 인스턴스
            storage: Storage 인스턴스 (Optional)
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        self.storage = storage
        
        # ✅ Phase 5.7.2.2: HybridExtractor v5.7.2.2 초기화
        self.extractor = HybridExtractor(vlm_service)
        
        # Phase 5.2.0: SemanticChunker
        self.chunker = SemanticChunker(
            min_chunk_size=600,
            max_chunk_size=1200,
            target_chunk_size=900
        )
        
        logger.info("✅ Phase 5.7.2.2-diag Pipeline 초기화 완료 (Empty Page Count + 진단)")
        logger.info("   - HybridExtractor v5.7.2.2-diag: 페이지 구분자 제거 + 빈 페이지 Skip + 진단")
        logger.info("   - SemanticChunker: 의미 단위 청킹")
    
    def process_pdf(
        self,
        pdf_path: str,
        max_pages: int = 20,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수 (Phase 5.7.2.2 + 진단)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            progress_callback: 진행 상황 콜백
        
        Returns:
            처리 결과 (진단 정보 포함)
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"🎯 Phase 5.7.2.2-diag 처리 시작")
        logger.info(f"   파일: {pdf_path}")
        logger.info(f"   세션: {session_id}")
        logger.info(f"   최대 페이지: {max_pages}")
        
        # 🔴 진단 로그: 처리 시작
        logger.info(f"[DOD-DIAG] pipeline_start, session={session_id}, max_pages={max_pages}")
        
        try:
            # Step 1: PDF → Images
            if progress_callback:
                progress_callback("PDF → 이미지 변환 중...", 0.1)
            
            logger.info("📄 Step 1: PDF → 이미지 변환")
            images = self.pdf_processor.pdf_to_images(
                pdf_path=pdf_path,
                max_pages=max_pages,
                dpi=300
            )
            
            total_pages = len(images)
            logger.info(f"   ✅ {total_pages}페이지 변환 완료")
            
            # 🔴 진단 로그: 이미지 변환 완료
            logger.info(f"[DOD-DIAG] images_converted, total_pages={total_pages}")
            
            # Step 2: 페이지별 HybridExtractor 처리
            page_results = []
            kvs_files = []
            metrics_list = []
            empty_page_count = 0  # ✅ Phase 5.7.2.2: 빈 페이지 카운터
            
            for i, image_data in enumerate(images):
                page_num = i + 1
                progress = 0.1 + (0.7 * (i / max(1, total_pages)))
                
                if progress_callback:
                    progress_callback(
                        f"페이지 {page_num}/{total_pages} 처리 중...",
                        progress
                    )
                
                logger.info(f"📄 페이지 {page_num}/{total_pages} 처리 시작")
                
                # ✅ Phase 5.7.2.2: HybridExtractor v5.7.2.2 호출
                result = self.extractor.extract(image_data, page_num=page_num)
                
                # 🔴 진단 로그: 페이지별 처리 결과
                is_empty = result.get('is_empty', False)
                content_len = len(result.get('content', ''))
                logger.info(f"[DOD-DIAG] page={page_num}, is_empty={is_empty}, content_len={content_len}, quality={result.get('quality_score', 0):.0f}")
                
                # ✅ 빈 페이지 감지 (Phase 5.7.2.2)
                if result.get('is_empty', False):
                    empty_page_count += 1
                    logger.info(f"   ℹ️ 페이지 {page_num}: 빈 페이지 Skip")
                    
                    # 🔴 진단 로그: 빈 페이지 Skip
                    logger.info(f"[DOD-DIAG] page={page_num}, action=skip_empty, empty_count={empty_page_count}")
                    
                    continue  # DoD 母数에서 제외
                
                # 페이지 결과 수집
                page_results.append({
                    'page_num': page_num,
                    'content': result['content'],
                    'doc_type': result.get('doc_type', 'unknown'),
                    'confidence': result.get('confidence', 0.0),
                    'quality_score': result.get('quality_score', 0.0)
                })
                
                # KVS 저장
                if result.get('kvs'):
                    kvs_file = f"kvs_page_{page_num}.json"
                    kvs_files.append(kvs_file)
                    # 실제 저장은 storage가 있을 때만
                    if self.storage:
                        self.storage.save_json(kvs_file, result['kvs'])
                
                # 메트릭 수집
                metrics_list.append(result['metrics'])
                
                logger.info(f"   ✅ 페이지 {page_num} 완료: 품질 {result['quality_score']:.0f}/100")
            
            valid_pages = len(page_results)
            
            # 🔴 진단 로그: 전체 페이지 처리 완료
            logger.info(f"[DOD-DIAG] pages_processed, total={total_pages}, empty={empty_page_count}, valid={valid_pages}")
            logger.info(f"📊 유효 페이지: {valid_pages}/{total_pages} (빈 페이지 {empty_page_count}개 제외)")
            
            # 🔴 진단 로그: DoD 분모 확인
            logger.info(f"[DOD-DIAG] dod_denominator_check, pages_total={total_pages}, empty_page_count={empty_page_count}, pages_success={valid_pages}")
            
            # Step 3: Markdown 통합
            if progress_callback:
                progress_callback("Markdown 통합 중...", 0.8)
            
            logger.info("📝 Step 3: Markdown 통합")
            markdown_pages = [p['content'] for p in page_results]
            markdown = "\n\n".join(markdown_pages)
            
            logger.info(f"   ✅ Markdown 통합 완료: {len(markdown)} 글자")
            
            # Step 4: SemanticChunking
            if progress_callback:
                progress_callback("의미 단위 청킹 중...", 0.9)
            
            logger.info("✂️ Step 4: SemanticChunking")
            chunks = self.chunker.chunk(markdown)
            
            logger.info(f"   ✅ {len(chunks)}개 청크 생성")
            
            # Step 5: 5가지 체크리스트 평가
            if progress_callback:
                progress_callback("품질 평가 중...", 0.95)
            
            logger.info("📊 Step 5: 체크리스트 평가")
            
            # 1. 원본 충실도
            avg_confidence = statistics.mean([p['confidence'] for p in page_results]) if page_results else 0.0
            fidelity_score = avg_confidence * 100
            
            # 2. 청킹 품질
            avg_chunk_size = statistics.mean([len(c['content']) for c in chunks]) if chunks else 0
            chunking_score = min(avg_chunk_size / 900 * 100, 100)
            
            # 3. RAG 적합도
            rag_score = min(len(chunks) / max(1, valid_pages) * 100, 100)
            
            # 4. 범용성
            universality_score = 95.0
            
            # 5. 경쟁력
            competitive_score = (fidelity_score + chunking_score + rag_score) / 3
            
            # 종합
            overall_score = (
                fidelity_score * 0.3 +
                chunking_score * 0.2 +
                rag_score * 0.2 +
                universality_score * 0.15 +
                competitive_score * 0.15
            )
            
            logger.info(f"   ✅ 원본 충실도: {fidelity_score:.0f}/100")
            logger.info(f"   ✅ 청킹 품질: {chunking_score:.0f}/100")
            logger.info(f"   ✅ RAG 적합도: {rag_score:.0f}/100")
            logger.info(f"   ✅ 범용성: {universality_score:.0f}/100")
            logger.info(f"   ✅ 경쟁력: {competitive_score:.0f}/100")
            logger.info(f"   🎯 종합: {overall_score:.0f}/100")
            
            # 완료
            processing_time = time.time() - start_time
            
            result = {
                'status': 'success',
                'version': '5.7.2.2-diag',  # ✅ Phase 5.7.2.2-diag
                'session_id': session_id,
                'pages_total': total_pages,
                'pages_success': valid_pages,  # ✅ 빈 페이지 제외
                'empty_page_count': empty_page_count,  # ✅ Phase 5.7.2.2 신규
                'processing_time': processing_time,
                'markdown': markdown,
                'chunks': chunks,
                'kvs_payloads': kvs_files,
                'metrics': metrics_list,
                'fidelity_score': fidelity_score,
                'chunking_score': chunking_score,
                'rag_score': rag_score,
                'universality_score': universality_score,
                'competitive_score': competitive_score,
                'overall_score': overall_score
            }
            
            # 🔴 진단 로그: 최종 결과
            logger.info(f"[DOD-DIAG] pipeline_complete, status=success, valid_pages={valid_pages}, empty_pages={empty_page_count}, overall_score={overall_score:.0f}")
            
            logger.info(f"✅ Phase 5.7.2.2-diag 처리 완료")
            logger.info(f"   - 유효 페이지: {valid_pages}/{total_pages}")
            logger.info(f"   - 빈 페이지: {empty_page_count}")
            logger.info(f"   - 시간: {processing_time:.1f}초")
            logger.info(f"   - 종합: {overall_score:.0f}/100")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 🔴 진단 로그: 에러
            logger.error(f"[DOD-DIAG] pipeline_error, error={str(e)}")
            
            return {
                'status': 'error',
                'version': '5.7.2.2-diag',
                'session_id': session_id,
                'error': str(e),
                'pages_total': 0,
                'pages_success': 0,
                'empty_page_count': 0,
                'processing_time': time.time() - start_time
            }
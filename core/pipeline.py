"""
core/pipeline.py
PRISM Phase 4.5 - Pipeline (품질 점수 수정)

✅ Phase 4.5 개선사항:
1. 품질 점수 계산 버그 수정
2. VLM Service v4.5 통합
3. 검증 강화

Author: 이서영 (Backend Lead)
Date: 2025-10-23
Version: 4.5
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid
import re

logger = logging.getLogger(__name__)


class Phase45Pipeline:
    """
    Phase 4.5 처리 파이프라인
    
    특징:
    - OCR + VLM 하이브리드
    - 품질 점수 정확 계산
    - 검증 강화
    """
    
    def __init__(self, pdf_processor, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMServiceV45 인스턴스
            storage: Storage 인스턴스
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        self.storage = storage
    
    def process_pdf(
        self,
        pdf_path: str,
        max_pages: int = 20,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수 (Phase 4.5)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            progress_callback: 진행 상황 콜백 함수
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Phase 4.5 처리 시작: {pdf_path}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"{'='*60}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 1: PDF → 고해상도 이미지 변환
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("📄 PDF 변환 중 (300 DPI)...", 0)
        
        logger.info("\n[Stage 1] PDF → 고해상도 이미지 변환")
        images = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages, dpi=300)
        logger.info(f"✅ {len(images)}개 페이지 변환 완료")
        
        if not images:
            logger.error("❌ PDF 변환 실패")
            return {
                'status': 'error',
                'error': 'PDF 변환 실패',
                'session_id': session_id
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 2: OCR + VLM 하이브리드 분석
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        results = []
        success_count = 0
        error_count = 0
        
        strategy_counts = {'simple': 0, 'complex_ocr': 0}
        validation_issues = []
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int((page_num / len(images)) * 90)
                progress_callback(
                    f"🎯 페이지 {page_num + 1}/{len(images)} OCR + VLM 분석 중...",
                    progress
                )
            
            logger.info(f"\n[Stage 2] 페이지 {page_num + 1} - OCR + VLM 하이브리드 분석")
            
            try:
                # OCR + VLM 호출
                vlm_result = self.vlm_service.analyze_page_intelligent(
                    image_data=img_data,
                    page_num=page_num + 1
                )
                
                content = vlm_result.get('content', '')
                confidence = vlm_result.get('confidence', 0.0)
                strategy = vlm_result.get('strategy', 'unknown')
                structure = vlm_result.get('structure', {})
                
                if not content:
                    logger.warning(f"   ⚠️ VLM 결과 없음")
                    error_count += 1
                    continue
                
                # 성공!
                success_count += 1
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                
                logger.info(f"   ✅ 성공 ({len(content)} 글자, 신뢰도: {confidence:.2f}, 전략: {strategy})")
                
                results.append({
                    'page_num': page_num + 1,
                    'content': content,
                    'confidence': confidence,
                    'strategy': strategy,
                    'structure': structure
                })
                
            except Exception as e:
                logger.error(f"   ❌ 처리 실패: {e}")
                error_count += 1
        
        logger.info(f"\n✅ VLM 분석 완료:")
        logger.info(f"   - 성공: {success_count}개")
        logger.info(f"   - 실패: {error_count}개")
        logger.info(f"   - 전략: Simple {strategy_counts.get('simple', 0)}개, Complex OCR {strategy_counts.get('complex_ocr', 0)}개")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 3: Markdown 통합
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("📝 Markdown 생성 중...", 95)
        
        logger.info(f"\n[Stage 3] Markdown 통합")
        
        full_markdown = self._generate_markdown(results)
        
        logger.info(f"✅ Markdown 생성 완료 ({len(full_markdown)} 글자)")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 4: 상세 품질 분석 (수정!)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        quality_metrics = self._analyze_quality(results, full_markdown)
        
        logger.info(f"\n[품질 분석]")
        logger.info(f"   - 평균 신뢰도: {quality_metrics['avg_confidence']:.2f}")
        logger.info(f"   - 품질 점수: {quality_metrics['quality_score']:.1f}/100")
        logger.info(f"   - 원본 충실도: {quality_metrics['fidelity_score']:.1f}/100")
        logger.info(f"   - 청킹 품질: {quality_metrics['chunking_score']:.1f}/100")
        logger.info(f"   - RAG 적합도: {quality_metrics['rag_score']:.1f}/100")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 5: 결과 저장
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("💾 저장 중...", 98)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result = {
            'status': 'success',
            'session_id': session_id,
            'processing_time': processing_time,
            'pages_processed': len(images),
            'pages_success': success_count,
            'pages_error': error_count,
            'strategy_simple': strategy_counts.get('simple', 0),
            'strategy_complex_ocr': strategy_counts.get('complex_ocr', 0),
            'validation_issues': len(validation_issues),
            'markdown': full_markdown,
            'page_results': results,
            **quality_metrics
        }
        
        # DB 저장
        try:
            if hasattr(self.storage, 'save_session'):
                self.storage.save_session(result)
                logger.info("✅ DB 저장 완료")
        except Exception as e:
            logger.error(f"⚠️ DB 저장 실패: {e}")
        
        if progress_callback:
            progress_callback("✅ 완료!", 100)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Phase 4.5 처리 완료")
        logger.info(f"   - 처리 시간: {processing_time:.1f}초")
        logger.info(f"   - 페이지 성공: {success_count}/{len(images)}")
        logger.info(f"   - 품질 점수: {quality_metrics['quality_score']:.1f}/100")
        logger.info(f"   - 총 글자 수: {len(full_markdown):,}")
        logger.info(f"{'='*60}\n")
        
        return result
    
    def _generate_markdown(self, results: List[Dict[str, Any]]) -> str:
        """페이지별 결과를 하나의 Markdown으로 통합"""
        markdown_parts = []
        
        for result in results:
            page_num = result['page_num']
            content = result['content']
            
            markdown_parts.append(content)
            markdown_parts.append("\n\n")
        
        return "".join(markdown_parts).strip()
    
    def _analyze_quality(self, results: List[Dict], markdown: str) -> Dict[str, float]:
        """상세 품질 분석 (Phase 4.5 - 수정!)"""
        
        if not results:
            return {
                'avg_confidence': 0.0,
                'quality_score': 0.0,
                'fidelity_score': 0.0,
                'chunking_score': 0.0,
                'rag_score': 0.0
            }
        
        # 1. 평균 신뢰도
        avg_confidence = sum(r.get('confidence', 0.0) for r in results) / len(results)
        
        # 2. 원본 충실도 (Fidelity)
        fidelity_score = self._calculate_fidelity(markdown)
        
        # 3. 청킹 품질
        chunking_score = self._calculate_chunking_quality(markdown)
        
        # 4. RAG 적합도
        rag_score = self._calculate_rag_suitability(markdown)
        
        # 5. 종합 품질 점수 (🔧 버그 수정!)
        quality_score = (
            avg_confidence * 100 * 0.30 +  # 신뢰도 30%
            fidelity_score * 0.30 +         # 원본 충실도 30%
            chunking_score * 0.20 +         # 청킹 품질 20%
            rag_score * 0.20                # RAG 적합도 20%
        )
        
        return {
            'avg_confidence': avg_confidence,
            'quality_score': min(quality_score, 100.0),
            'fidelity_score': fidelity_score,
            'chunking_score': chunking_score,
            'rag_score': rag_score
        }
    
    def _calculate_fidelity(self, markdown: str) -> float:
        """원본 충실도 계산 (Phase 4.5)"""
        score = 100.0
        
        # 1. 반복 패턴 감지 (환각) - 더 엄격!
        lines = markdown.split('\n')
        line_counts = {}
        for line in lines:
            clean = line.strip()
            if len(clean) > 5 and (clean.startswith('- ') or (len(clean) > 0 and clean[0].isdigit())):
                line_counts[clean] = line_counts.get(clean, 0) + 1
        
        max_repeat = max(line_counts.values()) if line_counts else 1
        if max_repeat >= 20:
            score -= 90  # 치명적!
        elif max_repeat >= 10:
            score -= 60  # 심각
        elif max_repeat >= 5:
            score -= 30  # 문제
        elif max_repeat >= 3:
            score -= 10  # 경미
        
        # 2. "읽기 불가" 개수
        unreadable = markdown.count('읽기 불가') + markdown.count('[불명확]')
        score -= min(20, unreadable * 2)
        
        # 3. 불필요한 메타 정보 (Phase 4.5 신규)
        if '✅ 체크리스트' in markdown:
            score -= 5
        if '⚠️ **품질 이슈:**' in markdown:
            score -= 5
        
        return max(0.0, score)
    
    def _calculate_chunking_quality(self, markdown: str) -> float:
        """청킹 품질 계산"""
        score = 0.0
        
        # 1. 섹션 구분 (`---`)
        sections = markdown.split('---')
        section_count = len(sections)
        
        if section_count >= 3:
            score += 40
        elif section_count >= 2:
            score += 30
        elif section_count >= 1:
            score += 20
        
        # 2. 섹션 헤더 (`####`)
        headers = re.findall(r'^####\s+(.+)$', markdown, re.MULTILINE)
        header_count = len(headers)
        
        if header_count >= 5:
            score += 30
        elif header_count >= 3:
            score += 20
        elif header_count >= 1:
            score += 10
        
        # 3. 균형잡힌 섹션 크기
        if section_count > 1:
            section_lengths = [len(s) for s in sections]
            avg_len = sum(section_lengths) / len(section_lengths)
            
            variance = sum((l - avg_len) ** 2 for l in section_lengths) / len(section_lengths)
            if variance < (avg_len ** 2) * 0.5:
                score += 30
            elif variance < (avg_len ** 2) * 1.0:
                score += 20
        
        return min(100.0, score)
    
    def _calculate_rag_suitability(self, markdown: str) -> float:
        """RAG 적합도 계산"""
        score = 100.0
        
        # 1. 불필요한 중복 (감점)
        lines = markdown.split('\n')
        line_counts = {}
        for line in lines:
            clean = line.strip()
            if len(clean) > 5:
                line_counts[clean] = line_counts.get(clean, 0) + 1
        
        max_repeat = max(line_counts.values()) if line_counts else 1
        if max_repeat >= 50:
            score -= 80
        elif max_repeat >= 20:
            score -= 50
        elif max_repeat >= 10:
            score -= 30
        
        # 2. 불필요한 메타 정보 (Phase 4.5 신규)
        if '✅ 체크리스트' in markdown:
            score -= 10
        if '⚠️ **품질 이슈:**' in markdown:
            score -= 10
        if '━━━━━' in markdown:  # 장식선
            score -= 5
        
        # 3. 자연어 설명 비율 (가산점)
        total_lines = len([l for l in lines if l.strip()])
        data_lines = len([l for l in lines if l.strip().startswith('- ')])
        
        if total_lines > 0:
            description_ratio = 1.0 - (data_lines / total_lines)
            if description_ratio >= 0.3:
                score += 20
            elif description_ratio >= 0.2:
                score += 10
        
        return max(0.0, min(100.0, score))
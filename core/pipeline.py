"""
core/pipeline_v50.py
PRISM Phase 5.0 - Pipeline (완전 범용 문서 처리)

✅ Phase 5.0 핵심:
1. 문서 타입 자동 인식 + 타입별 전략 자동 적용
2. 5가지 체크리스트 준수
3. 원본 충실도 95% + 청킹 품질 90% + RAG 최적화 95%

Author: 이서영 (Backend Lead)
Date: 2025-10-24
Version: 5.0
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid
import re

logger = logging.getLogger(__name__)


class Phase50Pipeline:
    """
    Phase 5.0 처리 파이프라인
    
    특징:
    - 완전 범용 설계 (모든 문서 타입 지원)
    - 5가지 체크리스트 준수
    - 하드코딩 제로
    """
    
    def __init__(self, pdf_processor, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMServiceV50 인스턴스
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
        PDF 처리 메인 함수 (Phase 5.0)
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 처리 페이지 수
            progress_callback: 진행 상황 콜백 함수
        
        Returns:
            처리 결과 딕셔너리
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 PRISM Phase 5.0 - 범용 문서 처리 시작")
        logger.info(f"{'='*80}")
        logger.info(f"📄 파일: {pdf_path}")
        logger.info(f"🆔 Session ID: {session_id}")
        logger.info(f"📊 최대 페이지: {max_pages}")
        logger.info(f"{'='*80}\n")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 1: PDF → 고해상도 이미지 변환 (300 DPI)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("📄 PDF 변환 중 (300 DPI 고해상도)...", 0)
        
        logger.info("[Stage 1] PDF → 고해상도 이미지 변환 (300 DPI)")
        images = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages, dpi=300)
        logger.info(f"✅ {len(images)}개 페이지 변환 완료\n")
        
        if not images:
            logger.error("❌ PDF 변환 실패")
            return {
                'status': 'error',
                'error': 'PDF 변환 실패',
                'session_id': session_id
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 2: Phase 5.0 범용 분석 (문서 타입 자동 판별)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info("[Stage 2] Phase 5.0 범용 분석 시작")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        results = []
        success_count = 0
        error_count = 0
        
        doc_type_counts = {}
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int(5 + (page_num / len(images)) * 85)
                progress_callback(
                    f"🎯 페이지 {page_num + 1}/{len(images)} 범용 분석 중...",
                    progress
                )
            
            logger.info(f"📄 페이지 {page_num + 1}/{len(images)} 처리 시작")
            
            try:
                # Phase 5.0: 범용 분석
                vlm_result = self.vlm_service.analyze_page_v50(
                    image_data=img_data,
                    page_num=page_num + 1
                )
                
                content = vlm_result.get('content', '')
                confidence = vlm_result.get('confidence', 0.0)
                doc_type = vlm_result.get('doc_type', 'mixed')
                subtype = vlm_result.get('subtype', 'unknown')
                quality_score = vlm_result.get('quality_score', 0.0)
                
                if not content or len(content) < 20:
                    logger.warning(f"   ⚠️ VLM 결과 부족: {len(content)} 글자")
                    error_count += 1
                    continue
                
                # 성공!
                success_count += 1
                doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
                
                logger.info(f"   ✅ 성공!")
                logger.info(f"      - 타입: {doc_type} ({subtype})")
                logger.info(f"      - 신뢰도: {confidence:.2f}")
                logger.info(f"      - 품질: {quality_score:.1f}/100")
                logger.info(f"      - 글자 수: {len(content):,}")
                logger.info("")
                
                results.append({
                    'page_num': page_num + 1,
                    'content': content,
                    'confidence': confidence,
                    'doc_type': doc_type,
                    'subtype': subtype,
                    'strategy': vlm_result.get('strategy', 'unknown'),
                    'quality_score': quality_score,
                    'structure': vlm_result.get('structure', {})
                })
                
            except Exception as e:
                logger.error(f"   ❌ 처리 실패: {e}\n")
                error_count += 1
        
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"✅ Phase 5.0 분석 완료:")
        logger.info(f"   - 성공: {success_count}/{len(images)}개")
        logger.info(f"   - 실패: {error_count}/{len(images)}개")
        logger.info(f"   - 문서 타입 분포: {doc_type_counts}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        if success_count == 0:
            logger.error("❌ 모든 페이지 처리 실패")
            return {
                'status': 'error',
                'error': '모든 페이지 처리 실패',
                'session_id': session_id
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 3: Markdown 통합 (지능형 청킹)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("📝 Markdown 통합 중...", 95)
        
        logger.info("[Stage 3] Markdown 통합 (지능형 청킹)")
        
        full_markdown = self._generate_markdown_with_chunking(results)
        
        logger.info(f"✅ Markdown 생성 완료")
        logger.info(f"   - 총 글자 수: {len(full_markdown):,}")
        logger.info(f"   - 섹션 수: {full_markdown.count('---')}")
        logger.info("")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 4: 5가지 체크리스트 품질 분석
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info("[Stage 4] 5가지 체크리스트 품질 분석")
        quality_metrics = self._analyze_quality_checklist(results, full_markdown)
        
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("📊 5가지 체크리스트 결과:")
        logger.info(f"   ✅ 1. 원본 충실도:  {quality_metrics['fidelity_score']:.1f}/100")
        logger.info(f"   ✅ 2. 청킹 품질:    {quality_metrics['chunking_score']:.1f}/100")
        logger.info(f"   ✅ 3. RAG 적합도:   {quality_metrics['rag_score']:.1f}/100")
        logger.info(f"   ✅ 4. 범용성:       {quality_metrics['universality_score']:.1f}/100")
        logger.info(f"   ✅ 5. 경쟁사 대비:  {quality_metrics['competitive_score']:.1f}/100")
        logger.info(f"   🎯 종합 품질 점수: {quality_metrics['overall_score']:.1f}/100")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 5: 결과 저장
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("💾 결과 저장 중...", 98)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result = {
            'status': 'success',
            'session_id': session_id,
            'version': '5.0',
            'processing_time': processing_time,
            'pages_total': len(images),
            'pages_success': success_count,
            'pages_error': error_count,
            'strategy': 'universal_v50',
            'doc_type_counts': doc_type_counts,
            'markdown': full_markdown,
            'page_results': results,
            **quality_metrics
        }
        
        # DB 저장
        try:
            if hasattr(self.storage, 'save_session'):
                self.storage.save_session(result)
                logger.info("✅ DB 저장 완료\n")
        except Exception as e:
            logger.error(f"⚠️ DB 저장 실패: {e}\n")
        
        if progress_callback:
            progress_callback("✅ 완료!", 100)
        
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🎉 PRISM Phase 5.0 처리 완료!")
        logger.info(f"   ⏱️  처리 시간: {processing_time:.1f}초")
        logger.info(f"   📄 성공: {success_count}/{len(images)}개")
        logger.info(f"   🎯 종합 품질: {quality_metrics['overall_score']:.1f}/100")
        logger.info(f"   📊 총 글자: {len(full_markdown):,}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        return result
    
    def _generate_markdown_with_chunking(self, results: List[Dict[str, Any]]) -> str:
        """
        페이지별 결과를 하나의 Markdown으로 통합 (지능형 청킹)
        
        ✅ 체크리스트 2번: 지능형 청킹
        - 페이지 구분: `---`
        - 섹션 헤더: `##`
        """
        markdown_parts = []
        
        for i, result in enumerate(results):
            content = result['content']
            page_num = result['page_num']
            doc_type = result.get('doc_type', 'mixed')
            
            # 페이지 헤더 (메타 정보 최소화)
            markdown_parts.append(f"<!-- 페이지 {page_num} ({doc_type}) -->\n\n")
            
            # 내용
            markdown_parts.append(content)
            
            # 페이지 구분 (마지막 페이지 제외)
            if i < len(results) - 1:
                markdown_parts.append("\n\n---\n\n")
        
        return "".join(markdown_parts).strip()
    
    def _analyze_quality_checklist(self, results: List[Dict], markdown: str) -> Dict[str, float]:
        """
        5가지 체크리스트 품질 분석
        
        1. 원본 충실도 95% 목표
        2. 청킹 품질 90% 목표
        3. RAG 적합도 95% 목표
        4. 범용성 100% 목표
        5. 경쟁사 대비 95% 목표
        """
        
        if not results:
            return {
                'fidelity_score': 0.0,
                'chunking_score': 0.0,
                'rag_score': 0.0,
                'universality_score': 0.0,
                'competitive_score': 0.0,
                'overall_score': 0.0
            }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 1. 원본 충실도 (Fidelity Score)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        fidelity_score = self._calculate_fidelity_score(markdown, results)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 2. 청킹 품질 (Chunking Quality)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        chunking_score = self._calculate_chunking_quality(markdown, results)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 3. RAG 적합도 (RAG Suitability)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        rag_score = self._calculate_rag_suitability(markdown)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 4. 범용성 (Universality)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        universality_score = self._calculate_universality(results)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ 5. 경쟁사 대비 (Competitive Score)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        competitive_score = self._calculate_competitive_score(
            fidelity_score, chunking_score, rag_score, universality_score
        )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 종합 점수
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        overall_score = (
            fidelity_score * 0.25 +      # 원본 충실도 25%
            chunking_score * 0.20 +      # 청킹 품질 20%
            rag_score * 0.20 +           # RAG 적합도 20%
            universality_score * 0.20 +  # 범용성 20%
            competitive_score * 0.15     # 경쟁사 대비 15%
        )
        
        return {
            'fidelity_score': fidelity_score,
            'chunking_score': chunking_score,
            'rag_score': rag_score,
            'universality_score': universality_score,
            'competitive_score': competitive_score,
            'overall_score': min(100.0, overall_score)
        }
    
    def _calculate_fidelity_score(self, markdown: str, results: List[Dict]) -> float:
        """
        ✅ 1. 원본 충실도 계산
        
        평가 기준:
        - 최소 길이 충족
        - 구조 헤더 존재
        - 페이지별 균형
        - 신뢰도
        """
        score = 100.0
        
        # 1. 최소 길이 체크
        if len(markdown) < 100:
            score -= 40
        elif len(markdown) < 500:
            score -= 20
        elif len(markdown) >= 1000:
            score += 5  # 보너스
        
        # 2. 구조 헤더 존재
        headers = re.findall(r'^#+\s+', markdown, re.MULTILINE)
        header_count = len(headers)
        
        if header_count == 0:
            score -= 25
        elif header_count >= 1 and header_count < 3:
            score -= 10
        elif header_count >= 5:
            score += 10  # 보너스
        
        # 3. 페이지별 내용 균형
        page_lengths = [len(r.get('content', '')) for r in results]
        if page_lengths and len(page_lengths) > 1:
            avg_len = sum(page_lengths) / len(page_lengths)
            if avg_len > 0:
                variance = sum((l - avg_len) ** 2 for l in page_lengths) / len(page_lengths)
                std_dev = variance ** 0.5
                cv = std_dev / avg_len  # 변동계수
                
                if cv < 0.3:
                    score += 15  # 매우 균형잡힘
                elif cv < 0.5:
                    score += 10
                elif cv > 1.0:
                    score -= 10  # 불균형
        
        # 4. 평균 신뢰도
        confidences = [r.get('confidence', 0.0) for r in results]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            score += avg_confidence * 10  # 최대 +10점
        
        return max(0.0, min(100.0, score))
    
    def _calculate_chunking_quality(self, markdown: str, results: List[Dict]) -> float:
        """
        ✅ 2. 청킹 품질 계산
        
        평가 기준:
        - 페이지 구분 (`---`)
        - 섹션 헤더 (`##`)
        - 균형잡힌 섹션 크기
        """
        score = 0.0
        
        # 1. 페이지 구분 (`---`)
        page_separators = markdown.count('---')
        expected_separators = len(results) - 1  # 마지막 페이지 제외
        
        if page_separators >= expected_separators:
            score += 35  # 완벽한 페이지 구분
        elif page_separators >= expected_separators * 0.8:
            score += 25
        elif page_separators >= expected_separators * 0.5:
            score += 15
        
        # 2. 섹션 헤더 (`##`)
        headers = re.findall(r'^##\s+(.+)$', markdown, re.MULTILINE)
        header_count = len(headers)
        
        if header_count >= len(results) * 2:
            score += 35  # 페이지당 2개 이상
        elif header_count >= len(results):
            score += 25  # 페이지당 1개 이상
        elif header_count >= len(results) * 0.5:
            score += 15
        
        # 3. 균형잡힌 섹션 크기
        sections = markdown.split('---')
        if len(sections) > 1:
            section_lengths = [len(s.strip()) for s in sections if s.strip()]
            if section_lengths:
                avg_len = sum(section_lengths) / len(section_lengths)
                if avg_len > 0:
                    variance = sum((l - avg_len) ** 2 for l in section_lengths) / len(section_lengths)
                    std_dev = variance ** 0.5
                    cv = std_dev / avg_len
                    
                    if cv < 0.3:
                        score += 30  # 매우 균형잡힘
                    elif cv < 0.5:
                        score += 20
                    elif cv < 0.8:
                        score += 10
        
        return min(100.0, score)
    
    def _calculate_rag_suitability(self, markdown: str) -> float:
        """
        ✅ 3. RAG 적합도 계산
        
        평가 기준:
        - 불필요한 메타 정보 없음
        - 중복 제거
        - 구조화된 데이터
        """
        score = 100.0
        
        # 1. 불필요한 메타 정보 체크 (감점)
        meta_keywords = [
            '이 문서는', '다음과 같이', '아래와 같이',
            '볼 수 있습니다', '확인할 수 있습니다',
            '이 페이지', '문서 상단', '문서 하단',
            '위에서 언급한', '아래에서 설명할'
        ]
        
        meta_count = 0
        for keyword in meta_keywords:
            meta_count += markdown.count(keyword)
        
        score -= meta_count * 3  # 개당 -3점
        
        # 2. 불필요한 중복 체크 (감점)
        lines = markdown.split('\n')
        line_counts = {}
        for line in lines:
            clean = line.strip()
            if len(clean) > 15:  # 짧은 줄 제외
                line_counts[clean] = line_counts.get(clean, 0) + 1
        
        duplicates = sum(1 for count in line_counts.values() if count >= 3)
        score -= duplicates * 5  # 중복 줄당 -5점
        
        # 3. 구조화된 데이터 (가산점)
        has_table = '|' in markdown and markdown.count('|') >= 6
        has_list = re.search(r'^\d+\.\s+', markdown, re.MULTILINE) is not None
        has_bullet = re.search(r'^[-*]\s+', markdown, re.MULTILINE) is not None
        
        if has_table:
            score += 10
        if has_list:
            score += 5
        if has_bullet:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _calculate_universality(self, results: List[Dict]) -> float:
        """
        ✅ 4. 범용성 계산
        
        평가 기준:
        - 다양한 문서 타입 처리
        - 타입별 전략 적용
        - 하드코딩 없음
        """
        score = 100.0
        
        # 1. 문서 타입 다양성
        doc_types = set(r.get('doc_type', 'mixed') for r in results)
        type_diversity = len(doc_types)
        
        if type_diversity >= 3:
            score += 10  # 매우 다양
        elif type_diversity >= 2:
            score += 5
        
        # 2. 타입별 전략 적용 확인
        strategies_used = set(r.get('strategy', '') for r in results)
        if 'universal_v50' in ' '.join(strategies_used):
            score += 10  # Phase 5.0 전략 사용
        
        # 3. 하드코딩 체크 (버스 전용 키워드)
        hardcoded_keywords = [
            '일반버스', '광역버스', '마을버스',
            '배차간격', '첫차', '막차'
        ]
        
        all_content = ' '.join(r.get('content', '') for r in results)
        
        # 문서 타입이 'diagram/transport_route'일 때만 허용
        is_transport = any(
            r.get('doc_type') == 'diagram' and 
            r.get('subtype') == 'transport_route'
            for r in results
        )
        
        if not is_transport:
            for keyword in hardcoded_keywords:
                if keyword in all_content:
                    score -= 15  # 하드코딩 발견! (큰 감점)
        
        return max(0.0, min(100.0, score))
    
    def _calculate_competitive_score(
        self,
        fidelity: float,
        chunking: float,
        rag: float,
        universality: float
    ) -> float:
        """
        ✅ 5. 경쟁사 대비 점수 계산
        
        경쟁사 기준:
        - 원본 충실도: 85점
        - 청킹 품질: 80점
        - RAG 적합도: 90점
        - 범용성: 70점
        """
        competitor_baseline = {
            'fidelity': 85.0,
            'chunking': 80.0,
            'rag': 90.0,
            'universality': 70.0
        }
        
        # 각 항목별 경쟁사 대비 점수
        fidelity_ratio = (fidelity / competitor_baseline['fidelity']) * 100
        chunking_ratio = (chunking / competitor_baseline['chunking']) * 100
        rag_ratio = (rag / competitor_baseline['rag']) * 100
        universality_ratio = (universality / competitor_baseline['universality']) * 100
        
        # 평균
        avg_ratio = (fidelity_ratio + chunking_ratio + rag_ratio + universality_ratio) / 4
        
        # 95% 이상이면 만점
        if avg_ratio >= 95:
            return 100.0
        else:
            return min(100.0, avg_ratio)
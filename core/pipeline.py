"""
core/pipeline.py
PRISM Phase 0.2 Hotfix - Pipeline with DocType Hardening

✅ Phase 0.2 긴급 수정:
1. DocType 전역 고정 (statute)
2. 페이지별 page_role과 분리
3. 후처리에 일관된 doc_type 전달
4. 코드펜스 제거 유지

Author: 이서영 (Backend Lead) + GPT 피드백
Date: 2025-11-06
Version: Phase 0.2 Hotfix
"""

import logging
import time
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class Phase53Pipeline:
    """
    Phase 0.2 통합 파이프라인 (DocType 일관성)
    
    ✅ Phase 0.2 개선:
    - DocType 전역 고정 (statute)
    - 페이지 역할(page_role)과 분리
    - 후처리 일관성 보장
    - 코드펜스 제거 유지
    - app.py 호환성 유지 (Phase53Pipeline)
    
    플로우:
    1. PDF → 이미지 변환
    2. HybridExtractor: 페이지별 추출 (page_role 전달)
    3. ✅ Markdown 통합 + 코드펜스 제거
    4. ✅ 후처리: doc_type=statute 고정 전달
    5. SemanticChunker: 조문 경계 기반 청킹
    6. 체크리스트 평가
    """
    
    def __init__(
        self,
        pdf_processor,
        vlm_service,
        max_pages: int = 20,
        session_id: str = None
    ):
        """
        초기화 (app.py 호환)
        
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMServiceV50 인스턴스 (classifier 포함)
            max_pages: 최대 페이지 수
            session_id: 세션 ID (선택)
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        self.max_pages = max_pages
        self.session_id = session_id or self._generate_session_id()
        
        # classifier는 vlm_service에서 가져옴
        self.classifier = getattr(vlm_service, 'classifier', None)
        
        if not self.classifier:
            logger.warning("⚠️ VLM Service에 classifier 없음 - 기본 분류기 사용")
            try:
                from core.document_classifier import DocumentClassifierV50
                self.classifier = DocumentClassifierV50()
            except:
                logger.error("❌ DocumentClassifierV50 로드 실패")
                self.classifier = None
        
        # Components
        from core.semantic_chunker import SemanticChunker
        self.chunker = SemanticChunker(
            min_chunk_size=600,
            max_chunk_size=1200,
            target_chunk_size=900
        )
        
        logger.info("✅ Phase 0.2 Pipeline 초기화 완료 (DocType 일관성)")
        logger.info("   - HybridExtractor: page_role 전달")
        logger.info("   - PostMerge/Typo: doc_type=statute 고정")
        logger.info("   - SemanticChunker: Fail-safe 지원")
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        ✅ app.py 호환성 메서드
        
        기존 API:
            pipeline = Phase53Pipeline(pdf_processor, vlm_service)
            result = pipeline.process_pdf(pdf_path)
        
        Args:
            pdf_path: PDF 파일 경로
        
        Returns:
            처리 결과
        """
        return self.process(pdf_path)
    
    def process(self, pdf_path: str) -> Dict[str, Any]:
        """
        Phase 0.2 전체 처리 (DocType 일관성)
        
        Args:
            pdf_path: PDF 파일 경로
        
        Returns:
            처리 결과
        """
        logger.info(f"🎯 Phase 0.2 처리 시작 (DocType 일관성)")
        logger.info(f"   파일: {pdf_path}")
        logger.info(f"   세션: {self.session_id}")
        logger.info(f"   최대 페이지: {self.max_pages}")
        
        start_time = time.time()
        
        # Step 1: PDF → 이미지
        logger.info("📄 Step 1: PDF → 이미지 변환")
        images = self.pdf_processor.pdf_to_images(
            pdf_path=pdf_path,
            max_pages=self.max_pages
        )
        logger.info(f"   ✅ {len(images)}페이지 변환 완료")
        
        # Step 2: 문서 분류 (전역 doc_type 결정)
        logger.info("📊 Step 2: 문서 분류")
        first_image = images[0][0] if images else None
        
        if first_image:
            doc_classification = self.classifier.classify(first_image)
            global_doc_type = doc_classification.get('domain', 'statute')
        else:
            global_doc_type = 'statute'
        
        logger.info(f"   ✅ 전역 doc_type: {global_doc_type}")
        
        # Step 3: HybridExtractor 초기화 (전역 allow_tables)
        from core.hybrid_extractor import HybridExtractor
        
        allow_tables = (global_doc_type == 'statute')
        
        extractor = HybridExtractor(
            vlm_service=self.vlm_service,
            pdf_path=pdf_path,
            allow_tables=allow_tables
        )
        
        # Step 4: 페이지별 추출
        logger.info("📝 Step 3: 페이지별 추출 (page_role 전달)")
        
        page_results = []
        empty_page_count = 0
        
        for i, (image_data, page_num) in enumerate(images, 1):
            result = extractor.extract(image_data, page_num)
            
            # 빈 페이지 필터링
            if result['quality_score'] >= 50:
                page_results.append(result)
            else:
                empty_page_count += 1
                logger.debug(f"      빈 페이지 제외: {page_num}")
        
        logger.info(f"📊 유효 페이지: {len(page_results)}/{len(images)} (빈 페이지 {empty_page_count}개 제외)")
        
        # Fallback 통계
        fallback_count = sum(1 for r in page_results if r['source'] == 'fallback')
        fallback_rate = (fallback_count / len(page_results) * 100) if page_results else 0
        
        logger.info("📊 Fallback 통계:")
        logger.info(f"   - VLM 성공: {len(page_results) - fallback_count}페이지")
        logger.info(f"   - Fallback 사용: {fallback_count}페이지")
        logger.info(f"   - Fallback 비율: {fallback_rate:.1f}%")
        
        # Step 5: Markdown 통합 + 코드펜스 제거
        logger.info("📝 Step 4: Markdown 통합 + 코드펜스 제거")
        
        markdown_parts = []
        for result in page_results:
            content = result['content']
            
            # 코드펜스 제거
            content = self._strip_code_fences(content)
            
            markdown_parts.append(content)
        
        full_markdown = '\n\n'.join(markdown_parts)
        
        logger.info(f"   ✅ Markdown 통합 완료: {len(full_markdown)} 글자")
        
        # ✅ Phase 0.2: 후처리에 global_doc_type 전달
        logger.info(f"🔧 Step 5: 후처리 (doc_type={global_doc_type})")
        
        from core.post_merge_normalizer import PostMergeNormalizer
        from core.typo_normalizer import TypoNormalizer
        
        post_normalizer = PostMergeNormalizer()
        typo_normalizer = TypoNormalizer()
        
        # 후처리 적용
        full_markdown = post_normalizer.normalize(full_markdown, global_doc_type)
        full_markdown = typo_normalizer.normalize(full_markdown, global_doc_type)
        
        # Step 6: SemanticChunking
        logger.info("✂️ Step 6: SemanticChunking Phase 0.2 (Fail-safe)")
        
        chunks = self.chunker.chunk(full_markdown)
        
        logger.info(f"   ✅ {len(chunks)}개 청크 생성")
        
        # Step 7: 체크리스트 평가
        logger.info("📊 Step 7: 체크리스트 평가")
        
        checklist_score = self._evaluate_checklist(
            markdown=full_markdown,
            chunks=chunks,
            page_results=page_results,
            doc_type=global_doc_type
        )
        
        logger.info(f"   ✅ 원본 충실도: {checklist_score['fidelity']}/100")
        logger.info(f"   ✅ 청킹 품질: {checklist_score['chunking']}/100")
        logger.info(f"   ✅ RAG 적합도: {checklist_score['rag']}/100")
        logger.info(f"   ✅ 범용성: {checklist_score['generality']}/100")
        logger.info(f"   ✅ 경쟁력: {checklist_score['competitiveness']}/100")
        logger.info(f"   🎯 종합: {checklist_score['overall']}/100")
        
        # 종료
        elapsed_time = time.time() - start_time
        
        logger.info("✅ Phase 0.2 처리 완료")
        logger.info(f"   - 유효 페이지: {len(page_results)}/{len(images)}")
        logger.info(f"   - 빈 페이지: {empty_page_count}")
        logger.info(f"   - Fallback 사용: {fallback_count}")
        logger.info(f"   - 시간: {elapsed_time:.1f}초")
        logger.info(f"   - 종합: {checklist_score['overall']}/100")
        
        return {
            'session_id': self.session_id,
            'markdown': full_markdown,
            'chunks': chunks,
            'metadata': {
                'total_pages': len(images),
                'valid_pages': len(page_results),
                'empty_pages': empty_page_count,
                'fallback_count': fallback_count,
                'fallback_rate': fallback_rate,
                'doc_type': global_doc_type,
                'elapsed_time': elapsed_time
            },
            'checklist': checklist_score
        }
    
    def _strip_code_fences(self, content: str) -> str:
        """
        코드펜스 제거
        
        Args:
            content: 원본 Markdown
        
        Returns:
            코드펜스 제거된 Markdown
        """
        # 앞쪽 코드펜스 제거
        content = re.sub(r'^```[a-z]*\s*\n', '', content, flags=re.MULTILINE)
        
        # 뒤쪽 코드펜스 제거
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        
        # 앞뒤 공백 정리
        content = content.strip()
        
        return content
    
    def _evaluate_checklist(
        self,
        markdown: str,
        chunks: List[Dict[str, Any]],
        page_results: List[Dict[str, Any]],
        doc_type: str
    ) -> Dict[str, int]:
        """
        5대 체크리스트 평가
        
        Args:
            markdown: 통합 Markdown
            chunks: 청크 리스트
            page_results: 페이지별 추출 결과
            doc_type: 문서 타입
        
        Returns:
            체크리스트 점수
        """
        # 1) 원본 충실도 (Fidelity)
        fidelity_score = self._evaluate_fidelity(markdown, doc_type)
        
        # 2) 청킹 품질 (Chunking Quality)
        chunking_score = self._evaluate_chunking(chunks, markdown)
        
        # 3) RAG 적합도 (RAG Suitability)
        rag_score = self._evaluate_rag(chunks, markdown)
        
        # 4) 범용성 (Generality)
        generality_score = self._evaluate_generality(page_results)
        
        # 5) 경쟁력 (Competitiveness)
        competitiveness_score = self._evaluate_competitiveness(markdown, chunks)
        
        # 종합 점수
        overall_score = int(
            fidelity_score * 0.3 +
            chunking_score * 0.2 +
            rag_score * 0.2 +
            generality_score * 0.15 +
            competitiveness_score * 0.15
        )
        
        return {
            'fidelity': fidelity_score,
            'chunking': chunking_score,
            'rag': rag_score,
            'generality': generality_score,
            'competitiveness': competitiveness_score,
            'overall': overall_score
        }
    
    def _evaluate_fidelity(self, markdown: str, doc_type: str) -> int:
        """원본 충실도 평가"""
        score = 100
        
        # 개정이력 존재 여부
        if doc_type == 'statute':
            if '| 차수 | 날짜 |' in markdown:
                revision_count = markdown.count('차 개정')
                
                if revision_count >= 15:
                    score += 0  # 만점 유지
                elif revision_count >= 10:
                    score -= 5
                else:
                    score -= 10
            else:
                score -= 20  # 개정이력 누락
            
            # "기본 정신" 존재 여부
            if '기본 정신' in markdown or '기본정신' in markdown:
                score += 0  # 만점 유지
            else:
                score -= 15  # 기본 정신 누락
            
            # 조문 커버리지
            article_count = len(re.findall(r'제\s?\d+조', markdown))
            
            if article_count >= 3:
                score += 0
            elif article_count >= 1:
                score -= 10
            else:
                score -= 30
        
        return max(0, min(100, score))
    
    def _evaluate_chunking(self, chunks: List[Dict[str, Any]], markdown: str) -> int:
        """청킹 품질 평가"""
        if not chunks:
            return 0
        
        score = 100
        
        # 청크 개수
        chunk_count = len(chunks)
        
        if chunk_count >= 3:
            score += 0  # 이상적
        elif chunk_count >= 2:
            score -= 10
        elif chunk_count == 1:
            score -= 40  # 과소분할
        
        # 청크 크기 분포
        chunk_sizes = [c['metadata']['char_count'] for c in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        
        if 600 <= avg_size <= 1200:
            score += 0
        else:
            score -= 10
        
        # 조문 메타데이터
        articles_with_meta = sum(
            1 for c in chunks 
            if c['metadata'].get('article_no', '')
        )
        
        if articles_with_meta >= chunk_count * 0.8:
            score += 0
        else:
            score -= 15
        
        return max(0, min(100, score))
    
    def _evaluate_rag(self, chunks: List[Dict[str, Any]], markdown: str) -> int:
        """RAG 적합도 평가"""
        score = 100
        
        # 노이즈 체크
        noise_patterns = [
            r'\d{3,4}-\d{1,2}',  # 페이지 번호
            r'Page\s+\d+',
            r'[-—–_*]{3,}',
        ]
        
        for pattern in noise_patterns:
            matches = re.findall(pattern, markdown)
            if matches:
                score -= len(matches) * 2
        
        # 중복 체크
        if markdown.count('| 차수 | 날짜 |') > 1:
            score -= 20  # 중복 표
        
        # 청크 독립성
        if len(chunks) >= 3:
            score += 0  # 검색 가능성 높음
        elif len(chunks) == 1:
            score -= 30  # 검색 가능성 낮음
        
        return max(0, min(100, score))
    
    def _evaluate_generality(self, page_results: List[Dict[str, Any]]) -> int:
        """범용성 평가"""
        score = 100
        
        # Fallback 비율
        fallback_count = sum(1 for r in page_results if r['source'] == 'fallback')
        fallback_rate = (fallback_count / len(page_results)) if page_results else 0
        
        if fallback_rate <= 0.1:
            score += 0  # 우수
        elif fallback_rate <= 0.3:
            score -= 5
        else:
            score -= 15
        
        return max(0, min(100, score))
    
    def _evaluate_competitiveness(self, markdown: str, chunks: List[Dict[str, Any]]) -> int:
        """경쟁력 평가"""
        score = 100
        
        # 개정이력 표 형식
        if '| 차수 | 날짜 |' in markdown:
            score += 0  # 표 형식 우수
        else:
            score -= 20
        
        # 조문 헤더 정규화
        irregular_headers = len(re.findall(r'제\s+\d+\s+조', markdown))
        
        if irregular_headers == 0:
            score += 0
        else:
            score -= irregular_headers * 3
        
        # 청킹 품질
        if len(chunks) >= 3:
            score += 0
        else:
            score -= 10
        
        return max(0, min(100, score))
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
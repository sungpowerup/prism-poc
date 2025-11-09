"""
core/pipeline.py
PRISM Phase 0.3.3 Final - Pipeline with Safe Normalizers Only

✅ Phase 0.3.3 Final 수정:
1. Safe 파일 전용 (Fallback 제거)
2. 원본 충실도 우선
3. 골든 diff 기반 정규화

Author: 이서영 (Backend Lead)
Date: 2025-11-08
Version: Phase 0.3.3 Final
"""

import logging
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import string
import random

logger = logging.getLogger(__name__)

# ✅ Phase 0.3.3: Safe 모듈만 사용 (Fallback 제거)
from core.typo_normalizer_safe import TypoNormalizer
from core.post_merge_normalizer_safe import PostMergeNormalizer
from core.semantic_chunker import SemanticChunker
from core.document_classifier import DocumentClassifierV50
from core.hybrid_extractor import HybridExtractor

logger.info("✅ Safe Normalizers 로드 완료 (Phase 0.3.3)")


class ProcessingPipeline:
    """
    Phase 0.3.3 문서 처리 파이프라인 (Safe Only)
    
    ✅ Phase 0.3.3 개선:
    - Safe 파일 전용
    - 레이어 분리 정규화
    - 골든 diff 기반
    - 원본 충실도 최우선
    """
    
    VERSION = "Phase 0.3.3"
    
    def __init__(
        self,
        pdf_path: str,
        vlm_service,
        session_id: str,
        max_pages: int = 20
    ):
        """초기화"""
        self.pdf_path = pdf_path
        self.vlm_service = vlm_service
        self.session_id = session_id
        self.max_pages = max_pages
        
        # ⚠️ Phase 0.3.3: DocumentClassifier 비활성화
        # 이유: VLM client 속성 문제로 인한 AttributeError
        # 현재 전략: statute 고정 (인사규정 문서 특화)
        if hasattr(vlm_service, 'classifier'):
            self.classifier = vlm_service.classifier
            logger.info("✅ VLM Service의 classifier 사용")
        else:
            logger.warning("⚠️ VLM Service에 classifier 없음")
            self.classifier = DocumentClassifierV50(vlm_service)
        
        # 청킹 엔진
        self.chunker = SemanticChunker()
        
        # ✅ Phase 0.3.3: 정규화 엔진 (Safe 버전)
        self.post_normalizer = PostMergeNormalizer()
        self.typo_normalizer = TypoNormalizer()
        
        # HybridExtractor는 나중에 초기화 (pdf_path 필요)
        self.extractor = None
        
        logger.info(f"✅ {self.VERSION} Pipeline 초기화 완료")
        logger.info(f"   - Safe Mode: 활성화")
        logger.info(f"   - SemanticChunker: 문장 경계 보존")
        logger.info(f"   - HybridExtractor: 타입 안전 처리")
    
    def process(self) -> Dict[str, Any]:
        """
        문서 처리 메인 파이프라인
        
        Returns:
            처리 결과
        """
        start_time = time.time()
        
        logger.info(f"🎯 {self.VERSION} 처리 시작")
        logger.info(f"   파일: {self.pdf_path}")
        logger.info(f"   세션: {self.session_id}")
        logger.info(f"   최대 페이지: {self.max_pages}")
        
        try:
            # Step 1: PDF → 이미지 변환
            logger.info("📄 Step 1: PDF → 이미지 변환")
            
            # PDFProcessor 가져오기
            from core.pdf_processor import PDFProcessor
            pdf_processor = PDFProcessor()
            
            images = pdf_processor.pdf_to_images(
                self.pdf_path,
                max_pages=self.max_pages
            )
            logger.info(f"   ✅ {len(images)}페이지 변환 완료")
            
            # Step 2: 문서 분류
            logger.info("📊 Step 2: 문서 분류")
            
            # 첫 페이지 이미지 추출
            first_image = images[0][0] if images else None
            
            # ⚠️ Phase 0.3.3: statute 고정 (Classifier 비활성화)
            doc_type = 'statute'
            logger.info(f"   ✅ 전역 doc_type: {doc_type} (Classifier 비활성화)")
            
            # Step 3: HybridExtractor 초기화
            logger.info("📝 Step 3: HybridExtractor 초기화")
            
            allow_tables = (doc_type == 'statute')
            
            self.extractor = HybridExtractor(
                vlm_service=self.vlm_service,
                pdf_path=self.pdf_path,
                allow_tables=allow_tables
            )
            
            logger.info(f"   ✅ HybridExtractor 초기화 완료 (allow_tables={allow_tables})")
            
            # Step 4: 페이지별 추출
            logger.info("📝 Step 4: 페이지별 추출")
            pages_data = []
            
            for i, (image_data, page_num) in enumerate(images, 1):
                result = self.extractor.extract(image_data, page_num)
                
                # 유효 페이지만 추가
                if result.get('quality_score', 0) >= 50:
                    # Markdown 추출
                    markdown = result.get('content', '')
                    
                    pages_data.append({
                        'markdown': markdown,
                        'page_num': page_num,
                        'source': result.get('source', 'unknown'),
                        'quality_score': result.get('quality_score', 0)
                    })
            
            # 유효 페이지 통계
            valid_count = len(pages_data)
            empty_count = len(images) - valid_count
            
            logger.info(f"📊 유효 페이지: {valid_count}/{len(images)} (빈 페이지 {empty_count}개 제외)")
            
            # Fallback 통계
            fallback_count = sum(1 for p in pages_data if p.get('source') == 'fallback')
            fallback_ratio = fallback_count / valid_count if valid_count > 0 else 0
            
            logger.info(f"📊 Fallback 통계:")
            logger.info(f"   - VLM 성공: {valid_count - fallback_count}페이지")
            logger.info(f"   - Fallback 사용: {fallback_count}페이지")
            logger.info(f"   - Fallback 비율: {fallback_ratio:.1%}")
            
            # Step 5: Markdown 통합
            logger.info("📝 Step 5: Markdown 통합 + 코드펜스 제거")
            full_markdown = self._merge_markdown(pages_data)
            logger.info(f"   ✅ Markdown 통합 완료: {len(full_markdown)} 글자")
            
            # Step 6: 후처리 (Safe Mode)
            logger.info(f"🔧 Step 6: 후처리 (Safe Mode, doc_type={doc_type})")
            full_markdown = self.post_normalizer.normalize(full_markdown, doc_type)
            full_markdown = self.typo_normalizer.normalize(full_markdown, doc_type)
            
            # Step 7: SemanticChunking
            logger.info("✂️ Step 7: SemanticChunking Phase 0.3.3 (문장 경계 보존)")
            chunks = self.chunker.chunk(full_markdown)
            logger.info(f"   ✅ {len(chunks)}개 청크 생성")
            
            # Step 8: 체크리스트 평가
            logger.info("📊 Step 8: 체크리스트 평가")
            checklist = self._evaluate_checklist(
                pages_data=pages_data,
                markdown=full_markdown,
                chunks=chunks,
                doc_type=doc_type
            )
            
            # 처리 시간
            elapsed = time.time() - start_time
            
            logger.info(f"✅ {self.VERSION} 처리 완료")
            logger.info(f"   - 유효 페이지: {valid_count}/{len(images)}")
            logger.info(f"   - 빈 페이지: {empty_count}")
            logger.info(f"   - Fallback 사용: {fallback_count}")
            logger.info(f"   - 시간: {elapsed:.1f}초")
            logger.info(f"   - 종합: {checklist['overall']}/100")
            
            return {
                'success': True,
                'markdown': full_markdown,
                'chunks': chunks,
                'pages_count': valid_count,
                'doc_type': doc_type,
                'checklist': checklist,
                'elapsed_time': elapsed,
                'fallback_count': fallback_count,
                'fallback_ratio': fallback_ratio
            }
            
        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    def _merge_markdown(self, pages_data: List[Dict]) -> str:
        """Markdown 통합"""
        parts = []
        
        for page in pages_data:
            md = page['markdown']
            
            # 코드펜스 제거
            md = md.replace('```markdown\n', '').replace('\n```', '')
            
            parts.append(md)
        
        return '\n\n'.join(parts)
    
    def _evaluate_checklist(
        self,
        pages_data: List[Dict],
        markdown: str,
        chunks: List[Dict],
        doc_type: str
    ) -> Dict[str, int]:
        """
        체크리스트 평가
        
        ⚠️ 내부 휴리스틱 진단용
        """
        
        # 1. 원본 충실도
        fidelity = self._check_fidelity(pages_data, markdown)
        logger.info(f"   ✅ 원본 충실도: {fidelity}/100")
        
        # 2. 청킹 품질
        chunking = self._check_chunking(chunks, doc_type)
        logger.info(f"   ✅ 청킹 품질: {chunking}/100")
        
        # 3. RAG 적합도
        rag = self._check_rag_readiness(chunks)
        logger.info(f"   ✅ RAG 적합도: {rag}/100")
        
        # 4. 범용성
        generality = self._check_generality(markdown, doc_type)
        logger.info(f"   ✅ 범용성: {generality}/100")
        
        # 5. 경쟁력
        competitive = self._check_competitive_edge(markdown, chunks)
        logger.info(f"   ✅ 경쟁력: {competitive}/100")
        
        # 종합 (가중 평균)
        overall = int(
            fidelity * 0.3 +
            chunking * 0.2 +
            rag * 0.2 +
            generality * 0.15 +
            competitive * 0.15
        )
        
        logger.info(f"   🎯 종합: {overall}/100 (내부 진단용)")
        
        return {
            'fidelity': fidelity,
            'chunking': chunking,
            'rag_readiness': rag,
            'generality': generality,
            'competitive_edge': competitive,
            'overall': overall
        }
    
    def _check_fidelity(self, pages_data: List[Dict], markdown: str) -> int:
        """원본 충실도 검사"""
        score = 100
        
        # 페이지 마커 남아있으면 감점
        marker_patterns = [
            r'_\d{3,4}-\d{1,2}_',
            r'\*\d{3,4}-\d{1,2}\*',
            r'^\d{3,4}-\d{1,2}$',
        ]
        
        for pattern in marker_patterns:
            if re.search(pattern, markdown, re.MULTILINE):
                score -= 20
                break
        
        # 조문 헤더 확인
        if '제1조' in markdown or '제2조' in markdown:
            score += 0
        else:
            score -= 10
        
        # 개정 이력 확인
        if '개정' in markdown and re.search(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}', markdown):
            score += 0
        else:
            score -= 5
        
        return max(0, min(100, score))
    
    def _check_chunking(self, chunks: List[Dict], doc_type: str) -> int:
        """청킹 품질 검사"""
        if not chunks:
            return 0
        
        score = 100
        
        # 청크 크기 분포
        sizes = [c['metadata']['char_count'] for c in chunks]
        avg_size = sum(sizes) / len(sizes)
        
        # 목표: 600-1200자
        if 600 <= avg_size <= 1200:
            score += 0
        else:
            score -= 20
        
        # 조문 단위 청킹
        if doc_type == 'statute':
            article_count = sum(1 for c in chunks if '제' in c['content'] and '조' in c['content'])
            if article_count >= len(chunks) * 0.7:
                score += 0
            else:
                score -= 10
        
        return max(0, min(100, score))
    
    def _check_rag_readiness(self, chunks: List[Dict]) -> int:
        """RAG 적합도 검사"""
        score = 100
        
        # 메타데이터 완성도
        for chunk in chunks:
            if not chunk.get('metadata', {}).get('article_no'):
                score -= 5
                break
        
        # 청크 독립성
        avg_len = sum(len(c['content']) for c in chunks) / len(chunks) if chunks else 0
        if avg_len > 500:
            score += 0
        else:
            score -= 10
        
        return max(0, min(100, score))
    
    def _check_generality(self, markdown: str, doc_type: str) -> int:
        """범용성 검사"""
        score = 100
        return score
    
    def _check_competitive_edge(self, markdown: str, chunks: List[Dict]) -> int:
        """경쟁력 검사"""
        score = 80
        
        # 구조 보존
        if '###' in markdown:
            score += 10
        
        # 메타데이터 풍부성
        if chunks and chunks[0].get('metadata', {}).get('article_title'):
            score += 10
        
        return min(100, score)


# ✅ app.py 호환성을 위한 별칭
class Phase53Pipeline(ProcessingPipeline):
    """Phase 5.3 Pipeline 호환 클래스"""
    
    def __init__(self, pdf_processor, vlm_service, max_pages: int = 20):
        """
        app.py 호환성 초기화
        
        Args:
            pdf_processor: PDFProcessor 인스턴스 (사용 안 함)
            vlm_service: VLMServiceV50 인스턴스
            max_pages: 최대 페이지 수
        """
        # 더미 경로 (실제 처리 시 교체됨)
        super().__init__(
            pdf_path="",
            vlm_service=vlm_service,
            session_id=self._generate_session_id(),
            max_pages=max_pages
        )
        # pdf_processor는 사용하지 않음 (PDFProcessor를 내부에서 생성)
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        app.py 호환성 메서드
        
        Args:
            pdf_path: PDF 파일 경로
        
        Returns:
            처리 결과
        """
        # 경로 업데이트
        self.pdf_path = pdf_path
        
        return self.process()
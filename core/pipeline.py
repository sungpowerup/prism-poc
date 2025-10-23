"""
core/pipeline.py
PRISM Phase 4.2 - Pipeline (멀티스텝 검증 및 청킹)

✅ Phase 4.2 개선사항:
1. 2-Pass VLM 처리
2. 자동 품질 검증
3. 재시도 로직 강화
4. 청킹 자동 생성

Author: 이서영 (Backend Lead), 박준호 (AI/ML Lead)
Date: 2025-10-23
Version: 4.2
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid
import re

logger = logging.getLogger(__name__)


class Phase42Pipeline:
    """
    Phase 4.2 처리 파이프라인
    
    특징:
    - 2-Pass 멀티스텝 처리
    - 자동 품질 검증
    - 강화된 재시도
    """
    
    def __init__(self, pdf_processor, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMServiceV42 인스턴스
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
        PDF 처리 메인 함수 (Phase 4.2)
        
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
        logger.info(f"🚀 Phase 4.2 처리 시작: {pdf_path}")
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
        # Stage 2: 2-Pass VLM 분석
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        results = []
        success_count = 0
        error_count = 0
        retry_count = 0
        low_confidence_count = 0
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int((page_num / len(images)) * 90)
                progress_callback(
                    f"🎯 페이지 {page_num + 1}/{len(images)} 2-Pass 분석 중...",
                    progress
                )
            
            logger.info(f"\n[Stage 2] 페이지 {page_num + 1} - 2-Pass VLM 분석")
            
            # 재시도 로직 (최대 3회)
            max_retries = 3
            attempt = 0
            best_result = None
            best_confidence = 0.0
            
            while attempt < max_retries:
                try:
                    logger.info(f"   시도 {attempt + 1}/{max_retries}...")
                    
                    # 2-Pass VLM 호출
                    vlm_result = self.vlm_service.analyze_page_multipass(
                        image_data=img_data,
                        page_num=page_num + 1
                    )
                    
                    content = vlm_result.get('content', '')
                    confidence = vlm_result.get('confidence', 0.0)
                    
                    if not content:
                        logger.warning(f"   ⚠️ VLM 결과 없음")
                        attempt += 1
                        retry_count += 1
                        continue
                    
                    # 품질 검증
                    is_valid, error_msg = self._validate_quality(content)
                    
                    if is_valid and confidence >= 0.8:
                        # 성공!
                        success_count += 1
                        logger.info(f"   ✅ 성공 ({len(content)} 글자, 신뢰도: {confidence:.2f})")
                        
                        results.append({
                            'page_num': page_num + 1,
                            'content': content,
                            'confidence': confidence,
                            'pass1_structure': vlm_result.get('pass1_structure', {}),
                            'retries': attempt
                        })
                        break  # 성공 시 루프 탈출
                    
                    else:
                        # 품질 문제 - 재시도
                        if confidence < 0.8:
                            logger.warning(f"   ⚠️ 낮은 신뢰도: {confidence:.2f}")
                            low_confidence_count += 1
                        
                        if error_msg:
                            logger.warning(f"   ⚠️ 품질 문제: {error_msg}")
                        
                        # 최고 점수 저장
                        if confidence > best_confidence:
                            best_result = vlm_result
                            best_confidence = confidence
                        
                        attempt += 1
                        retry_count += 1
                
                except Exception as e:
                    logger.error(f"   ❌ VLM 호출 실패: {e}")
                    attempt += 1
                    retry_count += 1
            
            # 최대 재시도 후에도 실패 → 최선의 결과 사용
            if attempt >= max_retries and best_result:
                logger.warning(f"   ⚠️ 최대 재시도 초과, 최선 결과 사용 (신뢰도: {best_confidence:.2f})")
                success_count += 1
                
                results.append({
                    'page_num': page_num + 1,
                    'content': best_result.get('content', ''),
                    'confidence': best_confidence,
                    'pass1_structure': best_result.get('pass1_structure', {}),
                    'retries': attempt,
                    'warning': 'low_confidence'
                })
            
            elif attempt >= max_retries:
                error_count += 1
                logger.error(f"   ❌ 페이지 {page_num + 1} 처리 완전 실패")
        
        logger.info(f"\n✅ VLM 분석 완료:")
        logger.info(f"   - 성공: {success_count}개")
        logger.info(f"   - 실패: {error_count}개")
        logger.info(f"   - 재시도: {retry_count}회")
        logger.info(f"   - 낮은 신뢰도: {low_confidence_count}개")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 3: Markdown 통합
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if progress_callback:
            progress_callback("📝 Markdown 생성 중...", 95)
        
        logger.info(f"\n[Stage 3] Markdown 통합")
        
        # 전체 Markdown 생성
        full_markdown = self._generate_markdown(results)
        
        logger.info(f"✅ Markdown 생성 완료 ({len(full_markdown)} 글자)")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Stage 4: 품질 점수 계산
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        avg_confidence = sum(r.get('confidence', 0.0) for r in results) / len(results) if results else 0.0
        quality_score = self._calculate_quality_score(results, full_markdown)
        
        logger.info(f"\n[품질 점수]")
        logger.info(f"   - 평균 신뢰도: {avg_confidence:.2f}")
        logger.info(f"   - 품질 점수: {quality_score:.1f}/100")
        
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
            'retry_count': retry_count,
            'low_confidence_count': low_confidence_count,
            'avg_confidence': avg_confidence,
            'quality_score': quality_score,
            'total_chars': len(full_markdown),
            'markdown': full_markdown,
            'page_results': results
        }
        
        # DB 저장
        try:
            self.storage.save_session(result)
            logger.info("✅ DB 저장 완료")
        except Exception as e:
            logger.error(f"⚠️ DB 저장 실패: {e}")
        
        if progress_callback:
            progress_callback("✅ 완료!", 100)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Phase 4.2 처리 완료")
        logger.info(f"   - 처리 시간: {processing_time:.1f}초")
        logger.info(f"   - 페이지 성공: {success_count}/{len(images)}")
        logger.info(f"   - 평균 신뢰도: {avg_confidence:.2f}")
        logger.info(f"   - 품질 점수: {quality_score:.1f}/100")
        logger.info(f"   - 총 글자 수: {len(full_markdown):,}")
        logger.info(f"{'='*60}\n")
        
        return result
    
    def _validate_quality(self, content: str) -> tuple[bool, Optional[str]]:
        """
        품질 검증
        
        Returns:
            (is_valid, error_message)
        """
        # 1. 최소 길이 확인
        if len(content) < 100:
            return False, "내용이 너무 짧음"
        
        # 2. 백분율 검증
        percentages = re.findall(r'(\d+\.?\d*)%', content)
        
        if len(percentages) >= 3:
            values = [float(p) for p in percentages]
            
            # 연속된 백분율 그룹 찾기
            valid_groups = 0
            for i in range(len(values)):
                group_sum = values[i]
                for j in range(i+1, min(i+10, len(values))):
                    group_sum += values[j]
                    
                    if 99.0 <= group_sum <= 101.0:
                        valid_groups += 1
                        break
                    
                    if group_sum > 105.0:
                        break
            
            # 백분율이 있는데 유효한 그룹이 없으면 문제
            if valid_groups == 0 and len(values) >= 3:
                return False, f"백분율 합계 검증 실패 (합계: {sum(values):.1f}%)"
        
        # 3. 숫자 패턴 확인 (최소한의 데이터 존재)
        numbers = re.findall(r'\d+\.?\d*', content)
        if len(numbers) < 5:
            return False, "숫자 데이터 부족"
        
        return True, None
    
    def _calculate_quality_score(self, results: List[Dict], markdown: str) -> float:
        """
        품질 점수 계산 (0~100)
        
        기준:
        - 평균 신뢰도: 40%
        - 청킹 품질: 30%
        - 데이터 밀도: 30%
        """
        if not results:
            return 0.0
        
        # 1. 평균 신뢰도 (40점)
        avg_confidence = sum(r.get('confidence', 0.0) for r in results) / len(results)
        confidence_score = avg_confidence * 40
        
        # 2. 청킹 품질 (30점)
        sections = markdown.split('---')
        chunking_score = min(len(sections) * 5, 30)  # 섹션당 5점, 최대 30점
        
        # 3. 데이터 밀도 (30점)
        numbers = re.findall(r'\d+\.?\d*', markdown)
        data_density = min(len(numbers) / 50 * 30, 30)  # 숫자 50개당 30점
        
        total_score = confidence_score + chunking_score + data_density
        
        return min(total_score, 100.0)
    
    def _generate_markdown(self, results: List[Dict[str, Any]]) -> str:
        """
        페이지별 결과를 하나의 Markdown으로 통합
        
        Args:
            results: 페이지별 VLM 결과 리스트
        
        Returns:
            통합된 Markdown 문자열
        """
        markdown_parts = []
        
        for result in results:
            page_num = result['page_num']
            content = result['content']
            confidence = result.get('confidence', 0.0)
            retries = result.get('retries', 0)
            
            # 디버그 정보 (주석 처리 가능)
            if retries > 0:
                logger.info(f"   페이지 {page_num}: {retries}회 재시도, 신뢰도 {confidence:.2f}")
            
            # 페이지 내용 추가
            markdown_parts.append(content)
            markdown_parts.append("\n\n")
        
        return "".join(markdown_parts).strip()
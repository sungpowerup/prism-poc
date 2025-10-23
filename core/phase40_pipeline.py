"""
core/phase40_pipeline.py
PRISM Phase 4.0 - VLM-First Pipeline (완전 재설계)

🔥 Phase 4.0 핵심 전략:
1. Layout Detection 완전 제거 (헤더/푸터만 유지)
2. 페이지 전체를 VLM에 전송 (맥락 유지)
3. 자연어 설명 요구 (JSON 아님)
4. Markdown 출력 (경쟁사 수준)
5. 범용성 우선 (모든 문서 대응)

Author: 전체 팀 (재설계)
Date: 2025-10-23
Version: 4.0
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid

logger = logging.getLogger(__name__)


class Phase40Pipeline:
    """
    Phase 4.0 처리 파이프라인 (VLM-First)
    
    특징:
    - Layout Detection 최소화 (불필요)
    - 페이지 전체 VLM 처리
    - 자연어 설명 생성
    - Markdown 출력
    """
    
    def __init__(self, pdf_processor, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMService 인스턴스
            storage: Storage 인스턴스
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        self.storage = storage
        
        # Phase 4.0 범용 프롬프트 (모든 문서 대응)
        self.prompt = """당신은 전문 문서 분석가입니다. 이 문서 페이지를 상세히 분석하여 자연어로 설명하세요.

**분석 요구사항:**

1. **페이지 구조 파악**
   - 제목, 섹션, 서브섹션 식별
   - 계층 구조 유지

2. **텍스트 내용 추출**
   - 모든 텍스트 정확히 추출
   - 맥락을 유지하며 작성

3. **시각 요소 분석**
   - 차트 (원그래프, 막대그래프, 선그래프 등)
     → 형태, 제목, 데이터, 의미 해석
   - 표 (테이블)
     → 헤더, 행/열 데이터, 의미
   - 지도/다이어그램
     → 지역명, 데이터, 관계
   - 이미지/아이콘
     → 역할, 의미

4. **데이터 해석**
   - 숫자의 의미 설명
   - 데이터 간 관계 설명
   - 주요 인사이트 제시

5. **독자 친화성**
   - 사람이 읽기 쉽게 작성
   - 전문 용어 설명 포함
   - 맥락 유지

**출력 형식 (Markdown):**

```markdown
### [섹션 제목]

[텍스트 내용 - 있는 경우]

#### [서브섹션 제목]

[텍스트 내용]

[차트/표 설명]
- **차트 형태**: [원그래프/막대그래프/표 등]
- **제목**: [차트 제목]
- **데이터**: 
  - [항목1]: [값1] ([단위] - [의미])
  - [항목2]: [값2] ([단위] - [의미])
  ...
- **해석**: [데이터의 의미와 인사이트]

[추가 텍스트 내용]
```

**중요 원칙:**

✅ **반드시 지킬 것:**
- 모든 텍스트를 빠짐없이 추출
- 모든 차트/표의 데이터를 완전히 추출
- 자연어로 서술 (JSON 금지)
- 맥락을 유지하며 설명
- 섹션 계층 구조 유지

❌ **절대 하지 말 것:**
- JSON/XML 같은 구조화된 데이터만 반환
- "이미지에 ~가 있습니다" 같은 메타 설명
- 데이터 누락 또는 생략
- 맥락 없는 단순 나열

**예시 (좋은 출력):**

```markdown
### 06. 응답자 특성

2023년 조사에 참여한 전체 응답자는 총 35,000명이며 이 중 프로스포츠 팬은 25,000명, 일반국민은 10,000명으로 응답자 주요 특성은 아래와 같습니다.

#### 응답자 성별 및 연령

성별 분포를 보면 원그래프에서 남성이 45.2%를 차지하며, 여성이 54.8%로 여성 응답자의 비중이 더 높습니다.

연령대별 분포는 막대그래프로 나타나며, 각 연령대별 비율은 다음과 같습니다:
- **14~19세**: 11.2%
- **20대**: 25.9% (가장 높은 비율)
- **30대**: 22.3%
- **40대**: 19.9%
- **50대 이상**: 20.7%

이 데이터를 통해 20대 응답자가 가장 많았음을 알 수 있습니다.
```

이제 페이지를 분석하세요."""
    
    def process_pdf(
        self, 
        pdf_path: str, 
        max_pages: int = 20,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수 (Phase 4.0)
        
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
        logger.info(f"🚀 Phase 4.0 처리 시작 (VLM-First): {pdf_path}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"{'='*60}")
        
        # ========================================
        # Stage 1: PDF → 고해상도 이미지 변환
        # ========================================
        if progress_callback:
            progress_callback("📄 PDF 변환 중 (고해상도)...", 0)
        
        logger.info("\n[Stage 1] PDF → 고해상도 이미지 변환 (300 DPI)")
        images = self.pdf_processor.pdf_to_images(pdf_path, max_pages=max_pages, dpi=300)
        logger.info(f"✅ {len(images)}개 페이지 변환 완료")
        
        if not images:
            logger.error("❌ PDF 변환 실패")
            return {
                'status': 'error',
                'error': 'PDF 변환 실패',
                'session_id': session_id
            }
        
        # ========================================
        # Stage 2: VLM 전체 페이지 분석
        # ========================================
        results = []
        success_count = 0
        error_count = 0
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int((page_num / len(images)) * 90)
                progress_callback(f"🤖 페이지 {page_num + 1}/{len(images)} 분석 중...", progress)
            
            logger.info(f"\n[Stage 2] 페이지 {page_num + 1} - VLM 전체 분석")
            
            try:
                # VLM 호출 (페이지 전체)
                logger.info(f"   페이지 {page_num + 1} VLM 분석 시작...")
                
                vlm_result = self.vlm_service.analyze_page(
                    image_data=img_data,
                    prompt=self.prompt
                )
                
                if vlm_result and len(vlm_result.strip()) > 0:
                    success_count += 1
                    logger.info(f"   ✅ 성공 ({len(vlm_result)} 글자)")
                    
                    results.append({
                        'page_num': page_num + 1,
                        'content': vlm_result,
                        'char_count': len(vlm_result)
                    })
                else:
                    error_count += 1
                    logger.warning(f"   ⚠️ VLM 결과 없음")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"   ❌ 실패: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"\n✅ VLM 분석 완료: 성공 {success_count}개, 실패 {error_count}개")
        
        # ========================================
        # Stage 3: Markdown 통합
        # ========================================
        if progress_callback:
            progress_callback("📝 Markdown 생성 중...", 95)
        
        logger.info(f"\n[Stage 3] Markdown 통합")
        
        # 전체 Markdown 생성
        full_markdown = self._generate_markdown(results)
        
        logger.info(f"✅ Markdown 생성 완료 ({len(full_markdown)} 글자)")
        
        # ========================================
        # Stage 4: 결과 저장
        # ========================================
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
        logger.info(f"🎉 Phase 4.0 처리 완료")
        logger.info(f"   - 처리 시간: {processing_time:.1f}초")
        logger.info(f"   - 페이지 성공: {success_count}/{len(images)}")
        logger.info(f"   - 총 글자 수: {len(full_markdown):,}")
        logger.info(f"{'='*60}\n")
        
        return result
    
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
            
            # 페이지 구분자 (선택적)
            # markdown_parts.append(f"\n---\n\n## 페이지 {page_num}\n\n")
            
            # 페이지 내용
            markdown_parts.append(content)
            markdown_parts.append("\n\n")
        
        return "".join(markdown_parts).strip()

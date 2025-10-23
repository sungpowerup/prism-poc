"""
core/phase41_pipeline.py
PRISM Phase 4.1 - Accurate Pipeline (정확도 개선)

✅ Phase 4.1 개선사항:
1. 정확도 최우선 프롬프트 적용
2. 백분율 합계 검증
3. Temperature 낮춤 (0.3 → 0.1)
4. 재시도 로직 추가 (백분율 오류 시)

Author: 박준호 (AI/ML Lead), 이서영 (Backend Lead)
Date: 2025-10-23
Version: 4.1
"""

import logging
from typing import List, Dict, Any, Optional
import time
import uuid

logger = logging.getLogger(__name__)


class Phase41Pipeline:
    """
    Phase 4.1 처리 파이프라인 (정확도 개선)
    
    특징:
    - 원본 텍스트 100% 충실도
    - 백분율 합계 자동 검증
    - 오류 감지 시 재시도
    """
    
    def __init__(self, pdf_processor, vlm_service, storage):
        """
        Args:
            pdf_processor: PDFProcessor 인스턴스
            vlm_service: VLMService 인스턴스 (v4.1)
            storage: Storage 인스턴스
        """
        self.pdf_processor = pdf_processor
        self.vlm_service = vlm_service
        self.storage = storage
        
        # ✅ Phase 4.1: 정확도 최우선 프롬프트
        self.prompt = """당신은 전문 문서 분석가입니다. 이 문서 페이지를 **완벽한 정확도**로 분석하세요.

🎯 **Phase 4.1 핵심 원칙: 100% 원본 충실도**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ⚠️ 절대 준수 사항 (CRITICAL)

### 1. 텍스트/숫자 변경 금지
- 원본 텍스트를 **정확히 그대로** 추출
- 숫자 반올림 금지 (52.5% ≠ 53%)
- 단어 추가/변경 금지 (수도권 ≠ 수도권 지역)

### 2. 지역명/용어 변경 금지
- 원본: "강원/제주권" → 출력: "강원/제주권" ✅
- 원본: "강원/제주권" → 출력: "강원권", "제주권" ❌ (분리 금지)

### 3. 백분율 합계 검증
- 동일한 차트 내 백분율 합계 = 100% (오차 ±1%)
- 합계가 맞지 않으면 다시 확인

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 분석 요구사항

### 1. 페이지 구조 파악
- 제목, 섹션, 서브섹션 식별
- 계층 구조 유지

### 2. 텍스트 내용 추출
- 모든 텍스트를 정확히 추출 (한 글자도 빠짐없이)
- 맥락을 유지하며 작성
- 원본 표현 그대로 사용

### 3. 시각 요소 분석

#### 차트 (원그래프, 막대그래프, 선그래프 등)
```markdown
**차트 형태:** [형태]
**제목:** [원본 그대로]
**데이터:**
- [항목명 그대로]: [숫자 정확히]% 또는 [단위]
- ...

**백분율 검증:** 합계 [XX.X]%
**해석:** [1~2문장]
```

#### 지도 차트 특별 처리
```
⚠️ 지역명과 수치를 절대 변경하지 말고 그대로 추출

✅ 올바른 예:
원본: "강원/제주 4.7%"
출력: 강원/제주권: 4.7%

❌ 잘못된 예:
원본: "강원/제주 4.7%"
출력: 강원권 + 제주권 분리 (금지)
```

#### 표 (Table)
```markdown
| 헤더1 | 헤더2 |
|-------|-------|
| 값1   | 값2   |

- 모든 셀 정확히 추출
- 숫자는 소수점 이하까지
```

### 4. 데이터 해석
- 숫자의 의미 설명 (1~2문장)
- 주요 인사이트 제시

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📝 출력 형식

```markdown
### [섹션 제목 - 원본 그대로]

[텍스트 내용]

#### [서브섹션 제목]

**차트 형태:** [...]
**제목:** [...]
**데이터:**
- [항목]: [값]
...

**백분율 검증:** 합계 XX.X%
**해석:** [...]
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ 체크리스트

- [ ] 모든 텍스트를 원본 그대로 추출
- [ ] 모든 숫자를 정확히 추출 (소수점 포함)
- [ ] 지역명/용어를 변경하지 않음
- [ ] 백분율 합계가 100% (±1%)
- [ ] 추측하지 않고 보이는 대로만 작성

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🚫 절대 금지

❌ 숫자 반올림
❌ 단어 추가/변경
❌ 지역명 분리
❌ 데이터 누락
❌ 추측

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이제 페이지를 분석하세요. **정확도 최우선!**
"""
    
    def process_pdf(
        self, 
        pdf_path: str, 
        max_pages: int = 20,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        PDF 처리 메인 함수 (Phase 4.1 - 정확도 개선)
        
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
        logger.info(f"🎯 Phase 4.1 처리 시작 (정확도 최우선): {pdf_path}")
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
        # Stage 2: VLM 전체 페이지 분석 (정확도 최우선)
        # ========================================
        results = []
        success_count = 0
        error_count = 0
        retry_count = 0  # ✅ Phase 4.1: 재시도 횟수
        
        for page_num, img_data in enumerate(images):
            if progress_callback:
                progress = int((page_num / len(images)) * 90)
                progress_callback(f"🎯 페이지 {page_num + 1}/{len(images)} 정확 분석 중...", progress)
            
            logger.info(f"\n[Stage 2] 페이지 {page_num + 1} - VLM 정확 분석")
            
            # ✅ Phase 4.1: 재시도 로직 (최대 2회)
            max_retries = 2
            attempt = 0
            vlm_result = None
            
            while attempt <= max_retries:
                try:
                    logger.info(f"   시도 {attempt + 1}/{max_retries + 1}...")
                    
                    # VLM 호출
                    vlm_result = self.vlm_service.analyze_page(
                        image_data=img_data,
                        prompt=self.prompt
                    )
                    
                    if vlm_result and len(vlm_result.strip()) > 0:
                        # 백분율 검증
                        is_valid = self._validate_result(vlm_result)
                        
                        if is_valid:
                            success_count += 1
                            logger.info(f"   ✅ 성공 ({len(vlm_result)} 글자)")
                            
                            results.append({
                                'page_num': page_num + 1,
                                'content': vlm_result,
                                'char_count': len(vlm_result),
                                'retries': attempt
                            })
                            break  # 성공 시 루프 탈출
                        else:
                            logger.warning(f"   ⚠️ 백분율 검증 실패 (재시도 {attempt + 1})")
                            attempt += 1
                            retry_count += 1
                    else:
                        logger.warning(f"   ⚠️ VLM 결과 없음 (재시도 {attempt + 1})")
                        attempt += 1
                        retry_count += 1
                
                except Exception as e:
                    logger.error(f"   ❌ VLM 호출 실패: {e}")
                    attempt += 1
                    retry_count += 1
            
            # 최대 재시도 후에도 실패
            if attempt > max_retries and (not vlm_result or len(vlm_result.strip()) == 0):
                error_count += 1
                logger.error(f"   ❌ 페이지 {page_num + 1} 처리 실패 (최대 재시도 초과)")
        
        logger.info(f"\n✅ VLM 분석 완료: 성공 {success_count}개, 실패 {error_count}개, 재시도 {retry_count}회")
        
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
            'retry_count': retry_count,  # ✅ Phase 4.1: 재시도 횟수 추가
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
        logger.info(f"🎉 Phase 4.1 처리 완료 (정확도 최우선)")
        logger.info(f"   - 처리 시간: {processing_time:.1f}초")
        logger.info(f"   - 페이지 성공: {success_count}/{len(images)}")
        logger.info(f"   - 재시도 횟수: {retry_count}회")
        logger.info(f"   - 총 글자 수: {len(full_markdown):,}")
        logger.info(f"{'='*60}\n")
        
        return result
    
    def _validate_result(self, text: str) -> bool:
        """
        VLM 결과 검증 (Phase 4.1)
        
        Args:
            text: VLM 응답 텍스트
        
        Returns:
            검증 성공 여부
        """
        import re
        
        # 백분율 패턴 찾기
        percentage_pattern = r'(\d+\.?\d*)%'
        percentages = re.findall(percentage_pattern, text)
        
        if not percentages:
            # 백분율이 없으면 검증 통과 (텍스트만 있는 페이지)
            return True
        
        # 숫자로 변환
        values = [float(p) for p in percentages]
        
        # 연속된 백분율 그룹 찾기
        valid_groups = 0
        for i in range(len(values)):
            group_sum = values[i]
            for j in range(i+1, min(i+10, len(values))):
                group_sum += values[j]
                
                # 합계가 99~101% 사이면 유효한 그룹
                if 99.0 <= group_sum <= 101.0:
                    valid_groups += 1
                    logger.info(f"   ✅ 백분율 그룹 검증: {values[i:j+1]} = {group_sum:.1f}%")
                    break
                
                # 합계가 105%를 초과하면 그룹 종료
                if group_sum > 105.0:
                    break
        
        # 유효한 그룹이 하나라도 있으면 통과
        if valid_groups > 0:
            return True
        
        # 백분율이 3개 미만이면 통과 (단일 수치일 수 있음)
        if len(values) < 3:
            return True
        
        logger.warning(f"   ⚠️ 백분율 검증 실패: 유효한 그룹 없음 ({values})")
        return False
    
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
            retries = result.get('retries', 0)
            
            # 재시도 정보 (디버그용 - 실제 출력에는 제외 가능)
            if retries > 0:
                logger.info(f"   페이지 {page_num}: {retries}회 재시도 후 성공")
            
            # 페이지 내용
            markdown_parts.append(content)
            markdown_parts.append("\n\n")
        
        return "".join(markdown_parts).strip()
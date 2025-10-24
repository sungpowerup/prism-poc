"""
core/vlm_service_v50.py
PRISM Phase 5.0 - VLM Service (범용 전략 패턴)

✅ Phase 5.0 핵심:
1. 문서 타입 우선 판별
2. 타입별 전략 자동 선택
3. 범용 프롬프트 (하드코딩 제로)
4. 원본 충실도 95% 목표

Author: 박준호 (AI/ML Lead)
Date: 2025-10-24
Version: 5.0
"""

import os
import logging
import json
import re
from typing import Dict, Any
from openai import AzureOpenAI
from anthropic import Anthropic
from dotenv import load_dotenv
from document_classifier import DocumentClassifierV50

load_dotenv()
logger = logging.getLogger(__name__)


class VLMServiceV50:
    """
    범용 VLM 서비스 v5.0
    
    특징:
    - 문서 타입 자동 인식
    - 전략 패턴 자동 적용
    - 완전 범용 설계
    """
    
    def __init__(self, provider: str = "azure_openai"):
        """VLM 서비스 초기화"""
        self.provider = provider
        
        if provider == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            
            if not all([api_key, azure_endpoint, deployment]):
                raise ValueError("❌ Azure OpenAI 환경 변수 누락")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            self.deployment = deployment
            
        elif provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("❌ ANTHROPIC_API_KEY 환경 변수 누락")
            
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        
        # 문서 타입 분류기
        self.classifier = DocumentClassifierV50(provider)
        
        logger.info(f"✅ VLM Service v5.0 초기화 완료: {provider}")
    
    def analyze_page_v50(
        self,
        image_data: str,
        page_num: int
    ) -> Dict[str, Any]:
        """
        Phase 5.0: 범용 문서 분석
        
        1단계: 문서 타입 판별
        2단계: 타입별 전략 선택
        3단계: 구조 분석
        4단계: 내용 추출
        5단계: 품질 평가
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Page {page_num}: Phase 5.0 범용 분석 시작")
        logger.info(f"{'='*60}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 1: 문서 타입 판별
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"\n[Step 1] 문서 타입 판별...")
        
        doc_type_result = self.classifier.classify(image_data, page_num)
        
        doc_type = doc_type_result.get('type', 'mixed')
        subtype = doc_type_result.get('subtype', 'unknown')
        confidence = doc_type_result.get('confidence', 0.5)
        
        logger.info(f"✅ 타입: {doc_type} ({subtype}), 신뢰도: {confidence:.2f}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 2-4: 타입별 전략 실행
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"\n[Step 2-4] 타입별 내용 추출...")
        
        if doc_type == 'text_document':
            content = self._extract_text_document(image_data, subtype)
        elif doc_type == 'diagram':
            content = self._extract_diagram(image_data, subtype)
        elif doc_type == 'technical_drawing':
            content = self._extract_technical_drawing(image_data, subtype)
        elif doc_type == 'image_content':
            content = self._extract_image_content(image_data, subtype)
        elif doc_type == 'chart_statistics':
            content = self._extract_chart_statistics(image_data, subtype)
        else:  # mixed
            content = self._extract_mixed(image_data)
        
        logger.info(f"✅ 추출 완료: {len(content)} 글자")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 5: 품질 평가
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        quality_score = self._calculate_quality(content, doc_type)
        
        logger.info(f"✅ 품질: {quality_score:.1f}/100")
        logger.info(f"{'='*60}\n")
        
        return {
            'content': content,
            'confidence': confidence,
            'strategy': f'{doc_type}_v50',
            'doc_type': doc_type,
            'subtype': subtype,
            'quality_score': quality_score,
            'structure': doc_type_result
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 타입별 추출 메서드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _extract_text_document(self, image_data: str, subtype: str) -> str:
        """텍스트 문서 추출 (사규, 계약서, 보고서)"""
        
        prompt = f"""이 {subtype} 문서의 내용을 Markdown으로 추출하세요.

**형식:**
# [문서 제목]

**문서 정보**
- 문서번호: [번호]
- 제정일: [날짜]
- 개정일: [날짜]

## [첫 번째 섹션]

### [하위 섹션]
내용...

**중요 규칙:**
1. 원본 텍스트를 정확히 추출하세요
2. 조항/항 번호를 정확히 보존하세요
3. 표가 있으면 Markdown 표로 변환하세요
4. 메타 정보는 최소화하세요 (RAG 최적화)
5. 간결하게 작성하세요"""
        
        return self._call_vlm(image_data, prompt)
    
    def _extract_diagram(self, image_data: str, subtype: str) -> str:
        """다이어그램 추출 (노선도, 플로우차트, 조직도)"""
        
        if subtype == 'transport_route':
            prompt = """이 교통 노선도를 분석하여 노선 정보를 추출하세요.

**형식:**
## 노선 정보

**노선명**: [노선번호/이름]
**운행 정보**: [배차간격, 운행시간 등]

### 경로
1. [출발지]
2. [경유지 1]
3. [경유지 2]
...
n. [종점]

**주의:**
- 정류장/역 이름을 정확히 추출하세요
- 순서를 정확히 지키세요
- 중복 없이 추출하세요"""
        
        elif subtype == 'flowchart':
            prompt = """이 플로우차트를 분석하여 프로세스를 추출하세요.

**형식:**
## 프로세스 플로우

### 단계
1. **[단계 이름]**
   - 내용: [설명]
   - 조건: [있다면]
   - 다음: [다음 단계]

2. **[단계 이름]**
   ...

### 의사결정 포인트
- [조건 A] → [결과 1]
- [조건 B] → [결과 2]"""
        
        else:  # organization, network 등
            prompt = """이 다이어그램을 분석하여 구조를 추출하세요.

**형식:**
## 구조

### 주요 요소
- [요소 1]: [설명]
- [요소 2]: [설명]

### 관계
- [요소 1] → [요소 2]: [관계 설명]"""
        
        return self._call_vlm(image_data, prompt)
    
    def _extract_technical_drawing(self, image_data: str, subtype: str) -> str:
        """기술 도면 추출 (인테리어, 건축)"""
        
        prompt = """이 도면을 분석하여 공간 정보를 추출하세요.

**형식:**
## 평면도

**전체 정보**
- 총 면적: [면적]
- 축척: [축척]

### 공간 구성
1. **[공간 이름]** ([면적])
   - 위치: [방향/위치]
   - 치수: [가로 × 세로]
   - 특징: [주요 특징]

2. **[공간 이름]**
   ...

**주의:**
- 공간 이름을 정확히 추출하세요
- 치수 정보를 포함하세요
- 간결하게 작성하세요"""
        
        return self._call_vlm(image_data, prompt)
    
    def _extract_image_content(self, image_data: str, subtype: str) -> str:
        """이미지 콘텐츠 추출 (패션, 제품)"""
        
        prompt = """이 이미지를 분석하여 내용을 설명하세요.

**형식:**
## 이미지 설명

### 주요 요소
- [요소 1]: [설명]
- [요소 2]: [설명]

### 시각적 특징
- 색상: [주요 색상]
- 스타일: [스타일 설명]
- 분위기: [분위기]

### 세부 사항
[상세 설명]

**주의:**
- 객관적으로 설명하세요
- 간결하게 작성하세요
- 불필요한 추측은 피하세요"""
        
        return self._call_vlm(image_data, prompt)
    
    def _extract_chart_statistics(self, image_data: str, subtype: str) -> str:
        """차트/통계 추출"""
        
        prompt = """이 차트/표를 분석하여 데이터를 추출하세요.

**형식:**
## 데이터

**차트 제목**: [제목]
**차트 타입**: [막대/원형/선 등]

### 데이터 테이블

| [항목] | [값 1] | [값 2] | [값 3] |
|--------|--------|--------|--------|
| [행 1] | [값]   | [값]   | [값]   |
| [행 2] | [값]   | [값]   | [값]   |

### 주요 발견
- [핵심 인사이트 1]
- [핵심 인사이트 2]

**주의:**
- 데이터를 정확히 추출하세요
- 표 형식으로 정리하세요
- 간결하게 작성하세요"""
        
        return self._call_vlm(image_data, prompt)
    
    def _extract_mixed(self, image_data: str) -> str:
        """복합 문서 추출"""
        
        prompt = """이 문서의 내용을 Markdown으로 추출하세요.

**형식:**
## [문서 제목]

### [섹션 1]
내용...

### [섹션 2]
내용...

**주의:**
- 문서 구조를 파악하여 적절히 추출하세요
- 텍스트, 표, 이미지 등을 모두 포함하세요
- 간결하고 명확하게 작성하세요"""
        
        return self._call_vlm(image_data, prompt)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VLM 호출
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _call_vlm(self, image_data: str, prompt: str) -> str:
        """VLM 호출"""
        
        try:
            if self.provider == "azure_openai":
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{image_data}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.2
                )
                
                return response.choices[0].message.content.strip()
                
            else:  # claude
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_data
                                    }
                                },
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                )
                
                return response.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"❌ VLM 호출 실패: {e}")
            return f"## 추출 실패\n오류: {str(e)}"
    
    def _calculate_quality(self, content: str, doc_type: str) -> float:
        """품질 평가 (범용)"""
        score = 100.0
        
        # 최소 길이 체크
        if len(content) < 50:
            score -= 30
        
        # 구조 체크 (헤더 존재)
        headers = re.findall(r'^#+\s+', content, re.MULTILINE)
        if len(headers) == 0:
            score -= 20
        elif len(headers) >= 3:
            score += 10
        
        # RAG 불필요 내용 체크
        meta_keywords = [
            '이 문서는', '다음과 같이', '아래와 같이',
            '볼 수 있습니다', '확인할 수 있습니다'
        ]
        for keyword in meta_keywords:
            if keyword in content:
                score -= 5
        
        return max(0.0, min(100.0, score))
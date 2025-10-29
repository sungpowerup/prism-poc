# PRISM Phase 5.7.0 - 통합 가이드

**버전:** 5.7.0 v1.0  
**날짜:** 2025-10-27  
**목표:** "평문 → 법령 트리" 완전 구현

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설치 및 적용](#설치-및-적용)
4. [사용 방법](#사용-방법)
5. [테스트](#테스트)
6. [성능 평가](#성능-평가)

---

## 개요

### Phase 5.7.0 완성 요약

**김민지 (PM):** "4개 컴포넌트로 완전한 법령 트리 시스템을 구축했습니다!"

| 컴포넌트 | 역할 | 파일 |
|----------|------|------|
| **TreeBuilder** | Markdown → Tree 변환 | `tree_builder_v570_v1_0.py` |
| **HierarchicalParser** | Tree 검증 + DoD | `hierarchical_parser_v570_v1_0.py` |
| **LLMAdapter** | Tree → RAG 프롬프트 | `llm_adapter_v570_v1_0.py` |
| **Tree Schema** | JSON 스키마 정의 | `Phase_570_Tree_Schema_v1_0.md` |

### 핵심 특징

1. ✅ **3단 계층 구조**: 조문(Article) → 항(Clause) → 호(Item)
2. ✅ **Phase 5.6.3 연동**: 7가지 지표로 자동 검증
3. ✅ **RAG 최적화**: 계층별 Top-k 검색 지원
4. ✅ **메타데이터 풍부**: 개정일, 삭제 여부, 변경 이력

---

## 아키텍처

### 전체 플로우

```
Markdown (Phase 5.6.x 출력)
    ↓
TreeBuilder
    ↓
법령 Tree (JSON)
    ↓
HierarchicalParser
    ↓
검증된 Tree + 메트릭
    ↓
LLMAdapter
    ↓
RAG 프롬프트
```

### 컴포넌트 의존성

```python
# TreeBuilder (독립)
tree_builder = TreeBuilder()
document = tree_builder.build(markdown, title="샘플 규정")

# HierarchicalParser (TreeBuilder 출력 필요)
parser = HierarchicalParser()
validated_document = parser.parse(document)

# LLMAdapter (HierarchicalParser 출력 권장)
adapter = LLMAdapter()
prompt = adapter.to_prompt(validated_document)
```

---

## 설치 및 적용

### Step 1: 파일 배치

```powershell
# Phase 5.7.0 컴포넌트
Copy-Item tree_builder_v570_v1_0.py core\tree_builder.py -Force
Copy-Item hierarchical_parser_v570_v1_0.py core\hierarchical_parser.py -Force
Copy-Item llm_adapter_v570_v1_0.py core\llm_adapter.py -Force

# 문서
Copy-Item Phase_570_Tree_Schema_v1_0.md README_570_SCHEMA.md -Force
Copy-Item Phase_570_Integration_Guide.md README_570_INTEGRATION.md -Force
```

### Step 2: 기존 Pipeline 통합

```python
# core/pipeline.py 수정

from .tree_builder import TreeBuilder
from .hierarchical_parser import HierarchicalParser
from .llm_adapter import LLMAdapter

class Phase57Pipeline:
    """Phase 5.7.0 통합 파이프라인"""
    
    def __init__(self, ...):
        # 기존 컴포넌트
        self.extractor = HybridExtractor(...)
        self.chunker = SemanticChunker(...)
        
        # ✅ Phase 5.7.0 신규
        self.tree_builder = TreeBuilder()
        self.hierarchical_parser = HierarchicalParser()
        self.llm_adapter = LLMAdapter()
    
    def process_pdf(self, pdf_path: str) -> Dict:
        # ... 기존 Phase 5.6.x 처리
        
        # ✅ Phase 5.7.0: Tree 생성
        markdown = result['markdown']
        
        # Step 1: Build
        document = self.tree_builder.build(
            markdown=markdown,
            document_title=Path(pdf_path).stem
        )
        
        # Step 2: Parse & Validate
        validated_doc = self.hierarchical_parser.parse(document)
        
        # Step 3: LLM Prompt
        prompt = self.llm_adapter.to_prompt(validated_doc)
        
        # Step 4: JSON Export
        json_export = self.llm_adapter.to_json_export(validated_doc)
        
        # 결과에 추가
        result['tree_document'] = validated_doc
        result['tree_prompt'] = prompt
        result['tree_json'] = json_export
        
        return result
```

---

## 사용 방법

### 기본 사용 (단일 문서)

```python
from core.tree_builder import TreeBuilder
from core.hierarchical_parser import HierarchicalParser
from core.llm_adapter import LLMAdapter

# Markdown 입력
markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.

### 제2조(정의)
이 규정에서 사용하는 용어의 정의는 다음과 같다.

① 다음 각 호의 어느 하나에 해당하는 경우
  가. 첫 번째 경우
  나. 두 번째 경우

② 제1항에도 불구하고...
"""

# Step 1: Build
builder = TreeBuilder()
document = builder.build(
    markdown=markdown,
    document_title="샘플 규정",
    enacted_date="2020.01.01"
)

# Step 2: Parse & Validate
parser = HierarchicalParser()
validated_doc = parser.parse(document)

# Step 3: LLM Prompt
adapter = LLMAdapter()
prompt = adapter.to_prompt(validated_doc)

print(prompt)
```

### 계층별 검색

```python
# 사용자 질의
query = "첫 번째 경우"

# Top-k 검색
results = adapter.to_hierarchical_context(
    document=validated_doc,
    query=query,
    top_k=3
)

for result in results:
    print(f"[{result['level']}] {result['text'][:100]}... (score: {result['score']})")
```

### JSON Export

```python
# JSON 저장
json_str = adapter.to_json_export(validated_doc)

with open('output.json', 'w', encoding='utf-8') as f:
    f.write(json_str)
```

---

## 테스트

### 테스트 스크립트

```python
"""
tests/test_phase_570.py
Phase 5.7.0 통합 테스트
"""

import pytest
from core.tree_builder import TreeBuilder
from core.hierarchical_parser import HierarchicalParser
from core.llm_adapter import LLMAdapter


def test_tree_builder_basic():
    """TreeBuilder 기본 테스트"""
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    # 검증
    assert 'document' in document
    assert 'tree' in document['document']
    assert len(document['document']['tree']) == 1
    
    article = document['document']['tree'][0]
    assert article['level'] == 'article'
    assert article['article_no'] == '제1조'
    assert article['article_title'] == '(목적)'


def test_tree_builder_with_clauses():
    """항·호 포함 테스트"""
    markdown = """
### 제1조(정의)
다음과 같다.

① 첫 번째 항
  가. 첫 번째 호
  나. 두 번째 호

② 두 번째 항
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    article = document['document']['tree'][0]
    
    # 항 검증
    assert len(article['children']) == 2
    
    clause1 = article['children'][0]
    assert clause1['level'] == 'clause'
    assert clause1['clause_no'] == '①'
    
    # 호 검증
    assert len(clause1['children']) == 2
    
    item1 = clause1['children'][0]
    assert item1['level'] == 'item'
    assert item1['item_no'] == '가.'


def test_hierarchical_parser():
    """HierarchicalParser 테스트"""
    # Tree 생성
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    # 파싱
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    # 메트릭 검증
    assert 'metrics' in validated['document']
    metrics = validated['document']['metrics']
    
    assert 'hierarchy_preservation_rate' in metrics
    assert 'boundary_cross_bleed_rate' in metrics
    assert 'empty_article_rate' in metrics
    assert 'dod_pass' in metrics


def test_llm_adapter_to_prompt():
    """LLMAdapter 프롬프트 생성 테스트"""
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    adapter = LLMAdapter()
    prompt = adapter.to_prompt(validated)
    
    # 검증
    assert '테스트 규정' in prompt
    assert '제1조' in prompt
    assert '(목적)' in prompt


def test_llm_adapter_hierarchical_search():
    """계층별 검색 테스트"""
    markdown = """
### 제1조(정의)
다음과 같다.

① 첫 번째 항
  가. 첫 번째 호
  나. 두 번째 호
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    adapter = LLMAdapter()
    results = adapter.to_hierarchical_context(
        document=validated,
        query="첫 번째",
        top_k=3
    )
    
    # 검증
    assert len(results) > 0
    assert any('첫 번째' in r['text'] for r in results)


def test_phase_563_integration():
    """Phase 5.6.3 지표 통합 테스트"""
    # 의도적 오류 케이스
    markdown = """
### 제1조(목적)
이 조문은 제2조를 참조한다.

### 제2조
<삭제 2024.01.01>
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    
    # 경계 누수 검출
    assert metrics['boundary_cross_bleed_rate'] > 0
    
    # 빈 조문 검출
    assert metrics['empty_article_rate'] > 0
    
    # DoD 실패
    assert not metrics['dod_pass']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### 실행

```powershell
# 전체 테스트
pytest tests/test_phase_570.py -v

# 단일 테스트
pytest tests/test_phase_570.py::test_tree_builder_basic -v
```

---

## 성능 평가

### 예상 성능

| 지표 | 목표 | 설명 |
|------|------|------|
| **계층 보존율** | ≥ 0.95 | 조·항·호 완전 검출 |
| **경계 누수율** | = 0 | 조문 혼입 없음 |
| **빈 조문율** | = 0 | 빈 조문 없음 |
| **처리 속도** | < 1초/문서 | Tree 생성 + 검증 |
| **RAG 정확도** | 10배 향상 | Flat 대비 |

### 벤치마크 스크립트

```python
"""
tests/benchmark_phase_570.py
Phase 5.7.0 성능 벤치마크
"""

import time
from pathlib import Path
from core.tree_builder import TreeBuilder
from core.hierarchical_parser import HierarchicalParser

# 테스트 문서 (10개 조문, 각 3개 항, 각 2개 호)
markdown = "\n\n".join([
    f"""### 제{i}조(제목{i})
본문 내용

① 첫 번째 항
  가. 첫 번째 호
  나. 두 번째 호

② 두 번째 항
  가. 첫 번째 호
  나. 두 번째 호

③ 세 번째 항
  가. 첫 번째 호
  나. 두 번째 호
"""
    for i in range(1, 11)
])

# 벤치마크
builder = TreeBuilder()
parser = HierarchicalParser()

iterations = 100
times = []

for i in range(iterations):
    start = time.time()
    
    document = builder.build(markdown, f"테스트{i}")
    validated = parser.parse(document)
    
    elapsed = time.time() - start
    times.append(elapsed)

# 결과
import statistics

print(f"🏁 Phase 5.7.0 벤치마크 결과 ({iterations}회)")
print(f"   평균: {statistics.mean(times):.3f}초")
print(f"   중앙값: {statistics.median(times):.3f}초")
print(f"   최소: {min(times):.3f}초")
print(f"   최대: {max(times):.3f}초")
print(f"   표준편차: {statistics.stdev(times):.3f}초")
```

---

## 다음 단계

### Phase 5.8.0 준비

```
✅ Phase 5.7.0 완료
   - 법령 Tree 구조화 ✅
   - Phase 5.6.3 지표 연동 ✅
   - RAG 프롬프트 생성 ✅

⏭️ Phase 5.8.0: RAG 통합
   - Embedding 인덱스 생성
   - 계층별 검색 엔진
   - LLM 응답 생성
   - 실시간 스트리밍
```

---

## 참고

- **GPT 제안**: "평문 → 법령 트리 게임"
- **안전장치**: Phase 5.6.3 Final+ 7가지 지표
- **목표**: RAG 검색 정확도 10배 향상

---

**Phase 5.7.0 완성을 축하합니다! 🎉**

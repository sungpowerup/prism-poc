# PRISM Phase 5.6.3 - 자동 진단 시스템

**버전:** 5.6.3 Final  
**날짜:** 2025-10-27  
**목표:** "고쳐놓은 게 다시 무너지지 않게 자동 지표로 조기 경보 세우기"

---

## 📋 목차

1. [개요](#개요)
2. [5가지 필수 지표](#5가지-필수-지표)
3. [DoD 기준](#dod-기준)
4. [사용 방법](#사용-방법)
5. [스모크 테스트](#스모크-테스트)
6. [결과 해석](#결과-해석)

---

## 개요

Phase 5.6.3는 GPT(미송)의 제안을 100% 반영하여 **자동 회귀 진단 시스템**을 구현합니다.

### 핵심 목표
- 번호목록 끊김 완전 제거
- 조문 경계 누수 완전 차단
- 개정/삭제 메타 동기화
- 표 환각 억제 유지
- 빈 조문 생성 방지

### 설계 원칙
1. **자동화**: 수동 검증 제거
2. **조기 경보**: 회귀 즉시 탐지
3. **DoD 기반**: 릴리스 기준 명확화
4. **스모크 테스트**: 5종 문서 자동 검증

---

## 5가지 필수 지표

### 1️⃣ Article Boundary Precision/Recall
- **목적**: 조문 경계 정확도
- **측정**: F1 Score
- **DoD 기준**: F1 ≥ 0.97

### 2️⃣ List Binding Fix Rate
- **목적**: 번호목록 결속 복구율
- **측정**: (원본 끊김 - 정규화 후 끊김) / 원본 끊김
- **DoD 기준**: ≥ 0.98

### 3️⃣ Table Confidence Precision
- **목적**: 표 환각 억제
- **측정**: False Positive (표 없는데 검출)
- **DoD 기준**: = 0

### 4️⃣ Amendment Capture Rate
- **목적**: 개정/삭제 메타 동기화
- **측정**: (동기화 성공 / 전체 청크)
- **DoD 기준**: = 1.0

### 5️⃣ Empty Article Rate
- **목적**: 빈 조문 생성 방지
- **측정**: (빈 조문 / 전체 조문)
- **DoD 기준**: = 0

---

## DoD 기준

**Definition of Done (릴리스 가능 기준)**

```python
DOD_CRITERIA = {
    'article_boundary_f1': 0.97,      # 조문 경계 F1 ≥ 0.97
    'list_binding_fix_rate': 0.98,    # 목록 결속 ≥ 0.98
    'table_false_positive': 0.0,      # 표 과검출 = 0
    'amendment_capture_rate': 1.0,    # 개정 메타 = 1.0
    'empty_article_rate': 0.0         # 빈 조문 = 0
}
```

### DoD 통과 = 릴리스 가능 ✅
### DoD 실패 = 릴리스 불가 ❌

---

## 사용 방법

### 1. 기본 사용 (단일 문서)

```python
from core.quality_metrics import QualityMetrics
from core.hybrid_extractor import HybridExtractor

# 추출
extractor = HybridExtractor()
result = extractor.extract_from_file('document.pdf')

# 메트릭 수집
metrics = QualityMetrics()
metrics.start_collection('doc_001', 'statute')

# 지표 기록
metrics.record_article_boundaries(
    detected_articles=['제1조', '제2조', '제3조'],
    ground_truth=['제1조', '제2조', '제3조']
)

metrics.record_list_binding(
    original=result['raw_content'],
    normalized=result['content']
)

metrics.record_table_detection(
    page_has_table=False,
    detected_tables=0,
    confidence=0.0
)

metrics.record_amendment_sync(result['chunks'])
metrics.record_empty_articles(result['chunks'])

# 저장 및 DoD 검증
metrics.save()
summary = metrics.get_summary()

if summary['dod_pass']:
    print("✅ DoD 통과: 릴리스 가능")
else:
    print("❌ DoD 실패: 릴리스 불가")
```

### 2. 스모크 테스트 (5종 문서)

```bash
# 테스트 실행
python tests/smoke_test_v563.py

# 결과 확인
cat metrics/smoke_test_summary.json
```

### 3. 메트릭 확인

```bash
# 개별 메트릭
cat metrics/metrics_doc_001_*.json

# 전체 요약
cat metrics/smoke_test_summary.json
```

---

## 스모크 테스트

### 테스트 세트 (5종)

| 타입 | 파일 | 목적 |
|------|------|------|
| 규정 01 | statute_sample_01.pdf | 조문·항·호 기본 |
| 규정 02 | statute_sample_02.pdf | 삭제 조문 포함 |
| 규정 03 | statute_sample_03.pdf | 긴 조문 (항/호 많음) |
| 버스/지도 | bus_diagram_sample.pdf | 도메인 가드 체크 |
| 통계/보고서 | report_sample.pdf | 표 과검출 체크 |

### 실행

```bash
# 전체 실행
python tests/smoke_test_v563.py

# 결과 예시
🧪 Phase 5.6.3 스모크 테스트 시작
📄 테스트: statute_01 (타입: statute)
   ✅ 통과
📄 테스트: statute_02 (타입: statute)
   ✅ 통과
📄 테스트: statute_03 (타입: statute)
   ✅ 통과
📄 테스트: bus_diagram_01 (타입: bus_diagram)
   ✅ 통과
📄 테스트: report_01 (타입: general)
   ✅ 통과

🏁 스모크 테스트 완료
   ✅ 통과: 5/5
   ❌ 실패: 0/5
```

---

## 결과 해석

### 메트릭 파일 구조

```json
{
  "timestamp": "2025-10-27T10:00:00",
  "doc_id": "statute_01",
  "doc_type": "statute",
  "stage_metrics": {
    "article_boundaries": {
      "f1_score": 1.0,
      "precision": 1.0,
      "recall": 1.0
    },
    "list_binding": {
      "fix_rate": 1.0,
      "original_broken_count": 10,
      "normalized_broken_count": 0
    },
    "table_detection": {
      "false_positive": 0
    },
    "amendment_sync": {
      "capture_rate": 1.0
    },
    "empty_articles": {
      "empty_rate": 0.0
    }
  },
  "quality_scores": {
    "article_boundary": 100.0,
    "list_binding": 100.0,
    "table_detection": 100.0,
    "amendment_sync": 100.0,
    "empty_articles": 100.0,
    "overall": 100.0
  },
  "regression_flags": [],
  "dod_status": {
    "article_boundary_f1": {
      "value": 1.0,
      "target": 0.97,
      "pass": true
    },
    "list_binding_fix_rate": {
      "value": 1.0,
      "target": 0.98,
      "pass": true
    },
    "table_false_positive": {
      "value": 0,
      "target": 0,
      "pass": true
    },
    "amendment_capture_rate": {
      "value": 1.0,
      "target": 1.0,
      "pass": true
    },
    "empty_article_rate": {
      "value": 0.0,
      "target": 0.0,
      "pass": true
    }
  }
}
```

### 회귀 플래그 예시

```json
"regression_flags": [
  "ARTICLE_BOUNDARY: F1=0.95 < 0.97",
  "LIST_BINDING: 8개 끊김 잔존 (목표: ≤5)"
]
```

### DoD 상태

```json
"dod_status": {
  "article_boundary_f1": {"pass": true},
  "list_binding_fix_rate": {"pass": true},
  "table_false_positive": {"pass": true},
  "amendment_capture_rate": {"pass": true},
  "empty_article_rate": {"pass": true}
}
```

---

## 다음 단계

### Phase 5.7.0 준비
- ✅ 5.6.3 DoD 통과 확인
- ⏭️ 데이터 모델 스키마 확정
- ⏭️ TreeBuilder 개발
- ⏭️ HierarchicalParser 개발
- ⏭️ LLM Adapter 개발

---

## 참고

- GPT 제안: "5.6.3: 안정화 + 자동 진단"
- 목표: "고쳐놓은 게 다시 무너지지 않게"
- DoD 기준: 릴리스 가능 여부 자동 판정

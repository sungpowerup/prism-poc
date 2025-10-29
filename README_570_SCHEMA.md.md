# PRISM Phase 5.7.0 - 법령 트리 JSON 스키마 v1.0

**버전:** 5.7.0 v1.0  
**날짜:** 2025-10-27  
**목표:** "조문·항·호를 3단 계층 트리로 구조화"

---

## 📋 목차

1. [개요](#개요)
2. [스키마 구조](#스키마-구조)
3. [필드 정의](#필드-정의)
4. [계층 구조](#계층-구조)
5. [메타데이터](#메타데이터)
6. [예시](#예시)
7. [검증 규칙](#검증-규칙)

---

## 개요

### 설계 원칙

**박준호 (AI/ML Lead):** "3단 계층 트리로 법령 구조를 완전히 표현합니다!"

1. **계층 보존**: 조문(Article) → 항(Clause) → 호(Item) 3단 구조
2. **관계 명확화**: 부모-자식 관계 명시적 표현
3. **메타데이터 풍부**: 개정일, 삭제 여부, 신설 여부 등
4. **RAG 최적화**: 계층별 검색 가능
5. **확장 가능**: 장·절·관 등 상위 계층 추가 가능

### 핵심 목표

```
Before (Flat):
제1조(목적) 이 법은 ... ① 항목1 ② 항목2 가. 세부1 나. 세부2

After (Tree):
Article(제1조)
  └─ Clause(①)
       ├─ Item(가.)
       └─ Item(나.)
  └─ Clause(②)
```

---

## 스키마 구조

### 전체 구조

```json
{
  "document": {
    "metadata": { ... },
    "tree": [ ... ]
  }
}
```

### Document 레벨

```typescript
interface Document {
  metadata: DocumentMetadata;
  tree: Article[];
}

interface DocumentMetadata {
  title: string;              // 법령명
  enacted_date?: string;      // 제정일 (YYYY.MM.DD)
  last_amended_date?: string; // 최종개정일
  law_number?: string;        // 법령번호
  source_url?: string;        // 출처 URL
  extracted_at: string;       // 추출일시 (ISO 8601)
  version: string;            // 스키마 버전 ("5.7.0")
}
```

---

## 필드 정의

### Article (조문)

**이서영 (Backend Lead):** "조문이 최상위 노드입니다!"

```typescript
interface Article {
  level: "article";
  article_no: string;         // 예: "제1조", "제2조"
  article_title?: string;     // 예: "(목적)", "(정의)"
  content: string;            // 조문 본문
  
  // 계층 관계
  children: (Clause | string)[]; // 하위 항 또는 직접 텍스트
  
  // 메타데이터
  metadata: ArticleMetadata;
  
  // 위치 정보
  position: PositionInfo;
}

interface ArticleMetadata {
  amended_dates: string[];    // 개정일 목록 ["2024.01.01", "2023.06.15"]
  is_deleted: boolean;        // 삭제된 조문 여부
  is_newly_established: boolean; // 신설 여부
  change_log: ChangeLog[];    // 변경 이력
  
  // Phase 5.6.3 지표 대응
  has_empty_content: boolean; // 빈 조문 여부 (empty_article_rate)
  has_cross_bleed: boolean;   // 경계 누수 여부 (boundary_cross_bleed_rate)
}

interface ChangeLog {
  type: "amended" | "deleted" | "newly_established";
  date: string;               // YYYY.MM.DD
  description?: string;       // 변경 내용 설명
}
```

### Clause (항)

```typescript
interface Clause {
  level: "clause";
  clause_no: string;          // 예: "①", "②", "제1항"
  content: string;            // 항 본문
  
  // 계층 관계
  parent_article_no: string;  // 부모 조문 번호
  children: (Item | string)[]; // 하위 호 또는 직접 텍스트
  
  // 메타데이터
  metadata: ClauseMetadata;
  
  // 위치 정보
  position: PositionInfo;
}

interface ClauseMetadata {
  amended_dates: string[];
  is_deleted: boolean;
}
```

### Item (호)

```typescript
interface Item {
  level: "item";
  item_no: string;            // 예: "가.", "나.", "1.", "2."
  content: string;            // 호 본문
  
  // 계층 관계
  parent_article_no: string;  // 부모 조문 번호
  parent_clause_no: string;   // 부모 항 번호
  children?: SubItem[];       // 하위 세부 항목 (선택)
  
  // 메타데이터
  metadata: ItemMetadata;
  
  // 위치 정보
  position: PositionInfo;
}

interface ItemMetadata {
  amended_dates: string[];
  is_deleted: boolean;
}
```

### SubItem (세부 항목) - 선택적

```typescript
interface SubItem {
  level: "subitem";
  subitem_no: string;         // 예: "1)", "2)", "가)", "나)"
  content: string;
  
  // 계층 관계
  parent_item_no: string;
  
  // 메타데이터
  metadata: SubItemMetadata;
}
```

### PositionInfo (위치 정보)

```typescript
interface PositionInfo {
  page_number: number;        // 원본 PDF 페이지 번호
  bbox?: BBox;                // 원본 위치 (선택)
  sequence: number;           // 문서 내 순서 (1부터 시작)
}

interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

---

## 계층 구조

### 3단 계층 예시

```
Document
  └─ Article (제1조)
       ├─ content: "이 법은 ..."
       └─ children: [
            Clause (①)
              ├─ content: "항목 내용"
              └─ children: [
                   Item (가.)
                     └─ content: "세부 내용"
                   Item (나.)
                     └─ content: "세부 내용"
              ]
            Clause (②)
              └─ content: "항목 내용"
       ]
  └─ Article (제2조)
       └─ ...
```

### 계층 보존율 검증

**정수아 (QA Lead):** "Phase 5.6.3 Final+ 지표와 연동됩니다!"

```python
# Phase 5.6.3 지표: hierarchy_preservation_rate
def verify_hierarchy(tree: Document) -> float:
    """
    계층 보존율 검증
    
    Returns:
        0.0 ~ 1.0 (1.0 = 완벽한 계층)
    """
    expected_layers = ['article', 'clause', 'item']
    detected_layers = set()
    
    for article in tree.tree:
        detected_layers.add('article')
        
        for child in article.children:
            if isinstance(child, dict) and child.get('level') == 'clause':
                detected_layers.add('clause')
                
                for item in child.get('children', []):
                    if isinstance(item, dict) and item.get('level') == 'item':
                        detected_layers.add('item')
    
    return len(detected_layers & set(expected_layers)) / len(expected_layers)
```

---

## 메타데이터

### ArticleMetadata 상세

```typescript
interface ArticleMetadata {
  // 개정 정보
  amended_dates: string[];    // ["2024.01.01", "2023.06.15"]
  is_deleted: boolean;        // 삭제 조문 (제○조 <삭제>)
  is_newly_established: boolean; // 신설 조문
  
  // 변경 이력
  change_log: ChangeLog[];    // 시간순 변경 로그
  
  // ✅ Phase 5.6.3 지표 대응
  has_empty_content: boolean; // empty_article_rate 검증용
  has_cross_bleed: boolean;   // boundary_cross_bleed_rate 검증용
  
  // RAG 최적화
  importance_score?: number;  // 0.0 ~ 1.0 (선택)
  keywords?: string[];        // 주요 키워드 (선택)
}
```

### ChangeLog 예시

```json
{
  "change_log": [
    {
      "type": "newly_established",
      "date": "2020.01.15",
      "description": "신설"
    },
    {
      "type": "amended",
      "date": "2023.06.15",
      "description": "개정"
    },
    {
      "type": "amended",
      "date": "2024.01.01",
      "description": "일부개정"
    }
  ]
}
```

---

## 예시

### 단순 조문 (항·호 없음)

```json
{
  "document": {
    "metadata": {
      "title": "샘플 규정",
      "enacted_date": "2020.01.01",
      "extracted_at": "2025-10-27T18:30:00Z",
      "version": "5.7.0"
    },
    "tree": [
      {
        "level": "article",
        "article_no": "제1조",
        "article_title": "(목적)",
        "content": "이 규정은 샘플을 위한 것이다.",
        "children": [],
        "metadata": {
          "amended_dates": ["2020.01.01"],
          "is_deleted": false,
          "is_newly_established": true,
          "change_log": [
            {
              "type": "newly_established",
              "date": "2020.01.01"
            }
          ],
          "has_empty_content": false,
          "has_cross_bleed": false
        },
        "position": {
          "page_number": 1,
          "sequence": 1
        }
      }
    ]
  }
}
```

### 복합 조문 (항·호 포함)

```json
{
  "level": "article",
  "article_no": "제2조",
  "article_title": "(정의)",
  "content": "이 규정에서 사용하는 용어의 정의는 다음과 같다.",
  "children": [
    {
      "level": "clause",
      "clause_no": "①",
      "content": "다음 각 호의 어느 하나에 해당하는 경우",
      "parent_article_no": "제2조",
      "children": [
        {
          "level": "item",
          "item_no": "가.",
          "content": "첫 번째 경우",
          "parent_article_no": "제2조",
          "parent_clause_no": "①",
          "metadata": {
            "amended_dates": ["2020.01.01"],
            "is_deleted": false
          },
          "position": {
            "page_number": 1,
            "sequence": 3
          }
        },
        {
          "level": "item",
          "item_no": "나.",
          "content": "두 번째 경우",
          "parent_article_no": "제2조",
          "parent_clause_no": "①",
          "metadata": {
            "amended_dates": ["2020.01.01"],
            "is_deleted": false
          },
          "position": {
            "page_number": 1,
            "sequence": 4
          }
        }
      ],
      "metadata": {
        "amended_dates": ["2020.01.01"],
        "is_deleted": false
      },
      "position": {
        "page_number": 1,
        "sequence": 2
      }
    },
    {
      "level": "clause",
      "clause_no": "②",
      "content": "제1항에도 불구하고 예외적으로...",
      "parent_article_no": "제2조",
      "children": [],
      "metadata": {
        "amended_dates": ["2023.06.15"],
        "is_deleted": false
      },
      "position": {
        "page_number": 1,
        "sequence": 5
      }
    }
  ],
  "metadata": {
    "amended_dates": ["2020.01.01", "2023.06.15"],
    "is_deleted": false,
    "is_newly_established": false,
    "change_log": [
      {
        "type": "newly_established",
        "date": "2020.01.01"
      },
      {
        "type": "amended",
        "date": "2023.06.15",
        "description": "제2항 신설"
      }
    ],
    "has_empty_content": false,
    "has_cross_bleed": false
  },
  "position": {
    "page_number": 1,
    "sequence": 1
  }
}
```

### 삭제 조문

```json
{
  "level": "article",
  "article_no": "제3조",
  "article_title": "",
  "content": "<삭제 2024.01.01>",
  "children": [],
  "metadata": {
    "amended_dates": ["2020.01.01", "2024.01.01"],
    "is_deleted": true,
    "is_newly_established": false,
    "change_log": [
      {
        "type": "newly_established",
        "date": "2020.01.01"
      },
      {
        "type": "deleted",
        "date": "2024.01.01",
        "description": "삭제"
      }
    ],
    "has_empty_content": true,
    "has_cross_bleed": false
  },
  "position": {
    "page_number": 1,
    "sequence": 6
  }
}
```

---

## 검증 규칙

### 필수 필드 검증

**정수아 (QA Lead):** "JSON Schema로 자동 검증합니다!"

```python
def validate_article(article: Dict) -> List[str]:
    """Article 노드 검증"""
    errors = []
    
    # 필수 필드
    if 'level' not in article or article['level'] != 'article':
        errors.append("level must be 'article'")
    
    if 'article_no' not in article:
        errors.append("article_no is required")
    
    if 'content' not in article:
        errors.append("content is required")
    
    if 'children' not in article:
        errors.append("children is required")
    
    if 'metadata' not in article:
        errors.append("metadata is required")
    
    if 'position' not in article:
        errors.append("position is required")
    
    return errors
```

### 계층 관계 검증

```python
def validate_hierarchy(tree: List[Dict]) -> List[str]:
    """계층 관계 검증"""
    errors = []
    
    for article in tree:
        article_no = article['article_no']
        
        for child in article.get('children', []):
            if isinstance(child, dict):
                if child.get('level') == 'clause':
                    # 항의 parent_article_no 검증
                    if child.get('parent_article_no') != article_no:
                        errors.append(
                            f"Clause {child.get('clause_no')} has wrong parent"
                        )
                    
                    # 호 검증
                    for item in child.get('children', []):
                        if isinstance(item, dict) and item.get('level') == 'item':
                            if item.get('parent_article_no') != article_no:
                                errors.append(
                                    f"Item {item.get('item_no')} has wrong article parent"
                                )
                            if item.get('parent_clause_no') != child.get('clause_no'):
                                errors.append(
                                    f"Item {item.get('item_no')} has wrong clause parent"
                                )
    
    return errors
```

### Phase 5.6.3 지표 검증

```python
def validate_against_dod(tree: List[Dict]) -> Dict[str, Any]:
    """DoD 기준 검증"""
    
    # 1. empty_article_rate
    total_articles = len(tree)
    empty_articles = sum(
        1 for a in tree 
        if a['metadata'].get('has_empty_content', False)
    )
    empty_rate = empty_articles / max(1, total_articles)
    
    # 2. boundary_cross_bleed_rate
    cross_bleed_articles = sum(
        1 for a in tree 
        if a['metadata'].get('has_cross_bleed', False)
    )
    cross_bleed_rate = cross_bleed_articles / max(1, total_articles)
    
    # 3. hierarchy_preservation_rate
    preservation_rate = verify_hierarchy({'tree': tree})
    
    return {
        'empty_article_rate': empty_rate,
        'boundary_cross_bleed_rate': cross_bleed_rate,
        'hierarchy_preservation_rate': preservation_rate,
        'dod_pass': (
            empty_rate == 0.0 and
            cross_bleed_rate == 0.0 and
            preservation_rate >= 0.95
        )
    }
```

---

## 다음 단계

### Step 2: TreeBuilder 개발

```python
class TreeBuilder:
    """Markdown → Tree 변환기"""
    
    def build(self, markdown: str) -> Document:
        """
        Markdown을 Tree로 변환
        
        Returns:
            Document (스키마 준수)
        """
        pass
```

### Step 3: HierarchicalParser 개발

```python
class HierarchicalParser:
    """계층 파싱 및 검증"""
    
    def parse(self, tree: Document) -> Document:
        """
        계층 구조 파싱 및 검증
        
        - 부모-자식 관계 설정
        - 경계 누수 탐지
        - 계층 보존율 계산
        """
        pass
```

### Step 4: LLM Adapter 개발

```python
class LLMAdapter:
    """Tree → RAG 프롬프트 변환"""
    
    def to_prompt(self, tree: Document, query: str) -> str:
        """
        Tree를 LLM 프롬프트로 변환
        
        - 계층별 Top-k 검색
        - 컨텍스트 생성
        """
        pass
```

---

## 참고

- **GPT 제안**: "평문 → 법령 트리 게임"
- **안전장치**: Phase 5.6.3 Final+ 7가지 지표
- **목표**: RAG 검색 정확도 10배 향상

---

**Phase 5.7.0 Step 1 완료!** 🎉

"""
tests/test_phase_570.py
PRISM Phase 5.7.0 - Complete Test Suite

테스트 범위:
1. TreeBuilder (Markdown → Tree)
2. HierarchicalParser (검증 + DoD)
3. LLMAdapter (Tree → RAG)
4. Phase 5.6.3 연동

Author: 정수아 (QA Lead)
Date: 2025-10-27
Version: 5.7.0 v1.0
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tree_builder import TreeBuilder
from core.hierarchical_parser import HierarchicalParser
from core.llm_adapter import LLMAdapter


# ==========================================
# TreeBuilder 테스트
# ==========================================

def test_tree_builder_initialization():
    """TreeBuilder 초기화 테스트"""
    builder = TreeBuilder()
    assert builder is not None


def test_tree_builder_basic_article():
    """기본 조문 파싱 테스트"""
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
    assert '샘플' in article['content']


def test_tree_builder_multiple_articles():
    """복수 조문 파싱 테스트"""
    markdown = """
### 제1조(목적)
첫 번째 조문

### 제2조(정의)
두 번째 조문

### 제3조(적용범위)
세 번째 조문
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    tree = document['document']['tree']
    assert len(tree) == 3
    
    assert tree[0]['article_no'] == '제1조'
    assert tree[1]['article_no'] == '제2조'
    assert tree[2]['article_no'] == '제3조'


def test_tree_builder_with_clauses():
    """항 포함 테스트"""
    markdown = """
### 제1조(정의)
다음과 같다.

① 첫 번째 항

② 두 번째 항

③ 세 번째 항
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    article = document['document']['tree'][0]
    
    # 항 검증
    assert len(article['children']) == 3
    
    clause1 = article['children'][0]
    assert clause1['level'] == 'clause'
    assert clause1['clause_no'] == '①'
    assert clause1['parent_article_no'] == '제1조'
    
    clause2 = article['children'][1]
    assert clause2['clause_no'] == '②'
    
    clause3 = article['children'][2]
    assert clause3['clause_no'] == '③'


def test_tree_builder_with_items():
    """호 포함 테스트"""
    markdown = """
### 제1조(정의)
다음과 같다.

① 다음 각 호의 어느 하나
  가. 첫 번째 호
  나. 두 번째 호
  다. 세 번째 호

② 제1항에도 불구하고
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    article = document['document']['tree'][0]
    clause1 = article['children'][0]
    
    # 호 검증
    assert len(clause1['children']) == 3
    
    item1 = clause1['children'][0]
    assert item1['level'] == 'item'
    assert item1['item_no'] == '가.'
    assert item1['parent_article_no'] == '제1조'
    assert item1['parent_clause_no'] == '①'
    
    item2 = clause1['children'][1]
    assert item2['item_no'] == '나.'
    
    item3 = clause1['children'][2]
    assert item3['item_no'] == '다.'


def test_tree_builder_deleted_article():
    """삭제 조문 테스트"""
    markdown = """
### 제1조(목적)
정상 조문

### 제2조
<삭제 2024.01.01>

### 제3조(정의)
정상 조문
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    tree = document['document']['tree']
    assert len(tree) == 3
    
    # 삭제 조문 검증
    deleted_article = tree[1]
    assert deleted_article['article_no'] == '제2조'
    assert deleted_article['metadata']['is_deleted'] is True
    assert deleted_article['metadata']['has_empty_content'] is True
    
    # 정상 조문
    assert tree[0]['metadata']['is_deleted'] is False
    assert tree[2]['metadata']['is_deleted'] is False


def test_tree_builder_amended_dates():
    """개정일 추출 테스트"""
    markdown = """
### 제1조(목적) [2020.01.01 제정, 2023.06.15 개정, 2024.01.01 일부개정]
이 규정은 ...
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    article = document['document']['tree'][0]
    amended_dates = article['metadata']['amended_dates']
    
    # 개정일 검증
    assert len(amended_dates) >= 1
    
    # 변경 로그 검증
    change_log = article['metadata']['change_log']
    assert len(change_log) >= 1
    assert change_log[0]['type'] == 'newly_established'


def test_tree_builder_cross_bleed_detection():
    """경계 누수 검출 테스트"""
    markdown = """
### 제1조(목적)
이 조문은 제2조를 참조한다.

### 제2조(정의)
정상 조문
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    article1 = document['document']['tree'][0]
    
    # 제1조 내부에 제2조 표식이 있음 → cross_bleed
    assert article1['metadata']['has_cross_bleed'] is True
    
    # 제2조는 정상
    article2 = document['document']['tree'][1]
    assert article2['metadata']['has_cross_bleed'] is False


# ==========================================
# HierarchicalParser 테스트
# ==========================================

def test_hierarchical_parser_initialization():
    """HierarchicalParser 초기화 테스트"""
    parser = HierarchicalParser()
    assert parser is not None


def test_hierarchical_parser_basic():
    """기본 파싱 테스트"""
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    # 메트릭 검증
    assert 'metrics' in validated['document']
    metrics = validated['document']['metrics']
    
    assert 'hierarchy_preservation_rate' in metrics
    assert 'boundary_cross_bleed_rate' in metrics
    assert 'empty_article_rate' in metrics
    assert 'dod_status' in metrics
    assert 'dod_pass' in metrics


def test_hierarchical_parser_hierarchy_preservation():
    """계층 보존율 테스트"""
    # 조·항·호 모두 포함
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
    
    metrics = validated['document']['metrics']
    
    # 계층 보존율 = 1.0 (완벽)
    assert metrics['hierarchy_preservation_rate'] == 1.0
    assert metrics['dod_status']['hierarchy_preservation_rate']['pass'] is True


def test_hierarchical_parser_missing_layer():
    """계층 누락 테스트"""
    # 조문만 있고 항·호 없음
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    
    # 계층 보존율 < 1.0 (item 누락)
    assert metrics['hierarchy_preservation_rate'] < 1.0


def test_hierarchical_parser_boundary_cross_bleed():
    """경계 누수 테스트"""
    markdown = """
### 제1조(목적)
이 조문은 제2조를 참조한다.

### 제2조(정의)
정상 조문
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    
    # 경계 누수 검출
    assert metrics['boundary_cross_bleed_rate'] > 0
    assert metrics['dod_status']['boundary_cross_bleed_rate']['pass'] is False


def test_hierarchical_parser_empty_article():
    """빈 조문 테스트"""
    markdown = """
### 제1조(목적)
정상 조문

### 제2조
<삭제 2024.01.01>
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    
    # 빈 조문율 > 0
    assert metrics['empty_article_rate'] > 0
    assert metrics['dod_status']['empty_article_rate']['pass'] is False


def test_hierarchical_parser_dod_pass():
    """DoD 통과 테스트"""
    # 완벽한 문서
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.

① 첫 번째 항
  가. 첫 번째 호
  나. 두 번째 호
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    
    # DoD 통과
    assert metrics['dod_pass'] is True


def test_hierarchical_parser_dod_fail():
    """DoD 실패 테스트"""
    # 경계 누수 + 빈 조문
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
    
    # DoD 실패
    assert metrics['dod_pass'] is False


# ==========================================
# LLMAdapter 테스트
# ==========================================

def test_llm_adapter_initialization():
    """LLMAdapter 초기화 테스트"""
    adapter = LLMAdapter()
    assert adapter is not None


def test_llm_adapter_to_prompt():
    """프롬프트 생성 테스트"""
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.

① 첫 번째 항
  가. 첫 번째 호
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
    assert '샘플' in prompt
    assert '①' in prompt
    assert '가.' in prompt


def test_llm_adapter_hierarchical_search():
    """계층별 검색 테스트"""
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
    
    # "첫 번째" 키워드 포함
    assert any('첫 번째' in r['text'] for r in results)
    
    # 레벨 확인
    levels = [r['level'] for r in results]
    assert 'item' in levels or 'clause' in levels


def test_llm_adapter_json_export():
    """JSON 내보내기 테스트"""
    markdown = """
### 제1조(목적)
샘플 조문
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "테스트 규정")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    adapter = LLMAdapter()
    json_str = adapter.to_json_export(validated)
    
    # 검증
    assert isinstance(json_str, str)
    assert '제1조' in json_str
    assert 'document' in json_str


# ==========================================
# 통합 테스트
# ==========================================

def test_phase_570_full_pipeline():
    """Phase 5.7.0 전체 파이프라인 테스트"""
    # 복잡한 문서
    markdown = """
### 제1조(목적)
이 규정은 샘플을 위한 것이다.

### 제2조(정의) [2020.01.01 제정, 2023.06.15 개정]
다음과 같다.

① 다음 각 호의 어느 하나에 해당하는 경우
  가. 첫 번째 경우
  나. 두 번째 경우
  다. 세 번째 경우

② 제1항에도 불구하고 예외적으로 인정한다.

③ 세 번째 항

### 제3조
<삭제 2024.01.01>

### 제4조(적용범위)
전체에 적용한다.
"""
    
    # Step 1: TreeBuilder
    builder = TreeBuilder()
    document = builder.build(markdown, "통합 테스트 규정", enacted_date="2020.01.01")
    
    assert 'document' in document
    assert len(document['document']['tree']) == 4
    
    # Step 2: HierarchicalParser
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    assert 'metrics' in validated['document']
    metrics = validated['document']['metrics']
    
    # 메트릭 검증
    assert metrics['hierarchy_preservation_rate'] == 1.0
    assert metrics['boundary_cross_bleed_rate'] == 0.0
    assert metrics['empty_article_rate'] > 0  # 제3조 삭제
    
    # Step 3: LLMAdapter
    adapter = LLMAdapter()
    prompt = adapter.to_prompt(validated)
    
    assert '통합 테스트 규정' in prompt
    assert '제1조' in prompt
    assert '제2조' in prompt
    assert '제4조' in prompt
    
    # 계층별 검색
    results = adapter.to_hierarchical_context(
        document=validated,
        query="첫 번째 경우",
        top_k=5
    )
    
    assert len(results) > 0
    assert any('첫 번째' in r['text'] for r in results)
    
    # JSON Export
    json_str = adapter.to_json_export(validated)
    assert '통합 테스트 규정' in json_str


def test_phase_563_integration():
    """Phase 5.6.3 Final+ 연동 테스트"""
    # 의도적 오류 케이스
    markdown = """
### 제1조(목적)
이 조문은 제2조와 제3조를 참조한다.

### 제2조(정의)
다음과 같다.

① 첫 번째 항

### 제3조
<삭제 2024.01.01>
"""
    
    builder = TreeBuilder()
    document = builder.build(markdown, "Phase 5.6.3 연동 테스트")
    
    parser = HierarchicalParser()
    validated = parser.parse(document)
    
    metrics = validated['document']['metrics']
    dod_status = metrics['dod_status']
    
    # Phase 5.6.3 Final+ 지표 검증
    
    # 1. 계층 보존율 (조·항만 있음, 호 없음)
    assert metrics['hierarchy_preservation_rate'] < 1.0
    assert not dod_status['hierarchy_preservation_rate']['pass']
    
    # 2. 경계 누수 (제1조에 제2조, 제3조 혼입)
    assert metrics['boundary_cross_bleed_rate'] > 0
    assert not dod_status['boundary_cross_bleed_rate']['pass']
    
    # 3. 빈 조문 (제3조 삭제)
    assert metrics['empty_article_rate'] > 0
    assert not dod_status['empty_article_rate']['pass']
    
    # DoD 실패
    assert not metrics['dod_pass']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

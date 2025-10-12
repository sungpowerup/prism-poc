"""
PRISM Phase 2.1 - Chunking Quality Tests

청킹 품질 자동 검증 테스트

Author: 정수아 (QA Lead)
Date: 2025-10-13
"""

import sys
import json
from pathlib import Path


def load_chunks(json_path: str):
    """청크 파일 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def test_table_preservation(data):
    """
    테스트 1: 표가 독립 청크로 유지되는가?
    
    기대:
    - table_chunks > 0
    - 각 표 청크는 type="table"
    """
    print("\n🧪 Test 1: Table Preservation")
    print("-" * 60)
    
    stats = data.get("statistics", {})
    table_chunks = stats.get("table_chunks", 0)
    
    if table_chunks == 0:
        print("❌ FAIL: No table chunks found")
        print("   Expected: At least 1 table chunk")
        print("   Actual: 0")
        return False
    
    # 실제 표 청크 확인
    chunks = data.get("chunks", [])
    actual_table_chunks = [c for c in chunks if c.get("type") == "table"]
    
    if len(actual_table_chunks) != table_chunks:
        print(f"❌ FAIL: Mismatch between stats and actual chunks")
        print(f"   Stats: {table_chunks}")
        print(f"   Actual: {len(actual_table_chunks)}")
        return False
    
    print(f"✅ PASS: Found {table_chunks} table chunk(s)")
    
    # 표 청크 내용 검증
    for i, chunk in enumerate(actual_table_chunks):
        content = chunk.get("content", "")
        
        # Markdown 표 형식인가?
        if "|" not in content or "---" not in content:
            print(f"⚠️  WARNING: Table chunk {i+1} may not be in Markdown format")
        else:
            print(f"   ✓ Table {i+1}: Valid Markdown format")
    
    return True


def test_sentence_completeness(data):
    """
    테스트 2: 문장이 중간에 끊기지 않는가?
    
    기대:
    - 청크가 불완전한 문장으로 끝나지 않음
    - "다, ", "며, ", "고, " 등으로 끝나지 않음
    """
    print("\n🧪 Test 2: Sentence Completeness")
    print("-" * 60)
    
    chunks = data.get("chunks", [])
    text_chunks = [c for c in chunks if c.get("type") == "text"]
    
    if not text_chunks:
        print("⚠️  SKIP: No text chunks to test")
        return True
    
    incomplete_endings = ["다, ", "며, ", "고, ", "을, ", "를, ", "의, ", "에, "]
    problematic_chunks = []
    
    for chunk in text_chunks:
        content = chunk.get("content", "")
        
        for ending in incomplete_endings:
            if content.rstrip().endswith(ending):
                problematic_chunks.append({
                    "chunk_id": chunk.get("chunk_id"),
                    "ending": ending,
                    "preview": content[-50:]
                })
                break
    
    if problematic_chunks:
        print(f"❌ FAIL: Found {len(problematic_chunks)} incomplete chunks")
        for prob in problematic_chunks[:3]:  # 최대 3개만 출력
            print(f"   • {prob['chunk_id']}: ends with '{prob['ending']}'")
            print(f"     Preview: ...{prob['preview']}")
        return False
    
    print(f"✅ PASS: All {len(text_chunks)} text chunks are complete")
    return True


def test_chunk_size_consistency(data):
    """
    테스트 3: 청크 크기가 일관적인가?
    
    기대:
    - 대부분의 청크가 목표 크기 범위 내
    - 표 청크는 예외 (크기 무관)
    """
    print("\n🧪 Test 3: Chunk Size Consistency")
    print("-" * 60)
    
    chunks = data.get("chunks", [])
    text_chunks = [c for c in chunks if c.get("type") == "text"]
    
    if not text_chunks:
        print("⚠️  SKIP: No text chunks to test")
        return True
    
    target_size = 512  # 기본 목표
    min_size = target_size * 0.5  # 최소 50%
    max_size = target_size * 1.5  # 최대 150%
    
    sizes = []
    out_of_range = []
    
    for chunk in text_chunks:
        metadata = chunk.get("metadata", {})
        token_count = metadata.get("token_count", 0)
        
        sizes.append(token_count)
        
        if token_count < min_size or token_count > max_size:
            out_of_range.append({
                "chunk_id": chunk.get("chunk_id"),
                "size": token_count
            })
    
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    
    print(f"   Target: {target_size} tokens")
    print(f"   Range: {min_size:.0f} - {max_size:.0f} tokens")
    print(f"   Actual avg: {avg_size:.0f} tokens")
    
    if len(out_of_range) > len(text_chunks) * 0.2:
        # 20% 이상이 범위를 벗어나면 실패
        print(f"❌ FAIL: {len(out_of_range)} chunks out of range (>{20}%)")
        for chunk in out_of_range[:3]:
            print(f"   • {chunk['chunk_id']}: {chunk['size']} tokens")
        return False
    
    print(f"✅ PASS: {len(text_chunks) - len(out_of_range)}/{len(text_chunks)} chunks in range")
    return True


def test_table_structure(data):
    """
    테스트 4: 표 구조가 올바른가?
    
    기대:
    - Markdown 형식
    - 헤더 행 존재
    - 구분선 존재
    """
    print("\n🧪 Test 4: Table Structure")
    print("-" * 60)
    
    chunks = data.get("chunks", [])
    table_chunks = [c for c in chunks if c.get("type") == "table"]
    
    if not table_chunks:
        print("⚠️  SKIP: No table chunks to test")
        return True
    
    valid_tables = 0
    
    for chunk in table_chunks:
        content = chunk.get("content", "")
        chunk_id = chunk.get("chunk_id", "unknown")
        
        # Markdown 표 검증
        lines = content.strip().split('\n')
        
        # 최소 3줄 (헤더 + 구분선 + 데이터)
        if len(lines) < 3:
            print(f"⚠️  WARNING: {chunk_id} has too few lines ({len(lines)})")
            continue
        
        # 구분선 확인
        has_separator = any("---" in line for line in lines)
        if not has_separator:
            print(f"⚠️  WARNING: {chunk_id} missing separator line")
            continue
        
        # 모든 행이 '|'를 포함하는가
        all_have_pipe = all("|" in line for line in lines)
        if not all_have_pipe:
            print(f"⚠️  WARNING: {chunk_id} has lines without '|'")
            continue
        
        valid_tables += 1
        
        # 메타데이터 출력
        metadata = chunk.get("metadata", {})
        rows = metadata.get("rows", "?")
        cols = metadata.get("columns", "?")
        print(f"   ✓ {chunk_id}: {rows}x{cols} table")
    
    if valid_tables == len(table_chunks):
        print(f"✅ PASS: All {valid_tables} tables have valid structure")
        return True
    else:
        print(f"⚠️  PARTIAL: {valid_tables}/{len(table_chunks)} tables are valid")
        return valid_tables > 0


def test_no_content_loss(data):
    """
    테스트 5: 내용 손실이 없는가?
    
    기대:
    - 모든 청크에 내용이 있음
    - 빈 청크 없음
    """
    print("\n🧪 Test 5: No Content Loss")
    print("-" * 60)
    
    chunks = data.get("chunks", [])
    
    if not chunks:
        print("❌ FAIL: No chunks generated")
        return False
    
    empty_chunks = [c for c in chunks if not c.get("content", "").strip()]
    
    if empty_chunks:
        print(f"❌ FAIL: Found {len(empty_chunks)} empty chunks")
        for chunk in empty_chunks[:3]:
            print(f"   • {chunk.get('chunk_id', 'unknown')}")
        return False
    
    print(f"✅ PASS: All {len(chunks)} chunks have content")
    return True


def run_all_tests(json_path: str):
    """모든 테스트 실행"""
    print("=" * 60)
    print("PRISM Chunking Quality Tests")
    print("=" * 60)
    print(f"File: {json_path}")
    
    try:
        data = load_chunks(json_path)
    except FileNotFoundError:
        print(f"\n❌ ERROR: File not found: {json_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"\n❌ ERROR: Invalid JSON: {e}")
        return False
    
    # 통계 출력
    stats = data.get("statistics", {})
    print("\n📊 Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 테스트 실행
    tests = [
        test_table_preservation,
        test_sentence_completeness,
        test_chunk_size_consistency,
        test_table_structure,
        test_no_content_loss
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func(data)
            results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR in {test_func.__name__}: {e}")
            results.append(False)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All tests passed! Chunking quality is excellent.")
        return True
    elif passed >= total * 0.8:
        print(f"\n⚠️  {total - passed} test(s) failed, but chunking quality is acceptable.")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed. Chunking quality needs improvement.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_chunking_quality.py <chunks.json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    success = run_all_tests(json_path)
    
    sys.exit(0 if success else 1)
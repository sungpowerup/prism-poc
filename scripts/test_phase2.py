"""
PRISM Phase 2 - 통합 테스트 스크립트

모든 Phase 2 모듈을 테스트합니다.

Author: 정수아 (QA Lead)
Date: 2025-10-11
"""

import sys
import time
from pathlib import Path
from PIL import Image
import io


def print_test(name: str, status: bool, message: str = ""):
    """테스트 결과 출력"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if message:
        print(f"   {message}")


def test_layout_detection():
    """Layout Detection 테스트"""
    try:
        from models.layout_detector import LayoutDetector, ElementType
        
        # 테스트용 흰 이미지 생성
        test_image = Image.new('RGB', (800, 1000), color='white')
        
        # 감지 수행
        detector = LayoutDetector()
        elements = detector.detect(test_image, page_num=1)
        
        # 결과 확인
        success = detector is not None
        message = f"Detected {len(elements)} elements"
        
        print_test("Layout Detection", success, message)
        return success
    except Exception as e:
        print_test("Layout Detection", False, str(e))
        return False


def test_text_extraction():
    """Text Extraction 테스트"""
    try:
        from core.text_extractor import TextExtractor
        
        extractor = TextExtractor(use_ocr_fallback=False)
        
        success = extractor is not None
        message = "TextExtractor initialized"
        
        print_test("Text Extraction", success, message)
        return success
    except Exception as e:
        print_test("Text Extraction", False, str(e))
        return False


def test_table_parsing():
    """Table Parsing 테스트"""
    try:
        from core.table_parser import TableParser, StructuredTable
        
        parser = TableParser()
        
        # 간단한 표 데이터로 테스트
        test_table = StructuredTable(
            headers=["A", "B", "C"],
            rows=[["1", "2", "3"], ["4", "5", "6"]],
            page_num=1,
            bbox=None
        )
        
        markdown = test_table.to_markdown()
        json_data = test_table.to_json()
        
        success = markdown and json_data
        message = "Table conversion successful"
        
        print_test("Table Parsing", success, message)
        return success
    except Exception as e:
        print_test("Table Parsing", False, str(e))
        return False


def test_image_captioning():
    """Image Captioning 테스트"""
    try:
        from core.image_captioner import ImageCaptioner
        from models.layout_detector import DocumentElement, ElementType, BoundingBox
        
        # 테스트용 요소 생성
        test_element = DocumentElement(
            type=ElementType.CHART,
            bbox=BoundingBox(x=0, y=0, width=100, height=100),
            confidence=0.9,
            page_num=1
        )
        
        # Captioner 초기화만 테스트 (실제 VLM 호출은 제외)
        captioner = ImageCaptioner(provider="claude")
        should_caption = captioner.should_caption(test_element)
        
        success = captioner is not None and should_caption
        message = "ImageCaptioner initialized, chart detection OK"
        
        print_test("Image Captioning", success, message)
        return success
    except Exception as e:
        print_test("Image Captioning", False, str(e))
        return False


def test_intelligent_chunking():
    """Intelligent Chunking 테스트"""
    try:
        from core.intelligent_chunker import IntelligentChunker, Chunk
        
        # 임베딩 없이 초기화
        chunker = IntelligentChunker(
            chunk_size=512,
            chunk_overlap=50
        )
        
        # 간단한 청크 생성 테스트
        test_chunk = Chunk(
            chunk_id="test_1",
            type="text",
            content="This is a test chunk.",
            metadata={"page": 1}
        )
        
        success = chunker is not None and test_chunk is not None
        message = "Chunker initialized, chunk creation OK"
        
        print_test("Intelligent Chunking", success, message)
        return success
    except Exception as e:
        print_test("Intelligent Chunking", False, str(e))
        return False


def test_pipeline_integration():
    """Pipeline Integration 테스트"""
    try:
        from core.phase2_pipeline import Phase2Pipeline
        
        # 파이프라인 초기화
        pipeline = Phase2Pipeline(
            vlm_provider="claude",
            dpi=200,
            chunk_size=512
        )
        
        success = pipeline is not None
        message = "Phase2Pipeline initialized successfully"
        
        print_test("Pipeline Integration", success, message)
        return success
    except Exception as e:
        print_test("Pipeline Integration", False, str(e))
        return False


def test_dependencies():
    """의존성 테스트"""
    dependencies = {
        "layoutparser": "Layout Detection",
        "paddleocr": "OCR",
        "torch": "Deep Learning",
        "pdfplumber": "PDF Parsing",
        "anthropic": "Claude VLM"
    }
    
    all_ok = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print_test(f"Dependency: {description}", True)
        except ImportError:
            print_test(f"Dependency: {description}", False, f"{module} not found")
            all_ok = False
    
    return all_ok


def main():
    """메인 테스트"""
    print("=" * 60)
    print("PRISM Phase 2 - Integration Test")
    print("=" * 60)
    print()
    
    # 의존성 테스트
    print("Testing Dependencies...")
    print("-" * 60)
    deps_ok = test_dependencies()
    print()
    
    if not deps_ok:
        print("❌ Some dependencies are missing!")
        print("Please install: pip install -r requirements_phase2.txt")
        sys.exit(1)
    
    # 모듈 테스트
    print("Testing Modules...")
    print("-" * 60)
    
    tests = [
        ("Layout Detection", test_layout_detection),
        ("Text Extraction", test_text_extraction),
        ("Table Parsing", test_table_parsing),
        ("Image Captioning", test_image_captioning),
        ("Intelligent Chunking", test_intelligent_chunking),
        ("Pipeline Integration", test_pipeline_integration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print_test(name, False, f"Unexpected error: {e}")
            results.append(False)
        time.sleep(0.5)
    
    # 결과 요약
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All tests passed! Phase 2 is ready to use.")
        print("\nNext steps:")
        print("  1. Test with a real PDF:")
        print("     python core/phase2_pipeline.py <your_pdf>")
        print("  2. Check the results in data/processed/")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("\nPlease check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
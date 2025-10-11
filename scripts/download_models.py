"""
PRISM Phase 2 - 모델 다운로드 스크립트

필요한 모든 AI 모델을 자동으로 다운로드합니다.

Author: 황태민 (DevOps Lead)
Date: 2025-10-11
"""

import sys
import time
from pathlib import Path


def print_step(step: int, total: int, message: str):
    """진행 상황 출력"""
    print(f"\n[{step}/{total}] {message}")
    print("-" * 60)


def download_layout_model():
    """Layout Detection 모델 다운로드"""
    print("Downloading LayoutParser model...")
    print("Model: PubLayNet (Faster R-CNN R50-FPN 3x)")
    print("Size: ~500MB")
    
    try:
        import layoutparser as lp
        
        model = lp.Detectron2LayoutModel(
            'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config'
        )
        print("✅ Layout model downloaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to download layout model: {e}")
        return False


def download_sentence_transformer():
    """Sentence Transformer 모델 다운로드 (Phase 3용, 지금은 스킵)"""
    print("⏭️  Skipping Sentence Transformer (not needed for Phase 2)")
    print("Note: Will be downloaded in Phase 3 when needed")
    return True


def download_paddleocr_models():
    """PaddleOCR 모델 다운로드"""
    print("Downloading PaddleOCR models...")
    print("Models: Detection + Recognition + Angle Classifier")
    print("Size: ~100MB")
    
    try:
        from paddleocr import PaddleOCR
        
        # 첫 실행 시 자동으로 모델 다운로드됨
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='korean',
            show_log=False
        )
        print("✅ PaddleOCR models downloaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to download PaddleOCR models: {e}")
        return False


def verify_installation():
    """설치 검증"""
    print("Verifying installation...")
    
    checks = {
        "layoutparser": False,
        "paddleocr": False,
        "torch": False,
        "torchvision": False
    }
    
    # 패키지 확인
    try:
        import layoutparser
        checks["layoutparser"] = True
    except ImportError:
        pass
    
    try:
        import paddleocr
        checks["paddleocr"] = True
    except ImportError:
        pass
    
    try:
        import torch
        checks["torch"] = True
    except ImportError:
        pass
    
    try:
        import torchvision
        checks["torchvision"] = True
    except ImportError:
        pass
    
    # 결과 출력
    print("\nInstallation Status:")
    all_ok = True
    for package, installed in checks.items():
        status = "✅" if installed else "❌"
        print(f"  {status} {package}")
        if not installed:
            all_ok = False
    
    return all_ok


def main():
    """메인 함수"""
    print("=" * 60)
    print("PRISM Phase 2 - Model Download Script")
    print("=" * 60)
    
    # 설치 확인
    print_step(1, 4, "Verifying installation")
    if not verify_installation():
        print("\n❌ Some packages are missing!")
        print("Please install dependencies first:")
        print("  pip install -r requirements_phase2.txt")
        sys.exit(1)
    
    # 모델 다운로드
    results = []
    
    print_step(2, 4, "Downloading Layout Detection model")
    results.append(download_layout_model())
    time.sleep(1)
    
    print_step(3, 4, "Checking Sentence Transformer (Phase 3)")
    results.append(download_sentence_transformer())
    time.sleep(1)
    
    print_step(4, 4, "Downloading PaddleOCR models")
    results.append(download_paddleocr_models())
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"✅ All models downloaded successfully ({success_count}/{total_count})")
        print("\nYou can now run Phase 2 pipeline:")
        print("  python core/phase2_pipeline.py <pdf_path>")
    else:
        print(f"⚠️  {success_count}/{total_count} models downloaded")
        print("\nSome models failed to download.")
        print("Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
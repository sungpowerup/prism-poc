"""
PRISM Phase 2.7 - Layout Detector (간단한 폴백 버전)
VLM 호출 대신 전체 페이지를 TEXT로 처리

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
Fix: VLM 대신 전체 페이지 폴백 전략 사용
"""

import os
from typing import List, Tuple
from PIL import Image
from dataclasses import dataclass


@dataclass
class Region:
    """문서 영역 정보"""
    type: str  # 'text', 'table', 'chart', 'image'
    bbox: Tuple[int, int, int, int]  # (left, top, right, bottom)
    confidence: float
    description: str


class LayoutDetector:
    """
    간단한 Layout Detector (폴백 전략)
    
    VLM 호출 없이 전체 페이지를 하나의 TEXT 영역으로 처리
    추후 VLM 기반 레이아웃 감지로 업그레이드 가능
    """
    
    def __init__(self, vlm_provider: str = 'claude'):
        """
        초기화
        
        Args:
            vlm_provider: VLM 프로바이더 (현재 미사용)
        """
        self.vlm_provider = vlm_provider
        print(f"✅ LayoutDetector initialized (Fallback mode: Full page as TEXT)")
    
    def detect_regions(self, page_image: Image.Image) -> List[Region]:
        """
        페이지 이미지에서 영역 감지
        
        현재 전략: 전체 페이지를 하나의 TEXT 영역으로 반환
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            Region 리스트 (1개: 전체 페이지)
        """
        width, height = page_image.size
        
        # 전체 페이지를 하나의 TEXT 영역으로
        region = Region(
            type='text',
            bbox=(0, 0, width, height),
            confidence=1.0,
            description='Full page content'
        )
        
        return [region]


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Layout Detector Test (Fallback)")
    print("="*60 + "\n")
    
    detector = LayoutDetector()
    
    # 테스트 이미지
    test_image = Image.new('RGB', (800, 1000), color='white')
    regions = detector.detect_regions(test_image)
    
    print(f"✅ Detected {len(regions)} region(s)")
    for i, region in enumerate(regions, 1):
        print(f"   Region {i}: {region.type} - {region.description}")
        print(f"   Bbox: {region.bbox}")
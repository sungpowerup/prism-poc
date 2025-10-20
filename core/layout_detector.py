"""
PRISM Phase 2.7 - Layout Detector
VLM 기반 문서 레이아웃 분석 및 영역 분류

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
"""

import os
import base64
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from PIL import Image
from anthropic import Anthropic
from dataclasses import dataclass


@dataclass
class Region:
    """문서 영역 정보"""
    type: str  # 'text', 'table', 'chart', 'image'
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    description: str


class LayoutDetector:
    """
    VLM 기반 문서 레이아웃 감지기
    
    역할:
    1. 문서 페이지에서 영역(Region) 탐지
    2. 각 영역의 타입 분류 (text/table/chart/image)
    3. 바운딩 박스 추출
    """
    
    def __init__(self):
        """초기화"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=api_key) if api_key else None
        
        if self.client:
            print("✅ LayoutDetector initialized with Claude API")
        else:
            print("⚠️  Claude API key not found - LayoutDetector disabled")
    
    def detect(self, page_image: Image.Image) -> List[Region]:
        """
        페이지 이미지에서 레이아웃 영역 탐지
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            Region 객체 리스트
        """
        if not self.client:
            print("❌ Layout detection skipped - No API client")
            return []
        
        try:
            # 이미지를 base64로 인코딩
            image_base64 = self._encode_image(page_image)
            
            # VLM으로 레이아웃 분석
            print("🔍 Analyzing page layout with VLM...")
            response = self._call_vlm_for_layout(image_base64)
            
            # 응답 파싱
            regions = self._parse_layout_response(response, page_image.size)
            
            print(f"✅ Detected {len(regions)} regions")
            for i, region in enumerate(regions, 1):
                print(f"   Region {i}: {region.type} (confidence: {region.confidence:.2f})")
            
            return regions
            
        except Exception as e:
            print(f"❌ Layout detection error: {str(e)}")
            return []
    
    def _encode_image(self, image: Image.Image) -> str:
        """이미지를 base64 인코딩"""
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _call_vlm_for_layout(self, image_base64: str) -> str:
        """
        VLM API 호출 - 레이아웃 분석
        
        CRITICAL: VLM은 "설명"이 아닌 "구조 분석"만 수행
        """
        
        prompt = """You are a document layout analyzer. Analyze this page and identify all distinct regions.

**Task:** Detect and classify all regions in this document page.

**Region Types:**
- TEXT: Pure text blocks, paragraphs, headings
- TABLE: Tabular data with rows and columns
- CHART: Charts, graphs, plots (bar, pie, line, etc.)
- IMAGE: Photos, diagrams, illustrations

**Output Format (JSON):**
```json
{
  "regions": [
    {
      "type": "TEXT|TABLE|CHART|IMAGE",
      "description": "Brief description (e.g., 'Section heading', 'Gender distribution pie chart')",
      "confidence": 0.0-1.0
    }
  ]
}
```

**Rules:**
1. Identify ALL distinct regions (don't merge related content)
2. Classify each region accurately
3. Provide brief, factual descriptions
4. Assign confidence scores
5. Return ONLY valid JSON

Analyze the page now:"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"❌ VLM API call failed: {str(e)}")
            raise
    
    def _parse_layout_response(self, response: str, image_size: Tuple[int, int]) -> List[Region]:
        """
        VLM 응답을 파싱하여 Region 리스트 생성
        
        Note: VLM은 바운딩 박스를 직접 제공하지 않으므로
              전체 페이지를 균등 분할하여 근사값 사용
        """
        import json
        import re
        
        regions = []
        
        try:
            # JSON 추출
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # JSON 마커 없이 직접 파싱 시도
                data = json.loads(response)
            
            # Region 생성
            region_list = data.get('regions', [])
            width, height = image_size
            
            # 간단한 분할 전략: 영역을 세로로 균등 분할
            num_regions = len(region_list)
            if num_regions > 0:
                region_height = height // num_regions
                
                for i, region_data in enumerate(region_list):
                    y1 = i * region_height
                    y2 = (i + 1) * region_height if i < num_regions - 1 else height
                    
                    region = Region(
                        type=region_data.get('type', 'TEXT').lower(),
                        bbox=(0, y1, width, y2),
                        confidence=region_data.get('confidence', 0.9),
                        description=region_data.get('description', '')
                    )
                    regions.append(region)
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {str(e)}")
            print(f"Response: {response[:200]}...")
            
            # 폴백: 전체 페이지를 하나의 TEXT 영역으로
            regions.append(Region(
                type='text',
                bbox=(0, 0, image_size[0], image_size[1]),
                confidence=0.5,
                description='Full page (fallback)'
            ))
        
        return regions
    
    def crop_region(self, page_image: Image.Image, region: Region) -> Image.Image:
        """Region을 기준으로 이미지 자르기"""
        return page_image.crop(region.bbox)


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Layout Detector Test")
    print("="*60 + "\n")
    
    detector = LayoutDetector()
    
    if detector.client:
        print("✅ Ready to detect layouts!")
    else:
        print("❌ Claude API not available")
"""
PRISM Phase 2.7 - Layout Detector
VLM 기반 문서 레이아웃 분석 및 영역 분류

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
"""

import os
import base64
import json
import re
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from PIL import Image
from dataclasses import dataclass


# VLM Provider 임포트는 필요할 때만
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


@dataclass
class Region:
    """문서 영역 정보"""
    type: str  # 'text', 'table', 'chart', 'image'
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
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
    
    def __init__(self, vlm_provider: str = 'claude'):
        """
        초기화
        
        Args:
            vlm_provider: VLM 프로바이더 ('claude', 'azure_openai', 'ollama')
        """
        self.vlm_provider = vlm_provider
        self.client = None
        
        # Provider별 클라이언트 초기화
        if vlm_provider == 'claude':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key and Anthropic:
                self.client = Anthropic(api_key=api_key)
                print("✅ LayoutDetector initialized with Claude API")
            else:
                print("⚠️  Claude API key not found - LayoutDetector disabled")
        
        elif vlm_provider == 'azure_openai':
            # Azure OpenAI는 레이아웃 감지가 제한적이므로 비활성화
            print("⚠️  Azure OpenAI doesn't support layout detection - disabled")
        
        elif vlm_provider == 'ollama':
            # Ollama는 로컬 VLM이므로 레이아웃 감지가 제한적
            print("⚠️  Ollama layout detection limited - disabled")
        
        else:
            print(f"⚠️  Unknown VLM provider: {vlm_provider} - LayoutDetector disabled")
    
    def detect_regions(self, page_image: Image.Image) -> List[Region]:
        """
        페이지 이미지에서 레이아웃 영역 탐지
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            Region 객체 리스트
        """
        if not self.client:
            print("❌ Layout detection skipped - No API client")
            # 폴백: 전체 페이지를 하나의 TEXT 영역으로
            print("   ⚠️  No regions detected, treating whole page as text")
            return [Region(
                type='text',
                bbox=(0, 0, page_image.width, page_image.height),
                confidence=0.5,
                description='Full page'
            )]
        
        try:
            # 이미지를 base64로 인코딩
            image_base64 = self._encode_image(page_image)
            
            # VLM으로 레이아웃 분석
            print("🔍 Analyzing page layout with VLM...")
            response = self._call_vlm_for_layout(image_base64)
            
            # 응답 파싱
            regions = self._parse_layout_response(response, page_image.size)
            
            if not regions:
                # 파싱 실패 시 폴백
                print("   ⚠️  No regions detected, treating whole page as text")
                return [Region(
                    type='text',
                    bbox=(0, 0, page_image.width, page_image.height),
                    confidence=0.5,
                    description='Full page'
                )]
            
            print(f"✅ Detected {len(regions)} regions")
            for i, region in enumerate(regions, 1):
                print(f"   Region {i}: {region.type} - {region.description}")
            
            return regions
            
        except Exception as e:
            print(f"❌ Layout detection error: {str(e)}")
            # 에러 발생 시 폴백
            return [Region(
                type='text',
                bbox=(0, 0, page_image.width, page_image.height),
                confidence=0.5,
                description='Full page'
            )]
    
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
- IMAGE: Photos, illustrations, diagrams

**Output Format (JSON):**
```json
{
  "regions": [
    {
      "type": "TEXT|TABLE|CHART|IMAGE",
      "description": "Brief description (e.g., 'Introduction paragraph', 'Sales data table')",
      "confidence": 0.0-1.0
    }
  ]
}
```

**Rules:**
1. Identify DISTINCT regions only
2. Do NOT describe content - just identify structure
3. Order regions top-to-bottom
4. Minimum 1 region, maximum 10 regions

Analyze now:"""

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
            
            return message.content[0].text.strip()
            
        except Exception as e:
            print(f"❌ VLM API call failed: {str(e)}")
            raise
    
    def _parse_layout_response(self, response: str, image_size: Tuple[int, int]) -> List[Region]:
        """VLM 응답을 Region 객체로 파싱"""
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
                    y = i * region_height
                    h = region_height if i < num_regions - 1 else (height - y)
                    
                    region = Region(
                        type=region_data.get('type', 'TEXT').lower(),
                        bbox=(0, y, width, h),
                        confidence=region_data.get('confidence', 0.9),
                        description=region_data.get('description', '')
                    )
                    regions.append(region)
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {str(e)}")
            print(f"Response preview: {response[:200]}...")
        
        except Exception as e:
            print(f"⚠️  Response parsing error: {str(e)}")
        
        return regions


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - Layout Detector Test")
    print("="*60 + "\n")
    
    detector = LayoutDetector(vlm_provider='claude')
    
    if detector.client:
        print("✅ Ready to detect layouts!")
    else:
        print("❌ Claude API not available")
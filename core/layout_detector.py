"""
PRISM Phase 2.7 - Layout Detector
VLM 기반 문서 레이아웃 분석 및 영역 분류

Author: 박준호 (AI/ML Lead)
Date: 2025-10-20
Fixed: Anthropic client initialization (proxies 제거)
"""

import os
import base64
import json
import re
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from PIL import Image
from dataclasses import dataclass


# VLM Provider 임포트
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
                try:
                    # ✅ 수정: proxies 파라미터 완전 제거
                    self.client = Anthropic(api_key=api_key)
                    print("✅ LayoutDetector initialized with Claude API")
                except Exception as e:
                    print(f"❌ Claude API initialization failed: {e}")
                    self.client = None
            else:
                print("⚠️  Claude API key not found - LayoutDetector disabled")
        
        elif vlm_provider == 'azure_openai':
            print("⚠️  Azure OpenAI doesn't support layout detection - disabled")
        
        elif vlm_provider == 'ollama':
            print("⚠️  Ollama layout detection limited - disabled")
        
        else:
            print(f"⚠️  Unknown VLM provider: {vlm_provider} - LayoutDetector disabled")
    
    def detect_regions(self, page_image: Image.Image) -> List[Region]:
        """
        페이지 이미지에서 영역 감지
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            Region 리스트
        """
        if not self.client:
            print("⚠️  VLM client not available, using fallback strategy")
            return self._fallback_detection(page_image)
        
        try:
            # 이미지를 base64로 인코딩
            buffered = BytesIO()
            page_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # VLM API 호출
            response_text = self._call_vlm(img_base64, page_image.size)
            
            # 응답 파싱
            regions = self._parse_response(response_text, page_image.size)
            
            return regions
            
        except Exception as e:
            print(f"⚠️  VLM detection failed: {str(e)}, using fallback")
            return self._fallback_detection(page_image)
    
    def _call_vlm(self, img_base64: str, image_size: Tuple[int, int]) -> str:
        """
        VLM API 호출 (Claude)
        
        Args:
            img_base64: base64 인코딩된 이미지
            image_size: (width, height)
            
        Returns:
            VLM 응답 텍스트
        """
        width, height = image_size
        
        prompt = f"""이 문서 페이지를 분석하여 다음 정보를 JSON 형식으로 추출해주세요:

1. 페이지에 있는 모든 영역(region)을 찾으세요
2. 각 영역의 타입을 분류하세요: TEXT, TABLE, CHART, IMAGE
3. 각 영역의 위치와 크기를 추정하세요 (이미지 크기: {width}x{height})

응답 형식 (JSON):
{{
  "regions": [
    {{
      "type": "TEXT" or "TABLE" or "CHART" or "IMAGE",
      "confidence": 0.0-1.0,
      "description": "영역 설명"
    }}
  ]
}}

주의사항:
- 영역을 위에서 아래로 나열하세요 (읽기 순서)
- 각 영역은 명확히 구분되어야 합니다
- 차트나 표는 반드시 식별해주세요"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # 응답 텍스트 추출
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return ""
                
        except Exception as e:
            print(f"⚠️  VLM API call failed: {str(e)}")
            raise
    
    def _parse_response(self, response: str, image_size: Tuple[int, int]) -> List[Region]:
        """
        VLM 응답 파싱
        
        Args:
            response: VLM 응답 텍스트
            image_size: (width, height)
            
        Returns:
            Region 리스트
        """
        regions = []
        
        try:
            # JSON 추출 (마크다운 코드 블록 고려)
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
    
    def _fallback_detection(self, page_image: Image.Image) -> List[Region]:
        """
        VLM이 없을 때 폴백 전략: 전체 페이지를 하나의 TEXT 영역으로 처리
        
        Args:
            page_image: PIL Image 객체
            
        Returns:
            Region 리스트 (1개)
        """
        width, height = page_image.size
        
        return [
            Region(
                type='text',
                bbox=(0, 0, width, height),
                confidence=1.0,
                description='Full page content'
            )
        ]


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
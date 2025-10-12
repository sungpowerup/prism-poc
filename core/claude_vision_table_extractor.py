"""
PRISM Phase 2.2 - Claude Vision Table Extractor (dotenv 지원)

.env 파일에서 자동으로 API 키를 읽습니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

import os
import base64
from typing import List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import io

# ✅ .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일에서 환경변수 로드
    print("✅ .env file loaded")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")

import anthropic


@dataclass
class ExtractedTable:
    """추출된 표"""
    markdown: str
    description: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    confidence: float = 0.95
    
    def to_dict(self):
        return {
            "markdown": self.markdown,
            "description": self.description,
            "page_num": self.page_num,
            "bbox": self.bbox,
            "confidence": self.confidence
        }


class ClaudeVisionTableExtractor:
    """
    Claude Vision API를 사용한 표 추출기
    
    .env 파일 또는 환경변수에서 ANTHROPIC_API_KEY를 자동으로 읽습니다.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API 키 (없으면 .env 또는 환경변수에서 읽음)
        """
        # API 키 우선순위: 파라미터 > 환경변수 > .env
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("❌ ANTHROPIC_API_KEY not found")
            print("\n해결 방법:")
            print("  1. .env 파일에 추가:")
            print("     echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env")
            print("\n  2. 환경변수로 설정 (PowerShell):")
            print("     $env:ANTHROPIC_API_KEY='sk-ant-...'")
            print("\n  3. 환경변수로 설정 (CMD):")
            print("     set ANTHROPIC_API_KEY=sk-ant-...")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print(f"✅ Claude Vision Table Extractor initialized")
            print(f"   API Key: {self.api_key[:20]}...")
    
    def extract_tables_from_page(
        self,
        page_image: Image.Image,
        page_num: int,
        ocr_boxes: List[dict] = None
    ) -> List[ExtractedTable]:
        """
        페이지 이미지에서 표 추출
        
        Args:
            page_image: PIL Image 객체
            page_num: 페이지 번호
            ocr_boxes: OCR bbox 리스트 (표 영역 힌트용, 선택)
            
        Returns:
            추출된 표 리스트
        """
        if not self.client:
            print("  ⚠️  Claude Vision unavailable (no API key)")
            return []
        
        # 1. 표 영역 탐지
        table_regions = self._detect_table_regions(page_image, ocr_boxes)
        
        if not table_regions:
            print(f"  ℹ️  No table regions detected on page {page_num}")
            return []
        
        print(f"  🔍 Found {len(table_regions)} potential table region(s) on page {page_num}")
        
        # 2. 각 표 영역을 Claude Vision으로 처리
        tables = []
        for i, region in enumerate(table_regions):
            print(f"  📊 Processing table {i+1}/{len(table_regions)}...")
            
            table = self._extract_single_table(
                page_image,
                region,
                page_num
            )
            
            if table:
                tables.append(table)
                print(f"  ✅ Table {i+1} extracted successfully")
            else:
                print(f"  ⚠️  Table {i+1} extraction failed or no table found")
        
        return tables
    
    def _detect_table_regions(
        self,
        page_image: Image.Image,
        ocr_boxes: List[dict] = None
    ) -> List[Tuple[int, int, int, int]]:
        """표 영역 탐지 (전체 페이지)"""
        width, height = page_image.size
        return [(0, 0, width, height)]
    
    def _extract_single_table(
        self,
        page_image: Image.Image,
        region: Tuple[int, int, int, int],
        page_num: int
    ) -> Optional[ExtractedTable]:
        """단일 표 추출 (Claude Vision 사용)"""
        try:
            # 1. 표 영역 크롭
            x1, y1, x2, y2 = region
            table_image = page_image.crop((x1, y1, x2, y2))
            
            # 2. 이미지를 base64로 인코딩
            buffered = io.BytesIO()
            table_image.save(buffered, format="PNG")
            image_data = base64.b64encode(buffered.getvalue()).decode()
            
            # 3. Claude Vision API 호출
            prompt = """이 이미지를 분석해주세요.

**지시사항:**
1. 이미지에 표(table)가 있다면, 표를 정확한 Markdown 형식으로 변환해주세요.
2. 표가 없다면 "NO_TABLE"이라고만 응답해주세요.
3. 표가 있다면 다음 형식으로 응답해주세요:

TABLE_START
[Markdown 표]
TABLE_END

DESCRIPTION_START
[표에 대한 간단한 설명 1-2문장]
DESCRIPTION_END

**중요:**
- 표의 모든 셀을 정확히 추출해주세요.
- 헤더 행과 데이터 행을 구분해주세요.
- 숫자, 퍼센트, 특수문자를 정확히 보존해주세요.
- 한글을 정확히 인식해주세요."""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
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
            
            # 4. 응답 파싱
            response_text = message.content[0].text
            
            # NO_TABLE 체크
            if "NO_TABLE" in response_text:
                return None
            
            # Markdown 추출
            markdown = self._extract_between(response_text, "TABLE_START", "TABLE_END")
            description = self._extract_between(response_text, "DESCRIPTION_START", "DESCRIPTION_END")
            
            if not markdown:
                return None
            
            # 5. ExtractedTable 생성
            table = ExtractedTable(
                markdown=markdown.strip(),
                description=description.strip() if description else "",
                page_num=page_num,
                bbox=region,
                confidence=0.95
            )
            
            return table
            
        except Exception as e:
            print(f"  ❌ Claude Vision API error: {e}")
            return None
    
    def _extract_between(self, text: str, start_marker: str, end_marker: str) -> Optional[str]:
        """마커 사이의 텍스트 추출"""
        try:
            start_idx = text.index(start_marker) + len(start_marker)
            end_idx = text.index(end_marker, start_idx)
            return text[start_idx:end_idx].strip()
        except ValueError:
            return None


# 테스트
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Claude Vision Table Extractor Test")
    print("=" * 60)
    print()
    
    # Extractor 초기화
    extractor = ClaudeVisionTableExtractor()
    
    if not extractor.client:
        print("\n❌ Initialization failed")
        sys.exit(1)
    
    print("\n✅ Initialization successful!")
    print("\nTo test with actual PDF:")
    print("  streamlit run app_phase2.py")
    print("  또는")
    print("  python core/phase2_pipeline.py test_parser_02.pdf")
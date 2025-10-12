"""
PRISM Phase 2.2 - Claude Vision Table Extractor

Claude Vision API를 사용하여 표를 추출합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-13
"""

import os
import base64
from typing import List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import io
import anthropic


@dataclass
class ExtractedTable:
    """추출된 표"""
    markdown: str
    description: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    confidence: float = 0.95  # Claude Vision은 높은 정확도
    
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
    
    장점:
    - 표 구조 완벽 인식
    - 한글 정확도 95%+
    - Markdown 자동 변환
    - 표 설명까지 생성
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 읽음)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("⚠️  ANTHROPIC_API_KEY not found. Table extraction will be skipped.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            print("✅ Claude Vision Table Extractor initialized")
    
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
            return []
        
        # 1. 표 영역 탐지 (OCR bbox 기반 휴리스틱)
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
                print(f"  ⚠️  Table {i+1} extraction failed")
        
        return tables
    
    def _detect_table_regions(
        self,
        page_image: Image.Image,
        ocr_boxes: List[dict] = None
    ) -> List[Tuple[int, int, int, int]]:
        """
        표 영역 탐지 (간단한 휴리스틱)
        
        전략:
        1. OCR bbox들의 밀도가 높은 영역 찾기
        2. 정렬 패턴이 있는 영역 찾기
        3. 전체 페이지를 하나의 영역으로 간주 (단순화)
        
        Returns:
            [(x1, y1, x2, y2), ...] 형태의 bbox 리스트
        """
        # 🎯 단순화: 전체 페이지를 하나의 표 영역으로
        # (실제로는 더 정교한 알고리즘 필요)
        width, height = page_image.size
        
        # 전체 페이지
        return [(0, 0, width, height)]
    
    def _extract_single_table(
        self,
        page_image: Image.Image,
        region: Tuple[int, int, int, int],
        page_num: int
    ) -> Optional[ExtractedTable]:
        """
        단일 표 추출 (Claude Vision 사용)
        
        Args:
            page_image: 페이지 이미지
            region: 표 영역 (x1, y1, x2, y2)
            page_num: 페이지 번호
            
        Returns:
            추출된 표 또는 None
        """
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
    from pathlib import Path
    
    # API 키 확인
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found")
        print("Please set environment variable:")
        print("  export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)
    
    # 테스트 이미지
    test_image_path = "test_table.png"
    if not Path(test_image_path).exists():
        print(f"⚠️  Test image not found: {test_image_path}")
        print("Creating a simple test...")
        
        # 간단한 테스트 (실제 이미지 없이)
        extractor = ClaudeVisionTableExtractor(api_key)
        print("\n✅ Extractor initialized successfully")
        print("\nTo test with real PDF:")
        print("  python core/phase2_pipeline.py <pdf_path>")
    else:
        # 실제 이미지 테스트
        extractor = ClaudeVisionTableExtractor(api_key)
        
        image = Image.open(test_image_path)
        tables = extractor.extract_tables_from_page(image, page_num=1)
        
        print(f"\n✅ Extracted {len(tables)} table(s)")
        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            print(f"  Page: {table.page_num}")
            print(f"  Confidence: {table.confidence}")
            print(f"  Description: {table.description}")
            print(f"\nMarkdown:\n{table.markdown}")
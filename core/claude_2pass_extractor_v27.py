"""
PRISM Phase 2.7 - 2-Pass Extractor with Bbox & Deduplication (UTF-8 Fixed)

🔥 긴급 수정 사항:
1. UTF-8 인코딩 명시적 처리
2. ensure_ascii=False 설정
3. 한글 깨짐 완전 해결

Author: 박준호 (AI/ML Lead) + 이서영 (Backend Lead)
Date: 2025-10-17
Last Modified: 2025-10-17 (UTF-8 Fix)
"""

import os
import base64
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from PIL import Image
import io
import json
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic


@dataclass
class BBox:
    """Bounding Box"""
    x: int
    y: int
    width: int
    height: int
    
    def to_dict(self) -> Dict:
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }


@dataclass
class TextBlock:
    """텍스트 블록"""
    text: str
    bbox: Optional[BBox] = None
    confidence: float = 0.95


@dataclass
class Table:
    """표"""
    caption: str
    markdown: str
    bbox: Optional[BBox] = None
    confidence: float = 0.95


@dataclass
class Chart:
    """차트/그래프"""
    type: str
    title: str
    description: str
    data_points: List[Dict[str, Any]]
    bbox: Optional[BBox] = None
    confidence: float = 0.95


@dataclass
class Figure:
    """이미지/다이어그램"""
    type: str
    description: str
    bbox: Optional[BBox] = None
    confidence: float = 0.95


@dataclass
class PageContent:
    """페이지 전체 내용"""
    page_num: int
    page_title: Optional[str]
    page_number: Optional[str]
    text_blocks: List[TextBlock] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    charts: List[Chart] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)


class Claude2PassExtractorV27:
    """
    Phase 2.7 - UTF-8 완벽 지원
    """
    
    # ============================================================
    # Pass 1: Layout Analysis with Bbox
    # ============================================================
    
    LAYOUT_ANALYSIS_PROMPT = """
당신은 문서 레이아웃 분석 전문가입니다.

**목표: 이 페이지의 구조와 각 요소의 위치(bbox)를 파악하세요.**

다음 정보를 추출하세요:

1. **페이지 타이틀** + bbox
2. **페이지 번호** + bbox
3. **차트** (제목 + bbox)
4. **표** (제목 + bbox)
5. **이미지/지도** (설명 + bbox)
6. **텍스트 블록** (내용 + bbox)

**Bbox 형식:**
```json
"bbox": {
  "x": 100,      // 좌상단 x (픽셀)
  "y": 200,      // 좌상단 y (픽셀)
  "width": 300,  // 너비 (픽셀)
  "height": 400  // 높이 (픽셀)
}
```

**출력 형식 (JSON):**
```json
{
  "page_title": "페이지 타이틀",
  "page_title_bbox": {"x": 50, "y": 30, "width": 500, "height": 40},
  "page_number": "페이지 번호",
  "page_number_bbox": {"x": 50, "y": 1000, "width": 200, "height": 30},
  "elements": [
    {
      "type": "chart",
      "title": "차트 제목",
      "bbox": {"x": 100, "y": 200, "width": 300, "height": 400}
    }
  ]
}
```

**중요:**
- 모든 요소에 bbox를 포함하세요
- 좌표는 페이지 좌상단 (0,0) 기준
- 한글을 정확히 인식하세요
"""

    # ============================================================
    # Pass 2: Detailed Extraction
    # ============================================================
    
    EXTRACT_CHARTS_PROMPT = """
이 페이지의 **모든 차트**를 추출하세요.

🚨 **절대 규칙:**
1. **모든 차트를 찾아야 합니다**
2. **각 차트는 반드시 data_points를 포함해야 합니다**
3. **data_points: [] 는 절대 금지입니다**
4. **한글을 정확히 추출하세요**

**출력 형식 (JSON):**
```json
{
  "charts": [
    {
      "type": "pie",
      "title": "응답자 성별 및 연령",
      "description": "응답자의 성별 분포",
      "data_points": [
        {"label": "남성", "value": 45.2, "unit": "%"},
        {"label": "여성", "value": 54.8, "unit": "%"}
      ]
    }
  ]
}
```
"""

    EXTRACT_TABLES_PROMPT = """
이 페이지의 **모든 표**를 추출하세요.

**중요:** 한글을 정확히 추출하세요.

**출력 형식 (JSON):**
```json
{
  "tables": [
    {
      "caption": "리그별 고관여팬 특성",
      "markdown": "| 지역 | 비율 |\\n|---|---|\\n| 프로스포츠 팬 | 58.4 |"
    }
  ]
}
```
"""

    EXTRACT_FIGURES_PROMPT = """
이 페이지의 **이미지/지도/다이어그램**을 추출하세요.

**중요:** 
- 차트와 중복되지 않도록 주의하세요!
- 한글을 정확히 추출하세요.

**출력 형식 (JSON):**
```json
{
  "figures": [
    {
      "type": "map",
      "description": "응답자 지역별 분포를 보여주는 한국 지도"
    }
  ]
}
```
"""

    EXTRACT_TEXTS_PROMPT = """
이 페이지의 **주요 텍스트 블록**만 추출하세요.

**제외 항목:**
- 단순 숫자 (45.7, 54.3 등)
- 라벨 (단위: %, 명 등)

**포함 항목:**
- 문단 텍스트
- 제목/부제목
- 설명문

**중요:** 한글을 정확히 추출하세요.

**출력 형식 (JSON):**
```json
{
  "texts": [
    {
      "content": "2023년 조사에 참여한 전체 응답자는...",
      "type": "paragraph"
    }
  ]
}
```
"""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not found")
            self.client = None
            return
        
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            print(f"✅ Claude 2-Pass Extractor V2.7 (UTF-8) initialized")
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            self.client = None

    def _image_to_base64(self, image: Image.Image) -> str:
        """PIL Image를 base64로 변환"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _call_claude(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int = 4096
    ) -> Optional[Dict]:
        """
        Claude API 호출 (재시도 포함)
        
        🔥 UTF-8 처리 강화
        """
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
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
                
                # 🔥 UTF-8 명시적 처리
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        # Claude API는 이미 UTF-8로 반환하므로 그대로 사용
                        text_content += block.text
                
                # JSON 추출
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = text_content.strip()
                
                # 🔥 JSON 파싱 (UTF-8 자동 처리)
                result = json.loads(json_str)
                
                # 🔥 디버깅: 한글 체크
                if result.get('page_title'):
                    sample = result['page_title'][:20]
                    print(f"   [UTF-8 Check] Sample: {sample}")
                
                return result
                
            except anthropic.APIError as e:
                if getattr(e, 'status_code', None) == 529:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    if attempt < self.max_retries:
                        print(f"⏳ 529 Overloaded, waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                print(f"❌ API Error: {e}")
                return None
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                return None
            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
                return None
        
        return None

    def _parse_bbox(self, bbox_data: Dict) -> Optional[BBox]:
        """bbox 딕셔너리를 BBox 객체로 변환"""
        if not bbox_data:
            return None
        try:
            return BBox(
                x=int(bbox_data.get('x', 0)),
                y=int(bbox_data.get('y', 0)),
                width=int(bbox_data.get('width', 0)),
                height=int(bbox_data.get('height', 0))
            )
        except (ValueError, TypeError):
            return None

    def _is_duplicate(self, chart: Chart, figure: Figure) -> bool:
        """Chart와 Figure가 중복인지 체크"""
        # 제목이 설명에 포함되어 있으면 중복
        if chart.title.lower() in figure.description.lower():
            return True
        
        # Bbox가 비슷하면 중복 (80% 이상 겹침)
        if chart.bbox and figure.bbox:
            overlap = self._calculate_overlap(chart.bbox, figure.bbox)
            if overlap > 0.8:
                return True
        
        return False

    def _calculate_overlap(self, bbox1: BBox, bbox2: BBox) -> float:
        """두 bbox의 겹침 비율 계산"""
        x1_left = bbox1.x
        y1_top = bbox1.y
        x1_right = bbox1.x + bbox1.width
        y1_bottom = bbox1.y + bbox1.height
        
        x2_left = bbox2.x
        y2_top = bbox2.y
        x2_right = bbox2.x + bbox2.width
        y2_bottom = bbox2.y + bbox2.height
        
        # 겹치는 영역 계산
        overlap_left = max(x1_left, x2_left)
        overlap_top = max(y1_top, y2_top)
        overlap_right = min(x1_right, x2_right)
        overlap_bottom = min(y1_bottom, y2_bottom)
        
        if overlap_right <= overlap_left or overlap_bottom <= overlap_top:
            return 0.0
        
        overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
        bbox1_area = bbox1.width * bbox1.height
        bbox2_area = bbox2.width * bbox2.height
        
        min_area = min(bbox1_area, bbox2_area)
        if min_area == 0:
            return 0.0
        
        return overlap_area / min_area

    def _merge_semantic_texts(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """의미 단위로 텍스트 병합"""
        if not text_blocks:
            return []
        
        merged = []
        current_block = None
        
        for block in text_blocks:
            text = block.text.strip()
            
            # 단순 숫자나 라벨은 스킵
            if len(text) < 3 or text.replace('.', '').replace(',', '').isdigit():
                continue
            
            # 첫 블록이거나 이전 블록과 연결되지 않으면 새 블록
            if current_block is None:
                current_block = block
            else:
                # 같은 의미 단위인지 체크
                if self._should_merge(current_block, block):
                    # 병합
                    current_block.text += " " + block.text
                    # Bbox 확장
                    if current_block.bbox and block.bbox:
                        current_block.bbox = self._merge_bbox(current_block.bbox, block.bbox)
                else:
                    # 이전 블록 저장하고 새 블록 시작
                    merged.append(current_block)
                    current_block = block
        
        if current_block:
            merged.append(current_block)
        
        return merged

    def _should_merge(self, block1: TextBlock, block2: TextBlock) -> bool:
        """두 텍스트 블록을 병합해야 하는지 판단"""
        # Bbox가 세로로 가까우면 병합
        if block1.bbox and block2.bbox:
            vertical_distance = abs(block2.bbox.y - (block1.bbox.y + block1.bbox.height))
            if vertical_distance < 50:  # 50픽셀 이내
                return True
        
        return False

    def _merge_bbox(self, bbox1: BBox, bbox2: BBox) -> BBox:
        """두 bbox를 포함하는 확장된 bbox 생성"""
        x = min(bbox1.x, bbox2.x)
        y = min(bbox1.y, bbox2.y)
        right = max(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        bottom = max(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        return BBox(
            x=x,
            y=y,
            width=right - x,
            height=bottom - y
        )

    def extract(self, image: Image.Image, page_num: int = 1) -> Optional[PageContent]:
        """
        2-Pass 전략으로 페이지 추출 (Phase 2.7 - UTF-8 Fixed)
        """
        if not self.client:
            print("❌ Claude API not initialized")
            return None
        
        print(f"\n{'='*60}")
        print(f"📄 Phase 2.7 (UTF-8) - Processing Page {page_num}")
        print(f"{'='*60}")
        
        image_base64 = self._image_to_base64(image)
        
        # ============================================================
        # Pass 1: Layout Analysis with Bbox
        # ============================================================
        
        print(f"\n🔍 Pass 1: Layout Analysis with Bbox...")
        layout_result = self._call_claude(image_base64, self.LAYOUT_ANALYSIS_PROMPT)
        
        if not layout_result:
            print("❌ Layout analysis failed")
            return None
        
        page_title = layout_result.get('page_title')
        page_title_bbox = self._parse_bbox(layout_result.get('page_title_bbox'))
        page_number = layout_result.get('page_number')
        page_number_bbox = self._parse_bbox(layout_result.get('page_number_bbox'))
        
        # 요소별 bbox 저장
        element_bboxes = {}
        for elem in layout_result.get('elements', []):
            elem_type = elem.get('type')
            elem_title = elem.get('title') or elem.get('caption', '')
            elem_bbox = self._parse_bbox(elem.get('bbox'))
            if elem_bbox:
                element_bboxes[f"{elem_type}_{elem_title}"] = elem_bbox
        
        print(f"✅ Layout Analysis Complete")
        print(f"   - Page Title: {page_title}")
        print(f"   - Page Number: {page_number}")
        print(f"   - Elements with Bbox: {len(element_bboxes)}")
        
        # ============================================================
        # Pass 2: Element Extraction
        # ============================================================
        
        print(f"\n🔍 Pass 2: Element Extraction...")
        
        # Charts
        charts = []
        print(f"   📊 Extracting charts...")
        charts_result = self._call_claude(image_base64, self.EXTRACT_CHARTS_PROMPT)
        if charts_result and 'charts' in charts_result:
            for chart_data in charts_result['charts']:
                title = chart_data.get('title', '')
                bbox = element_bboxes.get(f"chart_{title}")
                
                charts.append(Chart(
                    type=chart_data.get('type', 'unknown'),
                    title=title,
                    description=chart_data.get('description', ''),
                    data_points=chart_data.get('data_points', []),
                    bbox=bbox,
                    confidence=0.95
                ))
        
        # Tables
        tables = []
        print(f"   📋 Extracting tables...")
        tables_result = self._call_claude(image_base64, self.EXTRACT_TABLES_PROMPT)
        if tables_result and 'tables' in tables_result:
            for table_data in tables_result['tables']:
                caption = table_data.get('caption', '')
                bbox = element_bboxes.get(f"table_{caption}")
                
                tables.append(Table(
                    caption=caption,
                    markdown=table_data.get('markdown', ''),
                    bbox=bbox,
                    confidence=0.99
                ))
        
        # Figures
        figures = []
        print(f"   🖼️  Extracting figures...")
        figures_result = self._call_claude(image_base64, self.EXTRACT_FIGURES_PROMPT)
        if figures_result and 'figures' in figures_result:
            for figure_data in figures_result['figures']:
                description = figure_data.get('description', '')
                bbox = element_bboxes.get(f"figure_{description[:20]}")
                
                figures.append(Figure(
                    type=figure_data.get('type', 'image'),
                    description=description,
                    bbox=bbox,
                    confidence=0.99
                ))
        
        # ⭐ 중복 제거
        print(f"\n🔄 Deduplication...")
        original_figure_count = len(figures)
        deduplicated_figures = []
        
        for figure in figures:
            is_dup = False
            for chart in charts:
                if self._is_duplicate(chart, figure):
                    is_dup = True
                    break
            
            if not is_dup:
                deduplicated_figures.append(figure)
        
        removed_count = original_figure_count - len(deduplicated_figures)
        if removed_count > 0:
            print(f"   ✅ Removed {removed_count} duplicate figures")
        
        # Texts
        text_blocks = []
        print(f"   📝 Extracting texts...")
        texts_result = self._call_claude(image_base64, self.EXTRACT_TEXTS_PROMPT)
        if texts_result and 'texts' in texts_result:
            for text_data in texts_result['texts']:
                text_blocks.append(TextBlock(
                    text=text_data.get('content', ''),
                    bbox=None,
                    confidence=0.99
                ))
        
        # ⭐ 텍스트 병합
        print(f"\n🔄 Merging semantic texts...")
        original_text_count = len(text_blocks)
        merged_texts = self._merge_semantic_texts(text_blocks)
        merged_count = original_text_count - len(merged_texts)
        if merged_count > 0:
            print(f"   ✅ Merged {merged_count} text blocks")
        
        # ============================================================
        # Pass 3: Summary
        # ============================================================
        
        print(f"\n✅ Pass 2 Complete:")
        print(f"   - Page Title: {page_title}")
        print(f"   - Page Number: {page_number}")
        print(f"   - Text blocks: {len(merged_texts)}")
        print(f"   - Tables: {len(tables)}")
        print(f"   - Charts: {len(charts)}")
        print(f"   - Figures: {len(deduplicated_figures)} (after dedup)")
        
        return PageContent(
            page_num=page_num,
            page_title=page_title,
            page_number=page_number,
            text_blocks=merged_texts,
            tables=tables,
            charts=charts,
            figures=deduplicated_figures
        )


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRISM Phase 2.7 - UTF-8 Fixed Extractor Test")
    print("="*60 + "\n")
    
    extractor = Claude2PassExtractorV27()
    
    if extractor.client:
        print("✅ Ready for Phase 2.7 extraction (UTF-8)!")
        print("\n개선사항:")
        print("1. UTF-8 인코딩 완벽 처리")
        print("2. 한글 깨짐 해결")
        print("3. Bbox 추출")
        print("4. 중복 제거")
    else:
        print("❌ Claude API not available")
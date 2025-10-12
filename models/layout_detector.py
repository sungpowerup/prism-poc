"""
PRISM Phase 2 - Layout Detector

LayoutParser를 사용한 문서 레이아웃 감지

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image


class ElementType(Enum):
    """문서 요소 타입"""
    TEXT = "text"
    TITLE = "title"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"
    FIGURE = "figure"


@dataclass
class BoundingBox:
    """바운딩 박스"""
    x: int
    y: int
    width: int
    height: int
    
    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """(x1, y1, x2, y2) 형식"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class DocumentElement:
    """문서 요소"""
    type: ElementType
    bbox: BoundingBox
    confidence: float
    page_num: int
    
    def to_dict(self):
        return {
            "type": self.type.value,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "page_num": self.page_num
        }


class ImageTypeClassifier:
    """
    이미지 타입 분류 (차트 vs 일반 이미지)
    
    간단한 휴리스틱:
    - 색상 분포가 단순하면 차트
    - 복잡하면 일반 이미지
    """
    
    def classify(self, image: Image.Image) -> ElementType:
        """
        이미지 타입 분류
        
        Args:
            image: PIL Image
            
        Returns:
            ElementType.CHART or ElementType.IMAGE
        """
        try:
            # 이미지를 작게 리사이즈
            img_array = np.array(image.resize((100, 100)))
            
            # 색상 다양성 계산
            if len(img_array.shape) == 3:
                unique_colors = len(np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0))
            else:
                unique_colors = len(np.unique(img_array))
            
            # 단순한 색상 = 차트
            if unique_colors < 1000:
                return ElementType.CHART
            else:
                return ElementType.IMAGE
        
        except Exception:
            return ElementType.IMAGE


class LayoutDetector:
    """
    문서 레이아웃 감지기
    
    LayoutParser + PubLayNet 모델 사용
    """
    
    def __init__(
        self, 
        model_name: str = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
        confidence_threshold: float = 0.5,
        use_mock: bool = False  # ⭐ Mock 모드 추가
    ):
        """
        Args:
            model_name: LayoutParser 모델
            confidence_threshold: 신뢰도 임계값
            use_mock: Mock 모드 사용 여부 (Detectron2 없을 때)
        """
        self.confidence_threshold = confidence_threshold
        self.use_mock = use_mock
        self.model = None
        
        if not use_mock:
            try:
                import layoutparser as lp
                
                # Detectron2LayoutModel 체크
                if not hasattr(lp, 'Detectron2LayoutModel'):
                    print("⚠️  Detectron2LayoutModel not available. Using Mock mode.")
                    self.use_mock = True
                else:
                    self.model = lp.Detectron2LayoutModel(model_name)
                    print("✅ LayoutParser model loaded")
            
            except ImportError:
                print("⚠️  LayoutParser not installed. Using Mock mode.")
                self.use_mock = True
            except Exception as e:
                print(f"⚠️  Failed to load LayoutParser: {e}. Using Mock mode.")
                self.use_mock = True
        
        # Image Classifier
        self.image_classifier = ImageTypeClassifier()
    
    def detect(
        self, 
        image: Image.Image,
        page_num: int = 1
    ) -> List[DocumentElement]:
        """
        페이지에서 요소 감지
        
        Args:
            image: 페이지 이미지
            page_num: 페이지 번호
            
        Returns:
            감지된 요소 목록
        """
        if self.use_mock:
            return self._detect_mock(image, page_num)
        
        return self._detect_real(image, page_num)
    
    def _detect_real(
        self, 
        image: Image.Image,
        page_num: int
    ) -> List[DocumentElement]:
        """실제 LayoutParser로 감지"""
        # NumPy 배열로 변환
        image_array = np.array(image)
        
        # Layout Detection
        layout = self.model.detect(image_array)
        
        elements = []
        for block in layout:
            # 신뢰도 필터링
            if block.score < self.confidence_threshold:
                continue
            
            # 타입 매핑
            element_type = self._map_label_to_type(block.type)
            
            # 이미지 타입 세분화
            if element_type == ElementType.IMAGE:
                bbox_tuple = (
                    int(block.block.x_1),
                    int(block.block.y_1),
                    int(block.block.x_2),
                    int(block.block.y_2)
                )
                cropped = image.crop(bbox_tuple)
                element_type = self.image_classifier.classify(cropped)
            
            # BBox 생성
            bbox = BoundingBox(
                x=int(block.block.x_1),
                y=int(block.block.y_1),
                width=int(block.block.x_2 - block.block.x_1),
                height=int(block.block.y_2 - block.block.y_1)
            )
            
            element = DocumentElement(
                type=element_type,
                bbox=bbox,
                confidence=block.score,
                page_num=page_num
            )
            elements.append(element)
        
        # 읽기 순서 정렬 (위→아래, 왼쪽→오른쪽)
        elements.sort(key=lambda e: (e.bbox.y, e.bbox.x))
        
        return elements
    
    def _detect_mock(
        self, 
        image: Image.Image,
        page_num: int
    ) -> List[DocumentElement]:
        """
        Mock Detection (Detectron2 없을 때)
        
        전체 페이지를 하나의 TEXT 요소로 반환
        """
        width, height = image.size
        
        mock_element = DocumentElement(
            type=ElementType.TEXT,
            bbox=BoundingBox(x=0, y=0, width=width, height=height),
            confidence=1.0,
            page_num=page_num
        )
        
        print(f"⚠️  Mock mode: returning full page as TEXT element")
        return [mock_element]
    
    def _map_label_to_type(self, label: str) -> ElementType:
        """
        PubLayNet 레이블 → ElementType 매핑
        
        PubLayNet 레이블:
        - Text, Title, List, Table, Figure
        """
        mapping = {
            "Text": ElementType.TEXT,
            "Title": ElementType.TITLE,
            "List": ElementType.TEXT,
            "Table": ElementType.TABLE,
            "Figure": ElementType.IMAGE
        }
        
        return mapping.get(label, ElementType.TEXT)
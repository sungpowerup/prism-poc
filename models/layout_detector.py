"""
PRISM Phase 2 - Layout Detection Module

문서 페이지에서 텍스트, 표, 이미지, 차트 영역을 자동으로 감지합니다.

Author: 박준호 (AI/ML Lead)
Date: 2025-10-11
"""

import layoutparser as lp
import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class ElementType(Enum):
    """문서 요소 타입"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"
    TITLE = "title"
    FOOTER = "footer"
    HEADER = "header"


@dataclass
class BoundingBox:
    """바운딩 박스 좌표"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }


@dataclass
class DocumentElement:
    """문서 내 감지된 요소"""
    type: ElementType
    bbox: BoundingBox
    confidence: float
    page_num: int
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "page": self.page_num
        }


class LayoutDetector:
    """
    문서 레이아웃 감지 모듈
    
    LayoutParser + PubLayNet 모델 사용
    """
    
    def __init__(self, model_name: str = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"):
        """
        Args:
            model_name: LayoutParser 모델 이름
                - PubLayNet: 논문/보고서 최적화
                - TableBank: 표 감지 최적화
        """
        print(f"Loading layout detection model: {model_name}")
        self.model = lp.Detectron2LayoutModel(
            model_name,
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.6],
            label_map={
                0: "text",
                1: "title", 
                2: "list",
                3: "table",
                4: "figure"
            }
        )
        print("Layout model loaded successfully")
    
    def detect(self, image: Image.Image, page_num: int = 1) -> List[DocumentElement]:
        """
        이미지에서 문서 요소 감지
        
        Args:
            image: PIL Image 객체
            page_num: 페이지 번호
            
        Returns:
            List[DocumentElement]: 감지된 요소 리스트
        """
        # PIL Image → OpenCV 형식
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB@BGR)
        
        # Layout Detection 수행
        layout = self.model.detect(cv_image)
        
        # 결과 변환
        elements = []
        for block in layout:
            element_type = self._map_element_type(block.type)
            
            bbox = BoundingBox(
                x=int(block.block.x_1),
                y=int(block.block.y_1),
                width=int(block.block.width),
                height=int(block.block.height)
            )
            
            element = DocumentElement(
                type=element_type,
                bbox=bbox,
                confidence=block.score,
                page_num=page_num
            )
            
            elements.append(element)
        
        # 위에서 아래로 정렬 (읽기 순서)
        elements = self._sort_by_reading_order(elements)
        
        return elements
    
    def _map_element_type(self, layout_type: str) -> ElementType:
        """LayoutParser 타입 → 우리 타입으로 매핑"""
        type_mapping = {
            "text": ElementType.TEXT,
            "title": ElementType.TITLE,
            "list": ElementType.TEXT,
            "table": ElementType.TABLE,
            "figure": ElementType.IMAGE  # 일단 이미지로, 나중에 차트 분류
        }
        return type_mapping.get(layout_type, ElementType.TEXT)
    
    def _sort_by_reading_order(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """
        요소를 읽기 순서대로 정렬 (위→아래, 왼쪽→오른쪽)
        """
        return sorted(elements, key=lambda e: (e.bbox.y, e.bbox.x))
    
    def visualize(self, image: Image.Image, elements: List[DocumentElement]) -> Image.Image:
        """
        감지 결과를 이미지에 시각화
        
        Args:
            image: 원본 이미지
            elements: 감지된 요소 리스트
            
        Returns:
            시각화된 이미지
        """
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 타입별 색상
        colors = {
            ElementType.TEXT: (0, 255, 0),      # 초록
            ElementType.TITLE: (255, 0, 0),     # 빨강
            ElementType.TABLE: (0, 0, 255),     # 파랑
            ElementType.IMAGE: (255, 255, 0),   # 노랑
            ElementType.CHART: (255, 0, 255),   # 보라
        }
        
        for element in elements:
            bbox = element.bbox
            color = colors.get(element.type, (128, 128, 128))
            
            # 박스 그리기
            cv2.rectangle(
                cv_image,
                (bbox.x, bbox.y),
                (bbox.x + bbox.width, bbox.y + bbox.height),
                color,
                2
            )
            
            # 라벨 그리기
            label = f"{element.type.value} ({element.confidence:.2f})"
            cv2.putText(
                cv_image,
                label,
                (bbox.x, bbox.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
        
        # OpenCV → PIL
        result_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        return result_image


class ImageTypeClassifier:
    """
    이미지 타입 분류: 장식 이미지 vs 차트/도표
    
    차트/도표만 VLM 처리하기 위한 필터
    """
    
    def __init__(self):
        pass
    
    def classify(self, image: Image.Image) -> ElementType:
        """
        이미지가 차트/도표인지 판단
        
        Args:
            image: 크롭된 이미지
            
        Returns:
            ElementType.CHART or ElementType.IMAGE
        """
        # 간단한 휴리스틱 분류
        # 실제로는 더 정교한 분류 필요 (별도 분류 모델 사용 가능)
        
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # 1. 엣지 밀도 계산 (차트는 선이 많음)
        edges = cv2.Canny(cv_image, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # 2. 텍스트 영역 비율 (차트는 레이블/축 텍스트 많음)
        # PaddleOCR 사용하면 더 정확
        
        # 임계값 기반 분류
        if edge_density > 0.15:  # 엣지가 많으면 차트
            return ElementType.CHART
        else:
            return ElementType.IMAGE
    
    def should_caption(self, element_type: ElementType) -> bool:
        """VLM 캡션 생성 필요 여부"""
        return element_type in [ElementType.CHART, ElementType.TABLE]


# 테스트 코드
if __name__ == "__main__":
    from PIL import Image
    
    # 테스트 이미지 로드
    test_image = Image.open("data/uploads/sample.png")
    
    # Layout Detection
    detector = LayoutDetector()
    elements = detector.detect(test_image, page_num=1)
    
    print(f"감지된 요소: {len(elements)}개")
    for element in elements:
        print(f"- {element.type.value}: {element.bbox.to_dict()}")
    
    # 시각화
    vis_image = detector.visualize(test_image, elements)
    vis_image.save("data/processed/layout_detection_result.png")
    print("시각화 결과 저장 완료")
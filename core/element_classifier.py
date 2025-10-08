"""
core/element_classifier.py
PRISM POC - Element 자동 분류 (간단 버전)
"""

from typing import Dict
from PIL import Image
import numpy as np

class ElementClassifier:
    """이미지 타입 자동 분류"""
    
    def classify(self, image: Image.Image) -> Dict:
        """
        이미지 타입 분류 (간단 버전)
        
        Returns:
            {
                'element_type': 'chart' | 'table' | 'image' | 'diagram',
                'confidence': float,
                'reasoning': str
            }
        """
        
        # 간단한 휴리스틱 분류
        # 실제로는 더 복잡한 로직이지만, 일단 기본값 사용
        
        width, height = image.size
        aspect_ratio = width / height
        
        # 일단 모든 이미지를 'image'로 분류
        # (VLM이 알아서 판단하게 함)
        return {
            'element_type': 'image',
            'confidence': 0.8,
            'reasoning': 'Default classification'
        }
    
    def classify_batch(self, images: list) -> list:
        """배치 분류"""
        return [self.classify(img) for img in images]
"""
core/prompt_rules.py
PRISM Phase 0.3.4 P1 - GPT 핫픽스 반영

✅ 변경사항:
1. 개정이력 힌트 감지 함수 추가
2. 표 부분 허용 (개정이력 페이지만)
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """Phase 0.3.4 P1 프롬프트 규칙"""
    
    # 개정이력 감지 키워드
    REVISION_KEYWORDS = ['개정', '이력', '변경', '제정', '시행']
    
    def __init__(self):
        logger.info("✅ PromptRules Phase 0.3.4 P1 초기화")
    
    def has_revision_hints(self, hints: Dict[str, Any]) -> bool:
        """개정이력 힌트 감지"""
        # OCR 텍스트에서 개정 키워드 검색
        ocr_text = hints.get('ocr_text', '').lower()
        
        for keyword in self.REVISION_KEYWORDS:
            if keyword in ocr_text:
                return True
        
        # 날짜 패턴 (2024.01.01 형식)
        date_pattern = r'\d{4}\.\d{1,2}\.\d{1,2}'
        if re.search(date_pattern, ocr_text):
            # 날짜가 3개 이상이면 개정이력 가능성 높음
            dates = re.findall(date_pattern, ocr_text)
            if len(dates) >= 3:
                return True
        
        # 표 존재 + 텍스트 적음 = 개정이력 표
        if hints.get('tables') and hints.get('text_ratio', 1.0) < 0.3:
            return True
        
        return False
    
    def build_prompt(self, hints: Dict[str, Any]) -> str:
        """프롬프트 생성"""
        
        # GPT 핫픽스: 개정이력이 있으면 표 허용
        doc_type = hints.get('doc_type', 'general')
        allow_tables = hints.get('allow_tables', False)
        
        if doc_type == 'statute' and self.has_revision_hints(hints):
            allow_tables = True
            logger.info("   📊 개정이력 감지 → 표 허용")
        
        # 기본 프롬프트
        prompt = """이 이미지는 한국어 법규 문서입니다.
다음 규칙을 엄격히 따라 Markdown으로 변환하세요:

1. 원문을 정확히 추출하세요 (해석/요약 금지)
2. 조문 번호와 제목을 정확히 유지하세요
3. 개정 이력을 빠짐없이 포함하세요"""
        
        if allow_tables:
            prompt += """
4. 표는 Markdown 표 형식으로 변환하세요
5. 개정이력 표는 모든 행과 열을 포함하세요"""
        else:
            prompt += """
4. 표는 텍스트 목록으로 변환하세요"""
        
        logger.info(f"✅ 프롬프트 생성 완료 ({len(prompt)}자)")
        logger.info(f"   📋 표 허용: {allow_tables}")
        
        return prompt
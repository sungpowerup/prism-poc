"""
core/prompt_rules.py
PRISM Phase 0.3.4 P2 - 개정이력 표 화이트리스트

✅ 변경사항:
1. 개정이력 힌트 감지 로직 추가
2. 페이지 1 + 개정 키워드 → 표 허용
3. 로그 개선
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptRules:
    """Phase 0.3.4 P2 프롬프트 규칙 (개정이력 표 화이트리스트)"""
    
    # 개정이력 감지 키워드
    REVISION_KEYWORDS = ['개정', '차', '제정', '시행']
    
    def __init__(self):
        logger.info("✅ PromptRules Phase 0.3.4 P2 초기화")
    
    def has_revision_hints(self, hints: Dict[str, Any], page_num: int) -> bool:
        """
        개정이력 페이지 감지
        
        조건:
        1. 페이지 1
        2. OCR 텍스트에 개정/차 키워드
        3. 날짜 패턴 3개 이상
        """
        # 페이지 1이 아니면 False
        if page_num != 1:
            return False
        
        # OCR 텍스트
        ocr_text = hints.get('ocr_text', '')
        
        # 키워드 검사
        keyword_found = False
        for keyword in self.REVISION_KEYWORDS:
            if keyword in ocr_text:
                keyword_found = True
                break
        
        if not keyword_found:
            return False
        
        # 날짜 패턴 (2024.01.01 형식)
        date_pattern = r'\d{4}\.\d{1,2}\.\d{1,2}'
        dates = re.findall(date_pattern, ocr_text)
        
        # 날짜 3개 이상 → 개정이력 가능성 높음
        if len(dates) >= 3:
            logger.info(f"   📅 개정이력 감지: {len(dates)}개 날짜 패턴")
            return True
        
        return False
    
    def build_prompt(self, hints: Dict[str, Any], page_num: int = 1) -> str:
        """프롬프트 생성 (개정이력 표 화이트리스트)"""
        
        # 개정이력 감지 → 표 허용
        allow_tables = self.has_revision_hints(hints, page_num)
        
        # 기본 프롬프트
        prompt = """이 이미지는 한국어 법규 문서입니다.
다음 규칙을 엄격히 따라 Markdown으로 변환하세요:

1. 원문을 정확히 추출하세요 (해석/요약 금지)
2. 조문 번호와 제목을 정확히 유지하세요
3. 개정 이력을 빠짐없이 포함하세요
4. "기본정신" 섹션이 있으면 반드시 포함하세요"""
        
        if allow_tables:
            prompt += """
5. 개정이력 표는 Markdown 표 형식으로 변환하세요
   예시:
   | 차수 | 날짜 |
   |------|------|
   | 제37차 개정 | 2019.05.27 |
   | 제38차 개정 | 2019.07.01 |"""
        else:
            prompt += """
5. 표는 텍스트 목록으로 변환하세요"""
        
        logger.info(f"✅ 프롬프트 생성 완료 ({len(prompt)}자)")
        logger.info(f"   📋 표 허용: {allow_tables}")
        
        return prompt
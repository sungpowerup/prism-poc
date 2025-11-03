"""
core/post_merge_normalizer.py
PRISM Phase 5.7.7.2 - Post-merge Normalizer (Fallback 띄어쓰기 강화)

✅ Phase 5.7.7.2 긴급 수정:
- Fallback 띄어쓰기 고빈도 사전 추가 (미송 제안)
- "직무의종류" → "직무의 종류" 복원
- "그밖에" → "그 밖에" 복원
- "에 게" → "에게" 병합

(Phase 5.7.7.1 기능 유지)

Author: 이서영 (Backend Lead) + 미송 진단
Date: 2025-11-03
Version: 5.7.7.2 Hotfix
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PostMergeNormalizer:
    """
    Phase 5.7.7.2 문장 결속 + 띄어쓰기 복원 (Fallback 강화)
    
    목적:
    - 번호 목록 끊김 완전 복구
    - 문장 연속성 보장
    - ✅ 조사/어미 띄어쓰기 복원 (Phase 5.7.7)
    - ✅ Fallback 경로 띄어쓰기 복원 (Phase 5.7.7.1)
    - ✅ 고빈도 한글 연쇄 보정 (Phase 5.7.7.2)
    - RAG 문맥 파편화 제거
    
    처리 순서:
    1. 페이지 구분자 제거 (Phase 5.7.7)
    2. ✅ Fallback 경로 띄어쓰기 복원 + 고빈도 사전 (Phase 5.7.7.2)
    3. 숫자 목록 결속
    4. 한글 순서 결속
    5. 괄호 번호 결속
    6. 조문 번호 결속
    7. 조사/어미 띄어쓰기 복원 (Phase 5.7.7)
    8. 불필요한 공백 정리
    """
    
    def __init__(self):
        """초기화 + 고빈도 사전"""
        # ✅ Phase 5.7.7.2: 고빈도 한글 연쇄 사전 (미송 제안)
        self.spacing_dict = {
            # 붙여야 하는 것
            '에 게': '에게',
            '에 서': '에서',
            '로 부터': '로부터',
            '에 게 서': '에게서',
            '에 의 하여': '에 의하여',
            '에 대 하여': '에 대하여',
            '와 같이': '와 같이',
            '및 파': '및 파',
            '및 면': '및 면',
            
            # 띄어야 하는 것
            '직무의종류': '직무의 종류',
            '그밖에': '그 밖에',
            '이규정': '이 규정',
            '할수': '할 수',
            '있는': '있는',
            '없는': '없는',
            '제 6조': '제6조',  # 문서 컨벤션
            '제 7조': '제7조',
            '제 8조': '제8조',
        }
        
        logger.info("✅ PostMergeNormalizer v5.7.7.2 초기화 완료 (Fallback 강화)")
        logger.info(f"   📖 고빈도 사전: {len(self.spacing_dict)}개")
    
    def normalize(self, content: str, doc_type: str = 'general') -> str:
        """
        문장 결속 + 띄어쓰기 정규화
        
        Args:
            content: Markdown 텍스트
            doc_type: 문서 타입 ('statute', 'general', 'bus_diagram', 'table')
        
        Returns:
            정규화된 텍스트
        """
        logger.info(f"   🔧 PostMergeNormalizer v5.7.7.2 시작 (doc_type: {doc_type})")
        
        original_len = len(content)
        
        # ✅ Phase 5.7.7: 페이지 구분자 제거 (우선 처리)
        content = self._remove_page_dividers(content)
        
        # ✅ Phase 5.7.7.2: Fallback 경로 띄어쓰기 복원 + 고빈도 사전 (미송 제안)
        content = self._fix_spacing_for_fallback(content)
        
        # 1) 숫자 목록 결속 강화: "1.\n내용" → "1. 내용"
        content = self._normalize_numbered_lists(content)
        
        # 2) 한글 순서 결속 (범위 수정): "가.\n내용" → "가. 내용"
        content = self._normalize_korean_lists(content)
        
        # 3) 괄호 번호 결속: "(1)\n내용" → "(1) 내용"
        content = self._normalize_parenthesized_numbers(content)
        
        # 4) 조문 번호 결속 (규정 모드만)
        if doc_type == 'statute':
            content = self._normalize_article_numbers(content)
        
        # ✅ Phase 5.7.7: 조사/어미 띄어쓰기 복원
        content = self._fix_particle_spacing(content)
        
        # 5) 불필요한 공백 정리 (보수적)
        content = self._clean_whitespace(content)
        
        normalized_len = len(content)
        
        logger.info(f"   ✅ 정규화 완료: {original_len} → {normalized_len} 글자")
        return content
    
    def _fix_spacing_for_fallback(self, content: str) -> str:
        """
        ✅ Phase 5.7.7.2: Fallback 경로 띄어쓰기 복원 + 고빈도 사전 (미송 제안)
        
        pypdf는 단어 사이 공백을 누락하거나 이상하게 분리하므로 보정
        
        패턴:
        - "란1명의" → "란 1명의"
        - "있는직무와" → "있는 직무와"
        - "말한다2" → "말한다 2"
        - "2\"직위" → "2. \"직위"
        - "직무의종류" → "직무의 종류" (고빈도 사전)
        - "에 게" → "에게" (고빈도 사전)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            띄어쓰기 복원된 텍스트
        """
        # ✅ Phase 5.7.7.2: 고빈도 사전 먼저 적용 (미송 제안)
        for wrong, correct in self.spacing_dict.items():
            content = content.replace(wrong, correct)
        
        # 1) 조사 + 숫자 ("란1명" → "란 1명")
        content = re.sub(r'([가-힣])(\d+)', r'\1 \2', content)
        
        # 2) 용언 + 명사 ("있는직무" → "있는 직무")
        # 단, 단어가 2글자 이상일 때만 (false positive 방지)
        content = re.sub(r'([는은을를이가에서])([가-힣]{2,})', r'\1 \2', content)
        
        # 3) 숫자 + 따옴표 ("2\"" → "2. \"")
        content = re.sub(r'(\d)(\")', r'\1. \2', content)
        
        # 4) 마침표 + 한글 ("한다.직원" → "한다. 직원")
        content = re.sub(r'([다])\.([가-힣])', r'\1. \2', content)
        
        # 5) 조사 띄어쓰기 보정 ("수 있는" 패턴)
        content = re.sub(r'할수있는', '할 수 있는', content)
        content = re.sub(r'할수없는', '할 수 없는', content)
        
        logger.debug("      Fallback 띄어쓰기 복원 + 사전 적용 완료")
        return content
    
    def _remove_page_dividers(self, content: str) -> str:
        """
        ✅ Phase 5.7.7: 페이지 구분자 제거 (Fallback 후에도 적용)
        
        미송 제안: Fallback 경로에서도 반드시 실행
        
        패턴:
        - "402-1", "402-2", "402-3" (페이지 번호)
        - "인사규정" (반복되는 헤더)
        - "---", "===", "***" (구분선)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정제된 텍스트
        """
        lines = content.split('\n')
        filtered_lines = []
        
        # 페이지 구분자 패턴
        page_patterns = [
            r'^\d{3,4}-\d{1,2}$',  # 402-1, 402-2
            r'^인사규정$',  # 단독 "인사규정"
            r'^[-=*_]{3,}$',  # ---, ===, ***, ___
            r'^Page\s+\d+$',  # Page 1, Page 2
            r'^\d{1,2}$',  # 단독 숫자 (1, 2, 3)
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # 패턴 매칭
            is_divider = any(re.match(pattern, stripped) for pattern in page_patterns)
            
            if not is_divider:
                filtered_lines.append(line)
            else:
                logger.debug(f"      페이지 구분자 제거: '{stripped}'")
        
        logger.debug(f"      페이지 구분자 제거 완료: {len(lines)} → {len(filtered_lines)} 줄")
        return '\n'.join(filtered_lines)
    
    def _fix_particle_spacing(self, content: str) -> str:
        """
        ✅ Phase 5.7.7: 조사/어미 띄어쓰기 복원
        
        패턴:
        - "기함에 하는" → "기하게 하는"
        - "정함이 없는" → "정함이 없는" (이미 올바름)
        - "하는것을" → "하는 것을"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            띄어쓰기 복원된 텍스트
        """
        # 1) 용언 + 조사 패턴 ("기함에" → "기하게")
        content = re.sub(r'([가-힣]+)함에\s+([가-힣]+)는', r'\1하게 \2는', content)
        content = re.sub(r'([가-힣]+)함에\s+([가-힣]+)다', r'\1하게 \2다', content)
        
        # 2) 명사 + 조사 패턴 ("것을말한다" → "것을 말한다")
        content = re.sub(r'([가-힣]+)을([가-힣]{2,}다)', r'\1을 \2', content)
        content = re.sub(r'([가-힣]+)를([가-힣]{2,}다)', r'\1를 \2', content)
        content = re.sub(r'([가-힣]+)이([가-힣]{2,}다)', r'\1이 \2', content)
        content = re.sub(r'([가-힣]+)가([가-힣]{2,}다)', r'\1가 \2', content)
        
        # 3) 의존명사 띄어쓰기 ("하는것" → "하는 것")
        content = re.sub(r'([가-힣]+)는것([을를이가])', r'\1는 것\2', content)
        content = re.sub(r'([가-힣]+)한것([을를이가])', r'\1한 것\2', content)
        
        logger.debug("      조사/어미 띄어쓰기 복원 완료")
        return content
    
    def _normalize_numbered_lists(self, content: str) -> str:
        """
        Phase 5.6.2: 숫자 목록 결속 강화 (헤더 보호)
        
        패턴:
        - "1.\n직원은" → "1. 직원은"
        - "1.\n\n직원은" → "1. 직원은"
        
        보호:
        - 다음 줄이 #으로 시작하면 결속 안 함 (헤더)
        - 다음 줄이 ---로 시작하면 결속 안 함 (구분선)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        lines = content.split('\n')
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 숫자 목록 패턴 (1. 2. 3. ...)
            if re.match(r'^\d+\.\s*$', line.strip()):
                # 다음 줄 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # 헤더/구분선이면 결속 안 함
                    if next_line.startswith('#') or next_line.startswith('---') or next_line.startswith('```'):
                        result.append(line)
                    elif next_line:  # 평문이면 결속
                        result.append(line.strip() + ' ' + next_line)
                        i += 1  # 다음 줄 스킵
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
            
            i += 1
        
        logger.debug("      숫자 목록 결속 강화 완료")
        return '\n'.join(result)
    
    def _normalize_korean_lists(self, content: str) -> str:
        """
        Phase 5.6.2: 한글 순서 결속 (범위 수정)
        
        패턴:
        - "가.\n내용" → "가. 내용"
        - "나.\n내용" → "나. 내용"
        
        ✅ 수정: [가-하] → [가-힣] (전체 한글)
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        lines = content.split('\n')
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 한글 순서 패턴 (가. 나. 다. ...) - 전체 범위
            if re.match(r'^[가-힣]\.\s*$', line.strip()):
                # 다음 줄 확인
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # 헤더/구분선이면 결속 안 함
                    if next_line.startswith('#') or next_line.startswith('---') or next_line.startswith('```'):
                        result.append(line)
                    elif next_line:  # 평문이면 결속
                        result.append(line.strip() + ' ' + next_line)
                        i += 1  # 다음 줄 스킵
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
            
            i += 1
        
        logger.debug("      한글 순서 결속 완료 (전체 범위)")
        return '\n'.join(result)
    
    def _normalize_parenthesized_numbers(self, content: str) -> str:
        """
        괄호 번호 결속
        
        패턴:
        - "(1)\n내용" → "(1) 내용"
        - "①\n내용" → "① 내용"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # (1) (2) (3) 형태
        content = re.sub(r'(\(\d+\))\s*\n{1,3}\s*', r'\1 ', content)
        
        # ① ② ③ 형태
        content = re.sub(r'([①-⑳])\s*\n{1,3}\s*', r'\1 ', content)
        
        logger.debug("      괄호 번호 결속 완료")
        return content
    
    def _normalize_article_numbers(self, content: str) -> str:
        """
        Phase 5.6.2: 조문 번호 결속 (보수적 적용)
        
        패턴:
        - "제1조\n(목적)" → "제1조 (목적)"
        - "제1항\n내용" → "제1항 내용"
        
        Args:
            content: 원본 텍스트
        
        Returns:
            결속된 텍스트
        """
        # 제○조 + 괄호 제목 (헤더 마커 없을 때만)
        content = re.sub(r'(제\s?\d+조)\s*\n+\s*(\([^)]+\))(?!\s*\n#)', r'\1 \2', content)
        
        # 제○항 + 내용
        content = re.sub(r'(제\s?\d+항)\s*\n+\s*(?!#)', r'\1 ', content)
        
        # 제○호 + 내용
        content = re.sub(r'(제\s?\d+호)\s*\n+\s*(?!#)', r'\1 ', content)
        
        logger.debug("      조문 번호 결속 완료 (보수적)")
        return content
    
    def _clean_whitespace(self, content: str) -> str:
        """
        Phase 5.6.2: 불필요한 공백 정리 (보수적)
        
        패턴:
        - 연속 공백 → 단일 공백
        - 3개 이상 줄바꿈 → 2개 줄바꿈
        
        보호:
        - 코드블럭 (```) 내부 보존
        - 헤더 앞뒤 공백 보존
        
        Args:
            content: 원본 텍스트
        
        Returns:
            정리된 텍스트
        """
        # 연속 공백 → 단일 공백 (줄바꿈 제외)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 3개 이상 줄바꿈 → 2개 줄바꿈
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 줄 끝 공백 제거
        content = re.sub(r' +\n', '\n', content)
        
        logger.debug("      공백 정리 완료 (보수적)")
        return content
    
    def get_stats(self, original: str, normalized: str) -> Dict[str, Any]:
        """
        정규화 통계
        
        Args:
            original: 원본 텍스트
            normalized: 정규화된 텍스트
        
        Returns:
            통계 정보
        """
        return {
            'original_length': len(original),
            'normalized_length': len(normalized),
            'reduction': len(original) - len(normalized),
            'reduction_percent': (len(original) - len(normalized)) / max(1, len(original)) * 100
        }
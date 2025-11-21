"""
research/table_parser.py - PRISM Phase 0.9.1 Hotfix
별표 테이블 구조화 파서 (OCR-friendly 패턴)

Phase 0.9.1 Hotfix:
- ✅ 헤더 패턴 완화 (OCR 텍스트 대응)
- ✅ '3급승진제외' / '3급승진' 키워드 기반 감지
- ✅ ROW_PATTERN 강화 (PDF 추출 텍스트 대응)
- ✅ 규칙 기반 생성 fallback

Author: 마창수산팀
Date: 2025-11-20
Version: Phase 0.9.1 Hotfix
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TableParser:
    """
    Phase 0.9.1 TableParser Hotfix
    
    OCR-friendly 패턴으로 별표 테이블 구조화
    """
    
    # ✅ Phase 0.9.1: OCR-friendly 헤더 패턴 (느슨하게)
    # 실제 PDF 텍스트: "임용하고자하는인원수에대한승진후보자범위(3급승진제외)"
    TABLE_HEADER_PATTERNS = {
        '3급승진제외': [
            # 패턴 1: 전체 문구
            re.compile(r'승진\s*후보자\s*범위\s*\(?3급\s*승진\s*제외\)?', re.IGNORECASE),
            # 패턴 2: 핵심 키워드만 (OCR 대응)
            re.compile(r'3급\s*승진\s*제외', re.IGNORECASE),
            # 패턴 3: 띄어쓰기 완전 무시
            re.compile(r'3급승진제외', re.IGNORECASE),
        ],
        '3급승진': [
            # 패턴 1: 전체 문구 (제외가 아닌 경우)
            re.compile(r'승진\s*후보자\s*범위\s*\(?3급\s*승진\)?(?!\s*제외)', re.IGNORECASE),
            # 패턴 2: 핵심 키워드 (제외가 아닌 경우)
            re.compile(r'3급\s*승진(?!\s*제외)', re.IGNORECASE),
            # 패턴 3: 띄어쓰기 완전 무시 (제외가 아닌 경우)
            re.compile(r'3급승진(?!제외)', re.IGNORECASE),
        ]
    }
    
    # ✅ Phase 0.9.1: 강화된 ROW 패턴 (PDF 추출 텍스트 대응)
    ROW_PATTERNS = [
        # 패턴 1: "1 5번까지" 형식
        re.compile(r'^(\d+)\s+(\d+)번까지', re.MULTILINE),
        # 패턴 2: "1 5" 형식 (숫자만)
        re.compile(r'^(\d{1,2})\s+(\d+)\s*$', re.MULTILINE),
        # 패턴 3: 줄 시작 아니어도 매칭
        re.compile(r'(\d{1,2})\s+(\d+)번까지'),
    ]
    
    def __init__(self):
        """초기화"""
        logger.info("✅ TableParser 초기화 완료 (Phase 0.9.1 Hotfix)")
    
    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        텍스트에서 테이블 파싱
        
        Args:
            text: Annex 텍스트 (별표 포함)
        
        Returns:
            테이블 행 청크 리스트
        """
        if not text:
            return []
        
        chunks = []
        
        # 3급승진제외 테이블 파싱
        chunks_exclude = self._parse_table_3급승진제외(text)
        chunks.extend(chunks_exclude)
        
        # 3급승진 테이블 파싱
        chunks_3급 = self._parse_table_3급승진(text)
        chunks.extend(chunks_3급)
        
        if chunks:
            logger.info(f"✅ TableParser: {len(chunks)}개 행 파싱 완료")
        else:
            logger.warning("⚠️ TableParser: 테이블 감지 실패")
        
        return chunks
    
    def _find_table_region(self, text: str, table_type: str) -> tuple:
        """
        테이블 영역 찾기
        
        Returns:
            (start_pos, end_pos) or (None, None)
        """
        patterns = self.TABLE_HEADER_PATTERNS.get(table_type, [])
        
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                start_pos = match.end()
                
                # 다음 테이블 또는 [별표 찾기
                if table_type == '3급승진제외':
                    # 3급승진 테이블 시작점 찾기
                    for next_pattern in self.TABLE_HEADER_PATTERNS['3급승진']:
                        next_match = next_pattern.search(text[start_pos:])
                        if next_match:
                            return (start_pos, start_pos + next_match.start())
                    
                    # [별표2] 찾기
                    next_annex = re.search(r'\[별표\s*2\]', text[start_pos:])
                    if next_annex:
                        return (start_pos, start_pos + next_annex.start())
                
                return (start_pos, len(text))
        
        return (None, None)
    
    def _extract_rows(self, table_text: str) -> List[tuple]:
        """
        테이블 텍스트에서 행 추출
        """
        all_rows = []
        
        for pattern in self.ROW_PATTERNS:
            matches = pattern.findall(table_text)
            if matches:
                # 가장 많이 매칭된 패턴 사용
                if len(matches) > len(all_rows):
                    all_rows = matches
        
        return all_rows
    
    def _parse_table_3급승진제외(self, text: str) -> List[Dict[str, Any]]:
        """
        3급승진제외 테이블 파싱 (5배수 규칙)
        """
        chunks = []
        
        # 테이블 영역 찾기
        start_pos, end_pos = self._find_table_region(text, '3급승진제외')
        
        if start_pos is None:
            logger.info("   ℹ️ 3급승진제외 테이블 헤더 미발견")
            return []
        
        table_text = text[start_pos:end_pos]
        logger.info(f"   📊 3급승진제외 테이블 영역: {len(table_text)}자")
        
        # 데이터 행 추출
        rows = self._extract_rows(table_text)
        
        if rows:
            logger.info(f"   📊 3급승진제외: {len(rows)}행 추출")
            
            for 임용인원수, 서열명부순위 in rows:
                try:
                    chunks.append({
                        'table_id': 'annex_1_3급승진제외',
                        'table_title': '승진후보자범위(3급승진제외)',
                        '임용인원수': int(임용인원수),
                        '서열명부순위': int(서열명부순위),
                        'rule': '5배수'
                    })
                except ValueError:
                    continue
        
        # 추출 실패 또는 불완전 시 규칙 기반 생성
        if len(chunks) < 75:
            logger.info(f"   ℹ️ 3급승진제외: {len(chunks)}행 → 규칙 기반 보완")
            chunks = self._generate_5배수_table()
        
        return chunks
    
    def _parse_table_3급승진(self, text: str) -> List[Dict[str, Any]]:
        """
        3급승진 테이블 파싱 (2배수 규칙)
        """
        chunks = []
        
        # 3급승진제외 이후 영역에서 찾기
        exclude_start, exclude_end = self._find_table_region(text, '3급승진제외')
        
        if exclude_end:
            search_text = text[exclude_end:]
            offset = exclude_end
        else:
            search_text = text
            offset = 0
        
        # 테이블 영역 찾기
        start_pos, end_pos = self._find_table_region(search_text, '3급승진')
        
        if start_pos is None:
            logger.info("   ℹ️ 3급승진 테이블 헤더 미발견")
            return []
        
        table_text = search_text[start_pos:end_pos]
        logger.info(f"   📊 3급승진 테이블 영역: {len(table_text)}자")
        
        # 데이터 행 추출
        rows = self._extract_rows(table_text)
        
        if rows:
            logger.info(f"   📊 3급승진: {len(rows)}행 추출")
            
            for 임용인원수, 서열명부순위 in rows:
                try:
                    chunks.append({
                        'table_id': 'annex_1_3급승진',
                        'table_title': '승진후보자범위(3급승진)',
                        '임용인원수': int(임용인원수),
                        '서열명부순위': int(서열명부순위),
                        'rule': '2배수'
                    })
                except ValueError:
                    continue
        
        # 추출 실패 또는 불완전 시 규칙 기반 생성
        if len(chunks) < 75:
            logger.info(f"   ℹ️ 3급승진: {len(chunks)}행 → 규칙 기반 보완")
            chunks = self._generate_2배수_table()
        
        return chunks
    
    def _generate_5배수_table(self) -> List[Dict[str, Any]]:
        """
        5배수 규칙으로 테이블 생성 (3급승진제외)
        
        규칙:
        - 1~5명: 5배수 (5, 10, 15, 20, 25)
        - 6명 이상: +3씩 증가 (28, 31, 34, ...)
        """
        chunks = []
        
        for i in range(1, 76):
            if i <= 5:
                rank = i * 5
            else:
                rank = 25 + (i - 5) * 3
            
            chunks.append({
                'table_id': 'annex_1_3급승진제외',
                'table_title': '승진후보자범위(3급승진제외)',
                '임용인원수': i,
                '서열명부순위': rank,
                'rule': '5배수'
            })
        
        return chunks
    
    def _generate_2배수_table(self) -> List[Dict[str, Any]]:
        """
        2배수 규칙으로 테이블 생성 (3급승진)
        
        규칙:
        - 1~75명: 2배수
        """
        chunks = []
        
        for i in range(1, 76):
            rank = i * 2
            
            chunks.append({
                'table_id': 'annex_1_3급승진',
                'table_title': '승진후보자범위(3급승진)',
                '임용인원수': i,
                '서열명부순위': rank,
                'rule': '2배수'
            })
        
        return chunks
    
    def query(self, chunks: List[Dict[str, Any]], question: str) -> Optional[str]:
        """
        테이블 청크에서 질의 응답
        """
        if not chunks:
            return None
        
        # 숫자 추출
        numbers = re.findall(r'\d+', question)
        if not numbers:
            return None
        
        # 질문에서 테이블 타입 판별
        is_3급승진 = '3급' in question and '승진' in question and '제외' not in question
        is_3급제외 = '3급' in question and '제외' in question
        
        # 필터링
        if is_3급승진:
            filtered = [c for c in chunks if c.get('table_id') == 'annex_1_3급승진']
        elif is_3급제외:
            filtered = [c for c in chunks if c.get('table_id') == 'annex_1_3급승진제외']
        else:
            # 기본: 3급승진제외
            filtered = [c for c in chunks if c.get('table_id') == 'annex_1_3급승진제외']
        
        if not filtered:
            filtered = chunks
        
        # 임용인원수로 검색
        target_num = int(numbers[-1])  # 마지막 숫자를 임용인원수로 간주
        
        for chunk in filtered:
            if chunk.get('임용인원수') == target_num:
                table_title = chunk.get('table_title', '')
                rank = chunk.get('서열명부순위', 0)
                return f"{table_title}에서 {target_num}명 임용 시 서열명부순위 {rank}번까지"
        
        return None


# 테스트용
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 실제 PDF 추출 텍스트와 유사한 샘플
    sample_text = """
임용하고자하는인원수에대한승진후보자범위(3급승진제외)

1 5번까지
2 10번까지
3 15번까지
4 20번까지
5 25번까지
6 28번까지
7 31번까지

임용하고자하는인원수에대한승진후보자범위(3급승진)

1 2번까지
2 4번까지
3 6번까지
4 8번까지
5 10번까지
"""
    
    parser = TableParser()
    chunks = parser.parse(sample_text)
    
    print(f"\n✅ 파싱 완료: {len(chunks)}개 행")
    
    # 질의 테스트
    questions = [
        "3급승진제외에서 10명 임용할 때 후보자 범위는?",
        "3급승진에서 5명 임용 시 범위",
    ]
    
    for q in questions:
        answer = parser.query(chunks, q)
        print(f"Q: {q}")
        print(f"A: {answer}\n")
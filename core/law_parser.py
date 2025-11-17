"""
core/law_parser.py - Phase 0.8 통합
Annex 서브청킹 통합

수정 사항:
- to_chunks() 함수에 AnnexSubChunker 통합
- Annex 청크를 서브청크로 분해
"""

# 기존 import 유지
from core.annex_subchunker import AnnexSubChunker, validate_subchunks

class LawParser:
    # ... (기존 코드 유지)
    
    def to_chunks(self, parsed_result: dict) -> list:
        """
        파싱 결과 → RAG 청크 변환
        
        ✅ Phase 0.8: Annex 서브청킹 통합
        """
        chunks = []
        
        # Title
        if parsed_result['document_title']:
            chunks.append({
                'content': parsed_result['document_title'],
                'metadata': {
                    'type': 'title',
                    'boundary': 'document_title',
                    'title': parsed_result['document_title'],
                    'char_count': len(parsed_result['document_title']),
                    'section_order': -3
                }
            })
        
        # 개정이력
        if parsed_result['amendment_history']:
            for i, amendment in enumerate(parsed_result['amendment_history']):
                chunks.append({
                    'content': amendment,
                    'metadata': {
                        'type': 'amendment_history',
                        'boundary': 'header',
                        'title': '개정 이력',
                        'char_count': len(amendment),
                        'section_order': -2 - i
                    }
                })
        
        # 기본정신
        if parsed_result['basic_spirit']:
            chunks.append({
                'content': parsed_result['basic_spirit'],
                'metadata': {
                    'type': 'basic',
                    'boundary': 'header',
                    'title': '기본정신',
                    'char_count': len(parsed_result['basic_spirit']),
                    'section_order': -1
                }
            })
        
        # 장
        for chapter in parsed_result['chapters']:
            chunks.append({
                'content': f"{chapter.number} {chapter.title}",
                'metadata': {
                    'type': 'chapter',
                    'boundary': 'chapter',
                    'chapter_number': chapter.number,
                    'chapter_title': chapter.title,
                    'char_count': len(chapter.number) + len(chapter.title),
                    'section_order': chapter.section_order
                }
            })
        
        # 조문
        for article in parsed_result['articles']:
            content = f"{article.number}({article.title})\n{article.body}"
            chunks.append({
                'content': content,
                'metadata': {
                    'type': 'article',
                    'boundary': 'article',
                    'article_number': article.number,
                    'article_title': article.title,
                    'chapter_number': article.chapter_number,
                    'char_count': len(content),
                    'section_order': article.section_order
                }
            })
        
        # ✅ Phase 0.8: Annex 서브청킹
        if parsed_result.get('annex_content'):
            logger.info("✅ Phase 0.8: Annex 서브청킹 시작")
            
            subchunker = AnnexSubChunker()
            annex_text = parsed_result['annex_content']
            
            # 서브청크 생성
            sub_chunks = subchunker.chunk(annex_text)
            
            # 검증
            validation = validate_subchunks(sub_chunks, len(annex_text))
            
            if validation['is_valid']:
                logger.info(f"✅ Annex 서브청킹 성공: {validation['chunk_count']}개")
                logger.info(f"   📊 손실률: {validation['loss_rate']:.2%}")
                logger.info(f"   📊 타입: {validation['type_counts']}")
                
                # 서브청크 → 표준 청크 포맷 변환
                for sub in sub_chunks:
                    chunks.append({
                        'content': sub.content,
                        'metadata': {
                            'type': f"annex_{sub.section_type}",
                            'boundary': 'annex',
                            'section_id': sub.section_id,
                            'section_type': sub.section_type,
                            'char_count': sub.char_count,
                            'section_order': sub.order,
                            **sub.metadata
                        }
                    })
            else:
                logger.warning("⚠️ Annex 서브청킹 검증 실패 - Fallback to 기존 로직")
                # Fallback: 기존 단일 청크
                chunks.append({
                    'content': annex_text,
                    'metadata': {
                        'type': 'annex',
                        'boundary': 'annex',
                        'title': parsed_result.get('annex_title', ''),
                        'annex_no': parsed_result.get('annex_no'),
                        'related_article': parsed_result.get('related_article'),
                        'char_count': len(annex_text),
                        'section_order': 0
                    }
                })
        
        logger.info(f"✅ 청크 변환 완료 (Phase 0.8): {len(chunks)}개")
        
        # 타입별 통계
        type_counts = {}
        for chunk in chunks:
            ctype = chunk['metadata']['type']
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
        
        for ctype, count in sorted(type_counts.items()):
            logger.info(f"   - {ctype}: {count}개")
        
        return chunks
    
    # ... (나머지 코드 유지)
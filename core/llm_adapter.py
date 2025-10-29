"""
core/llm_adapter.py
PRISM Phase 5.7.0 - LLM Adapter v1.0

목표: 법령 Tree → RAG 프롬프트 변환

플로우:
1. Tree를 LLM이 이해할 수 있는 형식으로 변환
2. 계층별 Top-k 검색 지원
3. 컨텍스트 최적화
4. 프롬프트 템플릿 적용

Author: 최동현 (Frontend Lead) + 박준호 (AI/ML Lead)
Date: 2025-10-27
Version: 5.7.0 v1.0
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    Phase 5.7.0 LLM Adapter
    
    역할:
    - Tree를 LLM 프롬프트로 변환
    - 계층별 검색 지원
    - RAG 컨텍스트 최적화
    
    예시:
    Input: Document Tree
    Output: "제1조(목적) ① 항목1 가. 세부1 나. 세부2"
    """
    
    def __init__(self):
        """초기화"""
        logger.info("✅ LLMAdapter v5.7.0 초기화 완료")
    
    def to_prompt(
        self,
        document: Dict[str, Any],
        query: Optional[str] = None,
        max_tokens: int = 4000
    ) -> str:
        """
        Document Tree를 LLM 프롬프트로 변환
        
        Args:
            document: TreeBuilder + HierarchicalParser 출력
            query: 사용자 질의 (선택)
            max_tokens: 최대 토큰 수
        
        Returns:
            LLM 프롬프트 (Markdown)
        """
        logger.info("🤖 LLMAdapter to_prompt 시작")
        
        tree = document['document']['tree']
        metadata = document['document']['metadata']
        
        # Step 1: 문서 헤더
        header = self._build_header(metadata)
        
        # Step 2: 조문 변환
        articles_md = []
        for article in tree:
            article_md = self._article_to_markdown(article)
            articles_md.append(article_md)
        
        # Step 3: 조합
        prompt = f"{header}\n\n{''.join(articles_md)}"
        
        # Step 4: 토큰 제한 (간단한 추정)
        if len(prompt) > max_tokens * 4:  # 1 token ≈ 4 chars
            prompt = prompt[:max_tokens * 4] + "\n\n... (이하 생략)"
            logger.warning(f"   ⚠️ 프롬프트 truncated (max_tokens={max_tokens})")
        
        logger.info(f"   ✅ 프롬프트 생성 완료 ({len(prompt)} chars)")
        
        return prompt
    
    def to_hierarchical_context(
        self,
        document: Dict[str, Any],
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        계층별 Top-k 컨텍스트 생성
        
        Args:
            document: Tree
            query: 사용자 질의
            top_k: 반환할 최대 개수
        
        Returns:
            [
              {
                'level': 'article' | 'clause' | 'item',
                'text': str,
                'score': float,
                'metadata': dict
              }
            ]
        """
        logger.info(f"🔍 계층별 검색: query='{query}', top_k={top_k}")
        
        tree = document['document']['tree']
        
        # Step 1: 모든 노드 수집
        nodes = []
        
        for article in tree:
            # Article 레벨
            nodes.append({
                'level': 'article',
                'text': f"{article['article_no']} {article.get('article_title', '')} {article.get('content', '')}",
                'metadata': article['metadata'],
                'article_no': article['article_no']
            })
            
            # Clause 레벨
            for child in article.get('children', []):
                if isinstance(child, dict) and child.get('level') == 'clause':
                    nodes.append({
                        'level': 'clause',
                        'text': f"{child['clause_no']} {child.get('content', '')}",
                        'metadata': child['metadata'],
                        'article_no': article['article_no'],
                        'clause_no': child['clause_no']
                    })
                    
                    # Item 레벨
                    for item in child.get('children', []):
                        if isinstance(item, dict) and item.get('level') == 'item':
                            nodes.append({
                                'level': 'item',
                                'text': f"{item['item_no']} {item.get('content', '')}",
                                'metadata': item['metadata'],
                                'article_no': article['article_no'],
                                'clause_no': child['clause_no'],
                                'item_no': item['item_no']
                            })
        
        # Step 2: 간단한 키워드 매칭 (실제로는 임베딩 유사도 사용)
        scored_nodes = []
        query_lower = query.lower()
        
        for node in nodes:
            text_lower = node['text'].lower()
            
            # 간단한 스코어: 쿼리 키워드 포함 개수
            score = sum(1 for word in query_lower.split() if word in text_lower)
            
            if score > 0:
                scored_nodes.append({
                    **node,
                    'score': score
                })
        
        # Step 3: 정렬 및 Top-k
        scored_nodes.sort(key=lambda x: x['score'], reverse=True)
        
        top_nodes = scored_nodes[:top_k]
        
        logger.info(f"   ✅ {len(top_nodes)}개 노드 반환 (총 {len(scored_nodes)}개 매칭)")
        
        return top_nodes
    
    def _build_header(self, metadata: Dict[str, Any]) -> str:
        """
        문서 헤더 생성
        
        Args:
            metadata: DocumentMetadata
        
        Returns:
            Markdown 헤더
        """
        title = metadata.get('title', '(제목 없음)')
        enacted_date = metadata.get('enacted_date', '')
        last_amended = metadata.get('last_amended_date', '')
        
        header = f"# {title}\n\n"
        
        if enacted_date:
            header += f"**제정일:** {enacted_date}\n"
        
        if last_amended:
            header += f"**최종개정일:** {last_amended}\n"
        
        return header
    
    def _article_to_markdown(self, article: Dict[str, Any]) -> str:
        """
        Article 노드를 Markdown으로 변환
        
        Args:
            article: Article 노드
        
        Returns:
            Markdown 텍스트
        """
        article_no = article.get('article_no', '')
        article_title = article.get('article_title', '')
        content = article.get('content', '')
        
        # 제목 라인
        if article_title:
            md = f"### {article_no}{article_title}\n\n"
        else:
            md = f"### {article_no}\n\n"
        
        # 본문
        if content:
            md += f"{content}\n\n"
        
        # 하위 항
        for child in article.get('children', []):
            if isinstance(child, dict) and child.get('level') == 'clause':
                md += self._clause_to_markdown(child)
            elif isinstance(child, str):
                md += f"{child}\n\n"
        
        return md
    
    def _clause_to_markdown(self, clause: Dict[str, Any]) -> str:
        """
        Clause 노드를 Markdown으로 변환
        
        Args:
            clause: Clause 노드
        
        Returns:
            Markdown 텍스트
        """
        clause_no = clause.get('clause_no', '')
        content = clause.get('content', '')
        
        md = f"{clause_no} {content}\n\n"
        
        # 하위 호
        for child in clause.get('children', []):
            if isinstance(child, dict) and child.get('level') == 'item':
                md += self._item_to_markdown(child)
            elif isinstance(child, str):
                md += f"  {child}\n\n"
        
        return md
    
    def _item_to_markdown(self, item: Dict[str, Any]) -> str:
        """
        Item 노드를 Markdown으로 변환
        
        Args:
            item: Item 노드
        
        Returns:
            Markdown 텍스트
        """
        item_no = item.get('item_no', '')
        content = item.get('content', '')
        
        md = f"  {item_no} {content}\n\n"
        
        return md
    
    def to_json_export(self, document: Dict[str, Any]) -> str:
        """
        Document를 JSON 문자열로 변환 (저장용)
        
        Args:
            document: Tree + Metrics
        
        Returns:
            JSON 문자열
        """
        import json
        
        return json.dumps(document, ensure_ascii=False, indent=2)

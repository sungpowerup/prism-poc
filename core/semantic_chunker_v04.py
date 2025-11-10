"""
Semantic Chunker V0.4
Phase 0.4.0 "Quality Assurance Release"

Enhanced semantic chunking with mandatory non-article section handling
Creates independent chunks for critical sections (기본정신, 개정이력)

Author: 박준호 (AI/ML Lead)
Date: 2025-11-09
"""

from typing import List, Dict, Any
import re
from datetime import datetime

# Version check
from .version import PRISM_VERSION, check_version
VERSION = "0.4.0"
check_version(__name__, VERSION)

class SemanticChunkerV04:
    """
    Enhanced semantic chunker for Phase 0.4
    Handles both article-based and non-article sections
    """
    
    # ============================================
    # Chunking Strategy
    # ============================================
    
    CHUNKING_RULES = """
📋 CHUNKING STRATEGY (Phase 0.4)

🎯 Priority Order:
1. 개정이력 (Revision History) → Independent chunk
2. 기본정신 (Basic Principles) → Independent chunk
3. 제1조, 제2조, ... (Articles) → One chunk per article
4. 부칙 (Supplementary Provisions) → Independent chunk

⚠️ CRITICAL: Non-article sections MUST be chunked separately
- Each section gets its own chunk with proper metadata
- Do NOT merge with articles
- Do NOT skip these sections
"""
    
    def __init__(
        self,
        min_chunk_size: int = 300,
        max_chunk_size: int = 2000,
        overlap: int = 100
    ):
        """
        Initialize semantic chunker
        
        Args:
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        # Patterns
        self.article_pattern = re.compile(r'###\s*제\s*(\d+)\s*조')
        self.chapter_pattern = re.compile(r'##\s*제\s*(\d+)\s*장')
    
    def chunk(self, markdown: str, doc_type: str = "regulation") -> List[Dict[str, Any]]:
        """
        Create semantic chunks from markdown
        
        Args:
            markdown: Preprocessed markdown content
            doc_type: Document type
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        # 1. Extract revision history (highest priority)
        revision_chunk = self._extract_revision_history(markdown)
        if revision_chunk:
            chunks.append(revision_chunk)
        
        # 2. Extract basic principles
        principles_chunk = self._extract_basic_principles(markdown)
        if principles_chunk:
            chunks.append(principles_chunk)
        
        # 3. Extract articles
        article_chunks = self._extract_articles(markdown)
        chunks.extend(article_chunks)
        
        # 4. Extract supplementary provisions
        supplement_chunk = self._extract_supplementary(markdown)
        if supplement_chunk:
            chunks.append(supplement_chunk)
        
        # 5. Add metadata and finalize
        for i, chunk in enumerate(chunks, 1):
            chunk['id'] = f"chunk_{i:03d}"
            chunk['sequence'] = i
            chunk['total_chunks'] = len(chunks)
        
        return chunks
    
    def _extract_revision_history(self, markdown: str) -> Dict[str, Any] | None:
        """
        Extract revision history as independent chunk
        
        Returns:
            Chunk dict or None if not found
        """
        # Pattern: ## 개정이력 or | 개정일자 |
        patterns = [
            r'##\s*개정\s*이력.*?\n(.*?)(?=\n##|\Z)',
            r'\|\s*개정일자\s*\|.*?\n((?:\|.*?\n)+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(0).strip()
                
                # Parse table if present
                revision_count = len(re.findall(r'\|\s*\d{4}', content))
                
                return {
                    'content': content,
                    'metadata': {
                        'type': 'revision_history',
                        'section': '개정이력',
                        'article_no': None,
                        'char_count': len(content),
                        'revision_count': revision_count
                    }
                }
        
        return None
    
    def _extract_basic_principles(self, markdown: str) -> Dict[str, Any] | None:
        """
        Extract basic principles as independent chunk
        
        Returns:
            Chunk dict or None if not found
        """
        # Pattern: ## 기본정신 or ## 기본 정신
        pattern = r'##\s*기본\s*정신.*?\n(.*?)(?=\n##|\n###|\Z)'
        match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
        
        if match:
            content = match.group(0).strip()
            
            return {
                'content': content,
                'metadata': {
                    'type': 'basic_principles',
                    'section': '기본정신',
                    'article_no': None,
                    'char_count': len(content)
                }
            }
        
        return None
    
    def _extract_articles(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract articles as individual chunks
        
        Returns:
            List of article chunks
        """
        chunks = []
        
        # Split by article headers
        article_splits = re.split(r'(###\s*제\s*\d+\s*조.*?\n)', markdown)
        
        current_article = None
        current_content = []
        
        for i, segment in enumerate(article_splits):
            # Check if this is an article header
            article_match = self.article_pattern.match(segment.strip())
            
            if article_match:
                # Save previous article if exists
                if current_article and current_content:
                    chunks.append(self._create_article_chunk(
                        current_article,
                        ''.join(current_content)
                    ))
                
                # Start new article
                current_article = segment.strip()
                current_content = [segment]
            else:
                # Add to current article content
                if current_article:
                    current_content.append(segment)
        
        # Save last article
        if current_article and current_content:
            chunks.append(self._create_article_chunk(
                current_article,
                ''.join(current_content)
            ))
        
        return chunks
    
    def _create_article_chunk(self, header: str, content: str) -> Dict[str, Any]:
        """
        Create chunk from article header and content
        
        Args:
            header: Article header (e.g., "### 제1조(목적)")
            content: Full article content
        
        Returns:
            Chunk dictionary
        """
        # Extract article number
        article_match = re.search(r'제\s*(\d+)\s*조', header)
        article_no = article_match.group(1) if article_match else None
        
        # Extract article title
        title_match = re.search(r'제\s*\d+\s*조\s*\(([^)]+)\)', header)
        article_title = title_match.group(1) if title_match else None
        
        # Clean content
        content = content.strip()
        
        # Count sub-items
        item_count = len(re.findall(r'^\d+\.', content, re.MULTILINE))
        subitem_count = len(re.findall(r'^\s+[가-힣]\.', content, re.MULTILINE))
        
        return {
            'content': content,
            'metadata': {
                'type': 'article',
                'section': f'제{article_no}조',
                'article_no': article_no,
                'article_title': article_title,
                'char_count': len(content),
                'item_count': item_count,
                'subitem_count': subitem_count
            }
        }
    
    def _extract_supplementary(self, markdown: str) -> Dict[str, Any] | None:
        """
        Extract supplementary provisions
        
        Returns:
            Chunk dict or None if not found
        """
        pattern = r'##\s*부\s*칙.*?\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
        
        if match:
            content = match.group(0).strip()
            
            return {
                'content': content,
                'metadata': {
                    'type': 'supplementary',
                    'section': '부칙',
                    'article_no': None,
                    'char_count': len(content)
                }
            }
        
        return None
    
    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate chunking quality
        
        Args:
            chunks: List of chunks
        
        Returns:
            Validation report
        """
        issues = []
        
        # Check for critical chunks
        chunk_types = [c['metadata']['type'] for c in chunks]
        
        if 'basic_principles' not in chunk_types:
            issues.append({
                'severity': 'critical',
                'message': 'Missing "기본정신" chunk'
            })
        
        if 'revision_history' not in chunk_types:
            issues.append({
                'severity': 'major',
                'message': 'Missing "개정이력" chunk'
            })
        
        # Check chunk sizes
        for chunk in chunks:
            size = chunk['metadata']['char_count']
            if size < self.min_chunk_size:
                issues.append({
                    'severity': 'minor',
                    'message': f"Chunk {chunk.get('id', '?')} too small ({size} chars)"
                })
        
        # Calculate score
        critical_count = len([i for i in issues if i['severity'] == 'critical'])
        major_count = len([i for i in issues if i['severity'] == 'major'])
        
        score = 100 - (critical_count * 30) - (major_count * 10)
        
        return {
            'valid': len(issues) == 0,
            'score': max(0, score),
            'total_chunks': len(chunks),
            'chunk_types': chunk_types,
            'issues': issues
        }


# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    sample_markdown = """
## 개정이력

| 개정일자 | 개정사유 | 비고 |
|---------|---------|------|
| 2024.01.01 | 최초 제정 | - |

## 기본정신

모든 직원은 평등하게 대우받는다.

### 제1조(목적)
이 규정은 직원의 인사관리에 관한 사항을 정함을 목적으로 한다.

### 제2조(적용범위)
이 규정은 모든 직원에게 적용한다.
"""
    
    chunker = SemanticChunkerV04()
    chunks = chunker.chunk(sample_markdown)
    
    print("=" * 60)
    print(f"Total Chunks: {len(chunks)}")
    print("=" * 60)
    
    for chunk in chunks:
        print(f"\n[{chunk['id']}] {chunk['metadata']['type']}")
        print(f"Section: {chunk['metadata']['section']}")
        print(f"Size: {chunk['metadata']['char_count']} chars")
        print(f"Content: {chunk['content'][:100]}...")
    
    print("\n" + "=" * 60)
    print("Validation Report:")
    print("=" * 60)
    validation = chunker.validate_chunks(chunks)
    print(f"Valid: {validation['valid']}")
    print(f"Score: {validation['score']}/100")
    print(f"Issues: {len(validation['issues'])}")

"""
Semantic Chunker v0.4
Phase 0.4.0 "Quality Assurance Release"

Enhanced chunking with non-article section support
Treats "기본정신" and other sections as first-class chunks

Author: 박준호 (AI/ML Lead)
Date: 2025-11-10
Version: 0.4.0
"""

from typing import List, Dict, Any, Optional
import re
import logging

# Version check
try:
    from .version import PRISM_VERSION, check_version
    VERSION = "0.4.0"
    check_version(__name__, VERSION)
except ImportError:
    VERSION = "0.4.0"
    print(f"⚠️ Version module not found, using VERSION={VERSION}")

logger = logging.getLogger(__name__)

# ============================================
# Semantic Chunker v0.4
# ============================================

class SemanticChunker:
    """
    Phase 0.4.0 Semantic Chunker
    
    Key improvements:
    - Non-article sections (기본정신 etc.) as independent chunks
    - Better boundary detection
    - Korean sentence boundary preservation
    """
    
    # Article patterns
    ARTICLE_PATTERNS = [
        r'^###?\s*제\s*(\d+)조(?:의\s*(\d+))?\s*\(([^)]+)\)',  # ### 제1조(목적)
        r'^제\s*(\d+)조(?:의\s*(\d+))?\s*\(([^)]+)\)',        # 제1조(목적)
        r'^###?\s*제\s*(\d+)조(?:의\s*(\d+))?[^(]',          # ### 제1조
    ]
    
    # Special sections that should be independent chunks
    SPECIAL_SECTIONS = [
        '기본정신',
        '기본 정신',
        '개정이력'
    ]
    
    def __init__(
        self,
        target_chunk_size: int = 800,
        min_chunk_size: int = 300
    ):
        """
        Initialize Semantic Chunker v0.4
        
        Args:
            target_chunk_size: Target chunk size in characters
            min_chunk_size: Minimum chunk size in characters
        """
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        
        logger.info("✅ SemanticChunker Phase 0.4.0 초기화")
        logger.info(f"   🎯 목표: {target_chunk_size}자, 최소: {min_chunk_size}자")
        logger.info(f"   📋 조문 패턴: {len(self.ARTICLE_PATTERNS)}개")
        logger.info(f"   ⭐ 특별 섹션: {len(self.SPECIAL_SECTIONS)}개")
    
    def chunk(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Chunk markdown into semantic units
        
        Args:
            markdown: Input markdown text
        
        Returns:
            List of chunks with metadata
        """
        logger.info("   ✂️ SemanticChunker Phase 0.4.0 시작")
        
        chunks = []
        lines = markdown.split('\n')
        current_chunk = []
        current_article = None
        current_title = None
        chunk_index = 1
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for special sections
            special_section = self._is_special_section(line)
            if special_section:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        content='\n'.join(current_chunk),
                        article_no=current_article,
                        article_title=current_title,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = []
                
                # Extract special section content
                section_content = [line]
                i += 1
                
                # Collect until next article or special section
                while i < len(lines):
                    next_line = lines[i]
                    
                    # Stop at next article or special section
                    if self._is_article_header(next_line) or self._is_special_section(next_line):
                        break
                    
                    section_content.append(next_line)
                    i += 1
                
                # Create special section chunk
                chunks.append({
                    'content': '\n'.join(section_content).strip(),
                    'metadata': {
                        'section_type': special_section,
                        'char_count': len('\n'.join(section_content)),
                        'chunk_index': chunk_index
                    }
                })
                chunk_index += 1
                continue
            
            # Check for article header
            article_match = self._is_article_header(line)
            if article_match:
                # Save previous chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        content='\n'.join(current_chunk),
                        article_no=current_article,
                        article_title=current_title,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                
                # Start new chunk with this article
                current_article = article_match['article_no']
                current_title = article_match['title']
                current_chunk = [line]
            else:
                # Add to current chunk
                current_chunk.append(line)
            
            i += 1
        
        # Save final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                content='\n'.join(current_chunk),
                article_no=current_article,
                article_title=current_title,
                chunk_index=chunk_index
            ))
        
        logger.info(f"   ✅ 청킹 완료: {len(chunks)}개")
        logger.info(f"      📊 조문 청크: {sum(1 for c in chunks if 'article_no' in c['metadata'])}개")
        logger.info(f"      ⭐ 특별 섹션: {sum(1 for c in chunks if 'section_type' in c['metadata'])}개")
        
        return chunks
    
    def _is_special_section(self, line: str) -> Optional[str]:
        """Check if line is a special section header"""
        line_clean = line.strip()
        
        for section in self.SPECIAL_SECTIONS:
            # Check for ## 기본정신 or just 기본정신
            if section in line_clean:
                return section
        
        return None
    
    def _is_article_header(self, line: str) -> Optional[Dict[str, str]]:
        """
        Check if line is an article header
        
        Returns:
            Dict with article_no and title, or None
        """
        for pattern in self.ARTICLE_PATTERNS:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()
                article_no = f"제{groups[0]}조"
                
                # Add 의N if exists
                if len(groups) > 1 and groups[1]:
                    article_no += f"의{groups[1]}"
                
                # Extract title if exists
                title = groups[2] if len(groups) > 2 and groups[2] else ""
                
                return {
                    'article_no': article_no,
                    'title': title
                }
        
        return None
    
    def _create_chunk(
        self,
        content: str,
        article_no: Optional[str],
        article_title: Optional[str],
        chunk_index: int
    ) -> Dict[str, Any]:
        """Create chunk dictionary with metadata"""
        content = content.strip()
        
        metadata = {
            'char_count': len(content),
            'chunk_index': chunk_index
        }
        
        if article_no:
            metadata['article_no'] = article_no
        
        if article_title:
            metadata['article_title'] = article_title
        
        return {
            'content': content,
            'metadata': metadata
        }

# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    chunker = SemanticChunker()
    
    sample_md = """
# 인사규정

## 기본정신
이 규정은 직원의 인사관리를 규정합니다.

### 제1조(목적)
이 규정은 인사관리의 기준을 정합니다.

### 제2조(적용범위)
직원의 인사관리에 적용됩니다.
    """
    
    chunks = chunker.chunk(sample_md)
    
    print("=" * 60)
    print("Semantic Chunker v0.4 Example")
    print("=" * 60)
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"Metadata: {chunk['metadata']}")
        print(f"Content: {chunk['content'][:100]}...")

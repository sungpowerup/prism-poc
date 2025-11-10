"""
Prompt Rules V0.4
Phase 0.4.0 "Quality Assurance Release"

Enhanced prompt rules with MANDATORY section extraction
Forces extraction of critical document sections

Author: 박준호 (AI/ML Lead)
Date: 2025-11-09
"""

# Version check
from .version import PRISM_VERSION, check_version
VERSION = "0.4.0"
check_version(__name__, VERSION)

class PromptRulesV04:
    """
    Enhanced prompt rules for Phase 0.4
    Enforces extraction of critical sections
    """
    
    # ============================================
    # Document Structure Rules
    # ============================================
    
    DOCUMENT_STRUCTURE_RULES = """
📋 CRITICAL DOCUMENT STRUCTURE REQUIREMENTS

🚨 MANDATORY SECTIONS (누락 시 ERROR):

1. **기본정신** (Basic Principles)
   - Location: Usually at the beginning, before Article 1
   - Format: Section header "기본정신" or "기본 정신"
   - Content: Fundamental principles of the regulation
   - ⚠️ If missing: Search entire document carefully
   - ⚠️ Must extract even if only 1-2 sentences

2. **제1조** (Article 1)
   - Always present in legal documents
   - Format: "### 제1조(목적)" or "### 제 1 조(목적)"
   - Critical for document purpose

3. **개정이력** (Revision History)
   - Location: Usually at the beginning
   - Format: Table with columns [개정일자, 개정사유, 비고]
   - ⚠️ If in table format: Extract as Markdown table
   - ⚠️ Do NOT skip revision history tables

📊 SECTION EXTRACTION PRIORITY:
```
Priority 1 (CRITICAL): 기본정신, 제1조, 개정이력
Priority 2 (HIGH): All Articles (제2조, 제3조, ...)
Priority 3 (NORMAL): Sub-items (항, 호)
```

⚠️ FAILURE MODES TO AVOID:
- ❌ Skipping "기본정신" section
- ❌ Missing revision history table
- ❌ Hallucinating article numbers
- ❌ Merging separate articles
"""

    # ============================================
    # VLM Prompt Template
    # ============================================
    
    @staticmethod
    def get_vlm_prompt(page_num: int, total_pages: int, doc_type: str = "regulation") -> str:
        """
        Get VLM extraction prompt with mandatory section rules
        
        Args:
            page_num: Current page number (1-indexed)
            total_pages: Total number of pages
            doc_type: Document type ('regulation', 'statute', etc.)
        
        Returns:
            Formatted prompt string
        """
        
        base_prompt = f"""
당신은 법령 문서 전문 분석가입니다.
아래 이미지는 "{doc_type}" 문서의 {page_num}/{total_pages} 페이지입니다.

🎯 주요 임무:
이 페이지의 모든 텍스트를 정확하게 추출하여 Markdown 형식으로 변환하세요.

{PromptRulesV04.DOCUMENT_STRUCTURE_RULES}

📝 Markdown 변환 규칙:

1. **장/절 구조**
   ```markdown
   ## 제1장 총칙
   ### 제1절 목적
   ```

2. **조문 (Articles)**
   ```markdown
   ### 제1조(목적)
   이 규정은 ...
   ```

3. **항·호 (Items)**
   ```markdown
   1. 첫 번째 항목
      가. 세부 항목
      나. 세부 항목
   2. 두 번째 항목
   ```

4. **표 (Tables)**
   ```markdown
   | 개정일자 | 개정사유 | 비고 |
   |---------|---------|------|
   | 2024.01.01 | 최초 제정 | - |
   ```

5. **기본정신 (Basic Principles)**
   ```markdown
   ## 기본정신
   
   모든 직원은 ...
   ```

⚠️ 중요 지침:

1. **완전성**: 모든 텍스트를 빠짐없이 추출
2. **정확성**: 원본과 100% 일치하도록 작성
3. **구조 보존**: 조문 번호, 제목 정확히 유지
4. **NO 추측**: 불확실한 글자는 [?]로 표시
5. **필수 섹션**: 기본정신, 개정이력, 제1조 반드시 포함

🔍 특별 주의사항:
- 페이지 번호는 제외
- 헤더/푸터는 제외
- 워터마크는 제외
- 조문 번호 오인식 주의 (예: 제7조 ≠ 제73조)

출력: 순수 Markdown 텍스트만 반환 (설명 없이)
"""
        
        # Add page-specific instructions
        if page_num == 1:
            base_prompt += """

📌 첫 페이지 특별 지침:
- "기본정신" 섹션 반드시 확인
- "개정이력" 표 반드시 확인
- 문서 제목 정확히 추출
"""
        
        return base_prompt
    
    # ============================================
    # Validation Rules
    # ============================================
    
    @staticmethod
    def validate_extraction(markdown: str, doc_type: str = "regulation") -> dict:
        """
        Validate that extraction includes all mandatory sections
        
        Args:
            markdown: Extracted markdown content
            doc_type: Document type
        
        Returns:
            dict with validation results
        """
        issues = []
        
        # Check critical sections
        if '기본정신' not in markdown and '기본 정신' not in markdown:
            issues.append({
                'severity': 'critical',
                'section': '기본정신',
                'message': 'Missing "기본정신" section'
            })
        
        if '제1조' not in markdown and '제 1 조' not in markdown:
            issues.append({
                'severity': 'critical',
                'section': '제1조',
                'message': 'Missing "제1조" (Article 1)'
            })
        
        if '개정이력' not in markdown and '개정 이력' not in markdown:
            issues.append({
                'severity': 'major',
                'section': '개정이력',
                'message': 'Missing "개정이력" (Revision History)'
            })
        
        # Calculate completeness score
        critical_count = len([i for i in issues if i['severity'] == 'critical'])
        major_count = len([i for i in issues if i['severity'] == 'major'])
        
        score = 100 - (critical_count * 30) - (major_count * 10)
        
        return {
            'valid': len(issues) == 0,
            'score': max(0, score),
            'issues': issues,
            'critical_issues': critical_count,
            'major_issues': major_count
        }
    
    # ============================================
    # Legacy Compatibility
    # ============================================
    
    @staticmethod
    def get_system_prompt() -> str:
        """Legacy method for backward compatibility"""
        return PromptRulesV04.DOCUMENT_STRUCTURE_RULES
    
    @staticmethod
    def get_user_prompt(page_num: int, total_pages: int) -> str:
        """Legacy method for backward compatibility"""
        return PromptRulesV04.get_vlm_prompt(page_num, total_pages)


# ============================================
# Module-level convenience functions
# ============================================

def get_vlm_prompt(page_num: int, total_pages: int, doc_type: str = "regulation") -> str:
    """Convenience function for getting VLM prompt"""
    return PromptRulesV04.get_vlm_prompt(page_num, total_pages, doc_type)

def validate_extraction(markdown: str, doc_type: str = "regulation") -> dict:
    """Convenience function for validation"""
    return PromptRulesV04.validate_extraction(markdown, doc_type)


# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    # Example: Generate prompt for first page
    prompt = get_vlm_prompt(page_num=1, total_pages=3, doc_type="인사규정")
    print("=" * 60)
    print("VLM Prompt Example:")
    print("=" * 60)
    print(prompt)
    print()
    
    # Example: Validate extraction
    sample_markdown = """
## 기본정신

모든 직원은 평등하게 대우받는다.

### 제1조(목적)
이 규정은...
"""
    
    validation = validate_extraction(sample_markdown)
    print("=" * 60)
    print("Validation Result:")
    print("=" * 60)
    print(f"Valid: {validation['valid']}")
    print(f"Score: {validation['score']}/100")
    print(f"Issues: {len(validation['issues'])}")
    for issue in validation['issues']:
        print(f"  - [{issue['severity']}] {issue['message']}")

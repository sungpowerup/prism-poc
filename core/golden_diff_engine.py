"""
Golden Diff Engine
Phase 0.4.0 "Quality Assurance Release"

Automatic comparison between Golden Files and processing results
Provides honest quality scores based on actual differences

Author: 이서영 (Backend Lead)
Date: 2025-11-10
Version: 0.4.0
"""

from typing import Dict, List, Any, Tuple
import difflib
from dataclasses import dataclass
from pathlib import Path
import re

# Version check
try:
    from .version import PRISM_VERSION, check_version
    VERSION = "0.4.0"
    check_version(__name__, VERSION)
except ImportError:
    VERSION = "0.4.0"
    print(f"⚠️ Version module not found, using VERSION={VERSION}")

# ============================================
# Data Structures
# ============================================

@dataclass
class DiffError:
    """Single difference between golden and result"""
    error_type: str  # 'missing', 'extra', 'typo', 'structure'
    location: str    # Section/Article number
    expected: str    # Golden file content
    actual: str      # Result content
    severity: str    # 'critical', 'major', 'minor'
    
    def to_dict(self) -> Dict:
        return {
            'type': self.error_type,
            'location': self.location,
            'expected': self.expected,
            'actual': self.actual,
            'severity': self.severity
        }

@dataclass
class DiffResult:
    """Complete comparison result"""
    match_rate: float           # 0.0 ~ 1.0
    pass_status: bool           # True if meets threshold
    total_chars: int            # Total characters compared
    matched_chars: int          # Matched characters
    errors: List[DiffError]     # List of differences
    critical_sections_ok: bool  # All critical sections present
    
    def to_dict(self) -> Dict:
        return {
            'match_rate': round(self.match_rate, 4),
            'pass': self.pass_status,
            'total_chars': self.total_chars,
            'matched_chars': self.matched_chars,
            'error_count': len(self.errors),
            'errors': [e.to_dict() for e in self.errors],
            'critical_sections_ok': self.critical_sections_ok
        }

# ============================================
# Golden Diff Engine
# ============================================

class GoldenDiffEngine:
    """
    Compare processing results against Golden Files
    Provides honest quality measurement
    """
    
    # Critical sections that must be present
    CRITICAL_SECTIONS = [
        '기본정신',
        '기본 정신',
        '제1조',
        '개정이력'
    ]
    
    # Quality thresholds
    THRESHOLDS = {
        'strict': {
            'match_rate': 0.99,
            'max_errors': 5,
            'max_critical_errors': 0
        },
        'standard': {
            'match_rate': 0.97,
            'max_errors': 10,
            'max_critical_errors': 1
        },
        'lenient': {
            'match_rate': 0.95,
            'max_errors': 20,
            'max_critical_errors': 2
        }
    }
    
    def __init__(self, threshold_mode: str = 'strict'):
        """
        Initialize Golden Diff Engine
        
        Args:
            threshold_mode: 'strict', 'standard', or 'lenient'
        """
        self.threshold = self.THRESHOLDS[threshold_mode]
        self.threshold_mode = threshold_mode
    
    def compare(self, golden_md: str, result_md: str) -> DiffResult:
        """
        Compare golden file with result
        
        Args:
            golden_md: Golden markdown content
            result_md: Processing result markdown
        
        Returns:
            DiffResult with detailed comparison
        """
        # 1. Check critical sections
        critical_ok = self._check_critical_sections(result_md)
        
        # 2. Calculate match rate
        match_rate, matched, total = self._calculate_match_rate(golden_md, result_md)
        
        # 3. Find detailed differences
        errors = self._find_differences(golden_md, result_md)
        
        # 4. Determine pass/fail
        critical_errors = [e for e in errors if e.severity == 'critical']
        pass_status = (
            match_rate >= self.threshold['match_rate'] and
            len(errors) <= self.threshold['max_errors'] and
            len(critical_errors) <= self.threshold['max_critical_errors'] and
            critical_ok
        )
        
        return DiffResult(
            match_rate=match_rate,
            pass_status=pass_status,
            total_chars=total,
            matched_chars=matched,
            errors=errors,
            critical_sections_ok=critical_ok
        )
    
    def _check_critical_sections(self, text: str) -> bool:
        """Check if all critical sections are present"""
        for section in self.CRITICAL_SECTIONS:
            if section not in text:
                return False
        return True
    
    def _calculate_match_rate(self, golden: str, result: str) -> Tuple[float, int, int]:
        """
        Calculate character-level match rate
        
        Returns:
            (match_rate, matched_chars, total_chars)
        """
        # Use SequenceMatcher for accurate comparison
        matcher = difflib.SequenceMatcher(None, golden, result)
        
        # Get matching blocks
        matches = matcher.get_matching_blocks()
        matched_chars = sum(block.size for block in matches)
        total_chars = len(golden)
        
        match_rate = matched_chars / total_chars if total_chars > 0 else 0.0
        
        return match_rate, matched_chars, total_chars
    
    def _find_differences(self, golden: str, result: str) -> List[DiffError]:
        """Find specific differences between golden and result"""
        errors = []
        
        # 1. Check for missing critical sections
        for section in self.CRITICAL_SECTIONS:
            if section in golden and section not in result:
                errors.append(DiffError(
                    error_type='missing',
                    location=section,
                    expected=f'{section} section',
                    actual='Not found',
                    severity='critical'
                ))
        
        # 2. Line-by-line comparison for articles
        golden_lines = golden.split('\n')
        result_lines = result.split('\n')
        
        # Find article headers
        article_pattern = r'###?\s*제(\d+)조'
        
        for i, golden_line in enumerate(golden_lines):
            article_match = re.search(article_pattern, golden_line)
            if article_match:
                article_no = article_match.group(1)
                
                # Find corresponding line in result
                result_line = None
                for j, rline in enumerate(result_lines):
                    if f'제{article_no}조' in rline:
                        result_line = rline
                        break
                
                if not result_line:
                    errors.append(DiffError(
                        error_type='missing',
                        location=f'제{article_no}조',
                        expected=golden_line[:50] + '...',
                        actual='Not found',
                        severity='major'
                    ))
                elif golden_line != result_line:
                    # Only report if difference is significant (not just whitespace)
                    if golden_line.strip() != result_line.strip():
                        errors.append(DiffError(
                            error_type='typo',
                            location=f'제{article_no}조',
                            expected=golden_line[:50] + '...',
                            actual=result_line[:50] + '...',
                            severity='minor'
                        ))
        
        # 3. Check for extra content in result (hallucinations)
        for line in result_lines:
            article_match = re.search(article_pattern, line)
            if article_match:
                article_no = article_match.group(1)
                # Check if this article exists in golden
                if not any(f'제{article_no}조' in gline for gline in golden_lines):
                    errors.append(DiffError(
                        error_type='extra',
                        location=f'제{article_no}조',
                        expected='Should not exist',
                        actual=line[:50] + '...',
                        severity='major'
                    ))
        
        return errors
    
    def generate_report(self, result: DiffResult, output_path: str = None) -> str:
        """
        Generate human-readable diff report
        
        Args:
            result: DiffResult object
            output_path: Optional file path to save report
        
        Returns:
            Report text
        """
        report_lines = [
            "=" * 60,
            f"PRISM Golden Diff Report (Phase {VERSION})",
            f"Threshold Mode: {self.threshold_mode}",
            "=" * 60,
            "",
            "📊 Overall Quality",
            f"  Match Rate: {result.match_rate * 100:.2f}%",
            f"  Status: {'✅ PASS' if result.pass_status else '❌ FAIL'}",
            f"  Matched: {result.matched_chars:,} / {result.total_chars:,} chars",
            "",
            "🔍 Critical Sections",
            f"  Status: {'✅ All Present' if result.critical_sections_ok else '❌ Missing'}",
            ""
        ]
        
        if result.errors:
            report_lines.append(f"⚠️ Errors Found: {len(result.errors)}")
            report_lines.append("")
            
            # Group errors by severity
            critical = [e for e in result.errors if e.severity == 'critical']
            major = [e for e in result.errors if e.severity == 'major']
            minor = [e for e in result.errors if e.severity == 'minor']
            
            if critical:
                report_lines.append(f"🚨 Critical Errors ({len(critical)}):")
                for err in critical:
                    report_lines.append(f"  - [{err.error_type}] {err.location}")
                    report_lines.append(f"    Expected: {err.expected[:50]}...")
                    report_lines.append(f"    Actual: {err.actual[:50]}...")
                report_lines.append("")
            
            if major:
                report_lines.append(f"⚠️ Major Errors ({len(major)}):")
                for err in major[:5]:  # Show first 5
                    report_lines.append(f"  - [{err.error_type}] {err.location}")
                if len(major) > 5:
                    report_lines.append(f"  ... and {len(major) - 5} more")
                report_lines.append("")
            
            if minor:
                report_lines.append(f"ℹ️ Minor Errors ({len(minor)})")
                report_lines.append("")
        else:
            report_lines.append("✅ No errors found!")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        report = "\n".join(report_lines)
        
        if output_path:
            Path(output_path).write_text(report, encoding='utf-8')
        
        return report

# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    # Example usage
    engine = GoldenDiffEngine(threshold_mode='strict')
    
    golden = """
### 기본정신
이 규정은...

### 제1조(목적)
이 규정은 직원의 인사관리에 관한 사항을 정함을 목적으로 한다.
    """
    
    result = """
### 기본정신
이 규정은...

### 제1조(목적)
이 규정은 직원의 인사관리에 관한 사항을 정함을 목적으로 한다.
    """
    
    diff_result = engine.compare(golden, result)
    report = engine.generate_report(diff_result)
    print(report)

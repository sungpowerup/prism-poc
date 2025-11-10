"""
Version Management System
Phase 0.4.0 "Quality Assurance Release"

Single source of truth for all version numbers
All modules MUST import and check against this version

Author: 황태민 (DevOps Lead)
Date: 2025-11-10
"""

# ============================================
# PRISM Version (Single Source of Truth)
# ============================================
PRISM_VERSION = "0.4.0"
VERSION = "0.4.0"  # ✅ 추가: 자기 자신의 버전도 선언

# ============================================
# Module Version Registry
# ============================================
MODULE_VERSIONS = {
    'core.version': '0.4.0',
    'core.golden_diff_engine': '0.4.0',
    'core.prompt_rules_v04': '0.4.0',
    'core.semantic_chunker_v04': '0.4.0',
    'core.pipeline': '0.4.0',
}

# ============================================
# Version Check Function
# ============================================
def check_version(module_name: str, module_version: str) -> None:
    """
    Check if module version matches PRISM version
    
    Args:
        module_name: Name of the module (e.g., 'core.golden_diff_engine')
        module_version: Version string from the module
    
    Raises:
        ValueError: If version mismatch detected
    """
    if module_version != PRISM_VERSION:
        raise ValueError(
            f"❌ Version mismatch in {module_name}!\n"
            f"   Expected: {PRISM_VERSION}\n"
            f"   Got: {module_version}\n"
            f"   Please update module version to match PRISM_VERSION"
        )

# ============================================
# Version Info Display
# ============================================
def get_version_info() -> str:
    """
    Get formatted version information
    
    Returns:
        Formatted version string
    """
    return f"PRISM v{PRISM_VERSION} - Quality Assurance Release"

if __name__ == "__main__":
    print("=" * 60)
    print(get_version_info())
    print("=" * 60)
    print()
    print("Registered Modules:")
    for module, version in MODULE_VERSIONS.items():
        status = "✅" if version == PRISM_VERSION else "❌"
        print(f"  {status} {module}: {version}")

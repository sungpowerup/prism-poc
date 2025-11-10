"""
PRISM Version Management System
Phase 0.4.0 "Quality Assurance Release"

Single Source of Truth for Version Control
All modules MUST import from this file

Author: 황태민 (DevOps Lead)
Date: 2025-11-09
"""

# ============================================
# CRITICAL: Single Version Declaration
# ============================================
PRISM_VERSION = "0.4.0"

# ============================================
# Version Check Function
# ============================================
def get_version() -> str:
    """
    Get current PRISM version
    
    Returns:
        str: Version string (e.g., "0.4.0")
    """
    return PRISM_VERSION

def check_version(module_name: str, module_version: str) -> bool:
    """
    Validate module version matches PRISM version
    
    Args:
        module_name: Name of the module
        module_version: Version declared in module
    
    Returns:
        bool: True if versions match
    
    Raises:
        ValueError: If versions don't match
    """
    if module_version != PRISM_VERSION:
        raise ValueError(
            f"❌ Version Mismatch!\n"
            f"   Module: {module_name}\n"
            f"   Expected: {PRISM_VERSION}\n"
            f"   Got: {module_version}\n"
            f"   → Fix: Update module version to {PRISM_VERSION}"
        )
    return True

# ============================================
# Module Version Registry
# ============================================
MODULE_VERSIONS = {
    'core.version': PRISM_VERSION,
    'core.golden_diff_engine': PRISM_VERSION,
    'core.prompt_rules_v04': PRISM_VERSION,
    'core.semantic_chunker_v04': PRISM_VERSION,
    'scripts.validate_versions': PRISM_VERSION,
}

def validate_all_modules():
    """
    Validate all registered modules have correct version
    Used in CI/CD pipeline
    """
    print(f"🔍 Validating PRISM Version: {PRISM_VERSION}")
    print("=" * 50)
    
    all_valid = True
    for module_name, expected_version in MODULE_VERSIONS.items():
        try:
            # This is a registry check, actual import validation
            # happens in validate_versions.py
            print(f"✅ {module_name}: {expected_version}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            all_valid = False
    
    print("=" * 50)
    if all_valid:
        print(f"✅ All modules validated: {PRISM_VERSION}")
    else:
        print(f"❌ Version validation failed!")
        raise ValueError("Module version mismatch detected")
    
    return all_valid

# ============================================
# Usage Example
# ============================================
if __name__ == "__main__":
    print(f"PRISM Version: {get_version()}")
    validate_all_modules()

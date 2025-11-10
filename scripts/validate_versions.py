"""
Version Validation Script
Phase 0.4.0 "Quality Assurance Release"

CI/CD build-level version validation
Ensures all modules use consistent PRISM version

Author: 황태민 (DevOps Lead)
Date: 2025-11-10

Usage:
    python scripts/validate_versions.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def validate_versions():
    """
    Validate all module versions match PRISM_VERSION
    
    Returns:
        bool: True if all valid, False otherwise
    """
    print("=" * 60)
    print("PRISM Version Validation (Phase 0.4)")
    print("=" * 60)
    print()
    
    # Import version module
    try:
        from core.version import PRISM_VERSION, MODULE_VERSIONS
        print(f"✅ Target Version: {PRISM_VERSION}")
        print()
    except ImportError as e:
        print(f"❌ Failed to import core.version: {e}")
        return False
    
    # Module validation registry
    modules_to_check = [
        'core.version',
        'core.golden_diff_engine',
        'core.prompt_rules_v04',
        'core.semantic_chunker_v04',
    ]
    
    all_valid = True
    results = []
    
    for module_name in modules_to_check:
        try:
            # Import module
            if module_name == 'core.version':
                from core import version as mod
            elif module_name == 'core.golden_diff_engine':
                from core import golden_diff_engine as mod
            elif module_name == 'core.prompt_rules_v04':
                from core import prompt_rules_v04 as mod
            elif module_name == 'core.semantic_chunker_v04':
                from core import semantic_chunker_v04 as mod
            else:
                raise ImportError(f"Unknown module: {module_name}")
            
            # Check version
            module_version = getattr(mod, 'VERSION', None)
            
            if module_version is None:
                results.append({
                    'module': module_name,
                    'status': 'error',
                    'message': 'No VERSION attribute'
                })
                all_valid = False
            elif module_version != PRISM_VERSION:
                results.append({
                    'module': module_name,
                    'status': 'fail',
                    'version': module_version,
                    'expected': PRISM_VERSION
                })
                all_valid = False
            else:
                results.append({
                    'module': module_name,
                    'status': 'pass',
                    'version': module_version
                })
        
        except ImportError as e:
            results.append({
                'module': module_name,
                'status': 'error',
                'message': str(e)
            })
            all_valid = False
    
    # Print results
    print("Validation Results:")
    print("-" * 60)
    
    for result in results:
        module = result['module']
        status = result['status']
        
        if status == 'pass':
            print(f"✅ {module}: {result['version']}")
        elif status == 'fail':
            print(f"❌ {module}: {result['version']} (expected {result['expected']})")
        elif status == 'error':
            print(f"⚠️ {module}: {result['message']}")
    
    print()
    print("=" * 60)
    
    if all_valid:
        print("✅ All modules validated successfully!")
        print("=" * 60)
        return True
    else:
        print("❌ Version validation failed!")
        print("Please update module versions to match PRISM_VERSION")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = validate_versions()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Master test runner for all Python environment tests.
Generated automatically by setup_test_environments.py
"""

import subprocess
import sys
from pathlib import Path

def run_test_script(script_path, version_name):
    """Run a single test script."""
    print(f"🧪 Running tests for Python {version_name}...")
    print("-" * 40)
    
    try:
        if sys.platform == "win32":
            result = subprocess.run([str(script_path)], check=True, timeout=300)
        else:
            result = subprocess.run(["bash", str(script_path)], check=True, timeout=300)
        print(f"✅ Python {version_name} tests PASSED\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Python {version_name} tests FAILED (exit code {e.returncode})\n")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ Python {version_name} tests TIMEOUT\n")
        return False
    except Exception as e:
        print(f"❌ Python {version_name} tests ERROR: {e}\n")
        return False

def main():
    """Run all environment tests."""
    print("🧪 Running All Environment Tests")
    print("=" * 50)
    
    test_scripts = [
        [("'3.12'", "'test_environments/test_3_12.sh'"), ("'system'", "'test_environments/test_system.sh'")]
    ]
    
    passed = 0
    total = len(test_scripts)
    
    for version_name, script_path in test_scripts:
        if run_test_script(Path(script_path), version_name):
            passed += 1
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} environments passed")
    
    if passed == total:
        print("🎉 All environment tests PASSED!")
        print("\n📋 Ready for Phase 2: Package Building Tests")
        return 0
    else:
        print(f"❌ {total - passed} environment tests FAILED")
        print("\n🔧 Fix failing environments before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())

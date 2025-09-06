#!/usr/bin/env python3
"""
Phase 1: Basic functionality tests without full environment setup.
This runs quickly to verify core functionality works.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that basic imports work."""
    print("1. Testing imports...")
    
    try:
        import mini_rag
        print("   ✅ mini_rag package imports")
    except Exception as e:
        print(f"   ❌ mini_rag import failed: {e}")
        return False
    
    try:
        from mini_rag.cli import cli
        print("   ✅ CLI function imports")
    except Exception as e:
        print(f"   ❌ CLI import failed: {e}")
        return False
    
    return True

def test_pyproject_structure():
    """Test pyproject.toml has correct structure."""
    print("2. Testing pyproject.toml...")
    
    pyproject_file = project_root / "pyproject.toml"
    if not pyproject_file.exists():
        print("   ❌ pyproject.toml missing")
        return False
    
    content = pyproject_file.read_text()
    
    # Check essential elements
    checks = [
        ('name = "fss-mini-rag"', "Package name"),
        ('rag-mini = "mini_rag.cli:cli"', "Entry point"),
        ('requires-python = ">=3.8"', "Python version"),
        ('Brett Fox', "Author"),
        ('MIT', "License"),
    ]
    
    for check, desc in checks:
        if check in content:
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc} missing")
            return False
    
    return True

def test_install_scripts():
    """Test install scripts exist and have basic structure."""
    print("3. Testing install scripts...")
    
    # Check install.sh
    install_sh = project_root / "install.sh"
    if install_sh.exists():
        content = install_sh.read_text()
        if "uv tool install" in content and "pipx install" in content:
            print("   ✅ install.sh has proper structure")
        else:
            print("   ❌ install.sh missing key components")
            return False
    else:
        print("   ❌ install.sh missing")
        return False
    
    # Check install.ps1
    install_ps1 = project_root / "install.ps1"
    if install_ps1.exists():
        content = install_ps1.read_text()
        if "Install-UV" in content and "Install-WithPipx" in content:
            print("   ✅ install.ps1 has proper structure")
        else:
            print("   ❌ install.ps1 missing key components") 
            return False
    else:
        print("   ❌ install.ps1 missing")
        return False
    
    return True

def test_build_scripts():
    """Test build scripts exist."""
    print("4. Testing build scripts...")
    
    build_pyz = project_root / "scripts" / "build_pyz.py"
    if build_pyz.exists():
        content = build_pyz.read_text()
        if "zipapp" in content:
            print("   ✅ build_pyz.py exists with zipapp")
        else:
            print("   ❌ build_pyz.py missing zipapp code")
            return False
    else:
        print("   ❌ build_pyz.py missing")
        return False
    
    return True

def test_github_workflow():
    """Test GitHub workflow exists."""
    print("5. Testing GitHub workflow...")
    
    workflow_file = project_root / ".github" / "workflows" / "build-and-release.yml"
    if workflow_file.exists():
        content = workflow_file.read_text()
        if "cibuildwheel" in content and "pypa/gh-action-pypi-publish" in content:
            print("   ✅ GitHub workflow has proper structure")
        else:
            print("   ❌ GitHub workflow missing key components")
            return False
    else:
        print("   ❌ GitHub workflow missing")
        return False
    
    return True

def test_documentation():
    """Test documentation is updated."""
    print("6. Testing documentation...")
    
    readme = project_root / "README.md"
    if readme.exists():
        content = readme.read_text()
        if "One-Line Installers" in content and "uv tool install" in content:
            print("   ✅ README has new installation methods")
        else:
            print("   ❌ README missing new installation section")
            return False
    else:
        print("   ❌ README missing")
        return False
    
    return True

def main():
    """Run all basic tests."""
    print("🧪 FSS-Mini-RAG Phase 1: Basic Tests")
    print("=" * 40)
    
    tests = [
        ("Import Tests", test_imports),
        ("PyProject Structure", test_pyproject_structure),
        ("Install Scripts", test_install_scripts),
        ("Build Scripts", test_build_scripts), 
        ("GitHub Workflow", test_github_workflow),
        ("Documentation", test_documentation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 1: All basic tests PASSED!")
        print("\n📋 Ready for Phase 2: Package Building Tests")
        print("Next steps:")
        print("   1. python -m build --sdist")
        print("   2. python -m build --wheel") 
        print("   3. python scripts/build_pyz.py")
        print("   4. Test installations from built packages")
        return True
    else:
        print(f"❌ {total - passed} tests FAILED")
        print("🔧 Fix failing tests before proceeding to Phase 2")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
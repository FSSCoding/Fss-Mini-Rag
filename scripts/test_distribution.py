#!/usr/bin/env python3
"""
Test script for validating the new distribution methods.
This script helps verify that all the new installation methods work correctly.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def run_command(cmd, cwd=None, capture=True):
    """Run a command and return success/output."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, 
            capture_output=capture, text=True, timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {cmd}")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Command failed: {cmd} - {e}")
        return False, "", str(e)

def test_pyproject_validation():
    """Test that pyproject.toml is valid."""
    print("🔍 Testing pyproject.toml validation...")
    
    success, stdout, stderr = run_command("python -m build --help")
    if not success:
        print("❌ build module not available. Install with: pip install build")
        return False
    
    # Test building source distribution
    success, stdout, stderr = run_command("python -m build --sdist")
    if success:
        print("✅ Source distribution builds successfully")
        return True
    else:
        print(f"❌ Source distribution build failed: {stderr}")
        return False

def test_zipapp_build():
    """Test building the .pyz zipapp."""
    print("🔍 Testing zipapp build...")
    
    script_path = Path(__file__).parent / "build_pyz.py"
    if not script_path.exists():
        print(f"❌ Build script not found: {script_path}")
        return False
    
    success, stdout, stderr = run_command(f"python {script_path}")
    if success:
        print("✅ Zipapp builds successfully")
        
        # Test that the .pyz file works
        pyz_file = Path("dist/rag-mini.pyz")
        if pyz_file.exists():
            success, stdout, stderr = run_command(f"python {pyz_file} --help")
            if success:
                print("✅ Zipapp runs successfully")
                return True
            else:
                print(f"❌ Zipapp doesn't run: {stderr}")
                return False
        else:
            print("❌ Zipapp file not created")
            return False
    else:
        print(f"❌ Zipapp build failed: {stderr}")
        return False

def test_entry_point():
    """Test that the entry point is properly configured."""
    print("🔍 Testing entry point configuration...")
    
    # Install in development mode
    success, stdout, stderr = run_command("pip install -e .")
    if not success:
        print(f"❌ Development install failed: {stderr}")
        return False
    
    # Test that the command works
    success, stdout, stderr = run_command("rag-mini --help")
    if success:
        print("✅ Entry point works correctly")
        return True
    else:
        print(f"❌ Entry point failed: {stderr}")
        return False

def test_install_scripts():
    """Test that install scripts are syntactically correct."""
    print("🔍 Testing install scripts...")
    
    # Test bash script syntax
    bash_script = Path("install.sh")
    if bash_script.exists():
        success, stdout, stderr = run_command(f"bash -n {bash_script}")
        if success:
            print("✅ install.sh syntax is valid")
        else:
            print(f"❌ install.sh syntax error: {stderr}")
            return False
    else:
        print("❌ install.sh not found")
        return False
    
    # Test PowerShell script syntax
    ps_script = Path("install.ps1")
    if ps_script.exists():
        # Basic check - PowerShell syntax validation would require PowerShell
        if ps_script.read_text().count("function ") >= 5:  # Should have multiple functions
            print("✅ install.ps1 structure looks valid")
        else:
            print("❌ install.ps1 structure seems incomplete")
            return False
    else:
        print("❌ install.ps1 not found")
        return False
    
    return True

def test_github_workflow():
    """Test that GitHub workflow is valid YAML."""
    print("🔍 Testing GitHub workflow...")
    
    workflow_file = Path(".github/workflows/build-and-release.yml")
    if not workflow_file.exists():
        print("❌ GitHub workflow file not found")
        return False
    
    try:
        import yaml
        with open(workflow_file) as f:
            yaml.safe_load(f)
        print("✅ GitHub workflow is valid YAML")
        return True
    except ImportError:
        print("⚠️  PyYAML not available, skipping workflow validation")
        print("   Install with: pip install PyYAML")
        return True  # Don't fail if yaml is not available
    except Exception as e:
        print(f"❌ GitHub workflow invalid: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing FSS-Mini-RAG Distribution Setup")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    tests = [
        ("PyProject Validation", test_pyproject_validation),
        ("Entry Point Configuration", test_entry_point), 
        ("Zipapp Build", test_zipapp_build),
        ("Install Scripts", test_install_scripts),
        ("GitHub Workflow", test_github_workflow),
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((name, False))
    
    print(f"\n{'='*50}")
    print("📊 Test Results:")
    print(f"{'='*50}")
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:>8} {name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Distribution setup is ready.")
        print("\n📋 Next steps:")
        print("   1. Commit these changes")
        print("   2. Push to GitHub to test the workflow")
        print("   3. Create a release to trigger wheel building")
        return 0
    else:
        print(f"\n❌ {len(results) - passed} tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
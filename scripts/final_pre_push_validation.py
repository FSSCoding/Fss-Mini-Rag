#!/usr/bin/env python3
"""
Final validation before pushing to GitHub.
Ensures all critical components are working and ready for production.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_critical_files():
    """Check that all critical files exist and are valid."""
    print("1. Checking critical files...")
    
    project_root = Path(__file__).parent.parent
    
    critical_files = [
        # Core distribution files
        ("pyproject.toml", "Enhanced package metadata"),
        ("install.sh", "Linux/macOS install script"),
        ("install.ps1", "Windows install script"), 
        ("Makefile", "Build automation"),
        
        # GitHub Actions
        (".github/workflows/build-and-release.yml", "CI/CD workflow"),
        
        # Build scripts
        ("scripts/build_pyz.py", "Zipapp builder"),
        
        # Documentation
        ("README.md", "Updated documentation"),
        ("docs/TESTING_PLAN.md", "Testing plan"),
        ("docs/DEPLOYMENT_ROADMAP.md", "Deployment roadmap"),
        ("TESTING_RESULTS.md", "Test results"),
        ("IMPLEMENTATION_COMPLETE.md", "Implementation summary"),
        
        # Testing scripts
        ("scripts/validate_setup.py", "Setup validator"),
        ("scripts/phase1_basic_tests.py", "Basic tests"),
        ("scripts/phase1_local_validation.py", "Local validation"),
        ("scripts/phase2_build_tests.py", "Build tests"),
        ("scripts/final_pre_push_validation.py", "This script"),
    ]
    
    missing_files = []
    for file_path, description in critical_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ Missing: {description} ({file_path})")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def check_pyproject_toml():
    """Check pyproject.toml has required elements."""
    print("2. Validating pyproject.toml...")
    
    project_root = Path(__file__).parent.parent
    pyproject_file = project_root / "pyproject.toml"
    
    if not pyproject_file.exists():
        print("   ❌ pyproject.toml missing")
        return False
    
    content = pyproject_file.read_text()
    
    required_elements = [
        ('name = "fss-mini-rag"', "Package name"),
        ('rag-mini = "mini_rag.cli:cli"', "Console script"),
        ('requires-python = ">=3.8"', "Python version"),
        ('Brett Fox', "Author"),
        ('MIT', "License"),
        ('[build-system]', "Build system"),
        ('[project.urls]', "Project URLs"),
    ]
    
    all_good = True
    for element, description in required_elements:
        if element in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ Missing: {description}")
            all_good = False
    
    return all_good

def check_install_scripts():
    """Check install scripts are syntactically valid."""
    print("3. Validating install scripts...")
    
    project_root = Path(__file__).parent.parent
    
    # Check bash script
    install_sh = project_root / "install.sh"
    if install_sh.exists():
        try:
            result = subprocess.run(
                ["bash", "-n", str(install_sh)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print("   ✅ install.sh syntax valid")
            else:
                print(f"   ❌ install.sh syntax error: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Error checking install.sh: {e}")
            return False
    else:
        print("   ❌ install.sh missing")
        return False
    
    # Check PowerShell script exists and has key functions
    install_ps1 = project_root / "install.ps1"
    if install_ps1.exists():
        content = install_ps1.read_text()
        if "Install-UV" in content and "Install-WithPipx" in content:
            print("   ✅ install.ps1 structure valid")
        else:
            print("   ❌ install.ps1 missing key functions")
            return False
    else:
        print("   ❌ install.ps1 missing")
        return False
    
    return True

def check_readme_updates():
    """Check README has the new installation section."""
    print("4. Validating README updates...")
    
    project_root = Path(__file__).parent.parent
    readme_file = project_root / "README.md"
    
    if not readme_file.exists():
        print("   ❌ README.md missing")
        return False
    
    content = readme_file.read_text()
    
    required_sections = [
        ("One-Line Installers", "New installation section"),
        ("curl -fsSL", "Linux/macOS installer"),
        ("iwr", "Windows installer"),
        ("uv tool install", "uv installation method"),
        ("pipx install", "pipx installation method"),
        ("fss-mini-rag", "Correct package name"),
    ]
    
    all_good = True
    for section, description in required_sections:
        if section in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ Missing: {description}")
            all_good = False
    
    return all_good

def check_git_status():
    """Check git status and what will be committed."""
    print("5. Checking git status...")
    
    try:
        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            if changes:
                print(f"   📋 Found {len(changes)} changes to commit:")
                for change in changes[:10]:  # Show first 10
                    print(f"      {change}")
                if len(changes) > 10:
                    print(f"      ... and {len(changes) - 10} more")
            else:
                print("   ✅ No changes to commit")
            
            return True
        else:
            print(f"   ❌ Git status failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking git status: {e}")
        return False

def check_branch_status():
    """Check current branch."""
    print("6. Checking git branch...")
    
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            branch = result.stdout.strip()
            print(f"   ✅ Current branch: {branch}")
            return True
        else:
            print(f"   ❌ Failed to get branch: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking branch: {e}")
        return False

def check_no_large_files():
    """Check for unexpectedly large files."""
    print("7. Checking for large files...")
    
    project_root = Path(__file__).parent.parent
    
    large_files = []
    for file_path in project_root.rglob("*"):
        if file_path.is_file():
            try:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > 50:  # Files larger than 50MB
                    large_files.append((file_path, size_mb))
            except (OSError, PermissionError):
                pass  # Skip files we can't read
    
    if large_files:
        print("   ⚠️  Found large files:")
        for file_path, size_mb in large_files:
            rel_path = file_path.relative_to(project_root)
            print(f"      {rel_path}: {size_mb:.1f} MB")
        
        # Check if any are unexpectedly large (excluding known large files and gitignored paths)
        expected_large = ["dist/rag-mini.pyz"]  # Known large files
        gitignored_paths = [".venv/", "venv/", "test_environments/"]  # Gitignored directories
        unexpected = [f for f, s in large_files 
                     if not any(expected in str(f) for expected in expected_large)
                     and not any(ignored in str(f) for ignored in gitignored_paths)]
        
        if unexpected:
            print("   ❌ Unexpected large files found")
            return False
        else:
            print("   ✅ Large files are expected (zipapp, etc.)")
    else:
        print("   ✅ No large files found")
    
    return True

def main():
    """Run all pre-push validation checks."""
    print("🚀 FSS-Mini-RAG: Final Pre-Push Validation")
    print("=" * 50)
    
    checks = [
        ("Critical Files", check_critical_files),
        ("PyProject.toml", check_pyproject_toml),
        ("Install Scripts", check_install_scripts),
        ("README Updates", check_readme_updates),
        ("Git Status", check_git_status),
        ("Git Branch", check_branch_status),
        ("Large Files", check_no_large_files),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{'='*15} {check_name} {'='*15}")
        try:
            if check_func():
                print(f"✅ {check_name} PASSED")
                passed += 1
            else:
                print(f"❌ {check_name} FAILED")
        except Exception as e:
            print(f"❌ {check_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Pre-Push Validation: {passed}/{total} checks passed")
    print(f"{'='*50}")
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED!")
        print("✅ Ready to push to GitHub")
        print()
        print("Next steps:")
        print("   1. git add -A")
        print("   2. git commit -m 'Add modern distribution system with one-line installers'")
        print("   3. git push origin main")
        return True
    else:
        print(f"❌ {total - passed} checks FAILED")
        print("🔧 Fix issues before pushing")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
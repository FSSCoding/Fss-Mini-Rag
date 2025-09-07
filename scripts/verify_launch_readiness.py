#!/usr/bin/env python3
"""
Launch Readiness Verification Script
Discrete verification of all systems before PyPI launch
"""

import os
import subprocess
import sys
import json
from pathlib import Path
import yaml

def print_status(status, message, details=""):
    """Print color-coded status messages"""
    colors = {
        "✅": "\033[92m",  # Green
        "❌": "\033[91m",  # Red  
        "⚠️": "\033[93m",  # Yellow
        "ℹ️": "\033[94m",  # Blue
        "🔍": "\033[96m",  # Cyan
    }
    reset = "\033[0m"
    
    icon = status[0] if len(status) > 1 else "ℹ️"
    color = colors.get(icon, "")
    
    print(f"{color}{status} {message}{reset}")
    if details:
        print(f"   {details}")

def check_pyproject_toml():
    """Verify pyproject.toml is PyPI-ready"""
    print_status("🔍", "Checking pyproject.toml configuration...")
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print_status("❌", "pyproject.toml not found")
        return False
        
    try:
        with open(pyproject_path) as f:
            content = f.read()
            
        # Check for required fields
        required_fields = [
            'name = "fss-mini-rag"',
            'version = "2.1.0"',
            'description =',
            'authors =',
            'readme = "README.md"',
            'license =',
            'requires-python =',
            'classifiers =',
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in content:
                missing_fields.append(field)
                
        if missing_fields:
            print_status("❌", "Missing required fields in pyproject.toml:")
            for field in missing_fields:
                print(f"   - {field}")
            return False
            
        # Check CLI entry point
        if 'rag-mini = "mini_rag.cli:cli"' not in content:
            print_status("❌", "CLI entry point not configured correctly")
            return False
            
        print_status("✅", "pyproject.toml is PyPI-ready")
        return True
        
    except Exception as e:
        print_status("❌", f"Error reading pyproject.toml: {e}")
        return False

def check_github_workflow():
    """Verify GitHub Actions workflow exists and is correct"""
    print_status("🔍", "Checking GitHub Actions workflow...")
    
    workflow_path = Path(".github/workflows/build-and-release.yml")
    if not workflow_path.exists():
        print_status("❌", "GitHub Actions workflow not found")
        return False
        
    try:
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)
            
        # Check key components
        required_jobs = ["build-wheels", "build-zipapp", "test-installation", "publish", "create-release"]
        actual_jobs = list(workflow.get("jobs", {}).keys())
        
        missing_jobs = [job for job in required_jobs if job not in actual_jobs]
        if missing_jobs:
            print_status("❌", f"Missing workflow jobs: {missing_jobs}")
            return False
            
        # Check PyPI token reference
        publish_job = workflow["jobs"]["publish"]
        if "secrets.PYPI_API_TOKEN" not in str(publish_job):
            print_status("❌", "PYPI_API_TOKEN not referenced in publish job")
            return False
            
        print_status("✅", "GitHub Actions workflow is complete")
        return True
        
    except Exception as e:
        print_status("❌", f"Error checking workflow: {e}")
        return False

def check_installers():
    """Verify one-line installers exist"""
    print_status("🔍", "Checking one-line installers...")
    
    installers = ["install.sh", "install.ps1"]
    all_exist = True
    
    for installer in installers:
        if Path(installer).exists():
            print_status("✅", f"{installer} exists")
        else:
            print_status("❌", f"{installer} missing")
            all_exist = False
            
    return all_exist

def check_documentation():
    """Verify documentation is complete"""
    print_status("🔍", "Checking documentation...")
    
    docs = ["README.md", "docs/PYPI_PUBLICATION_GUIDE.md"]
    all_exist = True
    
    for doc in docs:
        if Path(doc).exists():
            print_status("✅", f"{doc} exists")
        else:
            print_status("❌", f"{doc} missing")
            all_exist = False
            
    # Check README has installation instructions
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text()
        if "pip install fss-mini-rag" in content:
            print_status("✅", "README includes pip installation")
        else:
            print_status("⚠️", "README missing pip installation example")
            
    return all_exist

def check_git_status():
    """Check git repository status"""
    print_status("🔍", "Checking git repository status...")
    
    try:
        # Check if we're in a git repo
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print_status("⚠️", "Uncommitted changes detected:")
            print(f"   {result.stdout.strip()}")
            print_status("ℹ️", "Consider committing before launch")
        else:
            print_status("✅", "Working directory is clean")
            
        # Check current branch
        result = subprocess.run(["git", "branch", "--show-current"], 
                              capture_output=True, text=True, check=True)
        branch = result.stdout.strip()
        
        if branch == "main":
            print_status("✅", "On main branch")
        else:
            print_status("⚠️", f"On branch '{branch}', consider switching to main")
            
        # Check if we have a remote
        result = subprocess.run(["git", "remote", "-v"], 
                              capture_output=True, text=True, check=True)
        if "github.com" in result.stdout:
            print_status("✅", "GitHub remote configured")
        else:
            print_status("❌", "GitHub remote not found")
            return False
            
        return True
        
    except subprocess.CalledProcessError as e:
        print_status("❌", f"Git error: {e}")
        return False

def check_package_buildable():
    """Test if package can be built locally"""
    print_status("🔍", "Testing local package build...")
    
    try:
        # Try to build the package
        result = subprocess.run([sys.executable, "-m", "build", "--sdist", "--outdir", "/tmp/build-test"], 
                              capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print_status("✅", "Package builds successfully")
            # Clean up
            subprocess.run(["rm", "-rf", "/tmp/build-test"], capture_output=True)
            return True
        else:
            print_status("❌", "Package build failed:")
            print(f"   {result.stderr}")
            return False
            
    except FileNotFoundError:
        print_status("⚠️", "build module not available (install with: pip install build)")
        return True  # Not critical for launch
    except Exception as e:
        print_status("❌", f"Build test error: {e}")
        return False

def estimate_launch_time():
    """Estimate launch timeline"""
    print_status("🔍", "Estimating launch timeline...")
    
    phases = {
        "Setup (PyPI account + token)": "15-30 minutes",
        "Test launch (v2.1.0-test)": "45-60 minutes", 
        "Production launch (v2.1.0)": "45-60 minutes",
        "Validation & testing": "30-45 minutes"
    }
    
    print_status("ℹ️", "Estimated launch timeline:")
    total_min = 0
    for phase, time in phases.items():
        print(f"   {phase}: {time}")
        # Extract max minutes for total
        max_min = int(time.split("-")[1].split()[0]) if "-" in time else int(time.split()[0])
        total_min += max_min
        
    hours = total_min / 60
    print_status("ℹ️", f"Total estimated time: {total_min} minutes ({hours:.1f} hours)")
    
    if hours <= 6:
        print_status("✅", "6-hour launch window is achievable")
    else:
        print_status("⚠️", "May exceed 6-hour window")

def generate_launch_checklist():
    """Generate a launch day checklist"""
    checklist_path = Path("LAUNCH_CHECKLIST.txt")
    
    checklist = """FSS-Mini-RAG PyPI Launch Checklist

PRE-LAUNCH (30 minutes):
□ PyPI account created and verified
□ PyPI API token generated (entire account scope)
□ GitHub Secret PYPI_API_TOKEN added
□ All files committed and pushed to GitHub
□ Working directory clean (git status)

TEST LAUNCH (45-60 minutes):
□ Create test tag: git tag v2.1.0-test
□ Push test tag: git push origin v2.1.0-test
□ Monitor GitHub Actions workflow
□ Verify test package on PyPI
□ Test installation: pip install fss-mini-rag==2.1.0-test
□ Verify CLI works: rag-mini --help

PRODUCTION LAUNCH (45-60 minutes):
□ Create production tag: git tag v2.1.0
□ Push production tag: git push origin v2.1.0
□ Monitor GitHub Actions workflow
□ Verify package on PyPI: https://pypi.org/project/fss-mini-rag/
□ Test installation: pip install fss-mini-rag
□ Verify GitHub release created with assets

POST-LAUNCH VALIDATION (30 minutes):
□ Test one-line installer (Linux/macOS)
□ Test PowerShell installer (Windows, if available)
□ Verify all documentation links work
□ Check package metadata on PyPI
□ Test search: pip search fss-mini-rag (if available)

SUCCESS CRITERIA:
□ PyPI package published and installable
□ CLI command works after installation
□ GitHub release has professional appearance
□ All installation methods documented and working
□ No broken links in documentation

EMERGENCY CONTACTS:
- PyPI Support: https://pypi.org/help/
- GitHub Actions Status: https://www.githubstatus.com/
- Python Packaging Guide: https://packaging.python.org/

ROLLBACK PROCEDURES:
- Yank PyPI release if critical issues found
- Delete and recreate tags if needed
- Re-run failed GitHub Actions workflows
"""
    
    checklist_path.write_text(checklist)
    print_status("✅", f"Launch checklist created: {checklist_path}")

def main():
    """Run all launch readiness checks"""
    print_status("🚀", "FSS-Mini-RAG Launch Readiness Check")
    print("=" * 60)
    
    checks = [
        ("Package Configuration", check_pyproject_toml),
        ("GitHub Workflow", check_github_workflow),
        ("Installers", check_installers), 
        ("Documentation", check_documentation),
        ("Git Repository", check_git_status),
        ("Package Build", check_package_buildable),
    ]
    
    results = {}
    for name, check_func in checks:
        print(f"\n{name}:")
        results[name] = check_func()
        
    print(f"\n{'=' * 60}")
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    if passed == total:
        print_status("✅", f"ALL CHECKS PASSED ({passed}/{total})")
        print_status("🚀", "FSS-Mini-RAG is READY FOR PYPI LAUNCH!")
        print_status("ℹ️", "Next steps:")
        print("   1. Set up PyPI account and API token")
        print("   2. Follow PYPI_LAUNCH_PLAN.md")
        print("   3. Launch with confidence! 🎉")
    else:
        failed = total - passed
        print_status("⚠️", f"SOME CHECKS FAILED ({passed}/{total} passed, {failed} failed)")
        print_status("ℹ️", "Address failed checks before launching")
        
    estimate_launch_time()
    generate_launch_checklist()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Analyze the GitHub Actions workflow for potential issues and improvements.
"""

import yaml
from pathlib import Path

def analyze_workflow():
    """Analyze the GitHub Actions workflow file."""
    print("🔍 GitHub Actions Workflow Analysis")
    print("=" * 50)
    
    workflow_file = Path(__file__).parent.parent / ".github/workflows/build-and-release.yml"
    
    if not workflow_file.exists():
        print("❌ Workflow file not found")
        return False
    
    try:
        with open(workflow_file, 'r') as f:
            workflow = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to parse YAML: {e}")
        return False
    
    print("✅ Workflow YAML is valid")
    
    # Analyze workflow structure
    print("\n📋 Workflow Structure Analysis:")
    
    # Check triggers
    triggers = workflow.get('on', {})
    print(f"   Triggers: {list(triggers.keys())}")
    
    if 'push' in triggers:
        push_config = triggers['push']
        if 'tags' in push_config:
            print(f"   ✅ Tag triggers: {push_config['tags']}")
        if 'branches' in push_config:
            print(f"   ✅ Branch triggers: {push_config['branches']}")
    
    if 'workflow_dispatch' in triggers:
        print("   ✅ Manual trigger enabled")
    
    # Analyze jobs
    jobs = workflow.get('jobs', {})
    print(f"\n🛠️  Jobs ({len(jobs)}):")
    
    for job_name, job_config in jobs.items():
        print(f"   📋 {job_name}:")
        
        # Check dependencies
        needs = job_config.get('needs', [])
        if needs:
            if isinstance(needs, list):
                print(f"      Dependencies: {', '.join(needs)}")
            else:
                print(f"      Dependencies: {needs}")
        
        # Check conditions
        if 'if' in job_config:
            print(f"      Condition: {job_config['if']}")
        
        # Check matrix
        strategy = job_config.get('strategy', {})
        if 'matrix' in strategy:
            matrix = strategy['matrix']
            for key, values in matrix.items():
                print(f"      Matrix {key}: {values}")
    
    return True

def check_potential_issues():
    """Check for potential issues in the workflow."""
    print("\n🔍 Potential Issues Analysis:")
    
    issues = []
    warnings = []
    
    workflow_file = Path(__file__).parent.parent / ".github/workflows/build-and-release.yml"
    content = workflow_file.read_text()
    
    # Check for common issues
    if 'PYPI_API_TOKEN' in content:
        if 'secrets.PYPI_API_TOKEN' not in content:
            issues.append("PyPI token referenced but not as secret")
        else:
            print("   ✅ PyPI token properly referenced as secret")
    
    if 'upload-artifact@v3' in content:
        warnings.append("Using upload-artifact@v3 - consider upgrading to v4")
    
    if 'setup-python@v4' in content:
        warnings.append("Using setup-python@v4 - consider upgrading to v5")
    
    if 'actions/checkout@v4' in content:
        print("   ✅ Using recent checkout action version")
    
    # Check cibuildwheel configuration
    if 'cibuildwheel@v2.16' in content:
        warnings.append("cibuildwheel version might be outdated - check for latest")
    
    if 'CIBW_TEST_COMMAND: "rag-mini --help"' in content:
        print("   ✅ Wheel testing configured")
    
    # Check for environment setup
    if 'environment: release' in content:
        print("   ✅ Release environment configured for security")
    
    # Check matrix strategy
    if 'ubuntu-latest, windows-latest, macos-13, macos-14' in content:
        print("   ✅ Good OS matrix coverage")
    
    if 'python-version: [\'3.8\', \'3.11\', \'3.12\']' in content:
        print("   ✅ Good Python version coverage")
    
    # Output results
    if issues:
        print(f"\n❌ Critical Issues ({len(issues)}):")
        for issue in issues:
            print(f"   • {issue}")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not issues and not warnings:
        print("\n✅ No critical issues or warnings found")
    
    return len(issues) == 0

def check_secrets_requirements():
    """Check what secrets are required."""
    print("\n🔐 Required Secrets Analysis:")
    
    print("   Required GitHub Secrets:")
    print("   ✅ GITHUB_TOKEN (automatically provided)")
    print("   ⚠️  PYPI_API_TOKEN (needs manual setup)")
    
    print("\n   Setup Instructions:")
    print("   1. Go to PyPI.org → Account Settings → API Tokens")
    print("   2. Create token with 'Entire account' scope")
    print("   3. Go to GitHub repo → Settings → Secrets → Actions")
    print("   4. Add secret named 'PYPI_API_TOKEN' with the token value")
    
    print("\n   Optional Setup:")
    print("   • TestPyPI token for testing (TESTPYPI_API_TOKEN)")
    print("   • Release environment protection rules")

def check_file_paths():
    """Check if referenced files exist."""
    print("\n📁 File References Check:")
    
    project_root = Path(__file__).parent.parent
    
    files_to_check = [
        ("requirements.txt", "Dependencies file"),
        ("scripts/build_pyz.py", "Zipapp build script"),
        ("pyproject.toml", "Package configuration"),
    ]
    
    all_exist = True
    for file_path, description in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {description}: {file_path}")
        else:
            print(f"   ❌ Missing {description}: {file_path}")
            all_exist = False
    
    return all_exist

def estimate_ci_costs():
    """Estimate CI costs and runtime."""
    print("\n💰 CI Cost & Runtime Estimation:")
    
    print("   Job Matrix:")
    print("   • build-wheels: 4 OS × ~20 min = 80 minutes")
    print("   • build-zipapp: 1 job × ~10 min = 10 minutes")
    print("   • test-installation: 7 combinations × ~5 min = 35 minutes")
    print("   • publish: 1 job × ~2 min = 2 minutes")
    print("   • create-release: 1 job × ~2 min = 2 minutes")
    
    print("\n   Total estimated runtime: ~45-60 minutes per release")
    print("   GitHub Actions free tier: 2000 minutes/month")
    print("   Estimated releases per month with free tier: ~30-40")
    
    print("\n   Optimization suggestions:")
    print("   • Cache dependencies to reduce build time")
    print("   • Run tests only on main Python versions")
    print("   • Use conditional jobs for PR vs release builds")

def main():
    """Run all analyses."""
    success = True
    
    if not analyze_workflow():
        success = False
    
    if not check_potential_issues():
        success = False
    
    check_secrets_requirements()
    
    if not check_file_paths():
        success = False
    
    estimate_ci_costs()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 GitHub Actions workflow looks good!")
        print("✅ Ready for production use")
        print("\n📋 Next steps:")
        print("   1. Set up PYPI_API_TOKEN secret in GitHub")
        print("   2. Test with a release tag: git tag v2.1.0-test && git push origin v2.1.0-test")
        print("   3. Monitor the workflow execution")
        print("   4. Verify artifacts are created correctly")
    else:
        print("❌ Issues found - fix before using")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
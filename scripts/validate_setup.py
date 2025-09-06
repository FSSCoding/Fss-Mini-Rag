#!/usr/bin/env python3
"""
Validate that the distribution setup files are correctly created.
This doesn't require dependencies, just validates file structure.
"""

import json
import re
import sys
from pathlib import Path

def main():
    """Validate distribution setup files."""
    print("🔍 FSS-Mini-RAG Setup Validation")
    print("=" * 40)
    
    project_root = Path(__file__).parent.parent
    issues = []
    
    # 1. Check pyproject.toml
    print("1. Validating pyproject.toml...")
    pyproject_file = project_root / "pyproject.toml"
    if not pyproject_file.exists():
        issues.append("pyproject.toml missing")
    else:
        content = pyproject_file.read_text()
        
        # Check key elements
        checks = [
            ('name = "fss-mini-rag"', "Package name"),
            ('rag-mini = "mini_rag.cli:cli"', "Console script entry point"),
            ('requires-python = ">=3.8"', "Python version requirement"),
            ('MIT', "License"),
            ('Brett Fox', "Author"),
        ]
        
        for check, desc in checks:
            if check in content:
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ {desc} missing")
                issues.append(f"pyproject.toml missing: {desc}")
    
    # 2. Check install scripts
    print("\n2. Validating install scripts...")
    
    # Linux/macOS script
    install_sh = project_root / "install.sh"
    if install_sh.exists():
        content = install_sh.read_text()
        if "curl -LsSf https://astral.sh/uv/install.sh" in content:
            print("   ✅ install.sh has uv installation")
        if "pipx install" in content:
            print("   ✅ install.sh has pipx fallback")
        if "pip install --user" in content:
            print("   ✅ install.sh has pip fallback")
    else:
        issues.append("install.sh missing")
        print("   ❌ install.sh missing")
    
    # Windows script
    install_ps1 = project_root / "install.ps1"
    if install_ps1.exists():
        content = install_ps1.read_text()
        if "Install-UV" in content:
            print("   ✅ install.ps1 has uv installation")
        if "Install-WithPipx" in content:
            print("   ✅ install.ps1 has pipx fallback")
        if "Install-WithPip" in content:
            print("   ✅ install.ps1 has pip fallback")
    else:
        issues.append("install.ps1 missing")
        print("   ❌ install.ps1 missing")
    
    # 3. Check build scripts
    print("\n3. Validating build scripts...")
    
    build_pyz = project_root / "scripts" / "build_pyz.py"
    if build_pyz.exists():
        content = build_pyz.read_text()
        if "zipapp.create_archive" in content:
            print("   ✅ build_pyz.py uses zipapp")
        if "__main__.py" in content:
            print("   ✅ build_pyz.py creates entry point")
    else:
        issues.append("scripts/build_pyz.py missing")
        print("   ❌ scripts/build_pyz.py missing")
    
    # 4. Check GitHub workflow
    print("\n4. Validating GitHub workflow...")
    
    workflow_file = project_root / ".github" / "workflows" / "build-and-release.yml"
    if workflow_file.exists():
        content = workflow_file.read_text()
        if "cibuildwheel" in content:
            print("   ✅ Workflow uses cibuildwheel")
        if "upload-artifact" in content:
            print("   ✅ Workflow uploads artifacts")
        if "pypa/gh-action-pypi-publish" in content:
            print("   ✅ Workflow publishes to PyPI")
    else:
        issues.append(".github/workflows/build-and-release.yml missing")
        print("   ❌ GitHub workflow missing")
    
    # 5. Check README updates
    print("\n5. Validating README updates...")
    
    readme_file = project_root / "README.md"
    if readme_file.exists():
        content = readme_file.read_text()
        if "One-Line Installers" in content:
            print("   ✅ README has new installation section")
        if "curl -fsSL" in content:
            print("   ✅ README has Linux/macOS installer")
        if "iwr" in content:
            print("   ✅ README has Windows installer")
        if "uv tool install" in content:
            print("   ✅ README has uv instructions")
        if "pipx install" in content:
            print("   ✅ README has pipx instructions")
    else:
        issues.append("README.md missing")
        print("   ❌ README.md missing")
    
    # 6. Check Makefile
    print("\n6. Validating Makefile...")
    
    makefile = project_root / "Makefile"
    if makefile.exists():
        content = makefile.read_text()
        if "build-pyz:" in content:
            print("   ✅ Makefile has pyz build target")
        if "test-dist:" in content:
            print("   ✅ Makefile has distribution test target")
    else:
        print("   ⚠️  Makefile missing (optional)")
    
    # Summary
    print(f"\n{'='*40}")
    if issues:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n🔧 Please fix the issues above before proceeding.")
        return 1
    else:
        print("🎉 All setup files are valid!")
        print("\n📋 Next steps:")
        print("   1. Test installation in a clean environment")
        print("   2. Commit and push changes to GitHub")
        print("   3. Create a release to trigger wheel building")
        print("   4. Test the install scripts:")
        print("      curl -fsSL https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.sh | bash")
        return 0

if __name__ == "__main__":
    sys.exit(main())
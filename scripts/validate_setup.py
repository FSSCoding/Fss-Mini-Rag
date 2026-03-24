#!/usr/bin/env python3
"""
Validate that the distribution setup files are correctly configured.
Checks file structure, metadata, and build readiness.
"""

import sys
from pathlib import Path


def main():
    """Validate distribution setup files."""
    print("FSS-Mini-RAG Setup Validation")
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

        checks = [
            ('name = "fss-mini-rag"', "Package name"),
            ('rag-mini = "mini_rag.cli:cli"', "Console script entry point"),
            ('rag-mini-gui = "mini_rag.gui:main"', "GUI entry point"),
            ("MIT", "License"),
            ("Brett Fox", "Author"),
        ]

        for check, desc in checks:
            if check in content:
                print(f"   OK: {desc}")
            else:
                print(f"   MISSING: {desc}")
                issues.append(f"pyproject.toml missing: {desc}")

    # 2. Check requirements.txt
    print("\n2. Validating requirements.txt...")
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        issues.append("requirements.txt missing")
        print("   MISSING: requirements.txt")
    else:
        content = req_file.read_text()
        required_deps = ["lancedb", "click", "rich", "rank-bm25", "beautifulsoup4", "pymupdf", "sv-ttk"]
        for dep in required_deps:
            if dep in content:
                print(f"   OK: {dep}")
            else:
                print(f"   MISSING: {dep}")
                issues.append(f"requirements.txt missing: {dep}")

    # 3. Check core modules exist
    print("\n3. Validating core modules...")
    core_modules = [
        "mini_rag/__init__.py",
        "mini_rag/cli.py",
        "mini_rag/search.py",
        "mini_rag/indexer.py",
        "mini_rag/chunker.py",
        "mini_rag/ollama_embeddings.py",
        "mini_rag/config.py",
        "mini_rag/llm_synthesizer.py",
        "mini_rag/deep_research.py",
        "mini_rag/web_scraper.py",
        "mini_rag/search_engines.py",
        "mini_rag/extractors.py",
        "mini_rag/rate_limiter.py",
        "mini_rag/gui/__init__.py",
        "mini_rag/gui/app.py",
    ]
    for module in core_modules:
        path = project_root / module
        if path.exists():
            print(f"   OK: {module}")
        else:
            print(f"   MISSING: {module}")
            issues.append(f"Missing module: {module}")

    # 4. Check build scripts
    print("\n4. Validating build scripts...")

    build_pyz = project_root / "scripts" / "build_pyz.py"
    if build_pyz.exists():
        content = build_pyz.read_text()
        if "zipapp.create_archive" in content:
            print("   OK: build_pyz.py uses zipapp")
    else:
        issues.append("scripts/build_pyz.py missing")
        print("   MISSING: scripts/build_pyz.py")

    # 5. Check GitHub workflow
    print("\n5. Validating GitHub workflows...")

    workflow_file = project_root / ".github" / "workflows" / "build-and-release.yml"
    if workflow_file.exists():
        content = workflow_file.read_text()
        if "build-wheel" in content:
            print("   OK: build-and-release.yml has wheel build")
        if "create-release" in content or "action-gh-release" in content:
            print("   OK: build-and-release.yml creates GitHub releases")
        if "build-windows-installer" in content:
            print("   OK: build-and-release.yml has Windows installer build")
        if "build-deb" in content or "build-appimage" in content:
            print("   OK: build-and-release.yml has Linux package builds")
    else:
        print("   WARNING: build-and-release.yml missing")

    ci_file = project_root / ".github" / "workflows" / "ci.yml"
    if ci_file.exists():
        print("   OK: ci.yml exists")
    else:
        print("   WARNING: ci.yml missing")

    # 6. Check Windows installer
    print("\n6. Validating install scripts...")

    win_installer = project_root / "install_windows.bat"
    if win_installer.exists():
        content = win_installer.read_text()
        if "rag-mini" in content:
            print("   OK: install_windows.bat references rag-mini CLI")
        if "pip install -e" in content or "pip install -r" in content:
            print("   OK: install_windows.bat installs dependencies")
    else:
        print("   WARNING: install_windows.bat missing")

    # 7. Check Makefile
    print("\n7. Validating Makefile...")
    makefile = project_root / "Makefile"
    if makefile.exists():
        content = makefile.read_text()
        if "build-pyz:" in content:
            print("   OK: Makefile has pyz build target")
        if "dev-install:" in content:
            print("   OK: Makefile has dev-install target")
    else:
        print("   WARNING: Makefile missing (optional)")

    # 8. Version consistency
    print("\n8. Checking version consistency...")
    versions_found = []

    if pyproject_file.exists():
        content = pyproject_file.read_text()
        for line in content.splitlines():
            if line.strip().startswith('version = "'):
                ver = line.split('"')[1]
                versions_found.append(("pyproject.toml", ver))
                print(f"   pyproject.toml: {ver}")

    init_file = project_root / "mini_rag" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        for line in content.splitlines():
            if "__version__" in line and "=" in line:
                ver = line.split('"')[1]
                versions_found.append(("__init__.py", ver))
                print(f"   __init__.py: {ver}")

    if len(set(v for _, v in versions_found)) > 1:
        issues.append("Version mismatch between pyproject.toml and __init__.py")
        print("   MISMATCH: versions differ!")
    elif versions_found:
        print("   OK: versions match")

    # Summary
    print(f"\n{'=' * 40}")
    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    else:
        print("All checks passed!")
        print("\nNext steps:")
        print("  1. Test in a clean venv: python -m venv test && source test/bin/activate && pip install -e .")
        print("  2. Verify CLI: rag-mini --help")
        print("  3. Build wheel: python -m build")
        print("  4. Tag release: git tag v2.3.0 && git push --tags")
        return 0


if __name__ == "__main__":
    sys.exit(main())

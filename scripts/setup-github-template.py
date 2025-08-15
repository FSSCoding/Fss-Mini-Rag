#!/usr/bin/env python3
"""
GitHub Template Setup Script

Converts a project to use the auto-update template system.
This script helps migrate projects from Gitea to GitHub with auto-update capability.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

def setup_project_template(
    project_path: Path,
    repo_owner: str,
    repo_name: str,
    project_type: str = "python",
    include_auto_update: bool = True
) -> bool:
    """
    Setup a project to use the GitHub auto-update template system.
    
    Args:
        project_path: Path to the project directory
        repo_owner: GitHub username/organization
        repo_name: GitHub repository name  
        project_type: Type of project (python, general)
        include_auto_update: Whether to include auto-update system
        
    Returns:
        True if setup successful
    """
    
    print(f"🚀 Setting up GitHub template for: {repo_owner}/{repo_name}")
    print(f"📁 Project path: {project_path}")
    print(f"🔧 Project type: {project_type}")
    print(f"🔄 Auto-update: {'Enabled' if include_auto_update else 'Disabled'}")
    print()
    
    try:
        # Create .github directory structure
        github_dir = project_path / ".github"
        workflows_dir = github_dir / "workflows"
        templates_dir = github_dir / "ISSUE_TEMPLATE"
        
        # Ensure directories exist
        workflows_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Setup GitHub Actions workflows
        setup_workflows(workflows_dir, repo_owner, repo_name, project_type)
        
        # 2. Setup auto-update system if requested
        if include_auto_update:
            setup_auto_update_system(project_path, repo_owner, repo_name)
            
        # 3. Create issue templates
        setup_issue_templates(templates_dir)
        
        # 4. Create/update project configuration
        setup_project_config(project_path, repo_owner, repo_name, include_auto_update)
        
        # 5. Create README template if needed
        setup_readme_template(project_path, repo_owner, repo_name)
        
        print("✅ GitHub template setup completed successfully!")
        print()
        print("📋 Next Steps:")
        print("1. Commit and push these changes to GitHub")
        print("2. Create your first release: git tag v1.0.0 && git push --tags")
        print("3. Test auto-update system: ./project check-update")
        print("4. Enable GitHub Pages for documentation (optional)")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def setup_workflows(workflows_dir: Path, repo_owner: str, repo_name: str, project_type: str):
    """Setup GitHub Actions workflow files."""
    
    print("🔧 Setting up GitHub Actions workflows...")
    
    # Release workflow
    release_workflow = f"""name: Auto Release & Update System
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release (e.g., v1.2.3)'
        required: true
        type: string

jobs:
  create-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        
    - name: Extract version
      id: version
      run: |
        if [ "${{{{ github.event_name }}}}" = "workflow_dispatch" ]; then
          VERSION="${{{{ github.event.inputs.version }}}}"
        else
          VERSION=${{GITHUB_REF#refs/tags/}}
        fi
        echo "version=$VERSION" >> $GITHUB_OUTPUT
        echo "clean_version=${{VERSION#v}}" >> $GITHUB_OUTPUT
        
    - name: Update version in code
      run: |
        VERSION="${{{{ steps.version.outputs.clean_version }}}}"
        # Update version files
        find . -name "__init__.py" -exec sed -i 's/__version__ = ".*"/__version__ = "'$VERSION'"/' {{}} +
        
    - name: Generate release notes
      id: release_notes
      run: |
        VERSION="${{{{ steps.version.outputs.version }}}}"
        
        # Get commits since last tag
        LAST_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "")
        if [ -n "$LAST_TAG" ]; then
          COMMITS=$(git log --oneline $LAST_TAG..HEAD --pretty=format:"• %s")
        else
          COMMITS=$(git log --oneline --pretty=format:"• %s" | head -10)
        fi
        
        # Create release notes
        cat > release_notes.md << EOF
        ## What's New in $VERSION
        
        ### 🚀 Changes
        $COMMITS
        
        ### 📥 Installation
        Download and install the latest version:
        \`\`\`bash
        curl -sSL https://github.com/{repo_owner}/{repo_name}/releases/latest/download/install.sh | bash
        \`\`\`
        
        ### 🔄 Auto-Update
        If you have auto-update support:
        \`\`\`bash
        ./{repo_name} check-update
        ./{repo_name} update
        \`\`\`
        EOF
        
    - name: Create GitHub Release
      uses: softprops/action-gh-release@v2
      with:
        tag_name: ${{{{ steps.version.outputs.version }}}}
        name: Release ${{{{ steps.version.outputs.version }}}}
        body_path: release_notes.md
        draft: false
        prerelease: false
        files: |
          *.sh
          *.bat
          requirements.txt
"""
    
    (workflows_dir / "release.yml").write_text(release_workflow)
    
    # CI workflow for Python projects
    if project_type == "python":
        ci_workflow = f"""name: CI/CD Pipeline
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{{{ matrix.os }}}}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v5
      with:
        python-version: ${{{{ matrix.python-version }}}}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        python -c "import {repo_name.replace('-', '_')}; print('✅ Import successful')"
        
    - name: Test auto-update system
      run: |
        python -c "
        try:
            from {repo_name.replace('-', '_')}.updater import UpdateChecker
            print('✅ Auto-update system available')
        except ImportError:
            print('⚠️ Auto-update not available')
        "
"""
        (workflows_dir / "ci.yml").write_text(ci_workflow)
    
    print("  ✅ GitHub Actions workflows created")

def setup_auto_update_system(project_path: Path, repo_owner: str, repo_name: str):
    """Setup the auto-update system for the project."""
    
    print("🔄 Setting up auto-update system...")
    
    # Copy updater.py from FSS-Mini-RAG as template
    template_updater = Path(__file__).parent.parent / "mini_rag" / "updater.py"
    
    if template_updater.exists():
        # Create project module directory if needed
        module_name = repo_name.replace('-', '_')
        module_dir = project_path / module_name
        module_dir.mkdir(exist_ok=True)
        
        # Copy and customize updater
        target_updater = module_dir / "updater.py"
        shutil.copy2(template_updater, target_updater)
        
        # Customize for this project
        content = target_updater.read_text()
        content = content.replace('repo_owner: str = "FSSCoding"', f'repo_owner: str = "{repo_owner}"')
        content = content.replace('repo_name: str = "Fss-Mini-Rag"', f'repo_name: str = "{repo_name}"')
        target_updater.write_text(content)
        
        # Update __init__.py to include updater
        init_file = module_dir / "__init__.py"
        if init_file.exists():
            content = init_file.read_text()
            if "updater" not in content:
                content += """
# Auto-update system (graceful import for legacy versions)
try:
    from .updater import UpdateChecker, check_for_updates, get_updater
    __all__.extend(["UpdateChecker", "check_for_updates", "get_updater"])
except ImportError:
    pass
"""
                init_file.write_text(content)
        
        print("  ✅ Auto-update system configured")
    else:
        print("  ⚠️ Template updater not found, you'll need to implement manually")

def setup_issue_templates(templates_dir: Path):
    """Setup GitHub issue templates."""
    
    print("📝 Setting up issue templates...")
    
    bug_template = """---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment:**
 - OS: [e.g. Ubuntu 22.04, Windows 11, macOS 13]
 - Python version: [e.g. 3.11.2]
 - Project version: [e.g. 1.2.3]

**Additional context**
Add any other context about the problem here.
"""
    
    feature_template = """---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
"""
    
    (templates_dir / "bug_report.md").write_text(bug_template)
    (templates_dir / "feature_request.md").write_text(feature_template)
    
    print("  ✅ Issue templates created")

def setup_project_config(project_path: Path, repo_owner: str, repo_name: str, include_auto_update: bool):
    """Setup project configuration file."""
    
    print("⚙️ Setting up project configuration...")
    
    config = {
        "project": {
            "name": repo_name,
            "owner": repo_owner,
            "github_url": f"https://github.com/{repo_owner}/{repo_name}",
            "auto_update_enabled": include_auto_update
        },
        "github": {
            "template_version": "1.0.0",
            "last_sync": None,
            "workflows_enabled": True
        }
    }
    
    config_file = project_path / ".github" / "project-config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("  ✅ Project configuration created")

def setup_readme_template(project_path: Path, repo_owner: str, repo_name: str):
    """Setup README template if one doesn't exist."""
    
    readme_file = project_path / "README.md"
    
    if not readme_file.exists():
        print("📖 Creating README template...")
        
        readme_content = f"""# {repo_name}

> A brief description of your project

## Quick Start

```bash
# Installation
curl -sSL https://github.com/{repo_owner}/{repo_name}/releases/latest/download/install.sh | bash

# Usage
./{repo_name} --help
```

## Features

- ✨ Feature 1
- 🚀 Feature 2  
- 🔧 Feature 3

## Installation

### Automated Install
```bash
curl -sSL https://github.com/{repo_owner}/{repo_name}/releases/latest/download/install.sh | bash
```

### Manual Install
```bash
git clone https://github.com/{repo_owner}/{repo_name}.git
cd {repo_name}
./install.sh
```

## Usage

Basic usage:
```bash
./{repo_name} command [options]
```

## Auto-Update

This project includes automatic update checking:

```bash
# Check for updates
./{repo_name} check-update

# Install updates
./{repo_name} update
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

---

🤖 **Auto-Update Enabled**: This project will notify you of new versions automatically!
"""
        
        readme_file.write_text(readme_content)
        print("  ✅ README template created")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup GitHub template with auto-update system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup-github-template.py myproject --owner username --name my-project
  python setup-github-template.py /path/to/project --owner org --name cool-tool --no-auto-update
        """
    )
    
    parser.add_argument('project_path', type=Path, help='Path to project directory')
    parser.add_argument('--owner', required=True, help='GitHub username or organization')
    parser.add_argument('--name', required=True, help='GitHub repository name')
    parser.add_argument('--type', choices=['python', 'general'], default='python', 
                       help='Project type (default: python)')
    parser.add_argument('--no-auto-update', action='store_true', 
                       help='Disable auto-update system')
    
    args = parser.parse_args()
    
    if not args.project_path.exists():
        print(f"❌ Project path does not exist: {args.project_path}")
        sys.exit(1)
        
    success = setup_project_template(
        project_path=args.project_path,
        repo_owner=args.owner,
        repo_name=args.name,
        project_type=args.type,
        include_auto_update=not args.no_auto_update
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
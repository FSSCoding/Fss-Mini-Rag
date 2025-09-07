# Python Packaging Templates for Professional Distribution

This collection of templates allows you to quickly set up professional Python package distribution for any CLI tool or library. Based on the successful FSS-Mini-RAG implementation.

## 🚀 **What This Gives You**

- **One-line installers** for Linux/macOS/Windows
- **Smart package manager fallbacks** (uv → pipx → pip)
- **Professional GitHub Actions CI/CD** with automated PyPI publishing
- **Cross-platform wheel building** (Windows/macOS/Linux)
- **Portable single-file distributions** (.pyz zipapps)
- **Complete PyPI publication workflow**

## 📁 **Template Files**

### **Core Configuration**
- `pyproject-template.toml` - Complete package configuration with PyPI metadata
- `build_pyz_template.py` - Script for creating portable .pyz distributions

### **One-Line Installers**
- `install-template.sh` - Smart Linux/macOS installer with fallbacks
- `install-template.ps1` - Windows PowerShell installer

### **CI/CD Pipeline**
- `python-package-workflow.yml` - Complete GitHub Actions workflow for automated building and publishing

## 🛠️ **Quick Start for New Projects**

### **1. Copy Template Files**
```bash
# Copy the workflow
cp templates/github-actions/python-package-workflow.yml .github/workflows/build-and-release.yml

# Copy package configuration
cp templates/python-packaging/pyproject-template.toml pyproject.toml

# Copy installers
cp templates/installers/install-template.sh install.sh
cp templates/installers/install-template.ps1 install.ps1
```

### **2. Customize for Your Project**
Search for `# CUSTOMIZE:` comments in each file and update:

**In `pyproject.toml`:**
- Package name, version, description
- Your name and email
- GitHub repository URLs
- CLI command name and entry point
- Python version requirements

**In `install.sh` and `install.ps1`:**
- Package name and CLI command
- GitHub repository path
- Usage examples

**In `python-package-workflow.yml`:**
- CLI test command
- .pyz filename
- GitHub repository references

### **3. Set Up PyPI Publication**
1. **Create PyPI account** at https://pypi.org/account/register/
2. **Generate API token** with "Entire account" scope
3. **Add to GitHub Secrets** as `PYPI_API_TOKEN`

### **4. Test and Release**
```bash
# Test release
git tag v1.0.0-test
git push origin v1.0.0-test

# Production release
git tag v1.0.0
git push origin v1.0.0
```

## 📋 **What Gets Automated**

### **On Every Push/PR**
- ✅ Cross-platform wheel building
- ✅ Installation testing across OS/Python combinations
- ✅ Zipapp creation and testing

### **On Tag Push (Release)**
- ✅ **Automated PyPI publishing**
- ✅ **GitHub release creation** with assets
- ✅ **Professional installation instructions**
- ✅ **Changelog generation**

## 🎯 **Features You Get**

### **User Experience**
- **One-line installation** that "just works"
- **Multiple installation methods** for different users
- **Portable single-file option** for no-Python-knowledge users
- **Professional README** with clear instructions

### **Developer Experience** 
- **Automated releases** - just push a tag
- **Quality gates** - testing before publishing
- **Cross-platform support** without manual work
- **Professional package metadata**

### **Distribution Quality**
- **Follows official Python packaging standards**
- **Security best practices** (release environments, secrets)
- **Comprehensive testing** across platforms
- **Professional release assets**

## 📊 **Success Examples**

This template system has been successfully used for:

- **FSS-Mini-RAG**: Educational RAG system with 95% production readiness score
- **Cross-platform compatibility**: Windows, macOS (Intel + ARM), Linux
- **Multiple Python versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Professional CI/CD**: ~45-60 minute automated build and release cycle

## 🔧 **Advanced Customization**

### **Build Matrix Optimization**
Adjust the GitHub Actions matrix in `python-package-workflow.yml`:
- Reduce Python versions for faster builds
- Exclude problematic OS combinations
- Add specialized testing environments

### **Additional Package Managers**
The installer templates support:
- **uv** (fastest, modern)
- **pipx** (isolated environments)  
- **pip** (universal fallback)

### **Distribution Methods**
- **PyPI package** - `pip install your-package`
- **Direct wheel download** - From GitHub releases
- **Zipapp (.pyz)** - Single file, no pip needed
- **Source install** - `pip install git+https://...`

## 📚 **Best Practices Included**

- **Semantic versioning** with automated changelog
- **Security-first approach** with environment protection
- **Cross-platform compatibility** testing
- **Multiple installation paths** for different user types
- **Professional documentation** structure
- **Quality gates** preventing broken releases

## 🎉 **Result**

Using these templates transforms your Python project from a development tool into **enterprise-grade software** with:

- **Professional installation experience**
- **Automated quality assurance** 
- **Cross-platform distribution**
- **PyPI publication ready**
- **Zero-maintenance releases**

**Perfect for CLI tools, libraries, and any Python package you want to distribute professionally!** 🚀
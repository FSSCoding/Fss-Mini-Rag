# FSS-Mini-RAG Distribution Testing Plan

> **CRITICAL**: This is a comprehensive testing plan for the new distribution system. Every stage must be completed and verified before deployment.

## Overview

We've implemented a complete distribution overhaul with:
- One-line installers for Linux/macOS/Windows
- Multiple installation methods (uv, pipx, pip, zipapp)
- Automated wheel building via GitHub Actions
- PyPI publishing automation
- Cross-platform compatibility

**This testing plan ensures everything works before we ship it.**

---

## Phase 1: Local Development Environment Testing

### 1.1 Virtual Environment Setup Testing

**Objective**: Verify our package works in clean environments

**Test Environments**:
- [ ] Python 3.8 in fresh venv
- [ ] Python 3.9 in fresh venv  
- [ ] Python 3.10 in fresh venv
- [ ] Python 3.11 in fresh venv
- [ ] Python 3.12 in fresh venv

**For each Python version**:
```bash
# Test commands for each environment
python -m venv test_env_38
source test_env_38/bin/activate  # or test_env_38\Scripts\activate on Windows
python --version
pip install -e .
rag-mini --help
rag-mini init --help
rag-mini search --help
# Test basic functionality
mkdir test_project
echo "def hello(): print('world')" > test_project/test.py
rag-mini init -p test_project
rag-mini search -p test_project "hello function"
deactivate
rm -rf test_env_38 test_project
```

**Success Criteria**:
- [ ] Package installs without errors
- [ ] All CLI commands show help properly
- [ ] Basic indexing and search works
- [ ] No dependency conflicts

### 1.2 Package Metadata Testing

**Objective**: Verify pyproject.toml produces correct package metadata

**Tests**:
```bash
# Build source distribution and inspect metadata
python -m build --sdist
tar -tzf dist/*.tar.gz | grep -E "(pyproject.toml|METADATA)"
tar -xzf dist/*.tar.gz --to-stdout */METADATA

# Verify key metadata fields
python -c "
import pkg_resources
dist = pkg_resources.get_distribution('fss-mini-rag')
print(f'Name: {dist.project_name}')
print(f'Version: {dist.version}')  
print(f'Entry points: {list(dist.get_entry_map().keys())}')
"
```

**Success Criteria**:
- [ ] Package name is "fss-mini-rag" 
- [ ] Console script "rag-mini" is registered
- [ ] Version matches pyproject.toml
- [ ] Author, license, description are correct
- [ ] Python version requirements are set

---

## Phase 2: Build System Testing

### 2.1 Source Distribution Testing

**Objective**: Verify source packages build and install correctly

**Tests**:
```bash
# Clean build
rm -rf dist/ build/ *.egg-info/
python -m build --sdist

# Test source install in fresh environment
python -m venv test_sdist
source test_sdist/bin/activate
pip install dist/*.tar.gz
rag-mini --help
# Test actual functionality
mkdir test_src && echo "print('test')" > test_src/main.py
rag-mini init -p test_src
rag-mini search -p test_src "print statement"
deactivate && rm -rf test_sdist test_src
```

**Success Criteria**:
- [ ] Source distribution builds without errors
- [ ] Contains all necessary files
- [ ] Installs and runs correctly from source
- [ ] No missing dependencies

### 2.2 Wheel Building Testing

**Objective**: Test wheel generation and installation

**Tests**:
```bash
# Build wheel
python -m build --wheel

# Inspect wheel contents  
python -m zipfile -l dist/*.whl
python -m wheel unpack dist/*.whl
ls -la fss_mini_rag-*/

# Test wheel install
python -m venv test_wheel
source test_wheel/bin/activate
pip install dist/*.whl
rag-mini --version
which rag-mini
rag-mini --help
deactivate && rm -rf test_wheel
```

**Success Criteria**:
- [ ] Wheel builds successfully
- [ ] Contains correct package structure
- [ ] Installs faster than source
- [ ] Entry point is properly registered

### 2.3 Zipapp (.pyz) Building Testing  

**Objective**: Test single-file zipapp distribution

**Tests**:
```bash
# Build zipapp
python scripts/build_pyz.py

# Test direct execution
python dist/rag-mini.pyz --help
python dist/rag-mini.pyz --version

# Test with different Python versions
python3.8 dist/rag-mini.pyz --help
python3.11 dist/rag-mini.pyz --help

# Test functionality
mkdir pyz_test && echo "def test(): pass" > pyz_test/code.py
python dist/rag-mini.pyz init -p pyz_test
python dist/rag-mini.pyz search -p pyz_test "test function"
rm -rf pyz_test

# Test file size and contents
ls -lh dist/rag-mini.pyz
python -m zipfile -l dist/rag-mini.pyz | head -20
```

**Success Criteria**:
- [ ] Builds without errors
- [ ] File size is reasonable (< 100MB)  
- [ ] Runs with multiple Python versions
- [ ] All core functionality works
- [ ] No missing dependencies in zipapp

---

## Phase 3: Installation Script Testing

### 3.1 Linux/macOS Install Script Testing

**Objective**: Test install.sh in various Unix environments

**Test Environments**:
- [ ] Ubuntu 20.04 (clean container)
- [ ] Ubuntu 22.04 (clean container)  
- [ ] Ubuntu 24.04 (clean container)
- [ ] CentOS 7 (clean container)
- [ ] CentOS Stream 9 (clean container)
- [ ] macOS 12+ (if available)
- [ ] Alpine Linux (minimal test)

**For each environment**:
```bash
# Test script download and execution
curl -fsSL file://$(pwd)/install.sh > /tmp/test_install.sh
chmod +x /tmp/test_install.sh

# Test dry run capabilities (modify script for --dry-run flag)
/tmp/test_install.sh --dry-run

# Test actual installation
/tmp/test_install.sh

# Verify installation
which rag-mini
rag-mini --help
rag-mini --version

# Test functionality
mkdir install_test
echo "def example(): return 'hello'" > install_test/sample.py
rag-mini init -p install_test  
rag-mini search -p install_test "example function"

# Cleanup
rm -rf install_test /tmp/test_install.sh
```

**Edge Case Testing**:
```bash
# Test without curl
mv /usr/bin/curl /usr/bin/curl.bak 2>/dev/null || true
# Run installer (should fall back to wget or pip)
# Restore curl

# Test without wget  
mv /usr/bin/wget /usr/bin/wget.bak 2>/dev/null || true
# Run installer
# Restore wget

# Test with Python but no pip
# Test with old Python versions
# Test with no internet (local package test)
```

**Success Criteria**:
- [ ] Script downloads and runs without errors
- [ ] Handles missing dependencies gracefully
- [ ] Installs correct package version
- [ ] Creates working `rag-mini` command
- [ ] Provides clear user feedback
- [ ] Falls back properly (uv → pipx → pip)

### 3.2 Windows PowerShell Script Testing

**Objective**: Test install.ps1 in Windows environments

**Test Environments**:
- [ ] Windows 10 (PowerShell 5.1)
- [ ] Windows 11 (PowerShell 5.1)
- [ ] Windows Server 2019
- [ ] PowerShell Core 7.x (cross-platform)

**For each environment**:
```powershell
# Download and test
Invoke-WebRequest -Uri "file://$(Get-Location)/install.ps1" -OutFile "$env:TEMP/test_install.ps1"

# Test execution policy handling
Get-ExecutionPolicy
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Test dry run (modify script)
& "$env:TEMP/test_install.ps1" -DryRun

# Test actual installation
& "$env:TEMP/test_install.ps1"

# Verify installation
Get-Command rag-mini
rag-mini --help
rag-mini --version

# Test functionality
New-Item -ItemType Directory -Name "win_test"
"def windows_test(): return True" | Out-File -FilePath "win_test/test.py"
rag-mini init -p win_test
rag-mini search -p win_test "windows test"

# Cleanup
Remove-Item -Recurse -Force win_test
Remove-Item "$env:TEMP/test_install.ps1"
```

**Edge Case Testing**:
- [ ] Test without Python in PATH
- [ ] Test with Python 3.8-3.12
- [ ] Test restricted execution policy
- [ ] Test without admin rights
- [ ] Test corporate firewall scenarios

**Success Criteria**:
- [ ] Script runs without PowerShell errors
- [ ] Handles execution policy correctly
- [ ] Installs package successfully
- [ ] PATH is updated correctly
- [ ] Error messages are user-friendly
- [ ] Falls back properly (uv → pipx → pip)

---

## Phase 4: GitHub Actions Workflow Testing

### 4.1 Local Workflow Testing

**Objective**: Test GitHub Actions workflow locally using act

**Setup**:
```bash
# Install act (GitHub Actions local runner)
# On macOS: brew install act
# On Linux: check https://github.com/nektos/act

# Test workflow syntax
act --list

# Test individual jobs
act -j build-wheels --dry-run
act -j build-zipapp --dry-run  
act -j test-installation --dry-run
```

**Tests**:
```bash
# Test wheel building job
act -j build-wheels

# Check artifacts
ls -la /tmp/act-* 

# Test zipapp building
act -j build-zipapp

# Test installation testing job
act -j test-installation

# Test release job (with dummy tag)
act push -e .github/workflows/test-release.json
```

**Success Criteria**:
- [ ] All jobs complete without errors
- [ ] Wheels are built for all platforms
- [ ] Zipapp is created successfully
- [ ] Installation tests pass
- [ ] Artifacts are properly uploaded

### 4.2 Fork Testing

**Objective**: Test workflow in a real GitHub environment

**Setup**:
1. [ ] Create a test fork of the repository
2. [ ] Enable GitHub Actions on the fork
3. [ ] Set up test PyPI token (TestPyPI)

**Tests**:
```bash
# Push changes to test branch
git checkout -b test-distribution
git push origin test-distribution

# Create test release
git tag v2.1.0-test
git push origin v2.1.0-test

# Monitor GitHub Actions:
# - Check all jobs complete
# - Download artifacts
# - Verify wheel contents  
# - Test zipapp download
```

**Success Criteria**:
- [ ] Workflow triggers on tag push
- [ ] All matrix builds complete
- [ ] Artifacts are uploaded
- [ ] Release is created with assets
- [ ] TestPyPI receives package (if configured)

---

## Phase 5: Manual Installation Method Testing

### 5.1 uv Installation Testing

**Test Environments**: Linux, macOS, Windows

**Tests**:
```bash
# Fresh environment
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Test uv tool install (will fail until we publish)  
# For now, test with local wheel
uv tool install dist/fss_mini_rag-*.whl

# Verify installation
which rag-mini
rag-mini --help

# Test functionality
mkdir uv_test
echo "print('uv test')" > uv_test/demo.py
rag-mini init -p uv_test
rag-mini search -p uv_test "print statement"
rm -rf uv_test

# Test uninstall
uv tool uninstall fss-mini-rag
```

**Success Criteria**:
- [ ] uv installs cleanly
- [ ] Package installs via uv tool install
- [ ] Command is available in PATH
- [ ] All functionality works
- [ ] Uninstall works cleanly

### 5.2 pipx Installation Testing

**Test Environments**: Linux, macOS, Windows

**Tests**:
```bash
# Install pipx
python -m pip install --user pipx
python -m pipx ensurepath

# Test pipx install (local wheel for now)
pipx install dist/fss_mini_rag-*.whl

# Verify installation
pipx list
which rag-mini  
rag-mini --help

# Test functionality
mkdir pipx_test
echo "def pipx_demo(): pass" > pipx_test/code.py
rag-mini init -p pipx_test
rag-mini search -p pipx_test "pipx demo"
rm -rf pipx_test

# Test uninstall
pipx uninstall fss-mini-rag
```

**Success Criteria**:
- [ ] pipx installs without issues
- [ ] Package is isolated in own environment
- [ ] Command works globally
- [ ] No conflicts with system packages
- [ ] Uninstall is clean

### 5.3 pip Installation Testing

**Test Environments**: Multiple Python versions

**Tests**:
```bash
# Test with --user flag
pip install --user dist/fss_mini_rag-*.whl

# Verify PATH  
echo $PATH | grep -q "$(python -m site --user-base)/bin"
which rag-mini
rag-mini --help

# Test functionality
mkdir pip_test
echo "class PipTest: pass" > pip_test/example.py
rag-mini init -p pip_test
rag-mini search -p pip_test "PipTest class"
rm -rf pip_test

# Test uninstall
pip uninstall -y fss-mini-rag
```

**Success Criteria**:
- [ ] Installs correctly with --user
- [ ] PATH is configured properly
- [ ] No permission issues
- [ ] Works across Python versions
- [ ] Uninstall removes everything

---

## Phase 6: End-to-End User Experience Testing

### 6.1 New User Experience Testing

**Scenario**: Complete beginner with no Python knowledge

**Test Script**:
```bash
# Start with fresh system (VM/container)
# Follow README instructions exactly

# Linux/macOS user
curl -fsSL https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.sh | bash

# Windows user  
# iwr https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.ps1 -UseBasicParsing | iex

# Follow quick start guide
rag-mini --help
mkdir my_project
echo "def hello_world(): print('Hello RAG!')" > my_project/main.py
echo "class DataProcessor: pass" > my_project/processor.py
rag-mini init -p my_project
rag-mini search -p my_project "hello function"
rag-mini search -p my_project "DataProcessor class"
```

**Success Criteria**:
- [ ] Installation completes without user intervention
- [ ] Clear, helpful output throughout
- [ ] `rag-mini` command is available immediately
- [ ] Basic workflow works as expected
- [ ] Error messages are user-friendly

### 6.2 Developer Experience Testing

**Scenario**: Python developer wanting to contribute

**Test Script**:
```bash
# Clone repository
git clone https://github.com/fsscoding/fss-mini-rag.git
cd fss-mini-rag

# Development installation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Test development commands
make help
make dev-install
make test-dist
make build
make build-pyz

# Test local installation
pip install dist/*.whl
rag-mini --help
```

**Success Criteria**:
- [ ] Development setup is straightforward
- [ ] Makefile commands work correctly
- [ ] Local builds install properly
- [ ] All development tools function

### 6.3 Advanced User Testing

**Scenario**: Power user with custom requirements

**Test Script**:
```bash
# Test zipapp usage
wget https://github.com/fsscoding/fss-mini-rag/releases/latest/download/rag-mini.pyz
python rag-mini.pyz --help

# Test with large codebase
git clone https://github.com/django/django.git test_django
python rag-mini.pyz init -p test_django
python rag-mini.pyz search -p test_django "model validation"

# Test server mode  
python rag-mini.pyz server -p test_django
curl http://localhost:7777/health

# Clean up
rm -rf test_django rag-mini.pyz
```

**Success Criteria**:
- [ ] Zipapp handles large codebases
- [ ] Performance is acceptable
- [ ] Server mode works correctly
- [ ] All advanced features function

---

## Phase 7: Performance and Edge Case Testing

### 7.1 Performance Testing

**Objective**: Ensure installation and runtime performance is acceptable

**Tests**:
```bash
# Installation speed testing
time curl -fsSL https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.sh | bash

# Package size testing
ls -lh dist/
du -sh .venv/

# Runtime performance
time rag-mini init -p large_project/
time rag-mini search -p large_project/ "complex query"

# Memory usage
rag-mini server &
ps aux | grep rag-mini
# Monitor memory usage during indexing/search
```

**Success Criteria**:
- [ ] Installation completes in < 5 minutes
- [ ] Package size is reasonable (< 50MB total)
- [ ] Indexing performance meets expectations
- [ ] Memory usage is acceptable

### 7.2 Edge Case Testing

**Objective**: Test unusual but possible scenarios

**Tests**:
```bash
# Network issues
# - Simulate slow connection
# - Test offline scenarios  
# - Test corporate firewalls

# System edge cases
# - Very old Python versions
# - Systems without pip
# - Read-only file systems
# - Limited disk space

# Unicode and special characters
mkdir "测试项目"
echo "def 函数名(): pass" > "测试项目/代码.py"
rag-mini init -p "测试项目"
rag-mini search -p "测试项目" "函数"

# Very large files
python -c "print('# ' + 'x'*1000000)" > large_file.py
rag-mini init -p .
# Should handle gracefully

# Concurrent usage
rag-mini server &
for i in {1..10}; do
    rag-mini search "test query $i" &
done
wait
```

**Success Criteria**:
- [ ] Graceful degradation with network issues
- [ ] Clear error messages for edge cases
- [ ] Handles Unicode correctly
- [ ] Doesn't crash on large files
- [ ] Concurrent access works properly

---

## Phase 8: Security Testing

### 8.1 Install Script Security

**Objective**: Verify install scripts are secure

**Tests**:
```bash
# Check install.sh
shellcheck install.sh
bandit -r install.sh (if applicable)

# Verify HTTPS usage
grep -n "http://" install.sh  # Should only be for localhost
grep -n "curl.*-k" install.sh  # Should be none
grep -n "wget.*--no-check" install.sh  # Should be none

# Check PowerShell script
# Run PowerShell security analyzer if available
```

**Success Criteria**:
- [ ] No shell script vulnerabilities
- [ ] Only HTTPS downloads (except localhost)
- [ ] No certificate verification bypasses
- [ ] Input validation where needed
- [ ] Clear error messages without info leakage

### 8.2 Package Security

**Objective**: Ensure distributed packages are secure

**Tests**:
```bash
# Check for secrets in built packages
python -m zipfile -l dist/*.whl | grep -i -E "(key|token|password|secret)"
strings dist/rag-mini.pyz | grep -i -E "(key|token|password|secret)"

# Verify package signatures (when implemented)
# Check for unexpected executables in packages
```

**Success Criteria**:
- [ ] No hardcoded secrets in packages
- [ ] No unexpected executables
- [ ] Package integrity is verifiable
- [ ] Dependencies are from trusted sources

---

## Phase 9: Documentation and User Support Testing

### 9.1 Documentation Accuracy Testing

**Objective**: Verify all documentation matches reality

**Tests**:
```bash
# Test every command in README
# Test every code example
# Verify all links work
# Check screenshots are current

# Test error scenarios mentioned in docs
# Verify troubleshooting sections
```

**Success Criteria**:
- [ ] All examples work as documented
- [ ] Links are valid and up-to-date
- [ ] Screenshots reflect current UI
- [ ] Error scenarios are accurate

### 9.2 Support Path Testing

**Objective**: Test user support workflows

**Tests**:
- [ ] GitHub issue templates work
- [ ] Error messages include helpful information
- [ ] Common problems have clear solutions
- [ ] Contact information is correct

---

## Phase 10: Release Readiness

### 10.1 Pre-Release Checklist

- [ ] All tests from Phases 1-9 pass
- [ ] Version numbers are consistent
- [ ] Changelog is updated
- [ ] Documentation is current
- [ ] Security review complete
- [ ] Performance benchmarks recorded
- [ ] Backup plan exists for rollback

### 10.2 Release Testing

**TestPyPI Release**:
```bash
# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ fss-mini-rag
```

**Success Criteria**:
- [ ] TestPyPI upload succeeds
- [ ] Installation from TestPyPI works
- [ ] All functionality works with TestPyPI package

### 10.3 Production Release

**Only after TestPyPI success**:
```bash
# Create GitHub release
git tag v2.1.0
git push origin v2.1.0

# Monitor automated workflows
# Test installation after PyPI publication
pip install fss-mini-rag
```

---

## Testing Tools and Infrastructure

### Required Tools
- [ ] Docker (for clean environment testing)
- [ ] act (for local GitHub Actions testing)  
- [ ] shellcheck (for bash script analysis)
- [ ] Various Python versions (3.8-3.12)
- [ ] Windows VM/container access
- [ ] macOS testing environment (if possible)

### Test Data
- [ ] Sample codebases of various sizes
- [ ] Unicode test files
- [ ] Edge case files (very large, empty, binary)
- [ ] Network simulation tools

### Monitoring
- [ ] Performance benchmarks
- [ ] Error rate tracking  
- [ ] User feedback collection
- [ ] Download/install statistics

---

## Conclusion

This testing plan is comprehensive but necessary. Each phase builds on the previous ones, and skipping phases risks shipping broken functionality to users.

**Estimated Timeline**: 3-5 days for complete testing
**Risk Level**: HIGH if phases are skipped
**Success Criteria**: 100% of critical tests must pass before release

The goal is to ship a distribution system that "just works" for every user, every time. This level of testing ensures we achieve that goal.
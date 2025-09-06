#!/usr/bin/env python3
"""
Set up multiple Python virtual environments for testing FSS-Mini-RAG distribution.
This implements Phase 1 of the testing plan.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Test configurations
PYTHON_VERSIONS = [
    ("python3.8", "3.8"),
    ("python3.9", "3.9"), 
    ("python3.10", "3.10"),
    ("python3.11", "3.11"),
    ("python3.12", "3.12"),
    ("python3", "system"),  # System default
]

TEST_ENV_DIR = Path("test_environments")

def run_command(cmd, cwd=None, capture=True, timeout=300):
    """Run a command with proper error handling."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=capture, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s: {cmd}"
    except Exception as e:
        return False, "", f"Command failed: {cmd} - {e}"

def check_python_version(python_cmd):
    """Check if Python version is available and get version info."""
    success, stdout, stderr = run_command(f"{python_cmd} --version")
    if success:
        return True, stdout.strip()
    return False, stderr

def create_test_environment(python_cmd, version_name):
    """Create a single test environment."""
    print(f"🔧 Creating test environment for Python {version_name}...")
    
    # Check if Python version exists
    available, version_info = check_python_version(python_cmd)
    if not available:
        print(f"   ❌ {python_cmd} not available: {version_info}")
        return False
    
    print(f"   ✅ Found {version_info}")
    
    # Create environment directory
    env_name = f"test_env_{version_name.replace('.', '_')}"
    env_path = TEST_ENV_DIR / env_name
    
    if env_path.exists():
        print(f"   🗑️  Removing existing environment...")
        shutil.rmtree(env_path)
    
    # Create virtual environment
    print(f"   📦 Creating virtual environment...")
    success, stdout, stderr = run_command(f"{python_cmd} -m venv {env_path}")
    if not success:
        print(f"   ❌ Failed to create venv: {stderr}")
        return False
    
    # Determine activation script
    if sys.platform == "win32":
        activate_script = env_path / "Scripts" / "activate.bat"
        pip_cmd = env_path / "Scripts" / "pip.exe"
        python_in_env = env_path / "Scripts" / "python.exe"
    else:
        activate_script = env_path / "bin" / "activate"  
        pip_cmd = env_path / "bin" / "pip"
        python_in_env = env_path / "bin" / "python"
    
    if not pip_cmd.exists():
        print(f"   ❌ pip not found in environment: {pip_cmd}")
        return False
    
    # Upgrade pip
    print(f"   ⬆️  Upgrading pip...")
    success, stdout, stderr = run_command(f"{python_in_env} -m pip install --upgrade pip")
    if not success:
        print(f"   ⚠️  Warning: pip upgrade failed: {stderr}")
    
    # Test pip works
    success, stdout, stderr = run_command(f"{pip_cmd} --version")
    if not success:
        print(f"   ❌ pip test failed: {stderr}")
        return False
    
    print(f"   ✅ Environment created successfully at {env_path}")
    return True

def create_test_script(env_path, version_name):
    """Create a test script for this environment."""
    if sys.platform == "win32":
        script_ext = ".bat"
        activate_cmd = f"call {env_path}\\Scripts\\activate.bat"
        pip_cmd = f"{env_path}\\Scripts\\pip.exe"
        python_cmd = f"{env_path}\\Scripts\\python.exe"
    else:
        script_ext = ".sh"
        activate_cmd = f"source {env_path}/bin/activate"
        pip_cmd = f"{env_path}/bin/pip"
        python_cmd = f"{env_path}/bin/python"
    
    script_path = TEST_ENV_DIR / f"test_{version_name.replace('.', '_')}{script_ext}"
    
    if sys.platform == "win32":
        script_content = f"""@echo off
echo Testing FSS-Mini-RAG in Python {version_name} environment
echo =========================================================

{activate_cmd}
if %ERRORLEVEL% neq 0 (
    echo Failed to activate environment
    exit /b 1
)

echo Python version:
{python_cmd} --version

echo Installing FSS-Mini-RAG in development mode...
{pip_cmd} install -e .
if %ERRORLEVEL% neq 0 (
    echo Installation failed
    exit /b 1
)

echo Testing CLI commands...
{python_cmd} -c "from mini_rag.cli import cli; print('CLI import: OK')"
if %ERRORLEVEL% neq 0 (
    echo CLI import failed
    exit /b 1
)

echo Testing rag-mini command...
rag-mini --help > nul
if %ERRORLEVEL% neq 0 (
    echo rag-mini command failed
    exit /b 1
)

echo Creating test project...
mkdir test_project_{version_name.replace('.', '_')} 2>nul
echo def hello(): return "world" > test_project_{version_name.replace('.', '_')}\\test.py

echo Testing basic functionality...
rag-mini init -p test_project_{version_name.replace('.', '_')}
if %ERRORLEVEL% neq 0 (
    echo Init failed
    exit /b 1
)

rag-mini search -p test_project_{version_name.replace('.', '_')} "hello function"
if %ERRORLEVEL% neq 0 (
    echo Search failed
    exit /b 1
)

echo Cleaning up...
rmdir /s /q test_project_{version_name.replace('.', '_')} 2>nul

echo ✅ All tests passed for Python {version_name}!
"""
    else:
        script_content = f"""#!/bin/bash
set -e

echo "Testing FSS-Mini-RAG in Python {version_name} environment"
echo "========================================================="

{activate_cmd}

echo "Python version:"
{python_cmd} --version

echo "Installing FSS-Mini-RAG in development mode..."
{pip_cmd} install -e .

echo "Testing CLI commands..."
{python_cmd} -c "from mini_rag.cli import cli; print('CLI import: OK')"

echo "Testing rag-mini command..."
rag-mini --help > /dev/null

echo "Creating test project..."
mkdir -p test_project_{version_name.replace('.', '_')}
echo 'def hello(): return "world"' > test_project_{version_name.replace('.', '_')}/test.py

echo "Testing basic functionality..."
rag-mini init -p test_project_{version_name.replace('.', '_')}
rag-mini search -p test_project_{version_name.replace('.', '_')} "hello function"

echo "Cleaning up..."
rm -rf test_project_{version_name.replace('.', '_')}

echo "✅ All tests passed for Python {version_name}!"
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    if sys.platform != "win32":
        os.chmod(script_path, 0o755)
    
    return script_path

def main():
    """Set up all test environments."""
    print("🧪 Setting up FSS-Mini-RAG Test Environments")
    print("=" * 50)
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Create test environments directory
    TEST_ENV_DIR.mkdir(exist_ok=True)
    
    successful_envs = []
    failed_envs = []
    
    for python_cmd, version_name in PYTHON_VERSIONS:
        try:
            if create_test_environment(python_cmd, version_name):
                env_name = f"test_env_{version_name.replace('.', '_')}"
                env_path = TEST_ENV_DIR / env_name
                
                # Create test script
                script_path = create_test_script(env_path, version_name)
                print(f"   📋 Test script created: {script_path}")
                
                successful_envs.append((version_name, env_path, script_path))
            else:
                failed_envs.append((version_name, "Environment creation failed"))
        except Exception as e:
            failed_envs.append((version_name, str(e)))
        
        print()  # Add spacing between environments
    
    # Summary
    print("=" * 50)
    print("📊 Environment Setup Summary")
    print("=" * 50)
    
    if successful_envs:
        print(f"✅ Successfully created {len(successful_envs)} environments:")
        for version_name, env_path, script_path in successful_envs:
            print(f"   • Python {version_name}: {env_path}")
    
    if failed_envs:
        print(f"\n❌ Failed to create {len(failed_envs)} environments:")
        for version_name, error in failed_envs:
            print(f"   • Python {version_name}: {error}")
    
    if successful_envs:
        print(f"\n🚀 Next Steps:")
        print(f"   1. Run individual test scripts:")
        for version_name, env_path, script_path in successful_envs:
            if sys.platform == "win32":
                print(f"      {script_path}")
            else:
                print(f"      ./{script_path}")
        
        print(f"\n   2. Or run all tests with:")
        if sys.platform == "win32":
            print(f"      python scripts\\run_all_env_tests.py")
        else:
            print(f"      python scripts/run_all_env_tests.py")
        
        print(f"\n   3. Clean up when done:")
        print(f"      rm -rf {TEST_ENV_DIR}")
        
        # Create master test runner
        create_master_test_runner(successful_envs)
    
    return len(failed_envs) == 0

def create_master_test_runner(successful_envs):
    """Create a script that runs all environment tests."""
    script_path = Path("scripts/run_all_env_tests.py")
    
    script_content = f'''#!/usr/bin/env python3
"""
Master test runner for all Python environment tests.
Generated automatically by setup_test_environments.py
"""

import subprocess
import sys
from pathlib import Path

def run_test_script(script_path, version_name):
    """Run a single test script."""
    print(f"🧪 Running tests for Python {{version_name}}...")
    print("-" * 40)
    
    try:
        if sys.platform == "win32":
            result = subprocess.run([str(script_path)], check=True, timeout=300)
        else:
            result = subprocess.run(["bash", str(script_path)], check=True, timeout=300)
        print(f"✅ Python {{version_name}} tests PASSED\\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Python {{version_name}} tests FAILED (exit code {{e.returncode}})\\n")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ Python {{version_name}} tests TIMEOUT\\n")
        return False
    except Exception as e:
        print(f"❌ Python {{version_name}} tests ERROR: {{e}}\\n")
        return False

def main():
    """Run all environment tests."""
    print("🧪 Running All Environment Tests")
    print("=" * 50)
    
    test_scripts = [
        {[(repr(version_name), repr(str(script_path))) for version_name, env_path, script_path in successful_envs]}
    ]
    
    passed = 0
    total = len(test_scripts)
    
    for version_name, script_path in test_scripts:
        if run_test_script(Path(script_path), version_name):
            passed += 1
    
    print("=" * 50)
    print(f"📊 Results: {{passed}}/{{total}} environments passed")
    
    if passed == total:
        print("🎉 All environment tests PASSED!")
        print("\\n📋 Ready for Phase 2: Package Building Tests")
        return 0
    else:
        print(f"❌ {{total - passed}} environment tests FAILED")
        print("\\n🔧 Fix failing environments before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    if sys.platform != "win32":
        os.chmod(script_path, 0o755)
    
    print(f"📋 Master test runner created: {script_path}")

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
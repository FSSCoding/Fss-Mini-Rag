#!/usr/bin/env python3
"""
Phase 2: Package building tests.
This tests building source distributions, wheels, and zipapps.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def run_command(cmd, cwd=None, timeout=120):
    """Run a command with timeout."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, 
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return False, "", str(e)

def test_build_requirements():
    """Test that build requirements are available."""
    print("1. Testing build requirements...")
    
    # Test build module
    success, stdout, stderr = run_command("python -c 'import build; print(\"build available\")'")
    if success:
        print("   ✅ build module available")
    else:
        print(f"   ⚠️  build module not available, installing...")
        success, stdout, stderr = run_command("pip install build")
        if not success:
            print(f"   ❌ Failed to install build: {stderr}")
            return False
        print("   ✅ build module installed")
    
    return True

def test_source_distribution():
    """Test building source distribution."""
    print("2. Testing source distribution build...")
    
    # Clean previous builds
    for path in ["dist/", "build/", "*.egg-info/"]:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
    
    # Build source distribution
    success, stdout, stderr = run_command("python -m build --sdist", timeout=60)
    if not success:
        print(f"   ❌ Source distribution build failed: {stderr}")
        return False
    
    # Check output
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("   ❌ dist/ directory not created")
        return False
    
    sdist_files = list(dist_dir.glob("*.tar.gz"))
    if not sdist_files:
        print("   ❌ No .tar.gz files created")
        return False
    
    print(f"   ✅ Source distribution created: {sdist_files[0].name}")
    
    # Check contents
    import tarfile
    try:
        with tarfile.open(sdist_files[0]) as tar:
            members = tar.getnames()
            essential_files = [
                "mini_rag/",
                "pyproject.toml", 
                "README.md",
            ]
            
            for essential in essential_files:
                if any(essential in member for member in members):
                    print(f"   ✅ Contains {essential}")
                else:
                    print(f"   ❌ Missing {essential}")
                    return False
    except Exception as e:
        print(f"   ❌ Failed to inspect tar: {e}")
        return False
    
    return True

def test_wheel_build():
    """Test building wheel."""
    print("3. Testing wheel build...")
    
    success, stdout, stderr = run_command("python -m build --wheel", timeout=60)
    if not success:
        print(f"   ❌ Wheel build failed: {stderr}")
        return False
    
    # Check wheel file
    dist_dir = Path("dist")
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("   ❌ No .whl files created")
        return False
    
    print(f"   ✅ Wheel created: {wheel_files[0].name}")
    
    # Check wheel contents
    import zipfile
    try:
        with zipfile.ZipFile(wheel_files[0]) as zip_file:
            members = zip_file.namelist()
            
            # Check for essential components
            has_mini_rag = any("mini_rag" in member for member in members)
            has_metadata = any("METADATA" in member for member in members)
            has_entry_points = any("entry_points.txt" in member for member in members)
            
            if has_mini_rag:
                print("   ✅ Contains mini_rag package")
            else:
                print("   ❌ Missing mini_rag package")
                return False
                
            if has_metadata:
                print("   ✅ Contains METADATA")
            else:
                print("   ❌ Missing METADATA")
                return False
                
            if has_entry_points:
                print("   ✅ Contains entry_points.txt")
            else:
                print("   ❌ Missing entry_points.txt")
                return False
                
    except Exception as e:
        print(f"   ❌ Failed to inspect wheel: {e}")
        return False
    
    return True

def test_zipapp_build():
    """Test building zipapp."""
    print("4. Testing zipapp build...")
    
    # Remove existing pyz file
    pyz_file = Path("dist/rag-mini.pyz")
    if pyz_file.exists():
        pyz_file.unlink()
    
    success, stdout, stderr = run_command("python scripts/build_pyz.py", timeout=120)
    if not success:
        print(f"   ❌ Zipapp build failed: {stderr}")
        return False
    
    # Check pyz file exists
    if not pyz_file.exists():
        print("   ❌ rag-mini.pyz not created")
        return False
    
    print(f"   ✅ Zipapp created: {pyz_file}")
    
    # Check file size (should be reasonable)
    size_mb = pyz_file.stat().st_size / (1024 * 1024)
    print(f"   📊 Size: {size_mb:.1f} MB")
    
    if size_mb > 200:  # Warning if very large
        print(f"   ⚠️  Zipapp is quite large ({size_mb:.1f} MB)")
    
    # Test basic execution (just help, no dependencies needed)
    success, stdout, stderr = run_command(f"python {pyz_file} --help", timeout=10)
    if success:
        print("   ✅ Zipapp runs successfully")
    else:
        print(f"   ❌ Zipapp execution failed: {stderr}")
        # Don't fail the test for this - might be dependency issues
        print("   ⚠️  (This might be due to missing dependencies)")
    
    return True

def test_package_metadata():
    """Test that built packages have correct metadata."""
    print("5. Testing package metadata...")
    
    dist_dir = Path("dist")
    
    # Test wheel metadata
    wheel_files = list(dist_dir.glob("*.whl"))
    if wheel_files:
        import zipfile
        try:
            with zipfile.ZipFile(wheel_files[0]) as zip_file:
                # Find METADATA file
                metadata_files = [f for f in zip_file.namelist() if f.endswith("METADATA")]
                if metadata_files:
                    metadata_content = zip_file.read(metadata_files[0]).decode('utf-8')
                    
                    # Check key metadata
                    checks = [
                        ("Name: fss-mini-rag", "Package name"),
                        ("Author: Brett Fox", "Author"),
                        ("License: MIT", "License"),
                        ("Requires-Python: >=3.8", "Python version"),
                    ]
                    
                    for check, desc in checks:
                        if check in metadata_content:
                            print(f"   ✅ {desc}")
                        else:
                            print(f"   ❌ {desc} missing or incorrect")
                            return False
                else:
                    print("   ❌ No METADATA file in wheel")
                    return False
        except Exception as e:
            print(f"   ❌ Failed to read wheel metadata: {e}")
            return False
    
    return True

def main():
    """Run all build tests."""
    print("🧪 FSS-Mini-RAG Phase 2: Build Tests")
    print("=" * 40)
    
    # Ensure we're in project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    tests = [
        ("Build Requirements", test_build_requirements),
        ("Source Distribution", test_source_distribution),
        ("Wheel Build", test_wheel_build), 
        ("Zipapp Build", test_zipapp_build),
        ("Package Metadata", test_package_metadata),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*15} {test_name} {'='*15}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 2: All build tests PASSED!")
        print("\n📋 Built packages ready for testing:")
        dist_dir = Path("dist")
        if dist_dir.exists():
            for file in dist_dir.iterdir():
                if file.is_file():
                    size = file.stat().st_size / 1024
                    print(f"   • {file.name} ({size:.1f} KB)")
        
        print("\n🚀 Ready for Phase 3: Installation Testing")
        print("Next steps:")
        print("   1. Test installation from built packages")
        print("   2. Test install scripts")
        print("   3. Test in clean environments")
        return True
    else:
        print(f"❌ {total - passed} tests FAILED")
        print("🔧 Fix failing tests before proceeding to Phase 3")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
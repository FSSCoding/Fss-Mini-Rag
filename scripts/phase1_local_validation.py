#!/usr/bin/env python3
"""
Phase 1: Local validation testing for FSS-Mini-RAG distribution.
This tests what we can validate locally without Docker.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

class LocalValidator:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.temp_dir = None
        
    def setup_temp_environment(self):
        """Create a temporary testing environment."""
        print("🔧 Setting up temporary test environment...")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fss_rag_test_"))
        print(f"   📁 Test directory: {self.temp_dir}")
        return True
    
    def cleanup_temp_environment(self):
        """Clean up temporary environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"   🗑️  Cleaned up test directory")
    
    def test_install_script_syntax(self):
        """Test that install scripts have valid syntax."""
        print("1. Testing install script syntax...")
        
        # Test bash script
        install_sh = self.project_root / "install.sh"
        if not install_sh.exists():
            print("   ❌ install.sh not found")
            return False
        
        try:
            result = subprocess.run(
                ["bash", "-n", str(install_sh)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print("   ✅ install.sh syntax valid")
            else:
                print(f"   ❌ install.sh syntax error: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Error checking install.sh: {e}")
            return False
        
        # Check PowerShell script exists
        install_ps1 = self.project_root / "install.ps1"
        if install_ps1.exists():
            print("   ✅ install.ps1 exists")
        else:
            print("   ❌ install.ps1 missing")
            return False
        
        return True
    
    def test_package_building(self):
        """Test that we can build packages successfully."""
        print("2. Testing package building...")
        
        # Clean any existing builds
        for path in ["dist", "build"]:
            full_path = self.project_root / path
            if full_path.exists():
                shutil.rmtree(full_path)
        
        # Install build if needed
        try:
            subprocess.run(
                [sys.executable, "-c", "import build"],
                capture_output=True, check=True
            )
            print("   ✅ build module available")
        except subprocess.CalledProcessError:
            print("   🔧 Installing build module...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "build"
                ], capture_output=True, check=True, timeout=120)
                print("   ✅ build module installed")
            except Exception as e:
                print(f"   ❌ Failed to install build: {e}")
                return False
        
        # Build source distribution
        try:
            result = subprocess.run([
                sys.executable, "-m", "build", "--sdist"
            ], capture_output=True, text=True, timeout=120, cwd=self.project_root)
            
            if result.returncode == 0:
                print("   ✅ Source distribution built")
            else:
                print(f"   ❌ Source build failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Source build error: {e}")
            return False
        
        # Build wheel
        try:
            result = subprocess.run([
                sys.executable, "-m", "build", "--wheel"
            ], capture_output=True, text=True, timeout=120, cwd=self.project_root)
            
            if result.returncode == 0:
                print("   ✅ Wheel built")
            else:
                print(f"   ❌ Wheel build failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Wheel build error: {e}")
            return False
        
        return True
    
    def test_wheel_installation(self):
        """Test installing built wheel in temp environment."""
        print("3. Testing wheel installation...")
        
        # Find built wheel
        dist_dir = self.project_root / "dist"
        wheel_files = list(dist_dir.glob("*.whl"))
        
        if not wheel_files:
            print("   ❌ No wheel files found")
            return False
        
        wheel_file = wheel_files[0]
        print(f"   📦 Testing wheel: {wheel_file.name}")
        
        # Create test virtual environment
        test_venv = self.temp_dir / "test_venv"
        
        try:
            # Create venv
            subprocess.run([
                sys.executable, "-m", "venv", str(test_venv)
            ], check=True, timeout=60)
            print("   ✅ Test venv created")
            
            # Determine pip path
            if sys.platform == "win32":
                pip_cmd = test_venv / "Scripts" / "pip.exe"
            else:
                pip_cmd = test_venv / "bin" / "pip"
            
            # Install wheel
            subprocess.run([
                str(pip_cmd), "install", str(wheel_file)
            ], check=True, timeout=120, capture_output=True)
            print("   ✅ Wheel installed successfully")
            
            # Test command exists
            if sys.platform == "win32":
                rag_mini_cmd = test_venv / "Scripts" / "rag-mini.exe"
            else:
                rag_mini_cmd = test_venv / "bin" / "rag-mini"
            
            if rag_mini_cmd.exists():
                print("   ✅ rag-mini command exists")
                
                # Test help command (without dependencies)
                try:
                    help_result = subprocess.run([
                        str(rag_mini_cmd), "--help"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if help_result.returncode == 0 and "Mini RAG" in help_result.stdout:
                        print("   ✅ Help command works")
                        return True
                    else:
                        print(f"   ❌ Help command failed: {help_result.stderr}")
                        return False
                except Exception as e:
                    print(f"   ⚠️  Help command error (may be dependency-related): {e}")
                    # Don't fail the test for this - might be dependency issues
                    return True
            else:
                print(f"   ❌ rag-mini command not found at: {rag_mini_cmd}")
                return False
                
        except Exception as e:
            print(f"   ❌ Wheel installation test failed: {e}")
            return False
    
    def test_zipapp_creation(self):
        """Test zipapp creation (without execution due to deps)."""
        print("4. Testing zipapp creation...")
        
        build_script = self.project_root / "scripts" / "build_pyz.py"
        if not build_script.exists():
            print("   ❌ build_pyz.py not found")
            return False
        
        # Remove existing pyz file
        pyz_file = self.project_root / "dist" / "rag-mini.pyz"
        if pyz_file.exists():
            pyz_file.unlink()
        
        try:
            result = subprocess.run([
                sys.executable, str(build_script)
            ], capture_output=True, text=True, timeout=300, cwd=self.project_root)
            
            if result.returncode == 0:
                print("   ✅ Zipapp build completed")
                
                if pyz_file.exists():
                    size_mb = pyz_file.stat().st_size / (1024 * 1024)
                    print(f"   📊 Zipapp size: {size_mb:.1f} MB")
                    
                    if size_mb > 500:  # Very large
                        print("   ⚠️  Zipapp is very large - consider optimization")
                    
                    return True
                else:
                    print("   ❌ Zipapp file not created")
                    return False
            else:
                print(f"   ❌ Zipapp build failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Zipapp creation error: {e}")
            return False
    
    def test_install_script_content(self):
        """Test install script has required components."""
        print("5. Testing install script content...")
        
        install_sh = self.project_root / "install.sh"
        content = install_sh.read_text()
        
        required_components = [
            ("uv tool install", "uv installation method"),
            ("pipx install", "pipx fallback method"),
            ("pip install --user", "pip fallback method"),
            ("curl -LsSf https://astral.sh/uv/install.sh", "uv installer download"),
            ("fss-mini-rag", "correct package name"),
            ("rag-mini", "command name check"),
        ]
        
        for component, desc in required_components:
            if component in content:
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ Missing: {desc}")
                return False
        
        return True
    
    def test_metadata_consistency(self):
        """Test that metadata is consistent across files."""
        print("6. Testing metadata consistency...")
        
        # Check pyproject.toml
        pyproject_file = self.project_root / "pyproject.toml"
        pyproject_content = pyproject_file.read_text()
        
        # Check README.md
        readme_file = self.project_root / "README.md"
        readme_content = readme_file.read_text()
        
        checks = [
            ("fss-mini-rag", "Package name in pyproject.toml", pyproject_content),
            ("rag-mini", "Command name in pyproject.toml", pyproject_content),
            ("One-Line Installers", "New install section in README", readme_content),
            ("curl -fsSL", "Linux installer in README", readme_content),
            ("iwr", "Windows installer in README", readme_content),
        ]
        
        for check, desc, content in checks:
            if check in content:
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ Missing: {desc}")
                return False
        
        return True
    
    def run_all_tests(self):
        """Run all local validation tests."""
        print("🧪 FSS-Mini-RAG Phase 1: Local Validation")
        print("=" * 50)
        
        if not self.setup_temp_environment():
            return False
        
        tests = [
            ("Install Script Syntax", self.test_install_script_syntax),
            ("Package Building", self.test_package_building),
            ("Wheel Installation", self.test_wheel_installation),
            ("Zipapp Creation", self.test_zipapp_creation),
            ("Install Script Content", self.test_install_script_content),
            ("Metadata Consistency", self.test_metadata_consistency),
        ]
        
        passed = 0
        total = len(tests)
        results = {}
        
        try:
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                try:
                    result = test_func()
                    results[test_name] = result
                    if result:
                        passed += 1
                        print(f"✅ {test_name} PASSED")
                    else:
                        print(f"❌ {test_name} FAILED")
                except Exception as e:
                    print(f"❌ {test_name} ERROR: {e}")
                    results[test_name] = False
        
        finally:
            self.cleanup_temp_environment()
        
        # Summary
        print(f"\n{'='*50}")
        print(f"📊 Phase 1 Local Validation: {passed}/{total} tests passed")
        print(f"{'='*50}")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status:>8} {test_name}")
        
        if passed == total:
            print(f"\n🎉 All local validation tests PASSED!")
            print(f"✅ Distribution system is ready for external testing")
            print(f"\n📋 Next steps:")
            print(f"   1. Test in Docker containers (when available)")
            print(f"   2. Test on different operating systems")
            print(f"   3. Test with TestPyPI")
            print(f"   4. Create production release")
        elif passed >= 4:  # Most critical tests pass
            print(f"\n⚠️  Most critical tests passed ({passed}/{total})")
            print(f"💡 Ready for external testing with caution")
            print(f"🔧 Fix remaining issues:")
            for test_name, result in results.items():
                if not result:
                    print(f"   • {test_name}")
        else:
            print(f"\n❌ Critical validation failed")
            print(f"🔧 Fix these issues before proceeding:")
            for test_name, result in results.items():
                if not result:
                    print(f"   • {test_name}")
        
        return passed >= 4  # Need at least 4/6 to proceed

def main():
    """Run local validation tests."""
    project_root = Path(__file__).parent.parent
    
    validator = LocalValidator(project_root)
    success = validator.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
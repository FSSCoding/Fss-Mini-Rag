#!/usr/bin/env python3
"""
Simple test script that works in any environment.
"""

import subprocess
import sys
from pathlib import Path

# Add the project root to Python path so we can import mini_rag
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Test basic functionality without installing."""
    print("🧪 FSS-Mini-RAG Simple Tests")
    print("=" * 40)
    
    # Test CLI import
    print("1. Testing CLI import...")
    try:
        import mini_rag.cli
        print("   ✅ CLI module imports successfully")
    except ImportError as e:
        print(f"   ❌ CLI import failed: {e}")
        return 1
    
    # Test console script entry point
    print("2. Testing entry point...")
    try:
        from mini_rag.cli import cli
        print("   ✅ Entry point function accessible")
    except ImportError as e:
        print(f"   ❌ Entry point not accessible: {e}")
        return 1
    
    # Test help command (should work without dependencies)
    print("3. Testing help command...")
    try:
        # This will test the CLI without actually running commands that need dependencies
        result = subprocess.run([
            sys.executable, "-c", 
            "from mini_rag.cli import cli; import sys; sys.argv = ['rag-mini', '--help']; cli()"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Mini RAG" in result.stdout:
            print("   ✅ Help command works")
        else:
            print(f"   ❌ Help command failed: {result.stderr}")
            return 1
    except Exception as e:
        print(f"   ❌ Help command test failed: {e}")
        return 1
    
    # Test install scripts exist
    print("4. Testing install scripts...")
    if Path("install.sh").exists():
        print("   ✅ install.sh exists")
    else:
        print("   ❌ install.sh missing")
        return 1
    
    if Path("install.ps1").exists():
        print("   ✅ install.ps1 exists")
    else:
        print("   ❌ install.ps1 missing")
        return 1
    
    # Test pyproject.toml has correct entry point
    print("5. Testing pyproject.toml...")
    try:
        with open("pyproject.toml") as f:
            content = f.read()
        
        if 'rag-mini = "mini_rag.cli:cli"' in content:
            print("   ✅ Entry point correctly configured")
        else:
            print("   ❌ Entry point not found in pyproject.toml")
            return 1
            
        if 'name = "fss-mini-rag"' in content:
            print("   ✅ Package name correctly set")
        else:
            print("   ❌ Package name not set correctly")
            return 1
            
    except Exception as e:
        print(f"   ❌ pyproject.toml test failed: {e}")
        return 1
    
    print("\n🎉 All basic tests passed!")
    print("\n📋 To complete setup:")
    print("   1. Commit and push these changes")
    print("   2. Create a GitHub release to trigger wheel building")
    print("   3. Test installation methods:")
    print("      • curl -fsSL https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.sh | bash")
    print("      • pipx install fss-mini-rag")
    print("      • uv tool install fss-mini-rag")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
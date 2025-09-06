#!/usr/bin/env python3
"""
Build script for creating a single-file Python zipapp (.pyz) distribution.
This creates a portable rag-mini.pyz that can be run with any Python 3.8+.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

def main():
    """Build the .pyz file."""
    project_root = Path(__file__).parent.parent
    build_dir = project_root / "dist"
    pyz_file = build_dir / "rag-mini.pyz"
    
    print(f"🔨 Building FSS-Mini-RAG zipapp...")
    print(f"   Project root: {project_root}")
    print(f"   Output: {pyz_file}")
    
    # Ensure dist directory exists
    build_dir.mkdir(exist_ok=True)
    
    # Create temporary directory for building
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        app_dir = temp_path / "app"
        
        print(f"📦 Preparing files in {app_dir}...")
        
        # Copy source code
        src_dir = project_root / "mini_rag"
        if not src_dir.exists():
            print(f"❌ Source directory not found: {src_dir}")
            sys.exit(1)
            
        shutil.copytree(src_dir, app_dir / "mini_rag")
        
        # Install dependencies to the temp directory
        print("📥 Installing dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "-t", str(app_dir),
                "-r", str(project_root / "requirements.txt")
            ], check=True, capture_output=True)
            print("   ✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install dependencies: {e}")
            print(f"   stderr: {e.stderr.decode()}")
            sys.exit(1)
        
        # Create __main__.py entry point
        main_py = app_dir / "__main__.py"
        main_py.write_text("""#!/usr/bin/env python3
# Entry point for rag-mini zipapp
import sys
from mini_rag.cli import cli

if __name__ == "__main__":
    sys.exit(cli())
""")
        
        print("🗜️  Creating zipapp...")
        
        # Remove existing pyz file if it exists
        if pyz_file.exists():
            pyz_file.unlink()
            
        # Create the zipapp
        try:
            zipapp.create_archive(
                source=app_dir,
                target=pyz_file,
                interpreter="/usr/bin/env python3",
                compressed=True
            )
            print(f"✅ Successfully created {pyz_file}")
            
            # Show file size
            size_mb = pyz_file.stat().st_size / (1024 * 1024)
            print(f"   📊 Size: {size_mb:.1f} MB")
            
            # Make executable
            pyz_file.chmod(0o755)
            print(f"   🔧 Made executable")
            
            print(f"""
🎉 Build complete! 

Usage:
  python {pyz_file} --help
  python {pyz_file} init
  python {pyz_file} search "your query"

Or make it directly executable (Unix/Linux/macOS):
  {pyz_file} --help
""")
            
        except Exception as e:
            print(f"❌ Failed to create zipapp: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
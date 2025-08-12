#!/usr/bin/env python3
"""
Analyze FSS-Mini-RAG dependencies to determine what's safe to remove.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict

def find_imports_in_file(file_path):
    """Find all imports in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    imports.add(module)
        
        return imports
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return set()

def analyze_dependencies():
    """Analyze all dependencies in the project."""
    project_root = Path(__file__).parent
    mini_rag_dir = project_root / "mini_rag"
    
    # Find all Python files
    python_files = []
    for file_path in mini_rag_dir.glob("*.py"):
        if file_path.name != "__pycache__":
            python_files.append(file_path)
    
    # Analyze imports
    file_imports = {}
    internal_deps = defaultdict(set)
    
    for file_path in python_files:
        imports = find_imports_in_file(file_path)
        file_imports[file_path.name] = imports
        
        # Check for internal imports
        for imp in imports:
            if imp in [f.stem for f in python_files]:
                internal_deps[file_path.name].add(imp)
    
    print("🔍 FSS-Mini-RAG Dependency Analysis")
    print("=" * 50)
    
    # Show what each file imports
    print("\n📁 File Dependencies:")
    for filename, imports in file_imports.items():
        internal = [imp for imp in imports if imp in [f.stem for f in python_files]]
        if internal:
            print(f"   {filename} imports: {', '.join(internal)}")
    
    # Show reverse dependencies (what depends on each file)
    reverse_deps = defaultdict(set)
    for file, deps in internal_deps.items():
        for dep in deps:
            reverse_deps[dep].add(file)
    
    print("\n🔗 Reverse Dependencies (what uses each file):")
    all_modules = {f.stem for f in python_files}
    
    for module in sorted(all_modules):
        users = reverse_deps.get(module, set())
        if users:
            print(f"   {module}.py is used by: {', '.join(users)}")
        else:
            print(f"   {module}.py is NOT imported by any other file")
    
    # Safety analysis
    print("\n🛡️ Safety Analysis:")
    
    # Files imported by __init__.py are definitely needed
    init_imports = file_imports.get('__init__.py', set())
    print(f"   Core modules (imported by __init__.py): {', '.join(init_imports)}")
    
    # Files not used anywhere might be safe to remove
    unused_files = []
    for module in all_modules:
        if module not in reverse_deps and module != '__init__':
            unused_files.append(module)
    
    if unused_files:
        print(f"   ⚠️ Potentially unused: {', '.join(unused_files)}")
        print("   ❗ Verify these aren't used by CLI or external scripts!")
    
    # Check CLI usage
    cli_files = ['cli.py', 'enhanced_cli.py']
    for cli_file in cli_files:
        if cli_file in file_imports:
            cli_imports = file_imports[cli_file]
            print(f"   📋 {cli_file} imports: {', '.join([imp for imp in cli_imports if imp in all_modules])}")

if __name__ == "__main__":
    analyze_dependencies()
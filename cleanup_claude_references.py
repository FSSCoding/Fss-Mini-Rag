#!/usr/bin/env python3
"""
Script to completely remove all Mini-RAG references from the FSS-Mini-RAG codebase.
This ensures the repository is completely independent and avoids any licensing issues.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Tuple

class Mini-RAGCleanup:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.replacements = {
            # Directory/module names
            'mini_rag': 'mini_rag',
            'mini-rag': 'mini-rag',
            
            # Class names and references
            'MiniRAG': 'MiniRAG', 
            'Mini RAG': 'Mini RAG',
            'Mini RAG': 'mini rag',
            'mini_rag': 'MINI_RAG',
            
            # File paths and imports
            'from mini_rag': 'from mini_rag',
            'import mini_rag': 'import mini_rag',
            '.mini-rag': '.mini-rag',
            
            # Comments and documentation
            'Mini-RAG': 'Mini-RAG',
            'Mini-RAG': 'mini-rag',
            
            # Specific technical references
            'the development environment': 'the development environment',
            'AI assistant': 'AI assistant',
            'Mini-RAG\'s': 'the system\'s',
            
            # Config and metadata
            'mini_': 'mini_',
            'mini_': 'Mini_',
        }
        
        self.files_to_rename = []
        self.dirs_to_rename = []
        self.files_modified = []
        
    def scan_for_references(self) -> Dict[str, int]:
        """Scan for all Mini-RAG references and return counts."""
        references = {}
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip git directory
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith(('.py', '.md', '.sh', '.yaml', '.json', '.txt')):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        for old_ref in self.replacements.keys():
                            count = content.lower().count(old_ref.lower())
                            if count > 0:
                                if old_ref not in references:
                                    references[old_ref] = 0
                                references[old_ref] += count
                                
                    except Exception as e:
                        print(f"Warning: Could not scan {file_path}: {e}")
        
        return references
        
    def rename_directories(self):
        """Rename directories with Mini-RAG references."""
        print("🔄 Renaming directories...")
        
        # Find directories to rename
        for root, dirs, files in os.walk(self.project_root):
            if '.git' in root:
                continue
                
            for dir_name in dirs:
                if 'Mini-RAG' in dir_name.lower():
                    old_path = Path(root) / dir_name
                    new_name = dir_name.replace('mini_rag', 'mini_rag').replace('mini-rag', 'mini-rag')
                    new_path = Path(root) / new_name
                    self.dirs_to_rename.append((old_path, new_path))
        
        # Actually rename directories (do this carefully with git)
        for old_path, new_path in self.dirs_to_rename:
            if old_path.exists():
                print(f"  📁 {old_path.name} → {new_path.name}")
                # Use git mv to preserve history
                try:
                    os.system(f'git mv "{old_path}" "{new_path}"')
                except Exception as e:
                    print(f"    Warning: git mv failed, using regular rename: {e}")
                    shutil.move(str(old_path), str(new_path))
                    
    def update_file_contents(self):
        """Update file contents to replace Mini-RAG references."""
        print("📝 Updating file contents...")
        
        for root, dirs, files in os.walk(self.project_root):
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith(('.py', '.md', '.sh', '.yaml', '.json', '.txt')):
                    file_path = Path(root) / file
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            original_content = f.read()
                            
                        modified_content = original_content
                        changes_made = False
                        
                        # Apply replacements in order (most specific first)
                        sorted_replacements = sorted(self.replacements.items(), 
                                                   key=lambda x: len(x[0]), reverse=True)
                        
                        for old_ref, new_ref in sorted_replacements:
                            if old_ref in modified_content:
                                modified_content = modified_content.replace(old_ref, new_ref)
                                changes_made = True
                                
                            # Also handle case variations
                            if old_ref.lower() in modified_content.lower():
                                # Use regex for case-insensitive replacement
                                pattern = re.escape(old_ref)
                                modified_content = re.sub(pattern, new_ref, modified_content, flags=re.IGNORECASE)
                                changes_made = True
                        
                        # Write back if changes were made
                        if changes_made and modified_content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(modified_content)
                            self.files_modified.append(file_path)
                            print(f"  📄 Updated: {file_path.relative_to(self.project_root)}")
                            
                    except Exception as e:
                        print(f"Warning: Could not process {file_path}: {e}")
    
    def update_imports_and_paths(self):
        """Update Python imports and file paths."""
        print("🔗 Updating imports and paths...")
        
        # Special handling for Python imports
        for root, dirs, files in os.walk(self.project_root):
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Fix relative imports
                        content = re.sub(r'from \.mini_rag', 'from .mini_rag', content)
                        content = re.sub(r'from mini_rag', 'from mini_rag', content)
                        content = re.sub(r'import mini_rag', 'import mini_rag', content)
                        
                        # Fix file paths in strings
                        content = content.replace("'mini_rag'", "'mini_rag'")
                        content = content.replace('"mini_rag"', '"mini_rag"')
                        content = content.replace("'mini-rag'", "'mini-rag'")
                        content = content.replace('"mini-rag"', '"mini-rag"')
                        content = content.replace("'.mini-rag'", "'.mini-rag'")
                        content = content.replace('".mini-rag"', '".mini-rag"')
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                            
                    except Exception as e:
                        print(f"Warning: Could not update imports in {file_path}: {e}")
    
    def verify_cleanup(self) -> Tuple[int, List[str]]:
        """Verify that cleanup was successful."""
        print("🔍 Verifying cleanup...")
        
        remaining_refs = []
        total_count = 0
        
        for root, dirs, files in os.walk(self.project_root):
            if '.git' in root:
                continue
                
            for file in files:
                if file.endswith(('.py', '.md', '.sh', '.yaml', '.json', '.txt')):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        # Look for any remaining "Mini-RAG" references (case insensitive)
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'Mini-RAG' in line.lower():
                                remaining_refs.append(f"{file_path}:{i}: {line.strip()}")
                                total_count += 1
                                
                    except Exception:
                        pass
        
        return total_count, remaining_refs
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        print("🧹 Starting Mini-RAG Reference Cleanup")
        print("=" * 50)
        
        # Initial scan
        print("📊 Scanning for Mini-RAG references...")
        initial_refs = self.scan_for_references()
        print(f"Found {sum(initial_refs.values())} total references")
        for ref, count in sorted(initial_refs.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  • {ref}: {count} occurrences")
        print()
        
        # Rename directories first
        self.rename_directories()
        
        # Update file contents
        self.update_file_contents()
        
        # Fix imports and paths
        self.update_imports_and_paths()
        
        # Verify cleanup
        remaining_count, remaining_refs = self.verify_cleanup()
        
        print("\n" + "=" * 50)
        print("🎯 Cleanup Summary:")
        print(f"📁 Directories renamed: {len(self.dirs_to_rename)}")
        print(f"📄 Files modified: {len(self.files_modified)}")
        print(f"⚠️  Remaining references: {remaining_count}")
        
        if remaining_refs:
            print("\nRemaining Mini-RAG references to review:")
            for ref in remaining_refs[:10]:  # Show first 10
                print(f"  • {ref}")
            if len(remaining_refs) > 10:
                print(f"  ... and {len(remaining_refs) - 10} more")
        
        if remaining_count == 0:
            print("✅ Cleanup successful! No Mini-RAG references remain.")
        else:
            print("⚠️  Some references remain - please review manually.")
        
        return remaining_count == 0

def main():
    project_root = Path(__file__).parent
    cleaner = Mini-RAGCleanup(project_root)
    
    success = cleaner.run_cleanup()
    
    if success:
        print("\n🎉 Ready to commit changes!")
        print("Next steps:")
        print("1. Review changes: git status")
        print("2. Test the application: ./rag-mini --help")
        print("3. Commit changes: git add . && git commit -m 'Remove all Mini-RAG references'")
    else:
        print("\n⚠️  Manual review required before committing.")

if __name__ == "__main__":
    main()
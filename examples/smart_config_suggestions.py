#!/usr/bin/env python3
"""
Smart configuration suggestions for FSS-Mini-RAG based on usage patterns.
Analyzes the indexed data to suggest optimal settings.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import sys

def analyze_project_patterns(manifest_path: Path):
    """Analyze project patterns and suggest optimizations."""
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    files = manifest.get('files', {})
    
    print("🔍 FSS-Mini-RAG Smart Tuning Analysis")
    print("=" * 50)
    
    # Analyze file types and chunking efficiency
    languages = Counter()
    chunk_efficiency = []
    large_files = []
    small_files = []
    
    for filepath, info in files.items():
        lang = info.get('language', 'unknown')
        languages[lang] += 1
        
        size = info.get('size', 0)
        chunks = info.get('chunks', 1)
        
        chunk_efficiency.append(chunks / max(1, size / 1000))  # chunks per KB
        
        if size > 10000:  # >10KB
            large_files.append((filepath, size, chunks))
        elif size < 500:  # <500B
            small_files.append((filepath, size, chunks))
    
    # Analysis results
    total_files = len(files)
    total_chunks = sum(info.get('chunks', 1) for info in files.values())
    avg_chunks_per_file = total_chunks / max(1, total_files)
    
    print(f"📊 Current Stats:")
    print(f"   Files: {total_files}")
    print(f"   Chunks: {total_chunks}")
    print(f"   Avg chunks/file: {avg_chunks_per_file:.1f}")
    
    print(f"\n🗂️ Language Distribution:")
    for lang, count in languages.most_common(10):
        pct = 100 * count / total_files
        print(f"   {lang}: {count} files ({pct:.1f}%)")
    
    print(f"\n💡 Smart Optimization Suggestions:")
    
    # Suggestion 1: Language-specific chunking
    if languages['python'] > 10:
        print(f"✨ Python Optimization:")
        print(f"   - Use function-level chunking (detected {languages['python']} Python files)")
        print(f"   - Increase chunk size to 3000 chars for Python (better context)")
    
    if languages['markdown'] > 5:
        print(f"✨ Markdown Optimization:")
        print(f"   - Use header-based chunking (detected {languages['markdown']} MD files)")
        print(f"   - Keep sections together for better search relevance")
    
    if languages['json'] > 20:
        print(f"✨ JSON Optimization:")
        print(f"   - Consider object-level chunking (detected {languages['json']} JSON files)")
        print(f"   - Might want to exclude large config JSONs")
    
    # Suggestion 2: File size optimization
    if large_files:
        print(f"\n📈 Large File Optimization:")
        print(f"   Found {len(large_files)} files >10KB:")
        for filepath, size, chunks in sorted(large_files, key=lambda x: x[1], reverse=True)[:3]:
            kb = size / 1024
            print(f"   - {filepath}: {kb:.1f}KB → {chunks} chunks")
        if len(large_files) > 5:
            print(f"   💡 Consider streaming threshold: 5KB (current: 1MB)")
    
    if small_files and len(small_files) > total_files * 0.3:
        print(f"\n📉 Small File Optimization:")
        print(f"   {len(small_files)} files <500B might not need chunking")
        print(f"   💡 Consider: combine small files or skip tiny ones")
    
    # Suggestion 3: Search optimization
    avg_efficiency = sum(chunk_efficiency) / len(chunk_efficiency)
    print(f"\n🔍 Search Optimization:")
    if avg_efficiency < 0.5:
        print(f"   💡 Chunks are large relative to files - consider smaller chunks")
        print(f"   💡 Current: {avg_chunks_per_file:.1f} chunks/file, try 2-3 chunks/file")
    elif avg_efficiency > 2:
        print(f"   💡 Many small chunks - consider larger chunk size")
        print(f"   💡 Reduce chunk overhead with 2000-4000 char chunks")
    
    # Suggestion 4: Smart defaults
    print(f"\n⚙️ Recommended Config Updates:")
    print(f"""{{
  "chunking": {{
    "max_size": {3000 if languages['python'] > languages['markdown'] else 2000},
    "min_size": 200,
    "strategy": "{"function" if languages['python'] > 10 else "semantic"}",
    "language_specific": {{
      "python": {{ "max_size": 3000, "strategy": "function" }},
      "markdown": {{ "max_size": 2500, "strategy": "header" }},
      "json": {{ "max_size": 1000, "skip_large": true }}
    }}
  }},
  "files": {{
    "skip_small_files": {500 if len(small_files) > total_files * 0.3 else 0},
    "streaming_threshold_kb": {5 if len(large_files) > 5 else 1024}
  }}
}}""")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smart_config_suggestions.py <path_to_manifest.json>")
        sys.exit(1)
    
    manifest_path = Path(sys.argv[1])
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)
        
    analyze_project_patterns(manifest_path)
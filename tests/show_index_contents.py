#!/usr/bin/env python3
"""
Show what files are actually indexed in the RAG system.
"""

import sys
import os
from pathlib import Path

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from mini_rag.vector_store import VectorStore
from collections import Counter

project_path = Path.cwd()
store = VectorStore(project_path)
store._connect()

# Get all indexed files
files = []
chunks_by_file = Counter()
chunk_types = Counter()

for row in store.table.to_pandas().itertuples():
    files.append(row.file_path)
    chunks_by_file[row.file_path] += 1
    chunk_types[row.chunk_type] += 1

unique_files = sorted(set(files))

print(f"\n Indexed Files Summary")
print(f"Total files: {len(unique_files)}")
print(f"Total chunks: {len(files)}")
print(f"\nChunk types: {dict(chunk_types)}")

print(f"\n Files with most chunks:")
for file, count in chunks_by_file.most_common(10):
    print(f"  {count:3d} chunks: {file}")

print(f"\n Text-to-speech files:")
tts_files = [f for f in unique_files if 'text-to-speech' in f or 'speak' in f.lower()]
for f in tts_files:
    print(f"  - {f} ({chunks_by_file[f]} chunks)")
"""Test with smaller min_chunk_size."""

from mini_rag.chunker import CodeChunker
from pathlib import Path

test_code = '''"""Test module."""

import os

class MyClass:
    def method(self):
        return 42

def my_function():
    return "hello"
'''

# Create chunker with smaller min_chunk_size
chunker = CodeChunker(min_chunk_size=1)  # Allow tiny chunks
chunks = chunker.chunk_file(Path("test.py"), test_code)

print(f"Created {len(chunks)} chunks:")
for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}: {chunk.chunk_type} '{chunk.name}'")
    print(f"Lines {chunk.start_line}-{chunk.end_line}")
    print(f"Size: {len(chunk.content.splitlines())} lines")
    print("-" * 40)
#!/usr/bin/env python3
"""Test RAG system integration with smart chunking."""

import tempfile
import shutil
from pathlib import Path
from claude_rag.indexer import ProjectIndexer
from claude_rag.search import CodeSearcher

# Sample Python file with proper structure
sample_code = '''"""
Sample module for testing RAG system.
This module demonstrates various Python constructs.
"""

import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

# Module-level constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


@dataclass
class Config:
    """Configuration dataclass."""
    timeout: int = DEFAULT_TIMEOUT
    retries: int = MAX_RETRIES


class DataProcessor:
    """
    Main data processor class.
    
    This class handles the processing of various data types
    and provides a unified interface for data operations.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the processor with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._cache = {}
        self._initialized = False
        
    def process(self, data: List[Dict]) -> List[Dict]:
        """
        Process a list of data items.
        
        Args:
            data: List of dictionaries to process
            
        Returns:
            Processed data list
        """
        if not self._initialized:
            self._initialize()
            
        results = []
        for item in data:
            processed = self._process_item(item)
            results.append(processed)
            
        return results
    
    def _initialize(self):
        """Initialize internal state."""
        self._cache.clear()
        self._initialized = True
        
    def _process_item(self, item: Dict) -> Dict:
        """Process a single item."""
        # Implementation details
        return {**item, 'processed': True}


def main():
    """Main entry point."""
    config = Config()
    processor = DataProcessor(config)
    
    test_data = [
        {'id': 1, 'value': 'test1'},
        {'id': 2, 'value': 'test2'},
    ]
    
    results = processor.process(test_data)
    print(f"Processed {len(results)} items")


if __name__ == "__main__":
    main()
'''

# Sample markdown file
sample_markdown = '''# RAG System Documentation

## Overview

This is the documentation for the RAG system that demonstrates
smart chunking capabilities.

## Features

### Smart Code Chunking

The system intelligently chunks code files by:
- Keeping docstrings with their functions/classes
- Creating logical boundaries at function and class definitions
- Preserving context through parent-child relationships

### Markdown Support

Markdown files are chunked by sections with:
- Header-based splitting
- Context overlap between chunks
- Preservation of document structure

## Usage

### Basic Example

```python
from claude_rag import ProjectIndexer

indexer = ProjectIndexer("/path/to/project")
indexer.index_project()
```

### Advanced Configuration

You can customize the chunking behavior:

```python
from claude_rag import CodeChunker

chunker = CodeChunker(
    max_chunk_size=1000,
    min_chunk_size=50
)
```

## API Reference

### ProjectIndexer

Main class for indexing projects.

### CodeSearcher

Provides semantic search capabilities.
'''


def test_integration():
    """Test the complete RAG system with smart chunking."""
    
    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create test files
        (project_path / "processor.py").write_text(sample_code)
        (project_path / "README.md").write_text(sample_markdown)
        
        print("=" * 60)
        print("TESTING RAG SYSTEM INTEGRATION")
        print("=" * 60)
        
        # Index the project
        print("\n1. Indexing project...")
        indexer = ProjectIndexer(project_path)
        stats = indexer.index_project()
        
        print(f"   - Files indexed: {stats['files_indexed']}")
        print(f"   - Total chunks: {stats['total_chunks']}")
        print(f"   - Indexing time: {stats['indexing_time']:.2f}s")
        
        # Verify chunks were created properly
        print("\n2. Verifying chunk metadata...")
        
        # Initialize searcher
        searcher = CodeSearcher(project_path)
        
        # Search for specific content
        print("\n3. Testing search functionality...")
        
        # Test 1: Search for class with docstring
        results = searcher.search("data processor class unified interface", top_k=3)
        print(f"\n   Test 1 - Class search:")
        for i, result in enumerate(results[:1]):
            print(f"   - Match {i+1}: {result['file_path']}")
            print(f"     Chunk type: {result['chunk_type']}")
            print(f"     Score: {result['score']:.3f}")
            if 'This class handles' in result['content']:
                print("     [OK] Docstring included with class")
            else:
                print("     [FAIL] Docstring not found")
        
        # Test 2: Search for method with docstring
        results = searcher.search("process list of data items", top_k=3)
        print(f"\n   Test 2 - Method search:")
        for i, result in enumerate(results[:1]):
            print(f"   - Match {i+1}: {result['file_path']}")
            print(f"     Chunk type: {result['chunk_type']}")
            print(f"     Parent class: {result.get('parent_class', 'N/A')}")
            if 'Args:' in result['content'] and 'Returns:' in result['content']:
                print("     [OK] Docstring included with method")
            else:
                print("     [FAIL] Method docstring not complete")
        
        # Test 3: Search markdown content
        results = searcher.search("smart chunking capabilities markdown", top_k=3)
        print(f"\n   Test 3 - Markdown search:")
        for i, result in enumerate(results[:1]):
            print(f"   - Match {i+1}: {result['file_path']}")
            print(f"     Chunk type: {result['chunk_type']}")
            print(f"     Lines: {result['start_line']}-{result['end_line']}")
        
        # Test 4: Verify chunk navigation
        print(f"\n   Test 4 - Chunk navigation:")
        all_results = searcher.search("", top_k=100)  # Get all chunks
        py_chunks = [r for r in all_results if r['file_path'].endswith('.py')]
        
        if py_chunks:
            first_chunk = py_chunks[0]
            print(f"   - First chunk: index={first_chunk.get('chunk_index', 'N/A')}")
            print(f"     Next chunk ID: {first_chunk.get('next_chunk_id', 'N/A')}")
            
            # Verify chain
            valid_chain = True
            for i in range(len(py_chunks) - 1):
                curr = py_chunks[i]
                next_chunk = py_chunks[i + 1]
                expected_next = f"processor_{i+1}"
                if curr.get('next_chunk_id') != expected_next:
                    valid_chain = False
                    break
            
            if valid_chain:
                print("     [OK] Chunk navigation chain is valid")
            else:
                print("     [FAIL] Chunk navigation chain broken")
        
        print("\n" + "=" * 60)
        print("INTEGRATION TEST COMPLETED")
        print("=" * 60)


if __name__ == "__main__":
    test_integration()
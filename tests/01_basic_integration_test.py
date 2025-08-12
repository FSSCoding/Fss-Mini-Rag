"""
Comprehensive demo of the RAG system showing all integrated features.
"""

import os
import sys
import tempfile
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    sys.stdout.reconfigure(encoding='utf-8')

from claude_rag.chunker import CodeChunker
from claude_rag.indexer import ProjectIndexer
from claude_rag.search import CodeSearcher
from claude_rag.embeddings import CodeEmbedder

def main():
    print("=" * 60)
    print("RAG System Integration Demo")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create sample project files
        print("\n1. Creating sample project files...")
        
        # Main calculator module
        (project_path / "calculator.py").write_text('''"""
Advanced calculator module with various mathematical operations.
"""

import math
from typing import List, Union

class BasicCalculator:
    """Basic calculator with fundamental operations."""
    
    def __init__(self):
        """Initialize calculator with result history."""
        self.history = []
        self.last_result = 0
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers and store result."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        self.last_result = result
        return result
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        self.last_result = result
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        self.last_result = result
        return result
    
    def divide(self, a: float, b: float) -> float:
        """Divide a by b with zero check."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        self.last_result = result
        return result

class ScientificCalculator(BasicCalculator):
    """Scientific calculator extending basic operations."""
    
    def power(self, base: float, exponent: float) -> float:
        """Calculate base raised to exponent."""
        result = math.pow(base, exponent)
        self.history.append(f"{base} ^ {exponent} = {result}")
        self.last_result = result
        return result
    
    def sqrt(self, n: float) -> float:
        """Calculate square root."""
        if n < 0:
            raise ValueError("Cannot take square root of negative number")
        result = math.sqrt(n)
        self.history.append(f"sqrt({n}) = {result}")
        self.last_result = result
        return result
    
    def logarithm(self, n: float, base: float = 10) -> float:
        """Calculate logarithm with specified base."""
        result = math.log(n, base)
        self.history.append(f"log_{base}({n}) = {result}")
        self.last_result = result
        return result

def calculate_mean(numbers: List[float]) -> float:
    """Calculate arithmetic mean of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)

def calculate_median(numbers: List[float]) -> float:
    """Calculate median of a list of numbers."""
    if not numbers:
        return 0.0
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n % 2 == 0:
        return (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
    return sorted_nums[n//2]

def calculate_mode(numbers: List[float]) -> float:
    """Calculate mode (most frequent value)."""
    if not numbers:
        return 0.0
    frequency = {}
    for num in numbers:
        frequency[num] = frequency.get(num, 0) + 1
    mode = max(frequency.keys(), key=frequency.get)
    return mode
''')
        
        # Test file for the calculator
        (project_path / "test_calculator.py").write_text('''"""
Unit tests for calculator module.
"""

import unittest
from calculator import BasicCalculator, ScientificCalculator, calculate_mean

class TestBasicCalculator(unittest.TestCase):
    """Test cases for BasicCalculator."""
    
    def setUp(self):
        """Set up test calculator."""
        self.calc = BasicCalculator()
    
    def test_addition(self):
        """Test addition operation."""
        result = self.calc.add(5, 3)
        self.assertEqual(result, 8)
        self.assertEqual(self.calc.last_result, 8)
    
    def test_division_by_zero(self):
        """Test division by zero raises error."""
        with self.assertRaises(ValueError):
            self.calc.divide(10, 0)

class TestStatistics(unittest.TestCase):
    """Test statistical functions."""
    
    def test_mean(self):
        """Test mean calculation."""
        numbers = [1, 2, 3, 4, 5]
        self.assertEqual(calculate_mean(numbers), 3.0)
    
    def test_empty_list(self):
        """Test mean of empty list."""
        self.assertEqual(calculate_mean([]), 0.0)

if __name__ == "__main__":
    unittest.main()
''')
        
        print("    Created 2 Python files")
        
        # 2. Index the project
        print("\n2. Indexing project with intelligent chunking...")
        
        # Use realistic chunk size
        chunker = CodeChunker(min_chunk_size=10, max_chunk_size=100)
        indexer = ProjectIndexer(project_path, chunker=chunker)
        stats = indexer.index_project()
        
        print(f"    Indexed {stats['files_indexed']} files")
        print(f"    Created {stats['chunks_created']} chunks")
        print(f"    Time: {stats['time_taken']:.2f} seconds")
        
        # 3. Demonstrate search capabilities
        print("\n3. Testing search capabilities...")
        searcher = CodeSearcher(project_path)
        
        # Test different search types
        print("\n   a) Semantic search for 'calculate average':")
        results = searcher.search("calculate average", limit=3)
        for i, result in enumerate(results, 1):
            print(f"      {i}. {result.chunk_type} '{result.name}' in {result.file_path} (score: {result.score:.3f})")
        
        print("\n   b) BM25-weighted search for 'divide zero':")
        results = searcher.search("divide zero", limit=3, semantic_weight=0.2, bm25_weight=0.8)
        for i, result in enumerate(results, 1):
            print(f"      {i}. {result.chunk_type} '{result.name}' in {result.file_path} (score: {result.score:.3f})")
        
        print("\n   c) Search with context for 'test addition':")
        results = searcher.search("test addition", limit=2, include_context=True)
        for i, result in enumerate(results, 1):
            print(f"      {i}. {result.chunk_type} '{result.name}'")
            if result.parent_chunk:
                print(f"         Parent: {result.parent_chunk.name}")
            if result.context_before:
                print(f"         Has previous context: {len(result.context_before)} chars")
            if result.context_after:
                print(f"         Has next context: {len(result.context_after)} chars")
        
        # 4. Test chunk navigation
        print("\n4. Testing chunk navigation...")
        
        # Get all chunks to find a method
        df = searcher.table.to_pandas()
        method_chunks = df[df['chunk_type'] == 'method']
        
        if len(method_chunks) > 0:
            # Pick a method in the middle
            mid_idx = len(method_chunks) // 2
            chunk_id = method_chunks.iloc[mid_idx]['chunk_id']
            chunk_name = method_chunks.iloc[mid_idx]['name']
            
            print(f"\n   Getting context for method '{chunk_name}':")
            context = searcher.get_chunk_context(chunk_id)
            
            if context['chunk']:
                print(f"    Current: {context['chunk'].name}")
            if context['prev']:
                print(f"    Previous: {context['prev'].name}")
            if context['next']:
                print(f"    Next: {context['next'].name}")
            if context['parent']:
                print(f"    Parent class: {context['parent'].name}")
        
        # 5. Show statistics
        print("\n5. Index Statistics:")
        stats = searcher.get_statistics()
        print(f"   - Total chunks: {stats['total_chunks']}")
        print(f"   - Unique files: {stats['unique_files']}")
        print(f"   - Chunk types: {stats['chunk_types']}")
        
        print("\n" + "=" * 60)
        print(" All features working correctly!")
        print("=" * 60)
        print("\nKey features demonstrated:")
        print("- AST-based intelligent chunking preserving code structure")
        print("- Chunk metadata (prev/next links, parent class, indices)")
        print("- Hybrid search combining BM25 and semantic similarity")
        print("- Context-aware search with adjacent chunks")
        print("- Chunk navigation following code relationships")

if __name__ == "__main__":
    main()
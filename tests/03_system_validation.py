"""
Integration test to verify all three agents' work integrates properly.
"""

import sys
import os
import tempfile
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    sys.stdout.reconfigure(encoding='utf-8')

from mini_rag.chunker import CodeChunker
from mini_rag.indexer import ProjectIndexer
from mini_rag.search import CodeSearcher
from mini_rag.ollama_embeddings import OllamaEmbedder as CodeEmbedder
from mini_rag.query_expander import QueryExpander
from mini_rag.config import RAGConfig

def test_chunker():
    """Test that chunker creates chunks with all required metadata."""
    print("1. Testing Chunker...")
    
    # Create test Python file with more substantial content
    test_code = '''"""Test module for integration testing the chunker."""

import os
import sys

class TestClass:
    """A test class with multiple methods."""
    
    def __init__(self):
        """Initialize the test class."""
        self.value = 42
        self.name = "test"
    
    def method_one(self):
        """First method with some logic."""
        result = self.value * 2
        return result
    
    def method_two(self, x):
        """Second method that takes a parameter."""
        if x > 0:
            return self.value + x
        else:
            return self.value - x
    
    def method_three(self):
        """Third method for testing."""
        data = []
        for i in range(10):
            data.append(i * self.value)
        return data

class AnotherClass:
    """Another test class."""
    
    def __init__(self, name):
        """Initialize with name."""
        self.name = name
    
    def process(self):
        """Process something."""
        return f"Processing {self.name}"

def standalone_function(arg1, arg2):
    """A standalone function that does something."""
    result = arg1 + arg2
    return result * 2

def another_function():
    """Another standalone function."""
    data = {"key": "value", "number": 123}
    return data
'''
    
    chunker = CodeChunker(min_chunk_size=1)  # Use small chunk size for testing
    chunks = chunker.chunk_file(Path("test.py"), test_code)
    
    print(f"    Created {len(chunks)} chunks")
    
    # Debug: Show what chunks were created
    print("   Chunks created:")
    for chunk in chunks:
        print(f"     - Type: {chunk.chunk_type}, Name: {chunk.name}, Lines: {chunk.start_line}-{chunk.end_line}")
    
    # Check metadata
    issues = []
    for i, chunk in enumerate(chunks):
        if chunk.chunk_index is None:
            issues.append(f"Chunk {i} missing chunk_index")
        if chunk.total_chunks is None:
            issues.append(f"Chunk {i} missing total_chunks")
        if chunk.file_lines is None:
            issues.append(f"Chunk {i} missing file_lines")
        
        # Check links (except first/last)
        if i > 0 and chunk.prev_chunk_id is None:
            issues.append(f"Chunk {i} missing prev_chunk_id")
        if i < len(chunks) - 1 and chunk.next_chunk_id is None:
            issues.append(f"Chunk {i} missing next_chunk_id")
        
        # Check parent_class for methods
        if chunk.chunk_type == 'method' and chunk.parent_class is None:
            issues.append(f"Method chunk {chunk.name} missing parent_class")
            
        print(f"   - Chunk {i}: {chunk.chunk_type} '{chunk.name}' "
              f"[{chunk.chunk_index}/{chunk.total_chunks}] "
              f"prev={chunk.prev_chunk_id} next={chunk.next_chunk_id}")
    
    if issues:
        print("    Issues found:")
        for issue in issues:
            print(f"      - {issue}")
    else:
        print("    All metadata present")
    
    return len(issues) == 0

def test_indexer_storage():
    """Test that indexer stores the new metadata."""
    print("\n2. Testing Indexer Storage...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create test file
        test_file = project_path / "test.py"
        test_file.write_text('''
class MyClass:
    def my_method(self):
        return 42
''')
        
        # Index the project with small chunk size for testing
        from mini_rag.chunker import CodeChunker
        chunker = CodeChunker(min_chunk_size=1)
        indexer = ProjectIndexer(project_path, chunker=chunker)
        stats = indexer.index_project()
        
        print(f"    Indexed {stats['chunks_created']} chunks")
        
        # Check what was stored
        if indexer.table:
            df = indexer.table.to_pandas()
            columns = df.columns.tolist()
            
            required_fields = ['chunk_id', 'prev_chunk_id', 'next_chunk_id', 'parent_class']
            missing_fields = [f for f in required_fields if f not in columns]
            
            if missing_fields:
                print(f"    Missing fields in database: {missing_fields}")
                print(f"   Current fields: {columns}")
                return False
            else:
                print("    All required fields in database schema")
                
                # Check if data is actually stored
                sample = df.iloc[0] if len(df) > 0 else None
                if sample is not None:
                    print(f"   Sample chunk_id: {sample.get('chunk_id', 'MISSING')}")
                    print(f"   Sample prev_chunk_id: {sample.get('prev_chunk_id', 'MISSING')}")
                    print(f"   Sample next_chunk_id: {sample.get('next_chunk_id', 'MISSING')}")
                    print(f"   Sample parent_class: {sample.get('parent_class', 'MISSING')}")
        
        return len(missing_fields) == 0

def test_search_integration():
    """Test that search uses the new metadata."""
    print("\n3. Testing Search Integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Create test files with proper content that will create multiple chunks
        (project_path / "math_utils.py").write_text('''"""Math utilities module."""

import math

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        """Initialize calculator."""
        self.result = 0
    
    def add(self, a, b):
        """Add two numbers."""
        self.result = a + b
        return self.result
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        self.result = a * b
        return self.result
    
    def divide(self, a, b):
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        self.result = a / b
        return self.result

class AdvancedCalculator(Calculator):
    """Advanced calculator with more operations."""
    
    def power(self, a, b):
        """Raise a to power b."""
        self.result = a ** b
        return self.result
    
    def sqrt(self, a):
        """Calculate square root."""
        self.result = math.sqrt(a)
        return self.result

def compute_average(numbers):
    """Compute average of a list."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

def compute_median(numbers):
    """Compute median of a list."""
    if not numbers:
        return 0
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    if n % 2 == 0:
        return (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
    return sorted_nums[n//2]
''')
        
        # Index with small chunk size for testing
        chunker = CodeChunker(min_chunk_size=1)
        indexer = ProjectIndexer(project_path, chunker=chunker)
        indexer.index_project()
        
        # Search
        searcher = CodeSearcher(project_path)
        
        # Test BM25 integration
        results = searcher.search("multiply numbers", top_k=5, 
                                 semantic_weight=0.3, bm25_weight=0.7)
        
        if results:
            print(f"    BM25 + semantic search returned {len(results)} results")
            for r in results[:2]:
                print(f"     - {r.chunk_type} '{r.name}' score={r.score:.3f}")
        else:
            print("    No search results returned")
            return False
        
        # Test context retrieval
        print("\n   Testing context retrieval...")
        if searcher.table:
            df = searcher.table.to_pandas()
            print(f"   Total chunks in DB: {len(df)}")
            
            # Find a method chunk to test parent context
            method_chunks = df[df['chunk_type'] == 'method']
            if len(method_chunks) > 0:
                method_chunk_id = method_chunks.iloc[0]['chunk_id']
                context = searcher.get_chunk_context(method_chunk_id)
                
                if context['chunk']:
                    print(f"    Got main chunk: {context['chunk'].name}")
                if context['prev']:
                    print(f"    Got previous chunk: {context['prev'].name}")
                else:
                    print(f"   - No previous chunk (might be first)")
                if context['next']:
                    print(f"    Got next chunk: {context['next'].name}")
                else:
                    print(f"   - No next chunk (might be last)")
                if context['parent']:
                    print(f"    Got parent chunk: {context['parent'].name}")
                else:
                    print(f"   - No parent chunk")
                    
                # Test include_context in search
                results_with_context = searcher.search("add", include_context=True, top_k=2)
                if results_with_context:
                    print(f"   Found {len(results_with_context)} results with context")
                    for r in results_with_context:
                        has_context = bool(r.context_before or r.context_after or r.parent_chunk)
                        print(f"     - {r.name}: context_before={bool(r.context_before)}, "
                              f"context_after={bool(r.context_after)}, parent={bool(r.parent_chunk)}")
                    
                    # Check if at least one result has some context
                    if any(r.context_before or r.context_after or r.parent_chunk for r in results_with_context):
                        print("    Search with context working")
                        return True
                    else:
                        print("    Search returned results but no context attached")
                        return False
                else:
                    print("    No search results returned")
                    return False
            else:
                print("    No method chunks found in database")
                return False
        
        return True

def test_server():
    """Test that server still works."""
    print("\n4. Testing Server...")
    
    # Just check if we can import and create server instance
    try:
        from mini_rag.server import RAGServer
        server = RAGServer(Path("."), port=7778)
        print("    Server can be instantiated")
        return True
    except Exception as e:
        print(f"    Server error: {e}")
        return False

def test_new_features():
    """Test new features: query expansion and smart ranking."""
    print("\n5. Testing New Features (Query Expansion & Smart Ranking)...")
    
    try:
        # Test configuration loading
        config = RAGConfig()
        print(f"    ✅ Configuration loaded successfully")
        print(f"       Query expansion enabled: {config.search.expand_queries}")
        print(f"       Max expansion terms: {config.llm.max_expansion_terms}")
        
        # Test query expander (will use mock if Ollama unavailable)
        expander = QueryExpander(config)
        test_query = "authentication"
        
        if expander.is_available():
            expanded = expander.expand_query(test_query)
            print(f"    ✅ Query expansion working: '{test_query}' → '{expanded}'")
        else:
            print(f"    ⚠️  Query expansion offline (Ollama not available)")
            # Test that it still returns original query
            expanded = expander.expand_query(test_query)
            if expanded == test_query:
                print(f"    ✅ Graceful degradation working: returns original query")
            else:
                print(f"    ❌ Error: should return original query when offline")
                return False
        
        # Test smart ranking (this always works as it's zero-overhead)
        print("    🧮 Testing smart ranking...")
        
        # Create a simple test to verify the method exists and can be called
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple test project
            test_file = temp_path / "README.md"
            test_file.write_text("# Test Project\nThis is a test README file.")
            
            try:
                searcher = CodeSearcher(temp_path)
                # Test that the _smart_rerank method exists
                if hasattr(searcher, '_smart_rerank'):
                    print("    ✅ Smart ranking method available")
                    return True
                else:
                    print("    ❌ Smart ranking method not found")
                    return False
                    
            except Exception as e:
                print(f"    ❌ Smart ranking test failed: {e}")
                return False
        
    except Exception as e:
        print(f"    ❌ New features test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("=" * 50)
    print("RAG System Integration Check")
    print("=" * 50)
    
    results = {
        "Chunker": test_chunker(),
        "Indexer": test_indexer_storage(), 
        "Search": test_search_integration(),
        "Server": test_server(),
        "New Features": test_new_features()
    }
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    all_passed = True
    for component, passed in results.items():
        status = " PASS" if passed else " FAIL"
        print(f"{component}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n All integration tests passed!")
    else:
        print("\n️  Some tests failed - fixes needed!")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test script for adjacent chunk retrieval functionality.
"""

from pathlib import Path
from mini_rag.search import CodeSearcher
from mini_rag.embeddings import CodeEmbedder

def test_context_retrieval():
    """Test the new context retrieval functionality."""
    
    # Initialize searcher
    project_path = Path(__file__).parent
    try:
        embedder = CodeEmbedder()
        searcher = CodeSearcher(project_path, embedder)
        
        print("Testing search with context...")
        
        # Test 1: Search without context
        print("\n1. Search WITHOUT context:")
        results = searcher.search("chunk metadata", limit=3, include_context=False)
        for i, result in enumerate(results, 1):
            print(f"  Result {i}: {result.file_path}:{result.start_line}-{result.end_line}")
            print(f"    Type: {result.chunk_type}, Name: {result.name}")
            print(f"    Has context_before: {result.context_before is not None}")
            print(f"    Has context_after: {result.context_after is not None}")
            print(f"    Has parent_chunk: {result.parent_chunk is not None}")
        
        # Test 2: Search with context
        print("\n2. Search WITH context:")
        results = searcher.search("chunk metadata", limit=3, include_context=True)
        for i, result in enumerate(results, 1):
            print(f"  Result {i}: {result.file_path}:{result.start_line}-{result.end_line}")
            print(f"    Type: {result.chunk_type}, Name: {result.name}")
            print(f"    Has context_before: {result.context_before is not None}")
            print(f"    Has context_after: {result.context_after is not None}")
            print(f"    Has parent_chunk: {result.parent_chunk is not None}")
            
            if result.context_before:
                print(f"    Context before preview: {result.context_before[:50]}...")
            if result.context_after:
                print(f"    Context after preview: {result.context_after[:50]}...")
            if result.parent_chunk:
                print(f"    Parent chunk: {result.parent_chunk.name} ({result.parent_chunk.chunk_type})")
        
        # Test 3: get_chunk_context method
        print("\n3. Testing get_chunk_context method:")
        # Get a sample chunk_id from the first result
        df = searcher.table.to_pandas()
        if not df.empty:
            sample_chunk_id = df.iloc[0]['chunk_id']
            print(f"  Getting context for chunk_id: {sample_chunk_id}")
            
            context = searcher.get_chunk_context(sample_chunk_id)
            
            if context['chunk']:
                print(f"    Main chunk: {context['chunk'].file_path}:{context['chunk'].start_line}")
            if context['prev']:
                print(f"    Previous chunk: lines {context['prev'].start_line}-{context['prev'].end_line}")
            if context['next']:
                print(f"    Next chunk: lines {context['next'].start_line}-{context['next'].end_line}")
            if context['parent']:
                print(f"    Parent chunk: {context['parent'].name} ({context['parent'].chunk_type})")
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_context_retrieval()
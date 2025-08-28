#!/usr/bin/env python3
"""
Basic usage example for FSS-Mini-RAG.
Shows how to index a project and search it programmatically.
"""

from pathlib import Path

from mini_rag import CodeEmbedder, CodeSearcher, ProjectIndexer


def main():
    # Example project path - change this to your project
    project_path = Path(".")  # Current directory

    print("=== FSS-Mini-RAG Basic Usage Example ===")
    print(f"Project: {project_path}")

    # Initialize the embedding system
    print("\n1. Initializing embedding system...")
    embedder = CodeEmbedder()
    print(f"   Using: {embedder.get_embedding_info()['method']}")

    # Initialize indexer and searcher
    indexer = ProjectIndexer(project_path, embedder)
    searcher = CodeSearcher(project_path, embedder)

    # Index the project
    print("\n2. Indexing project...")
    result = indexer.index_project()

    print(f"   Files processed: {result.get('files_processed', 0)}")
    print(f"   Chunks created: {result.get('chunks_created', 0)}")
    print(f"   Time taken: {result.get('indexing_time', 0):.2f}s")

    # Get index statistics
    print("\n3. Index statistics:")
    stats = indexer.get_stats()
    print(f"   Total files: {stats.get('total_files', 0)}")
    print(f"   Total chunks: {stats.get('total_chunks', 0)}")
    print(f"   Languages: {', '.join(stats.get('languages', []))}")

    # Example searches
    queries = [
        "chunker function",
        "embedding system",
        "search implementation",
        "file watcher",
        "error handling",
    ]

    print("\n4. Example searches:")
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = searcher.search(query, top_k=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"      {i}. {result.file_path.name} (score: {result.score:.3f})")
                print(f"         Type: {result.chunk_type}")
                # Show first 60 characters of content
                content_preview = result.content.replace("\n", " ")[:60]
                print(f"         Preview: {content_preview}...")
        else:
            print("      No results found")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

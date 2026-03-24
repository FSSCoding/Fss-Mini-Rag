"""
FSS-Mini-RAG - Self-contained research and code search system.

Hybrid semantic + BM25 search with RRF fusion, web scraping, deep research,
LLM synthesis, and desktop GUI. Works with any OpenAI-compatible endpoint.
"""

__version__ = "2.3.0"

from .chunker import CodeChunker
from .indexer import ProjectIndexer
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .search import CodeSearcher
from .watcher import FileWatcher

__all__ = [
    "CodeEmbedder",
    "CodeChunker",
    "ProjectIndexer",
    "CodeSearcher",
    "FileWatcher",
]

"""
FSS-Mini-RAG - Lightweight, portable semantic code search.

A hybrid RAG system with Ollama-first embeddings, ML fallback, and streaming indexing.
Designed for portability, efficiency, and simplicity across projects and computers.
"""

__version__ = "2.1.0"

from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .chunker import CodeChunker
from .indexer import ProjectIndexer
from .search import CodeSearcher
from .watcher import FileWatcher

# Auto-update system (graceful import for legacy versions)
try:
    from .updater import UpdateChecker, check_for_updates, get_updater
    __all__ = [
        "CodeEmbedder",
        "CodeChunker", 
        "ProjectIndexer",
        "CodeSearcher",
        "FileWatcher",
        "UpdateChecker",
        "check_for_updates", 
        "get_updater",
    ]
except ImportError:
    __all__ = [
        "CodeEmbedder",
        "CodeChunker", 
        "ProjectIndexer",
        "CodeSearcher",
        "FileWatcher",
    ]
"""Search and synthesis service for the GUI.

Wraps CodeSearcher and LLMSynthesizer with timing and event emission.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..events import EventBus

logger = logging.getLogger(__name__)


class SearchService:
    """Manages search and LLM synthesis operations."""

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._searchers: Dict[str, Any] = {}
        self.llm_url: str = "http://localhost:1234/v1"
        self.llm_model: str = "auto"
        self.embedding_url: str = "http://localhost:1234/v1"

    def search(self, path: str, query: str, top_k: int = 20, expand: bool = False):
        """Run search against a collection."""
        self.bus.emit("search:started", {"query": query, "mode": "search"})

        try:
            searcher = self._get_searcher(path)
            if not searcher:
                self.bus.emit("search:error", {"error": "Failed to initialise searcher"})
                return

            # Query expansion
            display_query = query
            if expand:
                try:
                    expanded = searcher.query_expander.expand_query(query)
                    if expanded != query:
                        display_query = f"{query} [expanded]"
                        query = expanded
                except Exception:
                    pass

            t0 = time.time()
            results = searcher.search(query, top_k=top_k)
            search_ms = (time.time() - t0) * 1000

            self.bus.emit("search:completed", {
                "results": results,
                "query": display_query,
                "timing_ms": search_ms,
            })
        except Exception as e:
            self.bus.emit("search:error", {"error": str(e)})

    def synthesize(self, path: str, query: str, results: list):
        """Send search results to LLM for synthesis."""
        self.bus.emit("synthesis:started", {"query": query})

        try:
            from mini_rag.llm_synthesizer import LLMSynthesizer

            logger.info(f"Synthesis: LLM={self.llm_url} model={self.llm_model}")
            synth = LLMSynthesizer(
                base_url=self.llm_url,
                model=self.llm_model if self.llm_model != "auto" else None,
                provider="openai",
            )
            t0 = time.time()
            result = synth.synthesize_search_results(query, results, Path(path))
            synth_ms = (time.time() - t0) * 1000

            self.bus.emit("synthesis:completed", {
                "text": result.summary,
                "timing_ms": synth_ms,
            })
        except Exception as e:
            self.bus.emit("search:error", {"error": f"Synthesis failed: {e}"})

    def _get_searcher(self, path: str):
        """Get or create a cached searcher for a path."""
        if path not in self._searchers:
            try:
                from mini_rag.search import CodeSearcher
                self._searchers[path] = CodeSearcher(Path(path))
            except Exception:
                return None
        return self._searchers[path]

    def invalidate(self, path: str = None):
        """Invalidate cached searcher(s) after reindexing."""
        if path:
            self._searchers.pop(path, None)
        else:
            self._searchers.clear()

"""Centralised application state.

Single source of truth for the GUI. Components read from state and
emit events to change it. No widget should hold its own state.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AppState:
    """Complete GUI application state."""

    # Collections
    collections: List[str] = field(default_factory=list)
    active_collection: Optional[str] = None

    # Search
    search_query: str = ""
    search_mode: str = "search"  # "search" or "ask"
    results: list = field(default_factory=list)
    selected_result_idx: Optional[int] = None
    synthesis_text: str = ""

    # Indexing
    indexing: bool = False
    indexing_path: Optional[str] = None
    indexing_progress: float = 0.0
    indexing_status: str = ""

    # Timing
    last_search_ms: float = 0.0
    last_init_ms: float = 0.0
    last_synthesis_ms: float = 0.0

    # Settings
    embedding_url: str = "http://localhost:1234/v1"
    embedding_model: str = "auto"
    llm_url: str = "http://localhost:1234/v1"
    llm_model: str = "auto"
    embedding_profile: str = "precision"
    expand_queries: bool = False

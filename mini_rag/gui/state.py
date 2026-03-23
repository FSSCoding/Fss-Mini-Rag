"""Observable application state.

Single source of truth for the GUI. When a field changes, an event
is auto-emitted on the EventBus so subscribed components update
without manual wiring.

Usage:
    state = ObservableState(event_bus)
    state.operation = "searching"   # auto-emits "state:operation"

Components subscribe:
    bus.on("state:operation", lambda d: ...)
    # d = {"field": "operation", "old": "idle", "new": "searching"}
"""

from typing import Any, Dict, List, Optional

# Fields with their defaults. Any field listed here is observable.
_STATE_FIELDS: Dict[str, Any] = {
    # Collections
    "collections": [],
    "active_collection": None,

    # Search
    "search_query": "",
    "search_mode": "search",  # "search" or "ask"
    "results": [],
    "selected_result_idx": None,
    "synthesis_text": "",

    # Indexing
    "indexing": False,
    "indexing_path": None,
    "indexing_progress": 0.0,
    "indexing_status": "",

    # Timing
    "last_search_ms": 0.0,
    "last_init_ms": 0.0,
    "last_synthesis_ms": 0.0,

    # Settings
    "embedding_url": "http://localhost:1234/v1",
    "embedding_model": "auto",
    "llm_url": "http://localhost:1234/v1",
    "llm_model": "auto",
    "embedding_profile": "precision",
    "expand_queries": False,

    # --- New fields for UX ---

    # Current async operation: "idle"|"searching"|"indexing"|"scraping"|"deep_research"|"streaming"
    "operation": "idle",

    # Persistent error — stays until next action clears it
    "error": None,

    # Next-step guidance text for status bar
    "hint": "",

    # Research tab state
    "research_results": [],
    "research_sessions": [],
}


class ObservableState:
    """Application state that auto-emits events on field changes.

    Only fields listed in _STATE_FIELDS are observable. Private attributes
    (prefixed with ``_``) bypass observation entirely.
    """

    def __init__(self, event_bus=None):
        # Use object.__setattr__ to avoid triggering our __setattr__
        object.__setattr__(self, "_bus", event_bus)
        object.__setattr__(self, "_fields", set(_STATE_FIELDS.keys()))
        # Initialize all fields with defaults
        for name, default in _STATE_FIELDS.items():
            if isinstance(default, list):
                object.__setattr__(self, name, list(default))  # copy
            else:
                object.__setattr__(self, name, default)

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_") or name not in self._fields:
            object.__setattr__(self, name, value)
            return

        old = getattr(self, name, None)
        object.__setattr__(self, name, value)

        # Emit event if value changed (use != for simple types, always emit for lists)
        changed = isinstance(value, list) or old != value
        if changed and self._bus is not None:
            self._bus.emit(f"state:{name}", {
                "field": name,
                "old": old,
                "new": value,
            })

    def set_bus(self, event_bus):
        """Attach or replace the event bus (useful for late binding)."""
        object.__setattr__(self, "_bus", event_bus)

    def clear_error(self):
        """Convenience: clear error state."""
        self.error = None

    def set_operation(self, op: str, hint: str = ""):
        """Set operation and optionally update hint in one call."""
        self.error = None  # new operation clears any previous error
        self.operation = op
        if hint:
            self.hint = hint

"""Background indexing service for the GUI.

Wraps ProjectIndexer with threading, progress callbacks, and cancellation.
Emits events via the EventBus so GUI components stay decoupled.
"""

import threading
import time
from pathlib import Path
from typing import Optional

from ..events import EventBus


class IndexingService:
    """Manages background indexing operations."""

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._indexer = None
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, path: Path, force: bool = False):
        """Start indexing a folder in a background thread."""
        if self.is_running:
            return

        self.bus.emit("indexing:started", {"path": str(path)})

        def _run():
            try:
                from mini_rag.indexer import ProjectIndexer

                indexer = ProjectIndexer(path)
                self._indexer = indexer

                indexer.set_progress_callback(
                    lambda done, total, chunks: self.bus.emit(
                        "indexing:progress",
                        {"done": done, "total": total, "chunks": chunks},
                    )
                )

                t0 = time.time()
                stats = indexer.index_project(force_reindex=force)
                stats["elapsed"] = time.time() - t0

                if stats.get("cancelled"):
                    self.bus.emit("indexing:cancelled", {"stats": stats})
                else:
                    self.bus.emit("indexing:completed", {"stats": stats, "path": str(path)})
            except Exception as e:
                self.bus.emit("indexing:error", {"error": str(e)})
            finally:
                self._indexer = None

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def cancel(self):
        """Cancel the running indexing operation."""
        if self._indexer:
            self._indexer.cancel_indexing()

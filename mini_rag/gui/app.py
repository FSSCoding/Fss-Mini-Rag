"""Main application window.

Wires together all components, services, and event handlers.
This is the only file that knows about all the pieces.
"""

import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .events import EventBus
from .config_store import load_config, save_config
from .components.search_bar import SearchBar
from .components.results_table import ResultsTable
from .components.content_panel import ContentPanel
from .components.collection_panel import CollectionPanel
from .components.status_bar import StatusBar
from .services.indexing import IndexingService
from .services.search import SearchService


class MiniRAGApp(tk.Tk):
    """FSS-Mini-RAG Desktop Application."""

    def __init__(self):
        super().__init__()

        self.title("FSS-Mini-RAG")
        self.config_data = load_config()
        self.geometry(self.config_data.get("geometry", "1100x700"))
        self.minsize(900, 550)

        # Core infrastructure
        self.bus = EventBus()
        self.indexing_service = IndexingService(self.bus)
        self.search_service = SearchService(self.bus)
        self._active_path = None
        self._last_results = []

        # Build UI
        self._create_menu()
        self._create_layout()
        self._bind_events()

        # Keyboard shortcuts
        self.bind("<Control-q>", lambda e: self._on_close())
        self.bind("<Control-w>", lambda e: self._on_close())

        # Poll for background events (thread-safe bridge)
        self._poll_interval = 100  # ms
        self._pending_events = []
        self._start_polling()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.search_bar.focus_entry()

    def _create_menu(self):
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add Folder", command=lambda: self.collections.listbox.event_generate("<<AddFolder>>"))
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._on_close, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Preferences...", command=self._open_preferences)
        menubar.add_cascade(label="Options", menu=options_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to Use", command=self._show_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _create_layout(self):
        """Build Option A layout: search+results left, collections right, content bottom."""

        # Main vertical split: top (search+collections) / bottom (content)
        main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Top section: horizontal split (search+results | collections)
        top_paned = ttk.PanedWindow(main_paned, orient=tk.HORIZONTAL)
        main_paned.add(top_paned, weight=1)

        # Left: search bar + results
        left_frame = ttk.Frame(top_paned)
        top_paned.add(left_frame, weight=3)

        self.search_bar = SearchBar(left_frame, self.bus)
        self.search_bar.pack(fill=tk.X, padx=2, pady=2)

        self.results_table = ResultsTable(left_frame, self.bus)
        self.results_table.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Right: collections
        self.collections = CollectionPanel(
            top_paned, self.bus,
            self.config_data.get("collections", []),
        )
        top_paned.add(self.collections, weight=1)

        # Bottom: content panel (full width)
        self.content_panel = ContentPanel(main_paned, self.bus)
        main_paned.add(self.content_panel, weight=2)

        # Status bar
        self.status_bar = StatusBar(self, self.bus)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def _bind_events(self):
        """Connect events to handlers."""
        self.bus.on("collection:selected", self._on_collection_selected)
        self.bus.on("collection:added", self._on_collection_added)
        self.bus.on("collection:deleted", self._on_collection_deleted)
        self.bus.on("collection:reindex", self._on_reindex)
        self.bus.on("indexing:cancel_requested", lambda d: self.indexing_service.cancel())

        self.bus.on("search:requested", self._on_search_requested)
        self.bus.on("search:completed", self._on_search_completed)
        self.bus.on("search:error", self._on_search_error)

        self.bus.on("synthesis:completed", self._on_synthesis_completed)

        self.bus.on("indexing:started", self._on_indexing_started)
        self.bus.on("indexing:progress", self._on_indexing_progress)
        self.bus.on("indexing:completed", self._on_indexing_completed)
        self.bus.on("indexing:cancelled", self._on_indexing_cancelled)
        self.bus.on("indexing:error", self._on_indexing_error)

        self.bus.on("settings:changed", self._on_settings_changed)

    # === Event Handlers ===

    def _on_collection_selected(self, data):
        self._active_path = data["path"]

    def _on_collection_added(self, data):
        self._save_collections()
        path = data["path"]
        if not (Path(path) / ".mini-rag").exists():
            self.indexing_service.start(Path(path))

    def _on_collection_deleted(self, data):
        self.search_service.invalidate(data["path"])
        self._save_collections()

    def _on_reindex(self, data):
        path = data["path"]
        self.search_service.invalidate(path)
        self.indexing_service.start(Path(path), force=True)

    def _on_search_requested(self, data):
        if not self._active_path:
            self.status_bar.set_text("Select a collection first")
            return

        if not (Path(self._active_path) / ".mini-rag").exists():
            self.status_bar.set_text("Collection not indexed. Click Index first.")
            return

        query = data["query"]
        mode = data["mode"]
        expand = data.get("expand", False)

        self.status_bar.set_text(f"Searching: {query}...")
        self.status_bar.show_progress()
        self.status_bar.set_progress(30)
        self.results_table.clear()
        self.content_panel.clear()

        # Run search in background thread
        def _run():
            self.search_service.search(self._active_path, query, top_k=20, expand=expand)

        threading.Thread(target=_run, daemon=True).start()
        self._pending_mode = mode
        self._pending_query = query

    def _on_search_completed(self, data):
        results = data["results"]
        timing = data["timing_ms"]
        query = data["query"]
        self._last_results = results

        self.after(0, lambda: self._display_search_results(results, query, timing))

        # Auto-trigger synthesis in Ask mode
        mode = getattr(self, "_pending_mode", "search")
        if mode == "ask" and results:
            self.after(100, lambda: self._start_synthesis(query, results))

    def _start_synthesis(self, query, results):
        self.status_bar.set_text(f"Generating answer with LLM...")
        self.status_bar.set_progress(60)
        self.content_panel.show_synthesis("Generating answer...")

        def _run():
            self.search_service.synthesize(self._active_path, query, results)

        threading.Thread(target=_run, daemon=True).start()

    def _display_search_results(self, results, query, timing):
        self.results_table.set_results(results)
        mode = getattr(self, "_pending_mode", "search")
        if mode != "ask":
            self.status_bar.hide_progress()
        self.status_bar.set_text(f"{len(results)} results for: {query} ({timing:.0f}ms)")

    def _on_search_error(self, data):
        self.after(0, lambda: self._show_search_error(data["error"]))

    def _show_search_error(self, error):
        self.status_bar.hide_progress()
        self.status_bar.set_text(f"Error: {error}")

    def _on_synthesis_completed(self, data):
        text = data["text"]
        timing = data["timing_ms"]
        self.after(0, lambda: self._display_synthesis(text, timing))

    def _display_synthesis(self, text, timing):
        self.content_panel.show_synthesis(f"LLM Synthesis ({timing:.0f}ms):\n\n{text}")
        self.status_bar.hide_progress()
        self.status_bar.set_text(f"Synthesis complete ({timing:.0f}ms)")

    def _on_indexing_started(self, data):
        self.after(0, lambda: self._update_indexing_ui(True, f"Indexing {Path(data['path']).name}..."))

    def _on_indexing_progress(self, data):
        done, total, chunks = data["done"], data["total"], data["chunks"]
        pct = (done / total * 100) if total > 0 else 0
        self.after(0, lambda: self._update_indexing_progress(done, total, chunks, pct))

    def _update_indexing_ui(self, active, text):
        self.collections.set_indexing(active)
        self.status_bar.set_text(text)
        if active:
            self.status_bar.show_progress()

    def _update_indexing_progress(self, done, total, chunks, pct):
        self.status_bar.set_progress(pct)
        self.status_bar.set_text(f"Indexing: {done}/{total} files | {chunks} chunks")

    def _on_indexing_completed(self, data):
        stats = data["stats"]
        self.after(0, lambda: self._finish_indexing(
            f"Indexed: {stats['files_indexed']} files, {stats['chunks_created']} chunks "
            f"in {stats.get('elapsed', stats.get('time_taken', 0)):.1f}s"
        ))
        self.search_service.invalidate(data.get("path"))

    def _on_indexing_cancelled(self, data):
        stats = data.get("stats", {})
        self.after(0, lambda: self._finish_indexing(
            f"Cancelled: {stats.get('files_indexed', 0)} files processed"
        ))

    def _on_indexing_error(self, data):
        self.after(0, lambda: self._finish_indexing(f"Indexing failed: {data['error']}"))

    def _finish_indexing(self, text):
        self.collections.set_indexing(False)
        self.status_bar.hide_progress()
        self.status_bar.set_text(text)

    def _on_settings_changed(self, data):
        self.config_data.update(data)
        save_config(self.config_data)
        self.status_bar.set_text("Settings saved")

    # === Dialogs ===

    def _open_preferences(self):
        from .dialogs.preferences import PreferencesDialog
        PreferencesDialog(self, self.config_data, self.bus)

    def _show_about(self):
        from .dialogs.about import AboutDialog
        AboutDialog(self)

    def _show_help(self):
        from tkinter import messagebox
        messagebox.showinfo(
            "How to Use",
            "1. Click '+ Add' to add a folder\n"
            "2. Wait for indexing to complete\n"
            "3. Type your query and press Enter\n\n"
            "Search mode: direct search results\n"
            "Ask mode: LLM synthesises an answer\n\n"
            "Use Options > Preferences to configure endpoints."
        )

    # === Lifecycle ===

    def _save_collections(self):
        self.config_data["collections"] = self.collections.get_collections()
        save_config(self.config_data)

    def _start_polling(self):
        """Poll for thread-safe event delivery."""
        # Events from background threads are already handled via self.after()
        # This polling is a safety net
        self.after(self._poll_interval, self._start_polling)

    def _on_close(self):
        self.config_data["geometry"] = self.geometry()
        self.config_data["collections"] = self.collections.get_collections()
        save_config(self.config_data)
        self.destroy()

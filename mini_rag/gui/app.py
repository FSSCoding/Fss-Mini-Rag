"""Main application window.

Wires together all components, services, and event handlers.
This is the only file that knows about all the pieces.
"""

import logging
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .events import EventBus
from .state import ObservableState

logger = logging.getLogger(__name__)
from .config_store import load_config, save_config
from .components.search_bar import SearchBar
from .components.results_table import ResultsTable
from .components.content_panel import ContentPanel
from .components.collection_panel import CollectionPanel
from .components.status_bar import StatusBar
from .services.indexing import IndexingService
from .services.search import SearchService
from .services.streaming import StreamingService
from .services.research import ResearchService
from .components.research_tab import ResearchTab


class MiniRAGApp(tk.Tk):
    """FSS-Mini-RAG Desktop Application."""

    def __init__(self):
        super().__init__()

        self.title("FSS-Mini-RAG")
        self.config_data = load_config()
        self.geometry(self.config_data.get("geometry", "1100x700"))
        self.minsize(900, 550)

        # Apply Sun Valley theme (dark/light based on OS or config)
        try:
            import sv_ttk
            theme = self.config_data.get("theme", "dark")
            sv_ttk.set_theme(theme)
        except ImportError:
            pass  # Fall back to system theme

        # Apply custom style overrides
        from .theme import apply_custom_styles
        apply_custom_styles(self)

        # Core infrastructure
        self.bus = EventBus()
        self.state = ObservableState(self.bus)
        self.indexing_service = IndexingService(self.bus)
        self.search_service = SearchService(self.bus)
        self.streaming_service = StreamingService(self.bus)
        self.research_service = ResearchService(self.bus)
        self._indexing_start_time = None

        # Cost tracking
        from .cost_tracker import CostTracker
        self.cost_tracker = CostTracker(self.bus)
        self.cost_tracker.cost_per_1m_input = self.config_data.get("cost_per_1m_input", 0.0)
        self.cost_tracker.cost_per_1m_output = self.config_data.get("cost_per_1m_output", 0.0)
        self.bus.on("cost:reset", lambda d: self.cost_tracker.reset())

        # Apply saved settings to services
        self.search_service.llm_url = self.config_data.get("llm_url", "http://localhost:1234/v1")
        self.search_service.llm_model = self.config_data.get("llm_model", "auto")
        self.search_service.embedding_url = self.config_data.get("embedding_url", "http://localhost:1234/v1")
        self.research_service.llm_url = self.config_data.get("llm_url", "http://localhost:1234/v1")
        self.research_service.llm_model = self.config_data.get("llm_model", "auto")
        logger.info(f"GUI started: LLM={self.search_service.llm_url} Embedding={self.search_service.embedding_url}")

        # Build UI
        self._create_menu()
        self._create_layout()
        self._bind_events()

        # Keyboard shortcuts
        self.bind("<Control-q>", lambda _: self._on_close())
        self.bind("<Control-w>", lambda _: self._on_close())
        self.bind("<Control-f>", lambda _: self.search_bar.focus_entry())
        self.bind("<Control-n>", lambda _: self.collections._on_add())
        self.bind("<Escape>", lambda _: self._on_escape())
        self.bind("<F1>", lambda _: self._show_help())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._set_initial_sash_positions)
        self.search_bar.focus_entry()

        # Welcome dialog on first launch
        if not self.config_data.get("welcome_shown"):
            self.after(500, self._show_welcome)

        # Initial hint
        if not self.config_data.get("collections"):
            self.state.hint = "Get started: click + Add to index a folder, or try Web Research"

        # Load research sessions on startup
        self.after(300, self._refresh_research_sessions)

    def _create_menu(self):
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add Folder", command=lambda: self.collections._on_add(), accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._on_close, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Preferences...", command=self._open_preferences)
        options_menu.add_separator()
        options_menu.add_command(label="Toggle Dark/Light", command=self._toggle_theme)
        menubar.add_cascade(label="Options", menu=options_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to Use", command=self._show_help, accelerator="F1")
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _create_layout(self):
        """Build tabbed layout: Search & Index tab + Web Research tab."""

        # Top bar: working directory display
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, padx=8, pady=(4, 0))

        self._workdir_var = tk.StringVar()
        self._update_workdir_display()
        workdir_label = ttk.Label(
            top_bar, textvariable=self._workdir_var,
            foreground="#888888", font=("", 8), anchor=tk.E,
            cursor="hand2",
        )
        workdir_label.pack(side=tk.RIGHT)
        workdir_label.bind("<Button-1>", lambda e: self._change_working_dir())

        ttk.Label(top_bar, text="Working Dir:", foreground="#666666", font=("", 8)).pack(side=tk.RIGHT, padx=(0, 4))

        # Notebook wraps everything except status bar
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 2))

        # === Tab 1: Search & Index (existing layout) ===
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Search & Index")

        self.main_paned = ttk.PanedWindow(search_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # Top section: horizontal split (search+results | collections)
        self.top_paned = ttk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL)
        self.main_paned.add(self.top_paned, weight=1)

        # Left: search bar + results
        left_frame = ttk.Frame(self.top_paned)
        self.top_paned.add(left_frame, weight=3)

        self.search_bar = SearchBar(left_frame, self.bus)
        self.search_bar.pack(fill=tk.X, padx=4, pady=4)

        self.results_table = ResultsTable(left_frame, self.bus)
        self.results_table.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # Right: collections
        self.collections = CollectionPanel(
            self.top_paned, self.bus,
            self.config_data.get("collections", []),
        )
        self.top_paned.add(self.collections, weight=1)

        # Bottom: content panel (full width)
        self.content_panel = ContentPanel(self.main_paned, self.bus)
        self.main_paned.add(self.content_panel, weight=2)

        # === Tab 2: Web Research ===
        self.research_tab = ResearchTab(self.notebook, self.bus, self.config_data)
        self.notebook.add(self.research_tab, text="Web Research")

        # Loading overlay (compact panel, floats over notebook)
        from .components.loading_overlay import LoadingOverlay
        self.loading_overlay = LoadingOverlay(self)

        # Status bar (shared, outside notebook)
        self.status_bar = StatusBar(self, self.bus)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def _bind_events(self):
        """Connect events to handlers."""
        self.bus.on("collection:selected", self._on_collection_selected)
        self.bus.on("collection:added", self._on_collection_added)
        self.bus.on("collection:deleted", self._on_collection_deleted)
        self.bus.on("collection:reindex", self._on_reindex)
        self.bus.on("indexing:cancel_requested", lambda d: self.indexing_service.cancel())
        self.bus.on("search:cancel_requested", lambda d: self.after(0, lambda: self.state.set_operation("idle", "Search cancelled")))
        self.bus.on("stream:cancel_requested", lambda d: self.streaming_service.cancel())

        self.bus.on("search:requested", self._on_search_requested)
        self.bus.on("search:completed", self._on_search_completed)
        self.bus.on("search:error", self._on_search_error)

        self.bus.on("synthesis:completed", self._on_synthesis_completed)

        self.bus.on("stream:started", lambda d: self.after(0, lambda: self.content_panel.renderer.begin_stream()))
        self.bus.on("stream:token", self._on_stream_token)
        self.bus.on("stream:complete", self._on_stream_complete)
        self.bus.on("stream:error", lambda d: self.after(0, lambda: self._show_search_error(f"Streaming: {d['error']}")))
        self.bus.on("stream:cancelled", lambda d: self.after(0, lambda: (
            self.state.set_operation("idle", "Synthesis cancelled"),
        )))
        self.bus.on("stream:thinking_start", lambda d: self.after(0, lambda: self.content_panel.renderer.set_stream_thinking(True)))
        self.bus.on("stream:thinking_end", lambda d: self.after(0, lambda: self.content_panel.renderer.set_stream_thinking(False)))

        self.bus.on("indexing:started", self._on_indexing_started)
        self.bus.on("indexing:progress", self._on_indexing_progress)
        self.bus.on("indexing:completed", self._on_indexing_completed)
        self.bus.on("indexing:cancelled", self._on_indexing_cancelled)
        self.bus.on("indexing:error", self._on_indexing_error)

        self.bus.on("settings:changed", self._on_settings_changed)

        # Research tab events
        self.bus.on("research:search_requested", self._on_research_search)
        self.bus.on("research:scrape_requested", self._on_research_scrape)
        self.bus.on("research:scrape_single", self._on_research_scrape_single)
        self.bus.on("research:deep_requested", self._on_research_deep)
        self.bus.on("research:index_session", self._on_research_index)
        self.bus.on("research:delete_session", self._on_research_delete)
        self.bus.on("research:refresh_sessions", lambda d: self._refresh_research_sessions())
        self.bus.on("research:cancel_requested", lambda d: self.research_service.cancel())
        self.bus.on("research:scrape_progress", self._on_research_scrape_progress)
        self.bus.on("research:deep_progress", self._on_research_deep_progress)
        self.bus.on("research:search_completed", self._on_research_search_completed)
        self.bus.on("research:scrape_completed", self._on_research_scrape_completed)
        self.bus.on("research:deep_completed", self._on_research_deep_completed)
        self.bus.on("research:error", self._on_research_error)

        # Tab switch requests (from research tab "Go to Search" button)
        self.bus.on("ui:switch_tab", lambda d: self.after(0, lambda: self.notebook.select(d.get("tab", 0))))

        # State-driven UI updates
        self.bus.on("state:operation", lambda d: self.after(0, lambda: self._on_operation_changed(d)))

    # === State-Driven UI ===

    def _on_operation_changed(self, data):
        """React to operation state changes — busy cursor, tab indicators, loading overlay."""
        op = data.get("new", "idle")

        # Busy cursor
        if op != "idle":
            self.configure(cursor="watch")
            self.loading_overlay.show(op)
        else:
            self.configure(cursor="")
            self.loading_overlay.hide()

        # Tab activity indicators
        search_ops = {"searching", "indexing", "streaming"}
        research_ops = {"scraping", "deep_research"}

        tab0_text = "Search & Index *" if op in search_ops else "Search & Index"
        tab1_text = "Web Research *" if op in research_ops else "Web Research"

        try:
            self.notebook.tab(0, text=tab0_text)
            self.notebook.tab(1, text=tab1_text)
        except tk.TclError:
            pass

    # === Event Handlers ===

    def _on_collection_selected(self, data):
        self.state.active_collection = data["path"]
        self.state.hint = "Type a query and press Enter to search"

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
        if not self.state.active_collection:
            self.state.set_operation("idle")
            self.state.hint = "Select a collection from the right panel to search"
            self.content_panel._empty.update_message("No collection selected")
            self.content_panel._empty.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.after(0, lambda: self.search_bar.set_searching(False))
            return

        if not (Path(self.state.active_collection) / ".mini-rag").exists():
            self.state.set_operation("idle")
            self.state.hint = "Click Index on the selected collection first"
            self.content_panel._empty.update_message("Collection not indexed yet")
            self.content_panel._empty.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.after(0, lambda: self.search_bar.set_searching(False))
            return

        query = data["query"]
        mode = data["mode"]
        expand = data.get("expand", False)

        self.state.set_operation("searching")
        self.results_table.clear()
        self.content_panel.clear()

        def _run():
            self.search_service.search(self.state.active_collection, query, top_k=20, expand=expand)

        threading.Thread(target=_run, daemon=True).start()
        self._pending_mode = mode
        self._pending_query = query

    def _on_search_completed(self, data):
        results = data["results"]
        timing = data["timing_ms"]
        query = data["query"]
        self.state.results = results

        self.after(0, lambda: self._display_search_results(results, query, timing))

        # Auto-trigger synthesis in Ask mode
        mode = getattr(self, "_pending_mode", "search")
        if mode == "ask" and results:
            self.after(100, lambda: self._start_synthesis(query, results))

    def _start_synthesis(self, query, results):
        self.state.set_operation("streaming")
        self.content_panel.renderer.show_placeholder("Generating answer...")

        self.streaming_service.start(
            llm_url=self.search_service.llm_url,
            llm_model=self.search_service.llm_model,
            query=query,
            results=results,
            project_path=self.state.active_collection,
        )

    def _display_search_results(self, results, query, timing):
        self.results_table.set_results(results)
        mode = getattr(self, "_pending_mode", "search")
        if mode != "ask":
            self.state.set_operation("idle", f"{len(results)} results for: {query} ({timing:.0f}ms)")
        else:
            self.status_bar.set_text(f"{len(results)} results for: {query} ({timing:.0f}ms)")

    def _on_search_error(self, data):
        self.after(0, lambda: self._show_search_error(data["error"]))

    def _show_search_error(self, error):
        self.state.set_operation("idle")
        self.state.error = f"Search error: {error}"
        self.search_bar.set_searching(False)

    def _on_synthesis_completed(self, data):
        text = data["text"]
        timing = data["timing_ms"]
        self.after(0, lambda: self._display_synthesis(text, timing))

    def _display_synthesis(self, text, timing):
        self.content_panel.show_synthesis(f"LLM Synthesis ({timing:.0f}ms):\n\n{text}")
        self.state.set_operation("idle", f"Synthesis complete ({timing:.0f}ms)")

    def _on_stream_token(self, data):
        text = data["text"]
        # Hide overlay once tokens start arriving so user sees the response
        self.after(0, lambda: (
            self.loading_overlay.hide(),
            self.content_panel.renderer.append_stream(text),
        ))

    def _on_stream_complete(self, data):
        timing = data["timing_ms"]
        def _finish():
            self.content_panel.renderer.end_stream()
            self.state.set_operation("idle", f"Synthesis complete ({timing:.0f}ms)")
        self.after(0, _finish)

    def _on_indexing_started(self, data):
        self._indexing_start_time = time.monotonic()
        self.after(0, lambda: (
            self.state.set_operation("indexing"),
            self._update_indexing_ui(True, f"Indexing {Path(data['path']).name}..."),
        ))

    def _on_indexing_progress(self, data):
        done, total, chunks = data["done"], data["total"], data["chunks"]
        pct = (done / total * 100) if total > 0 else 0
        elapsed = time.monotonic() - self._indexing_start_time if self._indexing_start_time else 0
        eta = ""
        if done > 0 and total > 0 and done < total:
            remaining = elapsed / done * (total - done)
            eta = f" | ~{remaining:.0f}s remaining"
        self.after(0, lambda: self._update_indexing_progress(done, total, chunks, pct, elapsed, eta))

    def _update_indexing_ui(self, active, text):
        self.collections.set_indexing(active)
        self.status_bar.set_text(text)
        if active:
            self.status_bar.show_progress()

    def _update_indexing_progress(self, done, total, chunks, pct, elapsed=0, eta=""):
        self.status_bar.set_progress(pct)
        detail = f"{done}/{total} files | {chunks} chunks | {elapsed:.0f}s{eta}"
        self.status_bar.set_text(f"Indexing: {detail}")
        self.loading_overlay.set_detail(detail)

    def _on_indexing_completed(self, data):
        stats = data["stats"]
        msg = (
            f"Indexed: {stats['files_indexed']} files, {stats['chunks_created']} chunks "
            f"in {stats.get('elapsed', stats.get('time_taken', 0)):.1f}s"
        )
        self.search_service.invalidate(data.get("path"))
        self.after(0, lambda: (
            self._finish_indexing(msg),
            self.state.set_operation("idle", "Search your collection with Ctrl+F"),
        ))

    def _on_indexing_cancelled(self, data):
        stats = data.get("stats", {})
        self.after(0, lambda: self._finish_indexing(
            f"Cancelled: {stats.get('files_indexed', 0)} files processed"
        ))
        self.state.set_operation("idle")

    def _on_indexing_error(self, data):
        error = data['error']
        def _show():
            self.collections.set_indexing(False)
            self.state.set_operation("idle")
            self.state.error = f"Indexing failed: {error}"
        self.after(0, _show)

    def _finish_indexing(self, text):
        self.collections.set_indexing(False)
        self.status_bar.hide_progress()
        self.status_bar.set_text(text)

    def _on_settings_changed(self, data):
        self.config_data.update(data)
        save_config(self.config_data)

        self.search_service.llm_url = data.get("llm_url", self.search_service.llm_url)
        self.search_service.llm_model = data.get("llm_model", self.search_service.llm_model)
        self.search_service.embedding_url = data.get("embedding_url", self.search_service.embedding_url)
        self.research_service.llm_url = self.search_service.llm_url
        self.research_service.llm_model = self.search_service.llm_model

        self.search_service.invalidate()
        self.status_bar.set_text(f"Settings saved (LLM: {self.search_service.llm_url})")

    # === Research Event Handlers ===

    def _get_working_dir(self) -> str:
        """Get the working directory for research data.

        Uses saved path from config, or the cross-platform default.
        Creates the directory if it doesn't exist.
        Never uses active_collection — working dir is independent.
        """
        from .config_store import get_default_working_dir
        path = self.config_data.get("working_dir")
        if not path:
            path = str(get_default_working_dir())
            self.config_data["working_dir"] = path
            save_config(self.config_data)
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    def _update_workdir_display(self):
        """Update the working directory label."""
        path = self.config_data.get("working_dir", "")
        if not path:
            from .config_store import get_default_working_dir
            path = str(get_default_working_dir())
        # Shorten for display: show last 2 components
        parts = Path(path).parts
        display = str(Path(*parts[-2:])) if len(parts) > 2 else path
        self._workdir_var.set(display)

    def _change_working_dir(self):
        """Let user change the working directory."""
        from tkinter import filedialog
        current = self.config_data.get("working_dir", "")
        new_dir = filedialog.askdirectory(
            title="Select working directory",
            initialdir=current or str(Path.home()),
        )
        if new_dir:
            self.config_data["working_dir"] = new_dir
            save_config(self.config_data)
            self._update_workdir_display()
            self.status_bar.set_text(f"Working directory: {new_dir}")

    def _on_research_search(self, data):
        self.state.set_operation("searching", "Searching the web...")
        self.research_service.web_search(
            data["query"], data.get("engine", "duckduckgo"),
            data.get("max_results", 10),
        )

    def _on_research_scrape(self, data):
        project_path = self._get_working_dir()
        if not project_path:
            self.state.error = "No project path selected"
            return
        self.state.set_operation("scraping", "Scraping web pages...")
        self.research_service.scrape_urls(
            data["urls"], project_path, data.get("query", "research"),
        )

    def _on_research_scrape_single(self, data):
        project_path = self._get_working_dir()
        if not project_path:
            return
        self.state.set_operation("scraping")
        self.research_service.scrape_single(data["url"], project_path)

    def _on_research_deep(self, data):
        project_path = self._get_working_dir()
        if not project_path:
            self.state.error = "No project path selected"
            return
        self.state.set_operation("deep_research", "Starting deep research...")
        self.research_service.deep_research(
            data["query"], data.get("engine", "duckduckgo"),
            project_path,
            data.get("max_time_min", 60), data.get("max_rounds", 5),
            disable_stall_detection=data.get("disable_stall_detection", False),
        )

    def _on_research_index(self, data):
        """Index a research session and auto-add to collections."""
        session_dir = data.get("session_dir", "")
        sources_dir = Path(session_dir) / "sources"
        if sources_dir.exists():
            # Auto-add to collections (Research → Search bridge)
            sources_str = str(sources_dir)
            if sources_str not in self.collections.get_collections():
                self.collections.add_collection(sources_str)
                self._save_collections()

            # Auto-select this collection so it's ready to search after indexing
            self.state.active_collection = sources_str

            self.indexing_service.start(sources_dir)
            self.state.set_operation("indexing", "Indexing research session...")
        else:
            self.state.error = "No sources directory in session"

    def _on_research_delete(self, data):
        import shutil
        session_dir = data.get("session_dir", "")
        if session_dir and Path(session_dir).exists():
            shutil.rmtree(session_dir)
            self.status_bar.set_text("Session deleted")
            self._refresh_research_sessions()

    def _on_research_search_completed(self, data):
        results = data.get("results", [])
        self.after(0, lambda: self.state.set_operation(
            "idle", f"Found {len(results)} web results — select and scrape to save"
        ))

    def _on_research_scrape_completed(self, data):
        pages = data.get("pages_scraped", 0)
        self.after(0, lambda: self.state.set_operation(
            "idle", f"Scraping complete: {pages} pages saved — click Index Session to make searchable"
        ))

    def _on_research_deep_completed(self, data):
        self.after(0, lambda: self.state.set_operation(
            "idle", f"Deep research complete — review report or Index Session"
        ))

    def _on_research_scrape_progress(self, data):
        done, total = data["done"], data["total"]
        url = data.get("current_url", "")[:50]
        pct = (done / total * 100) if total > 0 else 0
        def _update():
            self.status_bar.set_progress(pct)
            detail = f"{done}/{total} — {url}"
            self.status_bar.set_text(f"Scraping: {detail}")
            self.loading_overlay.set_detail(detail)
        self.after(0, _update)

    def _on_research_deep_progress(self, data):
        detail = data.get("detail", "")
        self.after(0, lambda: self.status_bar.set_text(f"Deep Research: {detail}"))

    def _on_research_error(self, data):
        def _show():
            self.state.set_operation("idle")
            self.state.error = f"Research error: {data['error']}"
        self.after(0, _show)

    def _refresh_research_sessions(self):
        project_path = self._get_working_dir()
        if project_path:
            sessions = self.research_service.load_sessions(project_path)
            self.after(0, lambda: self.research_tab.load_sessions(sessions))

    def _set_initial_sash_positions(self):
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            self.top_paned.sashpos(0, int(w * 0.7))
            self.main_paned.sashpos(0, int(h * 0.45))
        except (tk.TclError, ValueError):
            pass

    # === Theme & Keyboard ===

    def _toggle_theme(self):
        """Toggle between dark and light theme, updating all existing widgets."""
        try:
            import sv_ttk
            current = sv_ttk.get_theme()
            new_theme = "light" if current == "dark" else "dark"
            sv_ttk.set_theme(new_theme)
            self.config_data["theme"] = new_theme
            save_config(self.config_data)
            # Re-apply custom styles (sets option_add for new widgets)
            from .theme import apply_custom_styles, get_bg, get_bg_alt, get_accent_color
            apply_custom_styles(self)
            # Walk ALL existing tk widgets and update their colors
            self._apply_theme_to_existing_widgets()
        except ImportError:
            pass

    def _apply_theme_to_existing_widgets(self):
        """Force-update colors on all existing tk (non-ttk) widgets after theme switch."""
        from .theme import get_bg, get_bg_alt, _is_dark_theme
        from .theme import DARK_BG, DARK_FG, DARK_TREEVIEW_BG, DARK_ACCENT
        from .theme import LIGHT_BG, LIGHT_FG, LIGHT_TREEVIEW_BG, LIGHT_ACCENT

        is_dark = _is_dark_theme()
        bg = DARK_BG if is_dark else LIGHT_BG
        fg = DARK_FG if is_dark else LIGHT_FG
        tree_bg = DARK_TREEVIEW_BG if is_dark else LIGHT_TREEVIEW_BG
        accent = DARK_ACCENT if is_dark else LIGHT_ACCENT

        def _update_widget(w):
            cls = type(w).__name__
            try:
                if cls in ("Listbox", "Text"):
                    w.configure(bg=tree_bg, fg=fg)
                elif cls in ("Label", "Frame", "Canvas") and not isinstance(w, ttk.Widget):
                    w.configure(bg=bg)
                    if cls == "Label":
                        w.configure(fg=fg)
            except (tk.TclError, AttributeError):
                pass
            for child in w.winfo_children():
                _update_widget(child)

        _update_widget(self)

    def _on_escape(self):
        """Handle Escape key - cancel indexing if running, else clear search."""
        if self.state.operation != "idle":
            # Cancel whatever is running
            if self.state.operation == "indexing":
                self.indexing_service.cancel()
            elif self.state.operation in ("scraping", "deep_research"):
                self.research_service.cancel()
            elif self.state.operation == "streaming":
                self.streaming_service.cancel()
            self.state.set_operation("idle", "Cancelled")
        else:
            self.search_bar.search_var.set("")
            self.results_table.clear()
            self.content_panel.clear()
            self.state.hint = "Ready"

    # === Dialogs ===

    def _open_preferences(self):
        from .dialogs.preferences import PreferencesDialog
        PreferencesDialog(self, self.config_data, self.bus)

    def _show_about(self):
        from .dialogs.about import AboutDialog
        AboutDialog(self)

    def _show_welcome(self):
        """Show first-launch welcome dialog."""
        from .dialogs.welcome import WelcomeDialog
        WelcomeDialog(self, self.config_data)

    def _show_help(self):
        """Show help overlay."""
        from .dialogs.help_overlay import HelpOverlay
        HelpOverlay(self)

    # === Lifecycle ===

    def _save_collections(self):
        self.config_data["collections"] = self.collections.get_collections()
        save_config(self.config_data)

    def _on_close(self):
        self.config_data["geometry"] = self.geometry()
        self.config_data["collections"] = self.collections.get_collections()
        save_config(self.config_data)
        self.destroy()

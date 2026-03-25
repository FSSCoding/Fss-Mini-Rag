"""Web Research tab — search, scrape, and deep research UI.

Self-contained tab with toolbar, results/sessions list, and content viewer.
Emits events for the app to route to ResearchService.
"""

import os
import tkinter as tk
from tkinter import ttk, simpledialog
from pathlib import Path

from ..events import EventBus
from ..tooltip import ToolTip
from .rendered_markdown import RenderedMarkdown
from .empty_state import EmptyState


class ResearchTab(ttk.Frame):
    """Web Research tab containing search, scrape, and session management."""

    def __init__(self, parent, event_bus: EventBus, config: dict = None):
        super().__init__(parent)
        self.bus = event_bus
        self.config = config or {}
        self._search_results = []  # List of {title, url, snippet}
        self._progress_doc = []  # Accumulated markdown for live progress
        self._report_md = ""  # Final report markdown
        self._showing_progress = True  # Toggle state
        self._deep_session_dir = ""  # Session dir during deep research
        self._build()
        self._bind_events()

    def _build(self):
        # === Toolbar ===
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # Row 1: query + buttons
        row1 = ttk.Frame(toolbar)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(row1, textvariable=self.query_var)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.query_entry.bind("<Return>", lambda e: self._on_search())

        self.search_btn = ttk.Button(row1, text="Search", command=self._on_search)
        self.search_btn.pack(side=tk.LEFT, padx=2)

        self.scrape_url_btn = ttk.Button(row1, text="Scrape URL", command=self._on_scrape_url)
        self.scrape_url_btn.pack(side=tk.LEFT, padx=2)

        self.cancel_btn = ttk.Button(row1, text="Cancel", command=self._on_cancel,
                                     state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=2)

        # Row 2: engine, max pages, deep research toggle
        row2 = ttk.Frame(toolbar)
        row2.pack(fill=tk.X, pady=(3, 0))

        ttk.Label(row2, text="Engine:").pack(side=tk.LEFT, padx=(0, 3))
        self.engine_var = tk.StringVar(value=self.config.get("research_engine", "duckduckgo"))
        self.engine_combo = ttk.Combobox(row2, textvariable=self.engine_var,
                                         state="readonly", width=12)
        self.engine_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._refresh_engines()  # detect from env now
        # Also re-detect whenever the tab becomes visible
        self.bind("<Visibility>", lambda e: self._refresh_engines())

        ttk.Label(row2, text="Max pages:").pack(side=tk.LEFT, padx=(0, 3))
        self.max_pages_var = tk.IntVar(value=self.config.get("research_max_pages", 20))
        self.max_pages_spin = ttk.Spinbox(row2, from_=1, to=100,
                                          textvariable=self.max_pages_var, width=5)
        self.max_pages_spin.pack(side=tk.LEFT, padx=(0, 10))

        self.deep_var = tk.BooleanVar(value=False)
        self.deep_check = ttk.Checkbutton(row2, text="Deep Research",
                                          variable=self.deep_var,
                                          command=self._toggle_deep_options)
        self.deep_check.pack(side=tk.LEFT, padx=(0, 10))

        # Deep research options (hidden by default)
        self.deep_frame = ttk.Frame(row2)

        ttk.Label(self.deep_frame, text="Time:").pack(side=tk.LEFT, padx=(0, 3))
        self.time_var = tk.StringVar(value="30m")
        ttk.Entry(self.deep_frame, textvariable=self.time_var, width=6).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(self.deep_frame, text="Rounds:").pack(side=tk.LEFT, padx=(0, 3))
        self.rounds_var = tk.IntVar(value=5)
        ttk.Spinbox(self.deep_frame, from_=1, to=20,
                    textvariable=self.rounds_var, width=4).pack(side=tk.LEFT)

        self.no_stall_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.deep_frame, text="No stall-out",
                        variable=self.no_stall_var).pack(side=tk.LEFT, padx=(10, 0))

        # Tooltips
        ToolTip(self.search_btn, "Search the web or start deep research")
        ToolTip(self.scrape_url_btn, "Manually enter a URL to scrape")
        ToolTip(self.cancel_btn, "Cancel the current operation")
        ToolTip(self.engine_combo, "Search provider (auto-detected from API keys)")
        ToolTip(self.max_pages_spin, "Maximum pages to scrape per session")
        ToolTip(self.deep_check, "Run automated multi-round research with analysis")

        # === Inline progress bar (hidden by default) ===
        self.progress_frame = ttk.Frame(self)
        self.progress_label = ttk.Label(self.progress_frame, text="", foreground="#888888")
        self.progress_label.pack(side=tk.LEFT, padx=(5, 10))
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=300, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        # Don't pack progress_frame yet — shown during operations

        # === Main content: left/right split ===
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5)

        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel
        left = ttk.Frame(self.main_paned)
        self.main_paned.add(left, weight=1)

        # Search results section
        results_frame = ttk.LabelFrame(left, text="Search Results", padding=3)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        self._results_empty = EmptyState(
            results_frame, "No search results yet",
            "Enter a query and click Search", lambda: self.query_entry.focus_set(),
        )
        self._results_empty.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.results_tree = ttk.Treeview(
            results_frame, columns=("title", "url"), show="headings",
            selectmode="extended", height=8,
        )
        self.results_tree.heading("title", text="Title")
        self.results_tree.heading("url", text="URL")
        self.results_tree.column("title", width=250)
        self.results_tree.column("url", width=200)

        results_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL,
                                       command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scroll.set)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_tree.bind("<<TreeviewSelect>>", self._on_result_select)

        # Scrape buttons
        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=3)

        self.scrape_sel_btn = ttk.Button(btn_frame, text="Scrape Selected",
                                         command=self._on_scrape_selected)
        self.scrape_sel_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(self.scrape_sel_btn, "Download selected search results as source files")

        self.scrape_all_btn = ttk.Button(btn_frame, text="Scrape All",
                                         command=self._on_scrape_all)
        self.scrape_all_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(self.scrape_all_btn, "Download all search results as source files")

        # Sessions section
        sessions_frame = ttk.LabelFrame(left, text="Sessions", padding=3)
        sessions_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        self._sessions_empty = EmptyState(
            sessions_frame, "No research sessions",
            "Scrape web results to create sessions", None,
        )
        self._sessions_empty.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.sessions_tree = ttk.Treeview(
            sessions_frame, columns=("name", "pages", "status"),
            show="headings", height=5,
        )
        self.sessions_tree.heading("name", text="Session")
        self.sessions_tree.heading("pages", text="Pages")
        self.sessions_tree.heading("status", text="Status")
        self.sessions_tree.column("name", width=250)
        self.sessions_tree.column("pages", width=50, anchor=tk.CENTER)
        self.sessions_tree.column("status", width=70, anchor=tk.CENTER)

        self.sessions_tree.pack(fill=tk.BOTH, expand=True)
        self.sessions_tree.bind("<<TreeviewSelect>>", self._on_session_select)
        self.sessions_tree.bind("<Button-3>", self._on_session_right_click)

        self._session_menu = tk.Menu(self.sessions_tree, tearoff=0)
        self._session_menu.add_command(label="View Files", command=self._view_session_files)
        self._session_menu.add_command(label="Open Folder", command=self._open_session_folder)
        self._session_menu.add_separator()
        self._session_menu.add_command(label="Delete Session", command=self._on_delete_session)

        session_btn_frame = ttk.Frame(left)
        session_btn_frame.pack(fill=tk.X, pady=3)

        idx_btn = ttk.Button(session_btn_frame, text="Index Session",
                             command=self._on_index_session)
        idx_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(idx_btn, "Index session sources to make them searchable")

        del_btn = ttk.Button(session_btn_frame, text="Delete",
                             command=self._on_delete_session)
        del_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(del_btn, "Delete this research session and all its files")

        ref_btn = ttk.Button(session_btn_frame, text="Refresh",
                             command=self._on_refresh_sessions)
        ref_btn.pack(side=tk.LEFT, padx=2)
        ToolTip(ref_btn, "Reload sessions list from disk")

        self.goto_search_btn = ttk.Button(
            session_btn_frame, text="Go to Search",
            command=lambda: self.bus.emit("ui:switch_tab", {"tab": 0}),
            style="Accent.TButton",
        )
        # Hidden by default — shown after Index Session completes

        # Right panel: content viewer
        right = ttk.Frame(self.main_paned)
        self.main_paned.add(right, weight=2)

        # Toggle bar (hidden until deep research completes)
        self._toggle_frame = ttk.Frame(right)
        self._toggle_btn = ttk.Button(
            self._toggle_frame, text="Show Final Report",
            command=self._toggle_progress_report,
        )
        self._toggle_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        # Don't pack _toggle_frame yet — shown on completion

        content_lf = ttk.LabelFrame(right, text="Content", padding=3)
        content_lf.pack(fill=tk.BOTH, expand=True)

        self.content = RenderedMarkdown(content_lf)
        content_scroll = ttk.Scrollbar(content_lf, orient=tk.VERTICAL,
                                       command=self.content.yview)
        self.content.configure(yscrollcommand=content_scroll.set)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_events(self):
        self.bus.on("research:search_completed", self._on_search_completed)
        self.bus.on("research:page_scraped", self._on_page_scraped)
        self.bus.on("research:scrape_progress", self._on_scrape_progress)
        self.bus.on("research:scrape_completed", self._on_scrape_completed)
        self.bus.on("research:deep_started", self._on_deep_started)
        self.bus.on("research:deep_progress", self._on_deep_progress)
        self.bus.on("research:deep_completed", self._on_deep_completed)
        self.bus.on("research:error", self._on_error)
        self.bus.on("research:page_failed", self._on_page_failed)
        self._failed_urls = []  # Collects failures during a scrape run
        # Show "Go to Search" only after a research session is indexed
        def _maybe_show_goto(d):
            path = str(d.get("path", ""))
            if "web-research" in path or "sources" in path:
                self.after(0, lambda: self.goto_search_btn.pack(side=tk.RIGHT, padx=2))
        self.bus.on("indexing:completed", _maybe_show_goto)
        # State-driven button updates
        self.bus.on("state:operation", lambda d: self.after(0, lambda: self._on_operation(d)))

    # === Toolbar actions ===

    def _on_search(self):
        query = self.query_var.get().strip()
        if not query:
            return

        if self.deep_var.get():
            self._start_deep_research(query)
        else:
            self.bus.emit("research:search_requested", {
                "query": query,
                "engine": self.engine_var.get(),
                "max_results": 10,
            })
            self.search_btn.config(state=tk.DISABLED)

    def _start_deep_research(self, query):
        time_str = self.time_var.get().strip().lower()
        time_min = 60
        try:
            if time_str.endswith("h") and len(time_str) > 1:
                time_min = int(float(time_str[:-1]) * 60)
            elif time_str.endswith("m") and len(time_str) > 1:
                time_min = int(time_str[:-1])
            elif time_str.isdigit():
                time_min = int(time_str)
        except (ValueError, TypeError):
            time_min = 60

        self.bus.emit("research:deep_requested", {
            "query": query,
            "engine": self.engine_var.get(),
            "max_time_min": time_min,
            "max_rounds": self.rounds_var.get(),
            "disable_stall_detection": self.no_stall_var.get(),
        })
        self.search_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

    def _on_scrape_url(self):
        url = simpledialog.askstring("Scrape URL", "Enter URL to scrape:",
                                     parent=self)
        if url and url.strip():
            self.bus.emit("research:scrape_single", {"url": url.strip()})

    def _refresh_engines(self):
        """Re-detect available search engines from environment variables."""
        engines = ["duckduckgo"]
        if os.environ.get("TAVILY_API_KEY"):
            engines.append("tavily")
        if os.environ.get("SERPER_API_KEY"):
            engines.append("serper")
        if os.environ.get("BRAVE_API_KEY"):
            engines.append("brave")
        self.engine_combo["values"] = engines
        # Auto-select best available if current selection isn't valid
        current = self.engine_var.get()
        if current not in engines:
            if "tavily" in engines:
                self.engine_var.set("tavily")
            elif "serper" in engines:
                self.engine_var.set("serper")
            elif "brave" in engines:
                self.engine_var.set("brave")
            else:
                self.engine_var.set("duckduckgo")
        elif current == "duckduckgo" and "tavily" in engines:
            # Upgrade default if better engine became available
            self.engine_var.set("tavily")

    def _on_cancel(self):
        self.bus.emit("research:cancel_requested", {})
        self.cancel_btn.config(state=tk.DISABLED)

    def _toggle_deep_options(self):
        if self.deep_var.get():
            self.deep_frame.pack(side=tk.LEFT)
            self.search_btn.config(text="Start Research")
        else:
            self.deep_frame.pack_forget()
            self.search_btn.config(text="Search")

    # === Scrape actions ===

    def _on_scrape_selected(self):
        self._failed_urls.clear()
        selected = self.results_tree.selection()
        urls = []
        for item in selected:
            values = self.results_tree.item(item, "values")
            if len(values) >= 2:
                urls.append(values[1])  # URL column
        if urls:
            query = self.query_var.get().strip() or "research"
            self.bus.emit("research:scrape_requested", {
                "urls": urls, "query": query,
            })
            self.cancel_btn.config(state=tk.NORMAL)

    def _on_scrape_all(self):
        self._failed_urls.clear()
        urls = [r["url"] for r in self._search_results]
        if urls:
            query = self.query_var.get().strip() or "research"
            self.bus.emit("research:scrape_requested", {
                "urls": urls, "query": query,
            })
            self.cancel_btn.config(state=tk.NORMAL)

    # === Session actions ===

    def _get_selected_session_dir(self) -> str:
        """Get the session directory from the selected sessions tree item."""
        selected = self.sessions_tree.selection()
        if not selected:
            return ""
        item = self.sessions_tree.item(selected[0])
        return item.get("tags", [""])[0] if item.get("tags") else ""

    def _on_session_select(self, event):
        session_dir = self._get_selected_session_dir()
        if session_dir:
            self._show_session_content(session_dir)

    def _on_session_right_click(self, event):
        row = self.sessions_tree.identify_row(event.y)
        if row:
            self.sessions_tree.selection_set(row)
            self._session_menu.tk_popup(event.x_root, event.y_root)

    def _view_session_files(self):
        """Show individual files in the session with delete option."""
        session_dir = self._get_selected_session_dir()
        if not session_dir:
            return
        from pathlib import Path
        sources = Path(session_dir) / "sources"
        if not sources.exists():
            self.content.render("*No source files in this session.*")
            return

        files = sorted(f for f in sources.iterdir() if f.is_file() and f.suffix == ".md")
        if not files:
            self.content.render("*No source files in this session.*")
            return

        parts = [f"## Session Files ({len(files)})\n"]
        for f in files:
            size_kb = f.stat().st_size / 1024
            parts.append(f"- **{f.stem}** ({size_kb:.1f} KB)")
        parts.append(f"\n\n*Right-click a file in the session to manage it.*")
        self.content.render("\n".join(parts))

    def _open_session_folder(self):
        """Open the session directory in the file manager."""
        import subprocess, sys
        session_dir = self._get_selected_session_dir()
        if session_dir:
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", session_dir])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", session_dir])
            else:
                import os
                os.startfile(session_dir)

    def _on_index_session(self):
        session_dir = self._get_selected_session_dir()
        if session_dir:
            self.bus.emit("research:index_session", {"session_dir": session_dir})

    def _on_delete_session(self):
        session_dir = self._get_selected_session_dir()
        if not session_dir:
            return
        selected = self.sessions_tree.selection()
        if selected:
            from tkinter import messagebox
            name = self.sessions_tree.item(selected[0], "values")[0]
            if messagebox.askyesno("Delete Session", f"Delete session '{name}'?"):
                self.bus.emit("research:delete_session", {"session_dir": session_dir})

    def _on_refresh_sessions(self):
        self.bus.emit("research:refresh_sessions", {})

    def _on_result_select(self, event):
        selected = self.results_tree.selection()
        if not selected:
            return
        idx = self.results_tree.index(selected[0])
        if idx < len(self._search_results):
            result = self._search_results[idx]
            text = f"# {result['title']}\n\n{result['url']}\n\n{result['snippet']}"
            self.content.render(text)

    # === Event handlers (from service) ===

    def _on_search_completed(self, data):
        def _update():
            self.search_btn.config(state=tk.NORMAL)
            self._search_results = data.get("results", [])
            self.results_tree.delete(*self.results_tree.get_children())
            for r in self._search_results:
                self.results_tree.insert("", tk.END,
                                        values=(r["title"][:60], r["url"][:80]))
            # Hide empty state if we got results
            if self._search_results:
                self._results_empty.place_forget()
            else:
                self._results_empty.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.after(0, _update)

    def _on_page_scraped(self, data):
        def _update():
            self.content.render(
                f"# {data['title']}\n\n"
                f"**Source:** {data['url']}\n"
                f"**Words:** {data['word_count']}\n\n---\n\n"
                f"{data['content'][:2000]}"
            )
        self.after(0, _update)

    def _show_progress(self, text: str, value: float = 0):
        """Show inline progress bar with text."""
        if not self.progress_frame.winfo_ismapped():
            self.progress_frame.pack(fill=tk.X, padx=5, pady=(2, 0))
        self.progress_label.config(text=text)
        self.progress_bar["value"] = value

    def _hide_progress(self):
        """Hide inline progress bar."""
        self.progress_frame.pack_forget()

    def _on_scrape_progress(self, data):
        done, total = data["done"], data["total"]
        pct = (done / total * 100) if total > 0 else 0
        url = data.get("current_url", "")[:40]
        self.after(0, lambda: self._show_progress(f"Scraping {done}/{total}: {url}", pct))

    def _on_page_failed(self, data):
        """Collect failed URLs during scraping."""
        self._failed_urls.append(data)

    def _on_scrape_completed(self, data):
        def _update():
            self._hide_progress()
            self.cancel_btn.config(state=tk.DISABLED)
            pages = data.get("pages_scraped", 0)
            failed = self._failed_urls[:]
            self._failed_urls.clear()

            # Build completion message
            parts = [f"## Scraping Complete\n\n**{pages} pages saved.**"]

            if failed:
                parts.append(f"\n\n### Failed: {len(failed)} URLs\n")
                # Group by domain
                from urllib.parse import urlparse
                by_domain = {}
                for f in failed:
                    domain = urlparse(f["url"]).netloc
                    by_domain.setdefault(domain, []).append(f)

                for domain, items in sorted(by_domain.items()):
                    if len(items) > 3:
                        parts.append(f"- **{domain}** ({len(items)} failures)")
                    else:
                        for item in items:
                            short_url = item["url"][:60]
                            err = item.get("error", "unknown")[:80]
                            parts.append(f"- {short_url}\n  *{err}*")

            parts.append("\n\nClick **Index Session** to make this content searchable.")
            self.content.render("\n".join(parts))
            self._on_refresh_sessions()
        self.after(0, _update)

    def _on_deep_started(self, data):
        def _update():
            query = data.get("query", "")
            self._deep_session_dir = data.get("session_dir", "")
            self._progress_doc = [
                f"# Deep Research: {query}\n",
                "---\n",
            ]
            self._report_md = ""
            self._showing_progress = True
            self._toggle_frame.pack_forget()
            # Clear and prepare results tree for live source tracking
            self.results_tree.delete(*self.results_tree.get_children())
            self._results_empty.place_forget()
            self._search_results.clear()
            # Configure tag for failed items
            self.results_tree.tag_configure("failed", foreground="#888888")
            self.results_tree.tag_configure("success", foreground="")
            self._render_progress()
        self.after(0, _update)

    def _on_deep_progress(self, data):
        event_type = data.get("type", "")
        if not event_type:
            # Legacy fallback
            detail = data.get("detail", "")
            self.after(0, lambda: self._show_progress(f"Deep Research: {detail}", 50))
            return

        self.after(0, lambda: self._handle_progress_event(data))

    def _handle_progress_event(self, data):
        """Dispatch structured progress events to markdown builders."""
        t = data["type"]
        doc = self._progress_doc

        if t == "round_start":
            rn, tr = data["round_num"], data["total_rounds"]
            elapsed = data.get("elapsed_min", 0)
            remaining = data.get("remaining_min", 0)
            tokens = data.get("corpus_tokens", 0)
            files = data.get("corpus_files", 0)
            doc.append(f"\n## Round {rn} / {tr}\n")
            doc.append(
                f"| Metric | Value |\n|---|---|\n"
                f"| Elapsed | {elapsed:.1f} min |\n"
                f"| Remaining | {remaining:.1f} min |\n"
                f"| Corpus | {files} files, ~{tokens:,} tokens |\n\n"
            )
            pct = (rn / tr * 100) if tr else 50
            self._show_progress(f"Round {rn}/{tr}", pct)

        elif t == "phase_start":
            phase = data.get("phase", "")
            label = phase.upper()
            doc.append(f"### {label}\n")
            self._show_progress(f"Round — {label}", self.progress_bar["value"])

        elif t == "analyze_done":
            conf = data.get("confidence", "?")
            covered = data.get("covered_count", 0)
            gaps = data.get("gap_count", 0)
            gap_topics = data.get("gap_topics", [])
            queries = data.get("follow_up_queries", [])
            doc.append(f"**Confidence:** {conf}  |  **Covered:** {covered}  |  **Gaps:** {gaps}\n\n")
            if gap_topics:
                doc.append("Gaps: " + ", ".join(gap_topics[:6]))
                if len(gap_topics) > 6:
                    doc.append(f" (+{len(gap_topics) - 6} more)")
                doc.append("\n\n")
            if queries:
                doc.append("Queries:\n")
                for q in queries[:5]:
                    doc.append(f"- {q}\n")
                if len(queries) > 5:
                    doc.append(f"- *...and {len(queries) - 5} more*\n")
                doc.append("\n")

        elif t == "search_done":
            urls = data.get("urls_found", 0)
            skipped = data.get("skipped_domains", 0)
            doc.append(f"Found **{urls}** new URLs")
            if skipped:
                doc.append(f" (skipped {skipped} from failing domains)")
            doc.append("\n\n")

        elif t == "page_scraped":
            title = data.get("title", "?")
            words = data.get("word_count", 0)
            url = data.get("url", "")
            src = data.get("source_type", "")
            doc.append(f"- [{src}] **{title}** — {words:,} words\n")
            # Add to results tree
            display = f"[{src}] {title} ({words:,}w)"
            self.results_tree.insert("", tk.END, values=(display, url), tags=("success",))
            self.results_tree.yview_moveto(1.0)  # auto-scroll

        elif t == "page_failed":
            url = data.get("url", "")
            reason = data.get("reason", "failed")
            doc.append(f"- ~~{url[:60]}~~ *({reason})*\n")
            # Add to results tree in grey
            from urllib.parse import urlparse as _up
            short = _up(url).netloc + _up(url).path[:40]
            self.results_tree.insert("", tk.END, values=(f"FAILED: {short}", url), tags=("failed",))
            self.results_tree.yview_moveto(1.0)

        elif t == "scrape_done":
            scraped = data.get("pages_scraped", 0)
            attempted = data.get("pages_attempted", 0)
            doc.append(f"\nScraped **{scraped}/{attempted}** pages\n\n")

        elif t == "links_harvested":
            count = data.get("count", 0)
            doc.append(f"Harvested **{count}** new links for next round\n\n")

        elif t == "prune_done":
            removed = data.get("removed_count", 0)
            corr = data.get("corroborations_count", 0)
            parts = []
            if removed:
                parts.append(f"removed {removed} duplicates")
            if corr:
                parts.append(f"found {corr} corroborations")
            if parts:
                doc.append(f"Pruning: {', '.join(parts)}\n\n")
            else:
                doc.append("Pruning: no duplicates found\n\n")

        elif t == "briefing":
            text = data.get("briefing_text", "")
            if text:
                doc.append(f"> **Progress Briefing:** {text}\n\n")

        elif t == "round_end":
            rn = data.get("round_num", 0)
            dur = data.get("duration_min", 0)
            tok = data.get("tokens_added", 0)
            sc = data.get("scrape_successes", 0)
            sa = data.get("scrape_attempts", 0)
            llm = data.get("llm_calls", 0)
            doc.append(
                f"**Round {rn} complete:** {dur:.1f}min, "
                f"+{tok:,} tokens, {sc}/{sa} scraped, {llm} LLM calls\n\n"
                "---\n"
            )

        elif t == "stall_detected":
            override = data.get("override_active", False)
            if override:
                doc.append("**Stall detected** — override active, continuing\n\n")
            else:
                doc.append("**Stall detected** — triggering final roundup\n\n")

        elif t == "time_budget":
            remaining = data.get("remaining_min", 0)
            doc.append(f"**Time budget:** {remaining:.0f}min remaining — starting final roundup\n\n")

        elif t == "report_start":
            doc.append("\n## Generating Final Report...\n\n")
            self._show_progress("Generating report...", 95)

        elif t == "complete":
            conf = data.get("confidence", "?")
            rounds = data.get("total_rounds", 0)
            total_time = data.get("total_time", 0)
            doc.append(
                f"## Complete\n\n"
                f"**{rounds} rounds** in **{total_time:.1f} min** — "
                f"Confidence: **{conf}**\n"
            )

        self._render_progress()

    def _render_progress(self):
        """Re-render the accumulated progress document."""
        if self._showing_progress:
            self.content.render("".join(self._progress_doc))
            # Auto-scroll to bottom
            self.content.see(tk.END)

    def _toggle_progress_report(self):
        """Toggle between progress log and final report."""
        if self._showing_progress:
            self._showing_progress = False
            self._toggle_btn.config(text="Show Progress Log")
            if self._report_md:
                self.content.render(self._report_md)
        else:
            self._showing_progress = True
            self._toggle_btn.config(text="Show Final Report")
            self._render_progress()

    def _on_deep_completed(self, data):
        def _update():
            self._hide_progress()
            self.search_btn.config(state=tk.NORMAL, text="Search")
            self.cancel_btn.config(state=tk.DISABLED)
            self._report_md = data.get("report_md", "")

            # Show toggle button
            self._toggle_frame.pack(fill=tk.X, before=self.content.master)
            self._toggle_btn.config(text="Show Final Report")
            self._showing_progress = True  # Keep showing progress log initially

            # If no report, generate a basic one
            if not self._report_md:
                self._report_md = (
                    f"# Deep Research Complete\n\n"
                    f"**Rounds:** {data.get('rounds', 0)}\n"
                    f"**Time:** {data.get('time_minutes', 0):.1f} min\n"
                    f"**Pages:** {data.get('pages_scraped', 0)}\n"
                    f"**Confidence:** {data.get('confidence', 'unknown')}"
                )

            self._on_refresh_sessions()
        self.after(0, _update)

    def _on_operation(self, data):
        """React to state:operation changes for button text."""
        op = data.get("new", "idle")
        if op == "scraping":
            self.search_btn.config(state=tk.DISABLED, text="Scraping...")
            self.cancel_btn.config(state=tk.NORMAL)
        elif op == "deep_research":
            self.search_btn.config(state=tk.DISABLED, text="Researching...")
            self.cancel_btn.config(state=tk.NORMAL)
        elif op == "idle":
            is_deep = self.deep_var.get()
            self.search_btn.config(state=tk.NORMAL, text="Start Research" if is_deep else "Search")
            self.cancel_btn.config(state=tk.DISABLED)
            self._hide_progress()

    def _on_error(self, data):
        def _update():
            self._hide_progress()
            self.search_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
            self.content.render(f"**Error:** {data.get('error', 'Unknown error')}")
        self.after(0, _update)

    def _show_session_content(self, session_dir: str):
        """Load and display content from a session directory."""
        from pathlib import Path
        sources = Path(session_dir) / "sources"
        agent_notes = Path(session_dir) / "agent-notes"

        parts = []

        # Show research report if it exists
        report = agent_notes / "research-report.md"
        if report.exists():
            parts.append(report.read_text(encoding="utf-8", errors="replace"))
            parts.append("\n\n---\n\n")

        # List source files
        if sources.exists():
            files = sorted(f for f in sources.iterdir() if f.suffix == ".md")
            if files:
                parts.append(f"## Sources ({len(files)} files)\n\n")
                for f in files[:20]:
                    parts.append(f"- **{f.stem}**\n")

        if parts:
            self.content.render("".join(parts))
        else:
            self.content.render("*No content in this session.*")

    # === Public API ===

    def load_sessions(self, sessions: list):
        """Populate sessions tree from a list of session dicts."""
        self.sessions_tree.delete(*self.sessions_tree.get_children())
        for s in sessions:
            self.sessions_tree.insert(
                "", tk.END,
                values=(s["name"], s["pages"], s["status"]),
                tags=(s["dir"],),
            )
        if sessions:
            self._sessions_empty.place_forget()
        else:
            self._sessions_empty.place(relx=0, rely=0, relwidth=1, relheight=1)

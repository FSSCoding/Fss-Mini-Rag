"""Search bar component with mode toggle and cancel support."""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus


class SearchBar(ttk.Frame):
    """Search entry with Go button, Cancel button, and Search/Ask mode toggle."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent)
        self.bus = event_bus
        self._searching = False
        self._build()
        self.bus.on("search:completed", self._on_search_done)
        self.bus.on("search:error", lambda d: self.after(0, lambda: self._set_idle()))
        self.bus.on("synthesis:completed", lambda d: self.after(0, lambda: self._set_idle()))
        self.bus.on("stream:complete", lambda d: self.after(0, lambda: self._set_idle()))
        self.bus.on("stream:error", lambda d: self.after(0, lambda: self._set_idle()))
        self.bus.on("stream:cancelled", lambda d: self.after(0, lambda: self._set_idle()))
        # State-driven updates
        self.bus.on("state:operation", lambda d: self.after(0, lambda: self._on_operation(d)))

    def _build(self):
        # Top row: label + entry + buttons
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X)

        ttk.Label(mode_frame, text="Search:").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.entry = ttk.Entry(mode_frame, textvariable=self.search_var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry.bind("<Return>", lambda e: self._on_search())

        # Cancel button (hidden by default)
        self.cancel_btn = ttk.Button(
            mode_frame, text="Cancel", command=self._on_cancel, width=6
        )
        # Don't pack yet — shown during operations

        self.go_btn = ttk.Button(
            mode_frame, text="Go", command=self._on_search, width=6,
            style="Accent.TButton",
        )
        self.go_btn.pack(side=tk.RIGHT)

        # Mode radio row
        radio_frame = ttk.Frame(self)
        radio_frame.pack(fill=tk.X, pady=(2, 0))

        self.mode_var = tk.StringVar(value="search")
        ttk.Radiobutton(radio_frame, text="Search", variable=self.mode_var, value="search").pack(side=tk.LEFT)
        ttk.Radiobutton(radio_frame, text="Ask (LLM)", variable=self.mode_var, value="ask").pack(side=tk.LEFT, padx=5)

        self.expand_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(radio_frame, text="Expand query", variable=self.expand_var).pack(side=tk.RIGHT)

    def _on_search(self):
        if self._searching:
            return
        query = self.search_var.get().strip()
        if query:
            self._set_searching()
            self.bus.emit("search:requested", {
                "query": query,
                "mode": self.mode_var.get(),
                "expand": self.expand_var.get(),
            })

    def _on_cancel(self):
        """Cancel current operation."""
        self.bus.emit("search:cancel_requested", {})
        self.bus.emit("stream:cancel_requested", {})

    def _set_searching(self):
        self._searching = True
        self.go_btn.config(state="disabled", text="Searching...")
        self.entry.config(state="disabled")
        self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 2))

    def _set_idle(self):
        self._searching = False
        self.go_btn.config(state="normal", text="Go")
        self.entry.config(state="normal")
        self.cancel_btn.pack_forget()

    def _on_operation(self, data):
        """React to state:operation changes for button text."""
        op = data.get("new", "idle")
        if op == "searching":
            self._set_searching()
            self.go_btn.config(text="Searching...")
        elif op == "streaming":
            self.go_btn.config(text="Generating...")
            self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 2))
        elif op == "idle":
            self._set_idle()

    def set_searching(self, active: bool):
        """Legacy API for compatibility."""
        if active:
            self._set_searching()
        else:
            self._set_idle()

    def _on_search_done(self, data):
        # In "ask" mode, don't re-enable yet — wait for synthesis/stream
        if self.mode_var.get() != "ask":
            self.after(0, lambda: self._set_idle())

    def focus_entry(self):
        self.entry.focus_set()

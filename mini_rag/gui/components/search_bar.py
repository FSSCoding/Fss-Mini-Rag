"""Search bar component with mode toggle."""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus


class SearchBar(ttk.Frame):
    """Search entry with Go button and Search/Ask mode toggle."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent)
        self.bus = event_bus
        self._build()

    def _build(self):
        # Mode toggle
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X)

        ttk.Label(mode_frame, text="Search:").pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.entry = ttk.Entry(mode_frame, textvariable=self.search_var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry.bind("<Return>", lambda e: self._on_search())

        ttk.Button(mode_frame, text="Go", command=self._on_search, width=4).pack(side=tk.RIGHT)

        # Mode radio
        radio_frame = ttk.Frame(self)
        radio_frame.pack(fill=tk.X, pady=(2, 0))

        self.mode_var = tk.StringVar(value="search")
        ttk.Radiobutton(radio_frame, text="Search", variable=self.mode_var, value="search").pack(side=tk.LEFT)
        ttk.Radiobutton(radio_frame, text="Ask (LLM)", variable=self.mode_var, value="ask").pack(side=tk.LEFT, padx=5)

        self.expand_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(radio_frame, text="Expand query", variable=self.expand_var).pack(side=tk.RIGHT)

    def _on_search(self):
        query = self.search_var.get().strip()
        if query:
            self.bus.emit("search:requested", {
                "query": query,
                "mode": self.mode_var.get(),
                "expand": self.expand_var.get(),
            })

    def focus_entry(self):
        self.entry.focus_set()

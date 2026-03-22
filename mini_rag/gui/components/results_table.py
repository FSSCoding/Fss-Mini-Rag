"""Results table component."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from ..events import EventBus


def _score_label(score: float, max_score: float) -> str:
    """Plain text score label."""
    ref = max_score if max_score else score
    if ref < 0.1:
        thresholds = [(0.035, "HIGH"), (0.025, "GOOD"), (0.018, "FAIR"), (0.010, "LOW")]
    else:
        thresholds = [(0.7, "HIGH"), (0.5, "GOOD"), (0.3, "FAIR"), (0.1, "LOW")]
    for threshold, label in thresholds:
        if score >= threshold:
            return label
    return "WEAK"


class ResultsTable(ttk.Frame):
    """Treeview displaying search results with scores."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent)
        self.bus = event_bus
        self._results = []
        self._build()

    def _build(self):
        columns = ("score", "file", "type", "name")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("score", text="Score")
        self.tree.heading("file", text="File")
        self.tree.heading("type", text="Type")
        self.tree.heading("name", text="Name")

        self.tree.column("score", width=80, minwidth=60)
        self.tree.column("file", width=200, minwidth=80)
        self.tree.column("type", width=70, minwidth=50)
        self.tree.column("name", width=200, minwidth=80)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def set_results(self, results: list):
        """Display search results."""
        self.tree.delete(*self.tree.get_children())
        self._results = results

        if not results:
            return

        max_score = max(r.score for r in results)

        for i, result in enumerate(results):
            label = _score_label(result.score, max_score)
            file_name = Path(result.file_path).name
            name = (result.name or "-")[:50]

            if result.chunk_type == "image":
                file_name = f"[IMG] {file_name}"

            self.tree.insert("", tk.END, iid=str(i), values=(
                f"{result.score:.3f} {label}", file_name, result.chunk_type, name,
            ))

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0])
            if idx < len(self._results):
                self.bus.emit("result:selected", {
                    "index": idx,
                    "result": self._results[idx],
                })

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []

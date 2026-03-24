"""Results table component."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from ..events import EventBus
from ..tooltip import TreeviewToolTip
from .empty_state import EmptyState


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
        self._show_empty()

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
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        TreeviewToolTip(self.tree)

        self._context_menu = tk.Menu(self.tree, tearoff=0)
        self._context_menu.add_command(label="Open in Editor", command=self._ctx_open_editor)
        self._context_menu.add_command(label="Open Folder", command=self._ctx_open_folder)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Copy File Path", command=self._ctx_copy_path)

    def _show_empty(self):
        """Show empty state overlay."""
        if not hasattr(self, "_empty"):
            self._empty = EmptyState(
                self, "No search results yet",
                "Select a collection and search", None,
            )
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _hide_empty(self):
        if hasattr(self, "_empty"):
            self._empty.place_forget()

    def set_results(self, results: list):
        """Display search results."""
        self.tree.delete(*self.tree.get_children())
        self._results = results

        if not results:
            self._show_empty()
            return

        self._hide_empty()

        max_score = max(r.score for r in results)

        for i, result in enumerate(results):
            label = _score_label(result.score, max_score)
            file_name = Path(result.file_path).name
            name = result.name or "-"

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

    def _get_selected_result(self):
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0])
            if idx < len(self._results):
                return self._results[idx]
        return None

    def _on_double_click(self, event):
        result = self._get_selected_result()
        if result:
            self._open_in_editor(result)

    def _on_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self._context_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_open_editor(self):
        result = self._get_selected_result()
        if result:
            self._open_in_editor(result)

    def _ctx_open_folder(self):
        result = self._get_selected_result()
        if result:
            folder = str(Path(result.file_path).parent)
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                os.startfile(folder)

    def _ctx_copy_path(self):
        result = self._get_selected_result()
        if result:
            self.tree.clipboard_clear()
            self.tree.clipboard_append(result.file_path)

    def _open_in_editor(self, result):
        file_path = result.file_path
        line = getattr(result, "start_line", 1) or 1
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", file_path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        else:
            os.startfile(file_path)

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []
        self._show_empty()

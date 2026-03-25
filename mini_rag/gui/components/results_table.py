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
        self._collection_path = None
        self._build()
        self._show_empty()
        self.bus.on("state:active_collection", lambda d: self._set_collection(d.get("new")))

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

    def add_llm_response(self, timing_ms: float = 0):
        """Add an LLM Response row at the top of the results list."""
        if self.tree.exists("llm"):
            self.tree.delete("llm")
        timing_str = f"{timing_ms:.0f}ms" if timing_ms else ""
        self.tree.insert("", 0, iid="llm", values=(
            "LLM", "— response —", "synthesis", timing_str,
        ))
        self.tree.selection_set("llm")

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid == "llm":
                self.bus.emit("llm:response_selected", {})
                return
            try:
                idx = int(iid)
            except ValueError:
                return
            if idx < len(self._results):
                self.bus.emit("result:selected", {
                    "index": idx,
                    "result": self._results[idx],
                })

    def _get_selected_result(self):
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid == "llm":
                return None
            try:
                idx = int(iid)
            except ValueError:
                return None
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

    def _set_collection(self, path):
        self._collection_path = path

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a potentially relative file path against the active collection."""
        p = Path(file_path)
        if p.is_absolute() and p.exists():
            return str(p)
        if self._collection_path:
            resolved = Path(self._collection_path) / file_path
            if resolved.exists():
                return str(resolved)
        return file_path

    def _ctx_open_editor(self):
        result = self._get_selected_result()
        if result:
            self._open_in_editor(result)

    def _ctx_open_folder(self):
        result = self._get_selected_result()
        if result:
            resolved = self._resolve_path(result.file_path)
            folder = str(Path(resolved).parent)
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                os.startfile(folder)

    def _ctx_copy_path(self):
        result = self._get_selected_result()
        if result:
            resolved = self._resolve_path(result.file_path)
            self.tree.clipboard_clear()
            self.tree.clipboard_append(resolved)

    def _open_in_editor(self, result):
        resolved = self._resolve_path(result.file_path)
        line = getattr(result, "start_line", 1) or 1
        # Try code/text editors that support line numbers
        for editor_cmd in [
            ["code", "--goto", f"{resolved}:{line}"],
            ["subl", f"{resolved}:{line}"],
            ["gedit", f"+{line}", resolved],
        ]:
            if self._try_open(editor_cmd):
                return
        # Fallback to xdg-open
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", resolved])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", resolved])
        else:
            os.startfile(resolved)

    @staticmethod
    def _try_open(cmd: list) -> bool:
        """Try to run a command, return True if the executable exists."""
        import shutil
        if shutil.which(cmd[0]):
            subprocess.Popen(cmd)
            return True
        return False

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []
        self._show_empty()

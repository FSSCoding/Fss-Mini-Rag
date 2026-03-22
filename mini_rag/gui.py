"""
FSS-Mini-RAG Desktop GUI

Simple Tkinter interface for indexing folders and searching content.
Works on Windows and Linux with system native theme.

Usage:
    python -m mini_rag.gui
    rag-mini-gui
"""

import json
import logging
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "fss-mini-rag"
CONFIG_FILE = CONFIG_DIR / "gui.json"


def _load_config() -> Dict:
    """Load GUI config from disk."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"collections": [], "last_active": None, "geometry": "1000x650"}


def _save_config(config: Dict):
    """Save GUI config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _get_collection_info(path: Path) -> Optional[Dict]:
    """Get info about an indexed collection from its manifest."""
    manifest_path = path / ".mini-rag" / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        emb = manifest.get("embedding", {})
        return {
            "chunks": manifest.get("chunk_count", 0),
            "files": manifest.get("file_count", 0),
            "model": emb.get("model", "unknown"),
            "indexed_at": manifest.get("indexed_at", "never"),
        }
    except Exception:
        return None


def _score_label(score: float, max_score: float) -> str:
    """Plain text score label (no rich markup)."""
    ref = max_score if max_score else score
    if ref < 0.1:
        if score >= 0.035: return "HIGH"
        elif score >= 0.025: return "GOOD"
        elif score >= 0.018: return "FAIR"
        elif score >= 0.010: return "LOW"
        else: return "WEAK"
    else:
        if score >= 0.7: return "HIGH"
        elif score >= 0.5: return "GOOD"
        elif score >= 0.3: return "FAIR"
        elif score >= 0.1: return "LOW"
        else: return "WEAK"


class MiniRAGApp(tk.Tk):
    """FSS-Mini-RAG Desktop Application."""

    def __init__(self):
        super().__init__()

        self.title("FSS-Mini-RAG")
        self.config_data = _load_config()
        self.geometry(self.config_data.get("geometry", "1000x650"))
        self.minsize(800, 500)

        self.active_collection = None
        self.searcher = None
        self._indexing = False
        self._results = []

        self._create_ui()
        self._load_collections()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Build the main UI layout."""
        # Main paned window (left/right split)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === LEFT PANEL: Collections ===
        left_frame = ttk.LabelFrame(paned, text="Collections", padding=5)
        paned.add(left_frame, weight=1)

        # Collection list
        self.collection_list = tk.Listbox(left_frame, selectmode=tk.SINGLE)
        self.collection_list.pack(fill=tk.BOTH, expand=True)
        self.collection_list.bind("<<ListboxSelect>>", self._on_collection_select)

        # Collection buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="+ Add Folder", command=self._add_collection).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Reindex", command=self._reindex_collection).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Delete", command=self._delete_collection).pack(
            side=tk.LEFT, padx=2
        )

        # Collection info
        self.collection_info = ttk.Label(left_frame, text="No collection selected")
        self.collection_info.pack(fill=tk.X, pady=(5, 0))

        # === RIGHT PANEL: Search ===
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=3)

        # Search bar
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        ttk.Button(search_frame, text="Go", command=self._do_search).pack(side=tk.RIGHT)

        # Results treeview
        results_frame = ttk.Frame(right_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        columns = ("score", "file", "type", "name")
        self.results_tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", selectmode="browse"
        )
        self.results_tree.heading("score", text="Score")
        self.results_tree.heading("file", text="File")
        self.results_tree.heading("type", text="Type")
        self.results_tree.heading("name", text="Name")

        self.results_tree.column("score", width=80, minwidth=60)
        self.results_tree.column("file", width=250, minwidth=100)
        self.results_tree.column("type", width=80, minwidth=60)
        self.results_tree.column("name", width=250, minwidth=100)

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_tree.bind("<<TreeviewSelect>>", self._on_result_select)

        # Content detail panel
        detail_frame = ttk.LabelFrame(right_frame, text="Content", padding=5)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.detail_text = tk.Text(detail_frame, wrap=tk.WORD, height=10, font=("Courier", 10))
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)

        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # === STATUS BAR ===
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def _load_collections(self):
        """Load saved collections into the list."""
        self.collection_list.delete(0, tk.END)
        for path in self.config_data.get("collections", []):
            p = Path(path)
            has_index = (p / ".mini-rag").exists()
            label = f"{'[ok]' if has_index else '[--]'} {p.name}"
            self.collection_list.insert(tk.END, label)

        # Restore last active
        last = self.config_data.get("last_active")
        if last and last in self.config_data.get("collections", []):
            idx = self.config_data["collections"].index(last)
            self.collection_list.selection_set(idx)
            self._on_collection_select(None)

    def _get_selected_path(self) -> Optional[Path]:
        """Get the path of the currently selected collection."""
        sel = self.collection_list.curselection()
        if not sel:
            return None
        idx = sel[0]
        collections = self.config_data.get("collections", [])
        if idx < len(collections):
            return Path(collections[idx])
        return None

    def _on_collection_select(self, event):
        """Handle collection selection."""
        path = self._get_selected_path()
        if not path:
            return

        self.active_collection = path
        self.config_data["last_active"] = str(path)
        self.searcher = None  # Reset searcher for new collection

        info = _get_collection_info(path)
        if info:
            self.collection_info.config(
                text=f"{info['chunks']} chunks | {info['files']} files | {info['model']}"
            )
            self.status_var.set(f"Active: {path.name}")
        else:
            self.collection_info.config(text="Not indexed yet")
            self.status_var.set(f"Selected: {path.name} (not indexed)")

    def _add_collection(self):
        """Open folder picker and add/index a new collection."""
        folder = filedialog.askdirectory(title="Select folder to index")
        if not folder:
            return

        path = Path(folder)
        collections = self.config_data.get("collections", [])
        if str(path) not in collections:
            collections.append(str(path))
            self.config_data["collections"] = collections
            _save_config(self.config_data)

        self._load_collections()

        # Select the new collection
        idx = collections.index(str(path))
        self.collection_list.selection_clear(0, tk.END)
        self.collection_list.selection_set(idx)
        self._on_collection_select(None)

        # Index if not already indexed
        if not (path / ".mini-rag").exists():
            self._index_collection(path)

    def _index_collection(self, path: Path, force: bool = False):
        """Index a collection in a background thread."""
        if self._indexing:
            messagebox.showwarning("Busy", "Already indexing. Please wait.")
            return

        self._indexing = True
        self.status_var.set(f"Indexing {path.name}...")

        def _run():
            try:
                from .indexer import ProjectIndexer
                indexer = ProjectIndexer(path)
                stats = indexer.index_project(force_reindex=force)
                self.after(0, lambda: self._index_complete(path, stats))
            except Exception as e:
                self.after(0, lambda: self._index_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _index_complete(self, path: Path, stats: Dict):
        """Called when indexing finishes."""
        self._indexing = False
        self.status_var.set(
            f"Indexed {path.name}: {stats['files_indexed']} files, "
            f"{stats['chunks_created']} chunks in {stats['time_taken']:.1f}s"
        )
        self._load_collections()
        # Re-select
        collections = self.config_data.get("collections", [])
        if str(path) in collections:
            idx = collections.index(str(path))
            self.collection_list.selection_clear(0, tk.END)
            self.collection_list.selection_set(idx)
            self._on_collection_select(None)

    def _index_error(self, error: str):
        """Called when indexing fails."""
        self._indexing = False
        self.status_var.set(f"Indexing failed: {error}")
        messagebox.showerror("Indexing Error", error)

    def _reindex_collection(self):
        """Force reindex the selected collection."""
        path = self._get_selected_path()
        if not path:
            messagebox.showinfo("Select", "Select a collection first.")
            return
        self._index_collection(path, force=True)

    def _delete_collection(self):
        """Delete index for selected collection."""
        path = self._get_selected_path()
        if not path:
            return

        if not messagebox.askyesno(
            "Delete Collection",
            f"Remove index for {path.name}?\n\nThis deletes the .mini-rag/ directory.\nYour files are NOT deleted.",
        ):
            return

        rag_dir = path / ".mini-rag"
        if rag_dir.exists():
            shutil.rmtree(rag_dir)

        collections = self.config_data.get("collections", [])
        if str(path) in collections:
            collections.remove(str(path))
            self.config_data["collections"] = collections
            _save_config(self.config_data)

        self.active_collection = None
        self.searcher = None
        self._load_collections()
        self.status_var.set(f"Deleted index for {path.name}")

    def _do_search(self):
        """Execute search against active collection."""
        query = self.search_var.get().strip()
        if not query:
            return

        if not self.active_collection:
            messagebox.showinfo("Select", "Select a collection first.")
            return

        if not (self.active_collection / ".mini-rag").exists():
            messagebox.showinfo("Not Indexed", "This folder hasn't been indexed yet.\nClick 'Reindex' first.")
            return

        self.status_var.set(f"Searching: {query}")
        self.update_idletasks()

        try:
            if self.searcher is None:
                from .search import CodeSearcher
                self.searcher = CodeSearcher(self.active_collection)

            results = self.searcher.search(query, top_k=10)
            self._display_results(results, query)
        except Exception as e:
            self.status_var.set(f"Search error: {e}")
            logger.error(f"Search failed: {e}")

    def _display_results(self, results: List, query: str):
        """Display search results in the treeview."""
        # Clear previous
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self._results = results
        self.detail_text.delete("1.0", tk.END)

        if not results:
            self.status_var.set(f"No results for: {query}")
            return

        max_score = max(r.score for r in results)

        for i, result in enumerate(results):
            label = _score_label(result.score, max_score)
            file_name = Path(result.file_path).name
            name = (result.name or "-")[:50]

            if result.chunk_type == "image":
                file_name = f"[IMG] {file_name}"

            self.results_tree.insert(
                "", tk.END, iid=str(i),
                values=(f"{result.score:.3f} {label}", file_name, result.chunk_type, name),
            )

        self.status_var.set(f"{len(results)} results for: {query}")

    def _on_result_select(self, event):
        """Show content of selected result."""
        sel = self.results_tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        if idx < len(self._results):
            result = self._results[idx]
            self.detail_text.delete("1.0", tk.END)

            header = f"File: {result.file_path}\n"
            header += f"Type: {result.chunk_type} | Name: {result.name}\n"
            header += f"Lines: {result.start_line}-{result.end_line}\n"
            header += "-" * 60 + "\n\n"

            self.detail_text.insert("1.0", header + result.content)

    def _on_close(self):
        """Save config and close."""
        self.config_data["geometry"] = self.geometry()
        _save_config(self.config_data)
        self.destroy()


def main():
    """Launch the FSS-Mini-RAG GUI."""
    app = MiniRAGApp()
    app.mainloop()


if __name__ == "__main__":
    main()

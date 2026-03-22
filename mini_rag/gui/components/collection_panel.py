"""Collection manager panel (right side, compact)."""

import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from ..events import EventBus
from ..config_store import get_collection_info


class CollectionPanel(ttk.LabelFrame):
    """Compact collection list with add/index/delete buttons."""

    def __init__(self, parent, event_bus: EventBus, collections: list):
        super().__init__(parent, text="Collections", padding=5)
        self.bus = event_bus
        self._collections = list(collections)
        self._build()
        self._refresh_list()

    def _build(self):
        # Collection listbox
        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE, width=20)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="+ Add", command=self._on_add, width=6).pack(side=tk.LEFT, padx=1)
        self.index_btn = ttk.Button(btn_frame, text="Index", command=self._on_index, width=6)
        self.index_btn.pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="Delete", command=self._on_delete, width=6).pack(side=tk.LEFT, padx=1)

        # Info label
        self.info_label = ttk.Label(self, text="", wraplength=180)
        self.info_label.pack(fill=tk.X, pady=(5, 0))

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for path in self._collections:
            p = Path(path)
            info = get_collection_info(path)
            marker = "[ok]" if info.get("indexed") else "[--]"
            self.listbox.insert(tk.END, f"{marker} {p.name}")

    def _get_selected_path(self):
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self._collections):
            return self._collections[sel[0]]
        return None

    def _on_select(self, event):
        path = self._get_selected_path()
        if path:
            info = get_collection_info(path)
            if info.get("indexed"):
                self.info_label.config(
                    text=f"{info['chunks']} chunks | {info['files']} files\n{info['model']}"
                )
            else:
                self.info_label.config(text="Not indexed")
            self.bus.emit("collection:selected", {"path": path})

    def _on_add(self):
        folder = filedialog.askdirectory(title="Select folder to index")
        if not folder:
            return
        if folder not in self._collections:
            self._collections.append(folder)
            self.bus.emit("collection:added", {"path": folder})
        self._refresh_list()
        # Select the new one
        idx = self._collections.index(folder)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self._on_select(None)

    def _on_index(self):
        path = self._get_selected_path()
        if path:
            self.bus.emit("collection:reindex", {"path": path})

    def _on_delete(self):
        path = self._get_selected_path()
        if not path:
            return
        if not messagebox.askyesno(
            "Delete Collection",
            f"Remove index for {Path(path).name}?\n\nYour files are NOT deleted.",
        ):
            return
        rag_dir = Path(path) / ".mini-rag"
        if rag_dir.exists():
            shutil.rmtree(rag_dir)
        self._collections.remove(path)
        self.bus.emit("collection:deleted", {"path": path})
        self._refresh_list()
        self.info_label.config(text="")

    def set_indexing(self, active: bool):
        """Toggle index button text between Index/Stop."""
        if active:
            self.index_btn.config(text="Stop", command=lambda: self.bus.emit("indexing:cancel_requested", {}))
        else:
            self.index_btn.config(text="Index", command=self._on_index)
            self._refresh_list()

    def get_collections(self):
        return list(self._collections)

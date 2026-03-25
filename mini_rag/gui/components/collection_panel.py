"""Collection manager panel (right side, compact)."""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from ..events import EventBus
from ..config_store import get_collection_info, is_research_session
from ..tooltip import ToolTip
from .empty_state import EmptyState


class CollectionPanel(ttk.LabelFrame):
    """Compact collection list with add/index/delete buttons."""

    def __init__(self, parent, event_bus: EventBus, collections: list):
        super().__init__(parent, text="Collections", padding=5)
        self.bus = event_bus
        self._collections = list(collections)
        self._build()
        self._refresh_list()

    def _build(self):
        # Pack bottom elements FIRST so they're guaranteed space
        # Info label (bottom-most)
        self.info_label = ttk.Label(self, text="", wraplength=200, font=("", 8))
        self.info_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 0))

        # Buttons (above info)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        add_btn = ttk.Button(btn_frame, text="+ Add", command=self._on_add, width=6)
        add_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(add_btn, "Add a folder to index (Ctrl+N)")

        self.index_btn = ttk.Button(btn_frame, text="Index", command=self._on_index, width=6)
        self.index_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.index_btn, "Re-index selected collection")

        del_btn = ttk.Button(btn_frame, text="Delete", command=self._on_delete, width=6)
        del_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(del_btn, "Remove collection (files are not deleted)")

        # Collection listbox (fills remaining space)
        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE, width=20)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox_tooltip = ToolTip(self.listbox, delay=400)
        self.listbox.bind("<Motion>", self._on_listbox_motion, add="+")
        self.listbox.bind("<Button-3>", self._on_right_click)

        self._context_menu = tk.Menu(self.listbox, tearoff=0)
        self._context_menu.add_command(label="Open in File Manager", command=self._ctx_open_folder)
        self._context_menu.add_command(label="Copy Path", command=self._ctx_copy_path)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Re-index", command=self._on_index)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)

        if not self._collections:
            self._show_empty()
            return

        self._hide_empty()
        for path in self._collections:
            p = Path(path)
            info = get_collection_info(path)
            if is_research_session(path):
                marker = "[WEB]" if info.get("indexed") else "[web]"
                # Use session name not "sources"
                display = self._get_session_display_name(p)
            else:
                marker = "[ok]" if info.get("indexed") else "[--]"
                display = p.name
            self.listbox.insert(tk.END, f"{marker} {display}")

    @staticmethod
    def _get_session_display_name(p: Path) -> str:
        """Get a display name for a research session collection.
        If path is .../session-name/sources, show 'web: session-name'."""
        if p.name == "sources" and (p.parent / "session.json").exists():
            return f"web: {p.parent.name}"
        if (p / "session.json").exists():
            return f"web: {p.name}"
        return p.name

    def _show_empty(self):
        if not hasattr(self, "_empty"):
            self._empty = EmptyState(
                self, "No collections yet",
                "+ Add Folder", self._on_add,
            )
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=0.7)

    def _hide_empty(self):
        if hasattr(self, "_empty"):
            self._empty.place_forget()

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
                model = info['model']
                if len(model) > 25:
                    model = model[:22] + "..."
                self.info_label.config(
                    text=f"{info['chunks']} chunks | {info['files']} files | {model}"
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

    def _on_right_click(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self._collections):
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self._on_select(None)
            self._context_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_open_folder(self):
        path = self._get_selected_path()
        if path:
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                os.startfile(path)

    def _ctx_copy_path(self):
        path = self._get_selected_path()
        if path:
            self.listbox.clipboard_clear()
            self.listbox.clipboard_append(path)

    def _on_listbox_motion(self, event):
        idx = self.listbox.nearest(event.y)
        if 0 <= idx < len(self._collections):
            self._listbox_tooltip.update_text(self._collections[idx])
        else:
            self._listbox_tooltip.update_text("")

    def add_collection(self, path: str):
        """Add a collection programmatically (used by Research→Search bridge)."""
        if path not in self._collections:
            self._collections.append(path)
            self._refresh_list()

    def get_collections(self):
        return list(self._collections)

"""F1 help overlay with workflow diagrams and keyboard shortcuts."""

import tkinter as tk
from tkinter import ttk


class HelpOverlay(tk.Toplevel):
    """Help overlay showing workflows and keyboard shortcuts."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("FSS-Mini-RAG Help")
        self.geometry("550x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build()
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<F1>", lambda _: self.destroy())

    def _build(self):
        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Notebook for sections
        nb = ttk.Notebook(main)
        nb.pack(fill=tk.BOTH, expand=True)

        # --- Search Workflow ---
        search_frame = ttk.Frame(nb, padding=10)
        nb.add(search_frame, text="Search Workflow")

        workflow_text = (
            "Search & Index Workflow\n"
            "=======================\n\n"
            "  + Add Folder\n"
            "       |\n"
            "  Auto-Index (or click Index)\n"
            "       |\n"
            "  Type query + Enter\n"
            "       |\n"
            "  Browse results (click to view)\n"
            "       |\n"
            "  [Optional] Switch to Ask mode\n"
            "  for LLM-synthesised answers\n"
        )
        text_widget = tk.Text(search_frame, font=("Courier", 10), wrap=tk.WORD, height=14)
        text_widget.insert("1.0", workflow_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

        # --- Research Workflow ---
        research_frame = ttk.Frame(nb, padding=10)
        nb.add(research_frame, text="Research Workflow")

        research_text = (
            "Web Research Workflow\n"
            "=====================\n\n"
            "  Enter query + Search\n"
            "       |\n"
            "  Select results + Scrape\n"
            "       |\n"
            "  Pages saved to session\n"
            "       |\n"
            "  Index Session\n"
            "  (auto-adds to Collections)\n"
            "       |\n"
            "  Switch to Search tab\n"
            "  to query indexed content\n"
            "\n"
            "  [Deep Research]\n"
            "  Automated multi-round search,\n"
            "  scrape, and analysis loop\n"
        )
        text2 = tk.Text(research_frame, font=("Courier", 10), wrap=tk.WORD, height=14)
        text2.insert("1.0", research_text)
        text2.config(state=tk.DISABLED)
        text2.pack(fill=tk.BOTH, expand=True)

        # --- Keyboard Shortcuts ---
        shortcuts_frame = ttk.Frame(nb, padding=10)
        nb.add(shortcuts_frame, text="Shortcuts")

        shortcuts = [
            ("Ctrl+F", "Focus search bar"),
            ("Enter", "Execute search"),
            ("Ctrl+N", "Add new collection"),
            ("Escape", "Cancel operation / clear search"),
            ("F1", "Toggle this help overlay"),
            ("Ctrl+Q", "Quit application"),
            ("Double-click result", "Open file in editor"),
            ("Right-click result", "Context menu (open, copy)"),
        ]

        for key, desc in shortcuts:
            row = ttk.Frame(shortcuts_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=key, font=("Courier", 10, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row, text=desc).pack(side=tk.LEFT)

        # Close button
        ttk.Button(main, text="Close", command=self.destroy).pack(pady=(10, 0))

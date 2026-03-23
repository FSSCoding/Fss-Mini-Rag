"""First-launch welcome dialog."""

import tkinter as tk
from tkinter import ttk

from ..config_store import save_config


class WelcomeDialog(tk.Toplevel):
    """One-time welcome dialog shown on first launch."""

    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data
        self.title("Welcome to FSS-Mini-RAG")
        self.geometry("500x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(
            main, text="Welcome to FSS-Mini-RAG",
            font=("", 16, "bold"),
        ).pack(pady=(0, 15))

        # Workflow steps
        steps = [
            ("1. Add & Index", "Click + Add to select a folder. It gets indexed automatically so you can search its contents."),
            ("2. Search & Ask", "Type a query and press Enter. Use 'Ask (LLM)' mode for AI-synthesised answers from your indexed content."),
            ("3. Web Research", "Switch to the Web Research tab to search the web, scrape pages, and run deep research sessions."),
        ]

        for title, desc in steps:
            step_frame = ttk.Frame(main)
            step_frame.pack(fill=tk.X, pady=4)
            ttk.Label(step_frame, text=title, font=("", 11, "bold")).pack(anchor=tk.W)
            ttk.Label(step_frame, text=desc, wraplength=440, foreground="#888888").pack(anchor=tk.W, padx=(10, 0))

        # Tip
        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(
            main, text="Press F1 anytime for help and keyboard shortcuts.",
            foreground="#888888", font=("", 9, "italic"),
        ).pack()

        # Close button
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(15, 0))
        ttk.Button(
            btn_frame, text="Get Started", command=self._on_close,
            style="Accent.TButton",
        ).pack()

    def _on_close(self):
        self.config_data["welcome_shown"] = True
        save_config(self.config_data)
        self.destroy()

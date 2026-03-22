"""About dialog."""

import tkinter as tk
from tkinter import ttk


class AboutDialog(tk.Toplevel):
    """Simple about box."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("About FSS-Mini-RAG")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack()

        ttk.Label(frame, text="FSS-Mini-RAG", font=("", 14, "bold")).pack()
        ttk.Label(frame, text="Lightweight Semantic Code Search").pack(pady=5)
        ttk.Label(frame, text="Hybrid search: Semantic + BM25 with RRF Fusion").pack()
        ttk.Label(frame, text="").pack()
        ttk.Label(frame, text="Add folders. Index. Search or Ask.").pack()
        ttk.Label(frame, text="").pack()
        ttk.Label(frame, text="foxsoftwaresolutions.com.au").pack()

        ttk.Button(frame, text="OK", command=self.destroy).pack(pady=10)

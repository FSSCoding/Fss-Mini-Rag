"""About dialog."""

import tkinter as tk
import webbrowser
from tkinter import ttk

from mini_rag import __version__


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
        ttk.Label(frame, text=f"v{__version__}", font=("", 10)).pack()
        ttk.Label(frame, text="Lightweight Semantic Code Search").pack(pady=5)
        ttk.Label(frame, text="Hybrid search: Semantic + BM25 with RRF Fusion").pack()
        ttk.Label(frame, text="").pack()
        ttk.Label(frame, text="Add folders. Index. Search or Ask.").pack()
        ttk.Label(frame, text="").pack()

        link = ttk.Label(frame, text="foxsoftwaresolutions.com.au", foreground="dodgerblue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open("https://foxsoftwaresolutions.com.au"))

        repo_link = ttk.Label(frame, text="Gitea Repository", foreground="dodgerblue", cursor="hand2")
        repo_link.pack(pady=(2, 0))
        repo_link.bind("<Button-1>", lambda e: webbrowser.open("https://gitea.bobai.com.au/BobAi/Fss-Rag-Mini"))

        ttk.Button(frame, text="OK", command=self.destroy).pack(pady=10)

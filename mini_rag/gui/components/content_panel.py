"""Content panel for displaying chunk details."""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus


class ContentPanel(ttk.LabelFrame):
    """Text widget showing full content of selected search result."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent, text="Content", padding=5)
        self.bus = event_bus
        self._build()
        self.bus.on("result:selected", self._on_result_selected)

    def _build(self):
        self.text = tk.Text(self, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_result_selected(self, data):
        result = data.get("result")
        if not result:
            return

        self.text.delete("1.0", tk.END)

        header = f"File: {result.file_path}\n"
        header += f"Type: {result.chunk_type} | Name: {result.name}\n"
        header += f"Lines: {result.start_line}-{result.end_line}\n"
        header += "-" * 60 + "\n\n"

        self.text.insert("1.0", header + result.content)

    def show_synthesis(self, text: str):
        """Show LLM synthesis output."""
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)

    def clear(self):
        self.text.delete("1.0", tk.END)

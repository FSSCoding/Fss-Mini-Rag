"""Status bar with text and progress indicator."""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus


class StatusBar(ttk.Frame):
    """Bottom status bar with text + progress bar."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent)
        self.bus = event_bus
        self._flash_after_id = None

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.LEFT, expand=True)

        self.progress = ttk.Progressbar(self, length=200, mode="determinate")
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress.pack_forget()

    def set_text(self, text: str):
        self.status_var.set(text)
        self.status_label.config(foreground="")

    def set_error(self, text: str):
        self.status_var.set(text)
        self.status_label.config(foreground="red")
        self._flash(4)

    def _flash(self, count):
        if self._flash_after_id:
            self.after_cancel(self._flash_after_id)
        if count <= 0:
            return
        current = self.status_label.cget("foreground")
        self.status_label.config(foreground="" if current == "red" else "red")
        self._flash_after_id = self.after(300, lambda: self._flash(count - 1))

    def show_progress(self, value: float = 0):
        """Show progress bar (0-100)."""
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress["value"] = value

    def hide_progress(self):
        self.progress.pack_forget()

    def set_progress(self, value: float):
        self.progress["value"] = value

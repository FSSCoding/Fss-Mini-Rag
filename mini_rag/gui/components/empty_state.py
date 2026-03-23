"""Reusable empty-state widget with optional clickable action.

Shows a centered message with an optional blue underlined link
that triggers a callback. Used in every panel when there's no
content to display yet.

Usage:
    empty = EmptyState(parent, "No results yet", "Search now", on_search)
    empty.pack(fill="both", expand=True)
"""

import tkinter as tk
from tkinter import ttk


class EmptyState(ttk.Frame):
    """Centered placeholder with message and optional clickable action."""

    def __init__(
        self,
        parent,
        message: str,
        action_text: str = None,
        action_callback=None,
    ):
        super().__init__(parent)
        self._message = message
        self._action_text = action_text
        self._action_callback = action_callback
        self._build()

    def _build(self):
        # Center content vertically and horizontally
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = ttk.Frame(self)
        container.grid(row=0, column=0)

        # Message label (gray, slightly larger)
        msg_label = ttk.Label(
            container,
            text=self._message,
            foreground="#888888",
            font=("", 11),
            justify="center",
        )
        msg_label.pack(pady=(0, 4))

        # Action link (blue, underlined, clickable)
        if self._action_text and self._action_callback:
            action = tk.Label(
                container,
                text=self._action_text,
                fg="#4a9eff",
                cursor="hand2",
                font=("", 10, "underline"),
            )
            action.pack()
            action.bind("<Button-1>", lambda e: self._action_callback())

    def update_message(self, message: str):
        """Update the displayed message text."""
        self._message = message
        # Rebuild
        for child in self.winfo_children():
            child.destroy()
        self._build()

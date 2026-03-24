"""Status bar with text, progress indicator, and state subscriptions."""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus


class StatusBar(ttk.Frame):
    """Bottom status bar with text + progress bar.

    Subscribes to observable state for:
    - error: persistent red text until next action
    - hint: next-step guidance (italic gray)
    - operation: shows operation name while active
    """

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent)
        self.bus = event_bus
        self._flash_after_id = None
        self._is_error = False

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(8, 0))

        # Cost display (right side, before progress bar)
        self.cost_var = tk.StringVar(value="")
        self.cost_label = ttk.Label(self, textvariable=self.cost_var, anchor=tk.E, foreground="#888888")
        self.cost_label.pack(side=tk.RIGHT, padx=(5, 8))

        self.progress = ttk.Progressbar(self, length=200, mode="determinate")
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress.pack_forget()

        # Subscribe to state changes
        self.bus.on("state:error", lambda d: self.after(0, lambda: self._on_error(d)))
        self.bus.on("state:hint", lambda d: self.after(0, lambda: self._on_hint(d)))
        self.bus.on("state:operation", lambda d: self.after(0, lambda: self._on_operation(d)))
        self.bus.on("cost:updated", lambda d: self.after(0, lambda: self._on_cost(d)))

    def set_text(self, text: str):
        """Set normal status text. Clears any error state."""
        self._is_error = False
        if self._flash_after_id:
            self.after_cancel(self._flash_after_id)
            self._flash_after_id = None
        self.status_var.set(text)
        self.status_label.config(foreground="", font=("", 9))

    def set_error(self, text: str):
        """Set error text — persists until next set_text() call."""
        self._is_error = True
        self.status_var.set(text)
        self.status_label.config(foreground="red", font=("", 9))
        self._flash(4)

    def _flash(self, count):
        if self._flash_after_id:
            self.after_cancel(self._flash_after_id)
        if count <= 0:
            # End on red (persistent) instead of clearing
            self.status_label.config(foreground="red")
            return
        current = self.status_label.cget("foreground")
        self.status_label.config(foreground="" if current == "red" else "red")
        self._flash_after_id = self.after(300, lambda: self._flash(count - 1))

    def set_hint(self, text: str):
        """Show a hint (gray italic) — only if no error is active."""
        if self._is_error:
            return
        self.status_var.set(text)
        self.status_label.config(foreground="#888888", font=("", 9, "italic"))

    def show_progress(self, value: float = 0):
        """Show progress bar (0-100)."""
        self.progress.pack(side=tk.RIGHT, padx=(5, 8))
        self.progress["value"] = value

    def hide_progress(self):
        self.progress.pack_forget()

    def set_progress(self, value: float):
        self.progress["value"] = value

    # --- State subscribers ---

    def _on_error(self, data):
        error = data.get("new")
        if error:
            self.set_error(str(error))
        # Don't clear on None — set_text handles that

    def _on_hint(self, data):
        hint = data.get("new", "")
        if hint:
            self.set_hint(hint)

    def _on_cost(self, data):
        """Update cost display from cost:updated event."""
        cost = data.get("session_cost", 0.0)
        tok_in = data.get("session_tokens_in", 0)
        tok_out = data.get("session_tokens_out", 0)
        total_tok = tok_in + tok_out

        if cost > 0 or total_tok > 0:
            # Format tokens compactly
            if total_tok >= 1_000_000:
                tok_str = f"{total_tok / 1_000_000:.1f}M"
            elif total_tok >= 1_000:
                tok_str = f"{total_tok / 1_000:.1f}K"
            else:
                tok_str = str(total_tok)

            cost_str = f"${cost:.4f}" if cost < 1 else f"${cost:.2f}"
            self.cost_var.set(f"{cost_str} | {tok_str} tok")
        else:
            self.cost_var.set("")

    def _on_operation(self, data):
        op = data.get("new", "idle")
        if op == "idle":
            self.hide_progress()
        elif op == "searching":
            self.set_text("Searching...")
            self.show_progress(30)
        elif op == "indexing":
            self.set_text("Indexing...")
            self.show_progress(0)
        elif op == "scraping":
            self.set_text("Scraping...")
            self.show_progress(0)
        elif op == "deep_research":
            self.set_text("Deep research running...")
            self.show_progress(0)
        elif op == "streaming":
            self.set_text("Generating response...")

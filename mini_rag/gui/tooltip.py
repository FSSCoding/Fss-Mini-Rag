"""Tooltip widget for Tkinter."""

import tkinter as tk


class ToolTip:
    """Hover tooltip for any widget."""

    def __init__(self, widget, text="", delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", foreground="#000000",
            relief=tk.SOLID, borderwidth=1,
            font=("", 9),
            padx=4, pady=2,
        )
        label.pack()

    def _hide(self, event=None):
        self._cancel()
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None

    def update_text(self, text):
        self.text = text


class TreeviewToolTip:
    """Tooltip that shows full cell text on hover over a Treeview."""

    def __init__(self, treeview, delay=400):
        self.tree = treeview
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        treeview.bind("<Motion>", self._on_motion, add="+")
        treeview.bind("<Leave>", self._hide, add="+")

    def _on_motion(self, event):
        self._hide()
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or not col:
            return
        col_idx = int(col.replace("#", "")) - 1
        values = self.tree.item(row, "values")
        if col_idx < 0 or col_idx >= len(values):
            return
        text = str(values[col_idx])
        if len(text) < 30:
            return
        self._after_id = self.tree.after(
            self.delay,
            lambda: self._show(event.x_root + 15, event.y_root + 10, text),
        )

    def _show(self, x, y, text):
        if self._tip_window:
            return
        self._tip_window = tw = tk.Toplevel(self.tree)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=text, justify=tk.LEFT,
            background="#ffffe0", foreground="#000000",
            relief=tk.SOLID, borderwidth=1,
            font=("", 9),
            padx=4, pady=2,
            wraplength=500,
        )
        label.pack()

    def _hide(self, event=None):
        if self._after_id:
            self.tree.after_cancel(self._after_id)
            self._after_id = None
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None

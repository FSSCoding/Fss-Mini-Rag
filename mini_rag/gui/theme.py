"""Custom sv_ttk style overrides for visual polish.

Applied after sv_ttk.set_theme() to add:
- Accent styling for primary action buttons
- Padding adjustments for frames and tabs
- Visual depth via relief, spacing, and subtle color differences
"""

import tkinter as tk
from tkinter import ttk


def apply_custom_styles(root):
    """Apply custom style overrides on top of sv_ttk theme."""
    style = ttk.Style()

    # Detect current theme for color tuning
    is_dark = _is_dark_theme()

    # Accent buttons — primary actions (Go, Search, Index, +Add)
    style.configure(
        "Accent.TButton",
        font=("", 10, "bold"),
        padding=(12, 6),
    )

    # LabelFrame — padding + subtle visual separation
    style.configure("TLabelframe", padding=(10, 8))
    style.configure("TLabelframe.Label", font=("", 10, "bold"))

    # Notebook tab padding — more breathing room
    style.configure("TNotebook.Tab", padding=(14, 6))

    # Treeview row height — more readable
    style.configure("Treeview", rowheight=26)

    # Main window padding
    root.configure(padx=4, pady=4)

    # Status bar styling
    style.configure("Status.TLabel", padding=(8, 4))
    style.configure("Error.TLabel", foreground="#ff4444", padding=(8, 4))
    style.configure("Hint.TLabel", foreground="#888888", padding=(8, 4), font=("", 9, "italic"))

    # Depth: soften colors and add subtle border accents
    if is_dark:
        # Softer foreground — pure white is harsh
        style.configure("TLabel", foreground="#d4d4d4")
        style.configure("TLabelframe.Label", foreground="#a0c4ff")  # subtle blue accent for section headers
        # Treeview heading contrast
        style.configure("Treeview.Heading", font=("", 9, "bold"), foreground="#b0b0b0")
        # Subtle separator color
        style.configure("TSeparator", background="#404040")
        # LabelFrame border — slightly lighter than background for depth
        style.configure("TLabelframe", bordercolor="#3a3a3a", relief="groove")
    else:
        # Light mode: subtle accents
        style.configure("TLabel", foreground="#1a1a1a")
        style.configure("TLabelframe.Label", foreground="#2060a0")  # blue accent
        style.configure("Treeview.Heading", font=("", 9, "bold"), foreground="#333333")
        style.configure("TLabelframe", bordercolor="#c0c0c0", relief="groove")


def _is_dark_theme() -> bool:
    """Detect if current theme is dark."""
    try:
        import sv_ttk
        return sv_ttk.get_theme() == "dark"
    except ImportError:
        return False

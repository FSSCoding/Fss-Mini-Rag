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

    # Depth: soften harsh white-on-black in dark mode
    if is_dark:
        # Slightly softer foreground — pure white is harsh
        style.configure("TLabel", foreground="#d4d4d4")
        style.configure("TLabelframe.Label", foreground="#e0e0e0")
        # Treeview heading contrast
        style.configure("Treeview.Heading", font=("", 9, "bold"))
    else:
        # Light mode: slightly darker text for better readability
        style.configure("TLabel", foreground="#1a1a1a")
        style.configure("TLabelframe.Label", foreground="#111111")


def _is_dark_theme() -> bool:
    """Detect if current theme is dark."""
    try:
        import sv_ttk
        return sv_ttk.get_theme() == "dark"
    except ImportError:
        return False

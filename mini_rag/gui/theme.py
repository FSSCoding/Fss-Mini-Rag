"""Custom sv_ttk style overrides for visual polish.

Applied after sv_ttk.set_theme() to add:
- Softer background tones (not pure black/white)
- Accent colors: orange (dark mode), blue (light mode)
- Padding and depth adjustments
"""

import tkinter as tk
from tkinter import ttk

# Accent palette
DARK_ACCENT = "#e8913a"      # warm orange
DARK_ACCENT_SOFT = "#c47a30"  # muted orange for headers
DARK_BG = "#1e1e24"          # softer than pure black
DARK_FG = "#d0d0d0"          # softer than pure white
DARK_FG_DIM = "#909090"
DARK_BORDER = "#3a3a44"

LIGHT_ACCENT = "#2070b0"      # clean blue
LIGHT_ACCENT_SOFT = "#3080c0"
LIGHT_BG = "#f5f5f0"         # warm off-white, not pure white
LIGHT_FG = "#2a2a2a"         # softer than pure black
LIGHT_FG_DIM = "#606060"
LIGHT_BORDER = "#c8c8c0"


def apply_custom_styles(root):
    """Apply custom style overrides on top of sv_ttk theme."""
    style = ttk.Style()

    is_dark = _is_dark_theme()
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_soft = DARK_ACCENT_SOFT if is_dark else LIGHT_ACCENT_SOFT

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
    style.configure("Hint.TLabel", foreground=DARK_FG_DIM if is_dark else LIGHT_FG_DIM,
                    padding=(8, 4), font=("", 9, "italic"))

    if is_dark:
        # Softer foreground — warm dark mode, not harsh black/white
        style.configure("TLabel", foreground=DARK_FG)
        style.configure("TLabelframe.Label", foreground=DARK_ACCENT_SOFT)
        style.configure("Treeview.Heading", font=("", 9, "bold"), foreground="#a0a0a0")
        style.configure("TSeparator", background="#383840")
        style.configure("TLabelframe", bordercolor=DARK_BORDER, relief="groove")

        # Soften the root background
        try:
            root.configure(bg=DARK_BG)
        except tk.TclError:
            pass

    else:
        # Light mode: warm off-white with blue accents
        style.configure("TLabel", foreground=LIGHT_FG)
        style.configure("TLabelframe.Label", foreground=LIGHT_ACCENT)
        style.configure("Treeview.Heading", font=("", 9, "bold"), foreground="#404040")
        style.configure("TLabelframe", bordercolor=LIGHT_BORDER, relief="groove")

        try:
            root.configure(bg=LIGHT_BG)
        except tk.TclError:
            pass


def get_accent_color() -> str:
    """Get the current accent color for use by other components."""
    return DARK_ACCENT if _is_dark_theme() else LIGHT_ACCENT


def get_accent_soft() -> str:
    """Get the softer accent color for headers and labels."""
    return DARK_ACCENT_SOFT if _is_dark_theme() else LIGHT_ACCENT_SOFT


def _is_dark_theme() -> bool:
    """Detect if current theme is dark."""
    try:
        import sv_ttk
        return sv_ttk.get_theme() == "dark"
    except ImportError:
        return False

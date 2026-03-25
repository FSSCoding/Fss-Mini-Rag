"""Custom sv_ttk style overrides.

Applied after sv_ttk.set_theme() to soften colors and set accent palette.
Dark mode: warm charcoal + orange accents
Light mode: warm cream + blue accents
"""

import tkinter as tk
from tkinter import ttk

# ─── Dark mode palette ───
DARK_ACCENT = "#e8913a"        # warm orange — headings, links, actions
DARK_ACCENT_SOFT = "#c47a30"   # muted orange — secondary headings
DARK_BG = "#222228"            # warm charcoal (NOT pure black)
DARK_BG_ALT = "#2a2a30"       # slightly lighter for panels
DARK_FG = "#cccccc"            # soft grey text (NOT pure white)
DARK_FG_DIM = "#808080"
DARK_BORDER = "#3a3a44"
DARK_TREEVIEW_BG = "#26262c"

# ─── Light mode palette ───
LIGHT_ACCENT = "#2070b0"       # clean blue
LIGHT_ACCENT_SOFT = "#3080c0"
LIGHT_BG = "#f0ece4"           # warm cream (NOT pure white)
LIGHT_BG_ALT = "#e8e4dc"      # slightly darker cream for panels
LIGHT_FG = "#2a2a2a"          # soft dark (NOT pure black)
LIGHT_FG_DIM = "#606060"
LIGHT_BORDER = "#c8c0b4"
LIGHT_TREEVIEW_BG = "#ece8e0"


def apply_custom_styles(root):
    """Apply custom style overrides on top of sv_ttk theme."""
    style = ttk.Style()
    is_dark = _is_dark_theme()

    bg = DARK_BG if is_dark else LIGHT_BG
    bg_alt = DARK_BG_ALT if is_dark else LIGHT_BG_ALT
    fg = DARK_FG if is_dark else LIGHT_FG
    fg_dim = DARK_FG_DIM if is_dark else LIGHT_FG_DIM
    border = DARK_BORDER if is_dark else LIGHT_BORDER
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_soft = DARK_ACCENT_SOFT if is_dark else LIGHT_ACCENT_SOFT
    tree_bg = DARK_TREEVIEW_BG if is_dark else LIGHT_TREEVIEW_BG

    # ─── Override ALL widget backgrounds to softer tones ───
    style.configure(".", background=bg, foreground=fg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", foreground=fg, background=bg)
    style.configure("TLabelframe", background=bg, bordercolor=border, relief="groove", padding=(10, 8))
    style.configure("TLabelframe.Label", foreground=accent_soft, background=bg, font=("", 10, "bold"))
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", padding=(14, 6))
    style.configure("TPanedwindow", background=bg)
    style.configure("TSeparator", background=border)

    # Treeview — softer background
    style.configure("Treeview", background=tree_bg, fieldbackground=tree_bg,
                    foreground=fg, rowheight=26)
    style.configure("Treeview.Heading", font=("", 9, "bold"),
                    foreground=fg_dim, background=bg_alt)
    style.map("Treeview", background=[("selected", accent)])

    # Accent buttons
    style.configure("Accent.TButton", font=("", 10, "bold"), padding=(12, 6))

    # Status bar
    style.configure("Status.TLabel", padding=(8, 4), background=bg)
    style.configure("Error.TLabel", foreground="#ff4444", padding=(8, 4))
    style.configure("Hint.TLabel", foreground=fg_dim, padding=(8, 4), font=("", 9, "italic"))

    # Root window background
    try:
        root.configure(bg=bg, padx=4, pady=4)
    except tk.TclError:
        root.configure(padx=4, pady=4)

    # Force tk-level defaults with highest priority (*) for all widgets
    # This overrides sv_ttk's image-based theme for widget interiors
    root.option_add("*background", bg, "userDefault")
    root.option_add("*foreground", fg, "userDefault")
    root.option_add("*highlightBackground", bg, "userDefault")

    # Listbox
    root.option_add("*Listbox.background", tree_bg)
    root.option_add("*Listbox.foreground", fg)
    root.option_add("*Listbox.selectBackground", accent)
    root.option_add("*Listbox.selectForeground", "#ffffff")

    # Text widgets (rendered markdown content area)
    root.option_add("*Text.background", tree_bg)
    root.option_add("*Text.foreground", fg)

    # Entry fields
    root.option_add("*Entry.background", bg_alt)
    root.option_add("*Entry.foreground", fg)

    # Canvas
    root.option_add("*Canvas.background", bg)

    # Menu
    root.option_add("*Menu.background", bg_alt)
    root.option_add("*Menu.foreground", fg)
    root.option_add("*Menu.activeBackground", accent)
    root.option_add("*Menu.activeForeground", "#ffffff")

    # LabelFrame (tk native, not ttk)
    root.option_add("*Labelframe.background", bg)
    root.option_add("*Label.background", bg)


def get_accent_color() -> str:
    """Get the current accent color for use by other components."""
    return DARK_ACCENT if _is_dark_theme() else LIGHT_ACCENT


def get_accent_soft() -> str:
    """Get the softer accent color for headers and labels."""
    return DARK_ACCENT_SOFT if _is_dark_theme() else LIGHT_ACCENT_SOFT


def get_bg() -> str:
    """Get the current background color."""
    return DARK_BG if _is_dark_theme() else LIGHT_BG


def get_bg_alt() -> str:
    """Get the alternate background color for panels."""
    return DARK_BG_ALT if _is_dark_theme() else LIGHT_BG_ALT


def _is_dark_theme() -> bool:
    """Detect if current theme is dark."""
    try:
        import sv_ttk
        return sv_ttk.get_theme() == "dark"
    except ImportError:
        return False

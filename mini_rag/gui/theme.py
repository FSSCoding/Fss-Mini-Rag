"""Custom sv_ttk style overrides for visual polish.

Applied after sv_ttk.set_theme() to add:
- Accent styling for primary action buttons
- Padding adjustments for frames and tabs
- Subtle panel background differences
"""

from tkinter import ttk


def apply_custom_styles(root):
    """Apply custom style overrides on top of sv_ttk theme."""
    style = ttk.Style()

    # Accent buttons — primary actions (Go, Search, Index, +Add)
    # Use bold font to visually distinguish from secondary buttons
    style.configure(
        "Accent.TButton",
        font=("", 10, "bold"),
        padding=(12, 4),
    )

    # LabelFrame padding — prevent cramped layouts
    style.configure("TLabelframe", padding=(8, 6))
    style.configure("TLabelframe.Label", font=("", 10, "bold"))

    # Notebook tab padding — more breathing room
    style.configure("TNotebook.Tab", padding=(14, 6))

    # Treeview row height — slightly more readable
    style.configure("Treeview", rowheight=24)

    # Status bar styling
    style.configure("Status.TLabel", padding=(8, 4))
    style.configure("Error.TLabel", foreground="#ff4444", padding=(8, 4))
    style.configure("Hint.TLabel", foreground="#888888", padding=(8, 4), font=("", 9, "italic"))

"""Content panel - routes chunks to the correct renderer.

Auto-detects chunk type and file extension to decide between
code view (syntax highlighting) and rendered markdown (stripped syntax).
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from ..events import EventBus
from ..theme import (
    get_accent_color, get_accent_soft, get_bg_alt, _is_dark_theme,
    DARK_BG, DARK_FG, DARK_FG_DIM, DARK_BORDER,
    LIGHT_BG, LIGHT_FG, LIGHT_FG_DIM, LIGHT_BORDER,
)
from .rendered_markdown import RenderedMarkdown, prose_font
from .empty_state import EmptyState

# Chunk types that should use code view
_CODE_CHUNK_TYPES = {
    "function", "class", "method", "module_header", "module_code",
    "code_block", "config", "config_section",
}

# File extensions that should use code view (when chunk_type is ambiguous)
_CODE_EXTENSIONS = {
    "py", "js", "ts", "tsx", "jsx", "rs", "go", "java", "c", "cpp",
    "h", "hpp", "cs", "rb", "sh", "bash", "zsh", "yaml", "yml",
    "toml", "ini", "cfg", "conf",
}

# Human-friendly labels for chunk types
_CHUNK_TYPE_LABELS = {
    "function": "Function",
    "class": "Class",
    "method": "Method",
    "module_header": "Module Header",
    "module_code": "Module Code",
    "code_block": "Code Block",
    "config": "Config",
    "config_section": "Config Section",
    "section": "Section",
    "document": "Document",
    "file_overview": "File Overview",
    "table": "Table",
}


class ContentPanel(ttk.LabelFrame):
    """Displays selected search result content using RenderedMarkdown."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent, text="Content", padding=5)
        self.bus = event_bus
        self._current_file_path = None
        self._collection_path = None
        self._build()
        self.bus.on("result:selected", self._on_result_selected)
        self.bus.on("stream:started", lambda _d: self.after(0, self._on_stream_started))
        self.bus.on("state:active_collection", lambda d: setattr(self, '_collection_path', d.get("new")))

    def _get_colors(self):
        dark = _is_dark_theme()
        return {
            "bg": DARK_BG if dark else LIGHT_BG,
            "bg_alt": get_bg_alt(),
            "fg": DARK_FG if dark else LIGHT_FG,
            "fg_dim": DARK_FG_DIM if dark else LIGHT_FG_DIM,
            "border": DARK_BORDER if dark else LIGHT_BORDER,
            "accent": get_accent_color(),
            "accent_soft": get_accent_soft(),
        }

    def _build(self):
        c = self._get_colors()

        # --- Header bar ---
        self._header_frame = tk.Frame(self, bg=c["bg_alt"], bd=0, highlightthickness=1,
                                      highlightbackground=c["border"])
        self._header_frame.pack(fill=tk.X, pady=(0, 2))
        self._header_frame.pack_forget()  # hidden until content shown

        # Left side: type badge + name
        header_left = tk.Frame(self._header_frame, bg=c["bg_alt"])
        header_left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=4)

        self._type_badge = tk.Label(header_left, text="", font=prose_font(9, "bold"),
                                    fg=c["bg"], bg=c["accent"], padx=6, pady=1,
                                    relief=tk.FLAT)
        self._type_badge.pack(side=tk.LEFT, padx=(0, 8))

        self._name_label = tk.Label(header_left, text="", font=prose_font(11, "bold"),
                                    fg=c["fg"], bg=c["bg_alt"], anchor=tk.W)
        self._name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Right side: view file button
        header_right = tk.Frame(self._header_frame, bg=c["bg_alt"])
        header_right.pack(side=tk.RIGHT, padx=6, pady=4)

        self._view_file_btn = tk.Button(
            header_right, text="View Full File", font=prose_font(9),
            fg=c["accent"], bg=c["bg_alt"], activeforeground=c["bg"],
            activebackground=c["accent"], bd=1, relief=tk.GROOVE,
            cursor="hand2", padx=8, pady=2,
            command=self._open_current_file,
        )
        self._view_file_btn.pack(side=tk.RIGHT)
        self._view_file_btn.pack_forget()  # hidden until file result

        # --- Metrics bar ---
        self._metrics_frame = tk.Frame(self, bg=c["bg"], bd=0)
        self._metrics_frame.pack(fill=tk.X, pady=(0, 2))
        self._metrics_frame.pack_forget()  # hidden until content shown

        self._metrics_labels = []

        # --- Content area ---
        self._content_frame = tk.Frame(self)
        self._content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame = self._content_frame

        self.renderer = RenderedMarkdown(content_frame)
        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.renderer.yview)
        self.renderer.configure(yscrollcommand=scrollbar.set)

        self.renderer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Empty state overlay
        self._empty = EmptyState(self, "Click a result to view its content")
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_header(self, mode: str, name: str = "", chunk_type: str = "",
                     file_path: str = "", start_line: int = 0, end_line: int = 0,
                     score: float = 0.0, language: str = "", timing_ms: float = 0.0):
        """Populate and show the header bar and metrics."""
        c = self._get_colors()

        # Update header frame colors (theme may have changed)
        self._header_frame.configure(bg=c["bg_alt"], highlightbackground=c["border"])

        if mode == "llm":
            badge_text = "LLM Response"
            badge_bg = "#6a5acd" if _is_dark_theme() else "#4a3ab0"
            self._type_badge.configure(text=badge_text, bg=badge_bg, fg="#ffffff")
            self._name_label.configure(text="Synthesis", fg=c["fg"], bg=c["bg_alt"])
            self._view_file_btn.pack_forget()
            self._current_file_path = None

            metrics = []
            if timing_ms > 0:
                metrics.append(("Latency", f"{timing_ms:.0f}ms"))
        else:
            type_label = _CHUNK_TYPE_LABELS.get(chunk_type, chunk_type.replace("_", " ").title())
            self._type_badge.configure(text=type_label, bg=c["accent"], fg=c["bg"])
            display_name = name or os.path.basename(file_path)
            self._name_label.configure(text=display_name, fg=c["fg"], bg=c["bg_alt"])

            resolved = self._resolve_path(file_path) if file_path else ""
            if resolved and os.path.isfile(resolved):
                self._current_file_path = resolved
                self._view_file_btn.configure(fg=c["accent"], bg=c["bg_alt"],
                                              activeforeground=c["bg"],
                                              activebackground=c["accent"])
                self._view_file_btn.pack(side=tk.RIGHT)
            else:
                self._current_file_path = None
                self._view_file_btn.pack_forget()

            metrics = []
            if file_path:
                metrics.append(("File", os.path.basename(file_path)))
            if language:
                metrics.append(("Language", language))
            if start_line and end_line:
                metrics.append(("Lines", f"{start_line} - {end_line}"))
            if score > 0:
                score_label = "HIGH" if score >= 0.04 else "GOOD" if score >= 0.03 else "FAIR"
                metrics.append(("Score", f"{score:.3f} ({score_label})"))

        # Rebuild metrics row
        for lbl in self._metrics_labels:
            lbl.destroy()
        self._metrics_labels.clear()
        self._metrics_frame.configure(bg=c["bg"])

        for i, (key, val) in enumerate(metrics):
            if i > 0:
                sep = tk.Label(self._metrics_frame, text="|", font=prose_font(9),
                               fg=c["border"], bg=c["bg"])
                sep.pack(side=tk.LEFT, padx=4)
                self._metrics_labels.append(sep)

            k_lbl = tk.Label(self._metrics_frame, text=f"{key}: ", font=prose_font(9, "bold"),
                             fg=c["fg_dim"], bg=c["bg"])
            k_lbl.pack(side=tk.LEFT)
            self._metrics_labels.append(k_lbl)

            v_lbl = tk.Label(self._metrics_frame, text=val, font=prose_font(9),
                             fg=c["fg"], bg=c["bg"])
            v_lbl.pack(side=tk.LEFT)
            self._metrics_labels.append(v_lbl)

        # Re-pack in correct order: header, metrics, content
        self._header_frame.pack_forget()
        self._metrics_frame.pack_forget()
        self._content_frame.pack_forget()

        self._header_frame.pack(fill=tk.X, pady=(0, 2))
        if metrics:
            self._metrics_frame.pack(fill=tk.X, pady=(0, 4))
        self._content_frame.pack(fill=tk.BOTH, expand=True)

    def _hide_header(self):
        self._header_frame.pack_forget()
        self._metrics_frame.pack_forget()

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a potentially relative file path against the active collection."""
        from pathlib import Path
        p = Path(file_path)
        if p.is_absolute() and p.exists():
            return str(p)
        if self._collection_path:
            resolved = Path(self._collection_path) / file_path
            if resolved.exists():
                return str(resolved)
        return file_path

    def _open_current_file(self):
        if not self._current_file_path or not os.path.isfile(self._current_file_path):
            return
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", self._current_file_path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self._current_file_path])
        else:
            os.startfile(self._current_file_path)

    def _on_stream_started(self):
        self._empty.place_forget()
        self._show_header("llm")

    def _on_result_selected(self, data):
        result = data.get("result")
        if not result:
            return

        # Hide empty state on first result
        self._empty.place_forget()

        chunk_type = getattr(result, "chunk_type", "")
        file_path = getattr(result, "file_path", "")
        content = getattr(result, "content", "")
        name = getattr(result, "name", "")
        start_line = getattr(result, "start_line", 0)
        end_line = getattr(result, "end_line", 0)
        score = getattr(result, "score", 0.0)
        language = getattr(result, "language", "")

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        self._show_header("file", name=name, chunk_type=chunk_type,
                          file_path=file_path, start_line=start_line,
                          end_line=end_line, score=score, language=language)

        if self._should_use_code_view(chunk_type, ext):
            lang = self._detect_language(ext)
            self.renderer.render_code(content, language=lang)
        else:
            self.renderer.render(content, strip_markers=True)

    def _should_use_code_view(self, chunk_type: str, ext: str) -> bool:
        if chunk_type in _CODE_CHUNK_TYPES:
            return True
        if chunk_type in ("section", "document", "file_overview"):
            return False
        return ext in _CODE_EXTENSIONS

    def _detect_language(self, ext: str) -> str:
        lang_map = {
            "py": "python", "js": "javascript", "ts": "typescript",
            "rs": "rust", "go": "go", "java": "java", "rb": "ruby",
            "sh": "bash", "bash": "bash", "zsh": "bash",
            "yaml": "yaml", "yml": "yaml", "toml": "toml",
        }
        return lang_map.get(ext, "python")

    def show_synthesis(self, text: str):
        """Show LLM synthesis output with rendered markdown."""
        self._empty.place_forget()
        # Extract timing if present in the text
        import re
        timing_match = re.match(r'LLM Synthesis \((\d+)ms\):\n\n', text)
        timing_ms = float(timing_match.group(1)) if timing_match else 0.0
        clean_text = re.sub(r'^LLM Synthesis \(\d+ms\):\n\n', '', text) if timing_match else text
        self._show_header("llm", timing_ms=timing_ms)
        self.renderer.render_synthesis(clean_text)

    def clear(self):
        self.renderer.clear()
        self._hide_header()
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=1)

"""Content panel - routes chunks to the correct renderer.

Auto-detects chunk type and file extension to decide between
code view (syntax highlighting) and rendered markdown (stripped syntax).
"""

import tkinter as tk
from tkinter import ttk

from ..events import EventBus
from .rendered_markdown import RenderedMarkdown
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


class ContentPanel(ttk.LabelFrame):
    """Displays selected search result content using RenderedMarkdown."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent, text="Content", padding=5)
        self.bus = event_bus
        self._build()
        self.bus.on("result:selected", self._on_result_selected)

    def _build(self):
        self.renderer = RenderedMarkdown(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.renderer.yview)
        self.renderer.configure(yscrollcommand=scrollbar.set)

        self.renderer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Empty state overlay
        self._empty = EmptyState(self, "Click a result to view its content")
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=1)

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

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if self._should_use_code_view(chunk_type, ext):
            file_info = f"{file_path}  |  {chunk_type} | {name} | Lines {start_line}-{end_line}"
            lang = self._detect_language(ext)
            self.renderer.render_code(content, language=lang, file_info=file_info)
        else:
            self.renderer.render(content, strip_markers=True)

    def _should_use_code_view(self, chunk_type: str, ext: str) -> bool:
        if chunk_type in _CODE_CHUNK_TYPES:
            return True
        if chunk_type in ("section", "document", "file_overview"):
            return False
        # Fallback: decide by file extension
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
        self.renderer.render_synthesis(text)

    def clear(self):
        self.renderer.clear()
        # Re-show empty state
        self._empty.place(relx=0, rely=0, relwidth=1, relheight=1)

"""Rich markdown rendering widget for tk.Text.

Renders markdown as formatted rich text with:
- Headers at correct sizes without # markers
- Bold/italic without ** markers
- Code blocks as embedded syntax-highlighted widgets
- Tables as embedded Treeview widgets
- Horizontal rules as Separator widgets
- Clickable links
- Blockquotes with indent and styling
- Inline code with background highlighting

Used for content display, LLM synthesis output, and research results.
"""

import re
import sys
import tkinter as tk
from tkinter import ttk
import webbrowser

# Python keyword set for syntax highlighting
_PY_KW = {
    "def", "class", "import", "from", "return", "if", "elif", "else", "for",
    "while", "try", "except", "finally", "with", "as", "yield", "raise",
    "pass", "break", "continue", "lambda", "and", "or", "not", "in", "is",
    "None", "True", "False", "self", "async", "await",
}

# Font detection with fallback
def _detect_fonts():
    """Detect best available fonts for the current platform.

    Tries platform-preferred fonts first, then common fallbacks.
    Tkinter silently falls back to its default if none match, but
    we try to pick something good explicitly.
    """
    # Can't call tk.font.families() at module load (no Tk instance yet),
    # so we use platform heuristics with broad fallback chains.
    if sys.platform == "win32":
        prose_chain = ["Segoe UI", "Calibri", "Arial"]
        code_chain = ["Cascadia Mono", "Consolas", "Courier New"]
    elif sys.platform == "darwin":
        prose_chain = ["SF Pro Text", "Helvetica Neue", "Helvetica"]
        code_chain = ["Menlo", "Monaco", "Courier"]
    else:
        prose_chain = ["Cantarell", "Noto Sans", "DejaVu Sans", "Liberation Sans"]
        code_chain = ["Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono", "Monospace"]
    return prose_chain[0], code_chain[0], prose_chain, code_chain

_PROSE_FAMILY, _CODE_FAMILY, _PROSE_CHAIN, _CODE_CHAIN = _detect_fonts()


def _resolve_font_family(chain: list, tk_root=None) -> str:
    """Pick the first available font from the chain, verified against Tk."""
    if tk_root is None:
        return chain[0]
    try:
        import tkinter.font as tkfont
        available = set(tkfont.families(root=tk_root))
        for candidate in chain:
            if candidate in available:
                return candidate
    except Exception:
        pass
    return chain[0]


def prose_font(size=11, weight="normal"):
    mods = "bold" if weight == "bold" else ""
    if mods:
        return (_PROSE_FAMILY, size, mods)
    return (_PROSE_FAMILY, size)


def code_font(size=10, weight="normal"):
    mods = "bold" if weight == "bold" else ""
    if mods:
        return (_CODE_FAMILY, size, mods)
    return (_CODE_FAMILY, size)


class RenderedMarkdown(tk.Text):
    """Text widget that renders markdown as rich formatted content."""

    def __init__(self, parent, **kwargs):
        defaults = {
            "wrap": tk.WORD,
            "font": prose_font(),
            "padx": 12,
            "pady": 8,
            "spacing1": 2,
            "spacing3": 2,
            "cursor": "arrow",
            "insertwidth": 0,
            "bd": 0,
            "highlightthickness": 0,
        }
        defaults.update(kwargs)
        super().__init__(parent, **defaults)
        self._resolve_runtime_fonts()
        self._setup_tags()
        self.config(state=tk.DISABLED)

    def _resolve_runtime_fonts(self):
        """Verify font availability now that Tk is running."""
        global _PROSE_FAMILY, _CODE_FAMILY
        _PROSE_FAMILY = _resolve_font_family(_PROSE_CHAIN, self.winfo_toplevel())
        _CODE_FAMILY = _resolve_font_family(_CODE_CHAIN, self.winfo_toplevel())
        self.configure(font=prose_font())

    def _setup_tags(self):
        # Headers
        self.tag_configure("h1", font=prose_font(18, "bold"), foreground="#61afef",
                          spacing1=12, spacing3=6)
        self.tag_configure("h2", font=prose_font(15, "bold"), foreground="#61afef",
                          spacing1=10, spacing3=4)
        self.tag_configure("h3", font=prose_font(12, "bold"), foreground="#61afef",
                          spacing1=8, spacing3=3)

        # Inline formatting
        self.tag_configure("bold", font=prose_font(11, "bold"))
        self.tag_configure("italic", font=(_PROSE_FAMILY, 11, "italic"))
        self.tag_configure("inline_code", font=code_font(), background="#2c313a",
                          foreground="#e06c75")

        # Block elements
        self.tag_configure("blockquote", font=(_PROSE_FAMILY, 11, "italic"),
                          foreground="#98c379", lmargin1=20, lmargin2=20,
                          spacing1=4, spacing3=4)
        self.tag_configure("list_item", lmargin1=15, lmargin2=30)
        self.tag_configure("link", foreground="#61afef", underline=True)

        # Metadata header
        self.tag_configure("meta_header", font=prose_font(9), foreground="#6a9fb5")
        self.tag_configure("meta_separator", foreground="#555555")

        # Thinking/reasoning
        self.tag_configure("thinking", font=(_PROSE_FAMILY, 10, "italic"),
                          foreground="#5c6370", lmargin1=15, lmargin2=15)

        # Code highlighting (for embedded code blocks)
        self.tag_configure("kw", foreground="#c678dd", font=code_font())
        self.tag_configure("str", foreground="#98c379", font=code_font())
        self.tag_configure("comment", foreground="#5c6370", font=(_CODE_FAMILY, 10, "italic"))
        self.tag_configure("num", foreground="#d19a66", font=code_font())
        self.tag_configure("func_name", foreground="#61afef", font=code_font(10, "bold"))
        self.tag_configure("decorator", foreground="#e5c07b", font=code_font())

    # === Public API ===

    def render(self, text: str, strip_markers: bool = True):
        """Render markdown text with full formatting."""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)

        # Sanitize content before rendering
        text = self._sanitize_content(text)

        if strip_markers:
            self._render_markdown(text)
        else:
            self.insert("1.0", text)

        self.config(state=tk.DISABLED)

    @staticmethod
    def _sanitize_content(text: str) -> str:
        """Strip base64 images, fix links, and remove noise from scraped content."""
        import re
        # Strip markdown images with base64 data URIs (tracking pixels, icons)
        text = re.sub(r'!\[[^\]]*\]\(data:image/[^)]+\)', '', text)
        # Strip raw base64 data URI strings on their own line
        text = re.sub(r'^data:image/[^\s]+$', '', text, flags=re.MULTILINE)
        # Convert relative-path links to plain text (can't resolve without base URL)
        # [text](/path) or [text](path) → just text
        text = re.sub(r'\[([^\]]+)\]\((?!//)(?!https?://)([^)]+)\)', r'\1', text)
        # Strip empty image references
        text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
        # Collapse multiple blank lines left by stripping
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def render_code(self, code: str, language: str = "python", file_info: str = ""):
        """Render a code chunk with syntax highlighting and metadata header."""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)

        if file_info:
            self.insert(tk.END, file_info + "\n")
            self.tag_add("meta_header", "1.0", f"1.end")
            sep = "-" * 60 + "\n"
            sep_start = self.index(tk.END + "-1c")
            self.insert(tk.END, sep)
            self.tag_add("meta_separator", sep_start, self.index(tk.END + "-1c"))

        code_start = int(self.index(tk.END).split(".")[0])
        self.insert(tk.END, code)
        self._highlight_code(code_start, language)

        self.config(state=tk.DISABLED)

    def render_synthesis(self, text: str):
        """Render LLM synthesis output as markdown."""
        self.render(text, strip_markers=True)

    def show_placeholder(self, text: str):
        """Show placeholder text (e.g. 'Generating answer...')."""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.insert("1.0", text)
        self.tag_add("thinking", "1.0", tk.END)
        self.config(state=tk.DISABLED)

    def clear(self):
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.config(state=tk.DISABLED)

    # === Streaming API ===

    def begin_stream(self):
        """Prepare for incremental streaming content."""
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self._stream_thinking = False

    def set_stream_thinking(self, thinking: bool):
        """Toggle thinking/reasoning style during streaming."""
        self._stream_thinking = thinking

    def append_stream(self, text: str):
        """Append streaming text with optional thinking styling."""
        self.config(state=tk.NORMAL)
        start = self.index(tk.END + "-1c")
        self.insert(tk.END, text)
        if getattr(self, "_stream_thinking", False):
            self.tag_add("thinking", start, self.index(tk.END + "-1c"))

    def end_stream(self):
        """Final render pass after streaming completes."""
        full_text = self.get("1.0", tk.END)
        self.render(full_text.strip(), strip_markers=True)

    # === Internal rendering ===

    def _render_markdown(self, text: str):
        """Parse and render markdown with stripped syntax."""
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Code block
            if line.strip().startswith("```"):
                lang = line.strip()[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                self._insert_code_block("\n".join(code_lines), lang)
                i += 1
                continue

            # Horizontal rule
            if re.match(r'^---+$', line.strip()):
                self._insert_separator()
                i += 1
                continue

            # Table
            if "|" in line and line.strip().startswith("|"):
                table_lines = []
                while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                self._insert_table(table_lines)
                continue

            # Thinking tags
            if "<think>" in line:
                think_lines = []
                line = line.replace("<think>", "")
                while i < len(lines) and "</think>" not in lines[i]:
                    think_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    think_lines.append(lines[i].replace("</think>", ""))
                    i += 1
                self._insert_thinking("\n".join(think_lines))
                continue

            # Headers
            h_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            if h_match:
                level = len(h_match.group(1))
                self._insert_formatted_line(h_match.group(2), f"h{level}")
                i += 1
                continue

            # Blockquote
            if line.startswith("> "):
                self._insert_formatted_line(line[2:], "blockquote")
                i += 1
                continue

            # List items
            list_match = re.match(r'^(\s*[-*]|\s*\d+\.)\s+(.+)$', line)
            if list_match:
                bullet = "  •  " if line.strip()[0] in "-*" else f"  {list_match.group(1).strip()}  "
                start = self.index(tk.END + "-1c")
                self.insert(tk.END, bullet)
                self._insert_inline_formatted(list_match.group(2))
                self.insert(tk.END, "\n")
                self.tag_add("list_item", start, self.index(tk.END + "-1c"))
                i += 1
                continue

            # Empty line
            if not line.strip():
                self.insert(tk.END, "\n")
                i += 1
                continue

            # Normal paragraph
            self._insert_formatted_line(line, None)
            i += 1

    def _insert_formatted_line(self, text: str, tag: str | None = None):
        start = self.index(tk.END + "-1c")
        self._insert_inline_formatted(text)
        self.insert(tk.END, "\n")
        if tag:
            self.tag_add(tag, start, self.index(tk.END + "-1c"))

    def _insert_inline_formatted(self, text: str):
        """Parse bold, inline code, and links."""
        parts = re.split(r'(\*\*.*?\*\*|`[^`]+`|\[.*?\]\(.*?\))', text)

        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                start = self.index(tk.END + "-1c")
                self.insert(tk.END, part[2:-2])
                self.tag_add("bold", start, self.index(tk.END + "-1c"))
            elif part.startswith("`") and part.endswith("`"):
                start = self.index(tk.END + "-1c")
                self.insert(tk.END, part[1:-1])
                self.tag_add("inline_code", start, self.index(tk.END + "-1c"))
            elif part.startswith("["):
                link_match = re.match(r'\[(.+?)\]\((.+?)\)', part)
                if link_match:
                    link_text = link_match.group(1)
                    link_url = link_match.group(2)
                    start = self.index(tk.END + "-1c")
                    self.insert(tk.END, link_text)
                    end = self.index(tk.END + "-1c")
                    tag_name = f"link_{id(link_url)}"
                    self.tag_configure(tag_name, foreground="#61afef", underline=True)
                    self.tag_add(tag_name, start, end)
                    self.tag_bind(tag_name, "<Button-1>",
                                 lambda e, url=link_url: webbrowser.open(url))
                    self.tag_bind(tag_name, "<Button-3>",
                                 lambda e, url=link_url: self._show_link_menu(e, url))
                    self.tag_bind(tag_name, "<Enter>",
                                 lambda e: self.config(cursor="hand2"))
                    self.tag_bind(tag_name, "<Leave>",
                                 lambda e: self.config(cursor="arrow"))
                else:
                    self.insert(tk.END, part)
            else:
                self.insert(tk.END, part)

    def _show_link_menu(self, event, url: str):
        """Right-click context menu for links."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open in Browser", command=lambda: webbrowser.open(url))
        menu.add_command(label="Copy Link", command=lambda: self._copy_to_clipboard(url))
        menu.add_separator()
        menu.add_command(label="Scrape URL", command=lambda: self._emit_scrape(url))
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _emit_scrape(self, url: str):
        """Emit a scrape request for this URL (if event bus is available)."""
        # Walk up to find the app and emit
        widget = self.master
        while widget:
            if hasattr(widget, "bus"):
                widget.bus.emit("research:scrape_single", {"url": url})
                return
            widget = getattr(widget, "master", None)

    def _insert_code_block(self, code: str, lang: str = ""):
        """Embed a syntax-highlighted code block widget."""
        frame = tk.Frame(self, bg="#1e1e2e", bd=1, relief=tk.SOLID)

        if lang:
            lang_label = tk.Label(frame, text=lang, font=code_font(8),
                                 fg="#585b70", bg="#1e1e2e", anchor=tk.E)
            lang_label.pack(fill=tk.X, padx=5, pady=(2, 0))

        height = min(code.count("\n") + 1, 20)
        code_text = tk.Text(frame, wrap=tk.NONE, font=code_font(),
                           bg="#1e1e2e", fg="#abb2bf",
                           padx=10, pady=8, bd=0,
                           height=height,
                           insertwidth=0, cursor="arrow",
                           relief=tk.FLAT)
        code_text.insert("1.0", code)
        self._highlight_code_widget(code_text, lang)
        code_text.config(state=tk.DISABLED)

        if height >= 20:
            scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=code_text.yview)
            code_text.configure(yscrollcommand=scroll.set)
            code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            code_text.pack(fill=tk.X, padx=2, pady=2)

        self.insert(tk.END, "\n")
        self.window_create(tk.END, window=frame, padx=10, pady=5, stretch=True)
        self.insert(tk.END, "\n")

    def _highlight_code_widget(self, widget, lang=""):
        """Syntax highlight a code text widget."""
        widget.tag_configure("kw", foreground="#c678dd")
        widget.tag_configure("str", foreground="#98c379")
        widget.tag_configure("comment", foreground="#5c6370",
                            font=(_CODE_FAMILY, 10, "italic"))
        widget.tag_configure("num", foreground="#d19a66")
        widget.tag_configure("func_name", foreground="#61afef",
                            font=code_font(10, "bold"))
        widget.tag_configure("decorator", foreground="#e5c07b")

        end_line = int(widget.index(tk.END).split(".")[0])
        for ln in range(1, end_line + 1):
            line = widget.get(f"{ln}.0", f"{ln}.end")
            if not line.strip():
                continue

            for m in re.finditer(r'#.*$', line):
                widget.tag_add("comment", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', line):
                widget.tag_add("str", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'@\w+', line):
                widget.tag_add("decorator", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'\b(\w+)\b', line):
                if m.group(1) in _PY_KW:
                    widget.tag_add("kw", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'(?:def|function|fn)\s+(\w+)', line):
                widget.tag_add("func_name", f"{ln}.{m.start(1)}", f"{ln}.{m.end(1)}")
            for m in re.finditer(r'\b\d+\.?\d*\b', line):
                widget.tag_add("num", f"{ln}.{m.start()}", f"{ln}.{m.end()}")

    def _highlight_code(self, start_line: int, lang: str = "python"):
        """Highlight code directly in this widget (for code view mode)."""
        end_line = int(self.index(tk.END).split(".")[0])
        for ln in range(start_line, end_line + 1):
            line = self.get(f"{ln}.0", f"{ln}.end")
            if not line.strip():
                continue

            for m in re.finditer(r'#.*$', line):
                self.tag_add("comment", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', line):
                self.tag_add("str", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'@\w+', line):
                self.tag_add("decorator", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'\b(\w+)\b', line):
                if m.group(1) in _PY_KW:
                    self.tag_add("kw", f"{ln}.{m.start()}", f"{ln}.{m.end()}")
            for m in re.finditer(r'(?:def|function|fn)\s+(\w+)', line):
                self.tag_add("func_name", f"{ln}.{m.start(1)}", f"{ln}.{m.end(1)}")
            for m in re.finditer(r'\b\d+\.?\d*\b', line):
                self.tag_add("num", f"{ln}.{m.start()}", f"{ln}.{m.end()}")

    def _insert_separator(self):
        """Insert a horizontal rule."""
        sep = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.insert(tk.END, "\n")
        self.window_create(tk.END, window=sep, padx=20, pady=8, stretch=True)
        self.insert(tk.END, "\n")

    def _insert_table(self, table_lines: list):
        """Insert a rendered table as an embedded Treeview."""
        rows = []
        for line in table_lines:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and not all(re.match(r'^[-:]+$', c) for c in cells):
                rows.append(cells)

        if len(rows) < 2:
            return

        headers = rows[0]
        data_rows = rows[1:]

        frame = tk.Frame(self)
        tree = ttk.Treeview(frame, columns=list(range(len(headers))),
                           show="headings", height=min(len(data_rows), 10))

        for i, header in enumerate(headers):
            tree.heading(i, text=header)
            max_width = max(len(header), max((len(r[i]) if i < len(r) else 0) for r in data_rows))
            tree.column(i, width=max(80, min(max_width * 9, 300)), anchor=tk.W)

        for row in data_rows:
            values = row + [""] * (len(headers) - len(row))
            tree.insert("", tk.END, values=values[:len(headers)])

        tree.pack(fill=tk.X, padx=2, pady=2)

        self.insert(tk.END, "\n")
        self.window_create(tk.END, window=frame, padx=20, pady=5)
        self.insert(tk.END, "\n")

    def _insert_thinking(self, text: str):
        """Insert collapsible thinking/reasoning block."""
        frame = tk.Frame(self, bg="#2c313a", bd=1, relief=tk.GROOVE)

        is_expanded = tk.BooleanVar(value=False)
        toggle_btn = tk.Button(frame, text="▶ Reasoning (click to expand)",
                              font=prose_font(9), fg="#5c6370", bg="#2c313a",
                              bd=0, cursor="hand2", anchor=tk.W)

        thinking_text = tk.Text(frame, wrap=tk.WORD, font=(_PROSE_FAMILY, 10, "italic"),
                               fg="#5c6370", bg="#2c313a", bd=0,
                               padx=10, pady=5,
                               height=min(text.count("\n") + 1, 15),
                               insertwidth=0, cursor="arrow")
        thinking_text.insert("1.0", text.strip())
        thinking_text.config(state=tk.DISABLED)

        def _toggle():
            if is_expanded.get():
                thinking_text.pack_forget()
                toggle_btn.config(text="▶ Reasoning (click to expand)")
                is_expanded.set(False)
            else:
                thinking_text.pack(fill=tk.X, padx=5, pady=(0, 5))
                toggle_btn.config(text="▼ Reasoning (click to collapse)")
                is_expanded.set(True)

        toggle_btn.config(command=_toggle)
        toggle_btn.pack(fill=tk.X, padx=5, pady=2)

        self.insert(tk.END, "\n")
        self.window_create(tk.END, window=frame, padx=10, pady=5, stretch=True)
        self.insert(tk.END, "\n")

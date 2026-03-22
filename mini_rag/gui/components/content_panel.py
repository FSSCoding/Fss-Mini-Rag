"""Content panel for displaying chunk details with syntax highlighting."""

import re
import tkinter as tk
from tkinter import ttk

from ..events import EventBus


# Language keyword sets for highlighting
_PYTHON_KW = {
    "def", "class", "import", "from", "return", "if", "elif", "else", "for",
    "while", "try", "except", "finally", "with", "as", "yield", "raise",
    "pass", "break", "continue", "lambda", "and", "or", "not", "in", "is",
    "None", "True", "False", "self", "async", "await",
}
_JS_KW = {
    "function", "const", "let", "var", "return", "if", "else", "for", "while",
    "class", "new", "this", "import", "export", "from", "async", "await",
    "try", "catch", "finally", "throw", "typeof", "instanceof", "null",
    "undefined", "true", "false", "switch", "case", "default", "break",
    "continue", "yield", "of", "in",
}
_RUST_KW = {
    "fn", "let", "mut", "pub", "struct", "enum", "impl", "trait", "use",
    "mod", "crate", "self", "super", "match", "if", "else", "for", "while",
    "loop", "return", "break", "continue", "where", "async", "await",
    "unsafe", "move", "ref", "type", "const", "static", "true", "false",
}
_ALL_KW = _PYTHON_KW | _JS_KW | _RUST_KW


class ContentPanel(ttk.LabelFrame):
    """Text widget showing full content of selected search result with highlighting."""

    def __init__(self, parent, event_bus: EventBus):
        super().__init__(parent, text="Content", padding=5)
        self.bus = event_bus
        self._build()
        self.bus.on("result:selected", self._on_result_selected)

    def _build(self):
        self.text = tk.Text(self, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Syntax highlighting tags
        self.text.tag_configure("header", font=("Courier", 10, "bold"), foreground="#6a9fb5")
        self.text.tag_configure("separator", foreground="#555555")
        self.text.tag_configure("keyword", foreground="#c678dd")
        self.text.tag_configure("string", foreground="#98c379")
        self.text.tag_configure("comment", foreground="#5c6370", font=("Courier", 10, "italic"))
        self.text.tag_configure("number", foreground="#d19a66")
        self.text.tag_configure("decorator", foreground="#e5c07b")
        self.text.tag_configure("function_def", foreground="#61afef", font=("Courier", 10, "bold"))
        self.text.tag_configure("type_name", foreground="#e06c75")

        # Markdown tags
        self.text.tag_configure("md_h1", font=("Courier", 14, "bold"), foreground="#61afef")
        self.text.tag_configure("md_h2", font=("Courier", 12, "bold"), foreground="#61afef")
        self.text.tag_configure("md_h3", font=("Courier", 11, "bold"), foreground="#61afef")
        self.text.tag_configure("md_code", background="#2c313a", font=("Courier", 10))
        self.text.tag_configure("md_bold", font=("Courier", 10, "bold"))
        self.text.tag_configure("md_inline_code", background="#2c313a", foreground="#e06c75")

        # Synthesis tags
        self.text.tag_configure("synthesis_header", font=("Courier", 11, "bold"), foreground="#98c379")

    def _on_result_selected(self, data):
        result = data.get("result")
        if not result:
            return

        self.text.delete("1.0", tk.END)

        # Header section
        header_lines = [
            f"File: {result.file_path}",
            f"Type: {result.chunk_type} | Name: {result.name}",
            f"Lines: {result.start_line}-{result.end_line}",
        ]
        header = "\n".join(header_lines) + "\n"
        self.text.insert("1.0", header)
        for i in range(len(header_lines)):
            self.text.tag_add("header", f"{i+1}.0", f"{i+1}.end")

        sep = "-" * 60 + "\n\n"
        sep_start = self.text.index(tk.END + "-1c")
        self.text.insert(tk.END, sep)
        self.text.tag_add("separator", sep_start, f"{sep_start}+{len(sep)-1}c")

        # Content with highlighting
        content_start_line = int(self.text.index(tk.END + "-1c").split(".")[0])
        self.text.insert(tk.END, result.content)

        # Apply syntax highlighting based on file extension
        ext = result.file_path.rsplit(".", 1)[-1].lower() if "." in result.file_path else ""
        if ext in ("md", "markdown", "rst"):
            self._highlight_markdown(content_start_line)
        elif ext in ("py", "js", "ts", "tsx", "jsx", "rs", "go", "java", "c", "cpp", "h", "hpp", "cs", "rb", "sh", "bash", "zsh"):
            self._highlight_code(content_start_line)

    def _highlight_code(self, start_line):
        end_idx = self.text.index(tk.END)
        end_line = int(end_idx.split(".")[0])

        for line_num in range(start_line, end_line + 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            line_text = self.text.get(line_start, line_end)

            if not line_text.strip():
                continue

            # Comments (# or //)
            for m in re.finditer(r'(#|//).*$', line_text):
                self.text.tag_add("comment", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Strings (single, double, triple-quoted)
            for m in re.finditer(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', line_text):
                self.text.tag_add("string", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Decorators
            for m in re.finditer(r'@\w+', line_text):
                self.text.tag_add("decorator", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Keywords
            for m in re.finditer(r'\b(\w+)\b', line_text):
                word = m.group(1)
                if word in _ALL_KW:
                    self.text.tag_add("keyword", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Function/method definitions
            for m in re.finditer(r'(?:def|function|fn|func)\s+(\w+)', line_text):
                self.text.tag_add("function_def", f"{line_num}.{m.start(1)}", f"{line_num}.{m.end(1)}")

            # Numbers
            for m in re.finditer(r'\b\d+\.?\d*\b', line_text):
                self.text.tag_add("number", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Type annotations (capitalized words after : or ->)
            for m in re.finditer(r'(?::\s*|->)\s*([A-Z]\w+)', line_text):
                self.text.tag_add("type_name", f"{line_num}.{m.start(1)}", f"{line_num}.{m.end(1)}")

    def _highlight_markdown(self, start_line):
        end_idx = self.text.index(tk.END)
        end_line = int(end_idx.split(".")[0])
        in_code_block = False

        for line_num in range(start_line, end_line + 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            line_text = self.text.get(line_start, line_end)

            # Code blocks
            if line_text.strip().startswith("```"):
                in_code_block = not in_code_block
                self.text.tag_add("md_code", line_start, line_end)
                continue

            if in_code_block:
                self.text.tag_add("md_code", line_start, line_end)
                continue

            # Headers
            if line_text.startswith("### "):
                self.text.tag_add("md_h3", line_start, line_end)
            elif line_text.startswith("## "):
                self.text.tag_add("md_h2", line_start, line_end)
            elif line_text.startswith("# "):
                self.text.tag_add("md_h1", line_start, line_end)

            # Bold
            for m in re.finditer(r'\*\*(.+?)\*\*', line_text):
                self.text.tag_add("md_bold", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            # Inline code
            for m in re.finditer(r'`([^`]+)`', line_text):
                self.text.tag_add("md_inline_code", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

    def show_synthesis(self, text: str):
        """Show LLM synthesis output with basic formatting."""
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)

        # Highlight the header line
        first_line = self.text.get("1.0", "1.end")
        if first_line.startswith("LLM Synthesis") or first_line.startswith("Generating"):
            self.text.tag_add("synthesis_header", "1.0", "1.end")

        # Apply markdown highlighting to the rest
        self._highlight_markdown(2)

    def clear(self):
        self.text.delete("1.0", tk.END)

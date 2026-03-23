"""
AST-based code chunking for intelligent code splitting.
Chunks by functions, classes, and logical boundaries instead of arbitrary lines.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default per-language chunking configs (consolidated from smart_chunking.py)
DEFAULT_LANGUAGE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "python": {
        "max_size": 3000,
        "min_size": 200,
    },
    "javascript": {
        "max_size": 2500,
        "min_size": 150,
    },
    "typescript": {
        "max_size": 2500,
        "min_size": 150,
    },
    "markdown": {
        "max_size": 2500,
        "min_size": 300,
    },
    "json": {
        "max_size": 1000,
        "min_size": 50,
        "max_file_size": 50000,
    },
    "yaml": {
        "max_size": 1500,
        "min_size": 100,
    },
    "text": {
        "max_size": 2000,
        "min_size": 200,
    },
    "bash": {
        "max_size": 1500,
        "min_size": 100,
    },
    "go": {
        "max_size": 2500,
        "min_size": 150,
    },
    "java": {
        "max_size": 3000,
        "min_size": 200,
    },
    "html": {
        "max_size": 3000,
        "min_size": 200,
    },
    "shell": {
        "max_size": 2000,
        "min_size": 100,
    },
    "css": {
        "max_size": 2000,
        "min_size": 100,
    },
    "sql": {
        "max_size": 2500,
        "min_size": 150,
    },
}


class CodeChunk:
    """Represents a logical chunk of code."""

    def __init__(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
        name: Optional[str] = None,
        language: str = "python",
        file_lines: Optional[int] = None,
        chunk_index: Optional[int] = None,
        total_chunks: Optional[int] = None,
        parent_class: Optional[str] = None,
        parent_function: Optional[str] = None,
        prev_chunk_id: Optional[str] = None,
        next_chunk_id: Optional[str] = None,
        is_overlap: bool = False,
    ):
        self.content = content
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_type = (
            chunk_type  # 'function', 'class', 'method', 'module', 'module_header'
        )
        self.name = name
        self.language = language
        self.file_lines = file_lines
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.parent_class = parent_class
        self.parent_function = parent_function
        self.prev_chunk_id = prev_chunk_id
        self.next_chunk_id = next_chunk_id
        self.chunk_id: Optional[str] = None
        self.is_overlap = is_overlap

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "language": self.language,
            "num_lines": self.end_line - self.start_line + 1,
            "file_lines": self.file_lines,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "parent_class": self.parent_class,
            "parent_function": self.parent_function,
            "prev_chunk_id": self.prev_chunk_id,
            "next_chunk_id": self.next_chunk_id,
        }

    def __repr__(self):
        return (
            f"CodeChunk({self.chunk_type}:{self.name} "
            f"in {self.file_path}:{self.start_line}-{self.end_line})"
        )


class CodeChunker:
    """Intelligently chunks code files based on language and structure."""

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 150,
        overlap_chars: int = 200,
        language_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """
        Initialize chunker with size constraints.

        Args:
            max_chunk_size: Default maximum characters per chunk (fallback for unknown languages)
            min_chunk_size: Default minimum characters per chunk (fallback for unknown languages)
            overlap_chars: Characters of overlap between adjacent chunks for context continuity
            language_configs: Per-language size overrides. Keys are language names,
                values are dicts with optional 'max_size', 'min_size', 'max_file_size'.
                Defaults to DEFAULT_LANGUAGE_CONFIGS if not provided.
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_chars = overlap_chars
        self.language_configs = language_configs if language_configs is not None else DEFAULT_LANGUAGE_CONFIGS.copy()

        # Language detection patterns
        self.language_patterns = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            # Documentation formats
            ".md": "markdown",
            ".markdown": "markdown",
            ".rst": "restructuredtext",
            ".txt": "text",
            ".adoc": "asciidoc",
            ".asciidoc": "asciidoc",
            # Web files
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            # Shell scripts
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
            ".fish": "shell",
            # Config formats
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".xml": "xml",
            ".con": "config",
            ".config": "config",
            ".conf": "config",
            ".cfg": "config",
            ".nginx": "config",
            ".service": "config",
            # Data/query
            ".sql": "sql",
        }

    def _get_effective_config(self, language: str, file_size: int = 0) -> Dict[str, int]:
        """Get effective max/min chunk sizes for a language, with file-size adjustments."""
        lang_config = self.language_configs.get(language, {})
        max_size = lang_config.get("max_size", self.max_chunk_size)
        min_size = lang_config.get("min_size", self.min_chunk_size)

        # Adjust based on file size
        if file_size > 0:
            if file_size < 500:
                max_size = max(max_size // 2, 200)
                min_size = 50
            elif file_size > 20000:
                max_size = min(max_size + 1000, 4000)

        return {"max_size": max_size, "min_size": min_size}

    def _should_skip_file(self, language: str, file_size: int) -> bool:
        """Determine if a file should be skipped entirely."""
        lang_config = self.language_configs.get(language, {})

        # Skip huge JSON config files
        if language == "json":
            max_file = lang_config.get("max_file_size", 50000)
            if file_size > max_file:
                return True

        # Skip tiny files that won't provide good context (< 5 chars is truly empty)
        if file_size < 5:
            return True

        return False

    def chunk_file(self, file_path: Path, content: Optional[str] = None) -> List[CodeChunk]:
        """
        Chunk a code file intelligently based on its language.

        Args:
            file_path: Path to the file
            content: Optional content (if not provided, will read from file)

        Returns:
            List of CodeChunk objects
        """
        if content is None:
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return []

        # Get total lines for metadata
        lines = content.splitlines()
        total_lines = len(lines)

        # Detect language
        language = self._detect_language(file_path, content)

        # Check if file should be skipped
        if self._should_skip_file(language, len(content)):
            logger.debug(f"Skipping {file_path}: file too small or excluded by language config")
            return []

        # Get effective config for this language
        config = self._get_effective_config(language, len(content))
        logger.debug(
            f"Chunking {file_path}: language={language}, "
            f"size={len(content)}, max={config['max_size']}, min={config['min_size']}"
        )

        # Choose chunking strategy based on language
        chunks = []

        try:
            if language == "python":
                chunks = self._chunk_python(content, str(file_path))
            elif language in ["javascript", "typescript"]:
                chunks = self._chunk_javascript(content, str(file_path), language)
            elif language == "go":
                chunks = self._chunk_go(content, str(file_path))
            elif language == "java":
                chunks = self._chunk_java(content, str(file_path))
            elif language == "html":
                chunks = self._chunk_html(content, str(file_path))
            elif language == "shell":
                chunks = self._chunk_shell(content, str(file_path))
            elif language in ["markdown", "text", "restructuredtext", "asciidoc"]:
                chunks = self._chunk_markdown(content, str(file_path), language)
            elif language in ["json", "yaml", "toml", "ini", "xml", "config"]:
                chunks = self._chunk_config(content, str(file_path), language)
            else:
                chunks = self._chunk_generic(content, str(file_path), language)
        except Exception as e:
            logger.warning(
                f"Failed to chunk {file_path} with {language} chunker "
                f"({type(e).__name__}: {e}), falling back to generic"
            )
            chunks = self._chunk_generic(content, str(file_path), language)

        # Ensure chunks meet size constraints (uses language-aware config)
        pre_count = len(chunks)
        chunks = self._enforce_size_constraints(chunks, config["max_size"], config["min_size"])
        if len(chunks) != pre_count:
            logger.debug(
                f"Size enforcement on {file_path}: {pre_count} -> {len(chunks)} chunks "
                f"(max={config['max_size']}, min={config['min_size']})"
            )

        # Add file overview chunk
        if chunks:
            overview = self._create_file_overview(chunks, str(file_path), language, total_lines)
            if overview:
                chunks.insert(0, overview)

        # Set chunk links and indices for all chunks
        if chunks:
            for chunk in chunks:
                if chunk.file_lines is None:
                    chunk.file_lines = total_lines
            chunks = self._set_chunk_links(chunks, str(file_path))

        if chunks:
            logger.debug(
                f"Chunked {file_path}: {len(chunks)} chunks, "
                f"types={set(c.chunk_type for c in chunks)}"
            )
        else:
            logger.info(f"No chunks produced for {file_path} ({language}, {len(content)} chars)")

        return chunks

    def _detect_language(self, file_path: Path, content: Optional[str] = None) -> str:
        """Detect programming language from file extension and content."""
        suffix = file_path.suffix.lower()
        if suffix in self.language_patterns:
            return self.language_patterns[suffix]

        if content is None:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError, IOError):
                return "unknown"

        # Check for shebang
        lines = content.splitlines()
        if lines and lines[0].startswith("#!"):
            shebang = lines[0].lower()
            if "python" in shebang:
                return "python"
            elif "node" in shebang or "javascript" in shebang:
                return "javascript"
            elif "bash" in shebang or "sh" in shebang:
                return "bash"

        # Check for Python-specific patterns in first 50 lines
        sample_lines = lines[:50]
        sample_text = "\n".join(sample_lines)

        python_indicators = [
            "import ", "from ", "def ", "class ", "if __name__",
            "print(", "len(", "range(", "str(", "int(", "float(",
            "self.", "__init__", "__main__", "Exception:", "try:", "except:",
        ]

        python_score = sum(1 for indicator in python_indicators if indicator in sample_text)
        if python_score >= 3:
            return "python"

        if any(
            indicator in sample_text
            for indicator in ["function ", "var ", "const ", "let ", "=>"]
        ):
            return "javascript"

        return "unknown"

    # ──────────────────────────────────────────────────────────
    # Python chunking (AST-based)
    # ──────────────────────────────────────────────────────────

    def _chunk_python(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Python code using AST with enhanced function/class extraction."""
        chunks = []
        lines = content.splitlines()
        total_lines = len(lines)

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}, using fallback chunking")
            fallback = self._chunk_python_fallback(content, file_path)
            if fallback:
                return fallback
            # Fallback found nothing — use generic chunking so content isn't lost
            logger.info(f"Fallback found no definitions in {file_path}, using generic chunker")
            return self._chunk_generic(content, file_path, "python")

        # Extract all functions and classes with their metadata
        extracted_items = self._extract_python_items(tree, lines)

        if extracted_items:
            # Separate class items from non-class items
            class_items = [i for i in extracted_items if i["type"] == "class"]
            non_class_items = [i for i in extracted_items if i["type"] != "class"]

            # Filter out methods — they'll be handled inside _process_python_class
            standalone_items = [i for i in non_class_items if not i.get("parent_class")]

            # Module header: everything before the first item
            all_sorted = sorted(extracted_items, key=lambda x: x["start_line"])
            first_item_line = all_sorted[0]["start_line"] - 1  # 0-based
            if first_item_line > 0:
                header_content = "\n".join(lines[:first_item_line]).strip()
                if header_content:
                    chunks.append(CodeChunk(
                        content=header_content,
                        file_path=file_path,
                        start_line=1,
                        end_line=first_item_line,
                        chunk_type="module_header",
                        name=Path(file_path).stem + " (imports)",
                        language="python",
                        file_lines=total_lines,
                    ))

            # Process classes with the smart handler (class header + method splits)
            for item in class_items:
                for node in ast.walk(tree):
                    if (isinstance(node, ast.ClassDef)
                            and node.name == item["name"]
                            and node.lineno == item["start_line"]):
                        chunks.extend(
                            self._process_python_class(node, lines, file_path, total_lines)
                        )
                        break

            # Process standalone functions via _create_chunks_from_items
            if standalone_items:
                chunks.extend(
                    self._create_chunks_from_items(standalone_items, lines, file_path, total_lines)
                )

            # Capture inter-item and trailing module code gaps
            chunks.extend(
                self._capture_python_gaps(extracted_items, lines, file_path, total_lines)
            )

            # Sort by start line
            chunks.sort(key=lambda x: x.start_line)

        # If no chunks or very few chunks from a large file, add fallback chunks
        if len(chunks) < 3 and total_lines > 200:
            fallback_chunks = self._chunk_python_fallback(content, file_path)
            chunks = self._merge_chunks(chunks, fallback_chunks)

        if chunks:
            return chunks

        fallback = self._chunk_python_fallback(content, file_path)
        if fallback:
            return fallback

        # Last resort: treat the whole file as a single module chunk
        if content.strip():
            return [
                CodeChunk(
                    content=content.strip(),
                    file_path=file_path,
                    start_line=1,
                    end_line=total_lines,
                    chunk_type="module",
                    name=Path(file_path).stem,
                    language="python",
                    file_lines=total_lines,
                )
            ]
        return []

    def _capture_python_gaps(
        self, items: List[Dict], lines: List[str], file_path: str, total_lines: int
    ) -> List[CodeChunk]:
        """Capture inter-item gaps and trailing module code."""
        gap_chunks = []
        sorted_items = sorted(items, key=lambda x: x["start_line"])

        # Track covered ranges from items
        covered = set()
        for item in sorted_items:
            for ln in range(item["start_line"] - 1, min(item["end_line"], len(lines))):
                covered.add(ln)

        # Find gaps — contiguous uncovered lines after the first item
        if not sorted_items:
            return []

        first_line = sorted_items[0]["start_line"] - 1
        gap_start = None

        for ln in range(first_line, len(lines)):
            if ln not in covered:
                if gap_start is None:
                    gap_start = ln
            else:
                if gap_start is not None:
                    gap_content = "\n".join(lines[gap_start:ln]).strip()
                    if gap_content and len(gap_content) > 20:
                        gap_chunks.append(CodeChunk(
                            content=gap_content,
                            file_path=file_path,
                            start_line=gap_start + 1,
                            end_line=ln,
                            chunk_type="module_code",
                            name=f"{Path(file_path).stem} (module code)",
                            language="python",
                            file_lines=total_lines,
                        ))
                    gap_start = None

        # Trailing gap
        if gap_start is not None:
            gap_content = "\n".join(lines[gap_start:]).strip()
            if gap_content and len(gap_content) > 20:
                gap_chunks.append(CodeChunk(
                    content=gap_content,
                    file_path=file_path,
                    start_line=gap_start + 1,
                    end_line=total_lines,
                    chunk_type="module_code",
                    name=f"{Path(file_path).stem} (module code)",
                    language="python",
                    file_lines=total_lines,
                ))

        return gap_chunks

    def _extract_python_items(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Extract all functions and classes with metadata."""
        items = []

        class ItemExtractor(ast.NodeVisitor):

            def __init__(self):
                self.class_stack = []
                self.function_stack = []

            def visit_ClassDef(self, node):
                self.class_stack.append(node.name)

                item = {
                    "type": "class",
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or len(lines),
                    "parent_class": (
                        self.class_stack[-2] if len(self.class_stack) > 1 else None
                    ),
                    "decorators": [getattr(d, "id", "") for d in node.decorator_list if hasattr(d, "id")],
                    "methods": [],
                    "docstring": ast.get_docstring(node) or "",
                }

                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        item["methods"].append(child.name)

                items.append(item)

                self.generic_visit(node)
                self.class_stack.pop()

            def visit_FunctionDef(self, node):
                self._visit_function(node, "function")

            def visit_AsyncFunctionDef(self, node):
                self._visit_function(node, "async_function")

            def _visit_function(self, node, func_type):
                self.function_stack.append(node.name)

                item = {
                    "type": func_type,
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or len(lines),
                    "parent_class": self.class_stack[-1] if self.class_stack else None,
                    "parent_function": (
                        self.function_stack[-2] if len(self.function_stack) > 1 else None
                    ),
                    "decorators": [getattr(d, "id", "") for d in node.decorator_list if hasattr(d, "id")],
                    "args": [arg.arg for arg in node.args.args],
                    "is_method": bool(self.class_stack),
                    "docstring": ast.get_docstring(node) or "",
                }

                items.append(item)

                self.generic_visit(node)
                self.function_stack.pop()

        extractor = ItemExtractor()
        extractor.visit(tree)

        items.sort(key=lambda x: x["start_line"])
        return items

    def _create_chunks_from_items(
        self, items: List[Dict], lines: List[str], file_path: str, total_lines: int
    ) -> List[CodeChunk]:
        """Create chunks from extracted AST items (standalone functions only)."""
        chunks = []

        for item in sorted(items, key=lambda x: x["start_line"]):
            start_line = item["start_line"] - 1  # 0-based
            end_line = min(item["end_line"], len(lines)) - 1

            chunk_content = "\n".join(lines[start_line: end_line + 1])

            # Enrich name with docstring first line
            docstring = item.get("docstring", "")
            name = item["name"]
            if docstring:
                doc_first = docstring.strip().split("\n")[0][:60]
                name = f"{item['name']}: {doc_first}"

            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line + 1,
                end_line=end_line + 1,
                chunk_type=item["type"],
                name=name,
                language="python",
                parent_class=item.get("parent_class"),
                parent_function=item.get("parent_function"),
                file_lines=total_lines,
            )
            chunks.append(chunk)

        return chunks

    def _process_python_class(
        self, node: ast.ClassDef, lines: List[str], file_path: str, total_lines: int
    ) -> List[CodeChunk]:
        """Process a Python class with smart chunking: class header + individual methods."""
        chunks = []

        class_start = node.lineno - 1

        # Find where class docstring ends
        docstring_end = class_start
        class_docstring = ast.get_docstring(node)
        if class_docstring and node.body:
            first_stmt = node.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, ast.Constant
            ):
                docstring_end = (first_stmt.end_lineno or class_start + 1) - 1

        # Find __init__ method if exists
        init_method = None
        init_end = docstring_end
        for child in node.body:
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == "__init__"
            ):
                init_method = child
                init_end = (child.end_lineno or init_end + 1) - 1
                break

        # Collect method signatures for preview
        method_signatures = []
        for child in node.body:
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name != "__init__"
            ):
                sig_line = lines[child.lineno - 1].strip()
                method_signatures.append(f"    # {sig_line}")

        # Create class header chunk: class def + docstring + __init__ + method preview
        if init_method:
            header_lines = lines[class_start: init_end + 1]
        else:
            header_lines = lines[class_start: docstring_end + 1]

        if method_signatures:
            header_content = "\n".join(header_lines)
            if not header_content.rstrip().endswith(":"):
                header_content += "\n"
            header_content += "\n    # Method signatures:\n" + "\n".join(
                method_signatures[:5]
            )
            if len(method_signatures) > 5:
                header_content += f"\n    # ... and {len(method_signatures) - 5} more methods"
        else:
            header_content = "\n".join(header_lines)

        header_end = init_end + 1 if init_method else docstring_end + 1
        chunks.append(
            CodeChunk(
                content=header_content,
                file_path=file_path,
                start_line=class_start + 1,
                end_line=header_end,
                chunk_type="class",
                name=node.name,
                language="python",
                file_lines=total_lines,
            )
        )

        # Process each method as separate chunk
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name == "__init__":
                    continue  # Already included in class header

                method_chunk = self._process_python_function(
                    child,
                    lines,
                    file_path,
                    is_method=True,
                    parent_class=node.name,
                    total_lines=total_lines,
                )
                chunks.append(method_chunk)

        return chunks

    def _process_python_function(
        self,
        node,
        lines: List[str],
        file_path: str,
        is_method: bool = False,
        parent_class: Optional[str] = None,
        total_lines: Optional[int] = None,
    ) -> CodeChunk:
        """Process a Python function or method, including its decorators and docstring."""
        start_line = node.lineno - 1
        end_line = (node.end_lineno or len(lines)) - 1

        # Include any decorators
        if hasattr(node, "decorator_list") and node.decorator_list:
            first_decorator = node.decorator_list[0]
            if hasattr(first_decorator, "lineno"):
                start_line = min(start_line, first_decorator.lineno - 1)

        function_content = "\n".join(lines[start_line: end_line + 1])

        return CodeChunk(
            content=function_content,
            file_path=file_path,
            start_line=start_line + 1,
            end_line=end_line + 1,
            chunk_type="method" if is_method else "function",
            name=node.name,
            language="python",
            parent_class=parent_class,
            file_lines=total_lines,
        )

    def _chunk_python_fallback(self, content: str, file_path: str) -> List[CodeChunk]:
        """Fallback chunking for Python files with syntax errors or no AST items.
        Only matches top-level (indent 0) definitions."""
        chunks = []
        lines = content.splitlines()

        patterns = [
            (r"^(class\s+\w+.*?:)", "class"),
            (r"^(def\s+\w+.*?:)", "function"),
            (r"^(async\s+def\s+\w+.*?:)", "async_function"),
        ]

        matches = []
        for i, line in enumerate(lines):
            # Only match top-level definitions (no leading whitespace)
            if not line or line[0].isspace():
                continue
            for pattern, item_type in patterns:
                if re.match(pattern, line):
                    if item_type == "class":
                        name_match = re.match(r"class\s+(\w+)", line)
                    else:
                        name_match = re.match(r"(?:async\s+)?def\s+(\w+)", line)

                    if name_match:
                        matches.append(
                            {
                                "line": i,
                                "type": item_type,
                                "name": name_match.group(1),
                            }
                        )

        for i, match in enumerate(matches):
            start_line = match["line"]

            # Find end line by looking for next top-level item
            end_line = len(lines) - 1
            for j in range(start_line + 1, len(lines)):
                line = lines[j]
                if line.strip() and not line[0].isspace():
                    end_line = j - 1
                    break

            chunk_content = "\n".join(lines[start_line: end_line + 1])
            if chunk_content.strip():
                chunks.append(
                    CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=start_line + 1,
                        end_line=end_line + 1,
                        chunk_type=match["type"],
                        name=match["name"],
                        language="python",
                    )
                )

        return chunks

    def _merge_chunks(
        self, primary_chunks: List[CodeChunk], fallback_chunks: List[CodeChunk]
    ) -> List[CodeChunk]:
        """Merge chunks, avoiding duplicates."""
        if not primary_chunks:
            return fallback_chunks
        if not fallback_chunks:
            return primary_chunks

        merged = primary_chunks[:]
        primary_ranges = [(chunk.start_line, chunk.end_line) for chunk in primary_chunks]

        for fallback_chunk in fallback_chunks:
            overlaps = False
            for start, end in primary_ranges:
                if not (fallback_chunk.end_line < start or fallback_chunk.start_line > end):
                    overlaps = True
                    break

            if not overlaps:
                merged.append(fallback_chunk)

        merged.sort(key=lambda x: x.start_line)
        return merged

    # ──────────────────────────────────────────────────────────
    # JavaScript/TypeScript chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_javascript(
        self, content: str, file_path: str, language: str
    ) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code using regex patterns."""
        chunks = []
        lines = content.splitlines()

        patterns = {
            "function": r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "arrow_function": (
                r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*"
                r"(?:async\s+)?\([^)]*\)\s*=>"
            ),
            "class": r"^\s*(?:export\s+)?class\s+(\w+)",
            "method": r"^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*{",
        }

        matches = []
        for i, line in enumerate(lines):
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    matches.append((i, chunk_type, name))
                    break

        matches.sort(key=lambda x: x[0])

        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            max_end = matches[i + 1][0] - 1 if i + 1 < len(matches) else len(lines) - 1
            actual_end = self._find_block_end(lines, start_line, max_end)

            chunk_content = "\n".join(lines[start_line: actual_end + 1])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start_line + 1,
                    end_line=actual_end + 1,
                    chunk_type=chunk_type,
                    name=name,
                    language=language,
                )
            )

        if not chunks:
            return self._chunk_generic(content, file_path, language)

        return chunks

    # ──────────────────────────────────────────────────────────
    # Go chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_go(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Go code by functions and types."""
        chunks = []
        lines = content.splitlines()

        patterns = {
            "function": r"^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(",
            "type": r"^\s*type\s+(\w+)\s+(?:struct|interface)\s*{",
            "method": r"^\s*func\s+\((\w+)\s+\*?\w+\)\s+(\w+)\s*\(",
        }

        matches = []
        for i, line in enumerate(lines):
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    if chunk_type == "method":
                        name = f"{match.group(1)}.{match.group(2)}"
                    else:
                        name = match.group(1)
                    matches.append((i, chunk_type, name))
                    break

        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            max_end = matches[i + 1][0] - 1 if i + 1 < len(matches) else len(lines) - 1
            actual_end = self._find_block_end(lines, start_line, max_end)

            chunk_content = "\n".join(lines[start_line: actual_end + 1])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start_line + 1,
                    end_line=actual_end + 1,
                    chunk_type=chunk_type,
                    name=name,
                    language="go",
                )
            )

        return chunks if chunks else self._chunk_generic(content, file_path, "go")

    # ──────────────────────────────────────────────────────────
    # Java chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_java(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Java code by classes and methods."""
        chunks = []
        lines = content.splitlines()

        class_pattern = (
            r"^\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)"
        )
        # Require return type before method name; reject lines ending with ; (field decls)
        method_pattern = (
            r"^\s*(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:final\s+)?"
            r"(?:void|int|long|double|float|boolean|char|byte|short|String|\w+(?:<[^>]+>)?)\s+"
            r"(\w+)\s*\([^;]*$"
        )
        # Constructors: access modifier + ClassName(
        constructor_pattern = (
            r"^\s*(?:public|private|protected)\s+(\w+)\s*\("
        )

        matches = []
        for i, line in enumerate(lines):
            class_match = re.match(class_pattern, line)
            if class_match:
                matches.append((i, "class", class_match.group(1)))
                continue

            method_match = re.match(method_pattern, line)
            if method_match:
                matches.append((i, "method", method_match.group(1)))
                continue

            constructor_match = re.match(constructor_pattern, line)
            if constructor_match:
                # Only match constructors not already matched as class
                name = constructor_match.group(1)
                if not any(m[2] == name and m[1] == "class" for m in matches):
                    matches.append((i, "constructor", name))

        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            max_end = matches[i + 1][0] - 1 if i + 1 < len(matches) else len(lines) - 1
            actual_end = self._find_block_end(lines, start_line, max_end)

            chunk_content = "\n".join(lines[start_line: actual_end + 1])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start_line + 1,
                    end_line=actual_end + 1,
                    chunk_type=chunk_type,
                    name=name,
                    language="java",
                )
            )

        return chunks if chunks else self._chunk_generic(content, file_path, "java")

    # ──────────────────────────────────────────────────────────
    # String/comment-aware brace counting (shared by JS, Go, Java)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _count_braces_safe(line: str) -> int:
        """Count net braces ({-}) ignoring strings and single-line comments."""
        net = 0
        in_string: Optional[str] = None
        i = 0
        while i < len(line):
            c = line[i]
            if in_string:
                if c == '\\':
                    i += 2
                    continue
                if c == in_string:
                    in_string = None
            else:
                if c in ('"', "'", '`'):
                    in_string = c
                elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    break  # rest is single-line comment
                elif c == '{':
                    net += 1
                elif c == '}':
                    net -= 1
            i += 1
        return net

    def _find_block_end(self, lines: List[str], start_line: int, max_end: int) -> int:
        """Find the end of a brace-delimited block, handling strings and comments.

        Tracks multi-line /* */ comments across lines.
        """
        brace_count = 0
        in_block_comment = False

        for j in range(start_line, min(max_end + 1, len(lines))):
            line = lines[j]

            # Process multi-line comments
            processed_line = ""
            i = 0
            while i < len(line):
                if in_block_comment:
                    if line[i:i + 2] == "*/":
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue
                else:
                    if line[i:i + 2] == "/*":
                        in_block_comment = True
                        i += 2
                        continue
                    processed_line += line[i]
                    i += 1

            brace_count += self._count_braces_safe(processed_line)
            if brace_count == 0 and j > start_line:
                return j

        return max_end

    # ──────────────────────────────────────────────────────────
    # Shell script chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_shell(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk shell scripts by function boundaries."""
        chunks = []
        lines = content.splitlines()

        patterns = {
            "function": r"^([\w_]+)\s*\(\)\s*\{",
            "function_keyword": r"^function\s+([\w_]+)",
        }

        matches = []
        for i, line in enumerate(lines):
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    matches.append((i, "function", name))
                    break

        matches.sort(key=lambda x: x[0])

        # Capture preamble (shebang, global vars, sourcing) before first function
        if matches and matches[0][0] > 0:
            preamble = "\n".join(lines[: matches[0][0]])
            if preamble.strip():
                chunks.append(
                    CodeChunk(
                        content=preamble,
                        file_path=file_path,
                        start_line=1,
                        end_line=matches[0][0],
                        chunk_type="module_header",
                        name="shell_preamble",
                        language="shell",
                    )
                )

        for i in range(len(matches)):
            start_line = matches[i][0]
            name = matches[i][2]

            max_end = matches[i + 1][0] - 1 if i + 1 < len(matches) else len(lines) - 1
            actual_end = self._find_block_end(lines, start_line, max_end)

            chunk_content = "\n".join(lines[start_line: actual_end + 1])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start_line + 1,
                    end_line=actual_end + 1,
                    chunk_type="function",
                    name=name,
                    language="shell",
                )
            )

        if not chunks:
            return self._chunk_generic(content, file_path, "shell")

        return chunks

    # ──────────────────────────────────────────────────────────
    # HTML chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_html(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk HTML with tag-aware structural splitting."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.debug("BeautifulSoup not available, falling back to generic chunking")
            return self._chunk_generic(content, file_path, "html")

        try:
            soup = BeautifulSoup(content, "html.parser")
        except Exception:
            return self._chunk_generic(content, file_path, "html")

        # Remove noise tags
        for tag_name in ["script", "style", "nav", "footer"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        chunks = []
        current_heading = None
        current_text_parts = []
        current_start = 1

        def _flush_text():
            nonlocal current_text_parts, current_start
            if not current_text_parts:
                return
            text = "\n\n".join(current_text_parts)
            if text.strip():
                chunks.append(
                    CodeChunk(
                        content=text.strip(),
                        file_path=file_path,
                        start_line=current_start,
                        end_line=current_start,
                        chunk_type="section",
                        name=(current_heading or "content")[:50],
                        language="html",
                    )
                )
            current_text_parts = []

        # Walk top-level block elements
        block_tags = {"div", "section", "article", "main", "aside",
                      "table", "pre", "blockquote", "ul", "ol", "dl",
                      "h1", "h2", "h3", "h4", "h5", "h6", "p", "form"}

        for element in soup.find_all(True):
            if element.name not in block_tags:
                continue
            # Skip nested block elements (only process top-level occurrences)
            if element.parent and element.parent.name in block_tags and element.parent.name != "[document]":
                continue

            if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                _flush_text()
                current_heading = element.get_text(strip=True)
                current_start = len(chunks) + 1
                continue

            if element.name == "table":
                _flush_text()
                table_text = element.get_text(separator=" | ", strip=True)
                if table_text.strip():
                    chunks.append(
                        CodeChunk(
                            content=table_text,
                            file_path=file_path,
                            start_line=len(chunks) + 1,
                            end_line=len(chunks) + 1,
                            chunk_type="table",
                            name=(current_heading or "table")[:50],
                            language="html",
                        )
                    )
                continue

            if element.name == "pre":
                _flush_text()
                code_text = element.get_text()
                if code_text.strip():
                    chunks.append(
                        CodeChunk(
                            content=code_text.strip(),
                            file_path=file_path,
                            start_line=len(chunks) + 1,
                            end_line=len(chunks) + 1,
                            chunk_type="code_block",
                            name=(current_heading or "code")[:50],
                            language="html",
                        )
                    )
                continue

            # Regular block element — extract text
            text = element.get_text(separator="\n", strip=True)
            if text:
                current_text_parts.append(text)

        _flush_text()

        if not chunks:
            return self._chunk_generic(content, file_path, "html")

        return chunks

    # ──────────────────────────────────────────────────────────
    # Generic / fallback chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_generic(self, content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Generic chunking by empty lines and character-based size constraints."""
        chunks = []
        lines = content.splitlines()
        config = self._get_effective_config(language, len(content))
        max_size = config["max_size"]
        min_size = config["min_size"]

        current_chunk = []
        current_chars = 0
        current_start = 0

        for i, line in enumerate(lines):
            current_chunk.append(line)
            current_chars += len(line) + 1

            should_chunk = False

            if not line.strip() and current_chars >= min_size:
                should_chunk = True

            if current_chars >= max_size:
                should_chunk = True

            if i == len(lines) - 1 and current_chunk:
                should_chunk = True

            if should_chunk and current_chunk:
                chunk_content = "\n".join(current_chunk).strip()
                if chunk_content:
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            start_line=current_start + 1,
                            end_line=current_start + len(current_chunk),
                            chunk_type="code_block",
                            name=f"block_{len(chunks) + 1}",
                            language=language,
                        )
                    )

                current_chunk = []
                current_chars = 0
                current_start = i + 1

        return chunks

    # ──────────────────────────────────────────────────────────
    # Size enforcement with overlap
    # ──────────────────────────────────────────────────────────

    def _enforce_size_constraints(
        self,
        chunks: List[CodeChunk],
        max_size: Optional[int] = None,
        min_size: Optional[int] = None,
    ) -> List[CodeChunk]:
        """
        Ensure all chunks meet size constraints using character counts.
        Split too-large chunks at line boundaries.
        Merge too-small ones only within same semantic boundary.
        Applies overlap_chars between split sub-chunks.
        """
        if max_size is None:
            max_size = self.max_chunk_size
        if min_size is None:
            min_size = self.min_chunk_size

        result = []

        for chunk in chunks:
            char_count = len(chunk.content)

            if char_count > max_size:
                # Split oversized chunk at line boundaries with overlap
                lines = chunk.content.splitlines()
                current_sub = []
                current_chars = 0
                sub_start = chunk.start_line
                prev_sub_tail = ""  # trailing content for overlap

                for j, line in enumerate(lines):
                    line_chars = len(line) + 1
                    if current_chars + line_chars > max_size and current_sub:
                        sub_content = "\n".join(current_sub)
                        result.append(
                            CodeChunk(
                                content=sub_content,
                                file_path=chunk.file_path,
                                start_line=sub_start,
                                end_line=sub_start + len(current_sub) - 1,
                                chunk_type=chunk.chunk_type,
                                name=chunk.name,
                                language=chunk.language,
                            )
                        )
                        # Capture tail for overlap
                        prev_sub_tail = sub_content[-self.overlap_chars:] if self.overlap_chars > 0 else ""

                        current_sub = []
                        current_chars = 0
                        sub_start = chunk.start_line + j

                        # Prepend overlap from previous sub-chunk
                        if prev_sub_tail:
                            current_sub.append(prev_sub_tail)
                            current_chars += len(prev_sub_tail) + 1

                    current_sub.append(line)
                    current_chars += line_chars

                if current_sub:
                    sub_content = "\n".join(current_sub)
                    result.append(
                        CodeChunk(
                            content=sub_content,
                            file_path=chunk.file_path,
                            start_line=sub_start,
                            end_line=chunk.end_line,
                            chunk_type=chunk.chunk_type,
                            name=chunk.name,
                            language=chunk.language,
                        )
                    )

            elif char_count < min_size and result:
                prev = result[-1]

                # Never merge across section boundaries
                is_section_boundary = (
                    chunk.chunk_type == "section"
                    or prev.chunk_type == "section"
                )

                merged_size = len(prev.content) + char_count + 1
                can_merge = (
                    not is_section_boundary
                    and merged_size <= max_size
                )

                if can_merge:
                    prev.content += "\n" + chunk.content
                    prev.end_line = chunk.end_line
                else:
                    result.append(chunk)

            else:
                result.append(chunk)

        return result

    # ──────────────────────────────────────────────────────────
    # Markdown chunking
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _protect_fenced_blocks(content: str) -> Tuple[str, List[str]]:
        """Pre-scan for fenced code blocks and replace with placeholders.

        This must run BEFORE splitting on \\n\\n so that code blocks
        containing blank lines are not fragmented.

        Returns:
            (modified_content, list_of_extracted_blocks)
        """
        blocks = []
        # Match fenced code blocks: opening ``` (with optional lang), content, closing ```
        # The content can contain blank lines.
        pattern = re.compile(r"(```[^\n]*\n[\s\S]*?\n```)", re.MULTILINE)

        def replacer(match):
            idx = len(blocks)
            blocks.append(match.group(1))
            return f"\x00CODEBLOCK_{idx}\x00"

        modified = pattern.sub(replacer, content)
        return modified, blocks

    @staticmethod
    def _restore_fenced_blocks(text: str, blocks: List[str]) -> str:
        """Restore placeholder tokens back to original code block content."""
        for i, block in enumerate(blocks):
            text = text.replace(f"\x00CODEBLOCK_{i}\x00", block)
        return text

    @staticmethod
    def _protect_tables(content: str) -> Tuple[str, List[str]]:
        """Pre-scan for markdown tables and replace with placeholders.

        Must run AFTER _protect_fenced_blocks (so pipes inside code blocks
        are already replaced) and BEFORE splitting on \\n\\n.

        A table is consecutive lines starting with |, containing a separator
        row that matches |---|.
        """
        tables = []

        def _replace_table(match):
            block = match.group(0)
            # Only protect if it contains a separator row
            if re.search(r"\|[\s\-:]+\|", block):
                idx = len(tables)
                tables.append(block.rstrip("\n"))
                # Ensure placeholder is surrounded by \n\n so it becomes its own paragraph
                return f"\n\n\x00TABLE_{idx}\x00\n\n"
            return block

        pattern = re.compile(r"((?:^[ \t]*\|.+\|[ \t]*$\n?){2,})", re.MULTILINE)
        modified = pattern.sub(_replace_table, content)
        return modified, tables

    @staticmethod
    def _restore_tables(text: str, tables: List[str]) -> str:
        """Restore table placeholder tokens back to original content."""
        for i, table in enumerate(tables):
            text = text.replace(f"\x00TABLE_{i}\x00", table)
        return text

    @staticmethod
    def _compute_paragraph_positions(content: str, paragraphs: List[str]) -> List[int]:
        """Compute the 1-based starting line number of each paragraph.

        Scans the original content to find where each paragraph begins,
        avoiding the line-drift caused by assuming +2 per gap.
        """
        positions = []
        search_start = 0
        for para in paragraphs:
            if not para:
                # Empty paragraph from split — find it by advancing past \n\n
                positions.append(content[:search_start].count('\n') + 1)
                # Advance past the empty region
                search_start += 2  # the \n\n that produced this empty string
                continue
            idx = content.find(para, search_start)
            if idx == -1:
                # Fallback: use current position
                positions.append(content[:search_start].count('\n') + 1)
            else:
                positions.append(content[:idx].count('\n') + 1)
                search_start = idx + len(para)
        return positions

    def _chunk_markdown(
        self, content: str, file_path: str, language: str = "markdown"
    ) -> List[CodeChunk]:
        """
        Chunk markdown/text files using paragraph-based splitting with
        structure preservation.

        Key behaviours:
        - Fenced code blocks (```) are protected before splitting — never fragmented
        - Split on double newlines (paragraphs)
        - Headers merge downward into their section content
        - Character-based size limits from language config
        """
        chunks = []
        total_lines = len(content.splitlines())
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
        config = self._get_effective_config(language, len(content))
        max_size = config["max_size"]

        # Protect fenced code blocks before splitting
        protected_content, code_blocks = self._protect_fenced_blocks(content)

        # Warn about unclosed code blocks (odd number of ``` fences remaining)
        remaining_fences = protected_content.count("```")
        if remaining_fences > 0:
            logger.warning(
                f"Unclosed code block in {file_path}: {remaining_fences} unmatched "
                f"fence(s) after extracting {len(code_blocks)} complete block(s)"
            )

        # Protect markdown tables before splitting
        protected_content, tables = self._protect_tables(protected_content)

        def _restore_all(text: str) -> str:
            """Restore both code block and table placeholders."""
            text = self._restore_fenced_blocks(text, code_blocks)
            text = self._restore_tables(text, tables)
            return text

        # Split into paragraphs
        paragraphs = protected_content.split("\n\n")

        # Pre-compute paragraph start positions from original content
        positions = self._compute_paragraph_positions(protected_content, paragraphs)

        current_parts: List[str] = []
        current_chars = 0
        current_start_line = 1
        section_title = Path(file_path).stem

        consumed = set()  # Indices of paragraphs consumed by header-merge

        for i, para in enumerate(paragraphs):
            if i in consumed:
                continue

            para_stripped = para.strip()
            if not para_stripped:
                continue

            para_chars = len(para)
            start_line = positions[i] if i < len(positions) else current_start_line

            # Check if this is a placeholder for a code block or table
            is_code_placeholder = para_stripped.startswith("\x00CODEBLOCK_") and para_stripped.endswith("\x00")
            is_table_placeholder = para_stripped.startswith("\x00TABLE_") and para_stripped.endswith("\x00")

            # Check for standalone header
            header_match = header_pattern.match(para_stripped)
            is_standalone_header = (
                header_match
                and para_chars < 100
                and "\n" not in para_stripped
            )

            # Standalone header merges with next non-code paragraph
            if is_standalone_header and i + 1 < len(paragraphs):
                next_idx = i + 1
                while next_idx in consumed and next_idx < len(paragraphs):
                    next_idx += 1
                next_text = paragraphs[next_idx].strip() if next_idx < len(paragraphs) else ""
                next_is_code = next_text.startswith("\x00CODEBLOCK_") or next_text.startswith("\x00TABLE_")
                can_merge = next_text and not next_is_code

                # Flush current chunk before starting new section
                if current_parts:
                    chunk_content = "\n\n".join(current_parts).strip()
                    chunk_content = _restore_all(chunk_content)
                    end_line = start_line - 1 if start_line > current_start_line else current_start_line
                    chunks.append(self._make_md_chunk(
                        chunk_content, file_path, language,
                        current_start_line, end_line,
                        section_title, total_lines,
                    ))
                    current_parts = []
                    current_chars = 0

                assert header_match is not None  # guarded by is_standalone_header
                section_title = header_match.group(2).strip()
                current_start_line = start_line

                if can_merge:
                    merged = para + "\n\n" + paragraphs[next_idx]
                    current_parts.append(merged)
                    current_chars += len(merged)
                    consumed.add(next_idx)
                    continue
                else:
                    # Header becomes its own part; next (code block) handled on its iteration
                    current_parts.append(para)
                    current_chars += para_chars
                    continue

            # Header without merge — still starts a new section
            if header_match and not is_standalone_header:
                if current_parts:
                    chunk_content = "\n\n".join(current_parts).strip()
                    chunk_content = _restore_all(chunk_content)
                    chunks.append(self._make_md_chunk(
                        chunk_content, file_path, language,
                        current_start_line, start_line - 1,
                        section_title, total_lines,
                    ))
                    current_parts = []
                    current_chars = 0
                    current_start_line = start_line

                section_title = header_match.group(2).strip()

            # Code block placeholders get their own chunk (never split)
            if is_code_placeholder:
                if current_parts:
                    chunk_content = "\n\n".join(current_parts).strip()
                    chunk_content = _restore_all(chunk_content)
                    chunks.append(self._make_md_chunk(
                        chunk_content, file_path, language,
                        current_start_line, start_line - 1,
                        section_title, total_lines,
                    ))
                    current_parts = []
                    current_chars = 0

                restored = _restore_all(para_stripped)
                restored_lines = restored.count("\n") + 1
                chunks.append(CodeChunk(
                    content=restored,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=start_line + restored_lines - 1,
                    chunk_type="code_block",
                    name=f"{section_title} (code)" if section_title else "code_block",
                    language=language,
                    file_lines=total_lines,
                ))
                current_start_line = start_line + restored_lines
                continue

            # Table placeholders get their own chunk (never split)
            if is_table_placeholder:
                if current_parts:
                    chunk_content = "\n\n".join(current_parts).strip()
                    chunk_content = _restore_all(chunk_content)
                    chunks.append(self._make_md_chunk(
                        chunk_content, file_path, language,
                        current_start_line, start_line - 1,
                        section_title, total_lines,
                    ))
                    current_parts = []
                    current_chars = 0

                restored = self._restore_tables(para_stripped, tables)
                restored_lines = restored.count("\n") + 1
                chunks.append(CodeChunk(
                    content=restored,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=start_line + restored_lines - 1,
                    chunk_type="table",
                    name=f"{section_title} (table)" if section_title else "table",
                    language=language,
                    file_lines=total_lines,
                ))
                current_start_line = start_line + restored_lines
                continue

            # Size check — flush if adding this para would exceed max
            if current_chars + para_chars > max_size and current_parts:
                chunk_content = "\n\n".join(current_parts).strip()
                chunk_content = _restore_all(chunk_content)
                chunks.append(self._make_md_chunk(
                    chunk_content, file_path, language,
                    current_start_line, start_line - 1,
                    section_title, total_lines,
                ))
                current_parts = []
                current_chars = 0
                current_start_line = start_line

            current_parts.append(para)
            current_chars += para_chars

        # Final chunk
        if current_parts:
            chunk_content = "\n\n".join(current_parts).strip()
            chunk_content = _restore_all(chunk_content)
            chunks.append(self._make_md_chunk(
                chunk_content, file_path, language,
                current_start_line, total_lines,
                section_title, total_lines,
            ))

        # Fallback: whole file as one chunk if nothing produced
        if not chunks and content.strip():
            chunks.append(CodeChunk(
                content=content.strip(),
                file_path=file_path,
                start_line=1,
                end_line=total_lines,
                chunk_type="document",
                name=Path(file_path).stem,
                language=language,
                file_lines=total_lines,
            ))

        # NOTE: _set_chunk_links is NOT called here — chunk_file handles it uniformly
        return chunks

    @staticmethod
    def _make_md_chunk(
        content: str, file_path: str, language: str,
        start_line: int, end_line: int, section_title: str,
        total_lines: int,
    ) -> CodeChunk:
        """Create a markdown chunk from content."""
        return CodeChunk(
            content=content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            chunk_type="section",
            name=section_title[:50] if section_title else "content",
            language=language,
            file_lines=total_lines,
        )

    # ──────────────────────────────────────────────────────────
    # Config file chunking
    # ──────────────────────────────────────────────────────────

    def _chunk_config(
        self, content: str, file_path: str, language: str = "config"
    ) -> List[CodeChunk]:
        """Chunk configuration files by sections."""
        chunks = []
        lines = content.splitlines()

        if language == "json":
            chunks.append(
                CodeChunk(
                    content=content,
                    file_path=file_path,
                    start_line=1,
                    end_line=len(lines),
                    chunk_type="config",
                    name=Path(file_path).stem,
                    language=language,
                )
            )
        else:
            current_section = []
            current_start = 0
            section_name = "config"

            section_patterns = {
                "ini": re.compile(r"^\[(.+)\]$"),
                "toml": re.compile(r"^\[(.+)\]$"),
                "yaml": re.compile(r"^(\w+):$"),
            }

            pattern = section_patterns.get(language)

            for i, line in enumerate(lines):
                is_section = False

                new_section_name = section_name
                if pattern:
                    match = pattern.match(line.strip())
                    if match:
                        is_section = True
                        new_section_name = match.group(1)

                if is_section and current_section:
                    chunk_content = "\n".join(current_section)
                    if chunk_content.strip():
                        chunk = CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            start_line=current_start + 1,
                            end_line=current_start + len(current_section),
                            chunk_type="config_section",
                            name=section_name,
                            language=language,
                        )
                        chunks.append(chunk)

                    current_section = [line]
                    current_start = i
                    section_name = new_section_name
                else:
                    current_section.append(line)

            if current_section:
                chunk_content = "\n".join(current_section)
                if chunk_content.strip():
                    chunk = CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=current_start + 1,
                        end_line=len(lines),
                        chunk_type="config_section",
                        name=section_name,
                        language=language,
                    )
                    chunks.append(chunk)

        if not chunks and content.strip():
            chunks.append(
                CodeChunk(
                    content=content,
                    file_path=file_path,
                    start_line=1,
                    end_line=len(lines),
                    chunk_type="config",
                    name=Path(file_path).stem,
                    language=language,
                )
            )

        return chunks

    # ──────────────────────────────────────────────────────────
    # File overview and chunk linking
    # ──────────────────────────────────────────────────────────

    def _create_file_overview(
        self, chunks: List[CodeChunk], file_path: str, language: str, total_lines: int
    ) -> Optional[CodeChunk]:
        """Create a file overview chunk listing all functions/classes/sections."""
        if not chunks:
            return None

        names_by_type = {}
        for chunk in chunks:
            ct = chunk.chunk_type
            if ct in ("module_header", "module_code", "file_overview"):
                continue
            name = chunk.name.split(":")[0].strip() if chunk.name else None
            if name:
                names_by_type.setdefault(ct, []).append(name)

        if not names_by_type:
            return None

        parts = [f"File: {Path(file_path).name} ({language})"]
        for chunk_type, names in names_by_type.items():
            label = chunk_type.replace("_", " ").title()
            parts.append(f"{label} ({len(names)}): {', '.join(names[:15])}")
            if len(names) > 15:
                parts.append(f"  ... and {len(names) - 15} more")

        overview_text = "\n".join(parts)

        return CodeChunk(
            content=overview_text,
            file_path=file_path,
            start_line=1,
            end_line=1,
            chunk_type="file_overview",
            name=f"{Path(file_path).stem} (overview)",
            language=language,
            file_lines=total_lines,
        )

    def _set_chunk_links(self, chunks: List[CodeChunk], file_path: str) -> List[CodeChunk]:
        """Set chunk indices and prev/next links for navigation."""
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total_chunks
            chunk.chunk_id = f"{Path(file_path).stem}_{i}"

            if i > 0:
                chunk.prev_chunk_id = f"{Path(file_path).stem}_{i - 1}"

            if i < total_chunks - 1:
                chunk.next_chunk_id = f"{Path(file_path).stem}_{i + 1}"

        return chunks

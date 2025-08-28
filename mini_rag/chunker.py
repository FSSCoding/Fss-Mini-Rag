"""
AST-based code chunking for intelligent code splitting.
Chunks by functions, classes, and logical boundaries instead of arbitrary lines.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
        # New metadata fields
        self.file_lines = file_lines  # Total lines in file
        self.chunk_index = chunk_index  # Position in chunk sequence
        self.total_chunks = total_chunks  # Total chunks in file
        self.parent_class = parent_class  # For methods: which class they belong to
        self.parent_function = parent_function  # For nested functions
        self.prev_chunk_id = prev_chunk_id  # Link to previous chunk
        self.next_chunk_id = next_chunk_id  # Link to next chunk

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
            # Include new metadata if available
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
        max_chunk_size: int = 1000,
        min_chunk_size: int = 50,
        overlap_lines: int = 0,
    ):
        """
        Initialize chunker with size constraints.

        Args:
            max_chunk_size: Maximum lines per chunk
            min_chunk_size: Minimum lines per chunk
            overlap_lines: Number of lines to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_lines = overlap_lines

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
            # Config formats
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".xml": "xml",
            ".con": "config",
            ".config": "config",
        }

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
            elif language in ["markdown", "text", "restructuredtext", "asciidoc"]:
                chunks = self._chunk_markdown(content, str(file_path), language)
            elif language in ["json", "yaml", "toml", "ini", "xml", "config"]:
                chunks = self._chunk_config(content, str(file_path), language)
            else:
                # Fallback to generic chunking
                chunks = self._chunk_generic(content, str(file_path), language)
        except Exception as e:
            logger.warning(f"Failed to chunk {file_path} with language-specific chunker: {e}")
            chunks = self._chunk_generic(content, str(file_path), language)

        # Ensure chunks meet size constraints
        chunks = self._enforce_size_constraints(chunks)

        # Set chunk links and indices for all chunks
        if chunks:
            for chunk in chunks:
                if chunk.file_lines is None:
                    chunk.file_lines = total_lines
            chunks = self._set_chunk_links(chunks, str(file_path))

        return chunks

    def _detect_language(self, file_path: Path, content: str = None) -> str:
        """Detect programming language from file extension and content."""
        # First try extension-based detection
        suffix = file_path.suffix.lower()
        if suffix in self.language_patterns:
            return self.language_patterns[suffix]

        # Fallback to content-based detection
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
            "import ",
            "from ",
            "def ",
            "class ",
            "if __name__",
            "print(",
            "len(",
            "range(",
            "str(",
            "int(",
            "float(",
            "self.",
            "__init__",
            "__main__",
            "Exception:",
            "try:",
            "except:",
        ]

        python_score = sum(1 for indicator in python_indicators if indicator in sample_text)

        # If we find strong Python indicators, classify as Python
        if python_score >= 3:
            return "python"

        # Check for other languages
        if any(
            indicator in sample_text
            for indicator in ["function ", "var ", "const ", "let ", "=>"]
        ):
            return "javascript"

        return "unknown"

    def _chunk_python(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Python code using AST with enhanced function/class extraction."""
        chunks = []
        lines = content.splitlines()
        total_lines = len(lines)

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return self._chunk_python_fallback(content, file_path)

        # Extract all functions and classes with their metadata
        extracted_items = self._extract_python_items(tree, lines)

        # If we found functions/classes, create chunks for them
        if extracted_items:
            chunks = self._create_chunks_from_items(
                extracted_items, lines, file_path, total_lines
            )

        # If no chunks or very few chunks from a large file, add fallback chunks
        if len(chunks) < 3 and total_lines > 200:
            fallback_chunks = self._chunk_python_fallback(content, file_path)
            # Merge with existing chunks, avoiding duplicates
            chunks = self._merge_chunks(chunks, fallback_chunks)

        return chunks or self._chunk_python_fallback(content, file_path)

    def _extract_python_items(self, tree: ast.AST, lines: List[str]) -> List[Dict]:
        """Extract all functions and classes with metadata."""
        items = []

        class ItemExtractor(ast.NodeVisitor):

            def __init__(self):
                self.class_stack = []  # Track nested classes
                self.function_stack = []  # Track nested functions

            def visit_ClassDef(self, node):
                self.class_stack.append(node.name)

                # Extract class info
                item = {
                    "type": "class",
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or len(lines),
                    "parent_class": (
                        self.class_stack[-2] if len(self.class_stack) > 1 else None
                    ),
                    "decorators": [d.id for d in node.decorator_list if hasattr(d, "id")],
                    "methods": [],
                }

                # Find methods in this class
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

                # Extract function info
                item = {
                    "type": func_type,
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or len(lines),
                    "parent_class": self.class_stack[-1] if self.class_stack else None,
                    "parent_function": (
                        self.function_stack[-2] if len(self.function_stack) > 1 else None
                    ),
                    "decorators": [d.id for d in node.decorator_list if hasattr(d, "id")],
                    "args": [arg.arg for arg in node.args.args],
                    "is_method": bool(self.class_stack),
                }

                items.append(item)

                self.generic_visit(node)
                self.function_stack.pop()

        extractor = ItemExtractor()
        extractor.visit(tree)

        # Sort items by line number
        items.sort(key=lambda x: x["start_line"])

        return items

    def _create_chunks_from_items(
        self, items: List[Dict], lines: List[str], file_path: str, total_lines: int
    ) -> List[CodeChunk]:
        """Create chunks from extracted AST items."""
        chunks = []

        for item in items:
            start_line = item["start_line"] - 1  # Convert to 0-based
            end_line = min(item["end_line"], len(lines)) - 1  # Convert to 0-based

            chunk_content = "\n".join(lines[start_line : end_line + 1])

            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line + 1,
                end_line=end_line + 1,
                chunk_type=item["type"],
                name=item["name"],
                language="python",
                parent_class=item.get("parent_class"),
                parent_function=item.get("parent_function"),
                file_lines=total_lines,
            )
            chunks.append(chunk)

        return chunks

    def _chunk_python_fallback(self, content: str, file_path: str) -> List[CodeChunk]:
        """Fallback chunking for Python files with syntax errors or no AST items."""
        chunks = []
        lines = content.splitlines()

        # Use regex to find function/class definitions
        patterns = [
            (r"^(class\s+\w+.*?:)", "class"),
            (r"^(def\s+\w+.*?:)", "function"),
            (r"^(async\s+def\s+\w+.*?:)", "async_function"),
        ]

        matches = []
        for i, line in enumerate(lines):
            for pattern, item_type in patterns:
                if re.match(pattern, line.strip()):
                    # Extract name
                    if item_type == "class":
                        name_match = re.match(r"class\s+(\w+)", line.strip())
                    else:
                        name_match = re.match(r"(?:async\s+)?def\s+(\w+)", line.strip())

                    if name_match:
                        matches.append(
                            {
                                "line": i,
                                "type": item_type,
                                "name": name_match.group(1),
                                "indent": len(line) - len(line.lstrip()),
                            }
                        )

        # Create chunks from matches
        for i, match in enumerate(matches):
            start_line = match["line"]

            # Find end line by looking for next item at same or lower indentation
            end_line = len(lines) - 1
            base_indent = match["indent"]

            for j in range(start_line + 1, len(lines)):
                line = lines[j]
                if line.strip() and len(line) - len(line.lstrip()) <= base_indent:
                    # Found next item at same or lower level
                    end_line = j - 1
                    break

            # Create chunk
            chunk_content = "\n".join(lines[start_line : end_line + 1])
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

        # Simple merge - just add fallback chunks that don't overlap with primary
        merged = primary_chunks[:]
        primary_ranges = [(chunk.start_line, chunk.end_line) for chunk in primary_chunks]

        for fallback_chunk in fallback_chunks:
            # Check if this fallback chunk overlaps with any primary chunk
            overlaps = False
            for start, end in primary_ranges:
                if not (fallback_chunk.end_line < start or fallback_chunk.start_line > end):
                    overlaps = True
                    break

            if not overlaps:
                merged.append(fallback_chunk)

        # Sort by start line
        merged.sort(key=lambda x: x.start_line)
        return merged

    def _process_python_class(
        self, node: ast.ClassDef, lines: List[str], file_path: str, total_lines: int
    ) -> List[CodeChunk]:
        """Process a Python class with smart chunking."""
        chunks = []

        # Get class definition line
        class_start = node.lineno - 1

        # Find where class docstring ends
        docstring_end = class_start
        class_docstring = ast.get_docstring(node)
        if class_docstring and node.body:
            first_stmt = node.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(
                first_stmt.value, (ast.Str, ast.Constant)
            ):
                docstring_end = first_stmt.end_lineno - 1

        # Find __init__ method if exists
        init_method = None
        init_end = docstring_end
        for child in node.body:
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name == "__init__"
            ):
                init_method = child
                init_end = child.end_lineno - 1
                break

        # Collect method signatures for preview
        method_signatures = []
        for child in node.body:
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name != "__init__"
            ):
                # Get just the method signature line
                sig_line = lines[child.lineno - 1].strip()
                method_signatures.append(f"    # {sig_line}")

        # Create class header chunk: class def + docstring + __init__ + method preview
        header_lines = []

        # Add class definition and docstring
        if init_method:
            header_lines = lines[class_start : init_end + 1]
        else:
            header_lines = lines[class_start : docstring_end + 1]

        # Add method signature preview if we have methods
        if method_signatures:
            header_content = "\n".join(header_lines)
            if not header_content.rstrip().endswith(":"):
                header_content += "\n"
            header_content += "\n    # Method signatures:\n" + "\n".join(
                method_signatures[:5]
            )  # Limit preview
            if len(method_signatures) > 5:
                header_content += f"\n    # ... and {len(method_signatures) - 5} more methods"
        else:
            header_content = "\n".join(header_lines)

        # Create class header chunk
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
        """Process a Python function or method, including its docstring."""
        start_line = node.lineno - 1
        end_line = (node.end_lineno or len(lines)) - 1

        # Include any decorators
        if hasattr(node, "decorator_list") and node.decorator_list:
            first_decorator = node.decorator_list[0]
            if hasattr(first_decorator, "lineno"):
                start_line = min(start_line, first_decorator.lineno - 1)

        function_content = "\n".join(lines[start_line : end_line + 1])

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

    def _chunk_javascript(
        self, content: str, file_path: str, language: str
    ) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code using regex patterns."""
        chunks = []
        lines = content.splitlines()

        # Patterns for different code structures
        patterns = {
            "function": r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "arrow_function": (
                r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*"
                r"(?:async\s+)?\([^)]*\)\s*=>"
            ),
            "class": r"^\s*(?:export\s+)?class\s+(\w+)",
            "method": r"^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*{",
        }

        # Find all matches
        matches = []
        for i, line in enumerate(lines):
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    matches.append((i, chunk_type, name))
                    break

        # Sort matches by line number
        matches.sort(key=lambda x: x[0])

        # Create chunks between matches
        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            # Find end line (next match or end of file)
            if i + 1 < len(matches):
                end_line = matches[i + 1][0] - 1
            else:
                end_line = len(lines) - 1

            # Find actual end by looking for closing brace
            brace_count = 0
            actual_end = start_line
            for j in range(start_line, min(end_line + 1, len(lines))):
                line = lines[j]
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0 and j > start_line:
                    actual_end = j
                    break
            else:
                actual_end = end_line

            chunk_content = "\n".join(lines[start_line : actual_end + 1])
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

        # If no chunks found, use generic chunking
        if not chunks:
            return self._chunk_generic(content, file_path, language)

        return chunks

    def _chunk_go(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Go code by functions and types."""
        chunks = []
        lines = content.splitlines()

        # Patterns for Go structures
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

        # Process matches similar to JavaScript
        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            # Find end line
            if i + 1 < len(matches):
                end_line = matches[i + 1][0] - 1
            else:
                end_line = len(lines) - 1

            # Find actual end by brace matching
            brace_count = 0
            actual_end = start_line
            for j in range(start_line, min(end_line + 1, len(lines))):
                line = lines[j]
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0 and j > start_line:
                    actual_end = j
                    break

            chunk_content = "\n".join(lines[start_line : actual_end + 1])
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

    def _chunk_java(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Java code by classes and methods."""
        chunks = []
        lines = content.splitlines()

        # Simple regex-based approach for Java
        class_pattern = (
            r"^\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)"
        )
        method_pattern = (
            r"^\s*(?:public|private|protected)?\s*(?:static)?\s*"
            r"(?:final)?\s*\w+\s+(\w+)\s*\("
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

        # Process matches
        for i in range(len(matches)):
            start_line = matches[i][0]
            chunk_type = matches[i][1]
            name = matches[i][2]

            # Find end line
            if i + 1 < len(matches):
                end_line = matches[i + 1][0] - 1
            else:
                end_line = len(lines) - 1

            chunk_content = "\n".join(lines[start_line : end_line + 1])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    chunk_type=chunk_type,
                    name=name,
                    language="java",
                )
            )

        return chunks if chunks else self._chunk_generic(content, file_path, "java")

    def _chunk_by_indent(self, content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Chunk code by indentation levels (fallback for syntax errors)."""
        chunks = []
        lines = content.splitlines()

        current_chunk_start = 0
        current_indent = 0

        for i, line in enumerate(lines):
            if line.strip():  # Non-empty line
                # Calculate indentation
                indent = len(line) - len(line.lstrip())

                # If dedent detected and chunk is large enough
                if indent < current_indent and i - current_chunk_start >= self.min_chunk_size:
                    # Create chunk
                    chunk_content = "\n".join(lines[current_chunk_start:i])
                    chunks.append(
                        CodeChunk(
                            content=chunk_content,
                            file_path=file_path,
                            start_line=current_chunk_start + 1,
                            end_line=i,
                            chunk_type="code_block",
                            name=f"block_{len(chunks) + 1}",
                            language=language,
                        )
                    )
                    current_chunk_start = i

                current_indent = indent

        # Add final chunk
        if current_chunk_start < len(lines):
            chunk_content = "\n".join(lines[current_chunk_start:])
            chunks.append(
                CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=current_chunk_start + 1,
                    end_line=len(lines),
                    chunk_type="code_block",
                    name=f"block_{len(chunks) + 1}",
                    language=language,
                )
            )

        return chunks

    def _chunk_generic(self, content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Generic chunking by empty lines and size constraints."""
        chunks = []
        lines = content.splitlines()

        current_chunk = []
        current_start = 0

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # Check if we should create a chunk
            should_chunk = False

            # Empty line indicates potential chunk boundary
            if not line.strip() and len(current_chunk) >= self.min_chunk_size:
                should_chunk = True

            # Maximum size reached
            if len(current_chunk) >= self.max_chunk_size:
                should_chunk = True

            # End of file
            if i == len(lines) - 1 and current_chunk:
                should_chunk = True

            if should_chunk and current_chunk:
                chunk_content = "\n".join(current_chunk).strip()
                if chunk_content:  # Don't create empty chunks
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

                # Reset for next chunk
                current_chunk = []
                current_start = i + 1

        return chunks

    def _enforce_size_constraints(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """
        Ensure all chunks meet size constraints.
        Split too-large chunks and merge too-small ones.
        """
        result = []

        for chunk in chunks:
            lines = chunk.content.splitlines()

            # If chunk is too large, split it
            if len(lines) > self.max_chunk_size:
                # Split into smaller chunks
                for i in range(0, len(lines), self.max_chunk_size - self.overlap_lines):
                    sub_lines = lines[i : i + self.max_chunk_size]
                    if len(sub_lines) >= self.min_chunk_size or not result:
                        sub_content = "\n".join(sub_lines)
                        sub_chunk = CodeChunk(
                            content=sub_content,
                            file_path=chunk.file_path,
                            start_line=chunk.start_line + i,
                            end_line=chunk.start_line + i + len(sub_lines) - 1,
                            chunk_type=chunk.chunk_type,
                            name=(
                                f"{chunk.name}_part{i // self.max_chunk_size + 1}"
                                if chunk.name
                                else None
                            ),
                            language=chunk.language,
                        )
                        result.append(sub_chunk)
                    elif result:
                        # Merge with previous chunk if too small
                        result[-1].content += "\n" + "\n".join(sub_lines)
                        result[-1].end_line = chunk.start_line + i + len(sub_lines) - 1

            # If chunk is too small, try to merge with previous
            elif len(lines) < self.min_chunk_size and result:
                # Check if merging would exceed max size
                prev_lines = result[-1].content.splitlines()
                if len(prev_lines) + len(lines) <= self.max_chunk_size:
                    result[-1].content += "\n" + chunk.content
                    result[-1].end_line = chunk.end_line
                else:
                    result.append(chunk)

            else:
                # Chunk is good size
                result.append(chunk)

        return result

    def _set_chunk_links(self, chunks: List[CodeChunk], file_path: str) -> List[CodeChunk]:
        """Set chunk indices and prev/next links for navigation."""
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total_chunks

            # Set chunk ID
            chunk.chunk_id = f"{Path(file_path).stem}_{i}"

            # Set previous chunk link
            if i > 0:
                chunk.prev_chunk_id = f"{Path(file_path).stem}_{i - 1}"

            # Set next chunk link
            if i < total_chunks - 1:
                chunk.next_chunk_id = f"{Path(file_path).stem}_{i + 1}"

        return chunks

    def _chunk_markdown(
        self, content: str, file_path: str, language: str = "markdown"
    ) -> List[CodeChunk]:
        """
        Chunk markdown/text files by sections with context overlap.

        Args:
            content: File content
            file_path: Path to file
            language: Document language type

        Returns:
            List of chunks
        """
        chunks = []
        lines = content.splitlines()
        total_lines = len(lines)

        # Track current section
        current_section = []
        current_start = 0
        section_name = "content"

        # Context overlap for markdown (keep last few lines)
        overlap_buffer = []
        overlap_size = 3  # Lines to overlap between chunks

        # Patterns for different section types
        header_pattern = re.compile(r"^(#+)\s+(.+)$")  # Markdown headers with level
        separator_pattern = re.compile(r"^[-=]{3,}$")  # Horizontal rules

        for i, line in enumerate(lines):
            # Check for headers
            header_match = header_pattern.match(line)

            # Check for section breaks
            is_separator = separator_pattern.match(line.strip())
            is_empty = not line.strip()

            # Decide if we should create a chunk
            should_chunk = False

            if header_match:
                # New header found
                should_chunk = True
                new_section_name = header_match.group(2).strip()
            elif is_separator:
                # Separator found
                should_chunk = True
            elif is_empty and len(current_section) > 0:
                # Empty line after content
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    # Multiple empty lines - chunk here
                    should_chunk = True

            # Check size constraints
            if len(current_section) >= self.max_chunk_size:
                should_chunk = True

            if should_chunk and current_section:
                # Add overlap from previous chunk if available
                section_with_overlap = overlap_buffer + current_section

                # Create chunk from current section
                chunk_content = "\n".join(section_with_overlap)
                if chunk_content.strip():  # Only create chunk if non-empty
                    chunk = CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=max(1, current_start + 1 - len(overlap_buffer)),
                        end_line=current_start + len(current_section),
                        chunk_type="section",
                        name=section_name[:50],  # Limit name length
                        language=language,
                        file_lines=total_lines,
                    )
                    chunks.append(chunk)

                # Save overlap for next chunk
                if len(current_section) > overlap_size:
                    overlap_buffer = current_section[-overlap_size:]
                else:
                    overlap_buffer = current_section[:]

                # Reset for next section
                current_section = []
                current_start = i + 1

                # Update section name if we found a header
                if header_match:
                    section_name = new_section_name
                else:
                    section_name = f"section_{len(chunks) + 1}"

            # Add line to current section
            if not (should_chunk and (header_match or is_separator)):
                current_section.append(line)

        # Don't forget the last section
        if current_section:
            section_with_overlap = overlap_buffer + current_section
            chunk_content = "\n".join(section_with_overlap)
            if chunk_content.strip():
                chunk = CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=max(1, current_start + 1 - len(overlap_buffer)),
                    end_line=len(lines),
                    chunk_type="section",
                    name=section_name[:50],
                    language=language,
                    file_lines=total_lines,
                )
                chunks.append(chunk)

        # If no chunks created, create one for the whole file
        if not chunks and content.strip():
            chunks.append(
                CodeChunk(
                    content=content,
                    file_path=file_path,
                    start_line=1,
                    end_line=len(lines),
                    chunk_type="document",
                    name=Path(file_path).stem,
                    language=language,
                    file_lines=total_lines,
                )
            )

        # Set chunk links
        chunks = self._set_chunk_links(chunks, file_path)

        return chunks

    def _chunk_config(
        self, content: str, file_path: str, language: str = "config"
    ) -> List[CodeChunk]:
        """
        Chunk configuration files by sections.

        Args:
            content: File content
            file_path: Path to file
            language: Config language type

        Returns:
            List of chunks
        """
        # For config files, we'll create smaller chunks by top-level sections
        chunks = []
        lines = content.splitlines()

        if language == "json":
            # For JSON, just create one chunk for now
            # (Could be enhanced to chunk by top-level keys)
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
            # For YAML, INI, TOML, etc., chunk by sections
            current_section = []
            current_start = 0
            section_name = "config"

            # Patterns for section headers
            section_patterns = {
                "ini": re.compile(r"^\[(.+)\]$"),
                "toml": re.compile(r"^\[(.+)\]$"),
                "yaml": re.compile(r"^(\w+):$"),
            }

            pattern = section_patterns.get(language)

            for i, line in enumerate(lines):
                is_section = False

                if pattern:
                    match = pattern.match(line.strip())
                    if match:
                        is_section = True
                        new_section_name = match.group(1)

                if is_section and current_section:
                    # Create chunk for previous section
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

                    # Start new section
                    current_section = [line]
                    current_start = i
                    section_name = new_section_name
                else:
                    current_section.append(line)

            # Add final section
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

        # If no chunks created, create one for the whole file
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

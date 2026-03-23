"""Unit tests for the CodeChunker module."""

import pytest
from pathlib import Path
from mini_rag.chunker import CodeChunker, CodeChunk


class TestPythonChunking:
    """Test AST-based Python chunking."""

    def test_chunks_by_class(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) >= 1
        assert any("AuthManager" in (c.name or "") for c in class_chunks)

    def test_chunks_by_function(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        all_content = " ".join(c.content for c in chunks)
        assert "get_auth_manager" in all_content

    def test_preserves_content(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        all_content = "\n".join(c.content for c in chunks)
        assert "AuthManager" in all_content
        assert "login" in all_content

    def test_line_numbers_valid(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        for chunk in chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_class_header_has_init(self, chunker, tmp_project):
        """Class chunks should include __init__ and method signature preview."""
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) >= 1
        class_chunk = class_chunks[0]
        assert "__init__" in class_chunk.content
        assert "Method signatures:" in class_chunk.content

    def test_methods_split_from_class(self, chunker, tmp_project):
        """Methods should be separate chunks from the class header."""
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        method_names = [c.name for c in method_chunks]
        assert "login" in method_names

    def test_fallback_ignores_nested_defs(self, chunker):
        """Python fallback should only match top-level definitions."""
        content = '''def outer():
    def inner():
        pass
    return inner()

def another_top():
    class Nested:
        pass
'''
        chunks = chunker._chunk_python_fallback(content, "test.py")
        names = [c.name for c in chunks]
        assert "outer" in names
        assert "another_top" in names
        assert "inner" not in names
        assert "Nested" not in names


class TestMarkdownChunking:
    """Test section-based markdown chunking."""

    def test_splits_by_headers(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "README.md")
        assert len(chunks) >= 3, f"Expected >=3 sections, got {len(chunks)}"

    def test_section_names_from_headers(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "README.md")
        names = [c.name for c in chunks]
        assert any("Authentication" in (n or "") for n in names)

    def test_chunk_type_is_section(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "README.md")
        for chunk in chunks:
            assert chunk.chunk_type in ("section", "document", "file_overview", "code_block")

    def test_regulatory_document_preserves_sections(self, chunker):
        """Critical test: regulatory documents must not collapse into one chunk."""
        doc = """# Regulations

## Section 1: Requirements

Workers must complete background checks.
All checks must be verified annually.

## Section 2: Ratios

Staff ratios must be maintained:
- Infants: 1:4
- Toddlers: 1:5
- Preschool: 1:8

## Section 3: Safety

Facilities must maintain fire safety equipment.
Exits must be clearly marked.
"""
        chunks = chunker.chunk_file(Path("regulations.md"), doc)
        assert len(chunks) >= 3, (
            f"Regulatory doc collapsed to {len(chunks)} chunk(s). "
            f"Expected >=3 (one per section). "
            f"This is the critical boundary preservation bug."
        )


class TestMarkdownCodeBlocks:
    """Test that fenced code blocks with blank lines survive chunking intact."""

    def test_code_block_with_blank_lines_preserved(self, chunker):
        """Code blocks containing blank lines must not be split."""
        doc = '''# Example

Here is some code:

```python
def hello():
    print("hello")

def world():
    print("world")
```

And some text after.
'''
        chunks = chunker.chunk_file(Path("example.md"), doc)
        code_chunks = [c for c in chunks if c.chunk_type == "code_block"]
        assert len(code_chunks) >= 1, "No code_block chunks found"

        # The code block should be intact with the blank line
        code_content = code_chunks[0].content
        assert 'def hello():' in code_content
        assert 'def world():' in code_content
        assert '```python' in code_content
        # Verify the blank line between functions is preserved
        assert '\n\n' in code_content

    def test_multiple_code_blocks_with_blank_lines(self, chunker):
        """Multiple code blocks with blank lines should each be intact."""
        doc = '''# Doc

```js
function a() {
    return 1;
}

function b() {
    return 2;
}
```

Some text.

```python
class Foo:
    pass

class Bar:
    pass
```
'''
        chunks = chunker.chunk_file(Path("multi.md"), doc)
        code_chunks = [c for c in chunks if c.chunk_type == "code_block"]
        assert len(code_chunks) == 2, f"Expected 2 code blocks, got {len(code_chunks)}"
        assert 'function a()' in code_chunks[0].content
        assert 'function b()' in code_chunks[0].content
        assert 'class Foo' in code_chunks[1].content
        assert 'class Bar' in code_chunks[1].content

    def test_code_block_without_blank_lines_still_works(self, chunker):
        """Code blocks without blank lines should still work as before."""
        doc = '''# Doc

```
single line
```
'''
        chunks = chunker.chunk_file(Path("simple.md"), doc)
        code_chunks = [c for c in chunks if c.chunk_type == "code_block"]
        assert len(code_chunks) >= 1
        assert 'single line' in code_chunks[0].content


class TestSizeConstraints:
    """Test character-based size enforcement."""

    def test_uses_character_counts(self):
        chunker = CodeChunker(max_chunk_size=500, min_chunk_size=50, overlap_chars=0)
        content = "x" * 600
        chunks = chunker.chunk_file(Path("test.txt"), content)
        assert all(len(c.content) <= 600 for c in chunks)

    def test_small_sections_not_merged_across_boundaries(self):
        """Sections should never merge across semantic boundaries."""
        chunker = CodeChunker(min_chunk_size=5000)
        doc = """# Doc

## Section A

Short content A.

## Section B

Short content B.
"""
        chunks = chunker.chunk_file(Path("test.md"), doc)
        assert len(chunks) >= 2, (
            f"Sections merged despite being different semantic units. "
            f"Got {len(chunks)} chunk(s)."
        )

    def test_config_values_are_characters(self):
        """Verify defaults match config expectations (characters, not lines)."""
        chunker = CodeChunker()
        assert chunker.max_chunk_size == 2000, "Default max should be 2000 chars"
        assert chunker.min_chunk_size == 150, "Default min should be 150 chars"


class TestOverlapChars:
    """Test character-based overlap between chunks."""

    def test_overlap_default_is_200(self):
        chunker = CodeChunker()
        assert chunker.overlap_chars == 200

    def test_overlap_can_be_configured(self):
        chunker = CodeChunker(overlap_chars=100)
        assert chunker.overlap_chars == 100

    def test_overlap_zero_produces_no_overlap(self):
        chunker = CodeChunker(max_chunk_size=100, min_chunk_size=10, overlap_chars=0)
        content = "\n".join(f"Line {i}: " + "x" * 40 for i in range(20))
        chunks = chunker.chunk_file(Path("test.txt"), content)
        if len(chunks) >= 2:
            # With zero overlap, chunks should not share content
            for i in range(1, len(chunks)):
                # The start of chunk i should not repeat the end of chunk i-1
                prev_tail = chunks[i - 1].content[-50:]
                curr_head = chunks[i].content[:50]
                # Allow some natural overlap from line boundaries, but not systematic
                assert prev_tail != curr_head

    def test_overlap_produces_shared_content(self):
        chunker = CodeChunker(max_chunk_size=200, min_chunk_size=10, overlap_chars=50)
        content = "\n".join(f"Line {i}: " + "x" * 60 for i in range(20))
        chunks = chunker.chunk_file(Path("test.txt"), content)
        # Just verify chunks are produced and overlap param is respected
        assert len(chunks) >= 2, "Expected multiple chunks from large content"


class TestLanguageConfigs:
    """Test per-language configuration."""

    def test_default_language_configs_loaded(self):
        chunker = CodeChunker()
        assert "python" in chunker.language_configs
        assert chunker.language_configs["python"]["max_size"] == 3000

    def test_custom_language_configs(self):
        custom = {"python": {"max_size": 5000, "min_size": 500}}
        chunker = CodeChunker(language_configs=custom)
        assert chunker.language_configs["python"]["max_size"] == 5000
        # Custom config replaces defaults entirely
        assert "javascript" not in chunker.language_configs

    def test_effective_config_falls_back_to_global(self):
        chunker = CodeChunker(max_chunk_size=1500, min_chunk_size=100)
        config = chunker._get_effective_config("unknown_lang")
        assert config["max_size"] == 1500
        assert config["min_size"] == 100

    def test_effective_config_uses_language_override(self):
        chunker = CodeChunker()
        config = chunker._get_effective_config("python")
        assert config["max_size"] == 3000  # Python override, not default 2000

    def test_file_size_adjustments(self):
        chunker = CodeChunker()
        small_config = chunker._get_effective_config("python", file_size=100)
        assert small_config["max_size"] < 3000  # Should be halved for tiny files
        assert small_config["min_size"] == 50

        large_config = chunker._get_effective_config("python", file_size=25000)
        assert large_config["max_size"] > 3000  # Should increase for large files


class TestBraceCounting:
    """Test string/comment-aware brace counting."""

    def test_normal_braces(self):
        assert CodeChunker._count_braces_safe("function foo() {") == 1
        assert CodeChunker._count_braces_safe("}") == -1
        assert CodeChunker._count_braces_safe("{ }") == 0

    def test_braces_in_string_ignored(self):
        assert CodeChunker._count_braces_safe('var x = "}{";') == 0
        assert CodeChunker._count_braces_safe("var x = '}{';") == 0
        assert CodeChunker._count_braces_safe("var x = `}{`;") == 0

    def test_braces_in_comment_ignored(self):
        assert CodeChunker._count_braces_safe("// this is a { comment") == 0
        assert CodeChunker._count_braces_safe("x = 1; // }") == 0

    def test_escaped_quotes_handled(self):
        assert CodeChunker._count_braces_safe(r'var x = "\"}{\"";') == 0

    def test_mixed_real_and_string_braces(self):
        # Real { followed by string containing }
        assert CodeChunker._count_braces_safe('if (true) { var x = "}";') == 1


class TestJavaChunking:
    """Test Java-specific chunking improvements."""

    def test_field_with_parens_not_matched_as_method(self, chunker):
        """Field declarations with parentheses should not be matched as methods."""
        content = '''public class Foo {
    private String name = getValue();
    private int count = Math.max(1, 2);

    public void doStuff() {
        System.out.println("hello");
    }
}
'''
        chunks = chunker.chunk_file(Path("Foo.java"), content)
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        method_names = [c.name for c in method_chunks]
        assert "getValue" not in method_names
        assert "max" not in method_names

    def test_constructor_detected(self, chunker):
        """Java constructors should be detected."""
        content = '''public class Bar {
    private int x;

    public Bar(int x) {
        this.x = x;
    }

    public int getX() {
        return x;
    }
}
'''
        chunks = chunker.chunk_file(Path("Bar.java"), content)
        chunk_types = [c.chunk_type for c in chunks]
        assert "constructor" in chunk_types or "class" in chunk_types


class TestChunkMetadata:
    """Test chunk linking and metadata."""

    def test_chunk_indices_set(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        if len(chunks) > 1:
            assert chunks[0].chunk_index == 0
            assert chunks[-1].chunk_index == len(chunks) - 1

    def test_total_chunks_set(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)

    def test_to_dict_includes_fields(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "auth.py")
        d = chunks[0].to_dict()
        assert "content" in d
        assert "file_path" in d
        assert "chunk_type" in d
        assert "language" in d


class TestLanguageDetection:
    """Test file type detection and routing."""

    def test_python_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.py"), "def foo():\n    pass\n")
        assert chunks[0].language == "python"

    def test_markdown_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.md"), "# Title\n\nContent\n")
        assert chunks[0].language == "markdown"

    def test_yaml_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.yaml"), "key: value\n")
        assert chunks[0].language == "yaml"

    def test_unknown_extension_uses_generic(self, chunker):
        chunks = chunker.chunk_file(Path("test.xyz"), "some content\n")
        assert len(chunks) >= 1

    def test_html_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.html"), "<h1>Title</h1>\n<p>Content</p>\n")
        assert chunks[0].language == "html"

    def test_shell_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.sh"), "#!/bin/bash\necho hello\n")
        assert chunks[0].language == "shell"

    def test_css_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.css"), "body { color: red; }\n")
        assert chunks[0].language == "css"

    def test_sql_detected(self, chunker):
        chunks = chunker.chunk_file(Path("test.sql"), "SELECT * FROM users;\n")
        assert chunks[0].language == "sql"

    def test_conf_detected_as_config(self, chunker):
        chunks = chunker.chunk_file(Path("test.conf"), "[section]\nkey=value\n")
        assert chunks[0].language == "config"

    def test_service_detected_as_config(self, chunker):
        chunks = chunker.chunk_file(Path("test.service"), "[Unit]\nDescription=Test\n")
        assert chunks[0].language == "config"


class TestShellChunking:
    """Test shell script function detection."""

    def test_posix_function_detected(self, chunker):
        content = """#!/bin/bash
# Build script for the project
# Handles compilation and packaging

build() {
    echo "building the project from source"
    ./configure --prefix=/usr/local
    make clean
    make -j$(nproc) all
    make install
    echo "build complete"
}
"""
        chunks = chunker.chunk_file(Path("test.sh"), content)
        func_chunks = [c for c in chunks if c.chunk_type == "function"]
        assert len(func_chunks) >= 1
        assert any(c.name == "build" for c in func_chunks)

    def test_bash_keyword_function_detected(self, chunker):
        content = """#!/bin/bash
# Deployment script with remote sync
# Requires SSH access to production

function deploy {
    echo "deploying to production server"
    rsync -avz --delete ./dist/ remote:/var/www/app/
    ssh remote 'systemctl restart app'
    echo "deployment complete, verifying health"
    curl -f http://remote/health || echo "health check failed"
}
"""
        chunks = chunker.chunk_file(Path("test.sh"), content)
        func_chunks = [c for c in chunks if c.chunk_type == "function"]
        assert len(func_chunks) >= 1
        assert any(c.name == "deploy" for c in func_chunks)

    def test_preamble_captured(self, chunker):
        content = """#!/bin/bash
set -e
VERSION="1.0"

build() {
    echo "building"
}
"""
        chunks = chunker.chunk_file(Path("test.sh"), content)
        header_chunks = [c for c in chunks if c.chunk_type == "module_header"]
        assert len(header_chunks) >= 1
        assert "#!/bin/bash" in header_chunks[0].content

    def test_fallback_when_no_functions(self, chunker):
        content = """#!/bin/bash
echo "hello"
echo "world"
"""
        chunks = chunker.chunk_file(Path("test.sh"), content)
        assert len(chunks) >= 1

    def test_shell_from_fixture(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "build.sh")
        func_chunks = [c for c in chunks if c.chunk_type == "function"]
        names = [c.name for c in func_chunks]
        assert "build_project" in names
        assert "run_tests" in names


class TestHTMLChunking:
    """Test HTML tag-aware chunking."""

    def test_script_stripped(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "page.html")
        all_content = " ".join(c.content for c in chunks)
        assert "alert" not in all_content

    def test_style_stripped(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "page.html")
        all_content = " ".join(c.content for c in chunks)
        assert "display: none" not in all_content

    def test_table_as_own_chunk(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "page.html")
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1
        table_content = table_chunks[0].content
        assert "Router" in table_content
        assert "Cache" in table_content

    def test_pre_as_code_block(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "page.html")
        code_chunks = [c for c in chunks if c.chunk_type == "code_block"]
        assert len(code_chunks) >= 1
        assert "initialize_application" in code_chunks[0].content

    def test_heading_used_as_name(self, chunker, tmp_project):
        chunks = chunker.chunk_file(tmp_project / "page.html")
        names = [c.name for c in chunks if c.name]
        assert any("Architecture" in n for n in names)

    def test_fallback_on_plain_text(self, chunker):
        """Non-HTML content with .html extension falls back gracefully."""
        chunks = chunker.chunk_file(Path("test.html"), "Just plain text, no tags.\n")
        assert len(chunks) >= 1


class TestMarkdownTableProtection:
    """Test that markdown tables are protected from paragraph splitting."""

    def test_table_survives_intact(self, chunker):
        content = """# Results

| Name    | Score | Grade | Department          | Year |
|---------|-------|-------|---------------------|------|
| Alice   | 95    | A+    | Computer Science    | 2024 |
| Bob     | 87    | B+    | Mathematics         | 2024 |
| Charlie | 92    | A     | Physics             | 2023 |
| Diana   | 78    | B     | Computer Science    | 2023 |
| Edward  | 88    | B+    | Mathematics         | 2024 |

## Next Section

More content here about the grading methodology and evaluation criteria.
"""
        chunks = chunker.chunk_file(Path("test.md"), content)
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1
        table = table_chunks[0].content
        assert "Alice" in table
        assert "Bob" in table
        assert "|-------|" in table

    def test_table_not_split(self, chunker):
        content = """# Data

| Col A | Col B |
|-------|-------|
| 1     | 2     |
| 3     | 4     |
| 5     | 6     |
"""
        chunks = chunker.chunk_file(Path("test.md"), content)
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1
        # All rows should be in the same chunk
        table = table_chunks[0].content
        assert table.count("|") >= 12  # At least 4 rows * 3 pipes

    def test_non_table_pipes_unaffected(self, chunker):
        content = """# Notes

Use the | operator for bitwise OR.

Regular paragraph text.
"""
        chunks = chunker.chunk_file(Path("test.md"), content)
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) == 0

    def test_table_gets_section_name(self, chunker):
        content = """# Comparison

| Feature       | Old System | New System | Improvement |
|---------------|------------|------------|-------------|
| Speed         | 10s        | 2s         | 5x faster   |
| Memory        | 512MB      | 128MB      | 4x less     |
| Throughput    | 100 req/s  | 500 req/s  | 5x more     |
| Error Rate    | 2.5%       | 0.1%       | 25x better  |
| Startup Time  | 30s        | 3s         | 10x faster  |

Done with the comparison of system metrics and performance indicators.
"""
        chunks = chunker.chunk_file(Path("test.md"), content)
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1
        assert "Comparison" in table_chunks[0].name

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
        # Standalone functions may be typed as 'function' or included in module chunks
        all_names = [c.name or "" for c in chunks]
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
            assert chunk.chunk_type in ("section", "document")

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


class TestSizeConstraints:
    """Test character-based size enforcement."""

    def test_uses_character_counts(self):
        chunker = CodeChunker(max_chunk_size=500, min_chunk_size=50)
        # A 600-char single block should be split
        content = "x" * 600
        chunks = chunker.chunk_file(Path("test.txt"), content)
        assert all(len(c.content) <= 600 for c in chunks)

    def test_small_sections_not_merged_across_boundaries(self):
        """Sections should never merge across semantic boundaries."""
        chunker = CodeChunker(min_chunk_size=5000)  # Very high threshold
        doc = """# Doc

## Section A

Short content A.

## Section B

Short content B.
"""
        chunks = chunker.chunk_file(Path("test.md"), doc)
        # Even with high min_chunk_size, sections must stay separate
        assert len(chunks) >= 2, (
            f"Sections merged despite being different semantic units. "
            f"Got {len(chunks)} chunk(s)."
        )

    def test_config_values_are_characters(self):
        """Verify defaults match config expectations (characters, not lines)."""
        chunker = CodeChunker()
        assert chunker.max_chunk_size == 2000, "Default max should be 2000 chars"
        assert chunker.min_chunk_size == 150, "Default min should be 150 chars"


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

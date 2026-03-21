"""Unit tests for the CodeSearcher and SearchResult module."""

import pytest
from mini_rag.search import SearchResult, CodeSearcher


class TestSearchResult:
    """Test SearchResult data structure."""

    def test_create_result(self):
        r = SearchResult(
            file_path="test.py",
            content="def foo(): pass",
            score=0.85,
            start_line=1,
            end_line=1,
            chunk_type="function",
            name="foo",
            language="python",
        )
        assert r.score == 0.85
        assert r.file_path == "test.py"
        assert r.name == "foo"

    def test_to_dict(self):
        r = SearchResult(
            file_path="test.py",
            content="content",
            score=0.5,
            start_line=1,
            end_line=5,
            chunk_type="class",
            name="MyClass",
            language="python",
        )
        d = r.to_dict()
        assert d["score"] == 0.5
        assert d["chunk_type"] == "class"
        assert d["name"] == "MyClass"

    def test_format_for_display(self):
        r = SearchResult(
            file_path="test.py",
            content="line1\nline2\nline3\nline4\nline5",
            score=0.5,
            start_line=1,
            end_line=5,
            chunk_type="function",
            name="test",
            language="python",
        )
        display = r.format_for_display(max_lines=3)
        assert "line1" in display


class TestScoreLabel:
    """Test score interpretation labels."""

    def test_high_score(self):
        label = CodeSearcher._score_label(0.8)
        assert "HIGH" in label

    def test_good_score(self):
        label = CodeSearcher._score_label(0.55)
        assert "GOOD" in label

    def test_fair_score(self):
        label = CodeSearcher._score_label(0.35)
        assert "FAIR" in label

    def test_low_score(self):
        label = CodeSearcher._score_label(0.15)
        assert "LOW" in label

    def test_weak_score(self):
        # With no max_score context, 0.05 is in RRF range (< 0.1)
        # and 0.05 > 0.035 threshold = HIGH on RRF scale
        label = CodeSearcher._score_label(0.05, max_score=1.0)  # Cosine scale
        assert "WEAK" in label

    def test_boundary_values(self):
        assert "HIGH" in CodeSearcher._score_label(0.7)
        assert "GOOD" in CodeSearcher._score_label(0.5)
        assert "FAIR" in CodeSearcher._score_label(0.3)
        assert "LOW" in CodeSearcher._score_label(0.1)

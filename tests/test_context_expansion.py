"""Tests for search result consolidation (gap-filling pattern from Fss-Rag)."""

from mini_rag.search import SearchResult, CodeSearcher


def _make_result(file_path, start, end, score=0.5, name="test"):
    return SearchResult(
        file_path=file_path,
        content=f"content lines {start}-{end}",
        score=score,
        start_line=start,
        end_line=end,
        chunk_type="function",
        name=name,
        language="python",
    )


class TestConsolidation:
    """Test same-file chunk consolidation."""

    def test_merges_adjacent_chunks(self):
        results = [
            _make_result("a.py", 1, 10, score=0.8, name="func_a"),
            _make_result("a.py", 11, 20, score=0.6, name="func_b"),
        ]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 1
        assert merged[0].start_line == 1
        assert merged[0].end_line == 20
        assert merged[0].score == 0.8  # Best score kept

    def test_does_not_merge_distant_chunks(self):
        results = [
            _make_result("a.py", 1, 10),
            _make_result("a.py", 50, 60),
        ]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 2

    def test_does_not_merge_different_files(self):
        results = [
            _make_result("a.py", 1, 10),
            _make_result("b.py", 11, 20),
        ]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 2

    def test_single_result_unchanged(self):
        results = [_make_result("a.py", 1, 10)]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 1

    def test_empty_results(self):
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results([])
        assert merged == []

    def test_three_adjacent_chunks_merge_to_one(self):
        results = [
            _make_result("a.py", 1, 10, score=0.3),
            _make_result("a.py", 11, 20, score=0.8),
            _make_result("a.py", 21, 30, score=0.5),
        ]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 1
        assert merged[0].end_line == 30
        assert merged[0].score == 0.8

    def test_gap_of_one_line_still_merges(self):
        """Lines 1-10 and 12-20 have a 1-line gap - should merge."""
        results = [
            _make_result("a.py", 1, 10),
            _make_result("a.py", 12, 20),
        ]
        searcher = CodeSearcher.__new__(CodeSearcher)
        merged = searcher._consolidate_same_file_results(results)
        assert len(merged) == 1

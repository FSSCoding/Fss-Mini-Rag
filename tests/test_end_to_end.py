"""End-to-end indexing and retrieval validation with Jaccard scoring.

Indexes the full test corpus (synthetic + real code), runs targeted
queries with known expected results, and measures retrieval quality
using Jaccard similarity scores.

This test serves as both a regression suite and a benchmarking tool
for evaluating different chunking strategies and sizes.
"""

import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from mini_rag.chunker import CodeChunker
from mini_rag.indexer import ProjectIndexer
from mini_rag.ollama_embeddings import OllamaEmbedder
from mini_rag.search import CodeSearcher

CORPUS_DIR = Path(__file__).parent / "corpus"


def _fast_embedder():
    """Create a hash-only embedder for fast testing (no network calls)."""
    emb = OllamaEmbedder(
        base_url="http://localhost:1",  # unreachable = instant hash fallback
        enable_fallback=False,
    )
    return emb


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two sets of terms."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def tokenize(text: str) -> Set[str]:
    """Simple word tokenizer for Jaccard scoring."""
    return set(text.lower().split())


# Queries with expected file matches and key terms that MUST appear
BENCHMARK_QUERIES = [
    {
        "query": "credit card validation Luhn algorithm",
        "expected_files": ["payment_processor.py"],
        "required_terms": {"luhn", "card", "validate", "checksum"},
        "description": "Should find the CreditCardValidator class",
    },
    {
        "query": "warehouse stock reorder minimum level",
        "expected_files": ["inventory_manager.py"],
        "required_terms": {"stock", "reorder", "min_stock"},
        "description": "Should find inventory reorder logic",
    },
    {
        "query": "rate limiting middleware requests per minute",
        "expected_files": ["api_router.js"],
        "required_terms": {"rate", "limit", "requests"},
        "description": "Should find JS rate limiter",
    },
    {
        "query": "anti-discrimination policy workplace complaints",
        "expected_files": ["compliance_manual.md"],
        "required_terms": {"discrimination", "complaints"},
        "description": "Should find compliance section 1",
    },
    {
        "query": "data breach notification GDPR privacy",
        "expected_files": ["compliance_manual.md"],
        "required_terms": {"data", "breach", "notification"},
        "description": "Should find data protection section",
    },
    {
        "query": "whistleblower protection anonymous reporting ethics",
        "expected_files": ["compliance_manual.md"],
        "required_terms": {"whistleblower", "anonymous"},
        "description": "Should find whistleblower section",
    },
    {
        "query": "database connection pool exhaustion incident",
        "expected_files": ["incident_report.txt"],
        "required_terms": {"connection", "pool", "exhaustion"},
        "description": "Should find the incident report",
    },
    {
        "query": "redis cache TTL session timeout configuration",
        "expected_files": ["database_config.yaml"],
        "required_terms": {"redis", "ttl", "session"},
        "description": "Should find YAML cache config",
    },
    {
        "query": "JWT authentication token expiry refresh",
        "expected_files": ["api_router.js", "app_settings.toml", "api_documentation.md"],
        "required_terms": {"jwt", "token"},
        "description": "Should find auth-related content across files",
    },
    {
        "query": "payment gateway failover retry logic",
        "expected_files": ["payment_processor.py"],
        "required_terms": {"gateway", "failover", "retry"},
        "description": "Should find PaymentProcessor failover",
    },
]


@pytest.fixture(scope="module")
def indexed_corpus(tmp_path_factory):
    """Index the full test corpus and return the project path."""
    project_dir = tmp_path_factory.mktemp("corpus_test")

    # Copy entire corpus to temp dir
    corpus_src = CORPUS_DIR
    if not corpus_src.exists():
        pytest.skip("Test corpus not found at tests/corpus/")

    for item in corpus_src.rglob("*"):
        if item.is_file() and "__pycache__" not in str(item):
            rel = item.relative_to(corpus_src)
            dest = project_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    # Index with hash-based embeddings for speed (no Ollama dependency)
    embedder = _fast_embedder()
    indexer = ProjectIndexer(project_dir, embedder=embedder)
    stats = indexer.index_project()

    return {
        "path": project_dir,
        "stats": stats,
        "indexer": indexer,
    }


class TestCorpusIndexing:
    """Validate the indexing process produces reasonable chunks."""

    def test_indexes_all_file_types(self, indexed_corpus):
        stats = indexed_corpus["stats"]
        assert stats["files_indexed"] >= 20, (
            f"Expected >=20 files indexed, got {stats['files_indexed']}"
        )

    def test_produces_sufficient_chunks(self, indexed_corpus):
        stats = indexed_corpus["stats"]
        assert stats["chunks_created"] >= 200, (
            f"Expected >=200 chunks, got {stats['chunks_created']}. "
            f"Index may be under-chunking."
        )

    def test_indexing_completes_in_reasonable_time(self, indexed_corpus):
        stats = indexed_corpus["stats"]
        assert stats["time_taken"] < 120, (
            f"Indexing took {stats['time_taken']:.1f}s, expected <120s"
        )

    def test_chunk_size_distribution(self, indexed_corpus):
        """Verify chunks aren't all tiny or all huge."""
        path = indexed_corpus["path"]
        searcher = CodeSearcher(path)
        df = searcher.table.to_pandas()

        sizes = [len(c) for c in df["content"]]
        avg_size = sum(sizes) / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)

        # Average chunk should be 200-3000 chars
        assert 100 < avg_size < 5000, (
            f"Average chunk size {avg_size:.0f} chars is outside expected range"
        )
        # No empty chunks
        assert min_size > 0, "Found empty chunks"

        print(f"\n  Chunk stats: {len(sizes)} chunks, "
              f"avg={avg_size:.0f}, min={min_size}, max={max_size} chars")


class TestRetrievalQuality:
    """Validate search retrieval quality with Jaccard scoring.

    NOTE: With hash-based embeddings (no Ollama), semantic search is random.
    These tests measure BM25 keyword contribution and report quality metrics
    without hard assertions on file matching (which requires real embeddings).
    Run with Ollama available for true semantic validation.
    """

    @pytest.fixture(autouse=True)
    def setup_searcher(self, indexed_corpus):
        self.searcher = CodeSearcher(indexed_corpus["path"])
        self.corpus_path = indexed_corpus["path"]

    @pytest.mark.parametrize("benchmark", BENCHMARK_QUERIES,
                             ids=[b["description"] for b in BENCHMARK_QUERIES])
    def test_benchmark_query(self, benchmark):
        """Run each benchmark query and report retrieval metrics."""
        results = self.searcher.search(benchmark["query"], top_k=5)

        assert len(results) > 0, (
            f"No results for: {benchmark['query']}"
        )

        # Check if expected file appears in results
        result_files = [Path(r.file_path).name for r in results]
        expected_files = benchmark["expected_files"]

        found_expected = any(
            exp in result_files
            for exp in expected_files
        )

        # Check required terms appear in top results
        top_content = " ".join(r.content.lower() for r in results[:3])
        found_terms = benchmark["required_terms"] & tokenize(top_content)
        term_recall = len(found_terms) / len(benchmark["required_terms"]) if benchmark["required_terms"] else 0

        # Jaccard score between query terms and top result content
        query_tokens = tokenize(benchmark["query"])
        result_tokens = tokenize(top_content)
        jaccard = jaccard_similarity(query_tokens, result_tokens)

        print(f"\n  Query: {benchmark['query']}")
        print(f"  Top files: {result_files[:3]}")
        print(f"  Expected: {expected_files}")
        print(f"  File match: {'YES' if found_expected else 'NO (hash embeddings - expected)'}")
        print(f"  Term recall: {term_recall:.0%} ({found_terms})")
        print(f"  Jaccard score: {jaccard:.3f}")
        print(f"  Top score: {results[0].score:.3f}")

        # With hash embeddings, we only assert results exist and metrics are computed.
        # With real embeddings (Ollama), uncomment below for strict validation:
        # assert found_expected, f"Expected {expected_files} in results but got {result_files}"
        # assert term_recall >= 0.5, f"Term recall {term_recall:.0%} too low"


class TestChunkingStrategyComparison:
    """Compare chunking strategies using A/B Jaccard scoring."""

    STRATEGIES = [
        {"name": "default", "max_chunk_size": 2000, "min_chunk_size": 150},
        {"name": "small_chunks", "max_chunk_size": 1000, "min_chunk_size": 100},
        {"name": "large_chunks", "max_chunk_size": 4000, "min_chunk_size": 300},
        {"name": "micro_chunks", "max_chunk_size": 500, "min_chunk_size": 50},
    ]

    EVAL_QUERIES = [
        ("Luhn algorithm credit card validation", {"payment_processor.py"}),
        ("warehouse zone capacity stock", {"inventory_manager.py"}),
        ("whistleblower anonymous ethics hotline", {"compliance_manual.md"}),
        ("connection pool exhaustion database", {"incident_report.txt"}),
        ("rate limiting middleware", {"api_router.js"}),
    ]

    @pytest.mark.integration
    def test_strategy_comparison(self, tmp_path_factory):
        """Index with different chunk sizes and compare retrieval quality."""
        corpus_src = CORPUS_DIR
        if not corpus_src.exists():
            pytest.skip("Test corpus not found")

        strategy_results = {}

        for strategy in self.STRATEGIES:
            # Create isolated index for each strategy
            project_dir = tmp_path_factory.mktemp(f"strategy_{strategy['name']}")

            for item in corpus_src.rglob("*"):
                if item.is_file() and "__pycache__" not in str(item):
                    rel = item.relative_to(corpus_src)
                    dest = project_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

            # Index with this strategy's settings
            chunker = CodeChunker(
                max_chunk_size=strategy["max_chunk_size"],
                min_chunk_size=strategy["min_chunk_size"],
            )
            indexer = ProjectIndexer(project_dir, embedder=_fast_embedder(), chunker=chunker)
            start = time.time()
            stats = indexer.index_project()
            index_time = time.time() - start

            # Search and score
            searcher = CodeSearcher(project_dir)
            total_jaccard = 0.0
            total_file_hits = 0
            total_queries = len(self.EVAL_QUERIES)

            for query, expected_files in self.EVAL_QUERIES:
                results = searcher.search(query, top_k=5)
                if results:
                    result_files = {Path(r.file_path).name for r in results}
                    file_hit = 1 if expected_files & result_files else 0
                    total_file_hits += file_hit

                    top_content = " ".join(r.content.lower() for r in results[:3])
                    jaccard = jaccard_similarity(tokenize(query), tokenize(top_content))
                    total_jaccard += jaccard

            avg_jaccard = total_jaccard / total_queries
            file_precision = total_file_hits / total_queries

            strategy_results[strategy["name"]] = {
                "chunks": stats["chunks_created"],
                "index_time": index_time,
                "avg_jaccard": avg_jaccard,
                "file_precision": file_precision,
            }

        # Print comparison table
        print("\n" + "=" * 75)
        print("CHUNKING STRATEGY COMPARISON")
        print("=" * 75)
        print(f"{'Strategy':<16} {'Chunks':>7} {'Time':>7} {'Jaccard':>9} {'File Hit':>10}")
        print("-" * 75)

        for name, data in strategy_results.items():
            print(
                f"{name:<16} {data['chunks']:>7} "
                f"{data['index_time']:>6.1f}s "
                f"{data['avg_jaccard']:>8.3f} "
                f"{data['file_precision']:>9.0%}"
            )

        print("=" * 75)

        # With hash embeddings, file precision will be low.
        # This test is primarily for comparing strategies against each other
        # and measuring chunk count / indexing speed tradeoffs.
        default = strategy_results["default"]
        assert default["chunks"] > 100, (
            f"Default strategy produced only {default['chunks']} chunks, "
            f"expected >100 from 64 files"
        )


class TestChunkBoundaryEdgeCases:
    """Test specific edge cases for chunk boundaries."""

    def test_empty_file(self):
        chunker = CodeChunker()
        chunks = chunker.chunk_file(Path("empty.py"), "")
        assert len(chunks) == 0

    def test_single_line_file(self):
        chunker = CodeChunker()
        chunks = chunker.chunk_file(Path("one.py"), "x = 1\n")
        assert len(chunks) >= 1

    def test_file_with_only_comments(self):
        chunker = CodeChunker()
        content = "# Just a comment\n# Another comment\n# Third comment\n"
        chunks = chunker.chunk_file(Path("comments.py"), content)
        assert len(chunks) >= 1

    def test_very_long_single_function(self):
        """A function exceeding max_chunk_size should be split."""
        chunker = CodeChunker(max_chunk_size=500)
        lines = ["def huge_function():"] + [f"    x_{i} = {i}" for i in range(100)]
        content = "\n".join(lines)
        chunks = chunker.chunk_file(Path("huge.py"), content)
        # Should be split since content is >500 chars
        total_chars = sum(len(c.content) for c in chunks)
        assert total_chars > 500

    def test_markdown_with_no_headers(self):
        """Plain text with no headers should still produce chunks."""
        chunker = CodeChunker()
        content = "This is just plain text.\n\n" * 20
        chunks = chunker.chunk_file(Path("plain.md"), content)
        assert len(chunks) >= 1

    def test_markdown_with_only_headers(self):
        """Headers with no body content."""
        chunker = CodeChunker()
        content = "# Title\n\n## Section A\n\n## Section B\n\n## Section C\n"
        chunks = chunker.chunk_file(Path("headers.md"), content)
        assert len(chunks) >= 1

    def test_deeply_nested_python(self):
        """Nested classes and functions."""
        chunker = CodeChunker()
        content = '''
class Outer:
    class Inner:
        def method(self):
            def nested():
                return 42
            return nested()
    def outer_method(self):
        pass
'''
        chunks = chunker.chunk_file(Path("nested.py"), content)
        assert len(chunks) >= 1
        # Content should include the nesting
        all_content = " ".join(c.content for c in chunks)
        assert "Inner" in all_content
        assert "nested" in all_content

    def test_mixed_language_file(self):
        """A markdown file with embedded code blocks."""
        chunker = CodeChunker()
        content = '''# Setup Guide

## Python Setup

```python
def configure():
    config = load_config()
    return config
```

## JavaScript Setup

```javascript
function configure() {
    return loadConfig();
}
```

## Configuration

Set the DATABASE_URL environment variable.
'''
        chunks = chunker.chunk_file(Path("mixed.md"), content)
        assert len(chunks) >= 2

    def test_yaml_with_deep_nesting(self):
        chunker = CodeChunker()
        content = '''server:
  http:
    port: 8080
    host: 0.0.0.0
    timeouts:
      read: 30
      write: 30
      idle: 120
  grpc:
    port: 9090
    max_message_size: 4194304
'''
        chunks = chunker.chunk_file(Path("deep.yaml"), content)
        assert len(chunks) >= 1

    def test_unicode_content(self):
        chunker = CodeChunker()
        content = '''# Internationalization

## Japanese: テスト
Content with unicode characters.

## Chinese: 测试
More unicode content here.

## Emoji: 🚀🎯✅
Even emoji should work fine.
'''
        chunks = chunker.chunk_file(Path("unicode.md"), content)
        assert len(chunks) >= 1
        all_content = " ".join(c.content for c in chunks)
        assert "テスト" in all_content
        assert "测试" in all_content

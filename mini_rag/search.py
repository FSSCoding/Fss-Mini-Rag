"""
Fast semantic search using LanceDB.
Optimized for code search with relevance scoring.
"""

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import re

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

# CamelCase boundary pattern: split "getAuthManager" -> ["get", "auth", "manager"]
_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _tokenize_for_bm25(text: str) -> List[str]:
    """Tokenize text for BM25 with code-aware splitting.

    Splits on:
    - Whitespace
    - Underscores (snake_case -> [snake, case])
    - CamelCase boundaries (getAuth -> [get, auth])
    - Non-alphanumeric characters (dots, slashes, etc.)

    Keeps original compound tokens alongside split parts for exact matching.
    """
    # Split on non-alphanumeric (except underscores), preserve case for camelCase
    raw_tokens = re.split(r"[^a-zA-Z0-9_]+", text)

    tokens = []
    for token in raw_tokens:
        if not token:
            continue

        # Keep the original token (lowered)
        tokens.append(token.lower())

        # Split snake_case
        if "_" in token:
            parts = [p.lower() for p in token.split("_") if p]
            if len(parts) > 1:
                tokens.extend(parts)

        # Split camelCase (before lowering)
        camel_parts = _CAMEL_SPLIT.split(token)
        if len(camel_parts) > 1:
            tokens.extend(p.lower() for p in camel_parts if p)

    return tokens

# Optional LanceDB import
try:
    import lancedb

    LANCEDB_AVAILABLE = True
except ImportError:
    lancedb = None
    LANCEDB_AVAILABLE = False

from datetime import timedelta

from .config import ConfigManager
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .path_handler import display_path
from .query_expander import QueryExpander

logger = logging.getLogger(__name__)
console = Console()


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self,
        file_path: str,
        content: str,
        score: float,
        start_line: int,
        end_line: int,
        chunk_type: str,
        name: str,
        language: str,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        parent_chunk: Optional["SearchResult"] = None,
    ):
        self.file_path = file_path
        self.content = content
        self.score = score
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_type = chunk_type
        self.name = name
        self.language = language
        self.context_before = context_before
        self.context_after = context_after
        self.parent_chunk = parent_chunk

    def __repr__(self):
        return f"SearchResult({self.file_path}:{self.start_line}-{self.end_line}, score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "content": self.content,
            "score": self.score,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "language": self.language,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "parent_chunk": self.parent_chunk.to_dict() if self.parent_chunk else None,
        }

    def format_for_display(self, max_lines: int = 10) -> str:
        """Format for display with syntax highlighting."""
        lines = self.content.splitlines()
        if len(lines) > max_lines:
            # Show first and last few lines
            half = max_lines // 2
            lines = lines[:half] + ["..."] + lines[-half:]

        return "\n".join(lines)


class CodeSearcher:
    """Semantic code search using vector similarity."""

    def __init__(self, project_path: Path, embedder: Optional[CodeEmbedder] = None):
        """
        Initialize searcher.

        Args:
            project_path: Path to the project
            embedder: CodeEmbedder instance (creates one if not provided)
        """
        self.project_path = Path(project_path).resolve()
        self.rag_dir = self.project_path / ".mini-rag"
        self.embedder = embedder or CodeEmbedder()

        # Load configuration and initialize query expander
        config_manager = ConfigManager(project_path)
        self.config = config_manager.load_config()
        self.query_expander = QueryExpander(self.config)

        # Initialize database connection
        self.db = None
        self.table = None
        self.bm25 = None
        self.chunk_texts = []
        self.chunk_ids = []
        self._connect()
        self._build_bm25_index()

    def _connect(self):
        """Connect to the LanceDB database."""
        if not LANCEDB_AVAILABLE:
            print("❌ LanceDB Not Available")
            print("   LanceDB is required for search functionality")
            print("   Install it with: pip install lancedb pyarrow")
            print("   For basic Ollama functionality, use hash-based search instead")
            print()
            raise ImportError(
                "LanceDB dependency is required for search. Install with: pip install lancedb pyarrow"
            )

        try:
            if not self.rag_dir.exists():
                print("🗃️ No Search Index Found")
                print("   An index is a database that makes your files searchable")
                print(f"   Create index: ./rag-mini index {self.project_path}")
                print("   (This analyzes your files and creates semantic search vectors)")
                print()
                raise FileNotFoundError(f"No RAG index found at {self.rag_dir}")

            self.db = lancedb.connect(self.rag_dir)

            if "code_vectors" not in self.db.table_names():
                print("🔧 Index Database Corrupted")
                print("   The search index exists but is missing data tables")
                print(
                    f"   Rebuild index: rm -rf {self.rag_dir} && ./rag-mini index {self.project_path}"
                )
                print("   (This will recreate the search database)")
                print()
                raise ValueError("No code_vectors table found. Run indexing first.")

            self.table = self.db.open_table("code_vectors")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _build_bm25_index(self):
        """Build BM25 index from all chunks in the database."""
        if not self.table:
            return

        try:
            # Load all chunks into memory for BM25
            df = self.table.to_pandas()

            # Prepare texts for BM25 by combining content with metadata
            self.chunk_texts = []
            self.chunk_ids = []

            for idx, row in df.iterrows():
                # Create searchable text combining content, name, and type
                searchable_text = f"{row['content']} {row['name'] or ''} {row['chunk_type']}"

                # Tokenize for BM25 (code-aware splitting)
                tokens = _tokenize_for_bm25(searchable_text)

                self.chunk_texts.append(tokens)
                self.chunk_ids.append(idx)

            # Build BM25 index
            self.bm25 = BM25Okapi(self.chunk_texts)
            logger.info(f"Built BM25 index with {len(self.chunk_texts)} chunks")

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.bm25 = None

    def get_chunk_context(
        self, chunk_id: str, include_adjacent: bool = True, include_parent: bool = True
    ) -> Dict[str, Any]:
        """
        Get context for a specific chunk including adjacent and parent chunks.

        Args:
            chunk_id: The ID of the chunk to get context for
            include_adjacent: Whether to include previous and next chunks
            include_parent: Whether to include parent class chunk for methods

        Returns:
            Dictionary with 'chunk', 'prev', 'next', and 'parent' SearchResults
        """
        if not self.table:
            raise RuntimeError("Database not connected")

        try:
            # Get the main chunk by ID
            df = self.table.to_pandas()
            chunk_rows = df[df["chunk_id"] == chunk_id]

            if chunk_rows.empty:
                return {"chunk": None, "prev": None, "next": None, "parent": None}

            chunk_row = chunk_rows.iloc[0]
            context = {"chunk": self._row_to_search_result(chunk_row, score=1.0)}

            # Get adjacent chunks if requested
            if include_adjacent:
                # Get previous chunk
                if pd.notna(chunk_row.get("prev_chunk_id")):
                    prev_rows = df[df["chunk_id"] == chunk_row["prev_chunk_id"]]
                    if not prev_rows.empty:
                        context["prev"] = self._row_to_search_result(
                            prev_rows.iloc[0], score=1.0
                        )
                    else:
                        context["prev"] = None
                else:
                    context["prev"] = None

                # Get next chunk
                if pd.notna(chunk_row.get("next_chunk_id")):
                    next_rows = df[df["chunk_id"] == chunk_row["next_chunk_id"]]
                    if not next_rows.empty:
                        context["next"] = self._row_to_search_result(
                            next_rows.iloc[0], score=1.0
                        )
                    else:
                        context["next"] = None
                else:
                    context["next"] = None
            else:
                context["prev"] = None
                context["next"] = None

            # Get parent class chunk if requested and applicable
            if include_parent and pd.notna(chunk_row.get("parent_class")):
                # Find the parent class chunk
                parent_rows = df[
                    (df["name"] == chunk_row["parent_class"])
                    & (df["chunk_type"] == "class")
                    & (df["file_path"] == chunk_row["file_path"])
                ]
                if not parent_rows.empty:
                    context["parent"] = self._row_to_search_result(
                        parent_rows.iloc[0], score=1.0
                    )
                else:
                    context["parent"] = None
            else:
                context["parent"] = None

            return context

        except Exception as e:
            logger.error(f"Failed to get chunk context: {e}")
            return {"chunk": None, "prev": None, "next": None, "parent": None}

    def _search_bm25_full(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Run BM25 keyword search against the FULL index independently.

        Unlike the old approach (BM25 scoring within vector shortlist), this
        searches all chunks directly. Follows the Fss-Rag pattern where
        keyword and semantic searches run independently before fusion.
        """
        if not self.bm25 or not self.chunk_texts:
            return []

        query_tokens = _tokenize_for_bm25(query)
        scores = self.bm25.get_scores(query_tokens)

        # Get top_k indices by BM25 score
        top_indices = np.argsort(scores)[::-1][:top_k]

        df = self.table.to_pandas()
        results = []

        for idx in top_indices:
            bm25_score = scores[idx]
            if bm25_score <= 0:
                break  # No more relevant results

            # Map BM25 index back to dataframe row
            if idx < len(df):
                row = df.iloc[idx]
                # Normalize BM25 score to 0-1 range (cap at 1.0)
                normalized_score = min(bm25_score / max(scores), 1.0) if max(scores) > 0 else 0.0
                results.append(self._row_to_search_result(row, normalized_score))

        return results

    @staticmethod
    def _rrf_fusion(
        result_lists: List[List[SearchResult]], k: int = 60
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion (RRF) to merge results from multiple search methods.

        RRF score = sum(1 / (k + rank)) across all methods where the result appears.
        k=60 is the standard constant (from the original RRF paper).

        This is rank-based, not score-based, so it works even when score
        distributions differ wildly (e.g. BM25 unbounded vs cosine 0-1).
        """
        # Build RRF scores keyed by (file_path, start_line) for deduplication
        rrf_scores = {}
        result_map = {}

        for result_list in result_lists:
            for rank, result in enumerate(result_list):
                key = (result.file_path, result.start_line, result.end_line)
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
                # Keep the result object (prefer the one with higher original score)
                if key not in result_map or result.score > result_map[key].score:
                    result_map[key] = result

        # Sort by RRF score and assign as the result score
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        fused = []
        for key in sorted_keys:
            result = result_map[key]
            result.score = rrf_scores[key]
            fused.append(result)

        return fused

    def _row_to_search_result(self, row: pd.Series, score: float) -> SearchResult:
        """Convert a DataFrame row to a SearchResult."""
        return SearchResult(
            file_path=display_path(row["file_path"]),
            content=row["content"],
            score=score,
            start_line=row["start_line"],
            end_line=row["end_line"],
            chunk_type=row["chunk_type"],
            name=row["name"],
            language=row["language"],
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        chunk_types: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        file_pattern: Optional[str] = None,
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
        include_context: bool = False,
    ) -> List[SearchResult]:
        """
        Hybrid search using independent semantic + BM25 with RRF fusion.

        Follows the Fss-Rag pattern: semantic and keyword searches run
        independently against the full index, then results are merged
        using Reciprocal Rank Fusion (RRF). This ensures keyword matches
        are found even when embeddings are poor.

        Args:
            query: Natural language search query
            top_k: Maximum number of results to return
            chunk_types: Filter by chunk types (e.g., ['function', 'class'])
            languages: Filter by languages (e.g., ['python', 'javascript'])
            file_pattern: Filter by file path pattern (e.g., '**/test_*.py')
            semantic_weight: Weight for semantic similarity (default 0.7)
            bm25_weight: Weight for BM25 keyword score (default 0.3)
            include_context: Whether to include adjacent and parent chunks

        Returns:
            List of SearchResult objects, sorted by RRF score
        """
        if not self.table:
            raise RuntimeError("Database not connected")

        # Expand query for better recall (if enabled)
        expanded_query = self.query_expander.expand_query(query)
        search_query = expanded_query if expanded_query != query else query

        # --- Run searches INDEPENDENTLY (Fss-Rag pattern) ---
        result_lists = []

        # 1. Semantic search (vector similarity)
        # Skip semantic search if no embedding provider available
        use_semantic = self.embedder.get_mode() not in ("unavailable", "hash")

        if use_semantic:
            query_embedding = self.embedder.embed_query(search_query)
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding, dtype=np.float32)
            else:
                query_embedding = query_embedding.astype(np.float32)

            results_df = (
                self.table.search(query_embedding)
                .limit(top_k * 3)
                .to_pandas()
            )

            semantic_results = []
            if not results_df.empty:
                for _, row in results_df.iterrows():
                    distance = row["_distance"]
                    score = 1 / (1 + distance)
                    semantic_results.append(self._row_to_search_result(row, score))

            result_lists.append(semantic_results)

        # 2. BM25 keyword search (full index, independent)
        bm25_results = self._search_bm25_full(search_query, top_k=top_k * 3)
        result_lists.append(bm25_results)

        # --- Merge with Reciprocal Rank Fusion ---
        fused_results = self._rrf_fusion(result_lists)

        # Apply filters
        if chunk_types:
            fused_results = [r for r in fused_results if r.chunk_type in chunk_types]
        if languages:
            fused_results = [r for r in fused_results if r.language in languages]
        if file_pattern:
            import fnmatch
            fused_results = [r for r in fused_results
                           if fnmatch.fnmatch(r.file_path, file_pattern)]

        # Apply smart re-ranking
        fused_results = self._smart_rerank(fused_results)

        # Apply diversity constraints
        diverse_results = self._apply_diversity_constraints(fused_results, top_k)

        # Consolidate adjacent chunks from same file
        diverse_results = self._consolidate_same_file_results(diverse_results)

        # Add context if requested
        if include_context:
            diverse_results = self._add_context_to_results(diverse_results, results_df)

        return diverse_results

    def _consolidate_same_file_results(
        self, results: List[SearchResult], gap_threshold: int = 1
    ) -> List[SearchResult]:
        """
        Merge adjacent or near-adjacent chunks from the same file into
        contiguous passages. Follows the Fss-Rag gap-filling pattern.

        When search returns chunks at lines [10-20] and [22-35] from the same
        file, they represent one logical passage and should be merged for
        better context.

        Args:
            results: Search results to consolidate
            gap_threshold: Max gap in lines between chunks to merge (default 1)

        Returns:
            Consolidated results with merged adjacent chunks
        """
        if len(results) <= 1:
            return results

        # Group results by file
        from collections import defaultdict
        by_file = defaultdict(list)
        standalone = []

        for r in results:
            by_file[r.file_path].append(r)

        consolidated = []

        for file_path, file_results in by_file.items():
            if len(file_results) == 1:
                consolidated.extend(file_results)
                continue

            # Sort by start_line
            file_results.sort(key=lambda r: r.start_line)

            # Merge adjacent chunks
            merged = [file_results[0]]
            for current in file_results[1:]:
                prev = merged[-1]

                # Check if chunks are adjacent or overlapping
                gap = current.start_line - prev.end_line
                if gap <= gap_threshold + 1:  # +1 because line N end and N+1 start = adjacent
                    # Merge: combine content, extend range, keep best score
                    prev.content = prev.content + "\n" + current.content
                    prev.end_line = max(prev.end_line, current.end_line)
                    prev.score = max(prev.score, current.score)
                    if current.name and prev.name and current.name != prev.name:
                        prev.name = f"{prev.name} + {current.name}"
                else:
                    merged.append(current)

            consolidated.extend(merged)

        # Re-sort by score (merging may have changed scores)
        consolidated.sort(key=lambda r: r.score, reverse=True)
        return consolidated

    def _smart_rerank(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Smart result re-ranking for better quality with zero overhead.

        Boosts scores based on:
        - File importance (README, main files, configs)
        - Content freshness (recently modified files)
        - File type relevance
        """
        now = datetime.now()

        # Only apply boosts to results with meaningful scores.
        # With RRF fusion, scores are small (0.01-0.03) so boosts
        # must not distort relative ranking between relevant and
        # irrelevant results.
        if not results:
            return results
        max_score = max(r.score for r in results)
        boost_threshold = max_score * 0.5  # Only boost top-half results

        for result in results:
            if result.score < boost_threshold:
                continue  # Don't boost low-relevance results

            file_path_lower = str(result.file_path).lower()
            important_patterns = [
                "readme",
                "main.",
                "index.",
                "__init__",
                "config",
                "setup",
                "install",
                "getting",
                "started",
                "docs/",
                "documentation",
                "guide",
                "tutorial",
                "example",
            ]

            if any(pattern in file_path_lower for pattern in important_patterns):
                result.score *= 1.05  # Small boost (was 1.2 - too aggressive with RRF)
                logger.debug(f"Important file boost: {result.file_path}")

            # Recency boost (10% boost for files modified in last week)
            # Note: This uses file modification time if available in the data
            try:
                # Get file modification time (this is lightweight)
                file_mtime = Path(result.file_path).stat().st_mtime
                modified_date = datetime.fromtimestamp(file_mtime)
                days_old = (now - modified_date).days

                if days_old <= 7:  # Modified in last week
                    result.score *= 1.02
                elif days_old <= 30:  # Modified in last month
                    result.score *= 1.01

            except (OSError, ValueError):
                # File doesn't exist or can't get stats - no boost
                pass

            # Content type relevance boost
            if hasattr(result, "chunk_type"):
                if result.chunk_type in ["function", "class", "method"]:
                    # Code definitions are usually more valuable
                    result.score *= 1.1
                elif result.chunk_type in ["comment", "docstring"]:
                    # Documentation is valuable for understanding
                    result.score *= 1.05

            # Penalize very short content (likely not useful)
            if len(result.content.strip()) < 50:
                result.score *= 0.9

            # Small boost for content with good structure (has multiple lines)
            lines = result.content.strip().split("\n")
            if len(lines) >= 3 and any(len(line.strip()) > 10 for line in lines):
                result.score *= 1.02

        # Sort by updated scores
        return sorted(results, key=lambda x: x.score, reverse=True)

    def _apply_diversity_constraints(
        self, results: List[SearchResult], top_k: int
    ) -> List[SearchResult]:
        """
        Apply diversity constraints to search results.

        - Max 2 chunks per file
        - Prefer different chunk types
        - Deduplicate overlapping content
        """
        final_results = []
        file_counts = defaultdict(int)
        seen_content_hashes = set()
        chunk_type_counts = defaultdict(int)

        for result in results:
            # Check file limit
            if file_counts[result.file_path] >= 2:
                continue

            # Check for duplicate/overlapping content
            content_hash = hash(result.content.strip()[:200])  # Hash first 200 chars
            if content_hash in seen_content_hashes:
                continue

            # Prefer diverse chunk types
            if (
                len(final_results) >= top_k // 2
                and chunk_type_counts[result.chunk_type] > top_k // 3
            ):
                # Skip if we have too many of this type already
                continue

            # Add result
            final_results.append(result)
            file_counts[result.file_path] += 1
            seen_content_hashes.add(content_hash)
            chunk_type_counts[result.chunk_type] += 1

            if len(final_results) >= top_k:
                break

        return final_results

    def _add_context_to_results(
        self, results: List[SearchResult], search_df: pd.DataFrame
    ) -> List[SearchResult]:
        """
        Add context (adjacent and parent chunks) to search results.

        Args:
            results: List of search results to add context to
            search_df: DataFrame from the initial search (for finding chunk_id)

        Returns:
            List of SearchResult objects with context added
        """
        # Get full dataframe for context lookups
        full_df = self.table.to_pandas()

        # Create a mapping from result to chunk_id
        result_to_chunk_id = {}
        for result in results:
            # Find matching row in search_df
            matching_rows = search_df[
                (search_df["file_path"] == result.file_path)
                & (search_df["start_line"] == result.start_line)
                & (search_df["end_line"] == result.end_line)
            ]
            if not matching_rows.empty:
                result_to_chunk_id[result] = matching_rows.iloc[0]["chunk_id"]

        # Add context to each result
        for result in results:
            chunk_id = result_to_chunk_id.get(result)
            if not chunk_id:
                continue

            # Get the row for this chunk
            chunk_rows = full_df[full_df["chunk_id"] == chunk_id]
            if chunk_rows.empty:
                continue

            chunk_row = chunk_rows.iloc[0]

            # Add adjacent chunks as context
            if pd.notna(chunk_row.get("prev_chunk_id")):
                prev_rows = full_df[full_df["chunk_id"] == chunk_row["prev_chunk_id"]]
                if not prev_rows.empty:
                    result.context_before = prev_rows.iloc[0]["content"]

            if pd.notna(chunk_row.get("next_chunk_id")):
                next_rows = full_df[full_df["chunk_id"] == chunk_row["next_chunk_id"]]
                if not next_rows.empty:
                    result.context_after = next_rows.iloc[0]["content"]

            # Add parent class chunk if applicable
            if pd.notna(chunk_row.get("parent_class")):
                parent_rows = full_df[
                    (full_df["name"] == chunk_row["parent_class"])
                    & (full_df["chunk_type"] == "class")
                    & (full_df["file_path"] == chunk_row["file_path"])
                ]
                if not parent_rows.empty:
                    parent_row = parent_rows.iloc[0]
                    result.parent_chunk = SearchResult(
                        file_path=display_path(parent_row["file_path"]),
                        content=parent_row["content"],
                        score=1.0,
                        start_line=parent_row["start_line"],
                        end_line=parent_row["end_line"],
                        chunk_type=parent_row["chunk_type"],
                        name=parent_row["name"],
                        language=parent_row["language"],
                    )

        return results

    def search_similar_code(
        self, code_snippet: str, top_k: int = 10, exclude_self: bool = True
    ) -> List[SearchResult]:
        """
        Find code similar to a given snippet using hybrid search.

        Args:
            code_snippet: Code to find similar matches for
            top_k: Maximum number of results
            exclude_self: Whether to exclude exact matches

        Returns:
            List of similar code chunks
        """
        # Use the code snippet as query for hybrid search
        # This will use both semantic similarity and keyword matching
        results = self.search(
            query=code_snippet,
            top_k=top_k * 2 if exclude_self else top_k,
            semantic_weight=0.8,  # Higher semantic weight for code similarity
            bm25_weight=0.2,
        )

        if exclude_self:
            # Filter out exact matches
            filtered_results = []
            for result in results:
                if result.content.strip() != code_snippet.strip():
                    filtered_results.append(result)
                if len(filtered_results) >= top_k:
                    break
            return filtered_results

        return results[:top_k]

    def get_function(self, function_name: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for a specific function by name.

        Args:
            function_name: Name of the function to find
            top_k: Maximum number of results

        Returns:
            List of matching functions
        """
        # Create a targeted query
        query = f"function {function_name} implementation definition"

        # Search with filters
        results = self.search(query, top_k=top_k * 2, chunk_types=["function", "method"])

        # Further filter by name
        filtered = []
        for result in results:
            if result.name and function_name.lower() in result.name.lower():
                filtered.append(result)

        return filtered[:top_k]

    def get_class(self, class_name: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for a specific class by name.

        Args:
            class_name: Name of the class to find
            top_k: Maximum number of results

        Returns:
            List of matching classes
        """
        # Create a targeted query
        query = f"class {class_name} definition implementation"

        # Search with filters
        results = self.search(query, top_k=top_k * 2, chunk_types=["class"])

        # Further filter by name
        filtered = []
        for result in results:
            if result.name and class_name.lower() in result.name.lower():
                filtered.append(result)

        return filtered[:top_k]

    def explain_code(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Find code that helps explain a concept.

        Args:
            query: Concept to explain (e.g., "how to connect to database")
            top_k: Maximum number of examples

        Returns:
            List of relevant code examples
        """
        # Enhance query for explanation
        enhanced_query = f"example implementation {query}"

        return self.search(enhanced_query, top_k=top_k)

    def find_usage(self, identifier: str, top_k: int = 10) -> List[SearchResult]:
        """
        Find usage examples of an identifier (function, class, variable).

        Args:
            identifier: The identifier to find usage for
            top_k: Maximum number of results

        Returns:
            List of usage examples
        """
        # Search for usage patterns
        query = f"using {identifier} calling {identifier} import {identifier}"

        results = self.search(query, top_k=top_k * 2)

        # Filter to ensure identifier appears in content
        filtered = []
        for result in results:
            if identifier in result.content:
                filtered.append(result)

        return filtered[:top_k]

    @staticmethod
    def _score_label(score: float, max_score: float = None) -> str:
        """Interpret search score with a human-readable quality label.

        Auto-detects scoring scale:
        - RRF fusion scores: 0.01-0.05 range (rank-based)
        - Cosine similarity scores: 0.1-1.0 range (distance-based)

        Uses max_score from the result set to determine which scale applies.
        """
        # Determine scale from max_score or the score itself
        reference = max_score if max_score is not None else score

        if reference < 0.1:
            # RRF scale (rank-based fusion scores)
            if score >= 0.035:
                return "[bold green]HIGH[/bold green]"
            elif score >= 0.025:
                return "[green]GOOD[/green]"
            elif score >= 0.018:
                return "[yellow]FAIR[/yellow]"
            elif score >= 0.010:
                return "[dim yellow]LOW[/dim yellow]"
            else:
                return "[dim]WEAK[/dim]"
        else:
            # Cosine similarity scale
            if score >= 0.7:
                return "[bold green]HIGH[/bold green]"
            elif score >= 0.5:
                return "[green]GOOD[/green]"
            elif score >= 0.3:
                return "[yellow]FAIR[/yellow]"
            elif score >= 0.1:
                return "[dim yellow]LOW[/dim yellow]"
            else:
                return "[dim]WEAK[/dim]"

    def display_results(
        self,
        results: List[SearchResult],
        show_content: bool = True,
        max_content_lines: int = 10,
    ):
        """
        Display search results in a formatted table.

        Args:
            results: List of search results
            show_content: Whether to show code content
            max_content_lines: Maximum lines of content to show
        """
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        # Create table
        table = Table(title=f"Search Results ({len(results)} matches)")
        table.add_column("Score", style="cyan", width=12)
        table.add_column("File", style="blue")
        table.add_column("Type", style="green", width=10)
        table.add_column("Name", style="magenta")
        table.add_column("Lines", style="yellow", width=10)

        max_score = max(r.score for r in results) if results else 0.0
        for result in results:
            score_label = self._score_label(result.score, max_score)
            table.add_row(
                f"{result.score:.3f} {score_label}",
                result.file_path,
                result.chunk_type,
                result.name or "-",
                f"{result.start_line}-{result.end_line}",
            )

        console.print(table)

        # Show content if requested
        if show_content and results:
            console.print("\n[bold]Top Results:[/bold]\n")

            for i, result in enumerate(results[:3], 1):
                console.print(
                    f"[bold cyan]#{i}[/bold cyan] {result.file_path}:{result.start_line}"
                )
                console.print(f"[dim]Type: {result.chunk_type} | Name: {result.name}[/dim]")

                # Display code with syntax highlighting
                syntax = Syntax(
                    result.format_for_display(max_content_lines),
                    result.language,
                    theme="monokai",
                    line_numbers=True,
                    start_line=result.start_line,
                )
                console.print(syntax)
                console.print()

    def get_statistics(self) -> Dict[str, Any]:
        """Get search index statistics."""
        if not self.table:
            return {"error": "Database not connected"}

        try:
            # Get table statistics
            num_rows = len(self.table.to_pandas())

            # Get unique files
            df = self.table.to_pandas()
            unique_files = df["file_path"].nunique()

            # Get chunk type distribution
            chunk_types = df["chunk_type"].value_counts().to_dict()

            # Get language distribution
            languages = df["language"].value_counts().to_dict()

            return {
                "total_chunks": num_rows,
                "unique_files": unique_files,
                "chunk_types": chunk_types,
                "languages": languages,
                "index_ready": True,
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}


# Convenience functions


def search_code(project_path: Path, query: str, top_k: int = 10) -> List[SearchResult]:
    """
    Quick search function.

    Args:
        project_path: Path to the project
        query: Search query
        top_k: Maximum results

    Returns:
        List of search results
    """
    searcher = CodeSearcher(project_path)
    return searcher.search(query, top_k=top_k)

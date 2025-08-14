"""
Fast semantic search using LanceDB.
Optimized for code search with relevance scoring.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import lancedb
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rank_bm25 import BM25Okapi
from collections import defaultdict

from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .path_handler import display_path
from .query_expander import QueryExpander
from .config import ConfigManager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
console = Console()


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, 
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
                 parent_chunk: Optional['SearchResult'] = None):
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
            'file_path': self.file_path,
            'content': self.content,
            'score': self.score,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'chunk_type': self.chunk_type,
            'name': self.name,
            'language': self.language,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'parent_chunk': self.parent_chunk.to_dict() if self.parent_chunk else None,
        }
    
    def format_for_display(self, max_lines: int = 10) -> str:
        """Format for display with syntax highlighting."""
        lines = self.content.splitlines()
        if len(lines) > max_lines:
            # Show first and last few lines
            half = max_lines // 2
            lines = lines[:half] + ['...'] + lines[-half:]
        
        return '\n'.join(lines)


class CodeSearcher:
    """Semantic code search using vector similarity."""
    
    def __init__(self, 
                 project_path: Path,
                 embedder: Optional[CodeEmbedder] = None):
        """
        Initialize searcher.
        
        Args:
            project_path: Path to the project
            embedder: CodeEmbedder instance (creates one if not provided)
        """
        self.project_path = Path(project_path).resolve()
        self.rag_dir = self.project_path / '.mini-rag'
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
                print(f"   Rebuild index: rm -rf {self.rag_dir} && ./rag-mini index {self.project_path}")
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
                
                # Tokenize for BM25 (simple word splitting)
                tokens = searchable_text.lower().split()
                
                self.chunk_texts.append(tokens)
                self.chunk_ids.append(idx)
            
            # Build BM25 index
            self.bm25 = BM25Okapi(self.chunk_texts)
            logger.info(f"Built BM25 index with {len(self.chunk_texts)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.bm25 = None
    
    def get_chunk_context(self, chunk_id: str, include_adjacent: bool = True, include_parent: bool = True) -> Dict[str, Any]:
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
            chunk_rows = df[df['chunk_id'] == chunk_id]
            
            if chunk_rows.empty:
                return {'chunk': None, 'prev': None, 'next': None, 'parent': None}
            
            chunk_row = chunk_rows.iloc[0]
            context = {'chunk': self._row_to_search_result(chunk_row, score=1.0)}
            
            # Get adjacent chunks if requested
            if include_adjacent:
                # Get previous chunk
                if pd.notna(chunk_row.get('prev_chunk_id')):
                    prev_rows = df[df['chunk_id'] == chunk_row['prev_chunk_id']]
                    if not prev_rows.empty:
                        context['prev'] = self._row_to_search_result(prev_rows.iloc[0], score=1.0)
                    else:
                        context['prev'] = None
                else:
                    context['prev'] = None
                
                # Get next chunk
                if pd.notna(chunk_row.get('next_chunk_id')):
                    next_rows = df[df['chunk_id'] == chunk_row['next_chunk_id']]
                    if not next_rows.empty:
                        context['next'] = self._row_to_search_result(next_rows.iloc[0], score=1.0)
                    else:
                        context['next'] = None
                else:
                    context['next'] = None
            else:
                context['prev'] = None
                context['next'] = None
            
            # Get parent class chunk if requested and applicable
            if include_parent and pd.notna(chunk_row.get('parent_class')):
                # Find the parent class chunk
                parent_rows = df[(df['name'] == chunk_row['parent_class']) & 
                               (df['chunk_type'] == 'class') &
                               (df['file_path'] == chunk_row['file_path'])]
                if not parent_rows.empty:
                    context['parent'] = self._row_to_search_result(parent_rows.iloc[0], score=1.0)
                else:
                    context['parent'] = None
            else:
                context['parent'] = None
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get chunk context: {e}")
            return {'chunk': None, 'prev': None, 'next': None, 'parent': None}
    
    def _row_to_search_result(self, row: pd.Series, score: float) -> SearchResult:
        """Convert a DataFrame row to a SearchResult."""
        return SearchResult(
            file_path=display_path(row['file_path']),
            content=row['content'],
            score=score,
            start_line=row['start_line'],
            end_line=row['end_line'],
            chunk_type=row['chunk_type'],
            name=row['name'],
            language=row['language']
        )
    
    def search(self, 
              query: str, 
              top_k: int = 10,
              chunk_types: Optional[List[str]] = None,
              languages: Optional[List[str]] = None,
              file_pattern: Optional[str] = None,
              semantic_weight: float = 0.7,
              bm25_weight: float = 0.3,
              include_context: bool = False) -> List[SearchResult]:
        """
        Hybrid search for code similar to the query using both semantic and BM25.
        
        Args:
            query: Natural language search query
            top_k: Maximum number of results to return
            chunk_types: Filter by chunk types (e.g., ['function', 'class'])
            languages: Filter by languages (e.g., ['python', 'javascript'])
            file_pattern: Filter by file path pattern (e.g., '**/test_*.py')
            semantic_weight: Weight for semantic similarity (default 0.7)
            bm25_weight: Weight for BM25 keyword score (default 0.3)
            include_context: Whether to include adjacent and parent chunks for each result
            
        Returns:
            List of SearchResult objects, sorted by combined relevance
        """
        if not self.table:
            raise RuntimeError("Database not connected")
        
        # Expand query for better recall (if enabled)
        expanded_query = self.query_expander.expand_query(query)
        
        # Use original query for display but expanded query for search
        search_query = expanded_query if expanded_query != query else query
        
        # Embed the expanded query for semantic search
        query_embedding = self.embedder.embed_query(search_query)
        
        # Ensure query is a numpy array of float32
        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.array(query_embedding, dtype=np.float32)
        else:
            query_embedding = query_embedding.astype(np.float32)
            
        # Get more results for hybrid scoring
        results_df = (
            self.table.search(query_embedding)
            .limit(top_k * 4)  # Get extra results for filtering and diversity
            .to_pandas()
        )
        
        if results_df.empty:
            return []
        
        # Apply filters first
        if chunk_types:
            results_df = results_df[results_df['chunk_type'].isin(chunk_types)]
        
        if languages:
            results_df = results_df[results_df['language'].isin(languages)]
        
        if file_pattern:
            import fnmatch
            mask = results_df['file_path'].apply(
                lambda x: fnmatch.fnmatch(x, file_pattern)
            )
            results_df = results_df[mask]
        
        # Calculate BM25 scores if available
        if self.bm25:
            # Tokenize expanded query for BM25
            query_tokens = search_query.lower().split()
            
            # Get BM25 scores for all chunks in results
            bm25_scores = {}
            for idx, row in results_df.iterrows():
                if idx in self.chunk_ids:
                    chunk_idx = self.chunk_ids.index(idx)
                    bm25_score = self.bm25.get_scores(query_tokens)[chunk_idx]
                    # Normalize BM25 score to 0-1 range
                    bm25_scores[idx] = min(bm25_score / 10.0, 1.0)
                else:
                    bm25_scores[idx] = 0.0
        else:
            bm25_scores = {idx: 0.0 for idx in results_df.index}
        
        # Calculate hybrid scores
        hybrid_results = []
        for idx, row in results_df.iterrows():
            # Semantic score (convert distance to similarity)
            distance = row['_distance']
            semantic_score = 1 / (1 + distance)
            
            # BM25 score
            bm25_score = bm25_scores.get(idx, 0.0)
            
            # Combined score
            combined_score = (semantic_weight * semantic_score + 
                            bm25_weight * bm25_score)
            
            result = SearchResult(
                file_path=display_path(row['file_path']),
                content=row['content'],
                score=combined_score,
                start_line=row['start_line'],
                end_line=row['end_line'],
                chunk_type=row['chunk_type'],
                name=row['name'],
                language=row['language']
            )
            hybrid_results.append(result)
        
        # Apply smart re-ranking for better quality (zero overhead)
        hybrid_results = self._smart_rerank(hybrid_results)
        
        # Apply diversity constraints
        diverse_results = self._apply_diversity_constraints(hybrid_results, top_k)
        
        # Add context if requested
        if include_context:
            diverse_results = self._add_context_to_results(diverse_results, results_df)
        
        return diverse_results
    
    def _smart_rerank(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Smart result re-ranking for better quality with zero overhead.
        
        Boosts scores based on:
        - File importance (README, main files, configs)
        - Content freshness (recently modified files)
        - File type relevance
        """
        now = datetime.now()
        
        for result in results:
            # File importance boost (20% boost for important files)
            file_path_lower = str(result.file_path).lower()
            important_patterns = [
                'readme', 'main.', 'index.', '__init__', 'config',
                'setup', 'install', 'getting', 'started', 'docs/',
                'documentation', 'guide', 'tutorial', 'example'
            ]
            
            if any(pattern in file_path_lower for pattern in important_patterns):
                result.score *= 1.2
                logger.debug(f"Important file boost: {result.file_path}")
            
            # Recency boost (10% boost for files modified in last week)
            # Note: This uses file modification time if available in the data
            try:
                # Get file modification time (this is lightweight)
                file_mtime = Path(result.file_path).stat().st_mtime
                modified_date = datetime.fromtimestamp(file_mtime)
                days_old = (now - modified_date).days
                
                if days_old <= 7:  # Modified in last week
                    result.score *= 1.1
                    logger.debug(f"Recent file boost: {result.file_path} ({days_old} days old)")
                elif days_old <= 30:  # Modified in last month
                    result.score *= 1.05
                    
            except (OSError, ValueError):
                # File doesn't exist or can't get stats - no boost
                pass
            
            # Content type relevance boost
            if hasattr(result, 'chunk_type'):
                if result.chunk_type in ['function', 'class', 'method']:
                    # Code definitions are usually more valuable
                    result.score *= 1.1
                elif result.chunk_type in ['comment', 'docstring']:
                    # Documentation is valuable for understanding
                    result.score *= 1.05
            
            # Penalize very short content (likely not useful)
            if len(result.content.strip()) < 50:
                result.score *= 0.9
            
            # Small boost for content with good structure (has multiple lines)
            lines = result.content.strip().split('\n')
            if len(lines) >= 3 and any(len(line.strip()) > 10 for line in lines):
                result.score *= 1.02
        
        # Sort by updated scores
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _apply_diversity_constraints(self, results: List[SearchResult], top_k: int) -> List[SearchResult]:
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
            if len(final_results) >= top_k // 2 and chunk_type_counts[result.chunk_type] > top_k // 3:
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
    
    def _add_context_to_results(self, results: List[SearchResult], search_df: pd.DataFrame) -> List[SearchResult]:
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
                (search_df['file_path'] == result.file_path) &
                (search_df['start_line'] == result.start_line) &
                (search_df['end_line'] == result.end_line)
            ]
            if not matching_rows.empty:
                result_to_chunk_id[result] = matching_rows.iloc[0]['chunk_id']
        
        # Add context to each result
        for result in results:
            chunk_id = result_to_chunk_id.get(result)
            if not chunk_id:
                continue
                
            # Get the row for this chunk
            chunk_rows = full_df[full_df['chunk_id'] == chunk_id]
            if chunk_rows.empty:
                continue
                
            chunk_row = chunk_rows.iloc[0]
            
            # Add adjacent chunks as context
            if pd.notna(chunk_row.get('prev_chunk_id')):
                prev_rows = full_df[full_df['chunk_id'] == chunk_row['prev_chunk_id']]
                if not prev_rows.empty:
                    result.context_before = prev_rows.iloc[0]['content']
            
            if pd.notna(chunk_row.get('next_chunk_id')):
                next_rows = full_df[full_df['chunk_id'] == chunk_row['next_chunk_id']]
                if not next_rows.empty:
                    result.context_after = next_rows.iloc[0]['content']
            
            # Add parent class chunk if applicable
            if pd.notna(chunk_row.get('parent_class')):
                parent_rows = full_df[
                    (full_df['name'] == chunk_row['parent_class']) & 
                    (full_df['chunk_type'] == 'class') &
                    (full_df['file_path'] == chunk_row['file_path'])
                ]
                if not parent_rows.empty:
                    parent_row = parent_rows.iloc[0]
                    result.parent_chunk = SearchResult(
                        file_path=display_path(parent_row['file_path']),
                        content=parent_row['content'],
                        score=1.0,
                        start_line=parent_row['start_line'],
                        end_line=parent_row['end_line'],
                        chunk_type=parent_row['chunk_type'],
                        name=parent_row['name'],
                        language=parent_row['language']
                    )
        
        return results
    
    def search_similar_code(self, 
                          code_snippet: str, 
                          top_k: int = 10,
                          exclude_self: bool = True) -> List[SearchResult]:
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
            bm25_weight=0.2
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
        results = self.search(
            query,
            top_k=top_k * 2,
            chunk_types=['function', 'method']
        )
        
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
        results = self.search(
            query,
            top_k=top_k * 2,
            chunk_types=['class']
        )
        
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
    
    def display_results(self, 
                       results: List[SearchResult], 
                       show_content: bool = True,
                       max_content_lines: int = 10):
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
        table.add_column("Score", style="cyan", width=6)
        table.add_column("File", style="blue")
        table.add_column("Type", style="green", width=10)
        table.add_column("Name", style="magenta")
        table.add_column("Lines", style="yellow", width=10)
        
        for result in results:
            table.add_row(
                f"{result.score:.3f}",
                result.file_path,
                result.chunk_type,
                result.name or "-",
                f"{result.start_line}-{result.end_line}"
            )
        
        console.print(table)
        
        # Show content if requested
        if show_content and results:
            console.print("\n[bold]Top Results:[/bold]\n")
            
            for i, result in enumerate(results[:3], 1):
                console.print(f"[bold cyan]#{i}[/bold cyan] {result.file_path}:{result.start_line}")
                console.print(f"[dim]Type: {result.chunk_type} | Name: {result.name}[/dim]")
                
                # Display code with syntax highlighting
                syntax = Syntax(
                    result.format_for_display(max_content_lines),
                    result.language,
                    theme="monokai",
                    line_numbers=True,
                    start_line=result.start_line
                )
                console.print(syntax)
                console.print()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get search index statistics."""
        if not self.table:
            return {'error': 'Database not connected'}
        
        try:
            # Get table statistics
            num_rows = len(self.table.to_pandas())
            
            # Get unique files
            df = self.table.to_pandas()
            unique_files = df['file_path'].nunique()
            
            # Get chunk type distribution
            chunk_types = df['chunk_type'].value_counts().to_dict()
            
            # Get language distribution
            languages = df['language'].value_counts().to_dict()
            
            return {
                'total_chunks': num_rows,
                'unique_files': unique_files,
                'chunk_types': chunk_types,
                'languages': languages,
                'index_ready': True,
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}


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
#!/usr/bin/env python3
"""
Test and benchmark the hybrid BM25 + semantic search system.
Shows performance metrics and search quality comparisons.
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.syntax import Syntax
from rich.progress import track

from mini_rag.search import CodeSearcher, SearchResult
from mini_rag.embeddings import CodeEmbedder

console = Console()


class SearchTester:
    """Test harness for hybrid search evaluation."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        console.print(f"\n[cyan]Initializing search system for: {project_path}[/cyan]")
        
        # Initialize searcher
        start = time.time()
        self.searcher = CodeSearcher(project_path)
        init_time = time.time() - start
        
        console.print(f"[green] Initialized in {init_time:.2f}s[/green]")
        
        # Get statistics
        stats = self.searcher.get_statistics()
        if 'error' not in stats:
            console.print(f"[dim]Index contains {stats['total_chunks']} chunks from {stats['unique_files']} files[/dim]\n")
    
    def run_query(self, query: str, limit: int = 10, 
                  semantic_only: bool = False,
                  bm25_only: bool = False) -> Dict[str, Any]:
        """Run a single query and return metrics."""
        
        # Set weights based on mode
        if semantic_only:
            semantic_weight, bm25_weight = 1.0, 0.0
            mode = "Semantic Only"
        elif bm25_only:
            semantic_weight, bm25_weight = 0.0, 1.0
            mode = "BM25 Only"
        else:
            semantic_weight, bm25_weight = 0.7, 0.3
            mode = "Hybrid (70/30)"
        
        # Run search
        start = time.time()
        results = self.searcher.search(
            query=query,
            limit=limit,
            semantic_weight=semantic_weight,
            bm25_weight=bm25_weight
        )
        search_time = time.time() - start
        
        return {
            'query': query,
            'mode': mode,
            'results': results,
            'search_time_ms': search_time * 1000,
            'num_results': len(results),
            'top_score': results[0].score if results else 0,
            'avg_score': sum(r.score for r in results) / len(results) if results else 0,
        }
    
    def compare_search_modes(self, query: str, limit: int = 5):
        """Compare results across different search modes."""
        console.print(f"\n[bold cyan]Query:[/bold cyan] '{query}'")
        console.print(f"[dim]Top {limit} results per mode[/dim]\n")
        
        # Run searches in all modes
        modes = [
            ('hybrid', False, False),
            ('semantic', True, False),
            ('bm25', False, True)
        ]
        
        all_results = {}
        for mode_name, semantic_only, bm25_only in modes:
            result = self.run_query(query, limit, semantic_only, bm25_only)
            all_results[mode_name] = result
        
        # Create comparison table
        table = Table(title="Search Mode Comparison")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Hybrid (70/30)", style="green")
        table.add_column("Semantic Only", style="blue")
        table.add_column("BM25 Only", style="magenta")
        
        # Add metrics
        table.add_row(
            "Search Time (ms)",
            f"{all_results['hybrid']['search_time_ms']:.1f}",
            f"{all_results['semantic']['search_time_ms']:.1f}",
            f"{all_results['bm25']['search_time_ms']:.1f}"
        )
        
        table.add_row(
            "Results Found",
            str(all_results['hybrid']['num_results']),
            str(all_results['semantic']['num_results']),
            str(all_results['bm25']['num_results'])
        )
        
        table.add_row(
            "Top Score",
            f"{all_results['hybrid']['top_score']:.3f}",
            f"{all_results['semantic']['top_score']:.3f}",
            f"{all_results['bm25']['top_score']:.3f}"
        )
        
        table.add_row(
            "Avg Score",
            f"{all_results['hybrid']['avg_score']:.3f}",
            f"{all_results['semantic']['avg_score']:.3f}",
            f"{all_results['bm25']['avg_score']:.3f}"
        )
        
        console.print(table)
        
        # Show top results from each mode
        console.print("\n[bold]Top Results by Mode:[/bold]")
        
        for mode_name, result_data in all_results.items():
            console.print(f"\n[bold cyan]{result_data['mode']}:[/bold cyan]")
            for i, result in enumerate(result_data['results'][:3], 1):
                console.print(f"\n{i}. [green]{result.file_path}[/green]:{result.start_line}-{result.end_line}")
                console.print(f"   [dim]Type: {result.chunk_type} | Name: {result.name} | Score: {result.score:.3f}[/dim]")
                
                # Show snippet
                lines = result.content.splitlines()[:5]
                for line in lines:
                    console.print(f"   [dim]{line[:80]}{'...' if len(line) > 80 else ''}[/dim]")
    
    def test_query_types(self):
        """Test different types of queries to show system capabilities."""
        test_queries = [
            # Keyword-heavy queries (should benefit from BM25)
            {
                'query': 'class CodeSearcher search method',
                'description': 'Specific class and method names',
                'expected': 'Should find exact matches with BM25 boost'
            },
            {
                'query': 'import pandas numpy torch',
                'description': 'Multiple import keywords',
                'expected': 'BM25 should excel at finding import statements'
            },
            
            # Semantic queries (should benefit from embeddings)
            {
                'query': 'find similar code chunks using vector similarity',
                'description': 'Natural language description',
                'expected': 'Semantic search should understand intent'
            },
            {
                'query': 'how to initialize database connection',
                'description': 'How-to question',
                'expected': 'Semantic search should find relevant implementations'
            },
            
            # Mixed queries (benefit from hybrid)
            {
                'query': 'BM25 scoring implementation for search ranking',
                'description': 'Technical terms + intent',
                'expected': 'Hybrid should balance keyword and semantic matching'
            },
            {
                'query': 'embedding vectors for code search with transformers',
                'description': 'Domain-specific terminology',
                'expected': 'Hybrid should leverage both approaches'
            }
        ]
        
        console.print("\n[bold yellow]Query Type Analysis[/bold yellow]")
        console.print("[dim]Testing different query patterns to demonstrate hybrid search benefits[/dim]\n")
        
        for test_case in test_queries:
            console.rule(f"\n[cyan]{test_case['description']}[/cyan]")
            console.print(f"[dim]{test_case['expected']}[/dim]")
            self.compare_search_modes(test_case['query'], limit=3)
            time.sleep(0.5)  # Brief pause between tests
    
    def benchmark_performance(self, num_queries: int = 50):
        """Run performance benchmarks."""
        console.print("\n[bold yellow]Performance Benchmark[/bold yellow]")
        console.print(f"[dim]Running {num_queries} queries to measure performance[/dim]\n")
        
        # Sample queries for benchmarking
        benchmark_queries = [
            "search function implementation",
            "class definition with methods",
            "import statements and dependencies",
            "error handling try except",
            "database connection setup",
            "api endpoint handler",
            "test cases unit testing",
            "configuration settings",
            "logging and debugging",
            "performance optimization"
        ] * (num_queries // 10 + 1)
        
        benchmark_queries = benchmark_queries[:num_queries]
        
        # Benchmark each mode
        modes = [
            ('Hybrid (70/30)', 0.7, 0.3),
            ('Semantic Only', 1.0, 0.0),
            ('BM25 Only', 0.0, 1.0)
        ]
        
        results_table = Table(title="Performance Benchmark Results")
        results_table.add_column("Mode", style="cyan")
        results_table.add_column("Avg Time (ms)", style="green")
        results_table.add_column("Min Time (ms)", style="blue")
        results_table.add_column("Max Time (ms)", style="red")
        results_table.add_column("Total Time (s)", style="magenta")
        
        for mode_name, sem_weight, bm25_weight in modes:
            times = []
            
            console.print(f"[cyan]Testing {mode_name}...[/cyan]")
            for query in track(benchmark_queries, description=f"Running {mode_name}"):
                start = time.time()
                self.searcher.search(
                    query=query,
                    limit=10,
                    semantic_weight=sem_weight,
                    bm25_weight=bm25_weight
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            
            # Calculate statistics
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            total_time = sum(times) / 1000
            
            results_table.add_row(
                mode_name,
                f"{avg_time:.2f}",
                f"{min_time:.2f}",
                f"{max_time:.2f}",
                f"{total_time:.2f}"
            )
        
        console.print("\n")
        console.print(results_table)
    
    def test_diversity_constraints(self):
        """Test the diversity constraints in search results."""
        console.print("\n[bold yellow]Diversity Constraints Test[/bold yellow]")
        console.print("[dim]Verifying max 2 chunks per file and chunk type diversity[/dim]\n")
        
        # Query that might return many results from same files
        query = "function implementation code search"
        results = self.searcher.search(query, limit=20)
        
        # Analyze diversity
        file_counts = {}
        chunk_types = {}
        
        for result in results:
            file_counts[result.file_path] = file_counts.get(result.file_path, 0) + 1
            chunk_types[result.chunk_type] = chunk_types.get(result.chunk_type, 0) + 1
        
        # Create diversity report
        table = Table(title="Result Diversity Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Results", str(len(results)))
        table.add_row("Unique Files", str(len(file_counts)))
        table.add_row("Max Chunks per File", str(max(file_counts.values()) if file_counts else 0))
        table.add_row("Unique Chunk Types", str(len(chunk_types)))
        
        console.print(table)
        
        # Show file distribution
        if len(file_counts) > 0:
            console.print("\n[bold]File Distribution:[/bold]")
            for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {count}x {file_path}")
        
        # Show chunk type distribution
        if len(chunk_types) > 0:
            console.print("\n[bold]Chunk Type Distribution:[/bold]")
            for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
                console.print(f"  {chunk_type}: {count} chunks")
        
        # Verify constraints
        console.print("\n[bold]Constraint Verification:[/bold]")
        max_per_file = max(file_counts.values()) if file_counts else 0
        if max_per_file <= 2:
            console.print("  [green] Max 2 chunks per file constraint satisfied[/green]")
        else:
            console.print(f"  [red] Max chunks per file exceeded: {max_per_file}[/red]")


def main():
    """Run comprehensive hybrid search tests."""
    import sys
    
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = Path.cwd()
    
    if not (project_path / '.mini-rag').exists():
        console.print("[red]Error: No RAG index found. Run 'mini-rag index' first.[/red]")
        return
    
    # Create tester
    tester = SearchTester(project_path)
    
    # Run all tests
    console.print("\n" + "="*80)
    console.print("[bold green]Mini RAG Hybrid Search Test Suite[/bold green]")
    console.print("="*80)
    
    # Test 1: Query type analysis
    tester.test_query_types()
    
    # Test 2: Performance benchmark
    console.print("\n" + "-"*80)
    tester.benchmark_performance(num_queries=30)
    
    # Test 3: Diversity constraints
    console.print("\n" + "-"*80)
    tester.test_diversity_constraints()
    
    # Summary
    console.print("\n" + "="*80)
    console.print("[bold green]Test Suite Complete![/bold green]")
    console.print("\n[dim]The hybrid search combines:")
    console.print("  • Semantic understanding from transformer embeddings")
    console.print("  • Keyword relevance from BM25 scoring")
    console.print("  • Result diversity through intelligent filtering")
    console.print("  • Performance optimization through concurrent processing[/dim]")
    console.print("="*80 + "\n")


if __name__ == "__main__":
    main()
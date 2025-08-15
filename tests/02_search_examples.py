#!/usr/bin/env python3
"""
Simple demo of the hybrid search system showing real results.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

from mini_rag.search import CodeSearcher

console = Console()


def demo_search(project_path: Path):
    """Run demo searches showing the hybrid system in action."""
    
    console.print("\n[bold cyan]Mini RAG Hybrid Search Demo[/bold cyan]\n")
    
    # Initialize searcher
    console.print("Initializing search system...")
    searcher = CodeSearcher(project_path)
    
    # Get index stats
    stats = searcher.get_statistics()
    if 'error' not in stats:
        console.print(f"\n[green] Index ready:[/green] {stats['total_chunks']} chunks from {stats['unique_files']} files")
        console.print(f"[dim]Languages: {', '.join(stats['languages'].keys())}[/dim]")
        console.print(f"[dim]Chunk types: {', '.join(stats['chunk_types'].keys())}[/dim]\n")
    
    # Demo queries
    demos = [
        {
            'title': 'Keyword-Heavy Search',
            'query': 'BM25Okapi rank_bm25 search scoring',
            'description': 'This query has specific technical keywords that BM25 excels at finding',
            'top_k': 5
        },
        {
            'title': 'Natural Language Query',
            'query': 'how to build search index from database chunks',
            'description': 'This semantic query benefits from transformer embeddings understanding intent',
            'top_k': 5
        },
        {
            'title': 'Mixed Technical Query',
            'query': 'vector embeddings for semantic code search with transformers',
            'description': 'This hybrid query combines technical terms with conceptual understanding',
            'top_k': 5
        },
        {
            'title': 'Function Search',
            'query': 'search method implementation with filters',
            'description': 'Looking for specific function implementations',
            'top_k': 5
        }
    ]
    
    for demo in demos:
        console.rule(f"\n[bold yellow]{demo['title']}[/bold yellow]")
        console.print(f"[dim]{demo['description']}[/dim]")
        console.print(f"\n[cyan]Query:[/cyan] '{demo['query']}'")
        
        # Run search with hybrid mode
        results = searcher.search(
            query=demo['query'],
            top_k=demo['top_k'],
            semantic_weight=0.7,
            bm25_weight=0.3
        )
        
        if not results:
            console.print("[red]No results found![/red]")
            continue
        
        console.print(f"\n[green]Found {len(results)} results:[/green]\n")
        
        # Show each result
        for i, result in enumerate(results, 1):
            # Create result panel
            header = f"#{i} {result.file_path}:{result.start_line}-{result.end_line}"
            
            # Get code preview
            lines = result.content.splitlines()
            if len(lines) > 10:
                preview_lines = lines[:8] + ['...'] + lines[-2:]
            else:
                preview_lines = lines
            
            preview = '\n'.join(preview_lines)
            
            # Create info table
            info = Table.grid(padding=0)
            info.add_column(style="cyan", width=12)
            info.add_column(style="white")
            
            info.add_row("Score:", f"{result.score:.3f}")
            info.add_row("Type:", result.chunk_type)
            info.add_row("Name:", result.name or "N/A")
            info.add_row("Language:", result.language)
            
            # Display result
            console.print(Panel(
                f"{info}\n\n[dim]{preview}[/dim]",
                title=header,
                title_align="left",
                border_style="blue"
            ))
        
        # Show scoring breakdown for top result
        if results:
            console.print("\n[dim]Top result hybrid score: {:.3f} (70% semantic + 30% BM25)[/dim]".format(results[0].score))


def main():
    """Run the demo."""
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Use the RAG system itself as the demo project
        project_path = Path(__file__).parent
    
    if not (project_path / '.mini-rag').exists():
        console.print("[red]Error: No RAG index found. Run 'rag-mini index' first.[/red]")
        console.print(f"[dim]Looked in: {project_path / '.mini-rag'}[/dim]")
        return
    
    demo_search(project_path)


if __name__ == "__main__":
    main()
"""
Command-line interface for Mini RAG system.
Beautiful, intuitive, and highly effective.
"""

import click
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Fix Windows console for proper emoji/Unicode support
from .windows_console_fix import fix_windows_console
fix_windows_console()

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
from rich.syntax import Syntax
from rich.panel import Panel
from rich import print as rprint

from .indexer import ProjectIndexer
from .search import CodeSearcher
from .watcher import FileWatcher
from .non_invasive_watcher import NonInvasiveFileWatcher
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .chunker import CodeChunker
from .performance import get_monitor
from .server import RAGClient
from .server import RAGServer, RAGClient, start_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress output')
def cli(verbose: bool, quiet: bool):
    """
    Mini RAG - Fast semantic code search that actually works.
    
    A local RAG system for improving the development environment's grounding capabilities.
    Indexes your codebase and enables lightning-fast semantic search.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.', 
              help='Project path to index')
@click.option('--force', '-f', is_flag=True, 
              help='Force reindex all files')
@click.option('--reindex', '-r', is_flag=True, 
              help='Force complete reindex (same as --force)')
@click.option('--model', '-m', type=str, default=None,
              help='Embedding model to use')
def init(path: str, force: bool, reindex: bool, model: Optional[str]):
    """Initialize RAG index for a project."""
    project_path = Path(path).resolve()
    
    console.print(f"\n[bold cyan]Initializing Mini RAG for:[/bold cyan] {project_path}\n")
    
    # Check if already initialized
    rag_dir = project_path / '.mini-rag'
    force_reindex = force or reindex
    if rag_dir.exists() and not force_reindex:
        console.print("[yellow][/yellow]  Project already initialized!")
        console.print("Use --force or --reindex to reindex all files\n")
        
        # Show current stats
        indexer = ProjectIndexer(project_path)
        stats = indexer.get_statistics()
        
        table = Table(title="Current Index Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Files Indexed", str(stats['file_count']))
        table.add_row("Total Chunks", str(stats['chunk_count']))
        table.add_row("Index Size", f"{stats['index_size_mb']:.2f} MB")
        table.add_row("Last Updated", stats['indexed_at'] or "Never")
        
        console.print(table)
        return
    
    # Initialize components
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Initialize embedder
            task = progress.add_task("[cyan]Loading embedding model...", total=None)
            embedder = CodeEmbedder(model_name=model)
            progress.update(task, completed=True)
            
            # Create indexer
            task = progress.add_task("[cyan]Creating indexer...", total=None)
            indexer = ProjectIndexer(
                project_path,
                embedder=embedder
            )
            progress.update(task, completed=True)
        
        # Run indexing
        console.print("\n[bold green]Starting indexing...[/bold green]\n")
        stats = indexer.index_project(force_reindex=force_reindex)
        
        # Show summary
        if stats['files_indexed'] > 0:
            console.print(f"\n[bold green] Success![/bold green] Indexed {stats['files_indexed']} files")
            console.print(f"Created {stats['chunks_created']} searchable chunks")
            console.print(f"Time: {stats['time_taken']:.2f} seconds")
            console.print(f"Speed: {stats['files_per_second']:.1f} files/second")
        else:
            console.print("\n[green] All files are already up to date![/green]")
        
        # Show how to use
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  • Search your code: [cyan]mini-rag search \"your query\"[/cyan]")
        console.print("  • Watch for changes: [cyan]mini-rag watch[/cyan]")
        console.print("  • View statistics: [cyan]mini-rag stats[/cyan]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Initialization failed")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--top-k', '-k', type=int, default=10,
              help='Maximum results to show')
@click.option('--type', '-t', multiple=True,
              help='Filter by chunk type (function, class, method)')
@click.option('--lang', multiple=True,
              help='Filter by language (python, javascript, etc.)')
@click.option('--show-content', '-c', is_flag=True,
              help='Show code content in results')
@click.option('--show-perf', is_flag=True,
              help='Show performance metrics')
def search(query: str, path: str, top_k: int, type: tuple, lang: tuple, show_content: bool, show_perf: bool):
    """Search codebase using semantic similarity."""
    project_path = Path(path).resolve()
    
    # Check if indexed
    rag_dir = project_path / '.mini-rag'
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'mini-rag init' first.")
        sys.exit(1)
    
    # Get performance monitor
    monitor = get_monitor() if show_perf else None
    
    # Check if server is running
    client = RAGClient()
    use_server = client.is_running()
    
    try:
        if use_server:
            # Use server for fast queries
            console.print("[dim]Using RAG server...[/dim]")
            
            response = client.search(query, top_k=top_k)
            
            if response.get('success'):
                # Convert response to SearchResult objects
                from .search import SearchResult
                results = []
                for r in response['results']:
                    result = SearchResult(
                        file_path=r['file_path'],
                        content=r['content'],
                        score=r['score'],
                        start_line=r['start_line'],
                        end_line=r['end_line'],
                        chunk_type=r['chunk_type'],
                        name=r['name'],
                        language=r['language']
                    )
                    results.append(result)
                
                # Show server stats
                search_time = response.get('search_time_ms', 0)
                total_queries = response.get('total_queries', 0)
                console.print(f"[dim]Search time: {search_time}ms (Query #{total_queries})[/dim]\n")
            else:
                console.print(f"[red]Server error:[/red] {response.get('error')}")
                sys.exit(1)
        else:
            # Fall back to direct search
            # Create searcher with timing
            if monitor:
                with monitor.measure("Initialize (Load Model + Connect DB)"):
                    searcher = CodeSearcher(project_path)
            else:
                searcher = CodeSearcher(project_path)
            
            # Perform search with timing
            if monitor:
                with monitor.measure("Execute Vector Search"):
                    results = searcher.search(
                        query,
                        top_k=top_k,
                        chunk_types=list(type) if type else None,
                        languages=list(lang) if lang else None
                    )
            else:
                with console.status(f"[cyan]Searching for: {query}[/cyan]"):
                    results = searcher.search(
                        query,
                        top_k=top_k,
                        chunk_types=list(type) if type else None,
                        languages=list(lang) if lang else None
                    )
        
        # Display results
        if results:
            if use_server:
                # Need a searcher instance just for display
                display_searcher = CodeSearcher.__new__(CodeSearcher)
                display_searcher.console = console
                display_searcher.display_results(results, show_content=show_content)
            else:
                searcher.display_results(results, show_content=show_content)
            
            # Copy first result to clipboard if available
            try:
                import pyperclip
                first_result = results[0]
                location = f"{first_result.file_path}:{first_result.start_line}"
                pyperclip.copy(location)
                console.print(f"\n[dim]First result location copied to clipboard: {location}[/dim]")
            except:
                pass
        else:
            console.print(f"\n[yellow]No results found for: {query}[/yellow]")
            console.print("\n[dim]Tips:[/dim]")
            console.print("  • Try different keywords")
            console.print("  • Use natural language queries")
        
        # Show performance summary
        if monitor:
            monitor.print_summary()
            console.print("  • Check if files are indexed with 'mini-rag stats'")
        
    except Exception as e:
        console.print(f"\n[bold red]Search error:[/bold red] {e}")
        logger.exception("Search failed")
        sys.exit(1)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
def stats(path: str):
    """Show index statistics."""
    project_path = Path(path).resolve()
    
    # Check if indexed
    rag_dir = project_path / '.mini-rag'
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'mini-rag init' first.")
        sys.exit(1)
    
    try:
        # Get statistics
        indexer = ProjectIndexer(project_path)
        index_stats = indexer.get_statistics()
        
        searcher = CodeSearcher(project_path)
        search_stats = searcher.get_statistics()
        
        # Display project info
        console.print(f"\n[bold cyan]Project:[/bold cyan] {project_path.name}")
        console.print(f"[dim]Path: {project_path}[/dim]\n")
        
        # Index statistics table
        table = Table(title="Index Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Files Indexed", str(index_stats['file_count']))
        table.add_row("Total Chunks", str(index_stats['chunk_count']))
        table.add_row("Index Size", f"{index_stats['index_size_mb']:.2f} MB")
        table.add_row("Last Updated", index_stats['indexed_at'] or "Never")
        
        console.print(table)
        
        # Language distribution
        if 'languages' in search_stats:
            console.print("\n[bold]Language Distribution:[/bold]")
            lang_table = Table()
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Chunks", style="green")
            
            for lang, count in sorted(search_stats['languages'].items(), 
                                     key=lambda x: x[1], reverse=True):
                lang_table.add_row(lang, str(count))
            
            console.print(lang_table)
        
        # Chunk type distribution
        if 'chunk_types' in search_stats:
            console.print("\n[bold]Chunk Types:[/bold]")
            type_table = Table()
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="green")
            
            for chunk_type, count in sorted(search_stats['chunk_types'].items(),
                                           key=lambda x: x[1], reverse=True):
                type_table.add_row(chunk_type, str(count))
            
            console.print(type_table)
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to get statistics")
        sys.exit(1)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
def debug_schema(path: str):
    """Debug vector database schema and sample data."""
    project_path = Path(path).resolve()
    
    try:
        rag_dir = project_path / '.mini-rag'
        
        if not rag_dir.exists():
            console.print("[red]No RAG index found. Run 'init' first.[/red]")
            return
        
        # Connect to database
        import lancedb
        db = lancedb.connect(rag_dir)
        
        if "code_vectors" not in db.table_names():
            console.print("[red]No code_vectors table found.[/red]")
            return
        
        table = db.open_table("code_vectors")
        
        # Print schema
        console.print("\n[bold cyan] Table Schema:[/bold cyan]")
        console.print(table.schema)
        
        # Get sample data
        import pandas as pd
        df = table.to_pandas()
        console.print(f"\n[bold cyan] Table Statistics:[/bold cyan]")
        console.print(f"Total rows: {len(df)}")
        
        if len(df) > 0:
            # Check embedding column
            console.print(f"\n[bold cyan] Embedding Column Analysis:[/bold cyan]")
            first_embedding = df['embedding'].iloc[0]
            console.print(f"Type: {type(first_embedding)}")
            if hasattr(first_embedding, 'shape'):
                console.print(f"Shape: {first_embedding.shape}")
            if hasattr(first_embedding, 'dtype'):
                console.print(f"Dtype: {first_embedding.dtype}")
            
            # Show first few rows
            console.print(f"\n[bold cyan] Sample Data (first 3 rows):[/bold cyan]")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                console.print(f"\n[yellow]Row {i}:[/yellow]")
                console.print(f"  chunk_id: {row['chunk_id']}")
                console.print(f"  file_path: {row['file_path']}")
                console.print(f"  content: {row['content'][:50]}...")
                console.print(f"  embedding: {type(row['embedding'])} of length {len(row['embedding']) if hasattr(row['embedding'], '__len__') else 'unknown'}")
        
    except Exception as e:
        logger.error(f"Schema debug failed: {e}")
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--delay', '-d', type=float, default=10.0,
              help='Update delay in seconds (default: 10s for non-invasive)')
@click.option('--silent', '-s', is_flag=True, default=False,
              help='Run silently in background without output')
def watch(path: str, delay: float, silent: bool):
    """Watch for file changes and update index automatically (non-invasive by default)."""
    project_path = Path(path).resolve()
    
    # Check if indexed
    rag_dir = project_path / '.mini-rag'
    if not rag_dir.exists():
        if not silent:
            console.print("[red]Error:[/red] Project not indexed. Run 'mini-rag init' first.")
        sys.exit(1)
    
    try:
        # Always use non-invasive watcher
        watcher = NonInvasiveFileWatcher(project_path)
        
        # Only show startup messages if not silent
        if not silent:
            console.print(f"\n[bold green]🕊️ Non-Invasive Watcher:[/bold green] {project_path}")
            console.print("[dim]Low CPU/memory usage - won't interfere with development[/dim]")
            console.print(f"[dim]Update delay: {delay}s[/dim]")
            console.print("\n[yellow]Press Ctrl+C to stop watching[/yellow]\n")
        
        # Start watching
        watcher.start()
        
        if silent:
            # Silent mode: just wait for interrupt without any output
            try:
                while True:
                    time.sleep(60)  # Check every minute for interrupt
            except KeyboardInterrupt:
                pass
        else:
            # Interactive mode: display updates
            last_stats = None
            while True:
                try:
                    time.sleep(1)
                    
                    # Get current statistics
                    stats = watcher.get_statistics()
                    
                    # Only update display if something changed
                    if stats != last_stats:
                        # Clear previous line
                        console.print(
                            f"\r[green]✓[/green] Files updated: {stats.get('files_processed', 0)} | "
                            f"[red]✗[/red] Failed: {stats.get('files_dropped', 0)} | "
                            f"[cyan]⧗[/cyan] Queue: {stats['queue_size']}",
                            end=""
                        )
                        last_stats = stats
                    
                except KeyboardInterrupt:
                    break
        
        # Stop watcher
        if not silent:
            console.print("\n\n[yellow]Stopping watcher...[/yellow]")
        watcher.stop()
        
        # Show final stats only if not silent
        if not silent:
            final_stats = watcher.get_statistics()
            console.print(f"\n[bold green]Watch Summary:[/bold green]")
            console.print(f"Files updated: {final_stats.get('files_processed', 0)}")
            console.print(f"Files failed: {final_stats.get('files_dropped', 0)}")
            console.print(f"Total runtime: {final_stats.get('uptime_seconds', 0):.1f} seconds\n")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Watch failed")
        sys.exit(1)


@cli.command()
@click.argument('function_name')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--top-k', '-k', type=int, default=5,
              help='Maximum results')
def find_function(function_name: str, path: str, top_k: int):
    """Find a specific function by name."""
    project_path = Path(path).resolve()
    
    try:
        searcher = CodeSearcher(project_path)
        results = searcher.get_function(function_name, top_k=top_k)
        
        if results:
            searcher.display_results(results, show_content=True)
        else:
            console.print(f"[yellow]No functions found matching: {function_name}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('class_name')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--top-k', '-k', type=int, default=5,
              help='Maximum results')
def find_class(class_name: str, path: str, top_k: int):
    """Find a specific class by name."""
    project_path = Path(path).resolve()
    
    try:
        searcher = CodeSearcher(project_path)
        results = searcher.get_class(class_name, top_k=top_k)
        
        if results:
            searcher.display_results(results, show_content=True)
        else:
            console.print(f"[yellow]No classes found matching: {class_name}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
def update(path: str):
    """Update index for changed files."""
    project_path = Path(path).resolve()
    
    # Check if indexed
    rag_dir = project_path / '.mini-rag'
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'mini-rag init' first.")
        sys.exit(1)
    
    try:
        indexer = ProjectIndexer(project_path)
        
        console.print(f"\n[cyan]Checking for changes in {project_path}...[/cyan]\n")
        
        stats = indexer.index_project(force_reindex=False)
        
        if stats['files_indexed'] > 0:
            console.print(f"[green][/green] Updated {stats['files_indexed']} files")
            console.print(f"Created {stats['chunks_created']} new chunks")
        else:
            console.print("[green] All files are up to date![/green]")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--show-code', '-c', is_flag=True, help='Show example code')
def info(show_code: bool):
    """Show information about Mini RAG."""
    # Create info panel
    info_text = """
[bold cyan]Mini RAG[/bold cyan] - Local Semantic Code Search

[bold]Features:[/bold]
• Fast code indexing with AST-aware chunking
• Semantic search using CodeBERT embeddings
• Real-time file watching and incremental updates
• Language-aware parsing for Python, JS, Go, and more
• MCP integration for the development environment

[bold]How it works:[/bold]
1. Indexes your codebase into semantic chunks
2. Stores vectors locally in .mini-rag/ directory
3. Enables natural language search across your code
4. Updates automatically as you modify files

[bold]Performance:[/bold]
• Indexing: ~50-100 files/second
• Search: <50ms latency
• Storage: ~200MB for 10k files
"""
    
    panel = Panel(info_text, title="About Mini RAG", border_style="cyan")
    console.print(panel)
    
    if show_code:
        console.print("\n[bold]Example Usage:[/bold]\n")
        
        code = """# Initialize a project
mini-rag init

# Search for code
mini-rag search "database connection"
mini-rag search "auth middleware" --type function

# Find specific functions or classes
mini-rag find-function connect_to_db
mini-rag find-class UserModel

# Watch for changes
mini-rag watch

# Get statistics
mini-rag stats"""
        
        syntax = Syntax(code, "bash", theme="monokai")
        console.print(syntax)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--port', type=int, default=7777,
              help='Server port')
def server(path: str, port: int):
    """Start persistent RAG server (keeps model loaded)."""
    project_path = Path(path).resolve()
    
    # Check if indexed
    rag_dir = project_path / '.mini-rag'
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'mini-rag init' first.")
        sys.exit(1)
    
    try:
        console.print(f"[bold cyan]Starting RAG server for:[/bold cyan] {project_path}")
        console.print(f"[dim]Port: {port}[/dim]\n")
        
        start_server(project_path, port)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Server error:[/bold red] {e}")
        logger.exception("Server failed")
        sys.exit(1)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
              help='Project path')
@click.option('--port', type=int, default=7777,
              help='Server port')
@click.option('--discovery', '-d', is_flag=True,
              help='Run codebase discovery analysis')
def status(path: str, port: int, discovery: bool):
    """Show comprehensive RAG system status with optional codebase discovery."""
    project_path = Path(path).resolve()
    
    # Print header
    console.print(f"\n[bold cyan]RAG System Status for:[/bold cyan] {project_path.name}")
    console.print(f"[dim]Path: {project_path}[/dim]\n")
    
    # Check folder contents
    console.print("[bold]📁 Folder Contents:[/bold]")
    try:
        all_files = list(project_path.rglob("*"))
        source_files = [f for f in all_files if f.is_file() and f.suffix in ['.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.h']]
        
        console.print(f"   • Total files: {len([f for f in all_files if f.is_file()])}")
        console.print(f"   • Source files: {len(source_files)}")
        console.print(f"   • Directories: {len([f for f in all_files if f.is_dir()])}")
    except Exception as e:
        console.print(f"   [red]Error reading folder: {e}[/red]")
    
    # Check index status
    console.print("\n[bold]🗂️ Index Status:[/bold]")
    rag_dir = project_path / '.mini-rag'
    if rag_dir.exists():
        try:
            indexer = ProjectIndexer(project_path)
            index_stats = indexer.get_statistics()
            
            console.print(f"   • Status: [green]✅ Indexed[/green]")
            console.print(f"   • Files indexed: {index_stats['file_count']}")
            console.print(f"   • Total chunks: {index_stats['chunk_count']}")
            console.print(f"   • Index size: {index_stats['index_size_mb']:.2f} MB")
            console.print(f"   • Last updated: {index_stats['indexed_at'] or 'Never'}")
        except Exception as e:
            console.print(f"   • Status: [yellow]⚠️ Index exists but has issues[/yellow]")
            console.print(f"   • Error: {e}")
    else:
        console.print("   • Status: [red]❌ Not indexed[/red]")
        console.print("   • Run 'rag-start' to initialize")
    
    # Check server status
    console.print("\n[bold]🚀 Server Status:[/bold]")
    client = RAGClient(port)
    
    if client.is_running():
        console.print(f"   • Status: [green]✅ Running on port {port}[/green]")
        
        # Try to get server info
        try:
            response = client.search("test", top_k=1)  # Minimal query to get stats
            if response.get('success'):
                uptime = response.get('server_uptime', 0)
                queries = response.get('total_queries', 0)
                console.print(f"   • Uptime: {uptime}s")
                console.print(f"   • Total queries: {queries}")
        except Exception as e:
            console.print(f"   • [yellow]Server responding but with issues: {e}[/yellow]")
    else:
        console.print(f"   • Status: [red]❌ Not running on port {port}[/red]")
        console.print("   • Run 'rag-start' to start server")
    
    # Run codebase discovery if requested
    if discovery and rag_dir.exists():
        console.print("\n[bold]🧠 Codebase Discovery:[/bold]")
        try:
            # Import and run intelligent discovery
            import sys
            
            # Add tools directory to path  
            tools_path = Path(__file__).parent.parent.parent / "tools"
            if tools_path.exists():
                sys.path.insert(0, str(tools_path))
                from intelligent_codebase_discovery import IntelligentCodebaseDiscovery
                
                discovery_system = IntelligentCodebaseDiscovery(project_path)
                discovery_system.run_lightweight_discovery()
            else:
                console.print("   [yellow]Discovery system not found[/yellow]")
                
        except Exception as e:
            console.print(f"   [red]Discovery failed: {e}[/red]")
    
    elif discovery and not rag_dir.exists():
        console.print("\n[bold]🧠 Codebase Discovery:[/bold]")
        console.print("   [yellow]❌ Cannot run discovery - project not indexed[/yellow]")
        console.print("   Run 'rag-start' first to initialize the system")
    
    # Show next steps
    console.print("\n[bold]📋 Next Steps:[/bold]")
    if not rag_dir.exists():
        console.print("   1. Run [cyan]rag-start[/cyan] to initialize and start RAG system")
        console.print("   2. Use [cyan]rag-search \"your query\"[/cyan] to search code")
    elif not client.is_running():
        console.print("   1. Run [cyan]rag-start[/cyan] to start the server")
        console.print("   2. Use [cyan]rag-search \"your query\"[/cyan] to search code")
    else:
        console.print("   • System ready! Use [cyan]rag-search \"your query\"[/cyan] to search")
        console.print("   • Add [cyan]--discovery[/cyan] flag to run intelligent codebase analysis")
    
    console.print()


if __name__ == '__main__':
    cli()
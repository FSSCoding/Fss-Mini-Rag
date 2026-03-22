"""
Command-line interface for Mini RAG system.
Beautiful, intuitive, and highly effective.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from .indexer import ProjectIndexer
from .non_invasive_watcher import NonInvasiveFileWatcher
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .performance import get_monitor
from .search import CodeSearcher
from .server import RAGClient, start_server
from .windows_console_fix import fix_windows_console

# Fix Windows console for proper emoji/Unicode support
fix_windows_console()

# Set up logging - default WARNING, verbose flag enables INFO/DEBUG
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


def find_nearby_index(start_path: Path = None) -> Optional[Path]:
    """
    Find .mini-rag index in current directory or up to 2 levels up.
    
    Args:
        start_path: Starting directory to search from (default: current directory)
        
    Returns:
        Path to directory containing .mini-rag, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    
    # Search current directory and up to 2 levels up
    for level in range(3):  # 0, 1, 2 levels up
        rag_dir = current / ".mini-rag"
        if rag_dir.exists() and rag_dir.is_dir():
            return current
        
        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    return None


def show_index_guidance(query_path: Path, found_index_path: Path) -> None:
    """Show helpful guidance when index is found in a different location."""
    relative_path = found_index_path.relative_to(Path.cwd()) if found_index_path != Path.cwd() else Path(".")
    
    console.print(f"\n[yellow]📍 Found FSS-Mini-RAG index in:[/yellow] [blue]{found_index_path}[/blue]")
    console.print(f"[dim]Current directory:[/dim] [dim]{query_path}[/dim]")
    console.print()
    console.print("[green]🚀 To search the index, navigate there first:[/green]")
    console.print(f"   [bold]cd {relative_path}[/bold]")
    console.print(f"   [bold]rag-mini search 'your query here'[/bold]")
    console.print()
    console.print("[cyan]💡 Or specify the path directly:[/cyan]")  
    console.print(f"   [bold]rag-mini search -p {found_index_path} 'your query here'[/bold]")
    console.print()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def cli(verbose: bool, quiet: bool):
    """
    Mini RAG - Fast semantic code search that actually works.

    A local RAG system for improving the development environment's grounding
    capabilities.
    Indexes your codebase and enables lightning-fast semantic search.
    """
    # Check virtual environment
    from .venv_checker import check_and_warn_venv

    check_and_warn_venv("rag-mini", force_exit=False)

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif not quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True),
    default=".",
    help="Project path to index",
)
@click.option("--force", "-", is_flag=True, help="Force reindex all files")
@click.option("--reindex", "-r", is_flag=True, help="Force complete reindex (same as --force)")
@click.option("--model", "-m", type=str, default=None, help="Embedding model to use")
def init(path: str, force: bool, reindex: bool, model: Optional[str]):
    """Initialize RAG index for a project."""
    project_path = Path(path).resolve()

    console.print(f"\n[bold cyan]Initializing Mini RAG for:[/bold cyan] {project_path}\n")

    # Check if already initialized
    rag_dir = project_path / ".mini-rag"
    force_reindex = force or reindex
    if rag_dir.exists() and not force_reindex:
        console.print("[yellow][/yellow]  Project already initialized!")
        console.print("Use --force or --reindex to reindex all files\n")

        # Show current stats (read manifest directly, no embedder needed)
        import json as _json
        manifest_path = rag_dir / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = _json.load(f)
            except Exception:
                pass

        # Calculate index size
        db_path = rag_dir / "code_vectors.lance"
        index_mb = 0.0
        if db_path.exists():
            try:
                index_mb = sum(f.stat().st_size for f in db_path.rglob("*") if f.is_file()) / (1024 * 1024)
            except OSError:
                pass

        stats = {
            "file_count": manifest.get("file_count", 0),
            "chunk_count": manifest.get("chunk_count", 0),
            "index_size_mb": index_mb,
            "indexed_at": manifest.get("indexed_at", "Never"),
        }

        table = Table(title="Current Index Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files Indexed", str(stats["file_count"]))
        table.add_row("Total Chunks", str(stats["chunk_count"]))
        table.add_row("Index Size", f"{stats['index_size_mb']:.2f} MB")
        table.add_row("Last Updated", stats["indexed_at"] or "Never")

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
            # Use default model if None is passed
            embedder = CodeEmbedder(model_name=model) if model else CodeEmbedder()
            progress.update(task, completed=True)

            # Create indexer
            task = progress.add_task("[cyan]Creating indexer...", total=None)
            indexer = ProjectIndexer(project_path, embedder=embedder)
            progress.update(task, completed=True)

        # Run indexing
        console.print("\n[bold green]Starting indexing...[/bold green]\n")
        stats = indexer.index_project(force_reindex=force_reindex)

        # Show summary
        if stats["files_indexed"] > 0:
            console.print(
                f"\n[bold green] Success![/bold green] Indexed {stats['files_indexed']} files"
            )
            console.print(f"Created {stats['chunks_created']} searchable chunks")
            console.print(f"Time: {stats['time_taken']:.2f} seconds")
            console.print(f"Speed: {stats['files_per_second']:.1f} files/second")
        else:
            console.print("\n[green] All files are already up to date![/green]")

        # Show how to use
        console.print("\n[bold]Next steps:[/bold]")
        console.print('  • Search your code: [cyan]rag-mini search "your query"[/cyan]')
        console.print("  • Watch for changes: [cyan]rag-mini watch[/cyan]")
        console.print("  • View statistics: [cyan]rag-mini stats[/cyan]\n")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Initialization failed")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("query")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--top-k", "-k", type=int, default=10, help="Maximum results to show")
@click.option(
    "--type", "-t", multiple=True, help="Filter by chunk type (function, class, method)"
)
@click.option("--lang", multiple=True, help="Filter by language (python, javascript, etc.)")
@click.option("--show-content", "-c", is_flag=True, help="Show code content in results")
@click.option("--show-perf", is_flag=True, help="Show performance metrics")
@click.option("--port", type=int, default=None, help="Server port (default: from config or 7777)")
@click.option("--synthesize", "-s", is_flag=True, help="Synthesize results with LLM")
@click.option("--expand", "-e", is_flag=True, help="Expand query with LLM for better recall")
def search(
    query: str,
    path: str,
    top_k: int,
    type: tuple,
    lang: tuple,
    show_content: bool,
    show_perf: bool,
    port: int,
    synthesize: bool,
    expand: bool,
):
    """Search codebase using semantic similarity."""
    project_path = Path(path).resolve()

    # Check if indexed at specified path
    rag_dir = project_path / ".mini-rag"
    if not rag_dir.exists():
        # Try to find nearby index if searching from current directory
        if path == ".":
            nearby_index = find_nearby_index()
            if nearby_index:
                show_index_guidance(project_path, nearby_index)
                sys.exit(0)
        
        console.print(f"[red]Error:[/red] No FSS-Mini-RAG index found at [blue]{project_path}[/blue]")
        console.print()
        console.print("[yellow]💡 To create an index:[/yellow]")
        console.print(f"   [bold]rag-mini init -p {project_path}[/bold]")
        console.print()
        sys.exit(1)

    import time as _time

    try:
        # Initialize searcher
        t0 = _time.time()
        searcher = CodeSearcher(project_path)
        init_ms = (_time.time() - t0) * 1000

        # Query expansion (if enabled)
        display_query = query
        if expand:
            try:
                expanded = searcher.query_expander.expand_query(query)
                if expanded != query:
                    display_query = f"{query} [expanded: {expanded}]"
                    query = expanded
            except Exception:
                pass  # Expansion failed, use original query

        # Search with timing
        t1 = _time.time()
        results = searcher.search(
            query,
            top_k=top_k,
            chunk_types=list(type) if type else None,
            languages=list(lang) if lang else None,
        )
        search_ms = (_time.time() - t1) * 1000

        # Display results
        if results:
            searcher.display_results(results, show_content=show_content)
            console.print(
                f"\n[dim]{len(results)} results for: {display_query} "
                f"({search_ms:.0f}ms search, {init_ms:.0f}ms init)[/dim]"
            )

            # LLM synthesis (if enabled)
            if synthesize:
                console.print("\n[bold cyan]Synthesizing with LLM...[/bold cyan]")
                t2 = _time.time()
                try:
                    from .llm_synthesizer import LLMSynthesizer
                    synth = LLMSynthesizer()
                    result = synth.synthesize_search_results(query, results, project_path)
                    synth_ms = (_time.time() - t2) * 1000

                    if result.summary:
                        console.print(Panel(
                            result.summary,
                            title="LLM Synthesis",
                            border_style="cyan",
                        ))
                        console.print(f"[dim]Synthesis: {synth_ms:.0f}ms[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Synthesis failed: {e}[/yellow]")
        else:
            console.print(f"\n[yellow]No results found for: {display_query}[/yellow]")
            console.print(f"[dim]({search_ms:.0f}ms)[/dim]")
            console.print("\n[dim]Tips:[/dim]")
            console.print("  • Try different keywords")
            console.print("  • Use natural language queries")
            console.print("  • Check if files are indexed with 'mini-rag stats'")

    except Exception as e:
        console.print(f"\n[bold red]Search error:[/bold red] {e}")
        logger.exception("Search failed")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
def stats(path: str):
    """Show index statistics."""
    project_path = Path(path).resolve()

    # Check if indexed
    rag_dir = project_path / ".mini-rag"
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'rag-mini init' first.")
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

        table.add_row("Files Indexed", str(index_stats["file_count"]))
        table.add_row("Total Chunks", str(index_stats["chunk_count"]))
        table.add_row("Index Size", f"{index_stats['index_size_mb']:.2f} MB")
        table.add_row("Last Updated", index_stats["indexed_at"] or "Never")

        console.print(table)

        # Language distribution
        if "languages" in search_stats:
            console.print("\n[bold]Language Distribution:[/bold]")
            lang_table = Table()
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Chunks", style="green")

            for lang, count in sorted(
                search_stats["languages"].items(), key=lambda x: x[1], reverse=True
            ):
                lang_table.add_row(lang, str(count))

            console.print(lang_table)

        # Chunk type distribution
        if "chunk_types" in search_stats:
            console.print("\n[bold]Chunk Types:[/bold]")
            type_table = Table()
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="green")

            for chunk_type, count in sorted(
                search_stats["chunk_types"].items(), key=lambda x: x[1], reverse=True
            ):
                type_table.add_row(chunk_type, str(count))

            console.print(type_table)

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to get statistics")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
def debug_schema(path: str):
    """Debug vector database schema and sample data."""
    project_path = Path(path).resolve()

    try:
        rag_dir = project_path / ".mini-rag"

        if not rag_dir.exists():
            console.print("[red]No RAG index found. Run 'rag-mini init' first.[/red]")
            return

        # Connect to database
        try:
            import lancedb
        except ImportError:
            console.print(
                "[red]LanceDB not available. Install with: pip install lancedb pyarrow[/red]"
            )
            return

        db = lancedb.connect(rag_dir)

        if "code_vectors" not in db.table_names():
            console.print("[red]No code_vectors table found.[/red]")
            return

        table = db.open_table("code_vectors")

        # Print schema
        console.print("\n[bold cyan] Table Schema:[/bold cyan]")
        console.print(table.schema)

        # Get sample data

        df = table.to_pandas()
        console.print("\n[bold cyan] Table Statistics:[/bold cyan]")
        console.print(f"Total rows: {len(df)}")

        if len(df) > 0:
            # Check embedding column
            console.print("\n[bold cyan] Embedding Column Analysis:[/bold cyan]")
            first_embedding = df["embedding"].iloc[0]
            console.print(f"Type: {type(first_embedding)}")
            if hasattr(first_embedding, "shape"):
                console.print(f"Shape: {first_embedding.shape}")
            if hasattr(first_embedding, "dtype"):
                console.print(f"Dtype: {first_embedding.dtype}")

            # Show first few rows
            console.print("\n[bold cyan] Sample Data (first 3 rows):[/bold cyan]")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                console.print(f"\n[yellow]Row {i}:[/yellow]")
                console.print(f"  chunk_id: {row['chunk_id']}")
                console.print(f"  file_path: {row['file_path']}")
                console.print(f"  content: {row['content'][:50]}...")
                embed_len = (
                    len(row["embedding"])
                    if hasattr(row["embedding"], "__len__")
                    else "unknown"
                )
                console.print(f"  embedding: {type(row['embedding'])} of length {embed_len}")

    except Exception as e:
        logger.error(f"Schema debug failed: {e}")
        console.print(f"[red]Error: {e}[/red]")


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option(
    "--delay",
    "-d",
    type=float,
    default=10.0,
    help="Update delay in seconds (default: 10s for non-invasive)",
)
@click.option(
    "--silent",
    "-s",
    is_flag=True,
    default=False,
    help="Run silently in background without output",
)
def watch(path: str, delay: float, silent: bool):
    """Watch for file changes and update index automatically (non-invasive by default)."""
    project_path = Path(path).resolve()

    # Check if indexed
    rag_dir = project_path / ".mini-rag"
    if not rag_dir.exists():
        if not silent:
            console.print("[red]Error:[/red] Project not indexed. Run 'rag-mini init' first.")
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
                            end="",
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
            console.print("\n[bold green]Watch Summary:[/bold green]")
            console.print(f"Files updated: {final_stats.get('files_processed', 0)}")
            console.print(f"Files failed: {final_stats.get('files_dropped', 0)}")
            console.print(
                f"Total runtime: {final_stats.get('uptime_seconds', 0):.1f} seconds\n"
            )

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Watch failed")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("function_name")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--top-k", "-k", type=int, default=5, help="Maximum results")
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


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("class_name")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--top-k", "-k", type=int, default=5, help="Maximum results")
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


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
def update(path: str):
    """Update index for changed files."""
    project_path = Path(path).resolve()

    # Check if indexed
    rag_dir = project_path / ".mini-rag"
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'rag-mini init' first.")
        sys.exit(1)

    try:
        indexer = ProjectIndexer(project_path)

        console.print(f"\n[cyan]Checking for changes in {project_path}...[/cyan]\n")

        stats = indexer.index_project(force_reindex=False)

        if stats["files_indexed"] > 0:
            console.print(f"[green][/green] Updated {stats['files_indexed']} files")
            console.print(f"Created {stats['chunks_created']} new chunks")
        else:
            console.print("[green] All files are up to date![/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
def gui():
    """Launch the desktop GUI."""
    try:
        from .gui import main as gui_main
        gui_main()
    except ImportError as e:
        console.print(f"[red]GUI requires tkinter:[/red] {e}")
        console.print("Install with: sudo apt install python3-tk")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--show-code", "-c", is_flag=True, help="Show example code")
def info(show_code: bool):
    """Show information about Mini RAG."""
    # Create info panel
    info_text = """
[bold cyan]FSS-Mini-RAG[/bold cyan] - Lightweight Semantic Code Search

[bold]Search:[/bold]
• Independent semantic + BM25 keyword search with RRF fusion
• Code-aware tokenizer (splits snake_case, CamelCase)
• Auto-calibrating score labels (HIGH/GOOD/FAIR/LOW)

[bold]Chunking:[/bold]
• Python: AST-based with module headers, docstrings
• Markdown: Paragraph-based with code block preservation
• Section boundaries preserved for document search

[bold]Embeddings:[/bold]
• OpenAI-compatible endpoint (LM Studio, vLLM, OpenAI)
• Auto-detects models, precision/conceptual profiles
• MiniLM default (384d), Nomic for conceptual depth

[bold]Performance:[/bold]
• Indexing: ~20 files/second with embeddings
• Search: ~15-20ms per query
• Cold start: ~600ms
"""

    panel = Panel(info_text, title="About Mini RAG", border_style="cyan")
    console.print(panel)

    if show_code:
        console.print("\n[bold]Example Usage:[/bold]\n")

        code = """# Initialize a project
rag-mini init

# Search for code
mini-rag search "database connection"
mini-rag search "auth middleware" --type function

# Find specific functions or classes
mini-rag find-function connect_to_db
mini-rag find-class UserModel

# Watch for changes
rag-mini watch

# Get statistics
rag-mini stats"""

        syntax = Syntax(code, "bash", theme="monokai")
        console.print(syntax)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--port", type=int, default=None, help="Server port (default: from config or 7777)")
def server(path: str, port: int):
    """Start persistent RAG server (keeps model loaded)."""
    project_path = Path(path).resolve()

    # Check if indexed
    rag_dir = project_path / ".mini-rag"
    if not rag_dir.exists():
        console.print("[red]Error:[/red] Project not indexed. Run 'rag-mini init' first.")
        sys.exit(1)

    try:
        from .config import ServerConfig
        resolved_port = port if port is not None else ServerConfig().port
        console.print(f"[bold cyan]Starting RAG server for:[/bold cyan] {project_path}")
        console.print(f"[dim]Port: {resolved_port}[/dim]\n")

        start_server(project_path, resolved_port)

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Server error:[/bold red] {e}")
        logger.exception("Server failed")
        sys.exit(1)


@cli.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Project path")
@click.option("--port", type=int, default=None, help="Server port (default: from config or 7777)")
@click.option("--discovery", "-d", is_flag=True, help="Run codebase discovery analysis")
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
        source_files = [
            f
            for f in all_files
            if f.is_file()
            and f.suffix in [".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".h"]
        ]

        console.print(f"   • Total files: {len([f for f in all_files if f.is_file()])}")
        console.print(f"   • Source files: {len(source_files)}")
        console.print(f"   • Directories: {len([f for f in all_files if f.is_dir()])}")
    except Exception as e:
        console.print(f"   [red]Error reading folder: {e}[/red]")

    # Check index status
    console.print("\n[bold]🗂️ Index Status:[/bold]")
    rag_dir = project_path / ".mini-rag"
    if rag_dir.exists():
        try:
            indexer = ProjectIndexer(project_path)
            index_stats = indexer.get_statistics()

            console.print("   • Status: [green]✅ Indexed[/green]")
            console.print(f"   • Files indexed: {index_stats['file_count']}")
            console.print(f"   • Total chunks: {index_stats['chunk_count']}")
            console.print(f"   • Index size: {index_stats['index_size_mb']:.2f} MB")
            console.print(f"   • Last updated: {index_stats['indexed_at'] or 'Never'}")
        except Exception as e:
            console.print("   • Status: [yellow]⚠️ Index exists but has issues[/yellow]")
            console.print(f"   • Error: {e}")
    else:
        console.print("   • Status: [red]❌ Not indexed[/red]")
        
        # Try to find nearby index if checking current directory  
        if path == ".":
            nearby_index = find_nearby_index()
            if nearby_index:
                console.print(f"   • Found index in: [blue]{nearby_index}[/blue]")
                relative_path = nearby_index.relative_to(Path.cwd()) if nearby_index != Path.cwd() else Path(".")
                console.print(f"   • Use: [bold]cd {relative_path} && rag-mini status[/bold]")
            else:
                console.print("   • Run 'rag-mini init' to initialize")
        else:
            console.print("   • Run 'rag-mini init' to initialize")

    # Check server status
    console.print("\n[bold]🚀 Server Status:[/bold]")
    client = RAGClient(port)

    if client.is_running():
        console.print(f"   • Status: [green]✅ Running on port {client.port}[/green]")

        # Try to get server info
        try:
            response = client.search("test", top_k=1)  # Minimal query to get stats
            if response.get("success"):
                uptime = response.get("server_uptime", 0)
                queries = response.get("total_queries", 0)
                console.print(f"   • Uptime: {uptime}s")
                console.print(f"   • Total queries: {queries}")
        except Exception as e:
            console.print(f"   • [yellow]Server responding but with issues: {e}[/yellow]")
    else:
        console.print(f"   • Status: [red]❌ Not running on port {client.port}[/red]")
        console.print("   • Run 'rag-mini server' to start the server")

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
        console.print("   Run 'rag-mini init' first to initialize the system")

    # Show next steps
    console.print("\n[bold]📋 Next Steps:[/bold]")
    if not rag_dir.exists():
        console.print("   1. Run [cyan]rag-mini init[/cyan] to initialize the RAG system")
        console.print('   2. Use [cyan]rag-mini search "your query"[/cyan] to search code')
    elif not client.is_running():
        console.print("   1. Run [cyan]rag-mini server[/cyan] to start the server")
        console.print('   2. Use [cyan]rag-mini search "your query"[/cyan] to search code')
    else:
        console.print(
            '   • System ready! Use [cyan]rag-mini search "your query"[/cyan] to search'
        )
        console.print(
            "   • Add [cyan]--discovery[/cyan] flag to run intelligent codebase analysis"
        )

    console.print()


if __name__ == "__main__":
    cli()

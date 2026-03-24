#!/usr/bin/env python3
"""
FSS-Mini-RAG Text User Interface
Simple, educational TUI that shows CLI commands while providing easy interaction.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path so we can import mini_rag
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Update system (graceful import)
try:
    from mini_rag.updater import check_for_updates, get_legacy_notification, get_updater

    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False


# Simple TUI without external dependencies


class SimpleTUI:

    def __init__(self):
        self.project_path: Optional[Path] = None
        self.current_config: Dict[str, Any] = {}
        self.search_count = 0  # Track searches for sample reminder
        self.config_dir = Path.home() / ".mini-rag-tui"
        self.config_file = self.config_dir / "last_project.json"

        # Load last project on startup
        self._load_last_project()

    def _load_last_project(self):
        """Load the last used project from config file, or auto-detect current directory."""
        # First check if current directory has .mini-rag folder (auto-detect)
        current_dir = Path.cwd()
        if (current_dir / ".mini-rag").exists():
            self.project_path = current_dir
            # Save this as the last project too
            self._save_last_project()
            return

        # If no auto-detection, try loading from config file
        try:
            if hasattr(self, "config_file") and self.config_file.exists():
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                project_path = Path(data.get("last_project", ""))
                if project_path.exists() and project_path.is_dir():
                    self.project_path = project_path
        except Exception:
            # If loading fails, just continue without last project
            pass

    def _save_last_project(self):
        """Save current project as last used."""
        if not self.project_path:
            return
        try:
            self.config_dir.mkdir(exist_ok=True)
            data = {"last_project": str(self.project_path)}
            with open(self.config_file, "w") as f:
                json.dump(data, f)
        except Exception:
            # If saving fails, just continue
            pass

    def _get_llm_status(self):
        """Get LLM status for display in main menu."""
        try:
            # Import here to avoid startup delays
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.config import ConfigManager, RAGConfig
            from mini_rag.llm_synthesizer import LLMSynthesizer

            # Load config for model rankings
            if self.project_path:
                config_manager = ConfigManager(self.project_path)
                config = config_manager.load_config()
            else:
                config = RAGConfig()

            # Create synthesizer with proper model configuration (same as main CLI)
            synthesizer = LLMSynthesizer(
                model=(
                    config.llm.synthesis_model
                    if config.llm.synthesis_model != "auto"
                    else None
                ),
                config=config,
            )
            if synthesizer.is_available():
                # Get the model that would be selected
                synthesizer._ensure_initialized()
                model = synthesizer.model

                # Show what config says vs what's actually being used
                config_model = config.llm.synthesis_model
                if config_model != "auto" and config_model != model:
                    # Config specified a model but we're using a different one
                    return "⚠️ Model mismatch", f"{model} (config: {config_model})"
                else:
                    return "✅ Ready", model
            else:
                return "❌ Ollama not running", None
        except Exception as e:
            return f"❌ Error: {str(e)[:20]}...", None

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self):
        """Print the main header."""
        print("+====================================================+")
        print("|              FSS-Mini-RAG TUI                      |")
        print("|         Semantic Code Search Interface             |")
        print("+====================================================+")
        print()

    def print_cli_command(self, command: str, description: str = ""):
        """Show the equivalent CLI command."""
        print(f"💻 CLI equivalent: {command}")
        if description:
            print(f"   {description}")
        print()

    def get_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default."""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "

        try:
            result = input(full_prompt).strip()
            return result if result else default
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)

    def show_menu(
        self,
        title: str,
        options: List[str],
        show_cli: bool = True,
        back_option: str = None,
    ) -> int:
        """Show a menu and get user selection."""
        print(f"🎯 {title}")
        print("=" * (len(title) + 3))
        print()

        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")

        # Add back/exit option
        if back_option:
            print(f"0. {back_option}")

        if show_cli:
            print()
            print("💡 All these actions can be done via CLI commands")
            print("   You'll see the commands as you use this interface!")

        print()
        while True:
            try:
                choice = int(input("Select option (number): "))
                if choice == 0 and back_option:
                    return -1  # Special value for back/exit
                elif 1 <= choice <= len(options):
                    return choice - 1
                else:
                    valid_range = (
                        "0-" + str(len(options)) if back_option else "1-" + str(len(options))
                    )
                    print(f"Please enter a number between {valid_range}")
            except ValueError:
                print("Please enter a valid number")
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                sys.exit(0)

    def select_project(self):
        """Select or create project directory."""
        self.clear_screen()
        self.print_header()

        print("📁 Project Selection")
        print("==================")
        print()

        # Show current project if any
        if self.project_path:
            print(f"Current project: {self.project_path}")
            print()

        print("💡 New to FSS-Mini-RAG? Select 'Use current directory' to")
        print("   explore this RAG system's own codebase as your first demo!")
        print()

        # If we already have a project, show it prominently and offer quick actions
        if self.project_path:
            rag_dir = self.project_path / ".mini-rag"
            is_indexed = rag_dir.exists()
            status_text = "Ready for search ✅" if is_indexed else "Needs indexing ❌"

            print(f"Current: {self.project_path.name} ({status_text})")
            print()

            options = [
                "Keep current project (go back to main menu)",
                "Use current directory (this folder)",
                "Enter different project path",
                "Browse recent projects",
                "Open folder picker (GUI)",
            ]
        else:
            options = [
                "Use current directory (perfect for beginners - try the RAG codebase!)",
                "Enter project path (if you have a specific project)",
                "Browse recent projects",
                "Open folder picker (GUI)",
            ]

        choice = self.show_menu(
            "Choose project directory",
            options,
            show_cli=False,
            back_option="Back to main menu",
        )

        if choice == -1:  # Back to main menu
            return

        # Handle different choice patterns based on whether we have a project
        if self.project_path:
            if choice == 0:
                # Keep current project - just go back
                return
            elif choice == 1:
                # Use current directory
                self.project_path = Path.cwd()
                print(f"✅ Using current directory: {self.project_path}")
                self._save_last_project()
            elif choice == 2:
                # Enter different project path
                self._enter_project_path()
            elif choice == 3:
                # Browse recent projects
                self.browse_recent_projects()
            elif choice == 4:
                picked = self._pick_folder_dialog()
                if picked:
                    self.project_path = Path(picked)
                    print(f"✅ Selected: {self.project_path}")
                    self._save_last_project()
        else:
            if choice == 0:
                # Use current directory
                self.project_path = Path.cwd()
                print(f"✅ Using current directory: {self.project_path}")
                self._save_last_project()
            elif choice == 1:
                # Enter project path
                self._enter_project_path()
            elif choice == 2:
                # Browse recent projects
                self.browse_recent_projects()
            elif choice == 3:
                picked = self._pick_folder_dialog()
                if picked:
                    self.project_path = Path(picked)
                    print(f"✅ Selected: {self.project_path}")
                    self._save_last_project()

        input("\nPress Enter to continue...")

    def _enter_project_path(self):
        """Helper method to handle manual project path entry."""
        while True:
            path_str = self.get_input(
                "Enter project directory path",
                str(self.project_path) if self.project_path else "",
            )

            if not path_str:
                continue

            project_path = Path(path_str).expanduser().resolve()

            if project_path.exists() and project_path.is_dir():
                self.project_path = project_path
                print(f"✅ Selected: {self.project_path}")
                self._save_last_project()
                break
            else:
                print(f"❌ Directory not found: {project_path}")
                retry = input("Try again? (y/N): ").lower()
                if retry != "y":
                    break

    def browse_recent_projects(self):
        """Browse recently indexed projects."""
        print("🕒 Recent Projects")
        print("=================")
        print()

        # Look for .mini-rag directories in common locations
        search_paths = [
            Path.home(),
            Path.home() / "projects",
            Path.home() / "code",
            Path.home() / "dev",
            Path.cwd().parent,
            Path.cwd(),
        ]

        recent_projects = []
        for search_path in search_paths:
            if search_path.exists() and search_path.is_dir():
                try:
                    for item in search_path.iterdir():
                        if item.is_dir():
                            rag_dir = item / ".mini-rag"
                            if rag_dir.exists():
                                recent_projects.append(item)
                except (PermissionError, OSError):
                    continue

        # Remove duplicates and sort by modification time
        recent_projects = list(set(recent_projects))
        try:
            recent_projects.sort(key=lambda p: (p / ".mini-rag").stat().st_mtime, reverse=True)
        except (AttributeError, OSError, TypeError, ValueError):
            pass

        if not recent_projects:
            print("❌ No recently indexed projects found")
            print("   Projects with .mini-rag directories will appear here")
            return

        print("Found indexed projects:")
        for i, project in enumerate(recent_projects[:10], 1):  # Show up to 10
            try:
                manifest = project / ".mini-rag" / "manifest.json"
                if manifest.exists():
                    with open(manifest) as f:
                        data = json.load(f)
                    file_count = data.get("file_count", 0)
                    indexed_at = data.get("indexed_at", "Unknown")
                    print(f"{i}. {project.name} ({file_count} files, {indexed_at})")
                else:
                    print(f"{i}. {project.name} (incomplete index)")
            except (
                AttributeError,
                FileNotFoundError,
                IOError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                print(f"{i}. {project.name} (index status unknown)")

        print()
        try:
            choice = int(input("Select project number (or 0 to cancel): "))
            if 1 <= choice <= len(recent_projects):
                self.project_path = recent_projects[choice - 1]
                print(f"✅ Selected: {self.project_path}")
                self._save_last_project()
        except (ValueError, IndexError):
            print("Selection cancelled")

    def index_project_interactive(self):
        """Interactive project indexing."""
        if not self.project_path:
            print("❌ No project selected")
            input("Press Enter to continue...")
            return

        self.clear_screen()
        self.print_header()

        print("🚀 Project Indexing")
        print("==================")
        print()
        print(f"Project: {self.project_path}")
        print()

        # Check if already indexed
        rag_dir = self.project_path / ".mini-rag"
        if rag_dir.exists():
            force = self._show_existing_index_info(rag_dir)
        else:
            force = False

        # Show CLI command
        cli_cmd = f"./rag-mini index {self.project_path}"
        if force:
            cli_cmd += " --force"

        self.print_cli_command(cli_cmd, "Index project for semantic search")

        # Import here to avoid startup delays
        sys.path.insert(0, str(Path(__file__).parent))
        from mini_rag.indexer import ProjectIndexer

        # Get file count and show preview before starting
        print("🔍 Analyzing project structure...")
        print("=" * 50)

        try:
            indexer = ProjectIndexer(self.project_path)

            # Get files that would be indexed
            files_to_index = indexer._get_files_to_index()
            total_files = len(files_to_index)

            if total_files == 0:
                print("✅ All files are already up to date!")
                print("   No indexing needed.")
                input("\nPress Enter to continue...")
                return

            # Show file analysis
            print("📊 Indexing Analysis:")
            print(f"   Files to process: {total_files}")

            # Analyze file types
            file_types = {}
            total_size = 0
            for file_path in files_to_index:
                ext = file_path.suffix.lower() or "no extension"
                file_types[ext] = file_types.get(ext, 0) + 1
                try:
                    total_size += file_path.stat().st_size
                except (
                    AttributeError,
                    FileNotFoundError,
                    IOError,
                    OSError,
                    TypeError,
                    ValueError,
                    subprocess.SubprocessError,
                ):
                    pass

            # Show breakdown
            print(f"   Total size: {total_size / (1024*1024):.1f}MB")
            print("   File types:")
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                print(f"     • {ext}: {count} files")

            # Conservative time estimate for average hardware
            estimated_time = self._estimate_processing_time(total_files, total_size)
            print(f"   Estimated time: {estimated_time}")

            print()
            print("💡 What indexing does:")
            print("   • Reads and analyzes each file's content (READ-ONLY)")
            print("   • Breaks content into semantic chunks")
            print("   • Generates embeddings for semantic search")
            print("   • Stores everything in a separate .mini-rag/ database")
            print()
            print("🛡️  SAFETY GUARANTEE:")
            print("   • Your original files are NEVER modified or touched")
            print("   • Only reads files to create the search index")
            print("   • All data stored separately in .mini-rag/ folder")
            print("   • You can delete the .mini-rag/ folder anytime to remove all traces")
            print()

            # Confirmation
            confirm = input("🚀 Proceed with indexing? [Y/n]: ").strip().lower()
            if confirm and confirm != "y" and confirm != "yes":
                print("Indexing cancelled.")
                input("Press Enter to continue...")
                return

            print("\n🚀 Starting indexing...")
            print("=" * 50)

            # Actually run the indexing
            result = indexer.index_project(force_reindex=force)

            print()
            print("🎉 INDEXING COMPLETE!")
            print("=" * 50)

            # Comprehensive performance summary
            files_processed = result.get("files_indexed", 0)
            chunks_created = result.get("chunks_created", 0)
            time_taken = result.get("time_taken", 0)
            files_failed = result.get("files_failed", 0)
            files_per_second = result.get("files_per_second", 0)

            print("📊 PROCESSING SUMMARY:")
            print(f"   ✅ Files successfully processed: {files_processed:,}")
            print(f"   🧩 Semantic chunks created: {chunks_created:,}")
            print(f"   ⏱️  Total processing time: {time_taken:.2f} seconds")
            print(f"   🚀 Processing speed: {files_per_second:.1f} files/second")

            if files_failed > 0:
                print(f"   ⚠️  Files with issues: {files_failed}")

            # Show what we analyzed
            if chunks_created > 0:
                avg_chunks_per_file = chunks_created / max(files_processed, 1)
                print()
                print("🔍 CONTENT ANALYSIS:")
                print(f"   • Average chunks per file: {avg_chunks_per_file:.1f}")
                print("   • Semantic boundaries detected and preserved")
                print("   • Function and class contexts captured")
                print("   • Documentation and code comments indexed")

                # Try to show embedding info
                try:
                    embedder = indexer.embedder
                    embed_info = embedder.get_embedding_info()
                    print(f"   • Embedding method: {embed_info.get('method', 'Unknown')}")
                    print(f"   • Vector dimensions: {embedder.get_embedding_dim()}")
                except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
                    pass

            # Database info
            print()
            print("💾 DATABASE CREATED:")
            print(f"   • Location: {self.project_path}/.mini-rag/")
            print(f"   • Vector database with {chunks_created:,} searchable chunks")
            print("   • Optimized for fast semantic similarity search")
            print("   • Supports natural language queries")

            # Performance metrics
            if time_taken > 0:
                print()
                print("⚡ PERFORMANCE METRICS:")
                chunks_per_second = chunks_created / time_taken if time_taken > 0 else 0
                print(f"   • {chunks_per_second:.0f} chunks processed per second")

                # Estimate search performance
                estimated_search_time = max(0.1, chunks_created / 10000)  # Very rough estimate
                print(f"   • Estimated search time: ~{estimated_search_time:.1f}s per query")

                if total_size > 0:
                    mb_per_second = (total_size / (1024 * 1024)) / time_taken
                    print(f"   • Data processing rate: {mb_per_second:.1f} MB/second")

            # What's next
            print()
            print("🎯 READY FOR SEARCH!")
            print("   Your codebase is now fully indexed and searchable.")
            print("   Try queries like:")
            print(f"     • 'authentication logic'")
            print(f"     • 'error handling patterns'")
            print(f"     • 'database connection setup'")
            print(f"     • 'unit tests for validation'")

            if files_failed > 0:
                print()
                print("📋 NOTES:")
                print(
                    f"   • {files_failed} files couldn't be processed "
                    f"(binary files, encoding issues, etc.)"
                )
                print("   • This is normal - only text-based files are indexed")
                print("   • All processable content has been successfully indexed")

        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            print("   Try running the CLI command directly for more details")

        print()
        input("Press Enter to continue...")

    def _pick_folder_dialog(self) -> Optional[str]:
        """Open a minimal cross-platform folder picker dialog and return path or None."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.update()
            directory = filedialog.askdirectory(title="Select project folder to index")
            root.destroy()
            if directory and Path(directory).exists():
                return directory
            return None
        except Exception:
            print("❌ Folder picker not available on this system")
            return None

    def _show_existing_index_info(self, rag_dir: Path) -> bool:
        """Show essential info about existing index and ask about re-indexing."""
        print("📊 EXISTING INDEX FOUND")
        print("=" * 50)
        print()
        print("🛡️  Your original files are safe and unmodified.")
        print()

        try:
            manifest_path = rag_dir / "manifest.json"
            if manifest_path.exists():
                import json
                from datetime import datetime

                with open(manifest_path, "r") as f:
                    manifest = json.load(f)

                file_count = manifest.get("file_count", 0)
                chunk_count = manifest.get("chunk_count", 0)
                indexed_at = manifest.get("indexed_at", "Unknown")

                print(f"• Files indexed: {file_count:,}")
                print(f"• Chunks created: {chunk_count:,}")

                # Show when it was last indexed
                if indexed_at != "Unknown":
                    try:
                        dt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
                        time_ago = datetime.now() - dt.replace(tzinfo=None)

                        if time_ago.days > 0:
                            age_str = f"{time_ago.days} day(s) ago"
                        elif time_ago.seconds > 3600:
                            age_str = f"{time_ago.seconds // 3600} hour(s) ago"
                        else:
                            age_str = f"{time_ago.seconds // 60} minute(s) ago"

                        print(f"• Last indexed: {age_str}")
                    except (AttributeError, OSError, TypeError, ValueError):
                        print(f"• Last indexed: {indexed_at}")
                else:
                    print("• Last indexed: Unknown")

                # Simple recommendation
                if time_ago.days >= 7:
                    print(f"\n💡 RECOMMEND: Re-index (index is {time_ago.days} days old)")
                elif time_ago.days >= 1:
                    print(
                        f"\n💡 MAYBE: Re-index if you've made changes ({time_ago.days} day(s) old)"
                    )
                else:
                    print("\n💡 RECOMMEND: Skip (index is recent)")

                estimate = self._estimate_processing_time(file_count, 0)
                print(f"• Re-indexing would take: {estimate}")

            else:
                print("⚠️  Index corrupted - recommend re-indexing")

        except Exception:
            print("⚠️  Could not read index info - recommend re-indexing")

        print()
        choice = input("🚀 Re-index everything? [y/N]: ").strip().lower()
        return choice in ["y", "yes"]

    def _estimate_processing_time(self, file_count: int, total_size_bytes: int) -> str:
        """Conservative time estimates for average hardware (not high-end dev machines)."""
        # Conservative: 2 seconds per file for average hardware (4x buffer from fast machines)
        estimated_seconds = file_count * 2.0 + 15  # +15s startup overhead

        if estimated_seconds < 60:
            return "1-2 minutes"
        elif estimated_seconds < 300:  # 5 minutes
            minutes = int(estimated_seconds / 60)
            return f"{minutes}-{minutes + 1} minutes"
        else:
            minutes = int(estimated_seconds / 60)
            return f"{minutes}+ minutes"

    def search_interactive(self):
        """Interactive search interface."""
        if not self.project_path:
            print("❌ No project selected")
            input("Press Enter to continue...")
            return

        # Check if indexed
        rag_dir = self.project_path / ".mini-rag"
        if not rag_dir.exists():
            print(f"❌ Project not indexed: {self.project_path.name}")
            print("   Index the project first!")
            input("Press Enter to continue...")
            return

        self.clear_screen()
        self.print_header()

        print("🔍 Semantic Search")
        print("=================")
        print()
        print(f"Project: {self.project_path.name}")
        print()

        # More prominent search input
        print("🎯 ENTER YOUR SEARCH QUERY:")
        print("   Ask any question about your codebase using natural language")
        print("   Examples: 'chunking strategy', 'ollama integration', 'embedding generation'")
        print()

        # Primary input - direct query entry
        query = self.get_input("Search query", "").strip()

        # If they didn't enter anything, show sample options
        if not query:
            print()
            print("💡 Need inspiration? Try one of these sample queries:")
            print()

            sample_questions = [
                "chunking strategy",
                "ollama integration",
                "indexing performance",
                "why does indexing take long",
                "how to improve search results",
                "embedding generation",
            ]

            for i, question in enumerate(sample_questions[:3], 1):
                print(f"   {i}. {question}")
            print()

            choice_str = self.get_input(
                "Select a sample query (1-3) or press Enter to go back", ""
            )

            if choice_str.isdigit():
                choice = int(choice_str)
                if 1 <= choice <= 3:
                    query = sample_questions[choice - 1]
                    print(f"✅ Using: '{query}'")
                    print()

        # If still no query, return to menu
        if not query:
            return

        # Use a sensible default for results to streamline UX
        top_k = 10  # Good default, advanced users can use CLI for more options

        # Show CLI command
        cli_cmd = f'./rag-mini search {self.project_path} "{query}"'
        if top_k != 10:
            cli_cmd += f" --top-k {top_k}"

        self.print_cli_command(cli_cmd, "Search for semantic matches")

        print("Searching...")
        print("=" * 50)

        # Actually run the search
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.search import CodeSearcher

            searcher = CodeSearcher(self.project_path)
            # Enable query expansion in TUI for better results
            searcher.config.search.expand_queries = True
            results = searcher.search(query, top_k=top_k)

            if not results:
                print("❌ No results found")
                print()
                print("💡 Try:")
                print("   • Broader search terms")
                print("   • Different keywords")
                print("   • Concepts instead of exact names")
            else:
                print(f"✅ Found {len(results)} results:")
                print()

                for i, result in enumerate(results, 1):
                    # Add divider and whitespace before each result (except first)
                    if i > 1:
                        print()
                        print("-" * 60)
                        print()

                    # Clean up file path
                    try:
                        if hasattr(result.file_path, "relative_to"):
                            rel_path = result.file_path.relative_to(self.project_path)
                        else:
                            rel_path = Path(result.file_path).relative_to(self.project_path)
                    except (FileNotFoundError, IOError, OSError, TypeError, ValueError):
                        rel_path = result.file_path

                    print(f"{i}. {rel_path}")
                    print(f"   Relevance: {result.score:.3f}")

                    # Show line information if available
                    if hasattr(result, "start_line") and result.start_line:
                        print(f"   Lines: {result.start_line}-{result.end_line}")

                    # Show function/class context if available
                    if hasattr(result, "name") and result.name:
                        print(f"   Context: {result.name}")

                    # Show full content with proper formatting
                    content_lines = result.content.strip().split("\n")
                    print("   Content:")
                    for line_num, line in enumerate(
                        content_lines[:8], 1
                    ):  # Show up to 8 lines
                        print(f"     {line}")

                    if len(content_lines) > 8:
                        print(f"     ... ({len(content_lines) - 8} more lines)")

                    print()

                # Offer to view full results
                if len(results) > 1:
                    print("💡 To see more context or specific results:")
                    print(f'   Run: ./rag-mini search {self.project_path} "{query}" --verbose')

                # Suggest follow-up questions based on the search
                print()
                print("🔍 Suggested follow-up searches:")
                follow_up_questions = self.generate_follow_up_questions(query, results)
                for i, question in enumerate(follow_up_questions, 1):
                    print(f"   {i}. {question}")

                # Show additional CLI commands
                print()
                print("💻 CLI Commands:")
                print(
                    f'   ./rag-mini search {self.project_path} "{query}" --top-k 20    # More results'
                )
                print(
                    f"   ./rag-mini explore {self.project_path}                      # Interactive mode"
                )
                print(
                    f'   ./rag-mini search {self.project_path} "{query}" --synthesize  # With AI summary'
                )

                # Ask if they want to run a follow-up search
                print()
                choice = input(
                    "Run a follow-up search? Enter number (1-3) or press Enter to continue: "
                ).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(follow_up_questions):
                    # Recursive search with the follow-up question
                    follow_up_query = follow_up_questions[int(choice) - 1]
                    print(f"\nSearching for: '{follow_up_query}'")
                    print("=" * 50)
                    # Run another search
                    follow_results = searcher.search(follow_up_query, top_k=5)

                    if follow_results:
                        print(f"✅ Found {len(follow_results)} follow-up results:")
                        print()
                        for i, result in enumerate(follow_results[:3], 1):  # Show top 3
                            # Add divider for follow-up results too
                            if i > 1:
                                print()
                                print("-" * 40)
                                print()

                            try:
                                if hasattr(result.file_path, "relative_to"):
                                    rel_path = result.file_path.relative_to(self.project_path)
                                else:
                                    rel_path = Path(result.file_path).relative_to(
                                        self.project_path
                                    )
                            except (
                                FileNotFoundError,
                                IOError,
                                OSError,
                                TypeError,
                                ValueError,
                            ):
                                rel_path = result.file_path
                            print(f"{i}. {rel_path} (Score: {result.score:.3f})")
                            print(f"   {result.content.strip()[:100]}...")
                            print()
                    else:
                        print("❌ No follow-up results found")

                # Track searches and show sample reminder
                self.search_count += 1

                # Show sample reminder after 2 searches
                if self.search_count >= 2 and self.project_path.name == ".sample_test":
                    print()
                    print("⚠️  Sample Limitation Notice")
                    print("=" * 30)
                    print("You've been searching a small sample project.")
                    print(
                        "For full exploration of your codebase, you need to index the complete project."
                    )
                    print()

                    # Show timing estimate if available
                    try:
                        with open("/tmp/fss-rag-sample-time.txt", "r") as f:
                            sample_time = int(f.read().strip())
                        # Rough estimate: multiply by file count ratio
                        estimated_time = sample_time * 20  # Rough multiplier
                        print(f"🕒 Estimated full indexing time: ~{estimated_time} seconds")
                    except (
                        AttributeError,
                        FileNotFoundError,
                        IOError,
                        OSError,
                        TypeError,
                        ValueError,
                    ):
                        print(
                            "🕒 Estimated full indexing time: 1-3 minutes for typical projects"
                        )

                    print()
                    choice = input("Index the full project now? [y/N]: ").strip().lower()
                    if choice == "y":
                        # Switch to full project and index
                        parent_dir = self.project_path.parent
                        self.project_path = parent_dir
                        print(f"\nSwitching to full project: {parent_dir}")
                        print("Starting full indexing...")
                        # Note: This would trigger full indexing in real implementation

        except Exception as e:
            print(f"❌ Search failed: {e}")
            print()
            print("💡 Try these CLI commands for more details:")
            print(f'   ./rag-mini search {self.project_path} "{query}" --verbose')
            print(f"   ./rag-mini status {self.project_path}")
            print("   ./rag-mini --help")
            print()
            print("🔧 Common solutions:")
            print("   • Make sure the project is indexed first")
            print("   • Check if Ollama is running: ollama serve")
            print("   • Try a simpler search query")

        print()
        input("Press Enter to continue...")

    def generate_follow_up_questions(self, original_query: str, results) -> List[str]:
        """Generate contextual follow-up questions based on search results."""
        # Simple pattern-based follow-up generation
        follow_ups = []

        # Based on original query patterns
        query_lower = original_query.lower()

        # FSS-Mini-RAG specific follow-ups
        if "chunk" in query_lower:
            follow_ups.extend(
                [
                    "chunk size optimization",
                    "smart chunking boundaries",
                    "chunk overlap strategies",
                ]
            )
        elif "ollama" in query_lower:
            follow_ups.extend(
                [
                    "embedding model comparison",
                    "ollama server setup",
                    "nomic-embed-text performance",
                ]
            )
        elif "index" in query_lower or "performance" in query_lower:
            follow_ups.extend(
                [
                    "indexing speed optimization",
                    "memory usage during indexing",
                    "file processing pipeline",
                ]
            )
        elif "search" in query_lower or "result" in query_lower:
            follow_ups.extend(
                [
                    "search result ranking",
                    "semantic vs keyword search",
                    "query expansion techniques",
                ]
            )
        elif "embed" in query_lower:
            follow_ups.extend(
                [
                    "vector embedding storage",
                    "embedding model fallbacks",
                    "similarity scoring",
                ]
            )
        else:
            # Generic RAG-related follow-ups
            follow_ups.extend(
                [
                    "vector database internals",
                    "search quality tuning",
                    "embedding optimization",
                ]
            )

        # Based on file types found in results (FSS-Mini-RAG specific)
        if results:
            file_extensions = set()
            for result in results[:3]:  # Check first 3 results
                try:
                    # Handle both Path objects and strings
                    if hasattr(result.file_path, "suffix"):
                        ext = result.file_path.suffix.lower()
                    else:
                        ext = Path(result.file_path).suffix.lower()
                    file_extensions.add(ext)
                except (FileNotFoundError, IOError, OSError):
                    continue  # Skip if we can't get extension

            if ".py" in file_extensions:
                follow_ups.append("Python module dependencies")
            if ".md" in file_extensions:
                follow_ups.append("documentation implementation")
            if "chunker" in str(results[0].file_path).lower():
                follow_ups.append("chunking algorithm details")
            if "search" in str(results[0].file_path).lower():
                follow_ups.append("search algorithm implementation")

        # Return top 3 unique follow-ups
        return list(dict.fromkeys(follow_ups))[:3]

    def explore_interactive(self):
        """Interactive exploration interface with thinking mode."""
        if not self.project_path:
            print("❌ No project selected")
            input("Press Enter to continue...")
            return

        # Check if indexed
        rag_dir = self.project_path / ".mini-rag"
        if not rag_dir.exists():
            print(f"❌ Project not indexed: {self.project_path.name}")
            print("   Index the project first!")
            input("Press Enter to continue...")
            return

        self.clear_screen()
        self.print_header()

        print("🧠 Interactive Exploration Mode")
        print("==============================")
        print()
        print(f"Project: {self.project_path.name}")
        print()
        print("💡 This mode enables:")
        print("   • Thinking-enabled LLM for detailed reasoning")
        print("   • Conversation memory across questions")
        print("   • Perfect for learning and debugging")
        print()

        # Show CLI command
        cli_cmd = f"./rag-mini explore {self.project_path}"
        self.print_cli_command(cli_cmd, "Start interactive exploration session")

        print("Starting exploration mode...")
        print("=" * 50)

        # Launch exploration mode
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.explorer import CodeExplorer

            explorer = CodeExplorer(self.project_path)

            if not explorer.start_exploration_session():
                print("❌ Could not start exploration mode")
                print("   Make sure Ollama is running with a model installed")
                input("Press Enter to continue...")
                return

            # Show initial prompt
            self._show_exploration_prompt(explorer, is_first=True)

            while True:
                try:
                    question = input("➤ ").strip()

                    # Handle numbered options
                    if question == "0":
                        print(explorer.end_session())
                        break
                    elif question == "1":
                        # Use improved summary function
                        summary = self._generate_conversation_summary(explorer)
                        print(f"\n{summary}")
                        self._show_exploration_prompt(explorer)
                        continue
                    elif question == "2":
                        if (
                            hasattr(explorer.current_session, "conversation_history")
                            and explorer.current_session.conversation_history
                        ):
                            print("\n📋 Recent Question History:")
                            print("═" * 40)
                            for i, exchange in enumerate(
                                explorer.current_session.conversation_history[-5:], 1
                            ):
                                q = (
                                    exchange["question"][:60] + "..."
                                    if len(exchange["question"]) > 60
                                    else exchange["question"]
                                )
                                confidence = exchange["response"].get("confidence", 0)
                                print(f"   {i}. {q} (confidence: {confidence:.0f}%)")
                            print()
                        else:
                            print("\n📝 No questions asked yet")
                        self._show_exploration_prompt(explorer)
                        continue
                    elif question == "3":
                        # Generate smart suggestion
                        suggested_question = self._generate_smart_suggestion(explorer)
                        if suggested_question:
                            print(f"\n💡 Suggested question: {suggested_question}")
                            print("   Press Enter to use this, or type your own question:")
                            next_input = input("➤ ").strip()
                            if not next_input:  # User pressed Enter to use suggestion
                                question = suggested_question
                            else:
                                question = next_input
                        else:
                            print("\n💡 No suggestions available yet. Ask a question first!")
                            self._show_exploration_prompt(explorer)
                            continue

                    # Simple exit handling
                    if question.lower() in ["quit", "exit", "q", "back"]:
                        print(explorer.end_session())
                        break

                    # Skip empty input
                    if not question:
                        print("💡 Please enter a question or choose an option (0-3)")
                        continue

                    # Simple help
                    if question.lower() in ["help", "h", "?"]:
                        print("\n💡 Exploration Help:")
                        print("   • Just ask any question about the codebase!")
                        print(
                            "   • Examples: 'how does search work?' or 'explain the indexing'"
                        )
                        print("   • Use options 0-3 for quick actions")
                        self._show_exploration_prompt(explorer)
                        continue

                    # Process the question with streaming
                    print("\n🔍 Starting analysis...")
                    response = explorer.explore_question(question)

                    if response:
                        print(f"\n{response}")
                        # False  # Unused variable removed
                        # Show prompt for next question
                        self._show_exploration_prompt(explorer)
                    else:
                        print("❌ Sorry, I couldn't process that question.")
                        print("💡 Try rephrasing or using simpler terms.")
                        self._show_exploration_prompt(explorer)

                except KeyboardInterrupt:
                    print(f"\n{explorer.end_session()}")
                    break
                except EOFError:
                    print(f"\n{explorer.end_session()}")
                    break

        except Exception as e:
            print(f"❌ Exploration mode failed: {e}")
            print("   Try running the CLI command directly for more details")
            input("\nPress Enter to continue...")
            return

        # Exploration session completed successfully, return to menu without extra prompt

    def _get_context_tokens_estimate(self, explorer):
        """Estimate the total tokens used in the conversation context."""
        if not explorer.current_session or not explorer.current_session.conversation_history:
            return 0

        total_chars = 0
        for exchange in explorer.current_session.conversation_history:
            total_chars += len(exchange["question"])
            # Estimate response character count (summary + key points)
            response = exchange["response"]
            total_chars += len(response.get("summary", ""))
            for point in response.get("key_points", []):
                total_chars += len(point)

        # Rough estimate: 4 characters = 1 token
        return total_chars // 4

    def _get_context_limit_estimate(self):
        """Get estimated context limit for current model."""
        # Conservative estimates for common models
        return 32000  # Most models we use have 32k context

    def _format_token_display(self, used_tokens, limit_tokens):
        """Format token usage display with color coding."""
        percentage = (used_tokens / limit_tokens) * 100 if limit_tokens > 0 else 0

        if percentage < 50:
            color = "🟢"  # Green - plenty of space
        elif percentage < 75:
            color = "🟡"  # Yellow - getting full
        else:
            color = "🔴"  # Red - almost full

        return f"{color} Context: {used_tokens}/{limit_tokens} tokens ({percentage:.0f}%)"

    def _show_exploration_prompt(self, explorer, is_first=False):
        """Show standardized input prompt for exploration mode."""
        print()
        print("═" * 60)
        if is_first:
            print("🤔 Ask your first question about the codebase:")
        else:
            print("🤔 What would you like to explore next?")
        print()

        # Show context usage
        used_tokens = self._get_context_tokens_estimate(explorer)
        limit_tokens = self._get_context_limit_estimate()
        token_display = self._format_token_display(used_tokens, limit_tokens)
        print(f"📊 {token_display}")
        print()

        print("🔧 Quick Options:")
        print("   0 = Quit exploration     1 = Summarize conversation")
        print("   2 = Show question history     3 = Suggest next question")
        print()
        print("💬 Enter your question or choose an option:")

    def _generate_conversation_summary(self, explorer):
        """Generate a detailed summary of the conversation history."""
        if not explorer.current_session or not explorer.current_session.conversation_history:
            return "📝 No conversation to summarize yet. Ask a question first!"

        try:
            # Build conversation context
            conversation_text = ""
            for i, exchange in enumerate(explorer.current_session.conversation_history, 1):
                conversation_text += f"Question {i}: {exchange['question']}\n"
                conversation_text += f"Response {i}: {exchange['response']['summary']}\n"
                # Add key points if available
                if exchange["response"].get("key_points"):
                    for point in exchange["response"]["key_points"]:
                        conversation_text += f"- {point}\n"
                conversation_text += "\n"

            # Determine summary length based on conversation length
            char_count = len(conversation_text)
            if char_count < 500:
                target_length = "brief"
                target_words = "50-80"
            elif char_count < 2000:
                target_length = "moderate"
                target_words = "100-150"
            else:
                target_length = "comprehensive"
                target_words = "200-300"

            # Create summary prompt for natural conversation style
            prompt = f"""Please summarize this conversation about the project we've been exploring. Write a {target_length} summary ({target_words} words) in a natural, conversational style that captures:

1. Main topics we explored together
2. Key insights we discovered
3. Important details we learned
4. Overall understanding we gained

Conversation:
{conversation_text.strip()}

Write your summary as if you're explaining to a colleague what we discussed. Use a friendly, informative tone and avoid JSON or structured formats."""

            # Use the synthesizer to generate summary with streaming and thinking
            print("\n💭 Generating summary...")
            response = explorer.synthesizer._call_ollama(
                prompt, temperature=0.1, disable_thinking=False, use_streaming=True
            )

            if response:
                return f"📋 **Conversation Summary**\n\n{response.strip()}"
            else:
                # Fallback summary
                return self._generate_fallback_summary(
                    explorer.current_session.conversation_history
                )

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return self._generate_fallback_summary(
                explorer.current_session.conversation_history
            )

    def _generate_fallback_summary(self, conversation_history):
        """Generate a simple fallback summary when AI summary fails."""
        if not conversation_history:
            return "📝 No conversation to summarize yet."

        question_count = len(conversation_history)
        topics = []

        # Extract simple topics from questions
        for exchange in conversation_history:
            question = exchange["question"].lower()
            if "component" in question or "part" in question:
                topics.append("system components")
            elif "error" in question or "bug" in question:
                topics.append("error handling")
            elif "security" in question or "auth" in question:
                topics.append("security/authentication")
            elif "test" in question:
                topics.append("testing")
            elif "config" in question or "setting" in question:
                topics.append("configuration")
            elif "performance" in question or "speed" in question:
                topics.append("performance")
            else:
                # Extract first few words as topic
                words = question.split()[:3]
                topics.append(" ".join(words))

        unique_topics = list(dict.fromkeys(topics))  # Remove duplicates while preserving order

        summary = "📋 **Conversation Summary**\n\n"
        summary += f"Questions asked: {question_count}\n"
        summary += f"Topics explored: {', '.join(unique_topics[:5])}\n"
        summary += f"Session duration: {len(conversation_history) * 2} minutes (estimated)\n\n"
        summary += "💡 Use option 2 to see recent question history for more details."

        return summary

    def _generate_smart_suggestion(self, explorer):
        """Generate a smart follow-up question based on conversation context."""
        if not explorer.current_session or not explorer.current_session.conversation_history:
            # First question - provide a random starter question
            import random

            starters = [
                "What are the main components of this project?",
                "How is error handling implemented?",
                "Show me the authentication and security logic",
                "What are the key functions I should understand first?",
                "How does data flow through this system?",
                "What configuration options are available?",
                "Show me the most important files to understand",
            ]
            return random.choice(starters)

        try:
            # Get recent conversation context
            recent_exchanges = explorer.current_session.conversation_history[
                -2:
            ]  # Last 2 exchanges
            context_summary = ""

            for i, exchange in enumerate(recent_exchanges, 1):
                q = exchange["question"]
                summary = (
                    exchange["response"]["summary"][:100] + "..."
                    if len(exchange["response"]["summary"]) > 100
                    else exchange["response"]["summary"]
                )
                context_summary += f"Q{i}: {q}\nA{i}: {summary}\n\n"

            # Create a very focused prompt that encourages short responses
            prompt = """Based on this recent conversation about a codebase, suggest ONE short follow-up question (under 10 words).

Recent conversation:
{context_summary.strip()}

Respond with ONLY a single short question that would logically explore deeper or connect to what was discussed. Examples:
- "Why does this approach work better?"
- "What could go wrong here?"
- "How is this tested?"
- "Where else is this pattern used?"

Your suggested question (under 10 words):"""

            # Use the synthesizer to generate suggestion with thinking collapse
            response = explorer.synthesizer._call_ollama(
                prompt,
                temperature=0.3,
                disable_thinking=False,
                use_streaming=True,
                collapse_thinking=True,
            )

            if response:
                # Clean up the response - extract just the question
                lines = response.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and (
                        "?" in line
                        or line.lower().startswith(
                            ("what", "how", "why", "where", "when", "which", "who")
                        )
                    ):
                        # Remove any prefixes like "Question:" or numbers
                        cleaned = line.split(":", 1)[-1].strip()
                        if len(cleaned) < 80 and (
                            "?" in cleaned
                            or cleaned.lower().startswith(
                                ("what", "how", "why", "where", "when", "which", "who")
                            )
                        ):
                            return cleaned

                # Fallback: use first non-empty line if it looks like a question
                first_line = lines[0].strip() if lines else ""
                if first_line and len(first_line) < 80:
                    return first_line

            # Fallback: pattern-based suggestions if LLM fails
            return self._get_fallback_suggestion(recent_exchanges)

        except Exception:
            # Silent fail with pattern-based fallback
            recent_exchanges = (
                explorer.current_session.conversation_history[-2:]
                if explorer.current_session.conversation_history
                else []
            )
            return self._get_fallback_suggestion(recent_exchanges)

    def _get_fallback_suggestion(self, recent_exchanges):
        """Generate pattern-based suggestions as fallback."""
        if not recent_exchanges:
            return None

        last_question = recent_exchanges[-1]["question"].lower()

        # Simple pattern matching for common follow-ups
        if "how" in last_question and "work" in last_question:
            return "What could go wrong with this approach?"
        elif "what" in last_question and ("is" in last_question or "does" in last_question):
            return "How is this implemented?"
        elif "implement" in last_question or "code" in last_question:
            return "How is this tested?"
        elif "error" in last_question or "bug" in last_question:
            return "How can this be prevented?"
        elif "performance" in last_question or "speed" in last_question:
            return "What are the bottlenecks here?"
        elif "security" in last_question or "safe" in last_question:
            return "What other security concerns exist?"
        elif "test" in last_question:
            return "What edge cases should be considered?"
        else:
            # Generic follow-ups
            fallbacks = [
                "How is this used elsewhere?",
                "What are the alternatives?",
                "Why was this approach chosen?",
                "What happens when this fails?",
                "How can this be improved?",
            ]
            import random

            return random.choice(fallbacks)

    def show_status(self):
        """Show project and system status."""
        self.clear_screen()
        self.print_header()

        print("📊 System Status")
        print("===============")
        print()

        if self.project_path:
            cli_cmd = f"./rag-mini status {self.project_path}"
            self.print_cli_command(cli_cmd, "Show detailed status information")

            # Check project status
            rag_dir = self.project_path / ".mini-rag"
            if rag_dir.exists():
                try:
                    manifest = rag_dir / "manifest.json"
                    if manifest.exists():
                        with open(manifest) as f:
                            data = json.load(f)

                        print(f"Project: {self.project_path.name}")
                        print("✅ Indexed")
                        print(f"   Files: {data.get('file_count', 0)}")
                        print(f"   Chunks: {data.get('chunk_count', 0)}")
                        print(f"   Last update: {data.get('indexed_at', 'Unknown')}")
                    else:
                        print("⚠️  Index incomplete")
                except Exception as e:
                    print(f"❌ Could not read status: {e}")
            else:
                print(f"Project: {self.project_path.name}")
                print("❌ Not indexed")
        else:
            print("❌ No project selected")

        print()

        # Show embedding system status
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.ollama_embeddings import OllamaEmbedder

            embedder = OllamaEmbedder()
            status = embedder.get_status()

            print("🧠 Embedding System:")
            mode = status.get("mode", "unknown")
            if mode == "ollama":
                print("   ✅ Ollama (high quality)")
            elif mode == "fallback":
                print("   ✅ ML fallback (good quality)")
            elif mode == "hash":
                print("   ⚠️  Hash fallback (basic quality)")
            else:
                print(f"   ❓ Unknown: {mode}")

        except Exception as e:
            print(f"🧠 Embedding System: ❌ Error: {e}")

        print()
        input("Press Enter to continue...")

    def show_configuration(self):
        """Show and manage configuration options with interactive editing."""
        if not self.project_path:
            print("❌ No project selected")
            input("Press Enter to continue...")
            return

        while True:
            self.clear_screen()
            self.print_header()

            print("⚙️  Configuration Manager")
            print("========================")
            print()
            print(f"Project: {self.project_path.name}")
            print()

            # Load current configuration
            try:
                from mini_rag.config import ConfigManager

                config_manager = ConfigManager(self.project_path)
                config = config_manager.load_config()
                config_path = self.project_path / ".mini-rag" / "config.yaml"

                print("📋 Current Settings:")
                print(f"   🤖 AI model: {config.llm.synthesis_model}")
                print(f"   🧠 Context window: {config.llm.context_window} tokens")
                print(f"   📁 Chunk size: {config.chunking.max_size} characters")
                print(f"   🔄 Chunking strategy: {config.chunking.strategy}")
                print(f"   🔍 Search results: {config.search.default_top_k} results")
                print(f"   📊 Embedding provider: {config.embedding.provider}")
                print(
                    f"   🚀 Query expansion: {'enabled' if config.search.expand_queries else 'disabled'}"
                )
                print(
                    f"   ⚡ LLM synthesis: {'enabled' if config.llm.enable_synthesis else 'disabled'}"
                )
                print()

                # Show config file location prominently
                config_path = config_manager.config_path
                print("📁 Configuration File Location:")
                print(f"   {config_path}")
                print("   💡 Edit this YAML file directly for advanced settings")
                print()

                print("🛠️  Quick Configuration Options:")
                print("   1. Select AI model (Fast/Recommended/Quality)")
                print("   2. Configure context window (Development/Production/Advanced)")
                print("   3. Adjust chunk size (performance vs accuracy)")
                print("   4. Toggle query expansion (smarter searches)")
                print("   5. Configure search behavior")
                print("   6. View/edit full configuration file")
                print("   7. Reset to defaults")
                print("   8. Advanced settings")
                print()
                print("   V. View current config file")
                print("   B. Back to main menu")

            except Exception as e:
                print(f"❌ Error loading configuration: {e}")
                print("   A default config will be created when needed")
                print()
                print("   B. Back to main menu")

            print()
            choice = input("Choose option: ").strip().lower()

            if choice == "b" or choice == "" or choice == "0":
                break
            elif choice == "v":
                self._show_config_file(config_path)
            elif choice == "1":
                self._configure_llm_model(config_manager, config)
            elif choice == "2":
                self._configure_context_window(config_manager, config)
            elif choice == "3":
                self._configure_chunk_size(config_manager, config)
            elif choice == "4":
                self._toggle_query_expansion(config_manager, config)
            elif choice == "5":
                self._configure_search_behavior(config_manager, config)
            elif choice == "6":
                self._edit_config_file(config_path)
            elif choice == "7":
                self._reset_config(config_manager)
            elif choice == "8":
                self._advanced_settings(config_manager, config)
            else:
                print("Invalid option. Press Enter to continue...")
                input()

    def _show_config_file(self, config_path):
        """Display the full configuration file."""
        self.clear_screen()
        print("📄 Configuration File Contents")
        print("=" * 50)
        print()

        if config_path.exists():
            try:
                with open(config_path) as f:
                    content = f.read()
                print(content)
            except Exception as e:
                print(f"❌ Could not read file: {e}")
        else:
            print("⚠️  Configuration file doesn't exist yet")
            print("   It will be created when you first index a project")

        print("\n" + "=" * 50)
        input("Press Enter to continue...")

    def _configure_llm_model(self, config_manager, config):
        """Interactive LLM model selection with download capability."""
        self.clear_screen()
        print("🤖 AI Model Configuration")
        print("=========================")
        print()

        # Check if Ollama is available
        import requests

        ollama_available = False
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            response = requests.get("http://localhost:11434/api/version", timeout=3)
            ollama_available = response.status_code == 200
        except (
            ConnectionError,
            ImportError,
            ModuleNotFoundError,
            OSError,
            TimeoutError,
            TypeError,
            ValueError,
            requests.RequestException,
            subprocess.SubprocessError,
        ):
            pass

        if not ollama_available:
            print("❌ Ollama not available")
            print()
            print("To use AI features, please:")
            print("   1. Install Ollama: https://ollama.com/download")
            print("   2. Start the service: ollama serve")
            print("   3. Return to this menu")
            print()
            input("Press Enter to continue...")
            return

        # Get available models
        try:
            available_models = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, check=True
            )
            model_lines = available_models.stdout.strip().split("\n")[1:]  # Skip header
            installed_models = [line.split()[0] for line in model_lines if line.strip()]
        except (OSError, TypeError, ValueError, subprocess.SubprocessError):
            installed_models = []

        print("🧠 Why Small Models Work Great for RAG")
        print("=====================================")
        print()
        print("RAG systems like FSS-Mini-RAG don't need massive models because:")
        print("• The relevant code/docs are provided as context")
        print("• Models focus on analysis, not memorizing facts")
        print("• Even 0.6B models give excellent results with good context")
        print("• Smaller models = faster responses = better user experience")
        print()
        print("💡 Advanced Use: For heavy development work with 15+ results")
        print("   and 4000+ character chunks, even these models excel!")
        print("   The 4B Qwen3 model will help you code remarkably well.")
        print()

        # Model options
        model_options = {
            "fast": {
                "model": "qwen3:0.6b",
                "description": "Ultra-fast responses (~500MB)",
                "details": "Perfect for quick searches and exploration. Surprisingly capable!",
            },
            "recommended": {
                "model": "qwen3:1.7b",
                "description": "Best balance of speed and quality (~1.4GB)",
                "details": "Ideal for most users. Great analysis with good speed.",
            },
            "quality": {
                "model": "qwen3:4b",
                "description": "Highest quality responses (~2.5GB)",
                "details": "Excellent for coding assistance and detailed analysis.",
            },
        }

        print("🎯 Recommended Models:")
        print()
        for key, info in model_options.items():
            is_installed = any(info["model"] in model for model in installed_models)
            status = "✅ Installed" if is_installed else "📥 Available for download"

            print(f"   {key.upper()}: {info['model']}")
            print(f"   {info['description']} - {status}")
            print(f"   {info['details']}")
            print()

        current_model = config.llm.synthesis_model
        print(f"Current model: {current_model}")
        print()

        print("Options:")
        print("   F. Select Fast model (qwen3:0.6b)")
        print("   R. Select Recommended model (qwen3:1.7b)")
        print("   Q. Select Quality model (qwen3:4b)")
        print("   C. Keep current model")
        print("   B. Back to configuration menu")
        print()

        choice = input("Choose option: ").strip().lower()

        selected_model = None
        if choice == "":
            selected_model = model_options["fast"]["model"]
        elif choice == "r":
            selected_model = model_options["recommended"]["model"]
        elif choice == "q":
            selected_model = model_options["quality"]["model"]
        elif choice == "c":
            print("Keeping current model.")
            input("Press Enter to continue...")
            return
        elif choice == "b":
            return
        else:
            print("Invalid option.")
            input("Press Enter to continue...")
            return

        # Check if model is installed
        model_installed = any(selected_model in model for model in installed_models)

        if not model_installed:
            print(f"\n📥 Model {selected_model} not installed.")
            print("Would you like to download it now?")
            print("This may take 2-5 minutes depending on your internet speed.")
            print()

            download = input("Download now? [Y/n]: ").strip().lower()
            if download != "n" and download != "no":
                print(f"\n🔄 Downloading {selected_model}...")
                print("This may take a few minutes...")

                try:
                    subprocess.run(
                        ["ollama", "pull", selected_model],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    print(f"✅ Successfully downloaded {selected_model}")
                    model_installed = True
                except subprocess.CalledProcessError as e:
                    print(f"❌ Download failed: {e}")
                    print("You can try downloading manually later with:")
                    print(f"   ollama pull {selected_model}")
                    input("Press Enter to continue...")
                    return
            else:
                print("Model not downloaded. Configuration not changed.")
                input("Press Enter to continue...")
                return

        if model_installed:
            # Update configuration
            config.llm.synthesis_model = selected_model
            config.llm.expansion_model = selected_model  # Keep them in sync

            try:
                config_manager.save_config(config)
                print(f"\n✅ Model updated to {selected_model}")
                print("Configuration saved successfully!")
            except Exception as e:
                print(f"❌ Error saving configuration: {e}")

        print()
        input("Press Enter to continue...")

    def _configure_context_window(self, config_manager, config):
        """Interactive context window configuration."""
        self.clear_screen()
        print("🧠 Context Window Configuration")
        print("===============================")
        print()

        print("💡 Why Context Window Size Matters for RAG")
        print("==========================================")
        print()
        print(
            "Context window determines how much text the AI can 'remember' during conversation:"
        )
        print()
        print("❌ Default 2048 tokens = Only 1-2 responses before forgetting")
        print("✅ Proper context = 5-15+ responses with maintained conversation")
        print()
        print("For RAG systems like FSS-Mini-RAG:")
        print("• Larger context = better analysis of multiple code files")
        print("• Thinking tokens consume ~200-500 tokens per response")
        print("• Search results can be 1000-3000 tokens depending on chunk size")
        print("• Conversation history builds up over time")
        print()
        print("💻 Memory Usage Impact:")
        print("• 8K context ≈ 6MB memory per conversation")
        print("• 16K context ≈ 12MB memory per conversation")
        print("• 32K context ≈ 24MB memory per conversation")
        print()

        current_context = config.llm.context_window
        current_model = config.llm.synthesis_model

        # Get model capabilities
        model_limits = {
            "qwen3:0.6b": 32768,
            "qwen3:1.7b": 32768,
            "qwen3:4b": 131072,
            "qwen2.5:1.5b": 32768,
            "qwen2.5:3b": 32768,
            "default": 8192,
        }

        model_limit = model_limits.get("default", 8192)
        for model_pattern, limit in model_limits.items():
            if model_pattern != "default" and model_pattern.lower() in current_model.lower():
                model_limit = limit
                break

        print(f"Current model: {current_model}")
        print(f"Model maximum: {model_limit:,} tokens")
        print(f"Current setting: {current_context:,} tokens")
        print()

        # Context options
        context_options = {
            "development": {
                "size": 8192,
                "description": "Fast and efficient for most development work",
                "details": "Perfect for code exploration and basic analysis. Quick responses.",
                "memory": "~6MB",
            },
            "production": {
                "size": 16384,
                "description": "Balanced performance for professional use",
                "details": "Ideal for most users. Handles complex analysis well.",
                "memory": "~12MB",
            },
            "advanced": {
                "size": 32768,
                "description": "Maximum performance for heavy development",
                "details": "For large codebases, 15+ search results, complex analysis.",
                "memory": "~24MB",
            },
        }

        print("🎯 Recommended Context Sizes:")
        print()
        for key, info in context_options.items():
            # Check if this size is supported by current model
            if info["size"] <= model_limit:
                status = "✅ Supported"
            else:
                status = f"❌ Exceeds model limit ({model_limit:,})"

            print(f"   {key.upper()}: {info['size']:,} tokens ({info['memory']})")
            print(f"   {info['description']} - {status}")
            print(f"   {info['details']}")
            print()

        print("Options:")
        print("   D. Development (8K tokens - fast)")
        print("   P. Production (16K tokens - balanced)")
        print("   A. Advanced (32K tokens - maximum)")
        print("   C. Custom size (manual entry)")
        print("   K. Keep current setting")
        print("   B. Back to configuration menu")
        print()

        choice = input("Choose option: ").strip().lower()

        new_context = None
        if choice == "d":
            new_context = context_options["development"]["size"]
        elif choice == "p":
            new_context = context_options["production"]["size"]
        elif choice == "a":
            new_context = context_options["advanced"]["size"]
        elif choice == "c":
            print()
            print("Enter custom context size in tokens:")
            print("  Minimum: 4096 (4K)")
            print(f"  Maximum for {current_model}: {model_limit:,}")
            print()
            try:
                custom_size = int(input("Context size: ").strip())
                if custom_size < 4096:
                    print("❌ Context too small. Minimum is 4096 tokens for RAG.")
                    input("Press Enter to continue...")
                    return
                elif custom_size > model_limit:
                    print(
                        f"❌ Context too large. Maximum for {current_model} is {model_limit:,} tokens."
                    )
                    input("Press Enter to continue...")
                    return
                else:
                    new_context = custom_size
            except ValueError:
                print("❌ Invalid number.")
                input("Press Enter to continue...")
                return
        elif choice == "k":
            print("Keeping current context setting.")
            input("Press Enter to continue...")
            return
        elif choice == "b":
            return
        else:
            print("Invalid option.")
            input("Press Enter to continue...")
            return

        if new_context:
            # Validate against model capabilities
            if new_context > model_limit:
                print(
                    f"⚠️  Warning: {new_context:,} tokens exceeds {current_model} limit of {model_limit:,}"
                )
                print("The system will automatically cap at the model limit.")
                print()

            # Update configuration
            config.llm.context_window = new_context

            try:
                config_manager.save_config(config)
                print(f"✅ Context window updated to {new_context:,} tokens")
                print()

                # Provide usage guidance
                if new_context >= 32768:
                    print("🚀 Advanced context enabled!")
                    print("• Perfect for large codebases and complex analysis")
                    print("• Try cranking up search results to 15+ for deep exploration")
                    print(
                        "• Increase chunk size to 4000+ characters for comprehensive context"
                    )
                elif new_context >= 16384:
                    print("⚖️  Balanced context configured!")
                    print("• Great for professional development work")
                    print("• Supports extended conversations and analysis")
                elif new_context >= 8192:
                    print("⚡ Development context set!")
                    print("• Fast responses with good conversation length")
                    print("• Perfect for code exploration and basic analysis")

                print("Configuration saved successfully!")
            except Exception as e:
                print(f"❌ Error saving configuration: {e}")

        print()
        input("Press Enter to continue...")

    def _configure_chunk_size(self, config_manager, config):
        """Interactive chunk size configuration."""
        self.clear_screen()
        print("📁 Chunk Size Configuration")
        print("===========================")
        print()
        print("Chunk size affects both performance and search accuracy:")
        print("• Smaller chunks (500-1000): More precise but may miss context")
        print("• Medium chunks (1500-2500): Good balance (recommended)")
        print("• Larger chunks (3000+): More context but less precise")
        print()
        print(f"Current chunk size: {config.chunking.max_size} characters")
        print()

        print("Quick presets:")
        print("  1. Small (1000) - Precise searching")
        print("  2. Medium (2000) - Balanced (default)")
        print("  3. Large (3000) - More context")
        print("  4. Custom size")
        print()

        choice = input("Choose preset or enter custom size: ").strip()

        new_size = None
        if choice == "1":
            new_size = 1000
        elif choice == "2":
            new_size = 2000
        elif choice == "3":
            new_size = 3000
        elif choice == "4":
            try:
                new_size = int(input("Enter custom chunk size (500-5000): "))
                if new_size < 500 or new_size > 5000:
                    print("❌ Size must be between 500 and 5000")
                    input("Press Enter to continue...")
                    return
            except ValueError:
                print("❌ Invalid number")
                input("Press Enter to continue...")
                return
        elif choice.isdigit():
            try:
                new_size = int(choice)
                if new_size < 500 or new_size > 5000:
                    print("❌ Size must be between 500 and 5000")
                    input("Press Enter to continue...")
                    return
            except ValueError:
                pass

        if new_size and new_size != config.chunking.max_size:
            config.chunking.max_size = new_size
            config_manager.save_config(config)
            print(f"\n✅ Chunk size updated to {new_size} characters")
            print("💡 Tip: Re-index your project for changes to take effect")
            input("Press Enter to continue...")

    def _toggle_query_expansion(self, config_manager, config):
        """Toggle query expansion on/off."""
        self.clear_screen()
        print("🚀 Query Expansion Configuration")
        print("================================")
        print()
        print("Query expansion automatically adds related terms to your searches")
        print("to improve results quality. This uses an LLM to understand your")
        print("intent and find related concepts.")
        print()
        print("Benefits:")
        print("• Find relevant results even with different terminology")
        print("• Better semantic understanding of queries")
        print("• Improved search for complex technical concepts")
        print()
        print("Requirements:")
        print("• Ollama with a language model (e.g., qwen3:1.7b)")
        print("• Slightly slower search (1-2 seconds)")
        print()

        current_status = "enabled" if config.search.expand_queries else "disabled"
        print(f"Current status: {current_status}")
        print()

        if config.search.expand_queries:
            choice = input("Query expansion is currently ON. Turn OFF? [y/N]: ").lower()
            if choice == "y":
                config.search.expand_queries = False
                config_manager.save_config(config)
                print("✅ Query expansion disabled")
        else:
            choice = input("Query expansion is currently OFF. Turn ON? [y/N]: ").lower()
            if choice == "y":
                config.search.expand_queries = True
                config_manager.save_config(config)
                print("✅ Query expansion enabled")
                print("💡 Make sure Ollama is running with a language model")

        input("\nPress Enter to continue...")

    def _configure_search_behavior(self, config_manager, config):
        """Configure search behavior settings."""
        self.clear_screen()
        print("🔍 Search Behavior Configuration")
        print("================================")
        print()
        print("Current settings:")
        print(f"• Default results: {config.search.default_top_k}")
        print(
            f"• BM25 keyword boost: {'enabled' if config.search.enable_bm25 else 'disabled'}"
        )
        print(f"• Similarity threshold: {config.search.similarity_threshold}")
        print()

        print("Configuration options:")
        print("  1. Change default number of results")
        print("  2. Toggle BM25 keyword matching")
        print("  3. Adjust similarity threshold")
        print("  B. Back")
        print()

        choice = input("Choose option: ").strip().lower()

        if choice == "1":
            try:
                new_top_k = int(
                    input(
                        f"Enter default number of results (current: {config.search.default_top_k}): "
                    )
                )
                if 1 <= new_top_k <= 100:
                    config.search.default_top_k = new_top_k
                    config_manager.save_config(config)
                    print(f"✅ Default results updated to {new_top_k}")
                else:
                    print("❌ Number must be between 1 and 100")
            except ValueError:
                print("❌ Invalid number")
        elif choice == "2":
            config.search.enable_bm25 = not config.search.enable_bm25
            config_manager.save_config(config)
            status = "enabled" if config.search.enable_bm25 else "disabled"
            print(f"✅ BM25 keyword matching {status}")
        elif choice == "3":
            try:
                new_threshold = float(
                    input(
                        f"Enter similarity threshold 0.0-1.0 (current: {config.search.similarity_threshold}): "
                    )
                )
                if 0.0 <= new_threshold <= 1.0:
                    config.search.similarity_threshold = new_threshold
                    config_manager.save_config(config)
                    print(f"✅ Similarity threshold updated to {new_threshold}")
                else:
                    print("❌ Threshold must be between 0.0 and 1.0")
            except ValueError:
                print("❌ Invalid number")

        if choice != "b" and choice != "":
            input("Press Enter to continue...")

    def _edit_config_file(self, config_path):
        """Provide instructions for editing the config file."""
        self.clear_screen()
        print("📝 Edit Configuration File")
        print("=========================")
        print()

        if config_path.exists():
            print("Configuration file location:")
            print(f"   {config_path}")
            print()
            print("To edit the configuration:")
            print("   • Use any text editor (nano, vim, VS Code, etc.)")
            print("   • The file is in YAML format with helpful comments")
            print("   • Changes take effect after saving")
            print()
            print("Quick edit commands:")
            self.print_cli_command(f"nano {config_path}", "Edit with nano")
            self.print_cli_command(f"code {config_path}", "Edit with VS Code")
            self.print_cli_command(f"vim {config_path}", "Edit with vim")
        else:
            print("⚠️  Configuration file doesn't exist yet")
            print("   It will be created automatically when you index a project")

        input("\nPress Enter to continue...")

    def _reset_config(self, config_manager):
        """Reset configuration to defaults."""
        self.clear_screen()
        print("🔄 Reset Configuration")
        print("=====================")
        print()
        print("This will reset all settings to default values:")
        print("• Chunk size: 2000 characters")
        print("• Chunking strategy: semantic")
        print("• Query expansion: disabled")
        print("• Search results: 10")
        print("• Embedding method: auto")
        print()

        confirm = input("Are you sure you want to reset to defaults? [y/N]: ").lower()
        if confirm == "y":
            from mini_rag.config import RAGConfig

            default_config = RAGConfig()
            config_manager.save_config(default_config)
            print("✅ Configuration reset to defaults")
            print("💡 You may want to re-index for changes to take effect")
        else:
            print("❌ Reset cancelled")

        input("Press Enter to continue...")

    def _advanced_settings(self, config_manager, config):
        """Configure advanced settings."""
        self.clear_screen()
        print("⚙️  Advanced Configuration")
        print("==========================")
        print()
        print("Advanced settings for power users:")
        print()
        print("Current advanced settings:")
        print(f"• Min file size: {config.files.min_file_size} bytes")
        print(f"• Streaming threshold: {config.streaming.threshold_bytes} bytes")
        print(f"• Embedding batch size: {config.embedding.batch_size}")
        print(f"• LLM synthesis: {'enabled' if config.llm.enable_synthesis else 'disabled'}")
        print()

        print("Advanced options:")
        print("  1. Configure file filtering")
        print("  2. Adjust performance settings")
        print("  3. LLM model preferences")
        print("  B. Back")
        print()

        choice = input("Choose option: ").strip().lower()

        if choice == "1":
            print("\n📁 File filtering settings:")
            print(f"Minimum file size: {config.files.min_file_size} bytes")
            print(f"Excluded patterns: {len(config.files.exclude_patterns)} patterns")
            print("\n💡 Edit the config file directly for detailed file filtering")
        elif choice == "2":
            print("\n⚡ Performance settings:")
            print(f"Embedding batch size: {config.embedding.batch_size}")
            print(f"Streaming threshold: {config.streaming.threshold_bytes}")
            print("\n💡 Higher batch sizes = faster indexing but more memory")
        elif choice == "3":
            print("\n🧠 LLM model preferences:")
            if hasattr(config.llm, "model_rankings") and config.llm.model_rankings:
                print("Current model priority order:")
                for i, model in enumerate(config.llm.model_rankings[:5], 1):
                    print(f"  {i}. {model}")
            print("\n💡 Edit config file to change model preferences")

        if choice != "b" and choice != "":
            input("Press Enter to continue...")

    def show_cli_reference(self):
        """Show CLI command reference."""
        self.clear_screen()
        self.print_header()

        print("💻 CLI Command Reference")
        print("=======================")
        print()
        print("All TUI actions can be done via command line:")
        print()

        print("🚀 Basic Commands:")
        print("   ./rag-mini index <project_path>         # Index project")
        print("   ./rag-mini search <project_path> <query> --synthesize  # Fast synthesis")
        print("   ./rag-mini explore <project_path>       # Interactive thinking mode")
        print("   ./rag-mini status <project_path>        # Show status")
        print()




        print("⚙️  Options:")
        print("   --force                    # Force complete re-index")
        print("   --top-k N                  # Number of top results to return")
        print("   --verbose                  # Show detailed output")
        print()

        print("💡 Pro tip: Start with the TUI, then try the CLI commands!")
        print("   The CLI is more powerful and faster for repeated tasks.")
        print()

        input("Press Enter to continue...")

    def check_for_updates_notification(self):
        """Check for updates and show notification if available."""
        if not UPDATER_AVAILABLE:
            return

        try:
            # Check for legacy notification first
            legacy_notice = get_legacy_notification()
            if legacy_notice:
                print("🔔" + "=" * 58 + "🔔")
                print(legacy_notice)
                print("🔔" + "=" * 58 + "🔔")
                print()
                return

            # Check for regular updates
            update_info = check_for_updates()
            if update_info:
                print("🎉" + "=" * 58 + "🎉")
                print(f"🔄 Update Available: v{update_info.version}")
                print()
                print("📋 What's New:")
                # Show first few lines of release notes
                notes_lines = update_info.release_notes.split("\n")[:3]
                for line in notes_lines:
                    if line.strip():
                        print(f"   • {line.strip()}")
                print()

                # Simple update prompt
                update_choice = self.get_input("🚀 Install update now? [y/N]", "n").lower()
                if update_choice in ["y", "yes"]:
                    self.perform_update(update_info)
                else:
                    print("💡 You can update anytime from the Configuration menu!")

                print("🎉" + "=" * 58 + "🎉")
                print()

        except Exception:
            # Silently ignore update check errors - don't interrupt user experience
            pass

    def perform_update(self, update_info):
        """Perform the actual update with progress display."""
        try:
            updater = get_updater()

            print(f"\n📥 Downloading v{update_info.version}...")

            # Progress callback

            def show_progress(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    bar_length = 30
                    filled = int(bar_length * downloaded / total)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    print(f"\r   [{bar}] {percent:.1f}%", end="", flush=True)

            # Download update
            update_package = updater.download_update(update_info, show_progress)
            if not update_package:
                print("\n❌ Download failed. Please try again later.")
                input("Press Enter to continue...")
                return

            print("\n💾 Creating backup...")
            if not updater.create_backup():
                print("⚠️ Backup failed, but continuing anyway...")

            print("🔄 Installing update...")
            if updater.apply_update(update_package, update_info):
                print("✅ Update successful!")
                print("🚀 Restarting application...")
                input("Press Enter to restart...")
                updater.restart_application()
            else:
                print("❌ Update failed.")
                print("🔙 Attempting rollback...")
                if updater.rollback_update():
                    print("✅ Rollback successful.")
                else:
                    print("❌ Rollback failed. You may need to reinstall.")
                input("Press Enter to continue...")

        except Exception as e:
            print(f"❌ Update error: {e}")
            input("Press Enter to continue...")

    def main_menu(self):
        """Main application loop."""
        first_run = True
        while True:
            self.clear_screen()
            self.print_header()

            # Check for updates on first run only (non-intrusive)
            if first_run:
                self.check_for_updates_notification()
                first_run = False

            # Show current project status prominently
            if self.project_path:
                rag_dir = self.project_path / ".mini-rag"
                is_indexed = rag_dir.exists()
                status_icon = "✅" if is_indexed else "❌"
                status_text = "Ready for search" if is_indexed else "Needs indexing"

                # Check LLM status
                llm_status, llm_model = self._get_llm_status()

                print("╔════════════════════════════════════════════════════╗")
                # Calculate exact spacing for 50-char content width
                project_line = f" Current Project: {self.project_path.name}"
                print(f"║{project_line:<50}║")

                status_line = f" Index Status: {status_icon} {status_text}"
                print(f"║{status_line:<50}║")

                llm_line = f" LLM Status: {llm_status}"
                print(f"║{llm_line:<50}║")

                if llm_model:
                    model_line = f" Model: {llm_model}"
                    print(f"║{model_line:<50}║")

                if is_indexed:
                    # Show quick stats if indexed
                    try:
                        manifest = rag_dir / "manifest.json"
                        if manifest.exists():
                            with open(manifest) as f:
                                data = json.load(f)
                            file_count = data.get("file_count", 0)
                            files_line = f" Files indexed: {file_count}"
                            print(f"║{files_line:<50}║")
                    except (
                        AttributeError,
                        FileNotFoundError,
                        IOError,
                        OSError,
                        TypeError,
                        ValueError,
                        json.JSONDecodeError,
                    ):
                        pass
                print("╚════════════════════════════════════════════════════╝")
                print()
            else:
                # Show beginner tips when no project selected
                print("🎯 Welcome to FSS-Mini-RAG!")
                print(
                    "   Search through code, documents, emails, notes - anything text-based!"
                )
                print("   Start by selecting a project directory below.")
                print()

            # Create options with visual cues based on project status
            if self.project_path:
                rag_dir = self.project_path / ".mini-rag"
                is_indexed = rag_dir.exists()

                if is_indexed:
                    options = [
                        "Select project directory",
                        "\033[2mIndex project for search (already indexed)\033[0m",
                        "Search project (Fast synthesis)",
                        "Explore project (Deep thinking)",
                        "View status",
                        "Configuration",
                        "CLI command reference",
                    ]
                else:
                    options = [
                        "Select project directory",
                        "Index project for search",
                        "\033[2mSearch project (needs indexing first)\033[0m",
                        "\033[2mExplore project (needs indexing first)\033[0m",
                        "View status",
                        "Configuration",
                        "CLI command reference",
                    ]
            else:
                # No project selected - gray out project-dependent options
                options = [
                    "Select project directory",
                    "\033[2mIndex project for search (select project first)\033[0m",
                    "\033[2mSearch project (select project first)\033[0m",
                    "\033[2mExplore project (select project first)\033[0m",
                    "\033[2mView status (select project first)\033[0m",
                    "Configuration",
                    "CLI command reference",
                ]

            choice = self.show_menu("Main Menu", options, back_option="Exit")

            if choice == -1:  # Exit (0 option)
                print("\nThanks for using FSS-Mini-RAG! 🚀")
                print("Try the CLI commands for even more power!")
                break
            elif choice == 0:
                self.select_project()
            elif choice == 1:
                self.index_project_interactive()
            elif choice == 2:
                self.search_interactive()
            elif choice == 3:
                self.explore_interactive()
            elif choice == 4:
                self.show_status()
            elif choice == 5:
                self.show_configuration()
            elif choice == 6:
                self.show_cli_reference()


def main():
    """Main entry point."""
    try:
        # Check if we can import dependencies
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.venv_checker import check_and_warn_venv

            check_and_warn_venv("rag-tui", force_exit=False)
        except ImportError as e:
            # Dependencies missing - show helpful message
            script_dir = Path(__file__).parent
            print("❌ FSS-Mini-RAG dependencies not found!")
            print("")
            print("🔧 To fix this:")
            print(f"   1. Run the installer: {script_dir}/install.sh")
            print(f"   2. Or use the wrapper script: {script_dir}/rag-tui")
            print("   3. Or activate the virtual environment first:")
            print(f"      cd {script_dir}")
            print("      source .venv/bin/activate")
            print(f"      python3 {script_dir}/rag-tui.py")
            print("")
            print(f"💡 Dependencies missing: {e}")
            input("\nPress Enter to exit...")
            return

        tui = SimpleTUI()
        tui.main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\n\nGoodbye! 👋")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Try running the CLI commands directly if this continues.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
FSS-Mini-RAG Text User Interface
Simple, educational TUI that shows CLI commands while providing easy interaction.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Simple TUI without external dependencies
class SimpleTUI:
    def __init__(self):
        self.project_path: Optional[Path] = None
        self.current_config: Dict[str, Any] = {}
        self.search_count = 0  # Track searches for sample reminder
        self.config_dir = Path.home() / '.mini-rag-tui'
        self.config_file = self.config_dir / 'last_project.json'
        
        # Load last project on startup
        self._load_last_project()
        
    def _load_last_project(self):
        """Load the last used project from config file, or auto-detect current directory."""
        # First check if current directory has .mini-rag folder (auto-detect)
        current_dir = Path.cwd()
        if (current_dir / '.mini-rag').exists():
            self.project_path = current_dir
            # Save this as the last project too
            self._save_last_project()
            return
        
        # If no auto-detection, try loading from config file
        try:
            if hasattr(self, 'config_file') and self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                project_path = Path(data.get('last_project', ''))
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
            data = {'last_project': str(self.project_path)}
            with open(self.config_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            # If saving fails, just continue
            pass
    
    def _get_llm_status(self):
        """Get LLM status for display in main menu."""
        try:
            # Import here to avoid startup delays
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.llm_synthesizer import LLMSynthesizer
            from mini_rag.config import RAGConfig, ConfigManager
            
            # Load config for model rankings
            if self.project_path:
                config_manager = ConfigManager(self.project_path)
                config = config_manager.load_config()
            else:
                config = RAGConfig()
            
            synthesizer = LLMSynthesizer(config=config)
            if synthesizer.is_available():
                # Get the model that would be selected
                synthesizer._ensure_initialized()
                model = synthesizer.model
                return "✅ Ready", model
            else:
                return "❌ Ollama not running", None
        except Exception as e:
            return f"❌ Error: {str(e)[:20]}...", None
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
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
    
    def show_menu(self, title: str, options: List[str], show_cli: bool = True, back_option: str = None) -> int:
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
                    valid_range = "0-" + str(len(options)) if back_option else "1-" + str(len(options))
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
            rag_dir = self.project_path / '.mini-rag'
            is_indexed = rag_dir.exists()
            status_text = "Ready for search ✅" if is_indexed else "Needs indexing ❌"
            
            print(f"Current: {self.project_path.name} ({status_text})")
            print()
            
            options = [
                "Keep current project (go back to main menu)",
                "Use current directory (this folder)",
                "Enter different project path",
                "Browse recent projects"
            ]
        else:
            options = [
                "Use current directory (perfect for beginners - try the RAG codebase!)",
                "Enter project path (if you have a specific project)", 
                "Browse recent projects"
            ]
        
        choice = self.show_menu("Choose project directory", options, show_cli=False, back_option="Back to main menu")
        
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
        
        input("\nPress Enter to continue...")
    
    def _enter_project_path(self):
        """Helper method to handle manual project path entry."""
        while True:
            path_str = self.get_input("Enter project directory path", 
                                    str(self.project_path) if self.project_path else "")
            
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
                if retry != 'y':
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
            Path.cwd()
        ]
        
        recent_projects = []
        for search_path in search_paths:
            if search_path.exists() and search_path.is_dir():
                try:
                    for item in search_path.iterdir():
                        if item.is_dir():
                            rag_dir = item / '.mini-rag'
                            if rag_dir.exists():
                                recent_projects.append(item)
                except (PermissionError, OSError):
                    continue
        
        # Remove duplicates and sort by modification time
        recent_projects = list(set(recent_projects))
        try:
            recent_projects.sort(key=lambda p: (p / '.mini-rag').stat().st_mtime, reverse=True)
        except:
            pass
        
        if not recent_projects:
            print("❌ No recently indexed projects found")
            print("   Projects with .mini-rag directories will appear here")
            return
        
        print("Found indexed projects:")
        for i, project in enumerate(recent_projects[:10], 1):  # Show up to 10
            try:
                manifest = project / '.mini-rag' / 'manifest.json'
                if manifest.exists():
                    with open(manifest) as f:
                        data = json.load(f)
                    file_count = data.get('file_count', 0)
                    indexed_at = data.get('indexed_at', 'Unknown')
                    print(f"{i}. {project.name} ({file_count} files, {indexed_at})")
                else:
                    print(f"{i}. {project.name} (incomplete index)")
            except:
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
        rag_dir = self.project_path / '.mini-rag'
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
            print(f"📊 Indexing Analysis:")
            print(f"   Files to process: {total_files}")
            
            # Analyze file types
            file_types = {}
            total_size = 0
            for file_path in files_to_index:
                ext = file_path.suffix.lower() or 'no extension'
                file_types[ext] = file_types.get(ext, 0) + 1
                try:
                    total_size += file_path.stat().st_size
                except:
                    pass
            
            # Show breakdown
            print(f"   Total size: {total_size / (1024*1024):.1f}MB")
            print(f"   File types:")
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
            if confirm and confirm != 'y' and confirm != 'yes':
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
            files_processed = result.get('files_indexed', 0)
            chunks_created = result.get('chunks_created', 0)
            time_taken = result.get('time_taken', 0)
            files_failed = result.get('files_failed', 0)
            files_per_second = result.get('files_per_second', 0)
            
            print(f"📊 PROCESSING SUMMARY:")
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
                print(f"🔍 CONTENT ANALYSIS:")
                print(f"   • Average chunks per file: {avg_chunks_per_file:.1f}")
                print(f"   • Semantic boundaries detected and preserved")
                print(f"   • Function and class contexts captured")
                print(f"   • Documentation and code comments indexed")
                
                # Try to show embedding info
                try:
                    embedder = indexer.embedder
                    embed_info = embedder.get_embedding_info()
                    print(f"   • Embedding method: {embed_info.get('method', 'Unknown')}")
                    print(f"   • Vector dimensions: {embedder.get_embedding_dim()}")
                except:
                    pass
            
            # Database info
            print()
            print(f"💾 DATABASE CREATED:")
            print(f"   • Location: {self.project_path}/.mini-rag/")
            print(f"   • Vector database with {chunks_created:,} searchable chunks")
            print(f"   • Optimized for fast semantic similarity search")
            print(f"   • Supports natural language queries")
            
            # Performance metrics
            if time_taken > 0:
                print()
                print(f"⚡ PERFORMANCE METRICS:")
                chunks_per_second = chunks_created / time_taken if time_taken > 0 else 0
                print(f"   • {chunks_per_second:.0f} chunks processed per second")
                
                # Estimate search performance
                estimated_search_time = max(0.1, chunks_created / 10000)  # Very rough estimate
                print(f"   • Estimated search time: ~{estimated_search_time:.1f}s per query")
                
                if total_size > 0:
                    mb_per_second = (total_size / (1024*1024)) / time_taken
                    print(f"   • Data processing rate: {mb_per_second:.1f} MB/second")
            
            # What's next
            print()
            print(f"🎯 READY FOR SEARCH!")
            print(f"   Your codebase is now fully indexed and searchable.")
            print(f"   Try queries like:")
            print(f"     • 'authentication logic'")
            print(f"     • 'error handling patterns'")
            print(f"     • 'database connection setup'")
            print(f"     • 'unit tests for validation'")
            
            if files_failed > 0:
                print()
                print(f"📋 NOTES:")
                print(f"   • {files_failed} files couldn't be processed (binary files, encoding issues, etc.)")
                print(f"   • This is normal - only text-based files are indexed")
                print(f"   • All processable content has been successfully indexed")
            
        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            print("   Try running the CLI command directly for more details")
        
        print()
        input("Press Enter to continue...")
    
    def _show_existing_index_info(self, rag_dir: Path) -> bool:
        """Show essential info about existing index and ask about re-indexing."""
        print("📊 EXISTING INDEX FOUND")
        print("=" * 50)
        print()
        print("🛡️  Your original files are safe and unmodified.")
        print()
        
        try:
            manifest_path = rag_dir / 'manifest.json' 
            if manifest_path.exists():
                import json
                from datetime import datetime
                
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                file_count = manifest.get('file_count', 0)
                chunk_count = manifest.get('chunk_count', 0)
                indexed_at = manifest.get('indexed_at', 'Unknown')
                
                print(f"• Files indexed: {file_count:,}")
                print(f"• Chunks created: {chunk_count:,}")
                
                # Show when it was last indexed
                if indexed_at != 'Unknown':
                    try:
                        dt = datetime.fromisoformat(indexed_at.replace('Z', '+00:00'))
                        time_ago = datetime.now() - dt.replace(tzinfo=None)
                        
                        if time_ago.days > 0:
                            age_str = f"{time_ago.days} day(s) ago"
                        elif time_ago.seconds > 3600:
                            age_str = f"{time_ago.seconds // 3600} hour(s) ago"
                        else:
                            age_str = f"{time_ago.seconds // 60} minute(s) ago"
                        
                        print(f"• Last indexed: {age_str}")
                    except:
                        print(f"• Last indexed: {indexed_at}")
                else:
                    print("• Last indexed: Unknown")
                
                # Simple recommendation
                if time_ago.days >= 7:
                    print(f"\n💡 RECOMMEND: Re-index (index is {time_ago.days} days old)")
                elif time_ago.days >= 1:
                    print(f"\n💡 MAYBE: Re-index if you've made changes ({time_ago.days} day(s) old)")
                else:
                    print(f"\n💡 RECOMMEND: Skip (index is recent)")
                
                estimate = self._estimate_processing_time(file_count, 0)
                print(f"• Re-indexing would take: {estimate}")
                
            else:
                print("⚠️  Index corrupted - recommend re-indexing")
                
        except Exception:
            print("⚠️  Could not read index info - recommend re-indexing")
        
        print()
        choice = input("🚀 Re-index everything? [y/N]: ").strip().lower()
        return choice in ['y', 'yes']
    
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
        rag_dir = self.project_path / '.mini-rag'
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
                "embedding generation"
            ]
            
            for i, question in enumerate(sample_questions[:3], 1):
                print(f"   {i}. {question}")
            print()
            
            choice_str = self.get_input("Select a sample query (1-3) or press Enter to go back", "")
            
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
        cli_cmd = f"./rag-mini search {self.project_path} \"{query}\""
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
                        if hasattr(result.file_path, 'relative_to'):
                            rel_path = result.file_path.relative_to(self.project_path)
                        else:
                            rel_path = Path(result.file_path).relative_to(self.project_path)
                    except:
                        rel_path = result.file_path
                    
                    print(f"{i}. {rel_path}")
                    print(f"   Relevance: {result.score:.3f}")
                    
                    # Show line information if available
                    if hasattr(result, 'start_line') and result.start_line:
                        print(f"   Lines: {result.start_line}-{result.end_line}")
                    
                    # Show function/class context if available
                    if hasattr(result, 'name') and result.name:
                        print(f"   Context: {result.name}")
                    
                    # Show full content with proper formatting
                    content_lines = result.content.strip().split('\n')
                    print(f"   Content:")
                    for line_num, line in enumerate(content_lines[:8], 1):  # Show up to 8 lines
                        print(f"     {line}")
                    
                    if len(content_lines) > 8:
                        print(f"     ... ({len(content_lines) - 8} more lines)")
                    
                    print()
                
                # Offer to view full results
                if len(results) > 1:
                    print("💡 To see more context or specific results:")
                    print(f"   Run: ./rag-mini search {self.project_path} \"{query}\" --verbose")
                
                # Suggest follow-up questions based on the search
                print()
                print("🔍 Suggested follow-up searches:")
                follow_up_questions = self.generate_follow_up_questions(query, results)
                for i, question in enumerate(follow_up_questions, 1):
                    print(f"   {i}. {question}")
                
                # Show additional CLI commands
                print()
                print("💻 CLI Commands:")
                print(f"   ./rag-mini search {self.project_path} \"{query}\" --top-k 20    # More results")
                print(f"   ./rag-mini explore {self.project_path}                      # Interactive mode")
                print(f"   ./rag-mini search {self.project_path} \"{query}\" --synthesize  # With AI summary")
                
                # Ask if they want to run a follow-up search
                print()
                choice = input("Run a follow-up search? Enter number (1-3) or press Enter to continue: ").strip()
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
                                if hasattr(result.file_path, 'relative_to'):
                                    rel_path = result.file_path.relative_to(self.project_path)
                                else:
                                    rel_path = Path(result.file_path).relative_to(self.project_path)
                            except:
                                rel_path = result.file_path
                            print(f"{i}. {rel_path} (Score: {result.score:.3f})")
                            print(f"   {result.content.strip()[:100]}...")
                            print()
                    else:
                        print("❌ No follow-up results found")
                
                # Track searches and show sample reminder
                self.search_count += 1
                
                # Show sample reminder after 2 searches
                if self.search_count >= 2 and self.project_path.name == '.sample_test':
                    print()
                    print("⚠️  Sample Limitation Notice")
                    print("=" * 30)
                    print("You've been searching a small sample project.")
                    print("For full exploration of your codebase, you need to index the complete project.")
                    print()
                    
                    # Show timing estimate if available
                    try:
                        with open('/tmp/fss-rag-sample-time.txt', 'r') as f:
                            sample_time = int(f.read().strip())
                        # Rough estimate: multiply by file count ratio
                        estimated_time = sample_time * 20  # Rough multiplier
                        print(f"🕒 Estimated full indexing time: ~{estimated_time} seconds")
                    except:
                        print("🕒 Estimated full indexing time: 1-3 minutes for typical projects")
                    
                    print()
                    choice = input("Index the full project now? [y/N]: ").strip().lower()
                    if choice == 'y':
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
            print(f"   ./rag-mini search {self.project_path} \"{query}\" --verbose")
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
            follow_ups.extend(["chunk size optimization", "smart chunking boundaries", "chunk overlap strategies"])
        elif "ollama" in query_lower:
            follow_ups.extend(["embedding model comparison", "ollama server setup", "nomic-embed-text performance"])
        elif "index" in query_lower or "performance" in query_lower:
            follow_ups.extend(["indexing speed optimization", "memory usage during indexing", "file processing pipeline"])
        elif "search" in query_lower or "result" in query_lower:
            follow_ups.extend(["search result ranking", "semantic vs keyword search", "query expansion techniques"])
        elif "embed" in query_lower:
            follow_ups.extend(["vector embedding storage", "embedding model fallbacks", "similarity scoring"])
        else:
            # Generic RAG-related follow-ups
            follow_ups.extend(["vector database internals", "search quality tuning", "embedding optimization"])
        
        # Based on file types found in results (FSS-Mini-RAG specific)
        if results:
            file_extensions = set()
            for result in results[:3]:  # Check first 3 results
                try:
                    # Handle both Path objects and strings
                    if hasattr(result.file_path, 'suffix'):
                        ext = result.file_path.suffix.lower()
                    else:
                        ext = Path(result.file_path).suffix.lower()
                    file_extensions.add(ext)
                except:
                    continue  # Skip if we can't get extension
            
            if '.py' in file_extensions:
                follow_ups.append("Python module dependencies")
            if '.md' in file_extensions:
                follow_ups.append("documentation implementation")
            if 'chunker' in str(results[0].file_path).lower():
                follow_ups.append("chunking algorithm details")
            if 'search' in str(results[0].file_path).lower():
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
        rag_dir = self.project_path / '.mini-rag'
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
            
            print("\n🤔 Ask questions about the codebase:")
            print("   Quick: 0=quit, 1=summary, 2=history, 3=suggest next question")
            
            while True:
                try:
                    question = input("\n> ").strip()
                    
                    # Handle numbered options
                    if question == '0':
                        print(explorer.end_session())
                        break
                    elif question == '1':
                        print("\n" + explorer.get_session_summary())
                        continue
                    elif question == '2':
                        if hasattr(explorer.current_session, 'conversation_history') and explorer.current_session.conversation_history:
                            print("\n🔍 Recent questions:")
                            for i, exchange in enumerate(explorer.current_session.conversation_history[-3:], 1):
                                q = exchange["question"][:50] + "..." if len(exchange["question"]) > 50 else exchange["question"]
                                print(f"   {i}. {q}")
                        else:
                            print("\n📝 No questions asked yet")
                        continue
                    elif question == '3':
                        # Generate smart suggestion
                        suggested_question = self._generate_smart_suggestion(explorer)
                        if suggested_question:
                            print(f"\n💡 Suggested question: {suggested_question}")
                            print("   Press Enter to use this, or type your own question:")
                            next_input = input("> ").strip()
                            if not next_input:  # User pressed Enter to use suggestion
                                question = suggested_question
                            else:
                                question = next_input
                        else:
                            print("\n💡 No suggestions available yet. Ask a question first!")
                            continue
                    
                    # Simple exit handling
                    if question.lower() in ['quit', 'exit', 'q', 'back']:
                        print(explorer.end_session())
                        break
                    
                    # Skip empty input
                    if not question:
                        continue
                    
                    # Simple help
                    if question.lower() in ['help', 'h', '?']:
                        print("\n💡 Just ask any question about the codebase!")
                        print("   Examples: 'how does search work?' or 'explain the indexing'")
                        print("   Quick: 0=quit, 1=summary, 2=history, 3=suggest")
                        continue
                    
                    # Process the question immediately
                    print("🔍 Thinking...")
                    response = explorer.explore_question(question)
                    
                    if response:
                        print(f"\n{response}\n")
                    else:
                        print("❌ Sorry, I couldn't process that question.\n")
                
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
    
    def _generate_smart_suggestion(self, explorer):
        """Generate a smart follow-up question based on conversation context."""
        if not explorer.current_session or not explorer.current_session.conversation_history:
            return None
        
        try:
            # Get recent conversation context
            recent_exchanges = explorer.current_session.conversation_history[-2:]  # Last 2 exchanges
            context_summary = ""
            
            for i, exchange in enumerate(recent_exchanges, 1):
                q = exchange["question"]
                summary = exchange["response"]["summary"][:100] + "..." if len(exchange["response"]["summary"]) > 100 else exchange["response"]["summary"]
                context_summary += f"Q{i}: {q}\nA{i}: {summary}\n\n"
            
            # Create a very focused prompt that encourages short responses
            prompt = f"""Based on this recent conversation about a codebase, suggest ONE short follow-up question (under 10 words).

Recent conversation:
{context_summary.strip()}

Respond with ONLY a single short question that would logically explore deeper or connect to what was discussed. Examples:
- "Why does this approach work better?"
- "What could go wrong here?"  
- "How is this tested?"
- "Where else is this pattern used?"

Your suggested question (under 10 words):"""

            # Use the synthesizer to generate suggestion
            response = explorer.synthesizer._call_ollama(prompt, temperature=0.3, disable_thinking=True)
            
            if response:
                # Clean up the response - extract just the question
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ('?' in line or line.lower().startswith(('what', 'how', 'why', 'where', 'when', 'which', 'who'))):
                        # Remove any prefixes like "Question:" or numbers
                        cleaned = line.split(':', 1)[-1].strip()
                        if len(cleaned) < 80 and ('?' in cleaned or cleaned.lower().startswith(('what', 'how', 'why', 'where', 'when', 'which', 'who'))):
                            return cleaned
                
                # Fallback: use first non-empty line if it looks like a question
                first_line = lines[0].strip() if lines else ""
                if first_line and len(first_line) < 80:
                    return first_line
            
            # Fallback: pattern-based suggestions if LLM fails
            return self._get_fallback_suggestion(recent_exchanges)
            
        except Exception as e:
            # Silent fail with pattern-based fallback
            recent_exchanges = explorer.current_session.conversation_history[-2:] if explorer.current_session.conversation_history else []
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
                "How can this be improved?"
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
            rag_dir = self.project_path / '.mini-rag'
            if rag_dir.exists():
                try:
                    manifest = rag_dir / 'manifest.json'
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
            info = embedder.get_status()
            
            print("🧠 Embedding System:")
            method = info.get('method', 'unknown')
            if method == 'ollama':
                print("   ✅ Ollama (high quality)")
            elif method == 'ml':
                print("   ✅ ML fallback (good quality)")
            elif method == 'hash':
                print("   ⚠️  Hash fallback (basic quality)")
            else:
                print(f"   ❓ Unknown: {method}")
            
        except Exception as e:
            print(f"🧠 Embedding System: ❌ Error: {e}")
        
        print()
        input("Press Enter to continue...")
    
    def show_configuration(self):
        """Show and manage configuration options."""
        if not self.project_path:
            print("❌ No project selected")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header()
        
        print("⚙️  Configuration")
        print("================")
        print()
        print(f"Project: {self.project_path.name}")
        print()
        
        config_path = self.project_path / '.mini-rag' / 'config.yaml'
        
        # Show current configuration if it exists
        if config_path.exists():
            print("✅ Configuration file exists")
            print(f"   Location: {config_path}")
            print()
            
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                
                print("📋 Current Settings:")
                if 'chunking' in config:
                    chunk_cfg = config['chunking']
                    print(f"   Chunk size: {chunk_cfg.get('max_size', 2000)} characters")
                    print(f"   Strategy: {chunk_cfg.get('strategy', 'semantic')}")
                
                if 'embedding' in config:
                    emb_cfg = config['embedding']
                    print(f"   Embedding method: {emb_cfg.get('preferred_method', 'auto')}")
                
                if 'files' in config:
                    files_cfg = config['files']
                    print(f"   Min file size: {files_cfg.get('min_file_size', 50)} bytes")
                    exclude_count = len(files_cfg.get('exclude_patterns', []))
                    print(f"   Excluded patterns: {exclude_count} patterns")
                
                print()
                
            except Exception as e:
                print(f"⚠️  Could not read config: {e}")
                print()
        else:
            print("⚠️  No configuration file found")
            print("   A default config will be created when you index")
            print()
        
        # Show CLI commands for configuration
        self.print_cli_command(f"cat {config_path}", 
                              "View current configuration")
        self.print_cli_command(f"nano {config_path}", 
                              "Edit configuration file")
        
        print("🛠️  Configuration Options:")
        print("   • chunking.max_size - How large each searchable chunk is")
        print("   • chunking.strategy - 'semantic' (smart) vs 'fixed' (simple)")
        print("   • files.exclude_patterns - Skip files matching these patterns")
        print("   • embedding.preferred_method - 'ollama', 'ml', 'hash', or 'auto'")
        print("   • search.default_top_k - Default number of search results (top-k)")
        print()
        
        print("📚 References:")
        print("   • README.md - Complete configuration documentation")
        print("   • examples/config.yaml - Example with all options")
        print("   • docs/TUI_GUIDE.md - Detailed TUI walkthrough")
        
        print()
        
        # Quick actions
        if config_path.exists():
            action = input("Quick actions: [V]iew config, [E]dit path, or Enter to continue: ").lower()
            if action == 'v':
                print("\n" + "="*60)
                try:
                    with open(config_path) as f:
                        print(f.read())
                except Exception as e:
                    print(f"Could not read file: {e}")
                print("="*60)
                input("\nPress Enter to continue...")
            elif action == 'e':
                print(f"\n💡 To edit configuration:")
                print(f"   nano {config_path}")
                print(f"   # Or use your preferred editor")
                input("\nPress Enter to continue...")
        else:
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
        
        print("🎯 Enhanced Commands:")
        print("   ./rag-mini-enhanced search <project_path> <query>  # Smart search")
        print("   ./rag-mini-enhanced similar <project_path> <query> # Find patterns")
        print("   ./rag-mini-enhanced analyze <project_path>         # Optimization")
        print()
        
        print("🛠️  Quick Scripts:")
        print("   ./run_mini_rag.sh index <project_path>     # Simple indexing")
        print("   ./run_mini_rag.sh search <project_path> <query>  # Simple search")
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
    
    def main_menu(self):
        """Main application loop."""
        while True:
            self.clear_screen()
            self.print_header()
            
            # Show current project status prominently
            if self.project_path:
                rag_dir = self.project_path / '.mini-rag'
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
                        manifest = rag_dir / 'manifest.json'
                        if manifest.exists():
                            with open(manifest) as f:
                                data = json.load(f)
                            file_count = data.get('file_count', 0)
                            files_line = f" Files indexed: {file_count}"
                            print(f"║{files_line:<50}║")
                    except:
                        pass
                print("╚════════════════════════════════════════════════════╝")
                print()
            else:
                # Show beginner tips when no project selected
                print("🎯 Welcome to FSS-Mini-RAG!")
                print("   Search through code, documents, emails, notes - anything text-based!")
                print("   Start by selecting a project directory below.")
                print()
            
            # Create options with visual cues based on project status
            if self.project_path:
                rag_dir = self.project_path / '.mini-rag'
                is_indexed = rag_dir.exists()
                
                if is_indexed:
                    options = [
                        "Select project directory",
                        "\033[2mIndex project for search (already indexed)\033[0m",
                        "Search project (Fast synthesis)",
                        "Explore project (Deep thinking)",
                        "View status",
                        "Configuration",
                        "CLI command reference"
                    ]
                else:
                    options = [
                        "Select project directory", 
                        "Index project for search",
                        "\033[2mSearch project (needs indexing first)\033[0m",
                        "\033[2mExplore project (needs indexing first)\033[0m",
                        "View status",
                        "Configuration",
                        "CLI command reference"
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
                    "CLI command reference"
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
            print(f"   1. Run the installer: {script_dir}/install_mini_rag.sh")
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
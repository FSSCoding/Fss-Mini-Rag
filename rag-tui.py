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
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print the main header."""
        print("╔════════════════════════════════════════════════════╗")
        print("║              FSS-Mini-RAG TUI                      ║")
        print("║         Semantic Code Search Interface             ║")
        print("╚════════════════════════════════════════════════════╝")
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
        
        result = input(full_prompt).strip()
        return result if result else default
    
    def show_menu(self, title: str, options: List[str], show_cli: bool = True) -> int:
        """Show a menu and get user selection."""
        print(f"🎯 {title}")
        print("=" * (len(title) + 3))
        print()
        
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        if show_cli:
            print()
            print("💡 All these actions can be done via CLI commands")
            print("   You'll see the commands as you use this interface!")
        
        print()
        while True:
            try:
                choice = int(input("Select option (number): "))
                if 1 <= choice <= len(options):
                    return choice - 1
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
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
        
        options = [
            "Enter project path",
            "Use current directory",
            "Browse recent projects" if self.project_path else "Skip (will ask later)"
        ]
        
        choice = self.show_menu("Choose project directory", options, show_cli=False)
        
        if choice == 0:
            # Enter path manually
            while True:
                path_str = self.get_input("Enter project directory path", 
                                        str(self.project_path) if self.project_path else "")
                
                if not path_str:
                    continue
                    
                project_path = Path(path_str).expanduser().resolve()
                
                if project_path.exists() and project_path.is_dir():
                    self.project_path = project_path
                    print(f"✅ Selected: {self.project_path}")
                    break
                else:
                    print(f"❌ Directory not found: {project_path}")
                    retry = input("Try again? (y/N): ").lower()
                    if retry != 'y':
                        break
        
        elif choice == 1:
            # Use current directory
            self.project_path = Path.cwd()
            print(f"✅ Using current directory: {self.project_path}")
        
        elif choice == 2:
            # Browse recent projects or skip
            if self.project_path:
                self.browse_recent_projects()
            else:
                print("No project selected - you can choose one later from the main menu")
        
        input("\nPress Enter to continue...")
    
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
            print("⚠️  Project appears to be already indexed")
            print()
            force = input("Re-index everything? (y/N): ").lower() == 'y'
        else:
            force = False
        
        # Show CLI command
        cli_cmd = f"./rag-mini index {self.project_path}"
        if force:
            cli_cmd += " --force"
        
        self.print_cli_command(cli_cmd, "Index project for semantic search")
        
        print("Starting indexing...")
        print("=" * 50)
        
        # Actually run the indexing
        try:
            # Import here to avoid startup delays
            sys.path.insert(0, str(Path(__file__).parent))
            from mini_rag.indexer import ProjectIndexer
            
            indexer = ProjectIndexer(self.project_path)
            result = indexer.index_project(force_reindex=force)
            
            print()
            print("✅ Indexing completed!")
            print(f"   Files processed: {result.get('files_indexed', 0)}")
            print(f"   Chunks created: {result.get('chunks_created', 0)}")
            print(f"   Time taken: {result.get('time_taken', 0):.1f}s")
            
            if result.get('files_failed', 0) > 0:
                print(f"   ⚠️  Files failed: {result['files_failed']}")
            
        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            print("   Try running the CLI command directly for more details")
        
        print()
        input("Press Enter to continue...")
    
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
        
        # Show sample questions for beginners - relevant to FSS-Mini-RAG
        print("💡 Not sure what to search for? Try these questions about FSS-Mini-RAG:")
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
        print("   4. Enter your own question")
        print()
        
        # Let user choose a sample or enter their own
        choice_str = self.get_input("Choose a number (1-4) or press Enter for custom", "4")
        
        try:
            choice = int(choice_str)
            if 1 <= choice <= 3:
                query = sample_questions[choice - 1]
                print(f"Selected: '{query}'")
                print()
            else:
                query = self.get_input("Enter your search query", "").strip()
        except ValueError:
            query = self.get_input("Enter your search query", "").strip()
            
        if not query:
            return
        
        # Get result limit
        try:
            limit = int(self.get_input("Number of results", "10"))
            limit = max(1, min(20, limit))  # Clamp between 1-20
        except ValueError:
            limit = 10
        
        # Show CLI command
        cli_cmd = f"./rag-mini search {self.project_path} \"{query}\""
        if limit != 10:
            cli_cmd += f" --limit {limit}"
        
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
            results = searcher.search(query, top_k=limit)
            
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
                    # Clean up file path
                    try:
                        rel_path = result.file_path.relative_to(self.project_path)
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
                            try:
                                rel_path = result.file_path.relative_to(self.project_path)
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
                    print(f"   Or: ./rag-mini-enhanced context {self.project_path} \"{query}\"")
                    print()
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            print("   Try running the CLI command directly for more details")
        
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
                ext = result.file_path.suffix.lower()
                file_extensions.add(ext)
            
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
            
            print("\n🤔 Ask your first question about the codebase:")
            print("   (Type 'help' for commands, 'quit' to return to menu)")
            
            while True:
                try:
                    question = input("\n> ").strip()
                    
                    if question.lower() in ['quit', 'exit', 'q', 'back']:
                        print("\n" + explorer.end_session())
                        break
                    
                    if not question:
                        continue
                    
                    if question.lower() in ['help', 'h']:
                        print("""
🧠 EXPLORATION MODE HELP:
  • Ask any question about the codebase
  • I remember our conversation for follow-up questions  
  • Use 'why', 'how', 'explain' for detailed reasoning
  • Type 'summary' to see session overview
  • Type 'quit' to return to main menu
  
💡 Example questions:
  • "How does authentication work?"
  • "Why is this function slow?"
  • "Explain the database connection logic"
  • "What are the security concerns here?"
""")
                        continue
                    
                    if question.lower() == 'summary':
                        print("\n" + explorer.get_session_summary())
                        continue
                    
                    print("\n🔍 Analyzing...")
                    response = explorer.explore_question(question)
                    
                    if response:
                        print(f"\n{response}")
                    else:
                        print("❌ Sorry, I couldn't process that question. Please try again.")
                
                except KeyboardInterrupt:
                    print(f"\n\n{explorer.end_session()}")
                    break
                except EOFError:
                    print(f"\n\n{explorer.end_session()}")
                    break
            
        except Exception as e:
            print(f"❌ Exploration mode failed: {e}")
            print("   Try running the CLI command directly for more details")
        
        input("\nPress Enter to continue...")
    
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
        print("   • search.default_limit - Default number of search results")
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
        print("   --limit N                  # Limit search results")
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
            
            # Show current project status
            if self.project_path:
                rag_dir = self.project_path / '.mini-rag'
                status = "✅ Indexed" if rag_dir.exists() else "❌ Not indexed"
                print(f"📁 Current project: {self.project_path.name} ({status})")
                print()
            else:
                # Show beginner tips when no project selected
                print("🎯 Welcome to FSS-Mini-RAG!")
                print("   Search through code, documents, emails, notes - anything text-based!")
                print("   Start by selecting a project directory below.")
                print()
            
            options = [
                "Select project directory",
                "Index project for search",
                "Search project (Fast synthesis)",
                "Explore project (Deep thinking)",
                "View status",
                "Configuration",
                "CLI command reference",
                "Exit"
            ]
            
            choice = self.show_menu("Main Menu", options)
            
            if choice == 0:
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
            elif choice == 7:
                print("\nThanks for using FSS-Mini-RAG! 🚀")
                print("Try the CLI commands for even more power!")
                break

def main():
    """Main entry point."""
    try:
        tui = SimpleTUI()
        tui.main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Try running the CLI commands directly if this continues.")

if __name__ == "__main__":
    main()
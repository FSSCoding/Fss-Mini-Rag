#!/usr/bin/env python3
"""
rag-mini - FSS-Mini-RAG Command Line Interface

A lightweight, portable RAG system for semantic code search.
Usage: rag-mini <command> <project_path> [options]
"""

import sys
import argparse
from pathlib import Path
import json
import logging

# Add the RAG system to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mini_rag.indexer import ProjectIndexer
    from mini_rag.search import CodeSearcher
    from mini_rag.ollama_embeddings import OllamaEmbedder
    from mini_rag.llm_synthesizer import LLMSynthesizer
    from mini_rag.explorer import CodeExplorer
except ImportError as e:
    print("❌ Error: Missing dependencies!")
    print()
    print("It looks like you haven't installed the required packages yet.")
    print("This is a common mistake - here's how to fix it:")
    print()
    print("1. Make sure you're in the FSS-Mini-RAG directory")
    print("2. Run the installer script:")
    print("   ./install_mini_rag.sh")
    print()
    print("Or if you want to install manually:")
    print("   python3 -m venv .venv")
    print("   source .venv/bin/activate")
    print("   pip install -r requirements.txt")
    print()
    print(f"Missing module: {e.name}")
    sys.exit(1)

# Configure logging for user-friendly output
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def index_project(project_path: Path, force: bool = False):
    """Index a project directory."""
    try:
        # Show what's happening
        action = "Re-indexing" if force else "Indexing"
        print(f"🚀 {action} {project_path.name}")
        
        # Quick pre-check
        rag_dir = project_path / '.mini-rag'
        if rag_dir.exists() and not force:
            print("   Checking for changes...")
        
        indexer = ProjectIndexer(project_path)
        result = indexer.index_project(force_reindex=force)
        
        # Show results with context
        files_count = result.get('files_indexed', 0)
        chunks_count = result.get('chunks_created', 0)
        time_taken = result.get('time_taken', 0)
        
        if files_count == 0:
            print("✅ Index up to date - no changes detected")
        else:
            print(f"✅ Indexed {files_count} files in {time_taken:.1f}s")
            print(f"   Created {chunks_count} chunks")
            
            # Show efficiency
            if time_taken > 0:
                speed = files_count / time_taken
                print(f"   Speed: {speed:.1f} files/sec")
        
        # Show warnings if any
        failed_count = result.get('files_failed', 0)
        if failed_count > 0:
            print(f"⚠️  {failed_count} files failed (check logs with --verbose)")
        
        # Quick tip for first-time users
        if not (project_path / '.mini-rag' / 'last_search').exists():
            print(f"\n💡 Try: rag-mini search {project_path} \"your search here\"")
            
    except FileNotFoundError:
        print(f"📁 Directory Not Found: {project_path}")
        print("   Make sure the path exists and you're in the right location")
        print(f"   Current directory: {Path.cwd()}")
        print("   Check path: ls -la /path/to/your/project")
        print()
        sys.exit(1)
    except PermissionError:
        print("🔒 Permission Denied")
        print("   FSS-Mini-RAG needs to read files and create index database")
        print(f"   Check permissions: ls -la {project_path}")
        print("   Try a different location with write access")
        print()
        sys.exit(1)
    except Exception as e:
        # Connection errors are handled in the embedding module
        if "ollama" in str(e).lower() or "connection" in str(e).lower():
            sys.exit(1)  # Error already displayed
            
        print(f"❌ Indexing failed: {e}")
        print()
        print("🔧 Common solutions:")
        print("   • Check if path exists and you have read permissions")
        print("   • Ensure Python dependencies are installed: pip install -r requirements.txt")
        print("   • Try with smaller project first to test setup")
        print("   • Check available disk space for index files")
        print()
        print("📚 For detailed help:")
        print(f"   ./rag-mini index {project_path} --verbose")
        print("   Or see: docs/TROUBLESHOOTING.md")
        sys.exit(1)

def search_project(project_path: Path, query: str, top_k: int = 10, synthesize: bool = False):
    """Search a project directory."""
    try:
        # Check if indexed first
        rag_dir = project_path / '.mini-rag'
        if not rag_dir.exists():
            print(f"❌ Project not indexed: {project_path.name}")
            print(f"   Run: rag-mini index {project_path}")
            sys.exit(1)
        
        print(f"🔍 Searching \"{query}\" in {project_path.name}")
        searcher = CodeSearcher(project_path)
        results = searcher.search(query, top_k=top_k)
        
        if not results:
            print("❌ No results found")
            print()
            print("🔧 Quick fixes to try:")
            print("   • Use broader terms: \"login\" instead of \"authenticate_user_session\"")
            print("   • Try concepts: \"database query\" instead of specific function names")
            print("   • Check spelling and try simpler words")
            print("   • Search for file types: \"python class\" or \"javascript function\"")
            print()
            print("⚙️ Configuration adjustments:")
            print(f"   • Lower threshold: ./rag-mini search \"{project_path}\" \"{query}\" --threshold 0.05")
            print(f"   • More results: ./rag-mini search \"{project_path}\" \"{query}\" --top-k 20")
            print()
            print("📚 Need help? See: docs/TROUBLESHOOTING.md")
            return
            
        print(f"✅ Found {len(results)} results:")
        print()
        
        for i, result in enumerate(results, 1):
            # Clean up file path display
            file_path = Path(result.file_path)
            try:
                rel_path = file_path.relative_to(project_path)
            except ValueError:
                # If relative_to fails, just show the basename
                rel_path = file_path.name
            
            print(f"{i}. {rel_path}")
            print(f"   Score: {result.score:.3f}")
            
            # Show line info if available
            if hasattr(result, 'start_line') and result.start_line:
                print(f"   Lines: {result.start_line}-{result.end_line}")
            
            # Show content preview  
            if hasattr(result, 'name') and result.name:
                print(f"   Context: {result.name}")
            
            # Show full content with proper formatting
            print(f"   Content:")
            content_lines = result.content.strip().split('\n')
            for line in content_lines[:10]:  # Show up to 10 lines
                print(f"     {line}")
            
            if len(content_lines) > 10:
                print(f"     ... ({len(content_lines) - 10} more lines)")
                print(f"     Use --verbose or rag-mini-enhanced for full context")
            
            print()
        
        # LLM Synthesis if requested
        if synthesize:
            print("🧠 Generating LLM synthesis...")
            synthesizer = LLMSynthesizer()
            
            if synthesizer.is_available():
                synthesis = synthesizer.synthesize_search_results(query, results, project_path)
                print()
                print(synthesizer.format_synthesis_output(synthesis, query))
                
                # Add guidance for deeper analysis
                if synthesis.confidence < 0.7 or any(word in query.lower() for word in ['why', 'how', 'explain', 'debug']):
                    print("\n💡 Want deeper analysis with reasoning?")
                    print(f"   Try: rag-mini explore {project_path}")
                    print("   Exploration mode enables thinking and remembers conversation context.")
            else:
                print("❌ LLM synthesis unavailable")
                print("   • Ensure Ollama is running: ollama serve")
                print("   • Install a model: ollama pull qwen3:1.7b")
                print("   • Check connection to http://localhost:11434")
        
        # Save last search for potential enhancements
        try:
            (rag_dir / 'last_search').write_text(query)
        except:
            pass  # Don't fail if we can't save
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
        print()
        
        if "not indexed" in str(e).lower():
            print("🔧 Solution:")
            print(f"   ./rag-mini index {project_path}")
            print()
        else:
            print("🔧 Common solutions:")
            print("   • Check project path exists and is readable")
            print("   • Verify index isn't corrupted: delete .mini-rag/ and re-index")
            print("   • Try with a different project to test setup")
            print("   • Check available memory and disk space")
            print()
            print("📚 Get detailed error info:")
            print(f"   ./rag-mini search {project_path} \"{query}\" --verbose")
            print("   Or see: docs/TROUBLESHOOTING.md")
            print()
        sys.exit(1)

def status_check(project_path: Path):
    """Show status of RAG system."""
    try:
        print(f"📊 Status for {project_path.name}")
        print()
        
        # Check project indexing status first
        rag_dir = project_path / '.mini-rag'
        if not rag_dir.exists():
            print("❌ Project not indexed")
            print(f"   Run: rag-mini index {project_path}")
            print()
        else:
            manifest = rag_dir / 'manifest.json'
            if manifest.exists():
                try:
                    with open(manifest) as f:
                        data = json.load(f)
                    
                    file_count = data.get('file_count', 0)
                    chunk_count = data.get('chunk_count', 0)
                    indexed_at = data.get('indexed_at', 'Never')
                    
                    print("✅ Project indexed")
                    print(f"   Files: {file_count}")
                    print(f"   Chunks: {chunk_count}")
                    print(f"   Last update: {indexed_at}")
                    
                    # Show average chunks per file
                    if file_count > 0:
                        avg_chunks = chunk_count / file_count
                        print(f"   Avg chunks/file: {avg_chunks:.1f}")
                    
                    print()
                except Exception:
                    print("⚠️  Index exists but manifest unreadable")
                    print()
            else:
                print("⚠️  Index directory exists but incomplete")
                print(f"   Try: rag-mini index {project_path} --force")
                print()
        
        # Check embedding system status
        print("🧠 Embedding System:")
        try:
            embedder = OllamaEmbedder()
            emb_info = embedder.get_status()
            method = emb_info.get('method', 'unknown')
            
            if method == 'ollama':
                print("   ✅ Ollama (high quality)")
            elif method == 'ml':
                print("   ✅ ML fallback (good quality)")
            elif method == 'hash':
                print("   ⚠️  Hash fallback (basic quality)")
            else:
                print(f"   ❓ Unknown method: {method}")
                
            # Show additional details if available
            if 'model' in emb_info:
                print(f"   Model: {emb_info['model']}")
                
        except Exception as e:
            print(f"   ❌ Status check failed: {e}")
            
        # Show last search if available
        last_search_file = rag_dir / 'last_search' if rag_dir.exists() else None
        if last_search_file and last_search_file.exists():
            try:
                last_query = last_search_file.read_text().strip()
                print(f"\n🔍 Last search: \"{last_query}\"")
            except:
                pass
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        sys.exit(1)

def explore_interactive(project_path: Path):
    """Interactive exploration mode with thinking and context memory for any documents."""
    try:
        explorer = CodeExplorer(project_path)
        
        if not explorer.start_exploration_session():
            sys.exit(1)
        
        # Show enhanced first-time guidance
        print(f"\n🤔 Ask your first question about {project_path.name}:")
        print()
        print("💡 Enter your search query or question below:")
        print('   Examples: "How does authentication work?" or "Show me error handling"')
        print()
        print("🔧 Quick options:")
        print("   1. Help - Show example questions")
        print("   2. Status - Project information")  
        print("   3. Suggest - Get a random starter question")
        print()
        
        is_first_question = True
        
        while True:
            try:
                # Get user input with clearer prompt
                if is_first_question:
                    question = input("📝 Enter question or option (1-3): ").strip()
                else:
                    question = input("\n> ").strip()
                
                # Handle exit commands
                if question.lower() in ['quit', 'exit', 'q']:
                    print("\n" + explorer.end_session())
                    break
                
                # Handle empty input
                if not question:
                    if is_first_question:
                        print("Please enter a question or try option 3 for a suggestion.")
                    else:
                        print("Please enter a question or 'quit' to exit.")
                    continue
                
                # Handle numbered options and special commands
                if question in ['1'] or question.lower() in ['help', 'h']:
                    print("""
🧠 EXPLORATION MODE HELP:
  • Ask any question about your documents or code
  • I remember our conversation for follow-up questions
  • Use 'why', 'how', 'explain' for detailed reasoning
  • Type 'summary' to see session overview
  • Type 'quit' or 'exit' to end session
  
💡 Example questions:
  • "How does authentication work?"
  • "What are the main components?"
  • "Show me error handling patterns"
  • "Why is this function slow?"
  • "What security measures are in place?"
  • "How does data flow through this system?"
""")
                    continue
                    
                elif question in ['2'] or question.lower() == 'status':
                    print(f"""
📊 PROJECT STATUS: {project_path.name}
  • Location: {project_path}
  • Exploration session active
  • AI model ready for questions
  • Conversation memory enabled
""")
                    continue
                    
                elif question in ['3'] or question.lower() == 'suggest':
                    # Random starter questions for first-time users
                    if is_first_question:
                        import random
                        starters = [
                            "What are the main components of this project?",
                            "How is error handling implemented?", 
                            "Show me the authentication and security logic",
                            "What are the key functions I should understand first?",
                            "How does data flow through this system?",
                            "What configuration options are available?",
                            "Show me the most important files to understand"
                        ]
                        suggested = random.choice(starters)
                        print(f"\n💡 Suggested question: {suggested}")
                        print("   Press Enter to use this, or type your own question:")
                        
                        next_input = input("📝 > ").strip()
                        if not next_input:  # User pressed Enter to use suggestion
                            question = suggested
                        else:
                            question = next_input
                    else:
                        # For subsequent questions, could add AI-powered suggestions here
                        print("\n💡 Based on our conversation, you might want to ask:")
                        print('   "Can you explain that in more detail?"')
                        print('   "What are the security implications?"')
                        print('   "Show me related code examples"')
                        continue
                
                if question.lower() == 'summary':
                    print("\n" + explorer.get_session_summary())
                    continue
                
                # Process the question
                print(f"\n🔍 Searching {project_path.name}...")
                print("🧠 Thinking with AI model...")
                response = explorer.explore_question(question)
                
                # Mark as no longer first question after processing
                is_first_question = False
                
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
                print(f"❌ Error processing question: {e}")
                print("Please try again or type 'quit' to exit.")
        
    except Exception as e:
        print(f"❌ Failed to start exploration mode: {e}")
        print("Make sure the project is indexed first: rag-mini index <project>")
        sys.exit(1)

def main():
    """Main CLI interface."""
    # Check virtual environment
    try:
        from mini_rag.venv_checker import check_and_warn_venv
        check_and_warn_venv("rag-mini.py", force_exit=False)
    except ImportError:
        pass  # If venv checker can't be imported, continue anyway
    
    parser = argparse.ArgumentParser(
        description="FSS-Mini-RAG - Lightweight semantic code search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag-mini index /path/to/project              # Index a project
  rag-mini search /path/to/project "query"     # Search indexed project  
  rag-mini search /path/to/project "query" -s  # Search with LLM synthesis
  rag-mini explore /path/to/project            # Interactive exploration mode
  rag-mini status /path/to/project             # Show status
        """
    )
    
    parser.add_argument('command', choices=['index', 'search', 'explore', 'status'],
                       help='Command to execute')
    parser.add_argument('project_path', type=Path,
                       help='Path to project directory (REQUIRED)')
    parser.add_argument('query', nargs='?',
                       help='Search query (for search command)')
    parser.add_argument('--force', action='store_true',
                       help='Force reindex all files')
    parser.add_argument('--top-k', '--limit', type=int, default=10, dest='top_k',
                       help='Maximum number of search results (top-k)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--synthesize', '-s', action='store_true',
                       help='Generate LLM synthesis of search results (requires Ollama)')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Validate project path
    if not args.project_path.exists():
        print(f"❌ Project path does not exist: {args.project_path}")
        sys.exit(1)
        
    if not args.project_path.is_dir():
        print(f"❌ Project path is not a directory: {args.project_path}")
        sys.exit(1)
    
    # Execute command
    if args.command == 'index':
        index_project(args.project_path, args.force)
    elif args.command == 'search':
        if not args.query:
            print("❌ Search query required")
            sys.exit(1)
        search_project(args.project_path, args.query, args.top_k, args.synthesize)
    elif args.command == 'explore':
        explore_interactive(args.project_path)
    elif args.command == 'status':
        status_check(args.project_path)

if __name__ == '__main__':
    main()
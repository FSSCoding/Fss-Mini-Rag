"""
Fast RAG Server with Enhanced Startup, Feedback, and Monitoring
===============================================================

Drop-in replacement for the original server with:
- Blazing fast startup with pre-loading optimization
- Real-time progress feedback during initialization
- Comprehensive health checks and status monitoring
- Enhanced error handling and recovery
- Better indexing progress reporting
- Mini-RAG-friendly status updates
"""

import json
import socket
import threading
import time
import subprocess
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
import queue

# Rich console for beautiful output
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import print as rprint

# Fix Windows console first
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'
    try:
        from .windows_console_fix import fix_windows_console
        fix_windows_console()
    except:
        pass

from .search import CodeSearcher
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .indexer import ProjectIndexer
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)
console = Console()


class ServerStatus:
    """Real-time server status tracking"""
    
    def __init__(self):
        self.phase = "initializing"
        self.progress = 0.0
        self.message = "Starting server..."
        self.details = {}
        self.start_time = time.time()
        self.ready = False
        self.error = None
        self.health_checks = {}
        
    def update(self, phase: str, progress: float = None, message: str = None, **details):
        """Update server status"""
        self.phase = phase
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        self.details.update(details)
        
    def set_ready(self):
        """Mark server as ready"""
        self.ready = True
        self.phase = "ready"
        self.progress = 100.0
        self.message = "Server ready and accepting connections"
        
    def set_error(self, error: str):
        """Mark server as failed"""
        self.error = error
        self.phase = "failed"
        self.message = f"Server failed: {error}"
        
    def get_status(self) -> Dict[str, Any]:
        """Get complete status as dict"""
        return {
            'phase': self.phase,
            'progress': self.progress,
            'message': self.message,
            'ready': self.ready,
            'error': self.error,
            'uptime': time.time() - self.start_time,
            'health_checks': self.health_checks,
            'details': self.details
        }


class FastRAGServer:
    """Ultra-fast RAG server with enhanced feedback and monitoring"""
    
    def __init__(self, project_path: Path, port: int = 7777, auto_index: bool = True):
        self.project_path = project_path
        self.port = port
        self.auto_index = auto_index
        
        # Server state
        self.searcher = None
        self.embedder = None
        self.indexer = None
        self.running = False
        self.socket = None
        self.query_count = 0
        
        # Status and monitoring
        self.status = ServerStatus()
        self.performance = PerformanceMonitor()
        self.health_check_interval = 30  # seconds
        self.last_health_check = 0
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.status_callbacks = []
        
        # Progress tracking
        self.indexing_progress = None
        
    def add_status_callback(self, callback: Callable[[Dict], None]):
        """Add callback for status updates"""
        self.status_callbacks.append(callback)
        
    def _notify_status(self):
        """Notify all status callbacks"""
        status = self.status.get_status()
        for callback in self.status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.warning(f"Status callback failed: {e}")
    
    def _kill_existing_server(self) -> bool:
        """Kill any existing process using our port with better feedback"""
        try:
            self.status.update("port_check", 5, "Checking for existing servers...")
            self._notify_status()
            
            # Quick port check first
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(1.0)  # Faster timeout
            result = test_sock.connect_ex(('localhost', self.port))
            test_sock.close()
            
            if result != 0:  # Port is free
                return True
                
            console.print(f"[yellow]⚠️  Port {self.port} is occupied, clearing it...[/yellow]")
            self.status.update("port_cleanup", 10, f"Clearing port {self.port}...")
            self._notify_status()
            
            if sys.platform == 'win32':
                # Windows: Enhanced process killing
                cmd = ['netstat', '-ano']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                for line in result.stdout.split('\n'):
                    if f':{self.port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            console.print(f"[dim]Killing process {pid}[/dim]")
                            subprocess.run(['taskkill', '/PID', pid, '/F'], 
                                         capture_output=True, timeout=3)
                            time.sleep(0.5)  # Reduced wait time
                            break
            else:
                # Unix/Linux: Enhanced process killing
                result = subprocess.run(['lsof', '-ti', f':{self.port}'], 
                                      capture_output=True, text=True, timeout=3)
                if result.stdout.strip():
                    pids = result.stdout.strip().split()
                    for pid in pids:
                        console.print(f"[dim]Killing process {pid}[/dim]")
                        subprocess.run(['kill', '-9', pid], capture_output=True)
                    time.sleep(0.5)
            
            # Verify port is free
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(1.0)
            result = test_sock.connect_ex(('localhost', self.port))
            test_sock.close()
            
            if result == 0:
                raise RuntimeError(f"Failed to free port {self.port}")
                
            console.print(f"[green]✅ Port {self.port} cleared[/green]")
            return True
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout while clearing port")
        except Exception as e:
            raise RuntimeError(f"Failed to clear port {self.port}: {e}")
    
    def _check_indexing_needed(self) -> bool:
        """Quick check if indexing is needed"""
        rag_dir = self.project_path / '.mini-rag'
        if not rag_dir.exists():
            return True
            
        # Check if database exists and is not empty
        db_path = rag_dir / 'code_vectors.lance'
        if not db_path.exists():
            return True
            
        # Quick file count check
        try:
            import lancedb
        except ImportError:
            # If LanceDB not available, assume index is empty and needs creation
            return True
        
        try:
            db = lancedb.connect(rag_dir)
            if 'code_vectors' not in db.table_names():
                return True
            table = db.open_table('code_vectors')
            count = table.count_rows()
            return count == 0
        except:
            return True
    
    def _fast_index(self) -> bool:
        """Fast indexing with enhanced progress reporting"""
        try:
            self.status.update("indexing", 20, "Initializing indexer...")
            self._notify_status()
            
            # Create indexer with optimized settings
            self.indexer = ProjectIndexer(
                self.project_path,
                embedder=self.embedder,  # Reuse loaded embedder
                max_workers=min(4, os.cpu_count() or 2)
            )
            
            console.print("\n[bold cyan]🚀 Fast Indexing Starting...[/bold cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=console,
                refresh_per_second=10,  # More responsive updates
            ) as progress:
                
                # Override indexer's progress reporting
                original_index_project = self.indexer.index_project
                
                def enhanced_index_project(*args, **kwargs):
                    # Get files to index first
                    files_to_index = self.indexer._get_files_to_index()
                    total_files = len(files_to_index)
                    
                    if total_files == 0:
                        self.status.update("indexing", 80, "Index up to date")
                        return {'files_indexed': 0, 'chunks_created': 0, 'time_taken': 0}
                    
                    task = progress.add_task(
                        f"[cyan]Indexing {total_files} files...",
                        total=total_files
                    )
                    
                    # Track progress by hooking into the processor
                    processed_count = 0
                    
                    def track_progress():
                        nonlocal processed_count
                        while processed_count < total_files and self.running:
                            time.sleep(0.1)  # Fast polling
                            current_progress = (processed_count / total_files) * 60 + 20
                            self.status.update("indexing", current_progress, 
                                             f"Indexed {processed_count}/{total_files} files")
                            progress.update(task, completed=processed_count)
                            self._notify_status()
                    
                    # Start progress tracking
                    progress_thread = threading.Thread(target=track_progress)
                    progress_thread.daemon = True
                    progress_thread.start()
                    
                    # Hook into the processing
                    original_process_file = self.indexer._process_file
                    
                    def tracked_process_file(*args, **kwargs):
                        nonlocal processed_count
                        result = original_process_file(*args, **kwargs)
                        processed_count += 1
                        return result
                    
                    self.indexer._process_file = tracked_process_file
                    
                    # Run the actual indexing
                    stats = original_index_project(*args, **kwargs)
                    
                    progress.update(task, completed=total_files)
                    return stats
                
                self.indexer.index_project = enhanced_index_project
                
                # Run indexing
                stats = self.indexer.index_project(force_reindex=False)
                
                self.status.update("indexing", 80, 
                                 f"Indexed {stats.get('files_indexed', 0)} files, "
                                 f"created {stats.get('chunks_created', 0)} chunks")
                self._notify_status()
                
                console.print(f"\n[green]✅ Indexing complete: {stats.get('files_indexed', 0)} files, "
                            f"{stats.get('chunks_created', 0)} chunks in {stats.get('time_taken', 0):.1f}s[/green]")
                
                return True
                
        except Exception as e:
            self.status.set_error(f"Indexing failed: {e}")
            self._notify_status()
            console.print(f"[red]❌ Indexing failed: {e}[/red]")
            return False
    
    def _initialize_components(self) -> bool:
        """Fast parallel component initialization"""
        try:
            console.print("\n[bold blue]🔧 Initializing RAG Server...[/bold blue]")
            
            # Check if indexing is needed first
            needs_indexing = self._check_indexing_needed()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                
                # Task 1: Load embedder (this takes the most time)
                embedder_task = progress.add_task("[cyan]Loading embedding model...", total=100)
                
                def load_embedder():
                    self.status.update("embedder", 25, "Loading embedding model...")
                    self._notify_status()
                    self.embedder = CodeEmbedder()
                    self.embedder.warmup()  # Pre-warm the model
                    progress.update(embedder_task, completed=100)
                    self.status.update("embedder", 50, "Embedding model loaded")
                    self._notify_status()
                
                # Start embedder loading in background
                embedder_future = self.executor.submit(load_embedder)
                
                # Wait for embedder to finish (this is the bottleneck)
                embedder_future.result(timeout=120)  # 2 minute timeout
                
                # Task 2: Handle indexing if needed
                if needs_indexing and self.auto_index:
                    if not self._fast_index():
                        return False
                
                # Task 3: Initialize searcher (fast with pre-loaded embedder)
                searcher_task = progress.add_task("[cyan]Connecting to database...", total=100)
                self.status.update("searcher", 85, "Connecting to database...")
                self._notify_status()
                
                self.searcher = CodeSearcher(self.project_path, embedder=self.embedder)
                progress.update(searcher_task, completed=100)
                
                self.status.update("searcher", 95, "Database connected")
                self._notify_status()
            
            # Final health check
            self._run_health_checks()
            
            console.print("[green]✅ All components initialized successfully[/green]")
            return True
            
        except Exception as e:
            error_msg = f"Component initialization failed: {e}"
            self.status.set_error(error_msg)
            self._notify_status()
            console.print(f"[red]❌ {error_msg}[/red]")
            return False
    
    def _run_health_checks(self):
        """Comprehensive health checks"""
        checks = {}
        
        try:
            # Check 1: Embedder functionality
            if self.embedder:
                test_embedding = self.embedder.embed_code("def test(): pass")
                checks['embedder'] = {
                    'status': 'healthy',
                    'embedding_dim': len(test_embedding),
                    'model': getattr(self.embedder, 'model_name', 'unknown')
                }
            else:
                checks['embedder'] = {'status': 'missing'}
            
            # Check 2: Database connectivity
            if self.searcher:
                stats = self.searcher.get_statistics()
                checks['database'] = {
                    'status': 'healthy',
                    'chunks': stats.get('total_chunks', 0),
                    'languages': len(stats.get('languages', {}))
                }
            else:
                checks['database'] = {'status': 'missing'}
            
            # Check 3: Search functionality
            if self.searcher:
                test_results = self.searcher.search("test query", top_k=1)
                checks['search'] = {
                    'status': 'healthy',
                    'test_results': len(test_results)
                }
            else:
                checks['search'] = {'status': 'unavailable'}
            
            # Check 4: Port availability
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.bind(('localhost', self.port))
                test_sock.close()
                checks['port'] = {'status': 'available'}
            except:
                checks['port'] = {'status': 'occupied'}
                
        except Exception as e:
            checks['health_check_error'] = str(e)
        
        self.status.health_checks = checks
        self.last_health_check = time.time()
        
        # Display health summary
        table = Table(title="Health Check Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")
        
        for component, info in checks.items():
            status = info.get('status', 'unknown')
            details = ', '.join([f"{k}={v}" for k, v in info.items() if k != 'status'])
            
            color = "green" if status in ['healthy', 'available'] else "yellow"
            table.add_row(component, f"[{color}]{status}[/{color}]", details)
        
        console.print(table)
    
    def start(self):
        """Start the server with enhanced feedback"""
        try:
            start_time = time.time()
            
            # Step 1: Clear existing servers
            if not self._kill_existing_server():
                return False
            
            # Step 2: Initialize all components
            if not self._initialize_components():
                return False
            
            # Step 3: Start network server
            self.status.update("server", 98, "Starting network server...")
            self._notify_status()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('localhost', self.port))
            self.socket.listen(10)  # Increased backlog
            
            self.running = True
            
            # Server is ready!
            total_time = time.time() - start_time
            self.status.set_ready()
            self._notify_status()
            
            # Display ready status
            panel = Panel(
                f"[bold green]🎉 RAG Server Ready![/bold green]\n\n"
                f"🌐 Address: localhost:{self.port}\n"
                f"⚡ Startup Time: {total_time:.2f}s\n"
                f"📁 Project: {self.project_path.name}\n"
                f"🧠 Model: {getattr(self.embedder, 'model_name', 'default')}\n"
                f"📊 Chunks Indexed: {self.status.health_checks.get('database', {}).get('chunks', 0)}\n\n"
                f"[dim]Ready to serve the development environment queries...[/dim]",
                title="🚀 Server Status",
                border_style="green"
            )
            console.print(panel)
            
            # Start serving
            self._serve()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Server interrupted by user[/yellow]")
            self.stop()
        except Exception as e:
            error_msg = f"Server startup failed: {e}"
            self.status.set_error(error_msg)
            self._notify_status()
            console.print(f"[red]❌ {error_msg}[/red]")
            raise
    
    def _serve(self):
        """Main server loop with enhanced monitoring"""
        console.print("[dim]Waiting for connections... Press Ctrl+C to stop[/dim]\n")
        
        while self.running:
            try:
                client, addr = self.socket.accept()
                
                # Handle in thread pool for better performance
                self.executor.submit(self._handle_client, client)
                
                # Periodic health checks
                if time.time() - self.last_health_check > self.health_check_interval:
                    self.executor.submit(self._run_health_checks)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Server error: {e}")
                    console.print(f"[red]Server error: {e}[/red]")
    
    def _handle_client(self, client: socket.socket):
        """Enhanced client handling with better error reporting"""
        try:
            # Receive with timeout
            client.settimeout(30.0)  # 30 second timeout
            data = self._receive_json(client)
            request = json.loads(data)
            
            # Handle different request types
            if request.get('command') == 'shutdown':
                console.print("\n[yellow]🛑 Shutdown requested[/yellow]")
                response = {'success': True, 'message': 'Server shutting down'}
                self._send_json(client, response)
                self.stop()
                return
            
            if request.get('command') == 'status':
                response = {
                    'success': True,
                    'status': self.status.get_status()
                }
                self._send_json(client, response)
                return
            
            # Handle search requests
            query = request.get('query', '')
            top_k = request.get('top_k', 10)
            
            if not query:
                raise ValueError("Empty query")
            
            self.query_count += 1
            
            # Enhanced query logging
            console.print(f"[blue]🔍 Query #{self.query_count}:[/blue] [dim]{query[:50]}{'...' if len(query) > 50 else ''}[/dim]")
            
            # Perform search with timing
            start = time.time()
            results = self.searcher.search(query, top_k=top_k)
            search_time = time.time() - start
            
            # Enhanced response
            response = {
                'success': True,
                'query': query,
                'count': len(results),
                'search_time_ms': int(search_time * 1000),
                'results': [r.to_dict() for r in results],
                'server_uptime': int(time.time() - self.status.start_time),
                'total_queries': self.query_count,
                'server_status': 'ready'
            }
            
            self._send_json(client, response)
            
            # Enhanced result logging
            console.print(f"[green]✅ {len(results)} results in {search_time*1000:.0f}ms[/green]")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Client handler error: {error_msg}")
            
            error_response = {
                'success': False,
                'error': error_msg,
                'error_type': type(e).__name__,
                'server_status': self.status.phase
            }
            
            try:
                self._send_json(client, error_response)
            except:
                pass
            
            console.print(f"[red]❌ Query failed: {error_msg}[/red]")
        finally:
            try:
                client.close()
            except:
                pass
    
    def _receive_json(self, sock: socket.socket) -> str:
        """Receive JSON with length prefix and timeout handling"""
        try:
            # Receive length (4 bytes)
            length_data = b''
            while len(length_data) < 4:
                chunk = sock.recv(4 - len(length_data))
                if not chunk:
                    raise ConnectionError("Connection closed while receiving length")
                length_data += chunk
            
            length = int.from_bytes(length_data, 'big')
            if length > 10_000_000:  # 10MB limit
                raise ValueError(f"Message too large: {length} bytes")
            
            # Receive data
            data = b''
            while len(data) < length:
                chunk = sock.recv(min(65536, length - len(data)))
                if not chunk:
                    raise ConnectionError("Connection closed while receiving data")
                data += chunk
            
            return data.decode('utf-8')
        except socket.timeout:
            raise ConnectionError("Timeout while receiving data")
    
    def _send_json(self, sock: socket.socket, data: dict):
        """Send JSON with length prefix"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        
        # Send length prefix
        length = len(json_bytes)
        sock.send(length.to_bytes(4, 'big'))
        
        # Send data
        sock.sendall(json_bytes)
    
    def stop(self):
        """Graceful server shutdown"""
        console.print("\n[yellow]🛑 Shutting down server...[/yellow]")
        
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=5.0)
        
        console.print("[green]✅ Server stopped gracefully[/green]")


# Enhanced client with status monitoring
class FastRAGClient:
    """Enhanced client with better error handling and status monitoring"""
    
    def __init__(self, port: int = 7777):
        self.port = port
        self.timeout = 30.0
    
    def search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Enhanced search with better error handling"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(('localhost', self.port))
            
            request = {'query': query, 'top_k': top_k}
            self._send_json(sock, request)
            
            data = self._receive_json(sock)
            response = json.loads(data)
            
            sock.close()
            return response
            
        except ConnectionRefusedError:
            return {
                'success': False,
                'error': 'RAG server not running. Start with: python -m mini_rag server',
                'error_type': 'connection_refused'
            }
        except socket.timeout:
            return {
                'success': False,
                'error': f'Request timed out after {self.timeout}s',
                'error_type': 'timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed server status"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(('localhost', self.port))
            
            request = {'command': 'status'}
            self._send_json(sock, request)
            
            data = self._receive_json(sock)
            response = json.loads(data)
            
            sock.close()
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'server_running': False
            }
    
    def is_running(self) -> bool:
        """Enhanced server detection"""
        try:
            status = self.get_status()
            return status.get('success', False)
        except:
            return False
    
    def shutdown(self) -> Dict[str, Any]:
        """Gracefully shutdown server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect(('localhost', self.port))
            
            request = {'command': 'shutdown'}
            self._send_json(sock, request)
            
            data = self._receive_json(sock)
            response = json.loads(data)
            
            sock.close()
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_json(self, sock: socket.socket, data: dict):
        """Send JSON with length prefix"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        
        length = len(json_bytes)
        sock.send(length.to_bytes(4, 'big'))
        sock.sendall(json_bytes)
    
    def _receive_json(self, sock: socket.socket) -> str:
        """Receive JSON with length prefix"""
        # Receive length
        length_data = b''
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                raise ConnectionError("Connection closed")
            length_data += chunk
        
        length = int.from_bytes(length_data, 'big')
        
        # Receive data
        data = b''
        while len(data) < length:
            chunk = sock.recv(min(65536, length - len(data)))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        
        return data.decode('utf-8')


def start_fast_server(project_path: Path, port: int = 7777, auto_index: bool = True):
    """Start the fast RAG server"""
    server = FastRAGServer(project_path, port, auto_index)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


# Backwards compatibility
RAGServer = FastRAGServer
RAGClient = FastRAGClient
start_server = start_fast_server
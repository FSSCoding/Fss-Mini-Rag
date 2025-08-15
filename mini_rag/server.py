"""
Persistent RAG server that keeps models loaded in memory.
No more loading/unloading madness!
"""

import json
import socket
import threading
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import sys
import os

# Fix Windows console
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

from .search import CodeSearcher
from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class RAGServer:
    """Persistent server that keeps embeddings and DB loaded."""
    
    def __init__(self, project_path: Path, port: int = 7777):
        self.project_path = project_path
        self.port = port
        self.searcher = None
        self.embedder = None
        self.running = False
        self.socket = None
        self.start_time = None
        self.query_count = 0
        
    def _kill_existing_server(self):
        """Kill any existing process using our port."""
        try:
            # Check if port is in use
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = test_sock.connect_ex(('localhost', self.port))
            test_sock.close()
            
            if result == 0:  # Port is in use
                print(f"️  Port {self.port} is already in use, attempting to free it...")
                
                if sys.platform == 'win32':
                    # Windows: Find and kill process using netstat
                    import subprocess
                    try:
                        # Get process ID using the port
                        result = subprocess.run(
                            ['netstat', '-ano'], 
                            capture_output=True, 
                            text=True
                        )
                        
                        for line in result.stdout.split('\n'):
                            if f':{self.port}' in line and 'LISTENING' in line:
                                parts = line.split()
                                pid = parts[-1]
                                print(f"   Found process {pid} using port {self.port}")
                                
                                # Kill the process
                                subprocess.run(['taskkill', '//PID', pid, '//F'], check=False)
                                print(f"    Killed process {pid}")
                                time.sleep(1)  # Give it a moment to release the port
                                break
                    except Exception as e:
                        print(f"   ️  Could not auto-kill process: {e}")
                else:
                    # Unix/Linux: Use lsof and kill
                    import subprocess
                    try:
                        result = subprocess.run(
                            ['lsof', '-ti', f':{self.port}'], 
                            capture_output=True, 
                            text=True
                        )
                        if result.stdout.strip():
                            pid = result.stdout.strip()
                            subprocess.run(['kill', '-9', pid], check=False)
                            print(f"    Killed process {pid}")
                            time.sleep(1)
                    except Exception as e:
                        print(f"   ️  Could not auto-kill process: {e}")
        except Exception as e:
            # Non-critical error, just log it
            logger.debug(f"Error checking port: {e}")
        
    def start(self):
        """Start the RAG server."""
        # Kill any existing process on our port first
        self._kill_existing_server()
        
        print(f" Starting RAG server on port {self.port}...")
        
        # Load everything once
        perf = PerformanceMonitor()
        
        with perf.measure("Load Embedder"):
            self.embedder = CodeEmbedder()
            
        with perf.measure("Connect Database"):
            self.searcher = CodeSearcher(self.project_path, embedder=self.embedder)
        
        perf.print_summary()
        
        # Start server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('localhost', self.port))
        self.socket.listen(5)
        
        self.running = True
        self.start_time = time.time()
        
        print(f"\n RAG server ready on localhost:{self.port}")
        print("   Model loaded, database connected")
        print("   Waiting for queries...\n")
        
        # Handle connections
        while self.running:
            try:
                client, addr = self.socket.accept()
                thread = threading.Thread(target=self._handle_client, args=(client,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Server error: {e}")
    
    def _handle_client(self, client: socket.socket):
        """Handle a client connection."""
        try:
            # Receive query with proper message framing
            data = self._receive_json(client)
            request = json.loads(data)
            
            # Check for shutdown command
            if request.get('command') == 'shutdown':
                print("\n Shutdown requested")
                response = {'success': True, 'message': 'Server shutting down'}
                self._send_json(client, response)
                self.stop()
                return
            
            query = request.get('query', '')
            top_k = request.get('top_k', 10)
            
            self.query_count += 1
            print(f"[Query #{self.query_count}] {query}")
            
            # Perform search
            start = time.time()
            results = self.searcher.search(query, top_k=top_k)
            search_time = time.time() - start
            
            # Prepare response
            response = {
                'success': True,
                'query': query,
                'count': len(results),
                'search_time_ms': int(search_time * 1000),
                'results': [r.to_dict() for r in results],
                'server_uptime': int(time.time() - self.start_time),
                'total_queries': self.query_count,
            }
            
            # Send response with proper framing
            self._send_json(client, response)
            
            print(f"    Found {len(results)} results in {search_time*1000:.0f}ms")
            
        except ConnectionError as e:
            # Normal disconnection - client closed connection
            # This is expected behavior, don't log as error
            pass
        except Exception as e:
            # Only log actual errors, not normal disconnections
            if "Connection closed" not in str(e):
                logger.error(f"Client handler error: {e}")
            error_response = {
                'success': False,
                'error': str(e)
            }
            try:
                self._send_json(client, error_response)
            except:
                pass
        finally:
            client.close()
    
    def _receive_json(self, sock: socket.socket) -> str:
        """Receive a complete JSON message with length prefix."""
        # First receive the length (4 bytes)
        length_data = b''
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                raise ConnectionError("Connection closed while receiving length")
            length_data += chunk
        
        length = int.from_bytes(length_data, 'big')
        
        # Now receive the actual data
        data = b''
        while len(data) < length:
            chunk = sock.recv(min(65536, length - len(data)))
            if not chunk:
                raise ConnectionError("Connection closed while receiving data")
            data += chunk
        
        return data.decode('utf-8')
    
    def _send_json(self, sock: socket.socket, data: dict):
        """Send a JSON message with length prefix."""
        # Sanitize the data to ensure JSON compatibility
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        
        # Send length prefix (4 bytes)
        length = len(json_bytes)
        sock.send(length.to_bytes(4, 'big'))
        
        # Send the data
        sock.sendall(json_bytes)
    
    def stop(self):
        """Stop the server."""
        self.running = False
        if self.socket:
            self.socket.close()
        print("\n RAG server stopped")


class RAGClient:
    """Client to communicate with RAG server."""
    
    def __init__(self, port: int = 7777):
        self.port = port
        self.use_legacy = False
        
    def search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Send search query to server."""
        try:
            # Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', self.port))
            
            # Send request with proper framing
            request = {
                'query': query,
                'top_k': top_k
            }
            self._send_json(sock, request)
            
            # Receive response with proper framing
            data = self._receive_json(sock)
            response = json.loads(data)
            
            sock.close()
            return response
            
        except ConnectionRefusedError:
            return {
                'success': False,
                'error': 'RAG server not running. Start with: rag-mini server'
            }
        except ConnectionError as e:
            # Try legacy mode without message framing
            if not self.use_legacy and "receiving length" in str(e):
                self.use_legacy = True
                return self._search_legacy(query, top_k)
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _receive_json(self, sock: socket.socket) -> str:
        """Receive a complete JSON message with length prefix."""
        # First receive the length (4 bytes)
        length_data = b''
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                raise ConnectionError("Connection closed while receiving length")
            length_data += chunk
        
        length = int.from_bytes(length_data, 'big')
        
        # Now receive the actual data
        data = b''
        while len(data) < length:
            chunk = sock.recv(min(65536, length - len(data)))
            if not chunk:
                raise ConnectionError("Connection closed while receiving data")
            data += chunk
        
        return data.decode('utf-8')
    
    def _send_json(self, sock: socket.socket, data: dict):
        """Send a JSON message with length prefix."""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        
        # Send length prefix (4 bytes)
        length = len(json_bytes)
        sock.send(length.to_bytes(4, 'big'))
        
        # Send the data
        sock.sendall(json_bytes)
    
    def _search_legacy(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Legacy search without message framing for old servers."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', self.port))
            
            # Send request (old way)
            request = {
                'query': query,
                'top_k': top_k
            }
            sock.send(json.dumps(request).encode('utf-8'))
            
            # Receive response (accumulate until we get valid JSON)
            data = b''
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                try:
                    # Try to decode as JSON
                    response = json.loads(data.decode('utf-8'))
                    sock.close()
                    return response
                except json.JSONDecodeError:
                    # Keep receiving
                    continue
            
            sock.close()
            return {
                'success': False,
                'error': 'Incomplete response from server'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_running(self) -> bool:
        """Check if server is running."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            return result == 0
        except:
            return False


def start_server(project_path: Path, port: int = 7777):
    """Start the RAG server."""
    server = RAGServer(project_path, port)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


def auto_start_if_needed(project_path: Path) -> Optional[subprocess.Popen]:
    """Auto-start server if not running."""
    client = RAGClient()
    if not client.is_running():
        # Start server in background
        import subprocess
        cmd = [sys.executable, "-m", "mini_rag.cli", "server", "--path", str(project_path)]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        # Wait for server to start
        for _ in range(30):  # 30 second timeout
            time.sleep(1)
            if client.is_running():
                print(" RAG server started automatically")
                return process
        
        # Failed to start
        process.terminate()
        raise RuntimeError("Failed to start RAG server")
    
    return None
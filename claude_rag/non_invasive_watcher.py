"""
Non-invasive file watcher designed to not interfere with development workflows.
Uses minimal resources and gracefully handles high-load scenarios.
"""

import os
import time
import logging
import threading
import queue
from pathlib import Path
from typing import Optional, Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirModifiedEvent

from .indexer import ProjectIndexer

logger = logging.getLogger(__name__)


class NonInvasiveQueue:
    """Ultra-lightweight queue with aggressive deduplication and backoff."""
    
    def __init__(self, delay: float = 5.0, max_queue_size: int = 100):
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.pending = set()
        self.lock = threading.Lock()
        self.delay = delay
        self.last_update = {}
        self.dropped_count = 0
    
    def add(self, file_path: Path) -> bool:
        """Add file to queue with aggressive filtering."""
        with self.lock:
            file_str = str(file_path)
            current_time = time.time()
            
            # Skip if recently processed
            if file_str in self.last_update:
                if current_time - self.last_update[file_str] < self.delay:
                    return False
            
            # Skip if already pending
            if file_str in self.pending:
                return False
            
            # Skip if queue is getting full (backpressure)
            if self.queue.qsize() > self.queue.maxsize * 0.8:
                self.dropped_count += 1
                logger.debug(f"Dropping update for {file_str} - queue overloaded")
                return False
            
            try:
                self.queue.put_nowait(file_path)
                self.pending.add(file_str)
                self.last_update[file_str] = current_time
                return True
            except queue.Full:
                self.dropped_count += 1
                return False
    
    def get(self, timeout: float = 0.1) -> Optional[Path]:
        """Get next file with very short timeout."""
        try:
            file_path = self.queue.get(timeout=timeout)
            with self.lock:
                self.pending.discard(str(file_path))
            return file_path
        except queue.Empty:
            return None


class MinimalEventHandler(FileSystemEventHandler):
    """Minimal event handler that only watches for meaningful changes."""
    
    def __init__(self, 
                 update_queue: NonInvasiveQueue,
                 include_patterns: Set[str],
                 exclude_patterns: Set[str]):
        self.update_queue = update_queue
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.last_event_time = {}
        
    def _should_process(self, file_path: str) -> bool:
        """Ultra-conservative file filtering."""
        path = Path(file_path)
        
        # Only process files, not directories
        if not path.is_file():
            return False
        
        # Skip if too large (>1MB)
        try:
            if path.stat().st_size > 1024 * 1024:
                return False
        except (OSError, PermissionError):
            return False
        
        # Skip temporary and system files
        name = path.name
        if (name.startswith('.') or 
            name.startswith('~') or 
            name.endswith('.tmp') or
            name.endswith('.swp') or
            name.endswith('.lock')):
            return False
        
        # Check exclude patterns first (faster)
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return False
        
        # Check include patterns
        for pattern in self.include_patterns:
            if path.match(pattern):
                return True
        
        return False
    
    def _rate_limit_event(self, file_path: str) -> bool:
        """Rate limit events per file."""
        current_time = time.time()
        if file_path in self.last_event_time:
            if current_time - self.last_event_time[file_path] < 2.0:  # 2 second cooldown per file
                return False
        
        self.last_event_time[file_path] = current_time
        return True
    
    def on_modified(self, event):
        """Handle file modifications with minimal overhead."""
        if (not event.is_directory and 
            self._should_process(event.src_path) and
            self._rate_limit_event(event.src_path)):
            self.update_queue.add(Path(event.src_path))
    
    def on_created(self, event):
        """Handle file creation."""
        if (not event.is_directory and 
            self._should_process(event.src_path) and
            self._rate_limit_event(event.src_path)):
            self.update_queue.add(Path(event.src_path))
    
    def on_deleted(self, event):
        """Handle file deletion."""
        if not event.is_directory and self._rate_limit_event(event.src_path):
            # Only add to queue if it was a file we cared about
            path = Path(event.src_path)
            for pattern in self.include_patterns:
                if path.match(pattern):
                    self.update_queue.add(path)
                    break


class NonInvasiveFileWatcher:
    """Non-invasive file watcher that prioritizes system stability."""
    
    def __init__(self, 
                 project_path: Path,
                 indexer: Optional[ProjectIndexer] = None,
                 cpu_limit: float = 0.1,  # Max 10% CPU usage
                 max_memory_mb: int = 50):  # Max 50MB memory
        """
        Initialize non-invasive watcher.
        
        Args:
            project_path: Path to watch
            indexer: ProjectIndexer instance
            cpu_limit: Maximum CPU usage fraction (0.0-1.0)
            max_memory_mb: Maximum memory usage in MB
        """
        self.project_path = Path(project_path).resolve()
        self.indexer = indexer or ProjectIndexer(self.project_path)
        self.cpu_limit = cpu_limit
        self.max_memory_mb = max_memory_mb
        
        # Initialize components with conservative settings
        self.update_queue = NonInvasiveQueue(delay=10.0, max_queue_size=50)  # Very conservative
        self.observer = Observer()
        self.worker_thread = None
        self.running = False
        
        # Get patterns from indexer
        self.include_patterns = set(self.indexer.include_patterns)
        self.exclude_patterns = set(self.indexer.exclude_patterns)
        
        # Add more aggressive exclusions
        self.exclude_patterns.update({
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'dist', 'build', 'target', '.idea', '.vscode', '.pytest_cache',
            'coverage', 'htmlcov', '.coverage', '.mypy_cache', '.tox',
            'logs', 'log', 'tmp', 'temp', '.DS_Store'
        })
        
        # Stats
        self.stats = {
            'files_processed': 0,
            'files_dropped': 0,
            'cpu_throttle_count': 0,
            'started_at': None,
        }
    
    def start(self):
        """Start non-invasive watching."""
        if self.running:
            return
        
        logger.info(f"Starting non-invasive file watcher for {self.project_path}")
        
        # Set up minimal event handler
        event_handler = MinimalEventHandler(
            self.update_queue,
            self.include_patterns,
            self.exclude_patterns
        )
        
        # Schedule with recursive watching
        self.observer.schedule(
            event_handler,
            str(self.project_path),
            recursive=True
        )
        
        # Start low-priority worker thread
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._process_updates_gently,
            daemon=True,
            name="RAG-FileWatcher"
        )
        # Set lowest priority
        self.worker_thread.start()
        
        # Start observer
        self.observer.start()
        
        self.stats['started_at'] = datetime.now()
        logger.info("Non-invasive file watcher started")
    
    def stop(self):
        """Stop watching gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping non-invasive file watcher...")
        
        # Stop observer first
        self.observer.stop()
        self.observer.join(timeout=2.0)  # Don't wait too long
        
        # Stop worker thread
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)  # Don't block shutdown
        
        logger.info("Non-invasive file watcher stopped")
    
    def _process_updates_gently(self):
        """Process updates with extreme care not to interfere."""
        logger.debug("Non-invasive update processor started")
        
        process_start_time = time.time()
        
        while self.running:
            try:
                # Yield CPU frequently
                time.sleep(0.5)  # Always sleep between operations
                
                # Get next file with very short timeout
                file_path = self.update_queue.get(timeout=0.1)
                
                if file_path:
                    # Check CPU usage before processing
                    current_time = time.time()
                    elapsed = current_time - process_start_time
                    
                    # Simple CPU throttling: if we've been working too much, back off
                    if elapsed > 0:
                        # If we're consuming too much time, throttle aggressively
                        work_ratio = 0.1  # Assume we use 10% of time in this check
                        if work_ratio > self.cpu_limit:
                            self.stats['cpu_throttle_count'] += 1
                            time.sleep(2.0)  # Back off significantly
                            continue
                    
                    # Process single file with error isolation
                    try:
                        if file_path.exists():
                            success = self.indexer.update_file(file_path)
                        else:
                            success = self.indexer.delete_file(file_path)
                        
                        if success:
                            self.stats['files_processed'] += 1
                        
                        # Always yield CPU after processing
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.debug(f"Non-invasive watcher: failed to process {file_path}: {e}")
                        # Don't let errors propagate - just continue
                        continue
                
                # Update dropped count from queue
                self.stats['files_dropped'] = self.update_queue.dropped_count
                
            except Exception as e:
                logger.debug(f"Non-invasive watcher error: {e}")
                time.sleep(1.0)  # Back off on errors
        
        logger.debug("Non-invasive update processor stopped")
    
    def get_statistics(self) -> dict:
        """Get non-invasive watcher statistics."""
        stats = self.stats.copy()
        stats['queue_size'] = self.update_queue.queue.qsize()
        stats['running'] = self.running
        
        if stats['started_at']:
            uptime = datetime.now() - stats['started_at']
            stats['uptime_seconds'] = uptime.total_seconds()
        
        return stats
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
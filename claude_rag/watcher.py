"""
File watching with queue-based updates to prevent race conditions.
Monitors project files and updates the index incrementally.
"""

import logging
import threading
import queue
import time
from pathlib import Path
from typing import Set, Optional, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent

from .indexer import ProjectIndexer

logger = logging.getLogger(__name__)


class UpdateQueue:
    """Thread-safe queue for file updates with deduplication."""
    
    def __init__(self, delay: float = 1.0):
        """
        Initialize update queue.
        
        Args:
            delay: Delay in seconds before processing updates (for debouncing)
        """
        self.queue = queue.Queue()
        self.pending = set()  # Track pending files to avoid duplicates
        self.lock = threading.Lock()
        self.delay = delay
        self.last_update = {}  # Track last update time per file
    
    def add(self, file_path: Path):
        """Add a file to the update queue."""
        with self.lock:
            file_str = str(file_path)
            current_time = time.time()
            
            # Check if we should debounce this update
            if file_str in self.last_update:
                if current_time - self.last_update[file_str] < self.delay:
                    return  # Skip this update
            
            self.last_update[file_str] = current_time
            
            if file_str not in self.pending:
                self.pending.add(file_str)
                self.queue.put(file_path)
    
    def get(self, timeout: Optional[float] = None) -> Optional[Path]:
        """Get next file from queue."""
        try:
            file_path = self.queue.get(timeout=timeout)
            with self.lock:
                self.pending.discard(str(file_path))
            return file_path
        except queue.Empty:
            return None
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()


class CodeFileEventHandler(FileSystemEventHandler):
    """Handles file system events for code files."""
    
    def __init__(self, 
                 update_queue: UpdateQueue,
                 include_patterns: Set[str],
                 exclude_patterns: Set[str],
                 project_path: Path):
        """
        Initialize event handler.
        
        Args:
            update_queue: Queue for file updates
            include_patterns: File patterns to include
            exclude_patterns: Patterns to exclude
            project_path: Root project path
        """
        self.update_queue = update_queue
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.project_path = project_path
    
    def _should_process(self, file_path: str) -> bool:
        """Check if file should be processed."""
        path = Path(file_path)
        
        # Check if it's a file (not directory)
        if not path.is_file():
            return False
        
        # Check exclude patterns
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return False
        
        # Check include patterns
        for pattern in self.include_patterns:
            if path.match(pattern):
                return True
        
        return False
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification."""
        if not event.is_directory and self._should_process(event.src_path):
            logger.debug(f"File modified: {event.src_path}")
            self.update_queue.add(Path(event.src_path))
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation."""
        if not event.is_directory and self._should_process(event.src_path):
            logger.debug(f"File created: {event.src_path}")
            self.update_queue.add(Path(event.src_path))
    
    def on_deleted(self, event: FileDeletedEvent):
        """Handle file deletion."""
        if not event.is_directory and self._should_process(event.src_path):
            logger.debug(f"File deleted: {event.src_path}")
            # Add deletion task to queue (we'll handle it differently)
            self.update_queue.add(Path(event.src_path))
    
    def on_moved(self, event: FileMovedEvent):
        """Handle file move/rename."""
        if not event.is_directory:
            logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
            # Handle move as delete old + create new
            if self._should_process(event.src_path):
                self.update_queue.add(Path(event.src_path))  # Delete old location
            if self._should_process(event.dest_path):
                self.update_queue.add(Path(event.dest_path))  # Add new location


class FileWatcher:
    """Watches project files and updates index automatically."""
    
    def __init__(self, 
                 project_path: Path,
                 indexer: Optional[ProjectIndexer] = None,
                 update_delay: float = 1.0,
                 batch_size: int = 10,
                 batch_timeout: float = 5.0):
        """
        Initialize file watcher.
        
        Args:
            project_path: Path to project to watch
            indexer: ProjectIndexer instance (creates one if not provided)
            update_delay: Delay before processing file changes (debouncing)
            batch_size: Number of files to process in a batch
            batch_timeout: Maximum time to wait for a full batch
        """
        self.project_path = Path(project_path).resolve()
        self.indexer = indexer or ProjectIndexer(self.project_path)
        self.update_delay = update_delay
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Initialize components
        self.update_queue = UpdateQueue(delay=update_delay)
        self.observer = Observer()
        self.worker_thread = None
        self.running = False
        
        # Get patterns from indexer
        self.include_patterns = set(self.indexer.include_patterns)
        self.exclude_patterns = set(self.indexer.exclude_patterns)
        
        # Statistics
        self.stats = {
            'files_updated': 0,
            'files_failed': 0,
            'started_at': None,
            'last_update': None,
        }
    
    def start(self):
        """Start watching for file changes."""
        if self.running:
            logger.warning("Watcher is already running")
            return
        
        logger.info(f"Starting file watcher for {self.project_path}")
        
        # Set up file system observer
        event_handler = CodeFileEventHandler(
            self.update_queue,
            self.include_patterns,
            self.exclude_patterns,
            self.project_path
        )
        
        self.observer.schedule(
            event_handler,
            str(self.project_path),
            recursive=True
        )
        
        # Start worker thread
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._process_updates,
            daemon=True
        )
        self.worker_thread.start()
        
        # Start observer
        self.observer.start()
        
        self.stats['started_at'] = datetime.now()
        logger.info("File watcher started successfully")
    
    def stop(self):
        """Stop watching for file changes."""
        if not self.running:
            return
        
        logger.info("Stopping file watcher...")
        
        # Stop observer
        self.observer.stop()
        self.observer.join()
        
        # Stop worker thread
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        logger.info("File watcher stopped")
    
    def _process_updates(self):
        """Worker thread that processes file updates."""
        logger.info("Update processor thread started")
        
        batch = []
        batch_start_time = None
        
        while self.running:
            try:
                # Calculate timeout for getting next item
                timeout = 0.1
                if batch:
                    # If we have items in batch, check if we should process them
                    elapsed = time.time() - batch_start_time
                    if elapsed >= self.batch_timeout or len(batch) >= self.batch_size:
                        # Process batch
                        self._process_batch(batch)
                        batch = []
                        batch_start_time = None
                        continue
                    else:
                        # Wait for more items or timeout
                        timeout = min(0.1, self.batch_timeout - elapsed)
                
                # Get next file from queue
                file_path = self.update_queue.get(timeout=timeout)
                
                if file_path:
                    # Add to batch
                    if not batch:
                        batch_start_time = time.time()
                    batch.append(file_path)
                    
                    # Check if batch is full
                    if len(batch) >= self.batch_size:
                        self._process_batch(batch)
                        batch = []
                        batch_start_time = None
                
            except queue.Empty:
                # Check if we have a pending batch that's timed out
                if batch and (time.time() - batch_start_time) >= self.batch_timeout:
                    self._process_batch(batch)
                    batch = []
                    batch_start_time = None
            
            except Exception as e:
                logger.error(f"Error in update processor: {e}")
                time.sleep(1)  # Prevent tight loop on error
        
        # Process any remaining items
        if batch:
            self._process_batch(batch)
        
        logger.info("Update processor thread stopped")
    
    def _process_batch(self, files: list[Path]):
        """Process a batch of file updates."""
        if not files:
            return
        
        logger.info(f"Processing batch of {len(files)} file updates")
        
        for file_path in files:
            try:
                if file_path.exists():
                    # File exists - update index
                    logger.debug(f"Updating index for {file_path}")
                    success = self.indexer.update_file(file_path)
                else:
                    # File doesn't exist - delete from index
                    logger.debug(f"Deleting {file_path} from index - file no longer exists")
                    success = self.indexer.delete_file(file_path)
                
                if success:
                    self.stats['files_updated'] += 1
                else:
                    self.stats['files_failed'] += 1
                
                self.stats['last_update'] = datetime.now()
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                self.stats['files_failed'] += 1
        
        logger.info(f"Batch processing complete. Updated: {self.stats['files_updated']}, Failed: {self.stats['files_failed']}")
    
    def get_statistics(self) -> dict:
        """Get watcher statistics."""
        stats = self.stats.copy()
        stats['queue_size'] = self.update_queue.size()
        stats['is_running'] = self.running
        
        if stats['started_at']:
            uptime = datetime.now() - stats['started_at']
            stats['uptime_seconds'] = uptime.total_seconds()
        
        return stats
    
    def wait_for_updates(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for pending updates to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all updates completed, False if timeout
        """
        start_time = time.time()
        
        while not self.update_queue.empty():
            if timeout and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.1)
        
        # Wait a bit more to ensure batch processing completes
        time.sleep(self.batch_timeout + 0.5)
        return True
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Convenience function
def watch_project(project_path: Path, callback: Optional[Callable] = None):
    """
    Watch a project for changes and update index automatically.
    
    Args:
        project_path: Path to project
        callback: Optional callback function called after each update
    """
    watcher = FileWatcher(project_path)
    
    try:
        watcher.start()
        logger.info(f"Watching {project_path} for changes. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
            # Call callback if provided
            if callback:
                stats = watcher.get_statistics()
                callback(stats)
            
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
    finally:
        watcher.stop()
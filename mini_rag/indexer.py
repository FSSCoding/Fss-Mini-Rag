"""
Parallel indexing engine for efficient codebase processing.
Handles file discovery, chunking, embedding, and storage.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import numpy as np
import lancedb
import pandas as pd
import pyarrow as pa
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console

from .ollama_embeddings import OllamaEmbedder as CodeEmbedder
from .chunker import CodeChunker, CodeChunk
from .path_handler import normalize_path, normalize_relative_path

logger = logging.getLogger(__name__)
console = Console()


class ProjectIndexer:
    """Indexes a project directory for semantic search."""
    
    def __init__(self, 
                 project_path: Path,
                 embedder: Optional[CodeEmbedder] = None,
                 chunker: Optional[CodeChunker] = None,
                 max_workers: int = 4):
        """
        Initialize the indexer.
        
        Args:
            project_path: Path to the project to index
            embedder: CodeEmbedder instance (creates one if not provided)
            chunker: CodeChunker instance (creates one if not provided)
            max_workers: Number of parallel workers for indexing
        """
        self.project_path = Path(project_path).resolve()
        self.rag_dir = self.project_path / '.mini-rag'
        self.manifest_path = self.rag_dir / 'manifest.json'
        self.config_path = self.rag_dir / 'config.json'
        
        # Create RAG directory if it doesn't exist
        self.rag_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.embedder = embedder or CodeEmbedder()
        self.chunker = chunker or CodeChunker()
        self.max_workers = max_workers
        
        # Initialize database connection
        self.db = None
        self.table = None
        
        # File patterns to include/exclude
        self.include_patterns = [
            # Code files
            '*.py', '*.js', '*.jsx', '*.ts', '*.tsx',
            '*.go', '*.java', '*.cpp', '*.c', '*.cs',
            '*.rs', '*.rb', '*.php', '*.swift', '*.kt',
            '*.scala', '*.r', '*.m', '*.h', '*.hpp',
            # Documentation files
            '*.md', '*.markdown', '*.rst', '*.txt',
            '*.adoc', '*.asciidoc',
            # Config files
            '*.json', '*.yaml', '*.yml', '*.toml', '*.ini',
            '*.xml', '*.conf', '*.config',
            # Other text files
            'README', 'LICENSE', 'CHANGELOG', 'AUTHORS',
            'CONTRIBUTING', 'TODO', 'NOTES'
        ]
        
        self.exclude_patterns = [
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'env', 'dist', 'build', 'target', '.idea', '.vscode',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '*.so', '*.dll',
            '*.dylib', '*.exe', '*.bin', '*.log', '*.lock'
        ]
        
        # Load existing manifest if it exists
        self.manifest = self._load_manifest()
        
    def _load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
        
        return {
            'version': '1.0',
            'indexed_at': None,
            'file_count': 0,
            'chunk_count': 0,
            'files': {}
        }
    
    def _save_manifest(self):
        """Save manifest to disk."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load or create comprehensive configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Apply any loaded settings
                    self._apply_config(config)
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
        
        # Default configuration - comprehensive and user-friendly
        config = {
            "project": {
                "name": self.project_path.name,
                "description": f"RAG index for {self.project_path.name}",
                "created_at": datetime.now().isoformat()
            },
            "embedding": {
                "provider": "ollama",
                "model": self.embedder.model_name if hasattr(self.embedder, 'model_name') else 'nomic-embed-text:latest',
                "base_url": "http://localhost:11434",
                "batch_size": 4,
                "max_workers": 4
            },
            "chunking": {
                "max_size": self.chunker.max_chunk_size if hasattr(self.chunker, 'max_chunk_size') else 2500,
                "min_size": self.chunker.min_chunk_size if hasattr(self.chunker, 'min_chunk_size') else 100,
                "overlap": 100,
                "strategy": "semantic"
            },
            "streaming": {
                "enabled": True,
                "threshold_mb": 1,
                "chunk_size_kb": 64
            },
            "files": {
                "include_patterns": self.include_patterns,
                "exclude_patterns": self.exclude_patterns,
                "max_file_size_mb": 50,
                "encoding_fallbacks": ["utf-8", "latin-1", "cp1252", "utf-8-sig"]
            },
            "indexing": {
                "parallel_workers": self.max_workers,
                "incremental": True,
                "track_changes": True,
                "skip_binary": True
            },
            "search": {
                "default_limit": 10,
                "similarity_threshold": 0.7,
                "hybrid_search": True,
                "bm25_weight": 0.3
            },
            "storage": {
                "compress_vectors": False,
                "index_type": "ivf_pq",
                "cleanup_old_chunks": True
            }
        }
        
        # Save comprehensive config with nice formatting
        self._save_config(config)
        return config
    
    def _apply_config(self, config: Dict[str, Any]):
        """Apply configuration settings to the indexer."""
        try:
            # Apply embedding settings
            if 'embedding' in config:
                emb_config = config['embedding']
                if hasattr(self.embedder, 'model_name'):
                    self.embedder.model_name = emb_config.get('model', self.embedder.model_name)
                if hasattr(self.embedder, 'base_url'):
                    self.embedder.base_url = emb_config.get('base_url', self.embedder.base_url)
            
            # Apply chunking settings
            if 'chunking' in config:
                chunk_config = config['chunking']
                if hasattr(self.chunker, 'max_chunk_size'):
                    self.chunker.max_chunk_size = chunk_config.get('max_size', self.chunker.max_chunk_size)
                if hasattr(self.chunker, 'min_chunk_size'):
                    self.chunker.min_chunk_size = chunk_config.get('min_size', self.chunker.min_chunk_size)
            
            # Apply file patterns
            if 'files' in config:
                file_config = config['files']
                self.include_patterns = file_config.get('include_patterns', self.include_patterns)
                self.exclude_patterns = file_config.get('exclude_patterns', self.exclude_patterns)
            
            # Apply indexing settings
            if 'indexing' in config:
                idx_config = config['indexing']
                self.max_workers = idx_config.get('parallel_workers', self.max_workers)
                
        except Exception as e:
            logger.warning(f"Failed to apply some config settings: {e}")
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration with nice formatting and comments."""
        try:
            # Add helpful comments as a separate file
            config_with_comments = {
                "_comment": "RAG System Configuration - Edit this file to customize indexing behavior",
                "_version": "2.0",
                "_docs": "See README.md for detailed configuration options",
                **config
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_with_comments, f, indent=2, sort_keys=True)
                
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            return ""
    
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed based on patterns and content."""
        # Check file size (skip files > 1MB)
        try:
            if file_path.stat().st_size > 1_000_000:
                return False
        except:
            return False
        
        # Check exclude patterns first
        path_str = str(file_path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return False
        
        # Check include patterns (extension-based)
        for pattern in self.include_patterns:
            if file_path.match(pattern):
                return True
        
        # NEW: Content-based inclusion for extensionless files
        if not file_path.suffix:
            return self._should_index_extensionless_file(file_path)
        
        return False
    
    def _should_index_extensionless_file(self, file_path: Path) -> bool:
        """Check if an extensionless file should be indexed based on content."""
        try:
            # Read first 1KB to check content
            with open(file_path, 'rb') as f:
                first_chunk = f.read(1024)
            
            # Check if it's a text file (not binary)
            try:
                text_content = first_chunk.decode('utf-8')
            except UnicodeDecodeError:
                return False  # Binary file, skip
            
            # Check for code indicators
            code_indicators = [
                '#!/usr/bin/env python', '#!/usr/bin/python', '#!.*python',
                'import ', 'from ', 'def ', 'class ', 'if __name__',
                'function ', 'var ', 'const ', 'let ', 'package main',
                'public class', 'private class', 'public static void'
            ]
            
            text_lower = text_content.lower()
            for indicator in code_indicators:
                if indicator in text_lower:
                    return True
            
            # Check for configuration files
            config_indicators = [
                '#!/bin/bash', '#!/bin/sh', '[', 'version =', 'name =',
                'description =', 'author =', '<configuration>', '<?xml'
            ]
            
            for indicator in config_indicators:
                if indicator in text_lower:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _needs_reindex(self, file_path: Path) -> bool:
        """Smart check if a file needs to be reindexed - optimized for speed."""
        file_str = normalize_relative_path(file_path, self.project_path)
        
        # Not in manifest - needs indexing
        if file_str not in self.manifest['files']:
            return True
        
        file_info = self.manifest['files'][file_str]
        
        try:
            stat = file_path.stat()
            
            # Quick checks first (no I/O) - check size and modification time
            stored_size = file_info.get('size', 0)
            stored_mtime = file_info.get('mtime', 0)
            
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            
            # If size or mtime changed, definitely needs reindex
            if current_size != stored_size or current_mtime != stored_mtime:
                return True
            
            # Size and mtime same - check hash only if needed (for paranoia)
            # This catches cases where content changed but mtime didn't (rare but possible)
            current_hash = self._get_file_hash(file_path)
            stored_hash = file_info.get('hash', '')
            
            return current_hash != stored_hash
            
        except (OSError, IOError) as e:
            logger.warning(f"Could not check file stats for {file_path}: {e}")
            # If we can't check file stats, assume it needs reindex
            return True
    
    def _cleanup_removed_files(self):
        """Remove entries for files that no longer exist from manifest and database."""
        if 'files' not in self.manifest:
            return
        
        removed_files = []
        for file_str in list(self.manifest['files'].keys()):
            file_path = self.project_path / file_str
            if not file_path.exists():
                removed_files.append(file_str)
        
        if removed_files:
            logger.info(f"Cleaning up {len(removed_files)} removed files from index")
            
            for file_str in removed_files:
                # Remove from database
                try:
                    if hasattr(self, 'table') and self.table:
                        self.table.delete(f"file_path = '{file_str}'")
                        logger.debug(f"Removed chunks for deleted file: {file_str}")
                except Exception as e:
                    logger.warning(f"Could not remove chunks for {file_str}: {e}")
                
                # Remove from manifest
                del self.manifest['files'][file_str]
            
            # Save updated manifest
            self._save_manifest()
            logger.info(f"Cleanup complete - removed {len(removed_files)} files")
    
    def _get_files_to_index(self) -> List[Path]:
        """Get all files that need to be indexed."""
        files_to_index = []
        
        # Walk through project directory
        for root, dirs, files in os.walk(self.project_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.exclude_patterns)]
            
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                
                if self._should_index_file(file_path) and self._needs_reindex(file_path):
                    files_to_index.append(file_path)
        
        return files_to_index
    
    def _process_file(self, file_path: Path, stream_threshold: int = 1024 * 1024) -> Optional[List[Dict[str, Any]]]:
        """Process a single file: read, chunk, embed.
        
        Args:
            file_path: Path to the file to process
            stream_threshold: Files larger than this (in bytes) use streaming (default: 1MB)
        """
        try:
            # Check file size for streaming decision
            file_size = file_path.stat().st_size
            
            if file_size > stream_threshold:
                logger.info(f"Streaming large file ({file_size:,} bytes): {file_path}")
                content = self._read_file_streaming(file_path)
            else:
                # Read file content normally for small files
                content = file_path.read_text(encoding='utf-8')
            
            # Chunk the file
            chunks = self.chunker.chunk_file(file_path, content)
            
            if not chunks:
                return None
            
            # Prepare data for embedding
            chunk_texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.embedder.embed_code(chunk_texts)
            
            # Prepare records for database
            records = []
            expected_dim = self.embedder.get_embedding_dim()
            
            for i, chunk in enumerate(chunks):
                # Validate embedding
                embedding = embeddings[i].astype(np.float32)
                if embedding.shape != (expected_dim,):
                    raise ValueError(
                        f"Invalid embedding dimension for {file_path} chunk {i}: "
                        f"expected ({expected_dim},), got {embedding.shape}"
                    )
                
                record = {
                    'file_path': normalize_relative_path(file_path, self.project_path),
                    'absolute_path': normalize_path(file_path),
                    'chunk_id': f"{file_path.stem}_{i}",
                    'content': chunk.content,
                    'start_line': int(chunk.start_line),
                    'end_line': int(chunk.end_line),
                    'chunk_type': chunk.chunk_type,
                    'name': chunk.name or f"chunk_{i}",
                    'language': chunk.language,
                    'embedding': embedding,  # Keep as numpy array
                    'indexed_at': datetime.now().isoformat(),
                    # Add new metadata fields
                    'file_lines': int(chunk.file_lines) if chunk.file_lines else 0,
                    'chunk_index': int(chunk.chunk_index) if chunk.chunk_index is not None else i,
                    'total_chunks': int(chunk.total_chunks) if chunk.total_chunks else len(chunks),
                    'parent_class': chunk.parent_class or '',
                    'parent_function': chunk.parent_function or '',
                    'prev_chunk_id': chunk.prev_chunk_id or '',
                    'next_chunk_id': chunk.next_chunk_id or '',
                }
                records.append(record)
            
            # Update manifest with enhanced tracking
            file_str = normalize_relative_path(file_path, self.project_path)
            stat = file_path.stat()
            self.manifest['files'][file_str] = {
                'hash': self._get_file_hash(file_path),
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'chunks': len(chunks),
                'indexed_at': datetime.now().isoformat(),
                'language': chunks[0].language if chunks else 'unknown',
                'encoding': 'utf-8'  # Track encoding used
            }
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None
    
    def _read_file_streaming(self, file_path: Path, chunk_size: int = 64 * 1024) -> str:
        """
        Read large files in chunks to avoid loading entirely into memory.
        
        Args:
            file_path: Path to the file to read
            chunk_size: Size of each read chunk in bytes (default: 64KB)
            
        Returns:
            Complete file content as string
        """
        content_parts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)
            
            logger.debug(f"Streamed {len(content_parts)} chunks from {file_path}")
            return ''.join(content_parts)
            
        except UnicodeDecodeError:
            # Try with different encodings for problematic files
            for encoding in ['latin-1', 'cp1252', 'utf-8-sig']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content_parts = []
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            content_parts.append(chunk)
                    
                    logger.debug(f"Streamed {len(content_parts)} chunks from {file_path} using {encoding}")
                    return ''.join(content_parts)
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, return empty string
            logger.warning(f"Could not decode {file_path} with any encoding")
            return ""
    
    def _init_database(self):
        """Initialize LanceDB connection and table."""
        try:
            self.db = lancedb.connect(self.rag_dir)
            
            # Define schema with fixed-size vector
            embedding_dim = self.embedder.get_embedding_dim()
            schema = pa.schema([
                pa.field("file_path", pa.string()),
                pa.field("absolute_path", pa.string()),
                pa.field("chunk_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("start_line", pa.int32()),
                pa.field("end_line", pa.int32()),
                pa.field("chunk_type", pa.string()),
                pa.field("name", pa.string()),
                pa.field("language", pa.string()),
                pa.field("embedding", pa.list_(pa.float32(), embedding_dim)),  # Fixed-size list
                pa.field("indexed_at", pa.string()),
                # New metadata fields
                pa.field("file_lines", pa.int32()),
                pa.field("chunk_index", pa.int32()),
                pa.field("total_chunks", pa.int32()),
                pa.field("parent_class", pa.string(), nullable=True),
                pa.field("parent_function", pa.string(), nullable=True),
                pa.field("prev_chunk_id", pa.string(), nullable=True),
                pa.field("next_chunk_id", pa.string(), nullable=True),
            ])
            
            # Create or open table
            if "code_vectors" in self.db.table_names():
                try:
                    # Try to open existing table
                    self.table = self.db.open_table("code_vectors")
                    
                    # Check if schema matches by trying to get the schema
                    existing_schema = self.table.schema
                    
                    # Check if all required fields exist
                    required_fields = {field.name for field in schema}
                    existing_fields = {field.name for field in existing_schema}
                    
                    if not required_fields.issubset(existing_fields):
                        # Schema mismatch - drop and recreate table
                        logger.warning("Schema mismatch detected. Dropping and recreating table.")
                        self.db.drop_table("code_vectors")
                        self.table = self.db.create_table("code_vectors", schema=schema)
                        logger.info("Recreated code_vectors table with updated schema")
                    else:
                        logger.info("Opened existing code_vectors table")
                except Exception as e:
                    logger.warning(f"Failed to open existing table: {e}. Recreating...")
                    if "code_vectors" in self.db.table_names():
                        self.db.drop_table("code_vectors")
                    self.table = self.db.create_table("code_vectors", schema=schema)
                    logger.info("Recreated code_vectors table")
            else:
                # Create empty table with schema
                self.table = self.db.create_table("code_vectors", schema=schema)
                logger.info(f"Created new code_vectors table with embedding dimension {embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def index_project(self, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Index the entire project.
        
        Args:
            force_reindex: If True, reindex all files regardless of changes
            
        Returns:
            Dictionary with indexing statistics
        """
        start_time = datetime.now()
        
        # Initialize database
        self._init_database()
        
        # Clean up removed files (essential for portability)
        if not force_reindex:
            self._cleanup_removed_files()
        
        # Clear manifest if force reindex
        if force_reindex:
            self.manifest = {
                'version': '1.0',
                'indexed_at': None,
                'file_count': 0,
                'chunk_count': 0,
                'files': {}
            }
            # Clear existing table
            if "code_vectors" in self.db.table_names():
                self.db.drop_table("code_vectors")
                self.table = None
                # Reinitialize the database to recreate the table
                self._init_database()
        
        # Get files to index
        files_to_index = self._get_files_to_index()
        
        if not files_to_index:
            console.print("[green][/green] All files are up to date!")
            return {
                'files_indexed': 0,
                'chunks_created': 0,
                'time_taken': 0,
            }
        
        console.print(f"[cyan]Found {len(files_to_index)} files to index[/cyan]")
        
        # Process files in parallel
        all_records = []
        failed_files = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task(
                "[cyan]Indexing files...", 
                total=len(files_to_index)
            )
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(self._process_file, file_path): file_path
                    for file_path in files_to_index
                }
                
                # Process completed files
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        records = future.result()
                        if records:
                            all_records.extend(records)
                    except Exception as e:
                        logger.error(f"Failed to process {file_path}: {e}")
                        failed_files.append(file_path)
                    
                    progress.advance(task)
        
        # Batch insert all records
        if all_records:
            try:
                df = pd.DataFrame(all_records)
                # Ensure correct data types
                df["start_line"] = df["start_line"].astype("int32")
                df["end_line"] = df["end_line"].astype("int32")
                df["file_lines"] = df["file_lines"].astype("int32")
                df["chunk_index"] = df["chunk_index"].astype("int32")
                df["total_chunks"] = df["total_chunks"].astype("int32")
                
                # Table should already be created in _init_database
                if self.table is None:
                    raise RuntimeError("Table not initialized properly")
                
                self.table.add(df)
                    
                console.print(f"[green][/green] Added {len(all_records)} chunks to database")
            except Exception as e:
                logger.error(f"Failed to insert records: {e}")
                raise
        
        # Update manifest
        self.manifest['indexed_at'] = datetime.now().isoformat()
        self.manifest['file_count'] = len(self.manifest['files'])
        self.manifest['chunk_count'] = sum(
            f['chunks'] for f in self.manifest['files'].values()
        )
        self._save_manifest()
        
        # Calculate statistics
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        
        stats = {
            'files_indexed': len(files_to_index) - len(failed_files),
            'files_failed': len(failed_files),
            'chunks_created': len(all_records),
            'time_taken': time_taken,
            'files_per_second': len(files_to_index) / time_taken if time_taken > 0 else 0,
        }
        
        # Print summary
        console.print("\n[bold green]Indexing Complete![/bold green]")
        console.print(f"Files indexed: {stats['files_indexed']}")
        console.print(f"Chunks created: {stats['chunks_created']}")
        console.print(f"Time taken: {stats['time_taken']:.2f} seconds")
        console.print(f"Speed: {stats['files_per_second']:.1f} files/second")
        
        if failed_files:
            console.print(f"\n[yellow]Warning:[/yellow] {len(failed_files)} files failed to index")
        
        return stats
    
    def update_file(self, file_path: Path) -> bool:
        """
        Update index for a single file with proper vector multiply in/out.
        
        Args:
            file_path: Path to the file to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure database is initialized
            if self.table is None:
                self._init_database()
            
            # Get normalized file path for consistent lookup
            file_str = normalize_relative_path(file_path, self.project_path)
            
            # Process the file to get new chunks
            records = self._process_file(file_path)
            
            if records:
                # Create DataFrame with proper types
                df = pd.DataFrame(records)
                df["start_line"] = df["start_line"].astype("int32")
                df["end_line"] = df["end_line"].astype("int32")
                df["file_lines"] = df["file_lines"].astype("int32")
                df["chunk_index"] = df["chunk_index"].astype("int32")
                df["total_chunks"] = df["total_chunks"].astype("int32")
                
                # Use vector store's update method (multiply out old, multiply in new)
                if hasattr(self, '_vector_store') and self._vector_store:
                    success = self._vector_store.update_file_vectors(file_str, df)
                else:
                    # Fallback: delete by file path and add new data
                    try:
                        self.table.delete(f"file = '{file_str}'")
                    except Exception as e:
                        logger.debug(f"Could not delete existing chunks (might not exist): {e}")
                    self.table.add(df)
                    success = True
                
                if success:
                    # Update manifest with enhanced file tracking
                    file_hash = self._get_file_hash(file_path)
                    stat = file_path.stat()
                    if 'files' not in self.manifest:
                        self.manifest['files'] = {}
                    self.manifest['files'][file_str] = {
                        'hash': file_hash,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'chunks': len(records),
                        'last_updated': datetime.now().isoformat(),
                        'language': records[0].get('language', 'unknown') if records else 'unknown',
                        'encoding': 'utf-8'
                    }
                    self._save_manifest()
                    logger.debug(f"Successfully updated {len(records)} chunks for {file_str}")
                    return True
            else:
                # File exists but has no processable content - remove existing chunks
                if hasattr(self, '_vector_store') and self._vector_store:
                    self._vector_store.delete_by_file(file_str)
                else:
                    try:
                        self.table.delete(f"file = '{file_str}'")
                    except Exception:
                        pass
                logger.debug(f"Removed chunks for empty/unprocessable file: {file_str}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update {file_path}: {e}")
            return False
    
    def delete_file(self, file_path: Path) -> bool:
        """
        Delete all chunks for a file from the index.
        
        Args:
            file_path: Path to the file to delete from index
            
        Returns:
            True if successful, False otherwise  
        """
        try:
            if self.table is None:
                self._init_database()
            
            file_str = normalize_relative_path(file_path, self.project_path)
            
            # Delete from vector store
            if hasattr(self, '_vector_store') and self._vector_store:
                success = self._vector_store.delete_by_file(file_str)
            else:
                try:
                    self.table.delete(f"file = '{file_str}'")
                    success = True
                except Exception as e:
                    logger.error(f"Failed to delete {file_str}: {e}")  
                    success = False
            
            # Update manifest
            if success and 'files' in self.manifest and file_str in self.manifest['files']:
                del self.manifest['files'][file_str]
                self._save_manifest()
                logger.debug(f"Deleted chunks for file: {file_str}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        stats = {
            'project_path': str(self.project_path),
            'indexed_at': self.manifest.get('indexed_at', 'Never'),
            'file_count': self.manifest.get('file_count', 0),
            'chunk_count': self.manifest.get('chunk_count', 0),
            'index_size_mb': 0,
        }
        
        # Calculate index size
        try:
            db_path = self.rag_dir / 'code_vectors.lance'
            if db_path.exists():
                size_bytes = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
                stats['index_size_mb'] = size_bytes / (1024 * 1024)
        except:
            pass
        
        return stats
"""
Cross-platform path handler for the RAG system.
Handles forward/backward slashes on any file system.
No more path bullshit!
"""

import os
import sys
from pathlib import Path
from typing import Union, List


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path to always use forward slashes.
    This ensures consistency across platforms in storage.
    
    Args:
        path: Path as string or Path object
        
    Returns:
        Path string with forward slashes
    """
    # Convert to Path object first
    path_obj = Path(path)
    
    # Convert to string and replace backslashes
    path_str = str(path_obj).replace('\\', '/')
    
    # Handle UNC paths on Windows
    if sys.platform == 'win32' and path_str.startswith('//'):
        # Keep UNC paths as they are
        return path_str
    
    return path_str


def normalize_relative_path(path: Union[str, Path], base: Union[str, Path]) -> str:
    """
    Get a normalized relative path.
    
    Args:
        path: Path to make relative
        base: Base path to be relative to
        
    Returns:
        Relative path with forward slashes
    """
    path_obj = Path(path).resolve()
    base_obj = Path(base).resolve()
    
    try:
        rel_path = path_obj.relative_to(base_obj)
        return normalize_path(rel_path)
    except ValueError:
        # Path is not relative to base, return normalized absolute
        return normalize_path(path_obj)


def denormalize_path(path_str: str) -> Path:
    """
    Convert a normalized path string back to a Path object.
    This handles the conversion from storage format to OS format.
    
    Args:
        path_str: Normalized path string with forward slashes
        
    Returns:
        Path object appropriate for the OS
    """
    # Path constructor handles forward slashes on all platforms
    return Path(path_str)


def join_paths(*parts: Union[str, Path]) -> str:
    """
    Join path parts and return normalized result.
    
    Args:
        *parts: Path parts to join
        
    Returns:
        Normalized joined path
    """
    # Use Path to join, then normalize
    joined = Path(*[str(p) for p in parts])
    return normalize_path(joined)


def split_path(path: Union[str, Path]) -> List[str]:
    """
    Split a path into its components.
    
    Args:
        path: Path to split
        
    Returns:
        List of path components
    """
    path_obj = Path(path)
    parts = []
    
    # Handle drive on Windows
    if path_obj.drive:
        parts.append(path_obj.drive)
    
    # Add all other parts
    parts.extend(path_obj.parts[1:] if path_obj.drive else path_obj.parts)
    
    return parts


def ensure_forward_slashes(path_str: str) -> str:
    """
    Quick function to ensure a path string uses forward slashes.
    
    Args:
        path_str: Path string
        
    Returns:
        Path with forward slashes
    """
    return path_str.replace('\\', '/')


def ensure_native_slashes(path_str: str) -> str:
    """
    Ensure a path uses the native separator for the OS.
    
    Args:
        path_str: Path string
        
    Returns:
        Path with native separators
    """
    return str(Path(path_str))


# Convenience functions for common operations
def storage_path(path: Union[str, Path]) -> str:
    """Convert path to storage format (forward slashes)."""
    return normalize_path(path)


def display_path(path: Union[str, Path]) -> str:
    """Convert path to display format (native separators)."""
    return ensure_native_slashes(str(path))


def from_storage_path(path_str: str) -> Path:
    """Convert from storage format to Path object."""
    return denormalize_path(path_str)
"""
System Context Collection for Enhanced RAG Grounding

Collects minimal system information to help the LLM provide better,
context-aware assistance without compromising privacy.
"""

import platform
import sys
from pathlib import Path
from typing import Dict, Optional


class SystemContextCollector:
    """Collects system context information for enhanced LLM grounding."""

    @staticmethod
    def get_system_context(project_path: Optional[Path] = None) -> str:
        """
        Get concise system context for LLM grounding.

        Args:
            project_path: Current project directory

        Returns:
            Formatted system context string (max 200 chars for privacy)
        """
        try:
            # Basic system info
            os_name = platform.system()
            python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"

            # Simplified OS names
            os_short = {"Windows": "Win", "Linux": "Linux", "Darwin": "macOS"}.get(
                os_name, os_name
            )

            # Working directory info
            if project_path:
                # Use relative or shortened path for privacy
                try:
                    rel_path = project_path.relative_to(Path.home())
                    path_info = f"~/{rel_path}"
                except ValueError:
                    # If not relative to home, just use folder name
                    path_info = project_path.name
            else:
                path_info = Path.cwd().name

            # Trim path if too long for our 200-char limit
            if len(path_info) > 50:
                path_info = f".../{path_info[-45:]}"

            # Command style hints
            cmd_style = "rag.bat" if os_name == "Windows" else "./rag-mini"

            # Format concise context
            context = f"[{os_short} {python_ver}, {path_info}, use {cmd_style}]"

            # Ensure we stay under 200 chars
            if len(context) > 200:
                context = context[:197] + "...]"

            return context

        except Exception:
            # Fallback to minimal info if anything fails
            return f"[{platform.system()}, Python {sys.version_info.major}.{sys.version_info.minor}]"

    @staticmethod
    def get_command_context(os_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get OS-appropriate command examples.

        Returns:
            Dictionary with command patterns for the current OS
        """
        if os_name is None:
            os_name = platform.system()

        if os_name == "Windows":
            return {
                "launcher": "rag.bat",
                "index": "rag.bat index C:\\path\\to\\project",
                "search": 'rag.bat search C:\\path\\to\\project "query"',
                "explore": "rag.bat explore C:\\path\\to\\project",
                "path_sep": "\\",
                "example_path": "C:\\Users\\username\\Documents\\myproject",
            }
        else:
            return {
                "launcher": "./rag-mini",
                "index": "./rag-mini index /path/to/project",
                "search": './rag-mini search /path/to/project "query"',
                "explore": "./rag-mini explore /path/to/project",
                "path_sep": "/",
                "example_path": "~/Documents/myproject",
            }


def get_system_context(project_path: Optional[Path] = None) -> str:
    """Convenience function to get system context."""
    return SystemContextCollector.get_system_context(project_path)


def get_command_context() -> Dict[str, str]:
    """Convenience function to get command context."""
    return SystemContextCollector.get_command_context()


# Test function

if __name__ == "__main__":
    print("System Context Test:")
    print(f"Context: {get_system_context()}")
    print(f"Context with path: {get_system_context(Path('/tmp/test'))}")
    print()
    print("Command Context:")
    cmds = get_command_context()
    for key, value in cmds.items():
        print(f"  {key}: {value}")

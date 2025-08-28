"""
Windows Console Unicode/Emoji Fix
Reliable Windows console Unicode/emoji support for 2025.
"""

import io
import os
import sys


def fix_windows_console():
    """
    Fix Windows console to properly handle UTF-8 and emojis.
    Call this at the start of any script that needs to output Unicode/emojis.
    """
    # Set environment variable for UTF-8 mode
    os.environ["PYTHONUTF8"] = "1"

    # For Python 3.7+
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    else:
        # For older Python versions
        if sys.platform == "win32":
            # Replace streams with UTF-8 versions
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", line_buffering=True
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", line_buffering=True
            )

    # Also set the console code page to UTF-8 on Windows
    if sys.platform == "win32":
        import subprocess

        try:
            # Set console to UTF-8 code page
            subprocess.run(["chcp", "65001"], shell=True, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            pass


# Auto-fix on import
fix_windows_console()


# Test function to verify it works


def test_emojis():
    """Test that emojis work properly."""
    print("Testing emoji output:")
    print(" Check mark")
    print(" Cross mark")
    print(" Rocket")
    print(" Fire")
    print(" Computer")
    print(" Python")
    print(" Folder")
    print(" Search")
    print(" Lightning")
    print(" Sparkles")


if __name__ == "__main__":
    test_emojis()

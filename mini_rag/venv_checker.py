#!/usr/bin/env python3
"""
Virtual Environment Checker
Ensures scripts run in proper Python virtual environment for consistency and safety.
"""

import os
import sys
from pathlib import Path


def is_in_virtualenv() -> bool:
    """Check if we're running in a virtual environment."""
    # Check for virtual environment indicators
    return (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)  # virtualenv
        or os.environ.get("VIRTUAL_ENV") is not None  # venv/pyvenv  # Environment variable
    )


def get_expected_venv_path() -> Path:
    """Get the expected virtual environment path for this project."""
    # Assume .venv in the same directory as the script
    script_dir = Path(__file__).parent.parent
    return script_dir / ".venv"


def check_correct_venv() -> tuple[bool, str]:
    """
    Check if we're in the correct virtual environment.

    Returns:
        (is_correct, message)
    """
    if not is_in_virtualenv():
        return False, "not in virtual environment"

    expected_venv = get_expected_venv_path()
    if not expected_venv.exists():
        return False, "expected virtual environment not found"

    current_venv = os.environ.get("VIRTUAL_ENV")
    if current_venv:
        current_venv_path = Path(current_venv).resolve()
        expected_venv_path = expected_venv.resolve()

        if current_venv_path != expected_venv_path:
            return (
                False,
                f"wrong virtual environment (using {current_venv_path}, expected {expected_venv_path})",
            )

    return True, "correct virtual environment"


def show_venv_warning(script_name: str = "script") -> None:
    """Show virtual environment warning with helpful instructions."""
    expected_venv = get_expected_venv_path()

    print("⚠️  VIRTUAL ENVIRONMENT WARNING")
    print("=" * 50)
    print()
    print(f"This {script_name} should be run in a Python virtual environment for:")
    print("  • Consistent dependencies")
    print("  • Isolated package versions")
    print("  • Proper security isolation")
    print("  • Reliable functionality")
    print()

    if expected_venv.exists():
        print("✅ Virtual environment found!")
        print(f"   Location: {expected_venv}")
        print()
        print("🚀 To activate it:")
        print(f"   source {expected_venv}/bin/activate")
        print(f"   {script_name}")
        print()
        print("🔄 Or run with activation:")
        print(f"   source {expected_venv}/bin/activate && {script_name}")
    else:
        print("❌ No virtual environment found!")
        print()
        print("🛠️  Create one first:")
        print("   ./install.sh")
        print()
        print("📚 Or manually:")
        print(f"   python3 -m venv {expected_venv}")
        print(f"   source {expected_venv}/bin/activate")
        print("   pip install -r requirements.txt")

    print()
    print("💡 Why this matters:")
    print("   Without a virtual environment, you may experience:")
    print("   • Import errors from missing packages")
    print("   • Version conflicts with system Python")
    print("   • Inconsistent behavior across systems")
    print("   • Potential system-wide package pollution")
    print()


def check_and_warn_venv(script_name: str = "script", force_exit: bool = False) -> bool:
    """
    Check virtual environment and warn if needed.

    Args:
        script_name: Name of the script for user-friendly messages
        force_exit: Whether to exit if not in correct venv

    Returns:
        True if in correct venv, False otherwise
    """
    # Skip check if running as pip-installed entry point in a venv
    # (sys.prefix differs from base_prefix = we're in a venv via shebang)
    if hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix:
        return True

    # Skip venv warning if running through global wrapper
    if os.environ.get("FSS_MINI_RAG_GLOBAL_WRAPPER"):
        return True

    is_correct, message = check_correct_venv()

    if not is_correct:
        show_venv_warning(script_name)

        if force_exit:
            print(f"⛔ Exiting {script_name} for your safety.")
            print("   Please activate the virtual environment and try again.")
            sys.exit(1)
        else:
            print(f"⚠️  Continuing anyway, but {script_name} may not work correctly...")
            print()
            return False

    return True


def require_venv(script_name: str = "script") -> None:
    """Require virtual environment or exit."""
    check_and_warn_venv(script_name, force_exit=True)


# Quick test function


def main():
    """Test the virtual environment checker."""
    print("🧪 Virtual Environment Checker Test")
    print("=" * 40)

    print(f"In virtual environment: {is_in_virtualenv()}")
    print(f"Expected venv path: {get_expected_venv_path()}")

    is_correct, message = check_correct_venv()
    print(f"Correct venv: {is_correct} ({message})")

    if not is_correct:
        show_venv_warning("test script")


if __name__ == "__main__":
    main()

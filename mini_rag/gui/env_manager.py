"""Secure API key management via .env files.

Keys are stored in ~/.config/fss-mini-rag/.env with 0600 permissions.
The file format is standard KEY=VALUE with # comments preserved on save.

This module also syncs keys to os.environ so services can access them
via os.environ.get() without knowing about the .env file.
"""

import logging
import os
import stat
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ENV_DIR = Path.home() / ".config" / "fss-mini-rag"
ENV_FILE = ENV_DIR / ".env"

# Keys we manage — anything else in the file is left untouched
MANAGED_KEYS = {
    "LLM_API_KEY",
    "EMBEDDING_API_KEY",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
}


def load_env() -> Dict[str, str]:
    """Load managed keys from all sources: os.environ, config .env, project .env.

    Priority: os.environ > ~/.config/fss-mini-rag/.env > project .env
    This ensures keys loaded by _load_env_keys at CLI startup are visible.
    """
    result = {}

    # 1. Check config .env file
    if ENV_FILE.exists():
        try:
            result.update(_parse_env_file(ENV_FILE))
        except Exception as e:
            logger.warning(f"Failed to read {ENV_FILE}: {e}")

    # 2. os.environ overrides file (highest priority — set by _load_env_keys at startup)
    for key in MANAGED_KEYS:
        val = os.environ.get(key)
        if val:
            result[key] = val

    return result


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a .env file, returning only MANAGED_KEYS."""
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in MANAGED_KEYS and value:
            result[key] = value
    return result


def save_env(keys: Dict[str, str]):
    """Update managed keys in .env, preserving comments and unmanaged lines.

    Creates the file and directory if they don't exist.
    Sets file permissions to 0600 (owner read/write only).
    """
    ENV_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing lines
    existing_lines = []
    if ENV_FILE.exists():
        existing_lines = ENV_FILE.read_text().splitlines()

    # Track which managed keys we've already updated
    updated = set()
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in MANAGED_KEYS:
                if key in keys and keys[key]:
                    new_lines.append(f"{key}={keys[key]}")
                    updated.add(key)
                # If key not in new dict or empty, skip it (delete)
                continue
        new_lines.append(line)

    # Append any new keys not yet in the file
    for key, value in keys.items():
        if key in MANAGED_KEYS and key not in updated and value:
            new_lines.append(f"{key}={value}")

    # Write
    try:
        ENV_FILE.write_text("\n".join(new_lines) + "\n")
        ENV_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        logger.info(f"Saved {len(keys)} key(s) to {ENV_FILE}")
    except Exception as e:
        logger.error(f"Failed to write {ENV_FILE}: {e}")

    # Sync to os.environ
    for key, value in keys.items():
        if key in MANAGED_KEYS:
            if value:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


def get_key(name: str) -> Optional[str]:
    """Get a key — checks os.environ first, then .env file."""
    value = os.environ.get(name)
    if value:
        return value
    env = load_env()
    return env.get(name)


def set_key(name: str, value: str):
    """Set a single key in .env and os.environ."""
    if name not in MANAGED_KEYS:
        logger.warning(f"Attempted to set unmanaged key: {name}")
        return
    env = load_env()
    env[name] = value
    save_env(env)


def delete_key(name: str):
    """Remove a key from .env and os.environ."""
    env = load_env()
    env.pop(name, None)
    save_env(env)
    os.environ.pop(name, None)


def mask_key(value: Optional[str]) -> str:
    """Mask a key for display: '••••xxxx' or '(not set)'."""
    if not value:
        return "(not set)"
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]

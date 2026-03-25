"""Persistent GUI configuration.

Stores collections, window geometry, endpoint settings, and presets
at ~/.config/fss-mini-rag/gui.json.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "fss-mini-rag"
CONFIG_FILE = CONFIG_DIR / "gui.json"


def get_default_working_dir() -> Path:
    """Get the default working directory for research data.

    Linux/Mac: ~/.local/share/fss-mini-rag/
    Windows:   %LOCALAPPDATA%/fss-mini-rag/
    """
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".local" / "share"
    return base / "fss-mini-rag"

PRESETS = {
    "lmstudio": {
        "name": "LM Studio (local)",
        "embedding_url": "http://localhost:1234/v1",
        "llm_url": "http://localhost:1234/v1",
        "needs_api_key": False,
        "cost_per_1m_input": 0.0,
        "cost_per_1m_output": 0.0,
    },
    "bobai": {
        "name": "BobAI Cloud",
        "embedding_url": "https://rtx3090.bobai.com.au/v1",
        "llm_url": "https://rtx3090.bobai.com.au/v1",
        "needs_api_key": True,
        "cost_per_1m_input": 0.0,
        "cost_per_1m_output": 0.0,
    },
    "custom-remote": {
        "name": "Custom Remote Server",
        "embedding_url": "https://your-server.example.com/v1",
        "llm_url": "https://your-server.example.com/v1",
        "needs_api_key": True,
        "cost_per_1m_input": 0.0,
        "cost_per_1m_output": 0.0,
    },
    "openai": {
        "name": "OpenAI",
        "embedding_url": "https://api.openai.com/v1",
        "llm_url": "https://api.openai.com/v1",
        "needs_api_key": True,
        "cost_per_1m_input": 2.50,
        "cost_per_1m_output": 10.00,
    },
    "openai-mini": {
        "name": "OpenAI (mini)",
        "embedding_url": "https://api.openai.com/v1",
        "llm_url": "https://api.openai.com/v1",
        "needs_api_key": True,
        "cost_per_1m_input": 0.15,
        "cost_per_1m_output": 0.60,
    },
}

DEFAULTS = {
    "collections": [],
    "last_active": None,
    "geometry": "1100x700",
    "preset": "lmstudio",
    "embedding_url": "http://localhost:1234/v1",
    "embedding_model": "auto",
    "embedding_profile": "precision",
    "llm_url": "http://localhost:1234/v1",
    "llm_model": "auto",
    "expand_queries": False,
    "theme": "dark",
    "custom_presets": {},
    "research_engine": "duckduckgo",
    "research_max_pages": 20,
    "research_project_path": None,  # deprecated — use working_dir
    "working_dir": None,  # set on first use via get_default_working_dir()
    "welcome_shown": False,
    "cost_per_1m_input": 0.0,
    "cost_per_1m_output": 0.0,
    "needs_api_key": False,
}


def load_config() -> Dict[str, Any]:
    """Load GUI config from disk."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            # Merge with defaults (new keys get defaults)
            config = {**DEFAULTS, **saved}
            return config
        except Exception as e:
            logger.warning(f"Failed to load GUI config: {e}")
    return dict(DEFAULTS)


def save_config(config: Dict[str, Any]):
    """Save GUI config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save GUI config: {e}")


def apply_preset(config: Dict[str, Any], preset_name: str) -> Dict[str, Any]:
    """Apply a preset to the config, including cost rates and key requirements."""
    if preset_name in PRESETS:
        preset = PRESETS[preset_name]
        config["preset"] = preset_name
        config["embedding_url"] = preset["embedding_url"]
        config["llm_url"] = preset["llm_url"]
        config["needs_api_key"] = preset.get("needs_api_key", False)
        config["cost_per_1m_input"] = preset.get("cost_per_1m_input", 0.0)
        config["cost_per_1m_output"] = preset.get("cost_per_1m_output", 0.0)
    elif preset_name in config.get("custom_presets", {}):
        preset = config["custom_presets"][preset_name]
        config["preset"] = preset_name
        config["embedding_url"] = preset.get("embedding_url", config["embedding_url"])
        config["llm_url"] = preset.get("llm_url", config["llm_url"])
        config["needs_api_key"] = preset.get("needs_api_key", False)
        config["cost_per_1m_input"] = preset.get("cost_per_1m_input", 0.0)
        config["cost_per_1m_output"] = preset.get("cost_per_1m_output", 0.0)
    return config


def get_collection_info(path_str: str) -> Dict[str, Any]:
    """Get info about an indexed collection from its manifest."""
    path = Path(path_str)
    manifest_path = path / ".mini-rag" / "manifest.json"
    if not manifest_path.exists():
        return {"indexed": False}
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        emb = manifest.get("embedding", {})
        return {
            "indexed": True,
            "chunks": manifest.get("chunk_count", 0),
            "files": manifest.get("file_count", 0),
            "model": emb.get("model", "unknown"),
            "indexed_at": manifest.get("indexed_at", "never"),
        }
    except Exception:
        return {"indexed": False}


def is_research_session(path_str: str) -> bool:
    """Check if a collection path is a web research session.

    Detects:
    - Direct session dir (has session.json)
    - Sources subdir of a session (parent has session.json)
    - Path under mini-research/ or web-research/ folders
    """
    p = Path(path_str)
    if (p / "session.json").exists():
        return True
    if (p.parent / "session.json").exists():
        return True
    research_markers = {"web-research", "mini-research"}
    if research_markers & set(p.parts):
        return True
    return False

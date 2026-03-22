"""Persistent GUI configuration.

Stores collections, window geometry, endpoint settings, and presets
at ~/.config/fss-mini-rag/gui.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "fss-mini-rag"
CONFIG_FILE = CONFIG_DIR / "gui.json"

PRESETS = {
    "lmstudio": {
        "name": "LM Studio",
        "embedding_url": "http://localhost:1234/v1",
        "llm_url": "http://localhost:1234/v1",
    },
    "bobai": {
        "name": "BobAI",
        "embedding_url": "http://localhost:11440/embed",
        "llm_url": "http://localhost:11433/v1",
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
    "custom_presets": {},
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
    """Apply a preset to the config."""
    if preset_name in PRESETS:
        preset = PRESETS[preset_name]
        config["preset"] = preset_name
        config["embedding_url"] = preset["embedding_url"]
        config["llm_url"] = preset["llm_url"]
    elif preset_name in config.get("custom_presets", {}):
        preset = config["custom_presets"][preset_name]
        config["preset"] = preset_name
        config["embedding_url"] = preset.get("embedding_url", config["embedding_url"])
        config["llm_url"] = preset.get("llm_url", config["llm_url"])
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

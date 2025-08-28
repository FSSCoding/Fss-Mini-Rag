"""
Smart language-aware chunking strategies for FSS-Mini-RAG.
Automatically adapts chunking based on file type and content patterns.
"""

from pathlib import Path
from typing import Any, Dict, List


class SmartChunkingStrategy:
    """Intelligent chunking that adapts to file types and content."""

    def __init__(self):
        self.language_configs = {
            "python": {
                "max_size": 3000,  # Larger for better function context
                "min_size": 200,
                "strategy": "function",
                "prefer_semantic": True,
            },
            "javascript": {
                "max_size": 2500,
                "min_size": 150,
                "strategy": "function",
                "prefer_semantic": True,
            },
            "markdown": {
                "max_size": 2500,
                "min_size": 300,  # Larger minimum for complete thoughts
                "strategy": "header",
                "preserve_structure": True,
            },
            "json": {
                "max_size": 1000,  # Smaller for config files
                "min_size": 50,
                "skip_if_large": True,  # Skip huge config JSONs
                "max_file_size": 50000,  # 50KB limit
            },
            "yaml": {"max_size": 1500, "min_size": 100, "strategy": "key_block"},
            "text": {"max_size": 2000, "min_size": 200, "strategy": "paragraph"},
            "bash": {"max_size": 1500, "min_size": 100, "strategy": "function"},
        }

        # Smart defaults for unknown languages
        self.default_config = {
            "max_size": 2000,
            "min_size": 150,
            "strategy": "semantic",
        }

    def get_config_for_language(self, language: str, file_size: int = 0) -> Dict[str, Any]:
        """Get optimal chunking config for a specific language."""
        config = self.language_configs.get(language, self.default_config).copy()

        # Smart adjustments based on file size
        if file_size > 0:
            if file_size < 500:  # Very small files
                config["max_size"] = max(config["max_size"] // 2, 200)
                config["min_size"] = 50
            elif file_size > 20000:  # Large files
                config["max_size"] = min(config["max_size"] + 1000, 4000)

        return config

    def should_skip_file(self, language: str, file_size: int) -> bool:
        """Determine if a file should be skipped entirely."""
        lang_config = self.language_configs.get(language, {})

        # Skip huge JSON config files
        if language == "json" and lang_config.get("skip_if_large"):
            max_size = lang_config.get("max_file_size", 50000)
            if file_size > max_size:
                return True

        # Skip tiny files that won't provide good context
        if file_size < 30:
            return True

        return False

    def get_smart_defaults(self, project_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart defaults based on project language distribution."""
        languages = project_stats.get("languages", {})
        # sum(languages.values())  # Unused variable removed

        # Determine primary language
        primary_lang = max(languages.items(), key=lambda x: x[1])[0] if languages else "python"
        primary_config = self.language_configs.get(primary_lang, self.default_config)

        # Smart streaming threshold based on large files
        large_files = project_stats.get("large_files", 0)
        streaming_threshold = 5120 if large_files > 5 else 1048576  # 5KB vs 1MB

        return {
            "chunking": {
                "max_size": primary_config["max_size"],
                "min_size": primary_config["min_size"],
                "strategy": primary_config.get("strategy", "semantic"),
                "language_specific": {
                    lang: config
                    for lang, config in self.language_configs.items()
                    if languages.get(lang, 0) > 0
                },
            },
            "streaming": {
                "enabled": True,
                "threshold_bytes": streaming_threshold,
                "chunk_size_kb": 64,
            },
            "files": {
                "skip_tiny_files": True,
                "tiny_threshold": 30,
                "smart_json_filtering": True,
            },
        }


# Example usage


def analyze_and_suggest(manifest_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze project and suggest optimal configuration."""
    from collections import Counter

    files = manifest_data.get("files", {})
    languages = Counter()
    large_files = 0

    for info in files.values():
        lang = info.get("language", "unknown")
        languages[lang] += 1
        if info.get("size", 0) > 10000:
            large_files += 1

    stats = {
        "languages": dict(languages),
        "large_files": large_files,
        "total_files": len(files),
    }

    strategy = SmartChunkingStrategy()
    return strategy.get_smart_defaults(stats)

"""
Auto-optimizer for FSS-Mini-RAG.
Automatically tunes settings based on usage patterns.
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AutoOptimizer:
    """Automatically optimizes RAG settings based on project patterns."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.rag_dir = project_path / ".mini-rag"
        self.config_path = self.rag_dir / "config.json"
        self.manifest_path = self.rag_dir / "manifest.json"

    def analyze_and_optimize(self) -> Dict[str, Any]:
        """Analyze current patterns and auto-optimize settings."""

        if not self.manifest_path.exists():
            return {"error": "No index found - run indexing first"}

        # Load current data
        with open(self.manifest_path) as f:
            manifest = json.load(f)

        # Analyze patterns
        analysis = self._analyze_patterns(manifest)

        # Generate optimizations
        optimizations = self._generate_optimizations(analysis)

        # Apply optimizations if beneficial
        if optimizations["confidence"] > 0.7:
            self._apply_optimizations(optimizations)
            return {
                "status": "optimized",
                "changes": optimizations["changes"],
                "expected_improvement": optimizations["expected_improvement"],
            }
        else:
            return {
                "status": "no_changes_needed",
                "analysis": analysis,
                "confidence": optimizations["confidence"],
            }

    def _analyze_patterns(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current indexing patterns."""
        files = manifest.get("files", {})

        # Language distribution
        languages = Counter()
        sizes = []
        chunk_ratios = []

        for filepath, info in files.items():
            lang = info.get("language", "unknown")
            languages[lang] += 1

            size = info.get("size", 0)
            chunks = info.get("chunks", 1)

            sizes.append(size)
            chunk_ratios.append(chunks / max(1, size / 1000))  # chunks per KB

        avg_chunk_ratio = sum(chunk_ratios) / len(chunk_ratios) if chunk_ratios else 1
        avg_size = sum(sizes) / len(sizes) if sizes else 1000

        return {
            "languages": dict(languages.most_common()),
            "total_files": len(files),
            "total_chunks": sum(info.get("chunks", 1) for info in files.values()),
            "avg_chunk_ratio": avg_chunk_ratio,
            "avg_file_size": avg_size,
            "large_files": sum(1 for s in sizes if s > 10000),
            "small_files": sum(1 for s in sizes if s < 500),
        }

    def _generate_optimizations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization recommendations."""
        changes = []
        confidence = 0.5
        expected_improvement = 0

        # Optimize chunking based on dominant language
        languages = analysis["languages"]
        if languages:
            dominant_lang, count = list(languages.items())[0]
            lang_pct = count / analysis["total_files"]

            if lang_pct > 0.3:  # Dominant language >30%
                if dominant_lang == "python" and analysis["avg_chunk_ratio"] < 1.5:
                    changes.append(
                        "Increase Python chunk size to 3000 for better function context"
                    )
                    confidence += 0.2
                    expected_improvement += 15

                elif dominant_lang == "markdown" and analysis["avg_chunk_ratio"] < 1.2:
                    changes.append("Use header-based chunking for Markdown files")
                    confidence += 0.15
                    expected_improvement += 10

        # Optimize for large files
        if analysis["large_files"] > 5:
            changes.append("Reduce streaming threshold to 5KB for better large file handling")
            confidence += 0.1
            expected_improvement += 8

        # Optimize chunk ratio
        if analysis["avg_chunk_ratio"] < 1.0:
            changes.append("Reduce chunk size for more granular search results")
            confidence += 0.15
            expected_improvement += 12
        elif analysis["avg_chunk_ratio"] > 3.0:
            changes.append("Increase chunk size to reduce overhead")
            confidence += 0.1
            expected_improvement += 5

        # Skip tiny files optimization
        small_file_pct = analysis["small_files"] / analysis["total_files"]
        if small_file_pct > 0.3:
            changes.append("Skip files smaller than 300 bytes to improve focus")
            confidence += 0.1
            expected_improvement += 3

        return {
            "changes": changes,
            "confidence": min(confidence, 1.0),
            "expected_improvement": expected_improvement,
        }

    def _apply_optimizations(self, optimizations: Dict[str, Any]):
        """Apply the recommended optimizations."""

        # Load existing config or create default
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = json.load(f)
        else:
            config = self._get_default_config()

        changes = optimizations["changes"]

        # Apply changes based on recommendations
        for change in changes:
            if "Python chunk size to 3000" in change:
                config.setdefault("chunking", {})["max_size"] = 3000

            elif "header-based chunking" in change:
                config.setdefault("chunking", {})["strategy"] = "header"

            elif "streaming threshold to 5KB" in change:
                config.setdefault("streaming", {})["threshold_bytes"] = 5120

            elif "Reduce chunk size" in change:
                current_size = config.get("chunking", {}).get("max_size", 2000)
                config.setdefault("chunking", {})["max_size"] = max(1500, current_size - 500)

            elif "Increase chunk size" in change:
                current_size = config.get("chunking", {}).get("max_size", 2000)
                config.setdefault("chunking", {})["max_size"] = min(4000, current_size + 500)

            elif "Skip files smaller" in change:
                config.setdefault("files", {})["min_file_size"] = 300

        # Save optimized config
        config["_auto_optimized"] = True
        config["_optimization_timestamp"] = json.dumps(None, default=str)

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Applied {len(changes)} optimizations to {self.config_path}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "chunking": {"max_size": 2000, "min_size": 150, "strategy": "semantic"},
            "streaming": {"enabled": True, "threshold_bytes": 1048576},
            "files": {"min_file_size": 50},
        }

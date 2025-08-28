"""
Configuration management for FSS-Mini-RAG.
Handles loading, saving, and validation of YAML config files.
"""

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    max_size: int = 2000
    min_size: int = 150
    strategy: str = "semantic"  # "semantic" or "fixed"


@dataclass
class StreamingConfig:
    """Configuration for large file streaming."""

    enabled: bool = True
    threshold_bytes: int = 1048576  # 1MB


@dataclass
class FilesConfig:
    """Configuration for file processing."""

    min_file_size: int = 50
    exclude_patterns: list = None
    include_patterns: list = None

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "node_modules/**",
                ".git/**",
                "__pycache__/**",
                "*.pyc",
                ".venv/**",
                "venv/**",
                "build/**",
                "dist/**",
            ]
        if self.include_patterns is None:
            self.include_patterns = ["**/*"]  # Include everything by default


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    preferred_method: str = "ollama"  # "ollama", "ml", "hash", "auto"
    ollama_model: str = "nomic-embed-text"
    ollama_host: str = "localhost:11434"
    ml_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32


@dataclass
class SearchConfig:
    """Configuration for search behavior."""

    default_top_k: int = 10
    enable_bm25: bool = True
    similarity_threshold: float = 0.1
    expand_queries: bool = False  # Enable automatic query expansion


@dataclass
class LLMConfig:
    """Configuration for LLM synthesis and query expansion."""

    # Core settings
    synthesis_model: str = "auto"  # "auto", "qwen3:1.7b", "qwen2.5:1.5b", etc.
    expansion_model: str = "auto"  # Usually same as synthesis_model
    max_expansion_terms: int = 8  # Maximum additional terms to add
    enable_synthesis: bool = False  # Enable by default when --synthesize used
    synthesis_temperature: float = 0.3
    enable_thinking: bool = True  # Enable thinking mode for Qwen3 models
    cpu_optimized: bool = True  # Prefer lightweight models

    # Context window configuration (critical for RAG performance)
    context_window: int = 16384  # Context window size in tokens (16K recommended)
    auto_context: bool = True  # Auto-adjust context based on model capabilities

    # Model preference rankings (configurable)
    model_rankings: list = None  # Will be set in __post_init__

    # Provider-specific settings (for different LLM providers)
    provider: str = "ollama"  # "ollama", "openai", "anthropic"
    ollama_host: str = "localhost:11434"  # Ollama connection
    api_key: Optional[str] = None  # API key for cloud providers
    api_base: Optional[str] = None  # Base URL for API (e.g., OpenRouter)
    timeout: int = 20  # Request timeout in seconds

    def __post_init__(self):
        if self.model_rankings is None:
            # Default model preference rankings (can be overridden in config file)
            self.model_rankings = [
                # Testing model (prioritized for current testing phase)
                "qwen3:1.7b",
                # Ultra-efficient models (perfect for CPU-only systems)
                "qwen3:0.6b",
                # Recommended model (excellent quality but larger)
                "qwen3:4b",
                # Common fallbacks (prioritize Qwen models)
                "qwen2.5:1.5b",
                "qwen2.5:3b",
            ]


@dataclass
class UpdateConfig:
    """Configuration for auto-update system."""

    auto_check: bool = True  # Check for updates automatically
    check_frequency_hours: int = 24  # How often to check (hours)
    auto_install: bool = False  # Auto-install without asking (not recommended)
    backup_before_update: bool = True  # Create backup before updating
    notify_beta_releases: bool = False  # Include beta/pre-releases


@dataclass
class RAGConfig:
    """Main RAG system configuration."""

    chunking: ChunkingConfig = None
    streaming: StreamingConfig = None
    files: FilesConfig = None
    embedding: EmbeddingConfig = None
    search: SearchConfig = None
    llm: LLMConfig = None
    updates: UpdateConfig = None

    def __post_init__(self):
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.streaming is None:
            self.streaming = StreamingConfig()
        if self.files is None:
            self.files = FilesConfig()
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.search is None:
            self.search = SearchConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.updates is None:
            self.updates = UpdateConfig()


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.rag_dir = self.project_path / ".mini-rag"
        self.config_path = self.rag_dir / "config.yaml"

    def load_config(self) -> RAGConfig:
        """Load configuration from YAML file or create default."""
        if not self.config_path.exists():
            logger.info(f"No config found at {self.config_path}, creating default")
            config = RAGConfig()
            self.save_config(config)
            return config

        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning("Empty config file, using defaults")
                return RAGConfig()

            # Convert nested dicts back to dataclass instances
            config = RAGConfig()

            if "chunking" in data:
                config.chunking = ChunkingConfig(**data["chunking"])
            if "streaming" in data:
                config.streaming = StreamingConfig(**data["streaming"])
            if "files" in data:
                config.files = FilesConfig(**data["files"])
            if "embedding" in data:
                config.embedding = EmbeddingConfig(**data["embedding"])
            if "search" in data:
                config.search = SearchConfig(**data["search"])
            if "llm" in data:
                config.llm = LLMConfig(**data["llm"])

            return config

        except yaml.YAMLError as e:
            # YAML syntax error - help user fix it instead of silent fallback
            error_msg = (
                f"⚠️ Config file has YAML syntax error at line "
                f"{getattr(e, 'problem_mark', 'unknown')}: {e}"
            )
            logger.error(error_msg)
            print(f"\n{error_msg}")
            print(f"Config file: {self.config_path}")
            print("💡 Check YAML syntax (indentation, quotes, colons)")
            print("💡 Or delete config file to reset to defaults")
            return RAGConfig()  # Still return defaults but warn user

        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            logger.info("Using default configuration")
            return RAGConfig()

    def save_config(self, config: RAGConfig):
        """Save configuration to YAML file with comments."""
        try:
            self.rag_dir.mkdir(exist_ok=True)

            # Convert to dict for YAML serialization
            config_dict = asdict(config)

            # Create YAML content with comments
            yaml_content = self._create_yaml_with_comments(config_dict)

            # Write with basic file locking to prevent corruption
            with open(self.config_path, "w") as f:
                try:
                    import fcntl

                    fcntl.flock(
                        f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )  # Non-blocking exclusive lock
                    f.write(yaml_content)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
                except (OSError, ImportError):
                    # Fallback for Windows or if fcntl unavailable
                    f.write(yaml_content)

            logger.info(f"Configuration saved to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def _create_yaml_with_comments(self, config_dict: Dict[str, Any]) -> str:
        """Create YAML content with helpful comments."""
        yaml_lines = [
            "# FSS-Mini-RAG Configuration",
            "# Edit this file to customize indexing and search behavior",
            "# See docs/GETTING_STARTED.md for detailed explanations",
            "",
            "# Text chunking settings",
            "chunking:",
            f"  max_size: {config_dict['chunking']['max_size']}  # Max chars per chunk",
            f"  min_size: {config_dict['chunking']['min_size']}  # Min chars per chunk",
            f"  strategy: {config_dict['chunking']['strategy']}  # 'semantic' or 'fixed'",
            "",
            "# Large file streaming settings",
            "streaming:",
            f"  enabled: {str(config_dict['streaming']['enabled']).lower()}",
            f"  threshold_bytes: {config_dict['streaming']['threshold_bytes']}  # Stream files >1MB",
            "",
            "# File processing settings",
            "files:",
            f"  min_file_size: {config_dict['files']['min_file_size']}  # Skip small files",
            "  exclude_patterns:",
        ]

        for pattern in config_dict["files"]["exclude_patterns"]:
            yaml_lines.append(f'    - "{pattern}"')

        yaml_lines.extend(
            [
                "  include_patterns:",
                '    - "**/*"                  # Include all files by default',
                "",
                "# Embedding generation settings",
                "embedding:",
                f"  preferred_method: {config_dict['embedding']['preferred_method']}  # Method",
                f"  ollama_model: {config_dict['embedding']['ollama_model']}",
                f"  ollama_host: {config_dict['embedding']['ollama_host']}",
                f"  ml_model: {config_dict['embedding']['ml_model']}",
                f"  batch_size: {config_dict['embedding']['batch_size']}  # Per batch",
                "",
                "# Search behavior settings",
                "search:",
                f"  default_top_k: {config_dict['search']['default_top_k']}  # Top results",
                f"  enable_bm25: {str(config_dict['search']['enable_bm25']).lower()}  # Keyword boost",
                f"  similarity_threshold: {config_dict['search']['similarity_threshold']}  # Min score",
                f"  expand_queries: {str(config_dict['search']['expand_queries']).lower()}  # Auto expand",
                "",
                "# LLM synthesis and query expansion settings",
                "llm:",
                f"  ollama_host: {config_dict['llm']['ollama_host']}",
                f"  synthesis_model: {config_dict['llm']['synthesis_model']}  # Model name",
                f"  expansion_model: {config_dict['llm']['expansion_model']}  # Model name",
                f"  max_expansion_terms: {config_dict['llm']['max_expansion_terms']}  # Max terms",
                f"  enable_synthesis: {str(config_dict['llm']['enable_synthesis']).lower()}       # Enable synthesis by default",
                f"  synthesis_temperature: {config_dict['llm']['synthesis_temperature']}      # LLM temperature for analysis",
                "",
                "  # Context window configuration (critical for RAG performance)",
                "  # 💡 Sizing guide: 2K=1 question, 4K=1-2 questions, 8K=manageable, 16K=most users",
                "  #               32K=large codebases, 64K+=power users only",
                "  # ⚠️  Larger contexts use exponentially more CPU/memory - only increase if needed",
                "  # 🔧 Low context limits? Try smaller topk, better search terms, or archive noise",
                f"  context_window: {config_dict['llm']['context_window']}           # Context size in tokens",
                f"  auto_context: {str(config_dict['llm']['auto_context']).lower()}            # Auto-adjust context based on model capabilities",
                "",
                "  model_rankings:          # Preferred model order (edit to change priority)",
            ]
        )

        # Add model rankings list
        if "model_rankings" in config_dict["llm"] and config_dict["llm"]["model_rankings"]:
            for model in config_dict["llm"]["model_rankings"][:10]:  # Show first 10
                yaml_lines.append(f'    - "{model}"')
            if len(config_dict["llm"]["model_rankings"]) > 10:
                yaml_lines.append("    # ... (edit config to see all options)")

        # Add update settings
        yaml_lines.extend(
            [
                "",
                "# Auto-update system settings",
                "updates:",
                f"  auto_check: {str(config_dict['updates']['auto_check']).lower()}            # Check for updates automatically",
                f"  check_frequency_hours: {config_dict['updates']['check_frequency_hours']}    # Hours between update checks",
                f"  auto_install: {str(config_dict['updates']['auto_install']).lower()}          # Auto-install updates (not recommended)",
                f"  backup_before_update: {str(config_dict['updates']['backup_before_update']).lower()}   # Create backup before updating",
                f"  notify_beta_releases: {str(config_dict['updates']['notify_beta_releases']).lower()}   # Include beta releases in checks",
            ]
        )

        return "\n".join(yaml_lines)

    def update_config(self, **kwargs) -> RAGConfig:
        """Update specific configuration values."""
        config = self.load_config()

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"Unknown config key: {key}")

        self.save_config(config)
        return config

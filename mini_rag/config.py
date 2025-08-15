"""
Configuration management for FSS-Mini-RAG.
Handles loading, saving, and validation of YAML config files.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

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
                "dist/**"
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
    max_expansion_terms: int = 8   # Maximum additional terms to add
    enable_synthesis: bool = False # Enable by default when --synthesize used
    synthesis_temperature: float = 0.3
    enable_thinking: bool = True  # Enable thinking mode for Qwen3 models
    cpu_optimized: bool = True     # Prefer lightweight models
    
    # Context window configuration (critical for RAG performance)
    context_window: int = 16384    # Context window size in tokens (16K recommended)
    auto_context: bool = True      # Auto-adjust context based on model capabilities
    
    # Model preference rankings (configurable)
    model_rankings: list = None    # Will be set in __post_init__
    
    # Provider-specific settings (for different LLM providers)
    provider: str = "ollama"       # "ollama", "openai", "anthropic"
    ollama_host: str = "localhost:11434"  # Ollama connection
    api_key: Optional[str] = None  # API key for cloud providers
    api_base: Optional[str] = None # Base URL for API (e.g., OpenRouter)
    timeout: int = 20              # Request timeout in seconds
    
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
class RAGConfig:
    """Main RAG system configuration."""
    chunking: ChunkingConfig = None
    streaming: StreamingConfig = None  
    files: FilesConfig = None
    embedding: EmbeddingConfig = None
    search: SearchConfig = None
    llm: LLMConfig = None
    
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


class ConfigManager:
    """Manages configuration loading, saving, and validation."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.rag_dir = self.project_path / '.mini-rag'
        self.config_path = self.rag_dir / 'config.yaml'
        
    def load_config(self) -> RAGConfig:
        """Load configuration from YAML file or create default."""
        if not self.config_path.exists():
            logger.info(f"No config found at {self.config_path}, creating default")
            config = RAGConfig()
            self.save_config(config)
            return config
            
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                
            if not data:
                logger.warning("Empty config file, using defaults")
                return RAGConfig()
                
            # Convert nested dicts back to dataclass instances
            config = RAGConfig()
            
            if 'chunking' in data:
                config.chunking = ChunkingConfig(**data['chunking'])
            if 'streaming' in data:
                config.streaming = StreamingConfig(**data['streaming'])
            if 'files' in data:
                config.files = FilesConfig(**data['files'])
            if 'embedding' in data:
                config.embedding = EmbeddingConfig(**data['embedding'])
            if 'search' in data:
                config.search = SearchConfig(**data['search'])
            if 'llm' in data:
                config.llm = LLMConfig(**data['llm'])
                
            return config
            
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
            
            with open(self.config_path, 'w') as f:
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
            f"  max_size: {config_dict['chunking']['max_size']}      # Maximum characters per chunk",
            f"  min_size: {config_dict['chunking']['min_size']}       # Minimum characters per chunk", 
            f"  strategy: {config_dict['chunking']['strategy']}    # 'semantic' (language-aware) or 'fixed'",
            "",
            "# Large file streaming settings", 
            "streaming:",
            f"  enabled: {str(config_dict['streaming']['enabled']).lower()}",
            f"  threshold_bytes: {config_dict['streaming']['threshold_bytes']}  # Files larger than this use streaming (1MB)",
            "",
            "# File processing settings",
            "files:",
            f"  min_file_size: {config_dict['files']['min_file_size']}        # Skip files smaller than this",
            "  exclude_patterns:",
        ]
        
        for pattern in config_dict['files']['exclude_patterns']:
            yaml_lines.append(f"    - \"{pattern}\"")
        
        yaml_lines.extend([
            "  include_patterns:",
            "    - \"**/*\"                  # Include all files by default",
            "",
            "# Embedding generation settings",
            "embedding:",
            f"  preferred_method: {config_dict['embedding']['preferred_method']}     # 'ollama', 'ml', 'hash', or 'auto'",
            f"  ollama_model: {config_dict['embedding']['ollama_model']}",
            f"  ollama_host: {config_dict['embedding']['ollama_host']}",
            f"  ml_model: {config_dict['embedding']['ml_model']}",
            f"  batch_size: {config_dict['embedding']['batch_size']}               # Embeddings processed per batch",
            "",
            "# Search behavior settings", 
            "search:",
            f"  default_top_k: {config_dict['search']['default_top_k']}           # Default number of top results",
            f"  enable_bm25: {str(config_dict['search']['enable_bm25']).lower()}             # Enable keyword matching boost",
            f"  similarity_threshold: {config_dict['search']['similarity_threshold']}        # Minimum similarity score",
            f"  expand_queries: {str(config_dict['search']['expand_queries']).lower()}          # Enable automatic query expansion",
            "",
            "# LLM synthesis and query expansion settings",
            "llm:",
            f"  ollama_host: {config_dict['llm']['ollama_host']}",
            f"  synthesis_model: {config_dict['llm']['synthesis_model']}    # 'auto', 'qwen3:1.7b', etc.",
            f"  expansion_model: {config_dict['llm']['expansion_model']}     # Usually same as synthesis_model",
            f"  max_expansion_terms: {config_dict['llm']['max_expansion_terms']}        # Maximum terms to add to queries",
            f"  enable_synthesis: {str(config_dict['llm']['enable_synthesis']).lower()}       # Enable synthesis by default",
            f"  synthesis_temperature: {config_dict['llm']['synthesis_temperature']}      # LLM temperature for analysis",
            "",
            "  # Context window configuration (critical for RAG performance)",
            f"  context_window: {config_dict['llm']['context_window']}           # Context size in tokens (8K=fast, 16K=balanced, 32K=advanced)",
            f"  auto_context: {str(config_dict['llm']['auto_context']).lower()}            # Auto-adjust context based on model capabilities",
            "",
            "  model_rankings:          # Preferred model order (edit to change priority)",
        ])
        
        # Add model rankings list
        if 'model_rankings' in config_dict['llm'] and config_dict['llm']['model_rankings']:
            for model in config_dict['llm']['model_rankings'][:10]:  # Show first 10
                yaml_lines.append(f"    - \"{model}\"")
            if len(config_dict['llm']['model_rankings']) > 10:
                yaml_lines.append("    # ... (edit config to see all options)")
        
        return '\n'.join(yaml_lines)
    
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
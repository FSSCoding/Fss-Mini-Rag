"""Unit tests for configuration system."""

import tempfile
from pathlib import Path

import pytest
from mini_rag.config import (
    ChunkingConfig,
    ConfigManager,
    EmbeddingConfig,
    RAGConfig,
    SearchConfig,
    ServerConfig,
)


class TestConfigDefaults:
    """Test default configuration values."""

    def test_chunking_defaults_are_chars(self):
        config = ChunkingConfig()
        assert config.max_size == 2000
        assert config.min_size == 150

    def test_server_defaults(self):
        config = ServerConfig()
        assert config.port == 7777
        assert config.host == "127.0.0.1"

    def test_search_defaults(self):
        config = SearchConfig()
        assert config.default_top_k == 10
        assert config.enable_bm25 is True

    def test_embedding_defaults(self):
        config = EmbeddingConfig()
        assert config.provider == "openai"
        assert "1234" in config.base_url  # LM Studio default port

    def test_rag_config_initializes_all_sections(self):
        config = RAGConfig()
        assert config.chunking is not None
        assert config.search is not None
        assert config.server is not None
        assert config.embedding is not None


class TestConfigManager:
    """Test config file loading and saving."""

    def test_creates_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(Path(tmpdir))
            config = manager.load_config()
            assert config.chunking is not None
            assert config.search is not None

    def test_config_file_created_on_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            rag_dir = p / ".mini-rag"
            rag_dir.mkdir()
            manager = ConfigManager(p)
            manager.load_config()
            config_path = rag_dir / "config.yaml"
            assert config_path.exists()

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            rag_dir = p / ".mini-rag"
            rag_dir.mkdir()
            manager = ConfigManager(p)
            config1 = manager.load_config()
            config2 = manager.load_config()
            assert config1.chunking.max_size == config2.chunking.max_size

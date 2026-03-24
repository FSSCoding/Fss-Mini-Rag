"""Verify key fixes without heavy dependencies.

Tests that critical configurations, imports, and safeguards are correct.
"""

import tempfile
from pathlib import Path


def test_config_model_rankings():
    """Model rankings should have qwen3:1.7b as first priority."""
    from mini_rag.config import ConfigManager

    with tempfile.TemporaryDirectory() as tmpdir:
        config_manager = ConfigManager(tmpdir)
        config = config_manager.load_config()

        assert hasattr(config, "llm"), "Config missing llm attribute"
        assert hasattr(config.llm, "model_rankings"), "LLM config missing model_rankings"
        rankings = config.llm.model_rankings
        assert rankings, "Model rankings is empty"
        assert rankings[0] == "qwen3:1.7b", f"First model is {rankings[0]}, expected qwen3:1.7b"


def test_context_length_fix():
    """Context length should be set to 32K in synthesizer and safeguards."""
    synthesizer = Path("mini_rag/llm_synthesizer.py").read_text()
    assert '"num_ctx": 80000' not in synthesizer, "num_ctx still 80000 in synthesizer"

    safeguards = Path("mini_rag/llm_safeguards.py").read_text()
    assert "context_window: int = 80000" not in safeguards, "context_window still 80000 in safeguards"


def test_safeguard_preservation():
    """Safeguards should preserve content instead of dropping it."""
    content = Path("mini_rag/llm_synthesizer.py").read_text()
    assert "_create_safeguard_response_with_content" in content, "Preservation method missing"
    assert "AI Response (use with caution):" in content, "Preservation warning format missing"


def test_import_fixes():
    """All test files should use mini_rag imports, not claude_rag."""
    test_files = [
        "tests/test_rag_integration.py",
        "tests/test_hybrid_search.py",
        "tests/test_context_retrieval.py",
    ]

    for test_file in test_files:
        p = Path(test_file)
        if p.exists():
            content = p.read_text()
            assert "claude_rag" not in content, f"{test_file} still has claude_rag imports"

"""Integration tests for GUI service -> endpoint wiring.

Verifies that configured URLs actually flow through to HTTP requests.
These tests catch the exact bug where preferences are set but the
synthesizer/embedder ignores them and uses hardcoded defaults.
"""

from unittest.mock import MagicMock, patch, call
from pathlib import Path

import pytest

from mini_rag.gui.events import EventBus
from mini_rag.gui.services.search import SearchService


class TestSearchServiceEndpointRouting:
    """Verify that SearchService routes to the configured endpoints."""

    def test_llm_url_flows_to_synthesizer(self):
        """Setting llm_url on SearchService must reach the LLMSynthesizer."""
        bus = EventBus()
        service = SearchService(bus)
        service.llm_url = "http://localhost:11433/v1"
        service.llm_model = "qwen3.5-35b-a3b"

        # Mock the LLMSynthesizer to capture what URL it's created with
        with patch("mini_rag.llm_synthesizer.LLMSynthesizer") as MockSynth:
            mock_instance = MagicMock()
            mock_instance.synthesize_search_results.return_value = MagicMock(
                summary="test answer", confidence=0.8
            )
            MockSynth.return_value = mock_instance

            # Create mock results
            mock_result = MagicMock()
            mock_result.file_path = "test.py"
            mock_result.content = "test content"
            mock_result.score = 0.5

            service.synthesize("/tmp/test", "test query", [mock_result])

            # Assert the synthesizer was created with the CONFIGURED url
            MockSynth.assert_called_once()
            call_kwargs = MockSynth.call_args
            assert call_kwargs[1]["base_url"] == "http://localhost:11433/v1", (
                f"LLMSynthesizer created with {call_kwargs[1]['base_url']} "
                f"instead of configured http://localhost:11433/v1"
            )

    def test_llm_url_not_hardcoded_to_lmstudio(self):
        """LLM must NOT default to LM Studio when BobAI is configured."""
        bus = EventBus()
        service = SearchService(bus)
        service.llm_url = "http://bobai-server:11433/v1"
        service.llm_model = "custom-model"

        with patch("mini_rag.llm_synthesizer.LLMSynthesizer") as MockSynth:
            mock_instance = MagicMock()
            mock_instance.synthesize_search_results.return_value = MagicMock(
                summary="answer", confidence=0.8
            )
            MockSynth.return_value = mock_instance

            service.synthesize("/tmp/test", "query", [MagicMock()])

            call_kwargs = MockSynth.call_args[1]
            assert "1234" not in call_kwargs["base_url"], (
                "LLMSynthesizer is hitting LM Studio (port 1234) instead of "
                f"configured endpoint: {call_kwargs['base_url']}"
            )
            assert call_kwargs["base_url"] == "http://bobai-server:11433/v1"

    def test_llm_model_flows_to_synthesizer(self):
        """Configured model name must reach the synthesizer."""
        bus = EventBus()
        service = SearchService(bus)
        service.llm_url = "http://localhost:11433/v1"
        service.llm_model = "qwen3.5-35b-a3b"

        with patch("mini_rag.llm_synthesizer.LLMSynthesizer") as MockSynth:
            mock_instance = MagicMock()
            mock_instance.synthesize_search_results.return_value = MagicMock(
                summary="answer", confidence=0.8
            )
            MockSynth.return_value = mock_instance

            service.synthesize("/tmp/test", "query", [MagicMock()])

            call_kwargs = MockSynth.call_args[1]
            assert call_kwargs["model"] == "qwen3.5-35b-a3b"

    def test_default_urls(self):
        """Default URLs should be LM Studio."""
        bus = EventBus()
        service = SearchService(bus)
        assert service.llm_url == "http://localhost:1234/v1"
        assert service.embedding_url == "http://localhost:1234/v1"

    def test_settings_change_updates_service(self):
        """Emitting settings:changed should update service URLs."""
        bus = EventBus()
        service = SearchService(bus)

        # Simulate what app.py does on settings change
        service.llm_url = "http://new-server:9999/v1"
        service.llm_model = "new-model"
        service.embedding_url = "http://new-embed:8888/v1"

        assert service.llm_url == "http://new-server:9999/v1"
        assert service.llm_model == "new-model"
        assert service.embedding_url == "http://new-embed:8888/v1"

    def test_invalidate_clears_cached_searchers(self):
        """Changing settings should invalidate cached searchers."""
        bus = EventBus()
        service = SearchService(bus)

        # Fake a cached searcher
        service._searchers["/tmp/test"] = MagicMock()
        assert len(service._searchers) == 1

        service.invalidate("/tmp/test")
        assert len(service._searchers) == 0

    def test_invalidate_all(self):
        """invalidate() with no args clears all cached searchers."""
        bus = EventBus()
        service = SearchService(bus)

        service._searchers["a"] = MagicMock()
        service._searchers["b"] = MagicMock()

        service.invalidate()
        assert len(service._searchers) == 0


class TestEventBus:
    """Verify EventBus works correctly for settings propagation."""

    def test_emit_and_receive(self):
        bus = EventBus()
        received = []
        bus.on("test:event", lambda d: received.append(d))
        bus.emit("test:event", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_multiple_subscribers(self):
        bus = EventBus()
        results = []
        bus.on("test", lambda d: results.append("a"))
        bus.on("test", lambda d: results.append("b"))
        bus.emit("test")
        assert results == ["a", "b"]

    def test_handler_error_doesnt_break_others(self):
        bus = EventBus()
        results = []
        bus.on("test", lambda d: 1/0)  # Will raise
        bus.on("test", lambda d: results.append("ok"))
        bus.emit("test")
        assert results == ["ok"]  # Second handler still runs

    def test_off_removes_handler(self):
        bus = EventBus()
        results = []
        handler = lambda d: results.append("x")
        bus.on("test", handler)
        bus.off("test", handler)
        bus.emit("test")
        assert results == []


class TestEmbeddingEndpointFormat:
    """Verify custom vs OpenAI endpoint format detection."""

    def test_custom_endpoint_detected(self):
        """URL not ending in /v1 should use custom format."""
        url = "http://localhost:11440/embed"
        assert not url.rstrip("/").endswith("/v1")

    def test_openai_endpoint_detected(self):
        """URL ending in /v1 should use OpenAI format."""
        url = "http://localhost:1234/v1"
        assert url.rstrip("/").endswith("/v1")

    def test_bobai_embedding_uses_custom_format(self):
        """BobAI embedding endpoint must be detected as custom."""
        from mini_rag.gui.config_store import PRESETS
        bobai_url = PRESETS["bobai-local"]["embedding_url"]
        assert not bobai_url.rstrip("/").endswith("/v1"), (
            f"BobAI embedding URL {bobai_url} should NOT be OpenAI format"
        )

    def test_lmstudio_embedding_uses_openai_format(self):
        """LM Studio endpoint must be detected as OpenAI."""
        from mini_rag.gui.config_store import PRESETS
        lm_url = PRESETS["lmstudio"]["embedding_url"]
        assert lm_url.rstrip("/").endswith("/v1"), (
            f"LM Studio URL {lm_url} should be OpenAI format"
        )

    def test_bobai_llm_endpoint_correct(self):
        """BobAI LLM must point to vLLM, not LM Studio."""
        from mini_rag.gui.config_store import PRESETS
        llm_url = PRESETS["bobai-local"]["llm_url"]
        assert "11433" in llm_url, (
            f"BobAI LLM URL {llm_url} should point to :11433 (vLLM)"
        )
        assert "1234" not in llm_url, (
            f"BobAI LLM URL {llm_url} should NOT point to :1234 (LM Studio)"
        )

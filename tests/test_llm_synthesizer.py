"""Tests for LLM synthesizer integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mini_rag.llm_synthesizer import LLMSynthesizer, SynthesisResult


class TestSynthesizerInit:
    """Test synthesizer initialization and provider detection."""

    def test_default_init(self):
        """Synthesizer should initialize without errors."""
        synth = LLMSynthesizer()
        assert synth.base_url == "http://localhost:1234/v1"
        assert synth.ollama_url == "http://localhost:11434"
        assert synth.provider == "auto"

    def test_explicit_openai_provider(self):
        synth = LLMSynthesizer(provider="openai", base_url="http://localhost:1234/v1")
        assert synth.provider == "openai"

    def test_explicit_ollama_provider(self):
        synth = LLMSynthesizer(provider="ollama", ollama_url="http://localhost:11434")
        assert synth.provider == "ollama"

    def test_custom_model(self):
        synth = LLMSynthesizer(model="qwen3:1.7b")
        assert synth.model == "qwen3:1.7b"

    def test_api_key_stored(self):
        synth = LLMSynthesizer(api_key="test-key-123")
        assert synth.api_key == "test-key-123"


class TestSynthesisResult:
    """Test the SynthesisResult dataclass."""

    def test_create_result(self):
        result = SynthesisResult(
            summary="Test summary",
            key_points=["point 1", "point 2"],
            code_examples=["example 1"],
            suggested_actions=["action 1"],
            confidence=0.85,
        )
        assert result.summary == "Test summary"
        assert len(result.key_points) == 2
        assert result.confidence == 0.85

    def test_empty_result(self):
        result = SynthesisResult(
            summary="",
            key_points=[],
            code_examples=[],
            suggested_actions=[],
            confidence=0.0,
        )
        assert result.confidence == 0.0


class TestOpenAICompatibleCall:
    """Test the OpenAI-compatible LLM call path."""

    @patch("mini_rag.llm_synthesizer.requests.post")
    def test_call_openai_compatible_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        synth = LLMSynthesizer(provider="openai", model="test-model")
        result = synth._call_openai_compatible("test prompt")
        assert result == "Test response"

        # Verify correct API call
        call_args = mock_post.call_args
        assert "/chat/completions" in call_args[0][0]
        assert call_args[1]["json"]["model"] == "test-model"
        assert call_args[1]["json"]["messages"][0]["content"] == "test prompt"

    @patch("mini_rag.llm_synthesizer.requests.post")
    def test_call_openai_compatible_with_api_key(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_post.return_value = mock_response

        synth = LLMSynthesizer(provider="openai", model="m", api_key="sk-test")
        synth._call_openai_compatible("prompt")

        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-test"

    @patch("mini_rag.llm_synthesizer.requests.post")
    def test_call_openai_compatible_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        synth = LLMSynthesizer(provider="openai", model="test")
        result = synth._call_openai_compatible("prompt")
        assert result is None


class TestCallLLMRouting:
    """Test that _call_llm routes to the correct provider."""

    @patch.object(LLMSynthesizer, "_call_openai_compatible")
    @patch.object(LLMSynthesizer, "_ensure_initialized")
    def test_routes_to_openai(self, mock_init, mock_openai):
        mock_openai.return_value = "openai response"
        synth = LLMSynthesizer()
        synth._active_provider = "openai"
        synth._initialized = True

        result = synth._call_llm("test")
        mock_openai.assert_called_once_with("test", 0.3)
        assert result == "openai response"

    @patch.object(LLMSynthesizer, "_call_ollama")
    @patch.object(LLMSynthesizer, "_ensure_initialized")
    def test_routes_to_ollama(self, mock_init, mock_ollama):
        mock_ollama.return_value = "ollama response"
        synth = LLMSynthesizer()
        synth._active_provider = "ollama"
        synth._initialized = True

        result = synth._call_llm("test")
        mock_ollama.assert_called_once_with("test", 0.3)
        assert result == "ollama response"


class TestSynthesizeSearchResults:
    """Test the full synthesis pipeline."""

    @patch.object(LLMSynthesizer, "_call_llm")
    @patch.object(LLMSynthesizer, "is_available", return_value=True)
    @patch.object(LLMSynthesizer, "_ensure_initialized")
    def test_synthesize_returns_result(self, mock_init, mock_avail, mock_call):
        mock_call.return_value = "The search results show that RRF fusion works by combining ranks."

        synth = LLMSynthesizer()
        synth._initialized = True

        # Create mock search results
        mock_results = []
        for i in range(3):
            r = MagicMock()
            r.file_path = f"file_{i}.py"
            r.content = f"content {i}"
            r.score = 0.8 - i * 0.1
            mock_results.append(r)

        result = synth.synthesize_search_results(
            "how does RRF work", mock_results, Path("/tmp/test")
        )

        assert isinstance(result, SynthesisResult)
        assert "RRF" in result.summary
        assert result.confidence > 0

    @patch.object(LLMSynthesizer, "is_available", return_value=False)
    @patch.object(LLMSynthesizer, "_ensure_initialized")
    def test_synthesize_unavailable(self, mock_init, mock_avail):
        synth = LLMSynthesizer()
        synth._initialized = True

        result = synth.synthesize_search_results("query", [], Path("/tmp"))
        assert "unavailable" in result.summary.lower()
        assert result.confidence == 0.0

    @patch.object(LLMSynthesizer, "_call_llm", return_value=None)
    @patch.object(LLMSynthesizer, "is_available", return_value=True)
    @patch.object(LLMSynthesizer, "_ensure_initialized")
    def test_synthesize_llm_failure(self, mock_init, mock_avail, mock_call):
        synth = LLMSynthesizer()
        synth._initialized = True

        r = MagicMock()
        r.file_path = "test.py"
        r.content = "test content"
        r.score = 0.5

        result = synth.synthesize_search_results("query", [r], Path("/tmp"))
        assert "failed" in result.summary.lower()
        assert result.confidence == 0.0

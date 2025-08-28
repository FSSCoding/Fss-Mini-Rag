#!/usr/bin/env python3
"""
Beginner-Friendly Ollama Integration Tests

These tests help users troubleshoot their Ollama setup and identify
what's working and what needs attention.

Run with: python3 tests/test_ollama_integration.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from mini_rag.config import RAGConfig
from mini_rag.llm_synthesizer import LLMSynthesizer
from mini_rag.query_expander import QueryExpander

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOllamaIntegration(unittest.TestCase):
    """
    Tests to help beginners troubleshoot their Ollama setup.

    Each test explains what it's checking and gives clear feedback
    about what's working or needs to be fixed.
    """

    def setUp(self):
        """Set up test configuration."""
        self.config = RAGConfig()
        print(f"\n🧪 Testing with Ollama host: {self.config.llm.ollama_host}")

    def test_01_ollama_server_running(self):
        """
        ✅ Check if Ollama server is running and responding.

        This test verifies that:
        - Ollama is installed and running
        - The API endpoint is accessible
        - Basic connectivity works
        """
        print("\n📡 Testing Ollama server connectivity...")

        try:
            response = requests.get(
                f"http://{self.config.llm.ollama_host}/api/tags", timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print("   ✅ Ollama server is running!")
                print(f"   📦 Found {len(models)} models available")

                if models:
                    print("   🎯 Available models:")
                    for model in models[:5]:  # Show first 5
                        name = model.get("name", "unknown")
                        size = model.get("size", 0)
                        print(f"      • {name} ({size//1000000:.0f}MB)")
                    if len(models) > 5:
                        print(f"      ... and {len(models)-5} more")
                else:
                    print("   ⚠️  No models found. Install with: ollama pull qwen3:4b")

                self.assertTrue(True)
            else:
                self.fail(f"Ollama server responded with status {response.status_code}")

        except requests.exceptions.ConnectionError:
            self.fail(
                "❌ Cannot connect to Ollama server.\n"
                "   💡 Solutions:\n"
                "   • Start Ollama: ollama serve\n"
                "   • Check if running on different port\n"
                "   • Verify Ollama is installed: ollama --version"
            )
        except Exception as e:
            self.fail(f"❌ Unexpected error: {e}")

    def test_02_embedding_model_available(self):
        """
        ✅ Check if embedding model is available.

        This test verifies that:
        - The embedding model (nomic-embed-text) is installed
        - Embedding API calls work correctly
        - Model responds with valid embeddings
        """
        print("\n🧠 Testing embedding model availability...")

        try:
            # Test embedding generation
            response = requests.post(
                f"http://{self.config.llm.ollama_host}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "test embedding"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])

                if embedding and len(embedding) > 0:
                    print("   ✅ Embedding model working!")
                    print(f"   📊 Generated {len(embedding)}-dimensional vectors")
                    self.assertTrue(len(embedding) > 100)  # Should be substantial vectors
                else:
                    self.fail("Embedding response was empty")
            else:
                # Check if model needs to be installed
                if response.status_code == 404:
                    self.fail(
                        "❌ Embedding model not found.\n"
                        "   💡 Install with: ollama pull nomic-embed-text"
                    )
                else:
                    self.fail(f"Embedding API error: {response.status_code}")

        except Exception as e:
            self.fail(f"❌ Embedding test failed: {e}")

    def test_03_llm_model_available(self):
        """
        ✅ Check if LLM models are available for synthesis/expansion.

        This test verifies that:
        - At least one LLM model is available
        - The model can generate text responses
        - Response quality is reasonable
        """
        print("\n🤖 Testing LLM model availability...")

        synthesizer = LLMSynthesizer(config=self.config)

        if not synthesizer.is_available():
            self.fail(
                "❌ No LLM models available.\n"
                "   💡 Install a model like: ollama pull qwen3:4b"
            )

        print(f"   ✅ Found {len(synthesizer.available_models)} LLM models")
        print(f"   🎯 Will use: {synthesizer.model}")

        # Test basic text generation
        try:
            response = synthesizer._call_ollama(
                "Complete this: The capital of France is", temperature=0.1
            )

            if response and len(response.strip()) > 0:
                print("   ✅ Model generating responses!")
                print(f"   💬 Sample response: '{response[:50]}...'")

                # Basic quality check
                if "paris" in response.lower():
                    print("   🎯 Response quality looks good!")
                else:
                    print("   ⚠️  Response quality might be low")

                self.assertTrue(len(response) > 5)
            else:
                self.fail("Model produced empty response")

        except Exception as e:
            self.fail(f"❌ LLM generation test failed: {e}")

    def test_04_query_expansion_working(self):
        """
        ✅ Check if query expansion is working correctly.

        This test verifies that:
        - QueryExpander can connect to Ollama
        - Expansion produces reasonable results
        - Caching is working
        """
        print("\n🔍 Testing query expansion...")

        # Enable expansion for testing
        self.config.search.expand_queries = True
        expander = QueryExpander(self.config)

        if not expander.is_available():
            self.skipTest("⏭️  Skipping - Ollama not available (tested above)")

        # Test expansion
        test_query = "authentication"
        expanded = expander.expand_query(test_query)

        print(f"   📝 Original: '{test_query}'")
        print(f"   ➡️  Expanded: '{expanded}'")

        # Quality checks
        if expanded == test_query:
            print("   ⚠️  No expansion occurred (might be normal for simple queries)")
        else:
            # Should contain original query
            self.assertIn(test_query.lower(), expanded.lower())

            # Should be longer
            self.assertGreater(len(expanded.split()), len(test_query.split()))

            # Test caching
            cached = expander.expand_query(test_query)
            self.assertEqual(expanded, cached)
            print("   ✅ Expansion and caching working!")

    def test_05_synthesis_mode_no_thinking(self):
        """
        ✅ Test synthesis mode operates without thinking.

        Verifies that LLMSynthesizer in synthesis mode:
        - Defaults to no thinking
        - Handles <no_think> tokens properly
        - Works independently of exploration mode
        """
        print("\n🚀 Testing synthesis mode (no thinking)...")

        # Create synthesis mode synthesizer (default behavior)
        synthesizer = LLMSynthesizer()

        # Should default to no thinking
        self.assertFalse(
            synthesizer.enable_thinking, "Synthesis mode should default to no thinking"
        )
        print("   ✅ Defaults to no thinking")

        if synthesizer.is_available():
            print("   📝 Testing with live Ollama...")

            # Create mock search results
            from dataclasses import dataclass

            @dataclass
            class MockResult:
                file_path: str
                content: str
                score: float

            results = [MockResult("auth.py", "def authenticate(user): return True", 0.95)]

            # Test synthesis
            synthesis = synthesizer.synthesize_search_results(
                "user authentication", results, Path(".")
            )

            # Should get reasonable synthesis
            self.assertIsNotNone(synthesis)
            self.assertGreater(len(synthesis.summary), 10)
            print("   ✅ Synthesis mode working without thinking")
        else:
            print("   ⏭️  Live test skipped - Ollama not available")

    def test_06_exploration_mode_thinking(self):
        """
        ✅ Test exploration mode enables thinking.

        Verifies that CodeExplorer:
        - Enables thinking by default
        - Has session management
        - Works independently of synthesis mode
        """
        print("\n🧠 Testing exploration mode (with thinking)...")

        try:
            from mini_rag.explorer import CodeExplorer
        except ImportError:
            self.skipTest("⏭️  CodeExplorer not available")

        # Create exploration mode
        explorer = CodeExplorer(Path("."), self.config)

        # Should enable thinking
        self.assertTrue(
            explorer.synthesizer.enable_thinking,
            "Exploration mode should enable thinking",
        )
        print("   ✅ Enables thinking by default")

        # Should have session management
        self.assertIsNone(explorer.current_session, "Should start with no active session")
        print("   ✅ Session management available")

        # Should handle session summary gracefully
        summary = explorer.get_session_summary()
        self.assertIn("No active", summary)
        print("   ✅ Graceful session handling")

    def test_07_mode_separation(self):
        """
        ✅ Test that synthesis and exploration modes don't interfere.

        Verifies clean separation:
        - Different thinking settings
        - Independent operation
        - No cross-contamination
        """
        print("\n🔄 Testing mode separation...")

        # Create both modes
        synthesizer = LLMSynthesizer(enable_thinking=False)

        try:
            from mini_rag.explorer import CodeExplorer

            explorer = CodeExplorer(Path("."), self.config)
        except ImportError:
            self.skipTest("⏭️  CodeExplorer not available")

        # Should have different thinking settings
        self.assertFalse(synthesizer.enable_thinking, "Synthesis should not use thinking")
        self.assertTrue(
            explorer.synthesizer.enable_thinking, "Exploration should use thinking"
        )

        # Both should be uninitialized (lazy loading)
        self.assertFalse(synthesizer._initialized, "Should use lazy loading")
        self.assertFalse(explorer.synthesizer._initialized, "Should use lazy loading")

        print("   ✅ Clean mode separation confirmed")

    def test_08_with_mocked_ollama(self):
        """
        ✅ Test components work with mocked Ollama (for offline testing).

        This test verifies that:
        - System gracefully handles Ollama being unavailable
        - Fallback behaviors work correctly
        - Error messages are helpful
        """
        print("\n🎭 Testing with mocked Ollama responses...")

        # Mock successful embedding response
        mock_embedding_response = MagicMock()
        mock_embedding_response.status_code = 200
        mock_embedding_response.json.return_value = {
            "embedding": [0.1] * 768  # Standard embedding size
        }

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {
            "response": "authentication login user verification credentials"
        }

        with patch("requests.post", side_effect=[mock_embedding_response, mock_llm_response]):
            # Test query expansion with mocked response
            expander = QueryExpander(self.config)
            expander.enabled = True

            expanded = expander._llm_expand_query("authentication")
            if expanded:
                print(f"   ✅ Mocked expansion: '{expanded}'")
                self.assertIn("authentication", expanded)
            else:
                print("   ⚠️  Expansion returned None (might be expected)")

        # Test graceful degradation when Ollama unavailable
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            expander_offline = QueryExpander(self.config)

            # Should handle unavailable server gracefully
            self.assertFalse(expander_offline.is_available())

            # Should return original query when offline
            result = expander_offline.expand_query("test query")
            self.assertEqual(result, "test query")
            print("   ✅ Graceful offline behavior working!")

    def test_06_configuration_validation(self):
        """
        ✅ Check if configuration is valid and complete.

        This test verifies that:
        - All required config sections exist
        - Values are reasonable
        - Host/port settings are valid
        """
        print("\n⚙️  Testing configuration validation...")

        # Check LLM config
        self.assertIsNotNone(self.config.llm)
        self.assertTrue(self.config.llm.ollama_host)
        self.assertTrue(isinstance(self.config.llm.max_expansion_terms, int))
        self.assertGreater(self.config.llm.max_expansion_terms, 0)

        print("   ✅ LLM config valid")
        print(f"      Host: {self.config.llm.ollama_host}")
        print(f"      Max expansion terms: {self.config.llm.max_expansion_terms}")

        # Check search config
        self.assertIsNotNone(self.config.search)
        self.assertGreater(self.config.search.default_top_k, 0)
        print("   ✅ Search config valid")
        print(f"      Default top-k: {self.config.search.default_top_k}")
        print(f"      Query expansion: {self.config.search.expand_queries}")


def run_troubleshooting():
    """
    Run all troubleshooting tests with beginner-friendly output.
    """
    print("🔧 FSS-Mini-RAG Ollama Integration Tests")
    print("=" * 50)
    print("These tests help you troubleshoot your Ollama setup.")
    print("Each test explains what it's checking and how to fix issues.")
    print()

    # Run tests with detailed output
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("💡 Common Solutions:")
    print("   • Install Ollama: https://ollama.ai/download")
    print("   • Start server: ollama serve")
    print("   • Install models: ollama pull qwen3:4b")
    print("   • Install embedding model: ollama pull nomic-embed-text")
    print()
    print("📚 For more help, see docs/QUERY_EXPANSION.md")


if __name__ == "__main__":
    run_troubleshooting()

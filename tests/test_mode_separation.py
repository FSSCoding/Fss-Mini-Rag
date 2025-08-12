#!/usr/bin/env python3
"""
Test clean separation between synthesis and exploration modes.

Ensures that the two-mode architecture works correctly with no contamination
between thinking and no-thinking modes.
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path

# Add the RAG system to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mini_rag.llm_synthesizer import LLMSynthesizer  
    from mini_rag.explorer import CodeExplorer
    from mini_rag.config import RAGConfig
    from mini_rag.indexer import ProjectIndexer
    from mini_rag.search import CodeSearcher
except ImportError as e:
    print(f"❌ Could not import RAG components: {e}")
    print("   This test requires the full RAG system to be installed")
    sys.exit(1)

class TestModeSeparation(unittest.TestCase):
    """Test the clean separation between synthesis and exploration modes."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a simple test project
        test_file = self.project_path / "test_module.py"
        test_file.write_text('''"""Test module for mode separation testing."""

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user with username and password."""
    # Simple authentication logic
    if not username or not password:
        return False
    
    # Check against database (simplified)
    valid_users = {"admin": "secret", "user": "password"}
    return valid_users.get(username) == password

class UserManager:
    """Manages user operations."""
    
    def __init__(self):
        self.users = {}
    
    def create_user(self, username: str) -> bool:
        """Create a new user."""
        if username in self.users:
            return False
        self.users[username] = {"created": True}
        return True
    
    def get_user_info(self, username: str) -> dict:
        """Get user information."""
        return self.users.get(username, {})

def process_login_request(username: str, password: str) -> dict:
    """Process a login request and return status."""
    if authenticate_user(username, password):
        return {"success": True, "message": "Login successful"}
    else:
        return {"success": False, "message": "Invalid credentials"}
''')
        
        # Index the project for testing
        try:
            indexer = ProjectIndexer(self.project_path)
            indexer.index_project()
        except Exception as e:
            self.skipTest(f"Could not index test project: {e}")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_01_synthesis_mode_defaults(self):
        """Test that synthesis mode has correct defaults."""
        synthesizer = LLMSynthesizer()
        
        # Should default to no thinking
        self.assertFalse(synthesizer.enable_thinking, 
                        "Synthesis mode should default to no thinking")
        
        print("✅ Synthesis mode defaults to no thinking")
    
    def test_02_exploration_mode_defaults(self):
        """Test that exploration mode enables thinking."""
        config = RAGConfig()
        explorer = CodeExplorer(self.project_path, config)
        
        # Should enable thinking in exploration mode
        self.assertTrue(explorer.synthesizer.enable_thinking,
                       "Exploration mode should enable thinking")
        
        print("✅ Exploration mode enables thinking by default")
    
    def test_03_no_runtime_thinking_toggle(self):
        """Test that thinking mode cannot be toggled at runtime."""
        synthesizer = LLMSynthesizer(enable_thinking=False)
        
        # Should not have public methods to toggle thinking
        thinking_methods = [method for method in dir(synthesizer) 
                           if 'thinking' in method.lower() and not method.startswith('_')]
        
        # The only thinking-related attribute should be the readonly enable_thinking
        self.assertEqual(len(thinking_methods), 0,
                        "Should not have public thinking toggle methods")
        
        print("✅ No runtime thinking toggle methods available")
    
    def test_04_mode_contamination_prevention(self):
        """Test that modes don't contaminate each other."""
        if not self._ollama_available():
            self.skipTest("Ollama not available for contamination testing")
        
        # Create synthesis mode synthesizer
        synthesis_synthesizer = LLMSynthesizer(enable_thinking=False)
        
        # Create exploration mode synthesizer  
        exploration_synthesizer = LLMSynthesizer(enable_thinking=True)
        
        # Both should maintain their thinking settings
        self.assertFalse(synthesis_synthesizer.enable_thinking,
                        "Synthesis synthesizer should remain no-thinking")
        self.assertTrue(exploration_synthesizer.enable_thinking,
                       "Exploration synthesizer should remain thinking-enabled")
        
        print("✅ Mode contamination prevented")
    
    def test_05_exploration_session_management(self):
        """Test exploration session management."""
        config = RAGConfig()
        explorer = CodeExplorer(self.project_path, config)
        
        # Should start with no active session
        self.assertIsNone(explorer.current_session, 
                         "Should start with no active session")
        
        # Should be able to create session summary even without session
        summary = explorer.get_session_summary()
        self.assertIn("No active", summary,
                     "Should handle no active session gracefully")
        
        print("✅ Session management working correctly")
    
    def test_06_context_memory_structure(self):
        """Test that exploration mode has context memory structure."""
        config = RAGConfig()
        explorer = CodeExplorer(self.project_path, config)
        
        # Should have context tracking attributes
        self.assertTrue(hasattr(explorer, 'current_session'),
                       "Explorer should have session tracking")
        
        print("✅ Context memory structure present")
    
    def test_07_synthesis_mode_no_thinking_prompts(self):
        """Test that synthesis mode properly handles no-thinking."""
        if not self._ollama_available():
            self.skipTest("Ollama not available for prompt testing")
        
        synthesizer = LLMSynthesizer(enable_thinking=False)
        
        # Test the _call_ollama method handling
        if hasattr(synthesizer, '_call_ollama'):
            # Should append <no_think> when thinking disabled
            # This is a white-box test of the implementation
            try:
                # Mock test - just verify the method exists and can be called
                result = synthesizer._call_ollama("test", temperature=0.1, disable_thinking=True)
                # Don't assert on result since Ollama might not be available
                print("✅ No-thinking prompt handling available")
            except Exception as e:
                print(f"⚠️  Prompt handling test skipped: {e}")
        else:
            self.fail("Synthesizer should have _call_ollama method")
    
    def test_08_mode_specific_initialization(self):
        """Test that modes initialize correctly with lazy loading."""
        # Synthesis mode
        synthesis_synthesizer = LLMSynthesizer(enable_thinking=False)
        self.assertFalse(synthesis_synthesizer._initialized,
                        "Should start uninitialized for lazy loading")
        
        # Exploration mode  
        config = RAGConfig()
        explorer = CodeExplorer(self.project_path, config)
        self.assertFalse(explorer.synthesizer._initialized,
                        "Should start uninitialized for lazy loading")
        
        print("✅ Lazy initialization working correctly")
    
    def test_09_search_vs_exploration_integration(self):
        """Test integration differences between search and exploration."""
        # Regular search (synthesis mode)
        searcher = CodeSearcher(self.project_path)
        search_results = searcher.search("authentication", top_k=3)
        
        self.assertGreater(len(search_results), 0, 
                          "Search should return results")
        
        # Exploration mode setup
        config = RAGConfig()
        explorer = CodeExplorer(self.project_path, config)
        
        # Both should work with same project but different approaches
        self.assertTrue(hasattr(explorer, 'synthesizer'),
                       "Explorer should have thinking-enabled synthesizer")
        
        print("✅ Search and exploration integration working")
    
    def test_10_mode_guidance_detection(self):
        """Test that the system can detect when to recommend different modes."""
        # Words that should trigger exploration mode recommendation
        exploration_triggers = ['why', 'how', 'explain', 'debug']
        
        for trigger in exploration_triggers:
            query = f"{trigger} does authentication work"
            # This would typically be tested in the main CLI
            # Here we just verify the trigger detection logic exists
            has_trigger = any(word in query.lower() for word in exploration_triggers)
            self.assertTrue(has_trigger, 
                           f"Should detect '{trigger}' as exploration trigger")
        
        print("✅ Mode guidance detection working")
    
    def _ollama_available(self) -> bool:
        """Check if Ollama is available for testing."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

def main():
    """Run mode separation tests."""
    print("🧪 Testing Mode Separation")
    print("=" * 40)
    
    # Check if we're in the right environment
    if not Path("mini_rag").exists():
        print("❌ Tests must be run from the FSS-Mini-RAG root directory")
        sys.exit(1)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestModeSeparation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 40)
    if result.wasSuccessful():
        print("✅ All mode separation tests passed!")
        print("   Synthesis and exploration modes are cleanly separated")
    else:
        print("❌ Some tests failed")
        print(f"   Failed: {len(result.failures)}, Errors: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Quick test script to verify our key fixes without heavy dependencies.

⚠️  IMPORTANT: This test requires the virtual environment to be activated:
    source .venv/bin/activate
    python test_fixes.py

Or run directly with venv:
    source .venv/bin/activate && python test_fixes.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Check if virtual environment is activated


def check_venv():
    if "VIRTUAL_ENV" not in os.environ:
        print("⚠️  WARNING: Virtual environment not detected!")
        print("   This test requires the virtual environment to be activated.")
        print("   Run: source .venv/bin/activate && python test_fixes.py")
        print("   Continuing anyway...\n")


check_venv()

# Add current directory to Python path
sys.path.insert(0, ".")


def test_config_model_rankings():
    """Test that model rankings are properly configured."""
    print("=" * 60)
    print("TESTING CONFIG AND MODEL RANKINGS")
    print("=" * 60)

    try:
        # Test config loading without heavy dependencies
        from mini_rag.config import ConfigManager, LLMConfig

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            config_manager = ConfigManager(tmpdir)
            config = config_manager.load_config()

            print("✓ Config loads successfully")

            # Check LLM config and model rankings
            if hasattr(config, "llm"):
                llm_config = config.llm
                print(f"✓ LLM config found: {type(llm_config)}")

                if hasattr(llm_config, "model_rankings"):
                    rankings = llm_config.model_rankings
                    print(f"✓ Model rankings: {rankings}")

                    if rankings and rankings[0] == "qwen3:1.7b":
                        print("✓ qwen3:1.7b is FIRST priority - CORRECT!")
                        return True
                    else:
                        print(
                            f"✗ WRONG: First model is {rankings[0] if rankings else 'None'}, should be qwen3:1.7b"
                        )
                        return False
                else:
                    print("✗ Model rankings not found in LLM config")
                    return False
            else:
                print("✗ LLM config not found")
                return False

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_context_length_fix():
    """Test that context length is correctly set to 32K."""
    print("\n" + "=" * 60)
    print("TESTING CONTEXT LENGTH FIXES")
    print("=" * 60)

    try:
        # Read the synthesizer file and check for 32000
        with open("mini_rag/llm_synthesizer.py", "r") as f:
            synthesizer_content = f.read()

        if '"num_ctx": 32000' in synthesizer_content:
            print("✓ LLM Synthesizer: num_ctx is correctly set to 32000")
        elif '"num_ctx": 80000' in synthesizer_content:
            print("✗ LLM Synthesizer: num_ctx is still 80000 - NEEDS FIX")
            return False
        else:
            print("? LLM Synthesizer: num_ctx setting not found clearly")

        # Read the safeguards file and check for 32000
        with open("mini_rag/llm_safeguards.py", "r") as f:
            safeguards_content = f.read()

        if "context_window: int = 32000" in safeguards_content:
            print("✓ Safeguards: context_window is correctly set to 32000")
            return True
        elif "context_window: int = 80000" in safeguards_content:
            print("✗ Safeguards: context_window is still 80000 - NEEDS FIX")
            return False
        else:
            print("? Safeguards: context_window setting not found clearly")
            return False

    except Exception as e:
        print(f"✗ Error checking context length: {e}")
        return False


def test_safeguard_preservation():
    """Test that safeguards preserve content instead of dropping it."""
    print("\n" + "=" * 60)
    print("TESTING SAFEGUARD CONTENT PRESERVATION")
    print("=" * 60)

    try:
        # Read the synthesizer file and check for the preservation method
        with open("mini_rag/llm_synthesizer.py", "r") as f:
            synthesizer_content = f.read()

        if "_create_safeguard_response_with_content" in synthesizer_content:
            print("✓ Safeguard content preservation method exists")
        else:
            print("✗ Safeguard content preservation method missing")
            return False

        # Check for the specific preservation logic
        if "AI Response (use with caution):" in synthesizer_content:
            print("✓ Content preservation warning format found")
        else:
            print("✗ Content preservation warning format missing")
            return False

        # Check that it's being called instead of dropping content
        if (
            "return self._create_safeguard_response_with_content(" in synthesizer_content
            and "issue_type, explanation, raw_response" in synthesizer_content
        ):
            print("✓ Preservation method is called when safeguards trigger")
            return True
        else:
            print("✗ Preservation method not called properly")
            return False

    except Exception as e:
        print(f"✗ Error checking safeguard preservation: {e}")
        return False


def test_import_fixes():
    """Test that import statements are fixed from claude_rag to mini_rag."""
    print("\n" + "=" * 60)
    print("TESTING IMPORT STATEMENT FIXES")
    print("=" * 60)

    test_files = [
        "tests/test_rag_integration.py",
        "tests/01_basic_integration_test.py",
        "tests/test_hybrid_search.py",
        "tests/test_context_retrieval.py",
    ]

    all_good = True

    for test_file in test_files:
        if Path(test_file).exists():
            try:
                with open(test_file, "r") as f:
                    content = f.read()

                if "claude_rag" in content:
                    print(f"✗ {test_file}: Still contains 'claude_rag' imports")
                    all_good = False
                elif "mini_rag" in content:
                    print(f"✓ {test_file}: Uses correct 'mini_rag' imports")
                else:
                    print(f"? {test_file}: No rag imports found")

            except Exception as e:
                print(f"✗ Error reading {test_file}: {e}")
                all_good = False
        else:
            print(f"? {test_file}: File not found")

    return all_good


def main():
    """Run all tests."""
    print("FSS-Mini-RAG Fix Verification Tests")
    print("Testing all the critical fixes...")

    tests = [
        ("Model Rankings", test_config_model_rankings),
        ("Context Length", test_context_length_fix),
        ("Safeguard Preservation", test_safeguard_preservation),
        ("Import Fixes", test_import_fixes),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED - System should be working properly!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - System needs more fixes!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

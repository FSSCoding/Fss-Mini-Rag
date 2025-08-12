#!/usr/bin/env python3
"""
FSS-Mini-RAG Troubleshooting Tool

A beginner-friendly troubleshooting tool that checks your setup
and helps identify what's working and what needs attention.

Run with: python3 tests/troubleshoot.py
"""

import sys
import subprocess
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Run comprehensive troubleshooting checks."""
    
    print("🔧 FSS-Mini-RAG Troubleshooting Tool")
    print("=" * 50)
    print("This tool checks your setup and helps fix common issues.")
    print()
    
    # Menu of available tests
    print("Available tests:")
    print("  1. Full Ollama Integration Test")
    print("  2. Smart Ranking Test")
    print("  3. Basic System Validation")
    print("  4. All Tests (recommended)")
    print()
    
    choice = input("Select test (1-4, or Enter for all): ").strip()
    
    if choice == "1" or choice == "" or choice == "4":
        print("\n" + "🤖 OLLAMA INTEGRATION TESTS".center(50, "="))
        run_test("test_ollama_integration.py")
    
    if choice == "2" or choice == "" or choice == "4":
        print("\n" + "🧮 SMART RANKING TESTS".center(50, "="))
        run_test("test_smart_ranking.py")
    
    if choice == "3" or choice == "" or choice == "4":
        print("\n" + "🔍 SYSTEM VALIDATION TESTS".center(50, "="))
        run_test("03_system_validation.py")
    
    print("\n" + "✅ TROUBLESHOOTING COMPLETE".center(50, "="))
    print("💡 If you're still having issues:")
    print("   • Check docs/QUERY_EXPANSION.md for setup help")
    print("   • Ensure Ollama is installed: https://ollama.ai/download")
    print("   • Start Ollama server: ollama serve")
    print("   • Install models: ollama pull qwen3:1.7b")

def run_test(test_file):
    """Run a specific test file."""
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    try:
        # Run the test
        result = subprocess.run([
            sys.executable, str(test_path)
        ], capture_output=True, text=True, timeout=60)
        
        # Show output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        if result.returncode == 0:
            print(f"✅ {test_file} completed successfully!")
        else:
            print(f"⚠️  {test_file} had some issues (return code: {result.returncode})")
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Error running {test_file}: {e}")

if __name__ == "__main__":
    main()
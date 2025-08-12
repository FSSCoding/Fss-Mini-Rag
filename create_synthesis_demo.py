#!/usr/bin/env python3
"""
Create demo GIF for Synthesis Mode - Fast & Consistent RAG Search
Shows the streamlined workflow for quick answers and code discovery.
"""

import time
import sys
import os
from pathlib import Path

class SynthesisDemoSimulator:
    def __init__(self):
        self.width = 100
        self.height = 30
        
    def clear_screen(self):
        print("\033[H\033[2J", end="")
        
    def type_command(self, command: str, delay: float = 0.05):
        """Simulate typing a command."""
        print("$ ", end="", flush=True)
        for char in command:
            print(char, end="", flush=True)
            time.sleep(delay)
        print()
        time.sleep(0.5)
        
    def show_output(self, lines: list, delay: float = 0.3):
        """Show command output with realistic timing."""
        for line in lines:
            print(line)
            time.sleep(delay)
        time.sleep(1.0)
    
    def run_synthesis_demo(self):
        """Run the synthesis mode demonstration."""
        self.clear_screen()
        
        # Title
        print("🚀 FSS-Mini-RAG: Synthesis Mode Demo")
        print("=" * 50)
        print("Fast & consistent RAG search for quick answers")
        print()
        time.sleep(2)
        
        # Step 1: Index a project
        print("Step 1: Index a sample project")
        print("-" * 30)
        self.type_command("rag-mini index ./sample-project")
        
        self.show_output([
            "📁 Indexing project: sample-project",
            "🔍 Found 12 files to process",  
            "✂️  Creating semantic chunks...",
            "🧠 Generating embeddings...",
            "💾 Building vector index...",
            "✅ Indexed 89 chunks from 12 files in 3.2s",
            "",
            "💡 Try: rag-mini search ./sample-project \"your search here\""
        ])
        
        # Step 2: Quick search
        print("Step 2: Quick semantic search")  
        print("-" * 30)
        self.type_command("rag-mini search ./sample-project \"user authentication\"")
        
        self.show_output([
            "🔍 Searching \"user authentication\" in sample-project",
            "✅ Found 5 results:",
            "",
            "1. auth/models.py",
            "   Score: 0.923",
            "   Lines: 45-62",  
            "   Context: User class",
            "   Content:",
            "     class User:",
            "         def authenticate(self, password):",
            "             return bcrypt.checkpw(password, self.password_hash)",
            "",
            "2. auth/views.py",
            "   Score: 0.887", 
            "   Lines: 23-41",
            "   Context: login_view function",
            "   Content:",
            "     def login_view(request):",
            "         user = authenticate(username, password)",
            "         if user:",
            "             login(request, user)",
            "",
            "3. middleware/auth.py",
            "   Score: 0.845",
            "   Content: Authentication middleware checking..."
        ])
        
        # Step 3: Search with AI synthesis
        print("Step 3: Add AI synthesis for deeper understanding")
        print("-" * 50)
        self.type_command("rag-mini search ./sample-project \"error handling\" --synthesize")
        
        self.show_output([
            "🔍 Searching \"error handling\" in sample-project", 
            "🧠 Generating LLM synthesis...",
            "✅ Found 4 results:",
            "",
            "1. utils/exceptions.py",
            "   Score: 0.934",  
            "   Content: Custom exception classes for API errors...",
            "",
            "2. api/handlers.py", 
            "   Score: 0.889",
            "   Content: Global exception handler with logging...",
            "",
            "🧠 LLM SYNTHESIS",
            "=" * 50,
            "",
            "📝 Summary:",
            "   This codebase implements a robust error handling system with",
            "   custom exceptions, global handlers, and structured logging.",
            "",
            "🔍 Key Findings:",
            "   • Custom exception hierarchy in utils/exceptions.py",
            "   • Global error handler catches all API exceptions",  
            "   • Logging integrated with error tracking service",
            "",
            "💡 Code Patterns:",
            "   try/except blocks with specific exception types",
            "   Centralized error response formatting",
            "",
            "🎯 Suggested Actions:",
            "   • Review exception hierarchy for completeness",
            "   • Consider adding error recovery mechanisms",
            "",
            "🟢 Confidence: 87%"
        ])
        
        # Step 4: Show performance
        print("Step 4: Performance characteristics") 
        print("-" * 35)
        print("⚡ Synthesis Mode Benefits:")
        print("   • Lightning fast responses (no thinking overhead)")
        print("   • Consistent, reliable results") 
        print("   • Perfect for code discovery and quick answers")
        print("   • Works great with ultra-efficient models (qwen3:0.6b)")
        print()
        time.sleep(3)
        
        # Step 5: When to use
        print("💡 When to use Synthesis Mode:")
        print("   ✅ Quick code lookups")
        print("   ✅ Finding specific functions or classes") 
        print("   ✅ Understanding code structure")
        print("   ✅ Fast documentation searches")
        print("   ✅ Batch processing multiple queries")
        print()
        
        print("🧠 For deeper analysis, try: rag-mini explore ./project")
        print()
        time.sleep(3)
        
        print("🎬 Demo complete! This was Synthesis Mode - optimized for speed.")

def main():
    """Run the synthesis mode demo."""
    demo = SynthesisDemoSimulator() 
    
    print("Starting FSS-Mini-RAG Synthesis Mode Demo...")
    print("Record with: asciinema rec synthesis_demo.cast")
    print("Press Enter to start...")
    input()
    
    demo.run_synthesis_demo()
    
    print("\n🎯 To create GIF:")
    print("agg synthesis_demo.cast synthesis_demo.gif")

if __name__ == "__main__":
    main()
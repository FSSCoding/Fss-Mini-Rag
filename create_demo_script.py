#!/usr/bin/env python3
"""
Create an animated demo script that simulates the FSS-Mini-RAG TUI experience.
This script generates a realistic but controlled demonstration for GIF recording.
"""

import time
import sys
import os
from typing import List

class DemoSimulator:
    def __init__(self):
        self.width = 80
        self.height = 24
        
    def clear_screen(self):
        """Clear the terminal screen."""
        print("\033[H\033[2J", end="")
        
    def type_text(self, text: str, delay: float = 0.03):
        """Simulate typing text character by character."""
        for char in text:
            print(char, end="", flush=True)
            time.sleep(delay)
        print()
        
    def pause(self, duration: float):
        """Pause for the specified duration."""
        time.sleep(duration)
        
    def show_header(self):
        """Display the TUI header."""
        print("╔════════════════════════════════════════════════════╗")
        print("║              FSS-Mini-RAG TUI                      ║") 
        print("║         Semantic Code Search Interface             ║")
        print("╚════════════════════════════════════════════════════╝")
        print()
        
    def show_menu(self):
        """Display the main menu."""
        print("🎯 Main Menu")
        print("============")
        print()
        print("1. Select project directory")
        print("2. Index project for search") 
        print("3. Search project")
        print("4. View status")
        print("5. Configuration")
        print("6. CLI command reference")
        print("7. Exit")
        print()
        print("💡 All these actions can be done via CLI commands")
        print("   You'll see the commands as you use this interface!")
        print()
        
    def simulate_project_selection(self):
        """Simulate selecting a project directory."""
        print("Select option (number): ", end="", flush=True)
        self.type_text("1", delay=0.15)
        self.pause(0.5)
        print()
        print("📁 Select Project Directory")
        print("===========================")
        print()
        print("Project path: ", end="", flush=True)
        self.type_text("./demo-project", delay=0.08)
        self.pause(0.8)
        print()
        print("✅ Selected: ./demo-project")
        print()
        print("💡 CLI equivalent: rag-mini index ./demo-project")
        self.pause(1.5)
        
    def simulate_indexing(self):
        """Simulate the indexing process."""
        self.clear_screen()
        self.show_header()
        print("🚀 Indexing demo-project")
        print("========================")
        print()
        print("Found 12 files to index")
        print()
        
        # Simulate progress bar
        print("  Indexing files... ", end="")
        progress_chars = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        for i, char in enumerate(progress_chars):
            print(char, end="", flush=True)
            time.sleep(0.03)  # Slightly faster
            if i % 8 == 0:
                percentage = int((i / len(progress_chars)) * 100)
                print(f" {percentage}%", end="\r")
                print("  Indexing files... " + progress_chars[:i+1], end="")
        
        print(" 100%")
        print()
        print(" Added 58 chunks to database")
        print()
        print("Indexing Complete!")
        print("Files indexed: 12")
        print("Chunks created: 58") 
        print("Time taken: 2.8 seconds")
        print("Speed: 4.3 files/second")
        print("✅ Indexed 12 files in 2.8s")
        print("   Created 58 chunks")
        print("   Speed: 4.3 files/sec")
        print()
        print("💡 CLI equivalent: rag-mini index ./demo-project")
        self.pause(2.0)
        
    def simulate_search(self):
        """Simulate searching the indexed project."""
        self.clear_screen()
        self.show_header()
        print("🔍 Search Project")
        print("=================")
        print()
        print("Search query: ", end="", flush=True)
        self.type_text('"user authentication"', delay=0.08)
        self.pause(0.8)
        print()
        print("🔍 Searching \"user authentication\" in demo-project")
        self.pause(0.5)
        print("✅ Found 8 results:")
        print()
        
        # Show search results with multi-line previews
        results = [
            {
                "file": "auth/manager.py",
                "function": "AuthManager.login()",
                "preview": "Authenticate user and create session.\nValidates credentials against database and\nreturns session token on success.",
                "score": "0.94"
            },
            {
                "file": "auth/validators.py", 
                "function": "validate_password()",
                "preview": "Validate user password against stored hash.\nSupports bcrypt, scrypt, and argon2 hashing.\nIncludes timing attack protection.",
                "score": "0.91"
            },
            {
                "file": "middleware/auth.py",
                "function": "require_authentication()",
                "preview": "Authentication middleware decorator.\nChecks session tokens and JWT validity.\nRedirects to login on authentication failure.",
                "score": "0.88"
            },
            {
                "file": "api/endpoints.py",
                "function": "login_endpoint()",
                "preview": "Handle user login API requests.\nAccepts JSON credentials, validates input,\nand returns authentication tokens.",
                "score": "0.85"
            },
            {
                "file": "models/user.py",
                "function": "User.authenticate()",
                "preview": "User model authentication method.\nQueries database for user credentials\nand handles account status checks.",
                "score": "0.82"
            },
            {
                "file": "auth/tokens.py",
                "function": "generate_jwt_token()",
                "preview": "Generate JWT authentication tokens.\nIncludes expiration, claims, and signature.\nSupports refresh and access token types.",
                "score": "0.79"
            },
            {
                "file": "utils/security.py",
                "function": "hash_password()",
                "preview": "Secure password hashing utility.\nUses bcrypt with configurable rounds.\nProvides salt generation and validation.",
                "score": "0.76"
            },
            {
                "file": "config/auth_settings.py",
                "function": "load_auth_config()",
                "preview": "Load authentication configuration.\nHandles JWT secrets, token expiration,\nand authentication provider settings.",
                "score": "0.73"
            }
        ]
        
        for i, result in enumerate(results, 1):
            print(f"📄 Result {i} (Score: {result['score']})")
            print(f"   File: {result['file']}")
            print(f"   Function: {result['function']}")
            preview_lines = result['preview'].split('\n')
            for j, line in enumerate(preview_lines):
                if j == 0:
                    print(f"   Preview: {line}")
                else:
                    print(f"            {line}")
            print()
            self.pause(0.6)
        
        print("💡 CLI equivalent: rag-mini search ./demo-project \"user authentication\"")
        self.pause(2.5)
        
    def simulate_cli_reference(self):
        """Show CLI command reference."""
        self.clear_screen()
        self.show_header()
        print("🖥️  CLI Command Reference")
        print("=========================")
        print()
        print("What you just did in the TUI:")
        print()
        print("1️⃣  Select & Index Project:")
        print("    rag-mini index ./demo-project")
        print("    # Indexed 12 files → 58 semantic chunks")
        print()
        print("2️⃣  Search Project:")
        print('    rag-mini search ./demo-project "user authentication"')
        print("    # Found 8 relevant matches with context")
        print()
        print("3️⃣  Check Status:")
        print("    rag-mini status ./demo-project")
        print()
        print("🚀 You can now use these commands directly!")
        print("   No TUI required for power users.")
        print()
        print("💡 Try semantic queries like:")
        print('   • "error handling"  • "database queries"')
        print('   • "API validation"  • "configuration management"')
        self.pause(3.0)
        
    def run_demo(self):
        """Run the complete demo simulation."""
        print("🎬 Starting FSS-Mini-RAG Demo...")
        self.pause(1.0)
        
        # Clear and show TUI startup
        self.clear_screen()
        self.show_header()
        self.show_menu()
        self.pause(1.5)
        
        # Simulate workflow
        self.simulate_project_selection()
        self.simulate_indexing()
        self.simulate_search() 
        self.simulate_cli_reference()
        
        # Final message
        self.clear_screen()
        print("🎉 Demo Complete!")
        print()
        print("FSS-Mini-RAG: Semantic code search that actually works")
        print("Copy the folder, run ./rag-mini, and start searching!")
        print()
        print("Ready to try it yourself? 🚀")

if __name__ == "__main__":
    demo = DemoSimulator()
    demo.run_demo()
#!/usr/bin/env python3
"""
Create demo GIF for Exploration Mode - Deep Thinking & Interactive Learning
Shows the conversational workflow for understanding and debugging codebases.
"""

import time
import sys
import os
from pathlib import Path

class ExplorationDemoSimulator:
    def __init__(self):
        self.width = 100
        self.height = 35
        
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
        
    def type_question(self, question: str, delay: float = 0.04):
        """Simulate typing a question in exploration mode."""
        print("> ", end="", flush=True)
        for char in question:
            print(char, end="", flush=True)
            time.sleep(delay)
        print()
        time.sleep(0.5)
    
    def show_thinking(self, duration: float = 2.0):
        """Show thinking animation."""
        print("🔍 Analyzing...", end="", flush=True)
        for _ in range(3):
            time.sleep(duration / 3)
            print(".", end="", flush=True)
        print()
        time.sleep(0.5)
    
    def show_response(self, lines: list, delay: float = 0.4):
        """Show AI response with realistic timing."""
        for line in lines:
            print(line)
            time.sleep(delay)
        time.sleep(1.5)
    
    def run_exploration_demo(self):
        """Run the exploration mode demonstration."""
        self.clear_screen()
        
        # Title
        print("🧠 FSS-Mini-RAG: Exploration Mode Demo")
        print("=" * 55)
        print("Deep thinking & interactive learning for complex codebases")
        print()
        time.sleep(2)
        
        # Step 1: Start exploration
        print("Step 1: Start interactive exploration session")
        print("-" * 45)
        self.type_command("rag-mini explore ./webapp-project")
        
        self.show_response([
            "🧠 EXPLORATION MODE STARTED", 
            "=" * 50,
            "Project: webapp-project",
            "Session: explore_1702845632",
            "",
            "🎯 This mode uses thinking and remembers context.",
            "   Perfect for debugging, learning, and deep exploration.",
            "",  
            "💡 Tips:",
            "   • Ask follow-up questions - I'll remember our conversation",
            "   • Use 'why', 'how', 'explain' for detailed reasoning",
            "   • Type 'quit' or 'exit' to end session",
            "",
            "=" * 50,
            "",
            "🤔 Ask your first question about the codebase:"
        ])
        
        # Step 2: First question - How authentication works
        print("Step 2: Understanding authentication system")
        print("-" * 42)
        self.type_question("How does authentication work in this codebase?")
        
        self.show_thinking()
        
        self.show_response([
            "",
            "🧠 EXPLORATION ANALYSIS (Question #1)",
            "Session: 0.2m | Results: 8 | Time: 3.4s",
            "=" * 60,
            "",
            "📝 Analysis:", 
            "   This webapp implements a JWT-based authentication system with",
            "   session management, role-based permissions, and OAuth2 integration.",
            "",
            "🔍 Key Insights:",
            "   • JWT tokens generated in auth/jwt_handler.py with 24h expiry",
            "   • User sessions stored in Redis for fast lookups and invalidation", 
            "   • Role-based access control through middleware/permissions.py",
            "   • OAuth2 integration supports Google, GitHub, and Microsoft providers",
            "   • Password hashing uses bcrypt with 12 rounds for security",
            "",
            "💡 Code Examples:",
            "   JWT generation: jwt.encode(payload, SECRET_KEY, algorithm='HS256')",
            "   Session storage: redis.setex(f'session:{user_id}', 86400, token)",
            "   Permission check: @require_permission('admin') decorator",
            "",
            "🎯 Next Steps:",
            "   • Review JWT secret rotation policy", 
            "   • Consider implementing refresh tokens",
            "   • Audit OAuth2 scope permissions",
            "",
            "🟢 Confidence: 91%"
        ])
        
        # Step 3: Follow-up question - Security concerns
        print("Step 3: Follow-up question (context remembered)")
        print("-" * 48)
        self.type_question("What security concerns should I be aware of?")
        
        self.show_thinking(1.8)
        
        self.show_response([
            "",
            "🧠 EXPLORATION ANALYSIS (Question #2)",  
            "Session: 1.4m | Results: 6 | Time: 2.1s",
            "=" * 60,
            "",
            "📝 Analysis:",
            "   Building on the JWT authentication system we just discussed,",
            "   I've identified several security considerations that need attention.",
            "",
            "🔍 Key Insights:",
            "   • JWT secret is hardcoded in config.py (CRITICAL RISK)",
            "   • No rate limiting on login endpoints (brute force vulnerable)",
            "   • Session invalidation only happens on logout, not on password change",
            "   • OAuth2 state parameter validation could be strengthened",
            "   • CORS settings allow all origins in development config",
            "",
            "💡 Code Examples:",
            "   Vulnerable: SECRET_KEY = 'hardcoded-secret-123'",
            "   Missing: @rate_limit('5 per minute') on /api/login",
            "   Risk: CORS_ALLOW_ALL_ORIGINS = True",
            "",
            "🎯 Next Steps:",
            "   • Move JWT secret to environment variables immediately",
            "   • Implement rate limiting with Redis or in-memory store", 
            "   • Add session invalidation on password/email changes",
            "   • Review and restrict CORS origins for production",
            "   • Add security headers middleware",
            "",
            "🔴 Confidence: 94% | Context: 1 previous questions"
        ])
        
        # Step 4: Third question - Performance issues  
        print("Step 4: Exploring performance (conversation continues)")
        print("-" * 54)
        self.type_question("Why might the login process be slow?")
        
        self.show_thinking(2.2)
        
        self.show_response([
            "",
            "🧠 EXPLORATION ANALYSIS (Question #3)",
            "Session: 2.1m | Results: 7 | Time: 2.8s", 
            "=" * 60,
            "",
            "📝 Analysis:",
            "   Considering our previous discussion about JWT auth and security,",
            "   the login slowness likely stems from several performance bottlenecks.",
            "",
            "🔍 Key Insights:",
            "   • bcrypt rounds set to 15 (recommended: 10-12) causing CPU overhead",
            "   • Database queries for user lookup aren't indexed on email field",
            "   • Redis connection pool not configured, creating new connections",
            "   • OAuth2 provider calls lack timeout settings (can hang)",
            "   • Session cleanup runs synchronously during login flow",
            "",
            "💡 Code Examples:",
            "   Slow: bcrypt.hashpw(password, bcrypt.gensalt(rounds=15))",
            "   Missing: CREATE INDEX idx_users_email ON users(email)",  
            "   Blocking: cleanup_expired_sessions() # Should be async",
            "",
            "🎯 Next Steps:",
            "   • Reduce bcrypt rounds to 12 for better balance",
            "   • Add database index on users.email column",
            "   • Configure Redis connection pooling",
            "   • Move session cleanup to background task",
            "   • Add OAuth2 request timeouts (5-10 seconds)",
            "",
            "🟡 Confidence: 89% | Context: 2 previous questions"
        ])
        
        # Step 5: Session summary
        print("Step 5: Session summary and conclusion")
        print("-" * 38)
        self.type_question("summary")
        
        self.show_response([
            "",
            "🧠 EXPLORATION SESSION SUMMARY", 
            "=" * 40,
            "Project: webapp-project",
            "Session ID: explore_1702845632", 
            "Duration: 2.5 minutes",
            "Questions explored: 3",
            "",
            "📋 Topics explored:",
            "   1. How does authentication work in this codebase? (confidence: 91%)",
            "   2. What security concerns should I be aware of? (confidence: 94%)",
            "   3. Why might the login process be slow? (confidence: 89%)",
            "",
            "🎯 Key Discoveries:",
            "   • JWT-based auth with session management",
            "   • Critical security issues (hardcoded secrets, no rate limiting)",  
            "   • Performance bottlenecks (bcrypt settings, missing indexes)",
            "",
            "💡 Action Items Generated:",
            "   • Immediate: Fix hardcoded JWT secret",
            "   • High Priority: Add rate limiting and database indexes", 
            "   • Monitor: Review OAuth2 configurations"
        ])
        
        # Step 6: Exit
        self.type_question("quit")
        
        self.show_response([
            "",
            "✅ Exploration session ended.",
            "",
            "🎬 This was Exploration Mode - perfect for learning and debugging!"
        ])
        
        # Final summary
        print()
        print("💡 Exploration Mode Benefits:")
        print("   🧠 Thinking-enabled AI for detailed reasoning")
        print("   💭 Conversation memory across questions")
        print("   🔍 Perfect for debugging and understanding")
        print("   📚 Educational - learn how code really works")
        print("   🎯 Context-aware follow-up responses")
        print()
        time.sleep(3)

def main():
    """Run the exploration mode demo."""
    demo = ExplorationDemoSimulator()
    
    print("Starting FSS-Mini-RAG Exploration Mode Demo...")
    print("Record with: asciinema rec exploration_demo.cast")
    print("Press Enter to start...")
    input()
    
    demo.run_exploration_demo()
    
    print("\n🎯 To create GIF:")
    print("agg exploration_demo.cast exploration_demo.gif")

if __name__ == "__main__":
    main()
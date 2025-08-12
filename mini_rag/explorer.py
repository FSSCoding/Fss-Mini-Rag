#!/usr/bin/env python3
"""
Interactive Code Explorer with Thinking Mode

Provides multi-turn conversations with context memory for debugging and learning.
Perfect for exploring codebases with detailed reasoning and follow-up questions.
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

try:
    from .llm_synthesizer import LLMSynthesizer, SynthesisResult
    from .search import CodeSearcher
    from .config import RAGConfig
except ImportError:
    # For direct testing
    from llm_synthesizer import LLMSynthesizer, SynthesisResult
    from search import CodeSearcher
    from config import RAGConfig

logger = logging.getLogger(__name__)

@dataclass
class ExplorationSession:
    """Track an exploration session with context history."""
    project_path: Path
    conversation_history: List[Dict[str, Any]]
    session_id: str
    started_at: float
    
    def add_exchange(self, question: str, search_results: List[Any], response: SynthesisResult):
        """Add a question/response exchange to the conversation history."""
        self.conversation_history.append({
            "timestamp": time.time(),
            "question": question,
            "search_results_count": len(search_results),
            "response": {
                "summary": response.summary,
                "key_points": response.key_points,
                "code_examples": response.code_examples,
                "suggested_actions": response.suggested_actions,
                "confidence": response.confidence
            }
        })

class CodeExplorer:
    """Interactive code exploration with thinking and context memory."""
    
    def __init__(self, project_path: Path, config: RAGConfig = None):
        self.project_path = project_path
        self.config = config or RAGConfig()
        
        # Initialize components with thinking enabled
        self.searcher = CodeSearcher(project_path)
        self.synthesizer = LLMSynthesizer(
            ollama_url=f"http://{self.config.llm.ollama_host}",
            model=self.config.llm.synthesis_model,
            enable_thinking=True  # Always enable thinking in explore mode
        )
        
        # Session management
        self.current_session: Optional[ExplorationSession] = None
        
    def start_exploration_session(self) -> bool:
        """Start a new exploration session."""
        
        # Check if we should restart the model for optimal thinking
        model_restart_needed = self._check_model_restart_needed()
        if model_restart_needed:
            if not self._handle_model_restart():
                print("⚠️  Continuing with current model (quality may be reduced)")
        
        if not self.synthesizer.is_available():
            print("❌ LLM service unavailable. Please check Ollama is running.")
            return False
            
        session_id = f"explore_{int(time.time())}"
        self.current_session = ExplorationSession(
            project_path=self.project_path,
            conversation_history=[],
            session_id=session_id,
            started_at=time.time()
        )
        
        print("🧠 EXPLORATION MODE STARTED")
        print("=" * 50)
        print(f"Project: {self.project_path.name}")
        print(f"Session: {session_id}")
        print("\n🎯 This mode uses thinking and remembers context.")
        print("   Perfect for debugging, learning, and deep exploration.")
        print("\n💡 Tips:")
        print("   • Ask follow-up questions - I'll remember our conversation")
        print("   • Use 'why', 'how', 'explain' for detailed reasoning")
        print("   • Type 'quit' or 'exit' to end session")
        print("\n" + "=" * 50)
        
        return True
    
    def explore_question(self, question: str, context_limit: int = 10) -> Optional[str]:
        """Explore a question with full thinking and context."""
        if not self.current_session:
            return "❌ No exploration session active. Start one first."
            
        # Search for relevant information
        search_start = time.time()
        results = self.searcher.search(
            question, 
            limit=context_limit,
            include_context=True,
            semantic_weight=0.7,
            bm25_weight=0.3
        )
        search_time = time.time() - search_start
        
        # Build enhanced prompt with conversation context
        synthesis_prompt = self._build_contextual_prompt(question, results)
        
        # Get thinking-enabled analysis
        synthesis_start = time.time()
        synthesis = self._synthesize_with_context(synthesis_prompt, results)
        synthesis_time = time.time() - synthesis_start
        
        # Add to conversation history
        self.current_session.add_exchange(question, results, synthesis)
        
        # Format response with exploration context
        response = self._format_exploration_response(
            question, synthesis, len(results), search_time, synthesis_time
        )
        
        return response
    
    def _build_contextual_prompt(self, question: str, results: List[Any]) -> str:
        """Build a prompt that includes conversation context."""
        # Get recent conversation context (last 3 exchanges)
        context_summary = ""
        if self.current_session.conversation_history:
            recent_exchanges = self.current_session.conversation_history[-3:]
            context_parts = []
            
            for i, exchange in enumerate(recent_exchanges, 1):
                prev_q = exchange["question"]
                prev_summary = exchange["response"]["summary"]
                context_parts.append(f"Previous Q{i}: {prev_q}")
                context_parts.append(f"Previous A{i}: {prev_summary}")
            
            context_summary = "\n".join(context_parts)
        
        # Build search results context
        results_context = []
        for i, result in enumerate(results[:8], 1):
            file_path = result.file_path if hasattr(result, 'file_path') else 'unknown'
            content = result.content if hasattr(result, 'content') else str(result)
            score = result.score if hasattr(result, 'score') else 0.0
            
            results_context.append(f"""
Result {i} (Score: {score:.3f}):
File: {file_path}
Content: {content[:800]}{'...' if len(content) > 800 else ''}
""")
        
        results_text = "\n".join(results_context)
        
        # Create comprehensive exploration prompt
        prompt = f"""You are a senior software engineer helping explore and debug code. You have access to thinking mode and conversation context.

PROJECT: {self.project_path.name}

CONVERSATION CONTEXT:
{context_summary}

CURRENT QUESTION: "{question}"

SEARCH RESULTS:
{results_text}

Please provide a detailed analysis in JSON format. Think through the problem carefully and consider the conversation context:

{{
    "summary": "2-3 sentences explaining what you found and how it relates to the question",
    "key_points": [
        "Important insight 1 (reference specific code/files)",
        "Important insight 2 (explain relationships)", 
        "Important insight 3 (consider conversation context)"
    ],
    "code_examples": [
        "Relevant code snippet or pattern with explanation",
        "Another important code example with context"
    ],
    "suggested_actions": [
        "Specific next step the developer should take",
        "Follow-up investigation or debugging approach",
        "Potential improvements or fixes"
    ],
    "confidence": 0.85
}}

Focus on:
- Deep technical analysis with reasoning
- How this connects to previous questions in our conversation
- Practical debugging/learning insights
- Specific code references and explanations
- Clear next steps for the developer

Think carefully about the relationships between code components and how they answer the question in context."""

        return prompt
    
    def _synthesize_with_context(self, prompt: str, results: List[Any]) -> SynthesisResult:
        """Synthesize results with full context and thinking."""
        try:
            # Use thinking-enabled synthesis with lower temperature for exploration
            response = self.synthesizer._call_ollama(prompt, temperature=0.2)
            
            if not response:
                return SynthesisResult(
                    summary="Analysis unavailable (LLM service error)",
                    key_points=[],
                    code_examples=[],
                    suggested_actions=["Check LLM service status"],
                    confidence=0.0
                )
            
            # Parse the structured response
            try:
                # Extract JSON from response
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    data = json.loads(json_str)
                    
                    return SynthesisResult(
                        summary=data.get('summary', 'Analysis completed'),
                        key_points=data.get('key_points', []),
                        code_examples=data.get('code_examples', []),
                        suggested_actions=data.get('suggested_actions', []),
                        confidence=float(data.get('confidence', 0.7))
                    )
                else:
                    # Fallback: use raw response as summary
                    return SynthesisResult(
                        summary=response[:400] + '...' if len(response) > 400 else response,
                        key_points=[],
                        code_examples=[],
                        suggested_actions=[],
                        confidence=0.5
                    )
                    
            except json.JSONDecodeError:
                return SynthesisResult(
                    summary="Analysis completed but format parsing failed",
                    key_points=[],
                    code_examples=[],
                    suggested_actions=["Try rephrasing your question"],
                    confidence=0.3
                )
                
        except Exception as e:
            logger.error(f"Context synthesis failed: {e}")
            return SynthesisResult(
                summary="Analysis failed due to service error",
                key_points=[],
                code_examples=[],
                suggested_actions=["Check system status and try again"],
                confidence=0.0
            )
    
    def _format_exploration_response(self, question: str, synthesis: SynthesisResult, 
                                   result_count: int, search_time: float, synthesis_time: float) -> str:
        """Format exploration response with context indicators."""
        
        output = []
        
        # Header with session context
        session_duration = time.time() - self.current_session.started_at
        exchange_count = len(self.current_session.conversation_history)
        
        output.append(f"🧠 EXPLORATION ANALYSIS (Question #{exchange_count})")
        output.append(f"Session: {session_duration/60:.1f}m | Results: {result_count} | "
                     f"Time: {search_time+synthesis_time:.1f}s")
        output.append("=" * 60)
        output.append("")
        
        # Main analysis
        output.append(f"📝 Analysis:")
        output.append(f"   {synthesis.summary}")
        output.append("")
        
        if synthesis.key_points:
            output.append("🔍 Key Insights:")
            for point in synthesis.key_points:
                output.append(f"   • {point}")
            output.append("")
        
        if synthesis.code_examples:
            output.append("💡 Code Examples:")
            for example in synthesis.code_examples:
                output.append(f"   {example}")
            output.append("")
        
        if synthesis.suggested_actions:
            output.append("🎯 Next Steps:")
            for action in synthesis.suggested_actions:
                output.append(f"   • {action}")
            output.append("")
        
        # Confidence and context indicator
        confidence_emoji = "🟢" if synthesis.confidence > 0.7 else "🟡" if synthesis.confidence > 0.4 else "🔴"
        context_indicator = f" | Context: {exchange_count-1} previous questions" if exchange_count > 1 else ""
        output.append(f"{confidence_emoji} Confidence: {synthesis.confidence:.1%}{context_indicator}")
        
        return "\n".join(output)
    
    def get_session_summary(self) -> str:
        """Get a summary of the current exploration session."""
        if not self.current_session:
            return "No active exploration session."
            
        duration = time.time() - self.current_session.started_at
        exchange_count = len(self.current_session.conversation_history)
        
        summary = [
            f"🧠 EXPLORATION SESSION SUMMARY",
            f"=" * 40,
            f"Project: {self.project_path.name}",
            f"Session ID: {self.current_session.session_id}",
            f"Duration: {duration/60:.1f} minutes",
            f"Questions explored: {exchange_count}",
            f"",
        ]
        
        if exchange_count > 0:
            summary.append("📋 Topics explored:")
            for i, exchange in enumerate(self.current_session.conversation_history, 1):
                question = exchange["question"][:50] + "..." if len(exchange["question"]) > 50 else exchange["question"]
                confidence = exchange["response"]["confidence"]
                summary.append(f"   {i}. {question} (confidence: {confidence:.1%})")
        
        return "\n".join(summary)
    
    def end_session(self) -> str:
        """End the current exploration session."""
        if not self.current_session:
            return "No active session to end."
            
        summary = self.get_session_summary()
        self.current_session = None
        
        return summary + "\n\n✅ Exploration session ended."
    
    def _check_model_restart_needed(self) -> bool:
        """Check if model restart would improve thinking quality."""
        try:
            # Simple heuristic: if we can detect the model was recently used 
            # with <no_think>, suggest restart for better thinking quality
            
            # Test with a simple thinking prompt to see response quality
            test_response = self.synthesizer._call_ollama(
                "Think briefly: what is 2+2?", 
                temperature=0.1, 
                disable_thinking=False
            )
            
            if test_response:
                # If response is suspiciously short or shows signs of no-think behavior
                if len(test_response.strip()) < 10 or "4" == test_response.strip():
                    return True
                    
        except Exception:
            pass
            
        return False
    
    def _handle_model_restart(self) -> bool:
        """Handle user confirmation and model restart."""
        try:
            print("\n🤔 To ensure best thinking quality, exploration mode works best with a fresh model.")
            print(f"   Currently running: {self.synthesizer.model}")
            print("\n💡 Stop current model and restart for optimal exploration? (y/N): ", end="", flush=True)
            
            response = input().strip().lower()
            
            if response in ['y', 'yes']:
                print("\n🔄 Stopping current model...")
                
                # Use ollama stop command for clean model restart
                import subprocess
                try:
                    subprocess.run([
                        "ollama", "stop", self.synthesizer.model
                    ], timeout=10, capture_output=True)
                    
                    print("✅ Model stopped successfully.")
                    print("🚀 Exploration mode will restart the model with thinking enabled...")
                    
                    # Reset synthesizer initialization to force fresh start
                    self.synthesizer._initialized = False
                    return True
                    
                except subprocess.TimeoutExpired:
                    print("⚠️  Model stop timed out, continuing anyway...")
                    return False
                except FileNotFoundError:
                    print("⚠️  'ollama' command not found, continuing with current model...")
                    return False
                except Exception as e:
                    print(f"⚠️  Error stopping model: {e}")
                    return False
            else:
                print("📝 Continuing with current model...")
                return False
                
        except KeyboardInterrupt:
            print("\n📝 Continuing with current model...")
            return False
        except EOFError:
            print("\n📝 Continuing with current model...")
            return False

# Quick test function
def test_explorer():
    """Test the code explorer."""
    explorer = CodeExplorer(Path("."))
    
    if not explorer.start_exploration_session():
        print("❌ Could not start exploration session")
        return
        
    # Test question
    response = explorer.explore_question("How does authentication work in this codebase?")
    if response:
        print(response)
        
    print("\n" + explorer.end_session())

if __name__ == "__main__":
    test_explorer()
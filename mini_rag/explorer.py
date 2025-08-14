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
            enable_thinking=True,  # Always enable thinking in explore mode
            config=self.config  # Pass config for model rankings
        )
        
        # Session management
        self.current_session: Optional[ExplorationSession] = None
        
    def start_exploration_session(self) -> bool:
        """Start a new exploration session."""
        
        # Simple availability check - don't do complex model restart logic
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
        
        print("🧠 Exploration Mode Started")
        print(f"Project: {self.project_path.name}")
        
        return True
    
    def explore_question(self, question: str, context_limit: int = 10) -> Optional[str]:
        """Explore a question with full thinking and context."""
        if not self.current_session:
            return "❌ No exploration session active. Start one first."
            
        # Search for relevant information
        search_start = time.time()
        results = self.searcher.search(
            question, 
            top_k=context_limit,
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
        
        # Create comprehensive exploration prompt with thinking
        prompt = f"""<think>
The user asked: "{question}"

Let me analyze what they're asking and look at the information I have available.

From the search results, I can see relevant information about:
{results_text[:500]}...

I should think about:
1. What the user is trying to understand or accomplish
2. What information from the search results is most relevant
3. How to explain this in a clear, educational way
4. What practical next steps would be helpful

Based on our conversation so far: {context_summary}

Let me create a helpful response that breaks this down clearly and gives them actionable guidance.
</think>

You're a helpful assistant exploring a project with someone. You're good at breaking down complex topics into understandable pieces and explaining things clearly.

PROJECT: {self.project_path.name}

PREVIOUS CONVERSATION:
{context_summary}

CURRENT QUESTION: "{question}"

RELEVANT INFORMATION FOUND:
{results_text}

Please provide a helpful analysis in JSON format:

{{
    "summary": "Clear explanation of what you found and how it answers their question",
    "key_points": [
        "Most important insight from the information",
        "Secondary important point or relationship", 
        "Third key point or practical consideration"
    ],
    "code_examples": [
        "Relevant example or pattern from the information",
        "Another useful example or demonstration"
    ],
    "suggested_actions": [
        "Specific next step they could take",
        "Additional exploration or investigation suggestion",
        "Practical way to apply this information"
    ],
    "confidence": 0.85
}}

Guidelines:
- Be educational and break things down clearly
- Reference specific files and information when helpful
- Give practical, actionable suggestions
- Keep explanations beginner-friendly but not condescending
- Connect information to their question directly
"""
        
        return prompt
    
    def _synthesize_with_context(self, prompt: str, results: List[Any]) -> SynthesisResult:
        """Synthesize results with full context and thinking."""
        try:
            # TEMPORARILY: Use simple non-streaming call to avoid flow issues
            # TODO: Re-enable streaming once flow is stable
            response = self.synthesizer._call_ollama(prompt, temperature=0.2, disable_thinking=False)
            thinking_stream = ""
            
            # Display simple thinking indicator
            if response and len(response) > 200:
                print("\n💭 Analysis in progress...")
            
            # Don't display thinking stream again - keeping it simple for now
            
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
    
    def _call_ollama_with_thinking(self, prompt: str, temperature: float = 0.3) -> tuple:
        """Call Ollama with streaming for fast time-to-first-token."""
        import requests
        import json
        
        try:
            # Use the synthesizer's model and connection
            model_to_use = self.synthesizer.model
            if self.synthesizer.model not in self.synthesizer.available_models:
                if self.synthesizer.available_models:
                    model_to_use = self.synthesizer.available_models[0]
                else:
                    return None, None
            
            # Enable thinking by NOT adding <no_think>
            final_prompt = prompt
            
            # Get optimal parameters for this model
            from .llm_optimization import get_optimal_ollama_parameters
            optimal_params = get_optimal_ollama_parameters(model_to_use)
            
            payload = {
                "model": model_to_use,
                "prompt": final_prompt,
                "stream": True,  # Enable streaming for fast response
                "options": {
                    "temperature": temperature,
                    "top_p": optimal_params.get("top_p", 0.9),
                    "top_k": optimal_params.get("top_k", 40),
                    "num_ctx": optimal_params.get("num_ctx", 32768),
                    "num_predict": optimal_params.get("num_predict", 2000),
                    "repeat_penalty": optimal_params.get("repeat_penalty", 1.1),
                    "presence_penalty": optimal_params.get("presence_penalty", 1.0)
                }
            }
            
            response = requests.post(
                f"{self.synthesizer.ollama_url}/api/generate",
                json=payload,
                stream=True,
                timeout=65
            )
            
            if response.status_code == 200:
                # Collect streaming response
                raw_response = ""
                thinking_displayed = False
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line.decode('utf-8'))
                            chunk_text = chunk_data.get('response', '')
                            
                            if chunk_text:
                                raw_response += chunk_text
                                
                                # Display thinking stream as it comes in
                                if not thinking_displayed and '<think>' in raw_response:
                                    # Start displaying thinking
                                    self._start_thinking_display()
                                    thinking_displayed = True
                                
                                if thinking_displayed:
                                    self._stream_thinking_chunk(chunk_text)
                                
                            if chunk_data.get('done', False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Finish thinking display if it was shown
                if thinking_displayed:
                    self._end_thinking_display()
                
                # Extract thinking stream and final response
                thinking_stream, final_response = self._extract_thinking(raw_response)
                
                return final_response, thinking_stream
            else:
                return None, None
                
        except Exception as e:
            logger.error(f"Thinking-enabled Ollama call failed: {e}")
            return None, None
    
    def _extract_thinking(self, raw_response: str) -> tuple:
        """Extract thinking content from response."""
        thinking_stream = ""
        final_response = raw_response
        
        # Look for thinking patterns
        if "<think>" in raw_response and "</think>" in raw_response:
            # Extract thinking content between tags
            start_tag = raw_response.find("<think>")
            end_tag = raw_response.find("</think>") + len("</think>")
            
            if start_tag != -1 and end_tag != -1:
                thinking_content = raw_response[start_tag + 7:end_tag - 8]  # Remove tags
                thinking_stream = thinking_content.strip()
                
                # Remove thinking from final response
                final_response = (raw_response[:start_tag] + raw_response[end_tag:]).strip()
        
        # Alternative patterns for models that use different thinking formats
        elif "Let me think" in raw_response or "I need to analyze" in raw_response:
            # Simple heuristic: first paragraph might be thinking
            lines = raw_response.split('\n')
            potential_thinking = []
            final_lines = []
            
            thinking_indicators = ["Let me think", "I need to", "First, I'll", "Looking at", "Analyzing"]
            in_thinking = False
            
            for line in lines:
                if any(indicator in line for indicator in thinking_indicators):
                    in_thinking = True
                    potential_thinking.append(line)
                elif in_thinking and (line.startswith('{') or line.startswith('**') or line.startswith('#')):
                    # Likely end of thinking, start of structured response
                    in_thinking = False
                    final_lines.append(line)
                elif in_thinking:
                    potential_thinking.append(line)
                else:
                    final_lines.append(line)
            
            if potential_thinking:
                thinking_stream = '\n'.join(potential_thinking).strip()
                final_response = '\n'.join(final_lines).strip()
        
        return thinking_stream, final_response
    
    def _start_thinking_display(self):
        """Start the thinking stream display."""
        print("\n\033[2m\033[3m💭 AI Thinking:\033[0m")
        print("\033[2m\033[3m" + "─" * 40 + "\033[0m")
        self._thinking_buffer = ""
        self._in_thinking_tags = False
    
    def _stream_thinking_chunk(self, chunk: str):
        """Stream a chunk of thinking as it arrives."""
        import sys
        
        self._thinking_buffer += chunk
        
        # Check if we're in thinking tags
        if '<think>' in self._thinking_buffer and not self._in_thinking_tags:
            self._in_thinking_tags = True
            # Display everything after <think>
            start_idx = self._thinking_buffer.find('<think>') + 7
            thinking_content = self._thinking_buffer[start_idx:]
            if thinking_content:
                print(f"\033[2m\033[3m{thinking_content}\033[0m", end='', flush=True)
        elif self._in_thinking_tags and '</think>' not in chunk:
            # We're in thinking mode, display the chunk
            print(f"\033[2m\033[3m{chunk}\033[0m", end='', flush=True)
        elif '</think>' in self._thinking_buffer:
            # End of thinking
            self._in_thinking_tags = False
    
    def _end_thinking_display(self):
        """End the thinking stream display."""
        print(f"\n\033[2m\033[3m" + "─" * 40 + "\033[0m")
        print()
    
    def _display_thinking_stream(self, thinking_stream: str):
        """Display thinking stream in light gray and italic (fallback for non-streaming)."""
        if not thinking_stream:
            return
            
        print("\n\033[2m\033[3m💭 AI Thinking:\033[0m")
        print("\033[2m\033[3m" + "─" * 40 + "\033[0m")
        
        # Split into paragraphs and display with proper formatting
        paragraphs = thinking_stream.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Wrap long lines nicely
                lines = para.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # Light gray and italic
                        print(f"\033[2m\033[3m{line}\033[0m")
                print()  # Paragraph spacing
        
        print("\033[2m\033[3m" + "─" * 40 + "\033[0m")
        print()

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
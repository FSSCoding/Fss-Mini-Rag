#!/usr/bin/env python3
"""
LLM Safeguards for Small Model Management

Provides runaway prevention, context management, and intelligent detection
of problematic model behaviors to ensure reliable user experience.
"""

import re
import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SafeguardConfig:
    """Configuration for LLM safeguards - gentle and educational."""
    max_output_tokens: int = 4000        # Allow longer responses for learning
    max_repetition_ratio: float = 0.7    # Be very permissive - only catch extreme repetition
    max_response_time: int = 120         # Allow 2 minutes for complex thinking
    min_useful_length: int = 10          # Lower threshold - short answers can be useful
    context_window: int = 32000          # Match Qwen3 context length (32K token limit)
    enable_thinking_detection: bool = True  # Detect thinking patterns
    
class ModelRunawayDetector:
    """Detects and prevents model runaway behaviors."""
    
    def __init__(self, config: SafeguardConfig = None):
        self.config = config or SafeguardConfig()
        self.response_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for runaway detection."""
        return {
            # Excessive repetition patterns
            'word_repetition': re.compile(r'\b(\w+)\b(?:\s+\1\b){3,}', re.IGNORECASE),
            'phrase_repetition': re.compile(r'(.{10,50}?)\1{2,}', re.DOTALL),
            
            # Thinking loop patterns (small models get stuck)
            'thinking_loop': re.compile(r'(let me think|i think|thinking|consider|actually|wait|hmm|well)\s*[.,:]*\s*\1', re.IGNORECASE),
            
            # Rambling patterns
            'excessive_filler': re.compile(r'\b(um|uh|well|you know|like|basically|actually|so|then|and|but|however)\b(?:\s+[^.!?]*){5,}', re.IGNORECASE),
            
            # JSON corruption patterns
            'broken_json': re.compile(r'\{[^}]*\{[^}]*\{'),  # Nested broken JSON
            'json_repetition': re.compile(r'("[\w_]+"\s*:\s*"[^"]*",?\s*){4,}'),  # Repeated JSON fields
        }
    
    def check_response_quality(self, response: str, query: str, start_time: float) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check response quality and detect runaway behaviors.
        
        Returns:
            (is_valid, issue_type, user_explanation)
        """
        if not response or len(response.strip()) < self.config.min_useful_length:
            return False, "too_short", self._explain_too_short()
        
        # Check response time
        elapsed = time.time() - start_time
        if elapsed > self.config.max_response_time:
            return False, "timeout", self._explain_timeout()
        
        # Check for repetition issues
        repetition_issue = self._check_repetition(response)
        if repetition_issue:
            return False, repetition_issue, self._explain_repetition(repetition_issue)
        
        # Check for thinking loops
        if self.config.enable_thinking_detection:
            thinking_issue = self._check_thinking_loops(response)
            if thinking_issue:
                return False, thinking_issue, self._explain_thinking_loop()
        
        # Check for rambling
        rambling_issue = self._check_rambling(response)
        if rambling_issue:
            return False, rambling_issue, self._explain_rambling()
        
        # Check JSON corruption (for structured responses)
        if '{' in response and '}' in response:
            json_issue = self._check_json_corruption(response)
            if json_issue:
                return False, json_issue, self._explain_json_corruption()
        
        return True, None, None
    
    def _check_repetition(self, response: str) -> Optional[str]:
        """Check for excessive repetition."""
        # Word repetition
        if self.response_patterns['word_repetition'].search(response):
            return "word_repetition"
        
        # Phrase repetition  
        if self.response_patterns['phrase_repetition'].search(response):
            return "phrase_repetition"
        
        # Calculate repetition ratio (excluding Qwen3 thinking blocks)
        analysis_text = response
        if "<think>" in response and "</think>" in response:
            # Extract only the actual response (after thinking) for repetition analysis
            thinking_end = response.find("</think>")
            if thinking_end != -1:
                analysis_text = response[thinking_end + 8:].strip()
                
                # If the actual response (excluding thinking) is short, don't penalize
                if len(analysis_text.split()) < 20:
                    return None
        
        words = analysis_text.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            if repetition_ratio > self.config.max_repetition_ratio:
                return "high_repetition_ratio"
        
        return None
    
    def _check_thinking_loops(self, response: str) -> Optional[str]:
        """Check for thinking loops (common in small models)."""
        if self.response_patterns['thinking_loop'].search(response):
            return "thinking_loop"
        
        # Check for excessive meta-commentary
        thinking_words = ['think', 'considering', 'actually', 'wait', 'hmm', 'let me']
        thinking_count = sum(response.lower().count(word) for word in thinking_words)
        
        if thinking_count > 5 and len(response.split()) < 200:
            return "excessive_thinking"
        
        return None
    
    def _check_rambling(self, response: str) -> Optional[str]:
        """Check for rambling or excessive filler."""
        if self.response_patterns['excessive_filler'].search(response):
            return "excessive_filler"
        
        # Check for extremely long sentences (sign of rambling)
        sentences = re.split(r'[.!?]+', response)
        long_sentences = [s for s in sentences if len(s.split()) > 50]
        
        if len(long_sentences) > 2:
            return "excessive_rambling"
        
        return None
    
    def _check_json_corruption(self, response: str) -> Optional[str]:
        """Check for JSON corruption in structured responses."""
        if self.response_patterns['broken_json'].search(response):
            return "broken_json"
        
        if self.response_patterns['json_repetition'].search(response):
            return "json_repetition"
        
        return None
    
    def _explain_too_short(self) -> str:
        return """🤔 The AI response was too short to be helpful.

**Why this happens:**
• The model might be confused by the query
• Context might be insufficient  
• Model might be overloaded

**What to try:**
• Rephrase your question more specifically
• Try a broader search term first
• Use exploration mode for complex questions: `rag-mini explore`"""

    def _explain_timeout(self) -> str:
        return """⏱️ The AI took too long to respond (over 60 seconds).

**Why this happens:**
• Small models sometimes get "stuck" thinking
• Complex queries can overwhelm smaller models
• System might be under load

**What to try:**
• Try a simpler, more direct question
• Use synthesis mode for faster responses: `--synthesize`  
• Consider using a larger model if available"""

    def _explain_repetition(self, issue_type: str) -> str:
        return f"""🔄 The AI got stuck in repetition loops ({issue_type}).

**Why this happens:**
• Small models sometimes repeat when uncertain
• Query might be too complex for the model size
• Context window might be exceeded

**What to try:**
• Try a more specific question
• Break complex questions into smaller parts
• Use exploration mode which handles context better: `rag-mini explore`
• Consider: A larger model (qwen3:1.7b or qwen3:3b) would help"""

    def _explain_thinking_loop(self) -> str:
        return """🧠 The AI got caught in a "thinking loop" - overthinking the response.

**Why this happens:**
• Small models sometimes over-analyze simple questions
• Thinking mode can cause loops in smaller models
• Query complexity exceeds model capabilities

**What to try:**
• Ask more direct, specific questions
• Use synthesis mode (no thinking) for faster results
• Try: "What does this code do?" instead of "Explain how this works"
• Larger models (qwen3:1.7b+) handle thinking better"""

    def _explain_rambling(self) -> str:
        return """💭 The AI started rambling instead of giving focused answers.

**Why this happens:**
• Small models sometimes lose focus on complex topics
• Query might be too broad or vague  
• Model trying to cover too much at once

**What to try:**
• Ask more specific questions
• Break broad questions into focused parts
• Example: "How is data validated?" instead of "Explain the whole system"
• Exploration mode helps maintain focus across questions"""

    def _explain_json_corruption(self) -> str:
        return """🔧 The AI response format got corrupted.

**Why this happens:**
• Small models sometimes struggle with structured output
• Context limits can cause format errors
• Complex analysis might overwhelm formatting

**What to try:**  
• Try the question again (often resolves itself)
• Use simpler questions for better formatting
• Synthesis mode sometimes gives cleaner output
• This is less common with larger models"""

    def get_recovery_suggestions(self, issue_type: str, query: str) -> List[str]:
        """Get specific recovery suggestions based on the issue."""
        suggestions = []
        
        if issue_type in ['thinking_loop', 'excessive_thinking']:
            suggestions.extend([
                f"Try synthesis mode: `rag-mini search . \"{query}\" --synthesize`",
                "Ask more direct questions without 'why' or 'how'",
                "Break complex questions into smaller parts"
            ])
        
        elif issue_type in ['word_repetition', 'phrase_repetition', 'high_repetition_ratio']:
            suggestions.extend([
                "Try rephrasing your question completely",
                "Use more specific technical terms",  
                f"Try exploration mode: `rag-mini explore .`"
            ])
        
        elif issue_type == 'timeout':
            suggestions.extend([
                "Try a simpler version of your question",
                "Use synthesis mode for faster responses",
                "Check if Ollama is under heavy load"
            ])
        
        # Universal suggestions
        suggestions.extend([
            "Consider using a larger model if available (qwen3:1.7b or qwen3:3b)",
            "Check model status: `ollama list`"
        ])
        
        return suggestions

def get_optimal_ollama_parameters(model_name: str) -> Dict[str, any]:
    """Get optimal parameters for different Ollama models."""
    
    base_params = {
        "num_ctx": 32768,      # Good context window for most uses
        "num_predict": 2000,   # Reasonable response length
        "temperature": 0.3,    # Balanced creativity/consistency
    }
    
    # Model-specific optimizations
    if "qwen3:0.6b" in model_name.lower():
        return {
            **base_params,
            "repeat_penalty": 1.15,      # Prevent repetition in small model
            "presence_penalty": 1.5,     # Suppress repetitive outputs 
            "top_p": 0.8,               # Focused sampling
            "top_k": 20,                # Limit choices
            "num_predict": 1500,        # Shorter responses for reliability
        }
    
    elif "qwen3:1.7b" in model_name.lower():
        return {
            **base_params,
            "repeat_penalty": 1.1,       # Less aggressive for larger model
            "presence_penalty": 1.0,     # Balanced
            "top_p": 0.9,               # More creative
            "top_k": 40,                # More choices
        }
    
    elif any(size in model_name.lower() for size in ["3b", "7b", "8b"]):
        return {
            **base_params,
            "repeat_penalty": 1.05,      # Minimal for larger models
            "presence_penalty": 0.5,     # Light touch
            "top_p": 0.95,              # High creativity
            "top_k": 50,                # Many choices
            "num_predict": 3000,        # Longer responses OK
        }
    
    return base_params

# Quick test
def test_safeguards():
    """Test the safeguard system."""
    detector = ModelRunawayDetector()
    
    # Test repetition detection
    bad_response = "The user authentication system works by checking user credentials. The user authentication system works by checking user credentials. The user authentication system works by checking user credentials."
    
    is_valid, issue, explanation = detector.check_response_quality(bad_response, "auth", time.time())
    
    print(f"Repetition test: Valid={is_valid}, Issue={issue}")
    if explanation:
        print(explanation)

if __name__ == "__main__":
    test_safeguards()
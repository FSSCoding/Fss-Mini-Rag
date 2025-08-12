#!/usr/bin/env python3
"""
LLM Synthesizer for RAG Results

Provides intelligent synthesis of search results using Ollama LLMs.
Takes raw search results and generates coherent, contextual summaries.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SynthesisResult:
    """Result of LLM synthesis."""
    summary: str
    key_points: List[str]
    code_examples: List[str]
    suggested_actions: List[str]
    confidence: float

class LLMSynthesizer:
    """Synthesizes RAG search results using Ollama LLMs."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = None):
        self.ollama_url = ollama_url.rstrip('/')
        self.available_models = self._get_available_models()
        self.model = model or self._select_best_model()
        
    def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
        return []
    
    def _select_best_model(self) -> str:
        """Select the best available model based on modern performance rankings."""
        if not self.available_models:
            return "qwen2.5:1.5b"  # Fallback preference
        
        # Modern model preference ranking (best to acceptable)
        # Prioritize: Qwen3 > Qwen2.5 > Mistral > Llama3.2 > Others
        model_rankings = [
            # Qwen3 models (newest, most efficient) - prefer standard versions
            "qwen3:1.7b", "qwen3:0.6b", "qwen3:4b", "qwen3:8b",
            
            # Qwen2.5 models (excellent performance/size ratio)
            "qwen2.5-coder:1.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5-coder:3b",
            "qwen2.5:7b", "qwen2.5-coder:7b",
            
            # Qwen2 models (older but still good)
            "qwen2:1.5b", "qwen2:3b", "qwen2:7b",
            
            # Mistral models (good quality, reasonable size)
            "mistral:7b", "mistral-nemo", "mistral-small",
            
            # Llama3.2 models (decent but larger)
            "llama3.2:1b", "llama3.2:3b", "llama3.2", "llama3.2:8b",
            
            # Fallback to other Llama models
            "llama3.1:8b", "llama3:8b", "llama3", 
            
            # Other decent models
            "gemma2:2b", "gemma2:9b", "phi3:3.8b", "phi3.5",
        ]
        
        # Find first available model from our ranked list
        for preferred_model in model_rankings:
            for available_model in self.available_models:
                # Match model names (handle version tags)
                available_base = available_model.split(':')[0].lower()
                preferred_base = preferred_model.split(':')[0].lower()
                
                if preferred_base in available_base or available_base in preferred_base:
                    # Additional size filtering - prefer smaller models
                    if any(size in available_model.lower() for size in ['1b', '1.5b', '2b', '3b']):
                        logger.info(f"Selected efficient model: {available_model}")
                        return available_model
                    elif any(size in available_model.lower() for size in ['7b', '8b']):
                        # Only use larger models if no smaller ones available
                        logger.info(f"Selected larger model: {available_model}")
                        return available_model
                    elif ':' not in available_model:
                        # Handle models without explicit size tags
                        return available_model
        
        # If no preferred models found, use first available
        fallback = self.available_models[0]
        logger.warning(f"Using fallback model: {fallback}")
        return fallback
    
    def is_available(self) -> bool:
        """Check if Ollama is available and has models."""
        return len(self.available_models) > 0
    
    def _call_ollama(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Make a call to Ollama API."""
        try:
            # Use the best available model
            model_to_use = self.model
            if self.model not in self.available_models:
                # Fallback to first available model
                if self.available_models:
                    model_to_use = self.available_models[0]
                else:
                    logger.error("No Ollama models available")
                    return None
                    
            payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None
    
    def synthesize_search_results(self, query: str, results: List[Any], project_path: Path) -> SynthesisResult:
        """Synthesize search results into a coherent summary."""
        
        if not self.is_available():
            return SynthesisResult(
                summary="LLM synthesis unavailable (Ollama not running or no models)",
                key_points=[],
                code_examples=[],
                suggested_actions=["Install and run Ollama with a model"],
                confidence=0.0
            )
        
        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(results[:8], 1):  # Limit to top 8 results
            file_path = result.file_path if hasattr(result, 'file_path') else 'unknown'
            content = result.content if hasattr(result, 'content') else str(result)
            score = result.score if hasattr(result, 'score') else 0.0
            
            context_parts.append(f"""
Result {i} (Score: {score:.3f}):
File: {file_path}
Content: {content[:500]}{'...' if len(content) > 500 else ''}
""")
        
        context = "\n".join(context_parts)
        
        # Create synthesis prompt
        prompt = f"""You are a senior software engineer analyzing code search results. Your task is to synthesize the search results into a helpful, actionable summary.

SEARCH QUERY: "{query}"
PROJECT: {project_path.name}

SEARCH RESULTS:
{context}

Please provide a synthesis in the following JSON format:
{{
    "summary": "A 2-3 sentence overview of what the search results show",
    "key_points": [
        "Important finding 1",
        "Important finding 2", 
        "Important finding 3"
    ],
    "code_examples": [
        "Relevant code snippet or pattern from the results",
        "Another important code example"
    ],
    "suggested_actions": [
        "What the developer should do next",
        "Additional recommendations"
    ],
    "confidence": 0.85
}}

Focus on:
- What the code does and how it works
- Patterns and relationships between the results
- Practical next steps for the developer
- Code quality observations

Respond with ONLY the JSON, no other text."""

        # Get LLM response
        response = self._call_ollama(prompt, temperature=0.2)
        
        if not response:
            return SynthesisResult(
                summary="LLM synthesis failed (API error)",
                key_points=[],
                code_examples=[],
                suggested_actions=["Check Ollama status and try again"],
                confidence=0.0
            )
        
        # Parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                return SynthesisResult(
                    summary=data.get('summary', 'No summary generated'),
                    key_points=data.get('key_points', []),
                    code_examples=data.get('code_examples', []),
                    suggested_actions=data.get('suggested_actions', []),
                    confidence=float(data.get('confidence', 0.5))
                )
            else:
                # Fallback: use the raw response as summary
                return SynthesisResult(
                    summary=response[:300] + '...' if len(response) > 300 else response,
                    key_points=[],
                    code_examples=[],
                    suggested_actions=[],
                    confidence=0.3
                )
                
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return SynthesisResult(
                summary="LLM synthesis failed (JSON parsing error)",
                key_points=[],
                code_examples=[],
                suggested_actions=["Try the search again or check LLM output"],
                confidence=0.0
            )
    
    def format_synthesis_output(self, synthesis: SynthesisResult, query: str) -> str:
        """Format synthesis result for display."""
        
        output = []
        output.append("🧠 LLM SYNTHESIS")
        output.append("=" * 50)
        output.append("")
        
        output.append(f"📝 Summary:")
        output.append(f"   {synthesis.summary}")
        output.append("")
        
        if synthesis.key_points:
            output.append("🔍 Key Findings:")
            for point in synthesis.key_points:
                output.append(f"   • {point}")
            output.append("")
        
        if synthesis.code_examples:
            output.append("💡 Code Patterns:")
            for example in synthesis.code_examples:
                output.append(f"   {example}")
            output.append("")
        
        if synthesis.suggested_actions:
            output.append("🎯 Suggested Actions:")
            for action in synthesis.suggested_actions:
                output.append(f"   • {action}")
            output.append("")
        
        confidence_emoji = "🟢" if synthesis.confidence > 0.7 else "🟡" if synthesis.confidence > 0.4 else "🔴"
        output.append(f"{confidence_emoji} Confidence: {synthesis.confidence:.1%}")
        output.append("")
        
        return "\n".join(output)

# Quick test function
def test_synthesizer():
    """Test the synthesizer with sample data."""
    from dataclasses import dataclass
    
    @dataclass 
    class MockResult:
        file_path: str
        content: str
        score: float
    
    synthesizer = LLMSynthesizer()
    
    if not synthesizer.is_available():
        print("❌ Ollama not available for testing")
        return
    
    # Mock search results
    results = [
        MockResult("auth.py", "def authenticate_user(username, password):\n    return verify_credentials(username, password)", 0.95),
        MockResult("models.py", "class User:\n    def login(self):\n        return authenticate_user(self.username, self.password)", 0.87)
    ]
    
    synthesis = synthesizer.synthesize_search_results(
        "user authentication", 
        results, 
        Path("/test/project")
    )
    
    print(synthesizer.format_synthesis_output(synthesis, "user authentication"))

if __name__ == "__main__":
    test_synthesizer()
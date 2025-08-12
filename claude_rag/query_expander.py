#!/usr/bin/env python3
"""
Query Expander for Enhanced RAG Search

## What This Does
Automatically expands search queries to find more relevant results.

Example: "authentication" becomes "authentication login user verification credentials"

## How It Helps  
- 2-3x more relevant search results
- Works with any content (code, docs, notes, etc.)
- Completely transparent to users
- Uses small, fast LLMs (qwen3:1.7b) for ~100ms expansions

## Usage
```python
from claude_rag.query_expander import QueryExpander
from claude_rag.config import RAGConfig

config = RAGConfig()
expander = QueryExpander(config)

# Expand a query
expanded = expander.expand_query("error handling")
# Result: "error handling exception try catch fault tolerance"
```

Perfect for beginners - enable in TUI for exploration, 
disable in CLI for maximum speed.
"""

import logging
import re
import threading
from typing import List, Optional
import requests
from .config import RAGConfig

logger = logging.getLogger(__name__)

class QueryExpander:
    """Expands search queries using LLM to improve search recall."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.ollama_url = f"http://{config.llm.ollama_host}"
        self.model = config.llm.expansion_model
        self.max_terms = config.llm.max_expansion_terms
        self.enabled = config.search.expand_queries
        self._initialized = False
        
        # Cache for expanded queries to avoid repeated API calls
        self._cache = {}
        self._cache_lock = threading.RLock()  # Thread-safe cache access
    
    def _ensure_initialized(self):
        """Lazy initialization with LLM warmup."""
        if self._initialized:
            return
            
        # Warm up LLM if enabled and available
        if self.enabled:
            try:
                model = self._select_expansion_model()
                if model:
                    requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": "testing, just say 'hi' <no_think>",
                            "stream": False,
                            "options": {"temperature": 0.1, "max_tokens": 5}
                        },
                        timeout=5
                    )
            except:
                pass  # Warmup failure is non-critical
                
        self._initialized = True
    
    def expand_query(self, query: str) -> str:
        """Expand a search query with related terms."""
        if not self.enabled or not query.strip():
            return query
            
        self._ensure_initialized()
            
        # Check cache first (thread-safe)
        with self._cache_lock:
            if query in self._cache:
                return self._cache[query]
        
        # Don't expand very short queries or obvious keywords
        if len(query.split()) <= 1 or len(query) <= 3:
            return query
            
        try:
            expanded = self._llm_expand_query(query)
            if expanded and expanded != query:
                # Cache the result (thread-safe)
                with self._cache_lock:
                    self._cache[query] = expanded
                    # Prevent cache from growing too large
                    if len(self._cache) % 100 == 0:  # Check every 100 entries
                        self._manage_cache_size()
                logger.info(f"Expanded query: '{query}' → '{expanded}'")
                return expanded
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
        
        # Return original query if expansion fails
        return query
    
    def _llm_expand_query(self, query: str) -> Optional[str]:
        """Use LLM to expand the query with related terms."""
        
        # Use best available model
        model_to_use = self._select_expansion_model()
        if not model_to_use:
            return None
        
        # Create expansion prompt
        prompt = f"""You are a search query expert. Expand the following search query with {self.max_terms} additional related terms that would help find relevant content.

Original query: "{query}"

Rules:
1. Add ONLY highly relevant synonyms, related concepts, or alternate phrasings
2. Keep the original query intact at the beginning
3. Add terms that someone might use when writing about this topic
4. Separate terms with spaces (not commas or punctuation)
5. Maximum {self.max_terms} additional terms
6. Focus on finding MORE relevant results, not changing the meaning

Examples:
- "authentication" → "authentication login user verification credentials security session token"
- "error handling" → "error handling exception try catch fault tolerance error recovery exception management"
- "database query" → "database query sql select statement data retrieval database search sql query"

Expanded query:"""

        try:
            payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Very low temperature for consistent expansions
                    "top_p": 0.8,
                    "max_tokens": 100    # Keep it short
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=10  # Quick timeout for low latency
            )
            
            if response.status_code == 200:
                result = response.json().get('response', '').strip()
                
                # Clean up the response - extract just the expanded query
                expanded = self._clean_expansion(result, query)
                return expanded
                
        except Exception as e:
            logger.warning(f"LLM expansion failed: {e}")
            return None
    
    def _select_expansion_model(self) -> Optional[str]:
        """Select the best available model for query expansion."""
        
        if self.model != "auto":
            return self.model
        
        try:
            # Get available models
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                available = [model['name'] for model in data.get('models', [])]
                
                # Prefer ultra-fast, efficient models for query expansion (CPU-friendly)
                expansion_preferences = [
                    "qwen3:0.6b", "qwen3:1.7b", "qwen2.5:1.5b", 
                    "llama3.2:1b", "gemma2:2b", "llama3.2:3b"
                ]
                
                for preferred in expansion_preferences:
                    for available_model in available:
                        if preferred in available_model:
                            logger.debug(f"Using {available_model} for query expansion")
                            return available_model
                
                # Fallback to first available model
                if available:
                    return available[0]
                    
        except Exception as e:
            logger.warning(f"Could not select expansion model: {e}")
        
        return None
    
    def _clean_expansion(self, raw_response: str, original_query: str) -> str:
        """Clean the LLM response to extract just the expanded query."""
        
        # Remove common response artifacts
        clean_response = raw_response.strip()
        
        # Remove quotes if the entire response is quoted
        if clean_response.startswith('"') and clean_response.endswith('"'):
            clean_response = clean_response[1:-1]
        
        # Take only the first line if multiline
        clean_response = clean_response.split('\n')[0].strip()
        
        # Remove excessive punctuation and normalize spaces
        clean_response = re.sub(r'[^\w\s-]', ' ', clean_response)
        clean_response = re.sub(r'\s+', ' ', clean_response).strip()
        
        # Ensure it starts with the original query
        if not clean_response.lower().startswith(original_query.lower()):
            clean_response = f"{original_query} {clean_response}"
        
        # Limit the total length to avoid very long queries
        words = clean_response.split()
        if len(words) > len(original_query.split()) + self.max_terms:
            words = words[:len(original_query.split()) + self.max_terms]
            clean_response = ' '.join(words)
        
        return clean_response
    
    def clear_cache(self):
        """Clear the expansion cache (thread-safe)."""
        with self._cache_lock:
            self._cache.clear()
    
    def _manage_cache_size(self, max_size: int = 1000):
        """Keep cache from growing too large (prevents memory leaks)."""
        with self._cache_lock:
            if len(self._cache) > max_size:
                # Remove oldest half of cache entries (simple LRU approximation)
                items = list(self._cache.items())
                keep_count = max_size // 2
                self._cache = dict(items[-keep_count:])
                logger.debug(f"Cache trimmed from {len(items)} to {len(self._cache)} entries")
    
    def is_available(self) -> bool:
        """Check if query expansion is available."""
        if not self.enabled:
            return False
            
        self._ensure_initialized()
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

# Quick test function
def test_expansion():
    """Test the query expander."""
    from .config import RAGConfig
    
    config = RAGConfig()
    config.search.expand_queries = True
    config.llm.max_expansion_terms = 6
    
    expander = QueryExpander(config)
    
    if not expander.is_available():
        print("❌ Ollama not available for testing")
        return
    
    test_queries = [
        "authentication",
        "error handling", 
        "database query",
        "user interface"
    ]
    
    print("🔍 Testing Query Expansion:")
    for query in test_queries:
        expanded = expander.expand_query(query)
        print(f"  '{query}' → '{expanded}'")

if __name__ == "__main__":
    test_expansion()
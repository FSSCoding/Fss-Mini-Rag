#!/usr/bin/env python3
"""
LLM Synthesizer for RAG Results

Provides intelligent synthesis of search results using Ollama LLMs.
Takes raw search results and generates coherent, contextual summaries.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import requests

try:
    from .llm_safeguards import (
        ModelRunawayDetector,
        SafeguardConfig,
        get_optimal_ollama_parameters,
    )
    from .system_context import get_system_context
except ImportError:
    # Graceful fallback if safeguards not available
    ModelRunawayDetector = None
    SafeguardConfig = None

    def get_optimal_ollama_parameters(x):
        return {}

    def get_system_context(x=None):
        return ""


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
    """Synthesizes RAG search results using LLMs.

    Supports both OpenAI-compatible endpoints (LM Studio, vLLM, OpenAI)
    and Ollama's native API. Provider is auto-detected or set via config.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        ollama_url: str = "http://localhost:11434",
        model: str = None,
        enable_thinking: bool = False,
        config=None,
        provider: str = "auto",
        api_key: str = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.available_models = []
        self.model = model
        self.enable_thinking = enable_thinking
        self._initialized = False
        self.config = config
        self.provider = provider  # "auto", "openai", "ollama"
        self.api_key = api_key
        self._active_provider = None  # Set during init: "openai" or "ollama"
        self._last_usage = {}  # Token usage from last API call

        # Initialize safeguards
        if ModelRunawayDetector:
            self.safeguard_detector = ModelRunawayDetector(SafeguardConfig())
        else:
            self.safeguard_detector = None

    def get_last_usage(self) -> dict:
        """Return and clear token usage from the last API call.

        Returns dict with prompt_tokens and completion_tokens.
        """
        usage = self._last_usage.copy()
        self._last_usage = {}
        return usage

    def _get_available_models(self) -> List[str]:
        """Get list of available LLM models from the active provider."""
        # Try OpenAI-compatible first (unless provider is explicitly ollama)
        if self.provider != "ollama":
            try:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                response = requests.get(
                    f"{self.base_url}/models", headers=headers, timeout=5
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    # Filter to LLM models (exclude embedding models)
                    llm_models = [m for m in models
                                  if not any(kw in m.lower() for kw in ("embed", "bge", "e5", "gte"))]
                    if llm_models:
                        self._active_provider = "openai"
                        return llm_models
            except Exception as e:
                logger.debug(f"OpenAI-compatible endpoint not available: {e}")

        # Fall back to Ollama
        if self.provider != "openai":
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    if models:
                        self._active_provider = "ollama"
                        return models
            except Exception as e:
                logger.debug(f"Ollama not available: {e}")

        return []

    def _call_openai_compatible(
        self, prompt: str, temperature: float = 0.3
    ) -> Optional[str]:
        """Call an OpenAI-compatible chat completions endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Extra budget for thinking tokens when thinking mode is enabled
        token_limit = 2048 + (2000 if self.enable_thinking else 0)

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": token_limit,
        }

        try:
            response = requests.post(  # nosec B113 - timeout is set below
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120 if self.enable_thinking else 60,
            )
            response.raise_for_status()
            data = response.json()
            # Extract token usage if available
            usage = data.get("usage", {})
            self._last_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI-compatible LLM call failed: {e}")
            return None

    def _call_openai_stream(self, prompt: str, temperature: float = 0.3):
        """Stream tokens from an OpenAI-compatible chat completions endpoint.

        Yields individual token strings as they arrive via SSE.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        token_limit = 2048 + (2000 if self.enable_thinking else 0)

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": token_limit,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=(15, 30),
            )
            response.raise_for_status()

            total_chars = 0
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8") if isinstance(line, bytes) else line
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    # Check for usage in final chunk
                    usage = chunk.get("usage")
                    if usage:
                        self._last_usage = {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                        }
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        total_chars += len(token)
                        yield token
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            # Fallback: estimate tokens from char count if provider didn't send usage
            if not self._last_usage.get("completion_tokens"):
                self._last_usage = {
                    "prompt_tokens": len(prompt) // 4,
                    "completion_tokens": total_chars // 4,
                }
        except Exception as e:
            logger.error(f"OpenAI streaming call failed: {e}")
            yield f"\n\n[Streaming error: {e}]"

    def _select_best_model(self) -> str:
        """Select the best available model based on configuration rankings with robust name resolution."""
        if not self.available_models:
            # Use config fallback if available, otherwise use default
            if (
                self.config
                and hasattr(self.config, "llm")
                and hasattr(self.config.llm, "model_rankings")
                and self.config.llm.model_rankings
            ):
                return self.config.llm.model_rankings[0]  # First preferred model
            return "qwen2.5:1.5b"  # System fallback only if no config

        # Get model rankings from config or use defaults
        if (
            self.config
            and hasattr(self.config, "llm")
            and hasattr(self.config.llm, "model_rankings")
        ):
            model_rankings = self.config.llm.model_rankings
        else:
            # Fallback rankings if no config
            model_rankings = [
                "qwen3:1.7b",
                "qwen3:0.6b",
                "qwen3:4b",
                "qwen2.5:3b",
                "qwen2.5:1.5b",
                "qwen2.5-coder:1.5b",
            ]

        # Find first available model from our ranked list using relaxed name resolution
        for preferred_model in model_rankings:
            resolved_model = self._resolve_model_name(preferred_model)
            if resolved_model:
                logger.info(f"Selected model: {resolved_model} (requested: {preferred_model})")
                return resolved_model

        # If no preferred models found, use first available
        fallback = self.available_models[0]
        logger.warning(f"Using fallback model: {fallback}")
        return fallback

    def _resolve_model_name(self, configured_model: str) -> Optional[str]:
        """Auto-resolve model names to match what's actually available in Ollama.
        
        This handles common patterns like:
        - qwen3:1.7b -> qwen3:1.7b-q8_0
        - qwen3:4b -> qwen3:4b-instruct-2507-q4_K_M
        - auto -> first available model from ranked preference
        """
        logger.debug(f"Resolving model: {configured_model}")
        
        if not self.available_models:
            logger.warning("No available models for resolution")
            return None
            
        # Handle special 'auto' directive - use smart selection
        if configured_model.lower() == 'auto':
            logger.info("Using AUTO selection...")
            return self._select_best_available_model()
            
        # Direct exact match first (case-insensitive)
        for available_model in self.available_models:
            if configured_model.lower() == available_model.lower():
                logger.info(f"✅ EXACT MATCH: {available_model}")
                return available_model
        
        # Relaxed matching - extract base model and size, then find closest match
        logger.info(f"No exact match for '{configured_model}', trying relaxed matching...")
        match = self._find_closest_model_match(configured_model)
        if match:
            logger.info(f"✅ FUZZY MATCH: {configured_model} -> {match}")
        else:
            logger.warning(f"❌ NO MATCH: {configured_model} not found in available models")
        return match
    
    def _select_best_available_model(self) -> str:
        """Select the best available model from what's actually installed."""
        if not self.available_models:
            logger.warning("No models available from Ollama - using fallback")
            return "qwen2.5:1.5b"  # fallback
            
        logger.info(f"Available models: {self.available_models}")
        
        # Priority order for auto selection - prefer newer and larger models
        priority_patterns = [
            # Qwen3 series (newest)
            "qwen3:8b", "qwen3:4b", "qwen3:1.7b", "qwen3:0.6b",
            # Qwen2.5 series 
            "qwen2.5:3b", "qwen2.5:1.5b", "qwen2.5:0.5b",
            # Any other model as fallback
        ]
        
        # Find first match from priority list
        logger.info("Searching for best model match...")
        for pattern in priority_patterns:
            match = self._find_closest_model_match(pattern)
            if match:
                logger.info(f"✅ AUTO SELECTED: {match} (matched pattern: {pattern})")
                return match
            else:
                logger.debug(f"No match found for pattern: {pattern}")
                
        # If nothing matches, just use first available
        fallback = self.available_models[0]
        logger.warning(f"⚠️  Using first available model as fallback: {fallback}")
        return fallback
    
    def _find_closest_model_match(self, configured_model: str) -> Optional[str]:
        """Find the closest matching model using relaxed criteria."""
        if not self.available_models:
            logger.debug(f"No available models to match against for: {configured_model}")
            return None
            
        # Extract base model and size from configured model
        # e.g., "qwen3:4b" -> ("qwen3", "4b")
        if ':' not in configured_model:
            base_model = configured_model
            size = None
        else:
            base_model, size_part = configured_model.split(':', 1)
            # Extract just the size (remove any suffixes like -q8_0)
            size = size_part.split('-')[0] if '-' in size_part else size_part
        
        logger.debug(f"Looking for base model: '{base_model}', size: '{size}'")
        
        # Find all models that match the base model
        candidates = []
        for available_model in self.available_models:
            if ':' not in available_model:
                continue
                
            avail_base, avail_full = available_model.split(':', 1)
            if avail_base.lower() == base_model.lower():
                candidates.append(available_model)
                logger.debug(f"Found candidate: {available_model}")
        
        if not candidates:
            logger.debug(f"No candidates found for base model: {base_model}")
            return None
            
        # If we have a size preference, try to match it
        if size:
            for candidate in candidates:
                # Check if size appears in the model name
                if size.lower() in candidate.lower():
                    logger.debug(f"Size match found: {candidate} contains '{size}'")
                    return candidate
            logger.debug(f"No size match found for '{size}', using first candidate")
        
        # If no size match or no size specified, return first candidate
        selected = candidates[0]
        logger.debug(f"Returning first candidate: {selected}")
        return selected

    # Old pattern matching methods removed - using simpler approach now

    def _ensure_initialized(self):
        """Lazy initialization with LLM warmup."""
        if self._initialized:
            return

        # Load available models
        self.available_models = self._get_available_models()
        if not self.model:
            self.model = self._select_best_model()

        # Skip warmup - models are fast enough and warmup causes delays
        # Warmup removed to eliminate startup delays and unwanted model calls

        self._initialized = True

    def _get_optimal_context_size(self, model_name: str) -> int:
        """Get optimal context size based on model capabilities and configuration."""
        # Get configured context window
        if self.config and hasattr(self.config, "llm"):
            configured_context = self.config.llm.context_window
            auto_context = getattr(self.config.llm, "auto_context", True)
        else:
            configured_context = 16384  # Default to 16K
            auto_context = True

        # Model-specific maximum context windows (based on research)
        model_limits = {
            # Qwen3 models with native context support
            "qwen3:0.6b": 32768,  # 32K native
            "qwen3:1.7b": 32768,  # 32K native
            "qwen3:4b": 131072,  # 131K with YaRN extension
            # Qwen2.5 models
            "qwen2.5:1.5b": 32768,  # 32K native
            "qwen2.5:3b": 32768,  # 32K native
            "qwen2.5-coder:1.5b": 32768,  # 32K native
            # Fallback for unknown models
            "default": 8192,
        }

        # Find model limit (check for partial matches)
        model_limit = model_limits.get("default", 8192)
        for model_pattern, limit in model_limits.items():
            if model_pattern != "default" and model_pattern.lower() in model_name.lower():
                model_limit = limit
                break

        # If auto_context is enabled, respect model limits
        if auto_context:
            optimal_context = min(configured_context, model_limit)
        else:
            optimal_context = configured_context

        # Ensure minimum usable context for RAG
        optimal_context = max(optimal_context, 4096)  # Minimum 4K for basic RAG

        logger.debug(
            f"Context for {model_name}: {optimal_context} tokens (configured: {configured_context}, limit: {model_limit})"
        )
        return optimal_context

    def is_available(self) -> bool:
        """Check if Ollama is available and has models."""
        self._ensure_initialized()
        return len(self.available_models) > 0

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Call the LLM using the best available provider.

        Routes to OpenAI-compatible or Ollama based on what's available.
        """
        self._ensure_initialized()

        if self._active_provider == "openai":
            return self._call_openai_compatible(prompt, temperature)
        elif self._active_provider == "ollama":
            return self._call_ollama(prompt, temperature)
        else:
            # No provider initialized — try OpenAI as last resort
            # (covers case where provider="openai" but model listing failed
            # while the endpoint may still accept chat completions)
            result = self._call_openai_compatible(prompt, temperature)
            if result:
                return result
            logger.error("No LLM provider available")
            return None

    def _call_ollama(
        self,
        prompt: str,
        temperature: float = 0.3,
        disable_thinking: bool = False,
        use_streaming: bool = True,
        collapse_thinking: bool = True,
    ) -> Optional[str]:
        """Make a call to the LLM API with safeguards.

        Routes to OpenAI-compatible endpoint when the active provider is
        'openai' (e.g. models discovered via /v1/models with '/' names).
        Falls through to native Ollama /api/generate otherwise.
        """
        start_time = time.time()

        try:
            # Ensure we're initialized
            self._ensure_initialized()

            # If the active provider is OpenAI-compatible, delegate there
            # Native Ollama /api/generate doesn't understand '/' model names
            if getattr(self, '_active_provider', None) == 'openai':
                logger.debug(f"Routing to OpenAI-compatible endpoint (provider={self._active_provider})")
                return self._call_openai_compatible(prompt, temperature=temperature)

            # Use the best available model with retry logic
            model_to_use = self.model
            if self.model not in self.available_models:
                # Refresh model list in case of race condition
                logger.warning(
                    f"Configured model {self.model} not in available list, refreshing..."
                )
                self.available_models = self._get_available_models()

                if self.model in self.available_models:
                    model_to_use = self.model
                    logger.info(f"Model {self.model} found after refresh")
                elif self.available_models:
                    # Fallback to first available model
                    model_to_use = self.available_models[0]
                    logger.warning(f"Using fallback model: {model_to_use}")
                else:
                    logger.error("No Ollama models available")
                    return None

            # Handle thinking mode for Qwen3 models
            final_prompt = prompt
            use_thinking = self.enable_thinking and not disable_thinking

            # For non-thinking mode, add <no_think> tag for Qwen3
            if not use_thinking and "qwen3" in model_to_use.lower():
                if not final_prompt.endswith(" <no_think>"):
                    final_prompt += " <no_think>"

            # Get optimal parameters for this model
            optimal_params = get_optimal_ollama_parameters(model_to_use)

            # Qwen3-specific optimal parameters based on research
            if "qwen3" in model_to_use.lower():
                if use_thinking:
                    # Thinking mode: Temperature=0.6, TopP=0.95, TopK=20, PresencePenalty=1.5
                    qwen3_temp = 0.6
                    qwen3_top_p = 0.95
                    qwen3_top_k = 20
                    qwen3_presence = 1.5
                else:
                    # Non-thinking mode: Temperature=0.7, TopP=0.8, TopK=20, PresencePenalty=1.5
                    qwen3_temp = 0.7
                    qwen3_top_p = 0.8
                    qwen3_top_k = 20
                    qwen3_presence = 1.5
            else:
                qwen3_temp = temperature
                qwen3_top_p = optimal_params.get("top_p", 0.9)
                qwen3_top_k = optimal_params.get("top_k", 40)
                qwen3_presence = optimal_params.get("presence_penalty", 1.0)

            payload = {
                "model": model_to_use,
                "prompt": final_prompt,
                "stream": use_streaming,
                "options": {
                    "temperature": qwen3_temp,
                    "top_p": qwen3_top_p,
                    "top_k": qwen3_top_k,
                    "num_ctx": self._get_optimal_context_size(
                        model_to_use
                    ),  # Dynamic context based on model and config
                    "num_predict": optimal_params.get("num_predict", 2000),
                    "repeat_penalty": optimal_params.get("repeat_penalty", 1.1),
                    "presence_penalty": qwen3_presence,
                },
            }

            # Handle streaming with thinking display
            if use_streaming:
                return self._handle_streaming_with_thinking_display(
                    payload, model_to_use, use_thinking, start_time, collapse_thinking
                )

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=65,  # Slightly longer than safeguard timeout
            )

            if response.status_code == 200:
                result = response.json()

                # All models use standard response format
                # Qwen3 thinking tokens are embedded in the response content itself as <think>...</think>
                raw_response = result.get("response", "").strip()

                # Log thinking content for Qwen3 debugging
                if (
                    "qwen3" in model_to_use.lower()
                    and use_thinking
                    and "<think>" in raw_response
                ):
                    thinking_start = raw_response.find("<think>")
                    thinking_end = raw_response.find("</think>")
                    if thinking_start != -1 and thinking_end != -1:
                        thinking_content = raw_response[thinking_start + 7 : thinking_end]
                        logger.info(f"Qwen3 thinking: {thinking_content[:100]}...")

                # Apply safeguards to check response quality
                if self.safeguard_detector and raw_response:
                    is_valid, issue_type, explanation = (
                        self.safeguard_detector.check_response_quality(
                            raw_response,
                            prompt[:100],
                            start_time,  # First 100 chars of prompt for context
                        )
                    )

                    if not is_valid:
                        logger.warning(f"Safeguard triggered: {issue_type}")
                        # Preserve original response but add safeguard warning
                        return self._create_safeguard_response_with_content(
                            issue_type, explanation, raw_response
                        )

                # Clean up thinking tags from final response
                cleaned_response = raw_response
                if "<think>" in cleaned_response or "</think>" in cleaned_response:
                    # Remove thinking content but preserve the rest
                    cleaned_response = cleaned_response.replace("<think>", "").replace(
                        "</think>", ""
                    )
                    # Clean up extra whitespace that might be left
                    lines = cleaned_response.split("\n")
                    cleaned_lines = []
                    for line in lines:
                        if line.strip():  # Only keep non-empty lines
                            cleaned_lines.append(line)
                    cleaned_response = "\n".join(cleaned_lines)

                return cleaned_response.strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    def _create_safeguard_response(
        self, issue_type: str, explanation: str, original_prompt: str
    ) -> str:
        """Create a helpful response when safeguards are triggered."""
        return """⚠️ Model Response Issue Detected

{explanation}

**Original query context:** {original_prompt[:200]}{'...' if len(original_prompt) > 200 else ''}

**What happened:** The AI model encountered a common issue with small language models and was prevented from giving a problematic response.

**Your options:**
1. **Try again**: Ask the same question (often resolves itself)
2. **Rephrase**: Make your question more specific or break it into parts
3. **Use exploration mode**: `rag-mini explore` for complex questions
4. **Different approach**: Try synthesis mode: `--synthesize` for simpler responses

This is normal with smaller AI models and helps ensure you get quality responses."""

    def _create_safeguard_response_with_content(
        self, issue_type: str, explanation: str, original_response: str
    ) -> str:
        """Create a response that preserves the original content but adds a safeguard warning."""

        # For Qwen3, extract the actual response (after thinking)
        actual_response = original_response
        if "<think>" in original_response and "</think>" in original_response:
            thinking_end = original_response.find("</think>")
            if thinking_end != -1:
                actual_response = original_response[thinking_end + 8 :].strip()

        # If we have useful content, preserve it with a warning
        if len(actual_response.strip()) > 20:
            return """⚠️ **Response Quality Warning** ({issue_type})

{explanation}

---

**AI Response (use with caution):**

{actual_response}

---

💡 **Note**: This response may have quality issues. Consider rephrasing your question or trying exploration mode for better results."""
        else:
            # If content is too short or problematic, use the original safeguard response
            return """⚠️ Model Response Issue Detected

{explanation}

**What happened:** The AI model encountered a common issue with small language models.

**Your options:**
1. **Try again**: Ask the same question (often resolves itself)
2. **Rephrase**: Make your question more specific or break it into parts
3. **Use exploration mode**: `rag-mini explore` for complex questions

This is normal with smaller AI models and helps ensure you get quality responses."""

    def _handle_streaming_with_thinking_display(
        self,
        payload: dict,
        model_name: str,
        use_thinking: bool,
        start_time: float,
        collapse_thinking: bool = True,
    ) -> Optional[str]:
        """Handle streaming response with real-time thinking token display."""
        import json

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, stream=True, timeout=65
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return None

            full_response = ""
            thinking_content = ""
            is_in_thinking = False
            is_thinking_complete = False
            thinking_lines_printed = 0

            # ANSI escape codes for colors and cursor control
            GRAY = "\033[90m"  # Dark gray for thinking
            # "\033[37m"  # Light gray alternative  # Unused variable removed
            RESET = "\033[0m"  # Reset color
            CLEAR_LINE = "\033[2K"  # Clear entire line
            CURSOR_UP = "\033[A"  # Move cursor up one line

            print(f"\n💭 {GRAY}Thinking...{RESET}", flush=True)

            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line.decode("utf-8"))
                        chunk_text = chunk_data.get("response", "")

                        if chunk_text:
                            full_response += chunk_text

                            # Handle thinking tokens
                            if use_thinking and "<think>" in chunk_text:
                                is_in_thinking = True
                                chunk_text = chunk_text.replace("<think>", "")

                            if is_in_thinking and "</think>" in chunk_text:
                                is_in_thinking = False
                                is_thinking_complete = True
                                chunk_text = chunk_text.replace("</think>", "")

                                if collapse_thinking:
                                    # Clear thinking content and show completion
                                    # Move cursor up to clear thinking lines
                                    for _ in range(thinking_lines_printed + 1):
                                        print(
                                            f"{CURSOR_UP}{CLEAR_LINE}",
                                            end="",
                                            flush=True,
                                        )

                                    print(
                                        f"💭 {GRAY}Thinking complete ✓{RESET}",
                                        flush=True,
                                    )
                                    thinking_lines_printed = 0
                                else:
                                    # Keep thinking visible, just show completion
                                    print(
                                        f"\n💭 {GRAY}Thinking complete ✓{RESET}",
                                        flush=True,
                                    )

                                print("🤖 AI Response:", flush=True)
                                continue

                            # Display thinking content in gray with better formatting
                            if is_in_thinking and chunk_text.strip():
                                thinking_content += chunk_text

                                # Handle line breaks and word wrapping properly
                                if (
                                    " " in chunk_text
                                    or "\n" in chunk_text
                                    or len(thinking_content) > 100
                                ):
                                    # Split by sentences for better readability
                                    sentences = thinking_content.replace("\n", " ").split(". ")

                                    for sentence in sentences[
                                        :-1
                                    ]:  # Process complete sentences
                                        sentence = sentence.strip()
                                        if sentence:
                                            # Word wrap long sentences
                                            words = sentence.split()
                                            line = ""
                                            for word in words:
                                                if len(line + " " + word) > 70:
                                                    if line:
                                                        print(
                                                            f"{GRAY}   {line.strip()}{RESET}",
                                                            flush=True,
                                                        )
                                                        thinking_lines_printed += 1
                                                    line = word
                                                else:
                                                    line += " " + word if line else word

                                            if line.strip():
                                                print(
                                                    f"{GRAY}   {line.strip()}.{RESET}",
                                                    flush=True,
                                                )
                                                thinking_lines_printed += 1

                                    # Keep the last incomplete sentence for next iteration
                                    thinking_content = sentences[-1] if sentences else ""

                            # Display regular response content (skip any leftover thinking)
                            elif (
                                not is_in_thinking
                                and is_thinking_complete
                                and chunk_text.strip()
                            ):
                                # Filter out any remaining thinking tags that might leak through
                                clean_text = chunk_text
                                if "<think>" in clean_text or "</think>" in clean_text:
                                    clean_text = clean_text.replace("<think>", "").replace(
                                        "</think>", ""
                                    )

                                if clean_text:  # Remove .strip() here to preserve whitespace
                                    # Preserve all formatting including newlines and spaces
                                    print(clean_text, end="", flush=True)

                        # Check if response is done
                        if chunk_data.get("done", False):
                            print()  # Final newline
                            break

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream chunk: {e}")
                        continue

            return full_response

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            return None

    def _handle_streaming_with_early_stop(
        self, payload: dict, model_name: str, use_thinking: bool, start_time: float
    ) -> Optional[str]:
        """Handle streaming response with intelligent early stopping."""
        import json

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, stream=True, timeout=65
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return None

            full_response = ""
            word_buffer = []
            repetition_window = 30  # Check last 30 words for repetition (more context)
            stop_threshold = (
                0.8  # Stop only if 80% of recent words are repetitive (very permissive)
            )
            min_response_length = 100  # Don't early stop until we have at least 100 chars

            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line.decode("utf-8"))
                        chunk_text = chunk_data.get("response", "")

                        if chunk_text:
                            full_response += chunk_text

                            # Add words to buffer for repetition detection
                            new_words = chunk_text.split()
                            word_buffer.extend(new_words)

                            # Keep only recent words in buffer
                            if len(word_buffer) > repetition_window:
                                word_buffer = word_buffer[-repetition_window:]

                            # Check for repetition patterns after we have enough words AND content
                            if (
                                len(word_buffer) >= repetition_window
                                and len(full_response) >= min_response_length
                            ):
                                unique_words = set(word_buffer)
                                repetition_ratio = 1 - (len(unique_words) / len(word_buffer))

                                # Early stop only if repetition is EXTREMELY high (80%+)
                                if repetition_ratio > stop_threshold:
                                    logger.info(
                                        f"Early stopping due to repetition: {repetition_ratio:.2f}"
                                    )

                                    # Add a gentle completion to the response
                                    if not full_response.strip().endswith((".", "!", "?")):
                                        full_response += "..."

                                    # Send stop signal to model (attempt to gracefully stop)
                                    try:
                                        stop_payload = {
                                            "model": model_name,
                                            "stop": True,
                                        }
                                        requests.post(
                                            f"{self.ollama_url}/api/generate",
                                            json=stop_payload,
                                            timeout=2,
                                        )
                                    except (
                                        ConnectionError,
                                        FileNotFoundError,
                                        IOError,
                                        OSError,
                                        TimeoutError,
                                        requests.RequestException,
                                    ):
                                        pass  # If stop fails, we already have partial response

                                    break

                        if chunk_data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

            # Clean up thinking tags from final response
            cleaned_response = full_response
            if "<think>" in cleaned_response or "</think>" in cleaned_response:
                # Remove thinking content but preserve the rest
                cleaned_response = cleaned_response.replace("<think>", "").replace(
                    "</think>", ""
                )
                # Clean up extra whitespace that might be left
                lines = cleaned_response.split("\n")
                cleaned_lines = []
                for line in lines:
                    if line.strip():  # Only keep non-empty lines
                        cleaned_lines.append(line)
                cleaned_response = "\n".join(cleaned_lines)

            return cleaned_response.strip()

        except Exception as e:
            logger.error(f"Streaming with early stop failed: {e}")
            return None

    def synthesize_search_results(
        self, query: str, results: List[Any], project_path: Path
    ) -> SynthesisResult:
        """Synthesize search results into a coherent summary.

        Takes search results and sends them with the query to an LLM
        for a natural language synthesis.
        """
        self._ensure_initialized()
        if not self.is_available():
            return SynthesisResult(
                summary="LLM synthesis unavailable. Start an LLM server (LM Studio or Ollama).",
                key_points=[],
                code_examples=[],
                suggested_actions=["Start LM Studio or Ollama with a chat model loaded"],
                confidence=0.0,
            )

        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(results[:8], 1):
            file_path = getattr(result, "file_path", "unknown")
            content = getattr(result, "content", str(result))
            score = getattr(result, "score", 0.0)
            truncated = content[:500] + ("..." if len(content) > 500 else "")

            context_parts.append(
                f"Result {i} (Score: {score:.3f}):\n"
                f"File: {file_path}\n"
                f"Content: {truncated}\n"
            )

        context = "\n".join(context_parts)
        system_context = ""
        try:
            system_context = get_system_context(project_path)
        except Exception:
            pass

        prompt = f"""You are a senior software engineer analyzing code search results.
Synthesize these results into a clear, helpful answer.

QUERY: "{query}"
PROJECT: {project_path.name}
{f"CONTEXT: {system_context}" if system_context else ""}

SEARCH RESULTS:
{context}

Respond in well-formatted markdown. Use headers, bold, code blocks, and bullet points where appropriate.
Include specific file names and function names where relevant.
Keep under 300 words."""

        # Call LLM (routes to OpenAI-compatible or Ollama automatically)
        response = self._call_llm(prompt, temperature=0.3)

        if not response:
            return SynthesisResult(
                summary="LLM synthesis failed. Check that an LLM server is running.",
                key_points=[],
                code_examples=[],
                suggested_actions=["Start LM Studio or Ollama with a chat model"],
                confidence=0.0,
            )

        # Use the response directly as a summary (no JSON parsing needed)
        return SynthesisResult(
            summary=response.strip(),
            key_points=[],
            code_examples=[],
            suggested_actions=[],
            confidence=0.8,
        )

    def synthesize_stream(self, query: str, results: List[Any], project_path: Path):
        """Stream synthesis tokens. Yields individual tokens as they arrive."""
        self._ensure_initialized()
        if not self.is_available():
            yield "LLM synthesis unavailable. Start an LLM server."
            return

        context_parts = []
        for i, result in enumerate(results[:8], 1):
            file_path = getattr(result, "file_path", "unknown")
            content = getattr(result, "content", str(result))
            score = getattr(result, "score", 0.0)
            truncated = content[:500] + ("..." if len(content) > 500 else "")
            context_parts.append(
                f"Result {i} (Score: {score:.3f}):\nFile: {file_path}\nContent: {truncated}\n"
            )

        context = "\n".join(context_parts)
        system_context = ""
        try:
            system_context = get_system_context(project_path)
        except Exception:
            pass

        prompt = f"""You are a senior software engineer analyzing code search results.
Synthesize these results into a clear, helpful answer.

QUERY: "{query}"
PROJECT: {project_path.name}
{f"CONTEXT: {system_context}" if system_context else ""}

SEARCH RESULTS:
{context}

Respond in well-formatted markdown. Use headers, bold, code blocks, and bullet points where appropriate.
Include specific file names and function names where relevant.
Keep under 300 words."""

        if self._active_provider == "openai" or self._active_provider is None:
            # Stream from OpenAI-compatible endpoint (or try as fallback)
            yield from self._call_openai_stream(prompt, temperature=0.3)
        else:
            # Ollama: non-streaming fallback, yield entire response
            response = self._call_llm(prompt, temperature=0.3)
            if response:
                yield response
            else:
                yield "LLM synthesis failed. Check that an LLM server is running."

    def format_synthesis_output(self, synthesis: SynthesisResult, query: str) -> str:
        """Format synthesis result for display."""

        output = []
        output.append("🧠 LLM SYNTHESIS")
        output.append("=" * 50)
        output.append("")

        output.append("📝 Summary:")
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

        confidence_emoji = (
            "🟢"
            if synthesis.confidence > 0.7
            else "🟡" if synthesis.confidence > 0.4 else "🔴"
        )
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
        MockResult(
            "auth.py",
            "def authenticate_user(username, password):\n    return verify_credentials(username, password)",
            0.95,
        ),
        MockResult(
            "models.py",
            "class User:\n    def login(self):\n        return authenticate_user(self.username, self.password)",
            0.87,
        ),
    ]

    synthesis = synthesizer.synthesize_search_results(
        "user authentication", results, Path("/test/project")
    )

    print(synthesizer.format_synthesis_output(synthesis, "user authentication"))


if __name__ == "__main__":
    test_synthesizer()

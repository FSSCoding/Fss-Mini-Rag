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
    """Synthesizes RAG search results using Ollama LLMs."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = None,
        enable_thinking: bool = False,
        config=None,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.available_models = []
        self.model = model
        self.enable_thinking = enable_thinking  # Default False for synthesis mode
        self._initialized = False
        self.config = config  # For accessing model rankings

        # Initialize safeguards
        if ModelRunawayDetector:
            self.safeguard_detector = ModelRunawayDetector(SafeguardConfig())
        else:
            self.safeguard_detector = None

    def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
        return []

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

    def _call_ollama(
        self,
        prompt: str,
        temperature: float = 0.3,
        disable_thinking: bool = False,
        use_streaming: bool = True,
        collapse_thinking: bool = True,
    ) -> Optional[str]:
        """Make a call to Ollama API with safeguards."""
        start_time = time.time()

        try:
            # Ensure we're initialized
            self._ensure_initialized()

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
        """Synthesize search results into a coherent summary."""

        self._ensure_initialized()
        if not self.is_available():
            return SynthesisResult(
                summary="LLM synthesis unavailable (Ollama not running or no models)",
                key_points=[],
                code_examples=[],
                suggested_actions=["Install and run Ollama with a model"],
                confidence=0.0,
            )

        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(results[:8], 1):  # Limit to top 8 results
            # result.file_path if hasattr(result, "file_path") else "unknown"  # Unused variable removed
            # result.content if hasattr(result, "content") else str(result)  # Unused variable removed
            # result.score if hasattr(result, "score") else 0.0  # Unused variable removed

            context_parts.append(
                """
Result {i} (Score: {score:.3f}):
File: {file_path}
Content: {content[:500]}{'...' if len(content) > 500 else ''}
"""
            )

        # "\n".join(context_parts)  # Unused variable removed

        # Get system context for better responses
        # get_system_context(project_path)  # Unused variable removed

        # Create synthesis prompt with system context
        prompt = """You are a senior software engineer analyzing code search results. Your task is to synthesize the search results into a helpful, actionable summary.

SYSTEM CONTEXT: {system_context}
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
                confidence=0.0,
            )

        # Parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                return SynthesisResult(
                    summary=data.get("summary", "No summary generated"),
                    key_points=data.get("key_points", []),
                    code_examples=data.get("code_examples", []),
                    suggested_actions=data.get("suggested_actions", []),
                    confidence=float(data.get("confidence", 0.5)),
                )
            else:
                # Fallback: use the raw response as summary
                return SynthesisResult(
                    summary=response[:300] + "..." if len(response) > 300 else response,
                    key_points=[],
                    code_examples=[],
                    suggested_actions=[],
                    confidence=0.3,
                )

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return SynthesisResult(
                summary="LLM synthesis failed (JSON parsing error)",
                key_points=[],
                code_examples=[],
                suggested_actions=["Try the search again or check LLM output"],
                confidence=0.0,
            )

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

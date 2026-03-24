"""Streaming synthesis service for the GUI.

Runs LLM streaming in a background thread, buffers tokens,
and emits events to the main thread for live rendering.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, List

from ..events import EventBus

logger = logging.getLogger(__name__)

# How often to flush buffered tokens to the UI (ms)
_FLUSH_INTERVAL_MS = 150


class StreamingService:
    """Streams LLM synthesis tokens with buffered UI updates."""

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._cancel = threading.Event()
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancel(self):
        self._cancel.set()

    def start(self, llm_url: str, llm_model: str, query: str,
              results: List[Any], project_path: str):
        """Start streaming synthesis in a background thread."""
        self._cancel.clear()

        def _run():
            try:
                from mini_rag.llm_synthesizer import LLMSynthesizer
                from mini_rag.gui.env_manager import get_key

                synth = LLMSynthesizer(
                    base_url=llm_url,
                    model=llm_model if llm_model != "auto" else None,
                    provider="openai",
                    api_key=get_key("LLM_API_KEY") or get_key("OPENAI_API_KEY"),
                )

                self.bus.emit("stream:started", {"query": query})
                t0 = time.time()

                buffer = []
                last_flush = time.time()
                in_thinking = False
                full_text = []

                for token in synth.synthesize_stream(query, results, Path(project_path)):
                    if self._cancel.is_set():
                        self.bus.emit("stream:cancelled", {})
                        return

                    full_text.append(token)

                    # Detect thinking tags
                    if "<think>" in token:
                        in_thinking = True
                        self.bus.emit("stream:thinking_start", {})
                        token = token.replace("<think>", "")
                    if "</think>" in token:
                        in_thinking = False
                        self.bus.emit("stream:thinking_end", {})
                        token = token.replace("</think>", "")

                    if token:
                        buffer.append(token)

                    # Flush buffer at interval
                    now = time.time()
                    if (now - last_flush) * 1000 >= _FLUSH_INTERVAL_MS and buffer:
                        chunk = "".join(buffer)
                        buffer.clear()
                        last_flush = now
                        self.bus.emit("stream:token", {
                            "text": chunk,
                            "thinking": in_thinking,
                        })

                # Final flush
                if buffer:
                    self.bus.emit("stream:token", {
                        "text": "".join(buffer),
                        "thinking": in_thinking,
                    })

                elapsed_ms = (time.time() - t0) * 1000
                self.bus.emit("stream:complete", {
                    "text": "".join(full_text),
                    "timing_ms": elapsed_ms,
                })
                # Emit token usage for cost tracking
                usage = synth.get_last_usage()
                if usage:
                    self.bus.emit("llm:usage", usage)

            except Exception as e:
                logger.error(f"Streaming synthesis failed: {e}")
                self.bus.emit("stream:error", {"error": str(e)})

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

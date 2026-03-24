"""Session cost tracker for LLM API usage.

Listens to llm:usage events, accumulates token counts and dollar
cost estimates per session, and emits cost:updated for the UI.
"""

import logging
from typing import Any, Dict

from .events import EventBus

logger = logging.getLogger(__name__)


class CostTracker:
    """Accumulates LLM token usage and cost for the current session."""

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self.session_tokens_in = 0
        self.session_tokens_out = 0
        self.session_cost = 0.0
        self.query_count = 0

        # Cost rates (updated from config/presets)
        self.cost_per_1m_input = 0.0
        self.cost_per_1m_output = 0.0

        self.bus.on("llm:usage", self._on_usage)
        self.bus.on("settings:changed", self._on_settings)

    def _on_usage(self, data: Dict[str, Any]):
        """Handle token usage from an LLM call."""
        prompt_tokens = data.get("prompt_tokens", 0)
        completion_tokens = data.get("completion_tokens", 0)

        if prompt_tokens == 0 and completion_tokens == 0:
            return

        self.session_tokens_in += prompt_tokens
        self.session_tokens_out += completion_tokens
        self.query_count += 1

        query_cost = (
            prompt_tokens * self.cost_per_1m_input / 1_000_000
            + completion_tokens * self.cost_per_1m_output / 1_000_000
        )
        self.session_cost += query_cost

        logger.debug(
            f"LLM usage: +{prompt_tokens}/{completion_tokens} tokens, "
            f"query=${query_cost:.6f}, session=${self.session_cost:.6f}"
        )

        self.bus.emit("cost:updated", {
            "session_tokens_in": self.session_tokens_in,
            "session_tokens_out": self.session_tokens_out,
            "session_cost": self.session_cost,
            "query_count": self.query_count,
            "query_tokens_in": prompt_tokens,
            "query_tokens_out": completion_tokens,
            "query_cost": query_cost,
        })

    def _on_settings(self, data: Dict[str, Any]):
        """Update cost rates when settings change."""
        if "cost_per_1m_input" in data:
            self.cost_per_1m_input = float(data["cost_per_1m_input"])
        if "cost_per_1m_output" in data:
            self.cost_per_1m_output = float(data["cost_per_1m_output"])

    def reset(self):
        """Reset session counters."""
        self.session_tokens_in = 0
        self.session_tokens_out = 0
        self.session_cost = 0.0
        self.query_count = 0
        self.bus.emit("cost:updated", {
            "session_tokens_in": 0,
            "session_tokens_out": 0,
            "session_cost": 0.0,
            "query_count": 0,
            "query_tokens_in": 0,
            "query_tokens_out": 0,
            "query_cost": 0.0,
        })

    @staticmethod
    def format_tokens(count: int) -> str:
        """Format token count for display: 1234 -> '1.2K', 1234567 -> '1.2M'."""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return str(count)

    @staticmethod
    def format_cost(cost: float) -> str:
        """Format cost for display."""
        if cost == 0:
            return "$0.00"
        if cost < 0.01:
            return f"${cost:.4f}"
        return f"${cost:.2f}"

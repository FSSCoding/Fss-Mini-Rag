"""Event bus for cross-component communication.

Components emit and subscribe to events instead of calling each other
directly. This decouples the UI from the services and prevents callback
spaghetti.
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class EventBus:
    """Simple publish/subscribe event bus."""

    def __init__(self):
        self._subscribers: Dict[str, list] = defaultdict(list)

    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)

    def emit(self, event_type: str, data: Dict[str, Any] = None):
        """Emit an event to all subscribers."""
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(data or {})
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    def off(self, event_type: str, handler: Callable = None):
        """Unsubscribe from an event type."""
        if handler:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
        else:
            self._subscribers[event_type] = []

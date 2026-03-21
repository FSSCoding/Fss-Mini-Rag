"""
Performance monitoring for RAG system.
Track loading times, query times, and resource usage.
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Track performance metrics for RAG operations."""

    def __init__(self):
        self.metrics = {}
        self.process = psutil.Process(os.getpid())

    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation time and memory."""
        # Get initial state
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        try:
            yield self
        finally:
            # Calculate metrics
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            duration = end_time - start_time
            memory_delta = end_memory - start_memory

            # Store metrics
            self.metrics[operation] = {
                "duration_seconds": duration,
                "memory_delta_mb": memory_delta,
                "final_memory_mb": end_memory,
            }

            logger.info(
                f"[PERF] {operation}: {duration:.2f}s, "
                f"Memory: {end_memory:.1f}MB (+{memory_delta:+.1f}MB)"
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = sum(m["duration_seconds"] for m in self.metrics.values())

        return {
            "total_time_seconds": total_time,
            "operations": self.metrics,
            "current_memory_mb": self.process.memory_info().rss / 1024 / 1024,
        }

    def print_summary(self):
        """Print a formatted summary."""
        print("\n" + "=" * 50)
        print("PERFORMANCE SUMMARY")
        print("=" * 50)

        for op, metrics in self.metrics.items():
            print(f"\n{op}:")
            print(f"  Time: {metrics['duration_seconds']:.2f}s")
            print(f"  Memory: +{metrics['memory_delta_mb']:+.1f}MB")

        summary = self.get_summary()
        print(f"\nTotal Time: {summary['total_time_seconds']:.2f}s")
        print(f"Current Memory: {summary['current_memory_mb']:.1f}MB")
        print("=" * 50)


# Global instance for easy access
_monitor = None


def get_monitor() -> PerformanceMonitor:
    """Get or create global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor

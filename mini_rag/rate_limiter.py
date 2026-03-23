"""
Rate limiting and retry infrastructure for Mini RAG.

Provides token-bucket rate limiters and exponential backoff retry
for all external API calls: search engines, LLM, web scraping.
Designed for long-running deep research sessions where reliability matters.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ──────────────────────────────────────────────────────────
# Rate Limiter — token bucket algorithm
# ──────────────────────────────────────────────────────────


class RateLimiter:
    """Token bucket rate limiter.

    Controls the rate of API calls by maintaining a bucket of tokens
    that refill at a steady rate. Thread-safe for concurrent use.

    Args:
        calls_per_minute: Maximum calls allowed per minute
        burst: Maximum burst size (tokens held at once). Defaults to calls_per_minute.
        name: Identifier for logging
    """

    def __init__(self, calls_per_minute: float, burst: int = 0, name: str = ""):
        self.rate = calls_per_minute / 60.0  # Tokens per second
        self.capacity = burst or max(1, int(calls_per_minute))
        self.tokens = float(self.capacity)
        self.name = name
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 300.0) -> bool:
        """Wait until a token is available, then consume it.

        Args:
            timeout: Maximum seconds to wait (default 5 minutes)

        Returns:
            True if token acquired, False if timed out
        """
        deadline = time.monotonic() + timeout

        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True

                # Calculate wait time for next token
                wait = (1.0 - self.tokens) / self.rate if self.rate > 0 else timeout

            if time.monotonic() + wait > deadline:
                logger.warning(f"Rate limiter [{self.name}] timed out after {timeout}s")
                return False

            time.sleep(min(wait, 0.5))  # Sleep in small increments

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)


# ──────────────────────────────────────────────────────────
# Retry with exponential backoff
# ──────────────────────────────────────────────────────────


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Cap on delay
    backoff_factor: float = 2.0  # Multiply delay by this each retry
    retry_on_status: tuple = (429, 500, 502, 503, 504)  # HTTP status codes to retry


def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig = None,
    rate_limiter: RateLimiter = None,
    on_retry: Callable[[int, Exception, float], None] = None,
    **kwargs,
) -> T:
    """Execute a function with exponential backoff retry.

    Respects rate limiter before each attempt. Retries on specific
    exceptions and HTTP status codes.

    Args:
        func: Function to call
        config: Retry configuration
        rate_limiter: Optional rate limiter to acquire before each call
        on_retry: Optional callback(attempt, exception, delay) for logging
        **kwargs: Arguments to pass to func

    Returns:
        Result of func

    Raises:
        Last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception = None
    delay = config.base_delay

    for attempt in range(config.max_retries + 1):
        # Respect rate limiter
        if rate_limiter:
            if not rate_limiter.acquire():
                raise TimeoutError(f"Rate limiter timed out on attempt {attempt + 1}")

        try:
            return func(**kwargs)
        except Exception as e:
            last_exception = e

            # Check if this is a retryable error
            if not _is_retryable(e, config):
                raise

            if attempt >= config.max_retries:
                break

            # Calculate delay, respecting Retry-After header if present
            actual_delay = _get_retry_delay(e, delay, config.max_delay)

            if on_retry:
                on_retry(attempt + 1, e, actual_delay)
            else:
                logger.info(
                    f"Retry {attempt + 1}/{config.max_retries} "
                    f"after {actual_delay:.1f}s: {type(e).__name__}: {e}"
                )

            time.sleep(actual_delay)
            delay = min(delay * config.backoff_factor, config.max_delay)

    raise last_exception


def _is_retryable(exc: Exception, config: RetryConfig) -> bool:
    """Check if an exception is worth retrying."""
    # requests.HTTPError with retryable status code
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        return exc.response.status_code in config.retry_on_status

    # Connection errors are always retryable
    exc_name = type(exc).__name__
    retryable_types = (
        "ConnectionError", "Timeout", "ReadTimeout", "ConnectTimeout",
        "ConnectionResetError", "BrokenPipeError",
    )
    return exc_name in retryable_types


def _get_retry_delay(exc: Exception, default_delay: float, max_delay: float) -> float:
    """Extract Retry-After header from response, or use default delay."""
    if hasattr(exc, "response") and exc.response is not None:
        retry_after = exc.response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), max_delay)
            except ValueError:
                pass
    return min(default_delay, max_delay)


# ──────────────────────────────────────────────────────────
# Pre-configured rate limiters for known services
# ──────────────────────────────────────────────────────────


# Default rate limits per service (conservative, works without configuration)
_DEFAULT_LIMITS: Dict[str, Dict[str, Any]] = {
    "duckduckgo": {"calls_per_minute": 10, "burst": 3},
    "tavily": {"calls_per_minute": 30, "burst": 5},
    "brave": {"calls_per_minute": 15, "burst": 5},
    "llm": {"calls_per_minute": 30, "burst": 10},
    "scraper": {"calls_per_minute": 30, "burst": 5},
    "embeddings": {"calls_per_minute": 60, "burst": 20},
}

# Singleton registry of active rate limiters
_limiters: Dict[str, RateLimiter] = {}
_limiter_lock = threading.Lock()


def get_limiter(
    service: str,
    calls_per_minute: float = 0,
    burst: int = 0,
) -> RateLimiter:
    """Get or create a rate limiter for a service.

    Uses defaults for known services. Custom values override defaults.
    Returns the same limiter instance for repeated calls with the same service name.

    Args:
        service: Service identifier (e.g. "brave", "llm", "scraper")
        calls_per_minute: Override default rate (0 = use default)
        burst: Override default burst size (0 = use default)
    """
    with _limiter_lock:
        if service not in _limiters:
            defaults = _DEFAULT_LIMITS.get(service, {"calls_per_minute": 20, "burst": 5})
            cpm = calls_per_minute or defaults["calls_per_minute"]
            b = burst or defaults["burst"]
            _limiters[service] = RateLimiter(
                calls_per_minute=cpm, burst=b, name=service,
            )
        return _limiters[service]


def get_retry_config(service: str) -> RetryConfig:
    """Get retry configuration for a service."""
    configs = {
        "duckduckgo": RetryConfig(max_retries=2, base_delay=5.0, max_delay=30.0),
        "tavily": RetryConfig(max_retries=3, base_delay=2.0, max_delay=30.0),
        "brave": RetryConfig(max_retries=3, base_delay=2.0, max_delay=30.0),
        "llm": RetryConfig(max_retries=2, base_delay=1.0, max_delay=15.0),
        "scraper": RetryConfig(max_retries=2, base_delay=2.0, max_delay=20.0),
        "embeddings": RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0),
    }
    return configs.get(service, RetryConfig())

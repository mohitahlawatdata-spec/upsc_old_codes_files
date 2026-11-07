"""Bounded retry policy for transient external-provider failures."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from mainsmaster.diagnostics import logger

T = TypeVar("T")

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
TRANSIENT_MARKERS = (
    "deadline exceeded",
    "high demand",
    "internal server error",
    "rate limit",
    "resource exhausted",
    "service unavailable",
    "temporarily unavailable",
    "timeout",
    "too many requests",
    "unavailable",
)


def is_transient_provider_error(exc: Exception) -> bool:
    """Return whether an exception is safe to retry as a transient provider failure."""
    for attribute in ("status_code", "code"):
        value = getattr(exc, attribute, None)
        try:
            if int(value) in TRANSIENT_STATUS_CODES:
                return True
        except (TypeError, ValueError):
            pass
    message = str(exc).casefold()
    return any(str(code) in message for code in TRANSIENT_STATUS_CODES) or any(
        marker in message for marker in TRANSIENT_MARKERS
    )


def retry_provider_call(
    operation: Callable[[], T],
    label: str,
    *,
    attempts: int = 5,
    initial_delay: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run a synchronous provider call with bounded exponential backoff."""
    delay = initial_delay
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == attempts or not is_transient_provider_error(exc):
                raise
            logger.warning(
                "%s transient failure (%s); retrying %d/%d in %.1fs",
                label,
                type(exc).__name__,
                attempt + 1,
                attempts,
                delay,
            )
            sleep(delay)
            delay *= 2
    raise RuntimeError(f"{label} retry loop exhausted")


async def retry_provider_call_async(
    operation: Callable[[], Awaitable[T]],
    label: str,
    *,
    attempts: int = 5,
    initial_delay: float = 1.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an asynchronous provider call with bounded exponential backoff."""
    delay = initial_delay
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt == attempts or not is_transient_provider_error(exc):
                raise
            logger.warning(
                "%s transient failure (%s); retrying %d/%d in %.1fs",
                label,
                type(exc).__name__,
                attempt + 1,
                attempts,
                delay,
            )
            await sleep(delay)
            delay *= 2
    raise RuntimeError(f"{label} retry loop exhausted")

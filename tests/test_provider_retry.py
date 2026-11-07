"""Transient provider failures should retry without hiding permanent failures."""

import asyncio

import pytest

from mainsmaster.providers.retry import (
    is_transient_provider_error,
    retry_provider_call,
    retry_provider_call_async,
)


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def test_recognizes_transient_provider_failures() -> None:
    assert is_transient_provider_error(ProviderError("busy", status_code=503))
    assert is_transient_provider_error(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert is_transient_provider_error(RuntimeError("model is experiencing high demand"))
    assert not is_transient_provider_error(ValueError("invalid response schema"))


def test_sync_retry_uses_exponential_backoff() -> None:
    calls = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ProviderError("unavailable", status_code=503)
        return "ok"

    result = retry_provider_call(operation, "test", sleep=delays.append)

    assert result == "ok"
    assert calls == 3
    assert delays == [1.0, 2.0]


def test_sync_retry_does_not_retry_permanent_error() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("invalid request")

    with pytest.raises(ValueError, match="invalid request"):
        retry_provider_call(operation, "test", sleep=lambda _delay: None)
    assert calls == 1


def test_async_retry_uses_exponential_backoff() -> None:
    calls = 0
    delays: list[float] = []

    async def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TimeoutError("provider timeout")
        return "ok"

    async def record_delay(delay: float) -> None:
        delays.append(delay)

    result = asyncio.run(retry_provider_call_async(operation, "test", sleep=record_delay))

    assert result == "ok"
    assert calls == 3
    assert delays == [1.0, 2.0]

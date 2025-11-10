from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, TypeVar


T = TypeVar("T")


async def retry_async(fn: Callable[[], Awaitable[T]], attempts: int = 3, backoff_ms: int = 50) -> T:
    last_ex: Exception | None = None
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:  # pragma: no cover - behavior verified in router tests
            last_ex = e
            await asyncio.sleep((backoff_ms / 1000.0) * (i + 1))
    assert last_ex  # for type checkers
    raise last_ex


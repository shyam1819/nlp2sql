"""Cache protocol shared by every backend.

Keeping this to get/set/delete means an in-memory dict and a Redis client are
interchangeable: swapping backends is a config change, not a code change.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    def delete(self, key: str) -> None: ...

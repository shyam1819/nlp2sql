"""In-memory cache backend.

A dict with optional per-key TTL. Sakila's schema is static, so entries are
written once at startup with no TTL and served from memory for the process
lifetime. The Redis backend will implement the same `Cache` protocol.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class InMemoryCache:
    def __init__(self) -> None:
        # key -> (value, expires_at | None)
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + ttl if ttl else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

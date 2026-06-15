"""Cache layer for static metadata (table schemas + descriptions).

In-memory now; Redis later. `get_cache()` returns the configured backend so
callers never depend on the concrete implementation.
"""

from __future__ import annotations

from ..config import get_settings
from .base import Cache
from .memory import InMemoryCache

_cache: Cache | None = None


def get_cache() -> Cache:
    """Process-wide singleton cache selected by CACHE_BACKEND."""
    global _cache
    if _cache is not None:
        return _cache

    backend = get_settings().cache_backend.lower()
    if backend == "memory":
        _cache = InMemoryCache()
    elif backend == "redis":  # pragma: no cover - not implemented yet
        raise NotImplementedError(
            "Redis cache backend is not implemented yet; use CACHE_BACKEND=memory."
        )
    else:
        raise ValueError(f"Unknown CACHE_BACKEND: {backend!r}")
    return _cache


__all__ = ["Cache", "InMemoryCache", "get_cache"]

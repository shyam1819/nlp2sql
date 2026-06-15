"""LangSmith tracing setup.

LangGraph/LangChain auto-instrument when the LANGSMITH_* environment variables
are present. We load them from our `Settings` (i.e. from `.env`) and push them
into `os.environ` so the tracer picks them up — keeping all configuration in one
place instead of requiring callers to export shell vars manually.

Call `setup_tracing()` once at process start (done in `build_graph`). It is a
no-op unless LANGSMITH_TRACING=true.
"""

from __future__ import annotations

import os

from .config import get_settings

_configured = False


def setup_tracing() -> bool:
    """Enable LangSmith tracing if configured. Returns True when tracing is on."""
    global _configured
    if _configured:
        return os.environ.get("LANGSMITH_TRACING") == "true"
    _configured = True

    settings = get_settings()
    if not settings.langsmith_tracing:
        return False
    if not settings.langsmith_api_key:
        # Tracing requested but no key — warn rather than fail the whole agent.
        print("[observability] LANGSMITH_TRACING is on but LANGSMITH_API_KEY is unset; "
              "traces will not be sent.")
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    print(f"[observability] LangSmith tracing enabled -> project {settings.langsmith_project!r}")
    return True

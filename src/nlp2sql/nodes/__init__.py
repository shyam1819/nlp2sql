"""Graph nodes — one module per node in the pipeline."""

from __future__ import annotations


def format_history(messages: list, *, limit: int = 10) -> str:
    """Render recent conversation turns as plain text for prompt context.

    Excludes the most recent human message (that's the current question, passed
    separately). Returns "(no prior conversation)" when empty.
    """
    prior = messages[:-1] if messages else []
    prior = prior[-limit:]
    if not prior:
        return "(no prior conversation)"
    lines = []
    for m in prior:
        role = getattr(m, "type", "?")
        speaker = {"human": "User", "ai": "Assistant"}.get(role, role)
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)

"""Deterministic SQL safety check (defense layer 2 of 3).

Layer 1 is the read-only connection (writes can't execute at all).
Layer 2 is this static `sqlparse` check: cheap, deterministic, runs before the
LLM guard so obvious violations never cost a model call.
Layer 3 is the LLM guard (Node 6), which catches subtler intent and produces
natural-language feedback for regeneration.
"""

from __future__ import annotations

import sqlparse
from sqlparse.tokens import DDL, DML, Keyword

# Anything in this set makes a statement unsafe regardless of context.
_FORBIDDEN = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "PRAGMA", "ATTACH", "DETACH", "GRANT", "REVOKE", "VACUUM",
    "MERGE", "UPSERT",
}


def static_guard(sql: str) -> tuple[bool, str]:
    """Return (is_safe, reason). Safe == exactly one read-only SELECT."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return False, "Empty query."

    statements = [s for s in sqlparse.parse(sql) if str(s).strip().rstrip(";").strip()]
    if len(statements) != 1:
        return False, f"Expected exactly one statement, found {len(statements)}."

    stmt = statements[0]
    if stmt.get_type() != "SELECT":
        return False, f"Statement type is {stmt.get_type()!r}; only SELECT is allowed."

    for token in stmt.flatten():
        if token.ttype in (DML, DDL, Keyword):
            if token.normalized.upper() in _FORBIDDEN:
                return False, f"Forbidden keyword: {token.normalized.upper()}."
    return True, "ok"

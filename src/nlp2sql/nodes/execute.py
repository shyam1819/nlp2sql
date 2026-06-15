"""Node 7: run the verified query against the read-only database.

On a SQLite error we record the message and bump the mechanical retry counter so
generation (or table re-selection, for missing-table errors) can correct itself;
the routing function decides loop vs. give up.
"""

from __future__ import annotations

import sqlite3

from ..config import get_settings
from ..db.connection import ReadOnlyDB
from ..state import AgentState

_db = ReadOnlyDB()


def execute_node(state: AgentState) -> dict:
    sql = state.get("sql_query", "")
    max_rows = get_settings().max_result_rows
    try:
        rows = _db.execute_select(sql, max_rows=max_rows)
    except sqlite3.Error as exc:
        return {
            "execution_error": str(exc),
            "retry_count": state.get("retry_count", 0) + 1,
        }
    return {
        "query_result": rows,
        "row_count": len(rows),
        "execution_error": "",
        # Flag truncation so the answer can caveat it (a clipped GROUP BY misleads).
        "truncated": len(rows) >= max_rows,
    }

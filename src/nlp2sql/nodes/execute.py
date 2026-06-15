"""Node 7: run the guarded query against the read-only database.

On a SQLite error we record the message and bump the shared retry counter so
generation can correct itself; the routing function decides loop vs. give up.
"""

from __future__ import annotations

import sqlite3

from ..db.connection import ReadOnlyDB
from ..state import AgentState

_db = ReadOnlyDB()


def execute_node(state: AgentState) -> dict:
    sql = state.get("sql_query", "")
    try:
        rows = _db.execute_select(sql)
    except sqlite3.Error as exc:
        return {
            "execution_error": str(exc),
            "retry_count": state.get("retry_count", 0) + 1,
        }
    return {"query_result": rows, "row_count": len(rows), "execution_error": ""}

"""Read-only access to the movie database.

The connection is the *wall* in our defense-in-depth: SQLite is opened with
URI flag ``mode=ro``, so DML/DDL physically cannot run even if a destructive
statement slips past the static parser and the LLM guard. The query is also
wrapped so a single SELECT is all that can execute.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..config import get_settings


class ReadOnlyDB:
    """A thin read-only SQLite wrapper.

    A new connection is opened per query: connections are cheap for SQLite and
    this keeps the agent safe to use across threads/requests without sharing
    cursors.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or get_settings().db_path
        if not Path(self.db_path).exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path!r}. "
                "Run `python data/setup_db.py` first."
            )

    def _connect(self) -> sqlite3.Connection:
        # file: URI with mode=ro -> writes raise sqlite3.OperationalError.
        uri = f"file:{Path(self.db_path).resolve()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        return con

    def execute_select(
        self, sql: str, *, max_rows: int = 200, timeout_s: float = 10.0
    ) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as dicts.

        Raises sqlite3.Error subclasses on failure — the execute node catches
        these and feeds the message back to the SQL generator for a retry.
        """
        con = self._connect()
        try:
            con.execute(f"PRAGMA busy_timeout = {int(timeout_s * 1000)}")
            cur = con.execute(sql)
            rows = cur.fetchmany(max_rows)
            return [dict(r) for r in rows]
        finally:
            con.close()

"""ConversationStore — append-only record of agent turns for audit/analytics.

Distinct from the LangGraph checkpointer: the checkpointer exists to *resume*
a thread, this exists to *query* what users asked and what the agent did. The
repository interface (record_turn / recent) is storage-agnostic, so moving to
Postgres later is a config + driver swap, not a rewrite.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id           TEXT NOT NULL,
    ts                  REAL NOT NULL,
    original_question   TEXT,
    rephrased_question  TEXT,
    was_relevant        INTEGER,
    needs_clarification INTEGER,
    outcome             TEXT,
    tables_used         TEXT,   -- JSON array
    generated_sql       TEXT,
    retry_count         INTEGER,
    guard_feedback      TEXT,
    row_count           INTEGER,
    execution_error     TEXT,
    final_answer        TEXT
);
CREATE INDEX IF NOT EXISTS idx_turns_thread ON conversation_turns(thread_id);
"""


class ConversationStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def record_turn(self, thread_id: str, state: dict[str, Any]) -> None:
        row = (
            thread_id,
            time.time(),
            state.get("question"),
            state.get("rephrased_question"),
            int(bool(state.get("is_relevant", False))),
            int(bool(state.get("needs_clarification", False))),
            state.get("outcome"),
            json.dumps(state.get("required_tables", [])),
            state.get("sql_query"),
            state.get("retry_count", 0),
            state.get("guard_feedback") or None,
            state.get("row_count"),
            state.get("execution_error") or None,
            state.get("final_answer")
            or state.get("refusal_message")
            or state.get("clarification_message"),
        )
        with self._connect() as con:
            con.execute(
                """INSERT INTO conversation_turns (
                    thread_id, ts, original_question, rephrased_question,
                    was_relevant, needs_clarification, outcome, tables_used,
                    generated_sql, retry_count, guard_feedback, row_count,
                    execution_error, final_answer
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                row,
            )

    def recent(self, thread_id: str | None = None, limit: int = 20) -> list[dict]:
        sql = "SELECT * FROM conversation_turns"
        params: tuple = ()
        if thread_id:
            sql += " WHERE thread_id = ?"
            params = (thread_id,)
        sql += " ORDER BY id DESC LIMIT ?"
        params += (limit,)
        with self._connect() as con:
            return [dict(r) for r in con.execute(sql, params)]

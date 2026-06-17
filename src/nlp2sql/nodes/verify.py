"""Node 6b: verify the query is *correct*, not just *safe* and *runnable*.

The guard (6) blocks unsafe SQL and execute (7) catches SQL errors — but a query
can be safe and run cleanly while returning the WRONG numbers (join fan-out,
wrong grain, missing filter). For analytics that silent-wrong case is the
dominant failure mode, so this node adds two checks before execution:

  1. EXPLAIN dry-run — cheap compile check (missing tables/columns) with no scan.
  2. LLM correctness review — fan-out, grouping, filters, faithfulness.

On failure it records feedback and bumps the *semantic* retry budget; routing
sends it back to generation (or, on a missing-table compile error, lets the
mechanical path re-select tables).
"""

from __future__ import annotations

import sqlite3

from ..config import get_settings
from ..db.connection import ReadOnlyDB
from ..llm import client, prompts
from ..llm.schemas import VerificationDecision
from ..state import AgentState

_db = ReadOnlyDB()


def verify_node(state: AgentState) -> dict:
    sql = state.get("sql_query", "")
    dialect = get_settings().sql_dialect

    # 1) Cheap structural pre-flight: does it even compile against the schema?
    try:
        _db.explain(sql)
    except sqlite3.Error as exc:
        return {
            "verification_passed": False,
            "verification_feedback": f"The query does not compile: {exc}",
            "logic_retry_count": state.get("logic_retry_count", 0) + 1,
        }

    # 2) Semantic correctness review.
    decision = client.parse(
        prompts.render("verify.system", dialect=dialect),
        prompts.render(
            "verify.user",
            question=state.get("rephrased_question") or state.get("question", ""),
            schema=state.get("schema_context", ""),
            plan=state.get("query_plan", {}),
            sql=sql,
        ),
        VerificationDecision,
    )
    if not decision.is_sound:
        return {
            "verification_passed": False,
            "verification_feedback": decision.issues,
            "logic_retry_count": state.get("logic_retry_count", 0) + 1,
        }

    return {"verification_passed": True, "verification_feedback": ""}

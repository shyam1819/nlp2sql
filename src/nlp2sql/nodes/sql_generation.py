"""Node 5: generate a single read-only SELECT.

This node is the loop target for both the guard (Node 6) and execute (Node 7):
any guard feedback or execution error in state is folded back into the prompt
so the next attempt can correct itself.
"""

from __future__ import annotations

from ..config import get_settings
from ..llm import client, prompts
from ..state import AgentState


def _strip_fences(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1] if "\n" in sql else sql
        sql = sql.rsplit("```", 1)[0]
    return sql.strip().rstrip(";").strip()


def sql_generation_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    settings = get_settings()

    # The template handles column formatting (loop) and the retry-feedback
    # conditionals — the node just passes raw state values.
    user = prompts.render(
        "sql_generation.user",
        schema=state.get("schema_context", ""),
        columns=state.get("selected_columns", {}),
        question=question,
        guard_feedback=state.get("guard_feedback", ""),
        verification_feedback=state.get("verification_feedback", ""),
        execution_error=state.get("execution_error", ""),
        previous_sql=state.get("sql_query", ""),
    )
    system = prompts.render(
        "sql_generation.system",
        dialect=settings.sql_dialect,
        max_rows=settings.max_result_rows,
    )
    sql = _strip_fences(client.complete(system, user))
    # Clear stale feedback so a fresh attempt isn't re-penalised next loop.
    return {
        "sql_query": sql,
        "guard_feedback": "",
        "verification_feedback": "",
        "execution_error": "",
    }

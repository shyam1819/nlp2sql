"""Node 5: generate a single read-only SELECT.

This node is the loop target for both the guard (Node 6) and execute (Node 7):
any guard feedback or execution error in state is folded back into the prompt
so the next attempt can correct itself.
"""

from __future__ import annotations

from ..llm import client
from ..llm.prompts import SQL_GENERATION_SYSTEM
from ..state import AgentState


def _strip_fences(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1] if "\n" in sql else sql
        sql = sql.rsplit("```", 1)[0]
    return sql.strip().rstrip(";").strip()


def sql_generation_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    schema_context = state.get("schema_context", "")
    selected = state.get("selected_columns", {})
    columns_text = "\n".join(f"  {t}: {', '.join(cols)}" for t, cols in selected.items())

    feedback_parts = []
    if state.get("guard_feedback"):
        feedback_parts.append(f"Your previous query was rejected by the safety guard: {state['guard_feedback']}")
    if state.get("execution_error"):
        feedback_parts.append(f"Your previous query failed to execute: {state['execution_error']}")
    if state.get("sql_query") and feedback_parts:
        feedback_parts.append(f"Previous query was:\n{state['sql_query']}")
    feedback = ("\n\n" + "\n".join(feedback_parts)) if feedback_parts else ""

    user = (
        f"Schema:\n{schema_context}\n\n"
        f"Relevant columns:\n{columns_text}\n\n"
        f"Question: {question}{feedback}\n\nSQL:"
    )
    sql = _strip_fences(client.complete(SQL_GENERATION_SYSTEM, user))
    # Clear stale feedback so a fresh attempt isn't re-penalised next loop.
    return {"sql_query": sql, "guard_feedback": "", "execution_error": ""}

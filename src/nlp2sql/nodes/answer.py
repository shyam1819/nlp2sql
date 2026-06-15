"""Node 8: answer the question from the fetched rows.

Reached on success, or after the retry budget is exhausted (in which case we
explain the failure rather than inventing data).
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage

from ..llm import client
from ..llm.prompts import ANSWER_SYSTEM
from ..state import AgentState


def _truncate_rows(rows: list[dict], limit: int = 50) -> str:
    sample = rows[:limit]
    note = "" if len(rows) <= limit else f"\n(showing first {limit} of {len(rows)} rows)"
    return json.dumps(sample, default=str, indent=2) + note


def answer_node(state: AgentState) -> dict:
    question = state.get("rephrased_question") or state["question"]

    # Retry budget exhausted on execution errors.
    if state.get("execution_error"):
        answer = (
            "I couldn't run a working query for that after several attempts. "
            f"The database reported: {state['execution_error']}"
        )
        return {
            "final_answer": answer,
            "outcome": "failed",
            "messages": [AIMessage(content=answer)],
        }

    # Retry budget exhausted without ever producing a guard-approved query.
    # query_result is None until the execute node runs; [] is a valid empty result.
    if state.get("query_result") is None:
        answer = (
            "I couldn't construct a safe, valid query for that after several "
            "attempts. Could you try rephrasing your question?"
        )
        return {
            "final_answer": answer,
            "outcome": "failed",
            "messages": [AIMessage(content=answer)],
        }

    rows = state.get("query_result") or []
    answer = client.complete(
        ANSWER_SYSTEM,
        f"Question: {question}\n\nSQL: {state.get('sql_query','')}\n\n"
        f"Rows ({len(rows)}):\n{_truncate_rows(rows)}",
    )
    return {
        "final_answer": answer,
        "outcome": "answered",
        "messages": [AIMessage(content=answer)],
    }

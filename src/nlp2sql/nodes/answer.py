"""Node 8: answer the question from the fetched rows.

Reached on success, or after the retry budget is exhausted (in which case we
explain the failure rather than inventing data).
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage

from ..llm import client, prompts
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
        prompts.render("answer.system"),
        prompts.render(
            "answer.user",
            question=question,
            sql=state.get("sql_query", ""),
            row_count=len(rows),
            rows=_truncate_rows(rows),
        ),
    )

    # Caveats: a clipped result or an unresolved correctness concern must be flagged.
    caveats = []
    if state.get("truncated"):
        caveats.append(
            f"Note: results were capped at {len(rows)} rows, so this may be incomplete."
        )
    if state.get("verification_passed") is False and state.get("verification_feedback"):
        caveats.append(
            "Caution: an automated review still flagged a possible correctness "
            f"issue I couldn't fully resolve — {state['verification_feedback']}"
        )
    if caveats:
        answer = answer + "\n\n" + "\n".join(caveats)

    return {
        "final_answer": answer,
        "outcome": "answered",
        "messages": [AIMessage(content=answer)],
    }

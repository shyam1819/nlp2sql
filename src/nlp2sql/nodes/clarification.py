"""Node 1b: does the question need clarification before we can build SQL?

If yes, we surface a single follow-up question and the graph routes to ingest;
the next user turn resumes the same thread (memory carries the context).
"""

from __future__ import annotations

from ..llm import client, prompts
from ..llm.schemas import ClarificationDecision
from ..state import AgentState
from . import format_history


def clarification_node(state: AgentState) -> dict:
    question = state["question"]
    history = format_history(state.get("messages", []))
    decision = client.parse(
        prompts.render("clarification.system"),
        prompts.render("clarification.user", history=history, question=question),
        ClarificationDecision,
    )
    if decision.needs_clarification and decision.question:
        return {
            "needs_clarification": True,
            "clarification_message": decision.question,
            "outcome": "clarification",
        }
    return {"needs_clarification": False}

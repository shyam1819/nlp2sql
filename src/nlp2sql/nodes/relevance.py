"""Node 1: is the latest message in scope for this database?

History-aware: a follow-up that refers to prior results ("does that add up?",
"verify that", "break it down by month") is in scope even though, read alone, it
names no table. Only genuinely unrelated messages are refused (routed to ingest).
"""

from __future__ import annotations

from ..llm import client, prompts
from ..llm.schemas import RelevanceDecision
from ..state import AgentState
from . import format_history


def relevance_node(state: AgentState) -> dict:
    question = state["question"]
    history = format_history(state.get("messages", []))
    decision = client.parse(
        prompts.render("relevance.system"),
        prompts.render("relevance.user", history=history, question=question),
        RelevanceDecision,
    )
    # on_topic and follow_up are both answerable; only out_of_scope is refused.
    if decision.classification != "out_of_scope":
        return {"is_relevant": True}
    return {
        "is_relevant": False,
        "refusal_message": decision.reason,
        "outcome": "refused",
    }

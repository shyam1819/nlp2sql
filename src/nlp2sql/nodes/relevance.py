"""Node 1: is the question answerable from this database?

If not, we set a user-facing refusal and the graph routes straight to ingest.
"""

from __future__ import annotations

from ..llm import client, prompts
from ..llm.schemas import RelevanceDecision
from ..state import AgentState


def relevance_node(state: AgentState) -> dict:
    question = state["question"]
    decision = client.parse(
        prompts.render("relevance.system"),
        prompts.render("relevance.user", question=question),
        RelevanceDecision,
    )
    if decision.is_relevant:
        return {"is_relevant": True}
    return {
        "is_relevant": False,
        "refusal_message": decision.reason,
        "outcome": "refused",
    }

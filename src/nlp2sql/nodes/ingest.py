"""Terminal node: ingest the turn into the conversation store.

Every path — answered, refused, clarification, failed — routes through here so
the analytics record is complete. It also appends the assistant's message to
history for refusal/clarification paths (the answer node already does this for
answered/failed), so memory stays consistent across turns.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from ..persistence import get_conversation_store
from ..state import AgentState


def ingest_node(state: AgentState) -> dict:
    thread_id = state.get("thread_id", "default")
    get_conversation_store().record_turn(thread_id, dict(state))

    # Append assistant turn for paths that didn't go through the answer node.
    outcome = state.get("outcome")
    extra: dict = {}
    if outcome == "refused" and state.get("refusal_message"):
        extra["messages"] = [AIMessage(content=state["refusal_message"])]
    elif outcome == "clarification" and state.get("clarification_message"):
        extra["messages"] = [AIMessage(content=state["clarification_message"])]
    return extra

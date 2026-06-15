"""Node 2: rewrite the question into a self-contained form using history."""

from __future__ import annotations

from ..llm import client
from ..llm.prompts import REPHRASE_SYSTEM
from ..state import AgentState
from . import format_history


def rephrase_node(state: AgentState) -> dict:
    question = state["question"]
    history = format_history(state.get("messages", []))
    rephrased = client.complete(
        REPHRASE_SYSTEM,
        f"Conversation so far:\n{history}\n\nLatest question: {question}\n\nRewritten question:",
    )
    return {"rephrased_question": rephrased or question}

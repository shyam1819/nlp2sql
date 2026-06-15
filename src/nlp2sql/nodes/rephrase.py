"""Node 2: rewrite the question into a self-contained form using history."""

from __future__ import annotations

from ..llm import client, prompts
from ..state import AgentState
from . import format_history


def rephrase_node(state: AgentState) -> dict:
    question = state["question"]
    history = format_history(state.get("messages", []))
    rephrased = client.complete(
        prompts.render("rephrase.system"),
        prompts.render("rephrase.user", history=history, question=question),
    )
    return {"rephrased_question": rephrased or question}

"""Node 6: schema guard — static check first, then the LLM guard.

On failure we record feedback and bump the shared retry counter; the routing
function decides whether to loop back to generation or give up.
"""

from __future__ import annotations

from ..llm import client, prompts
from ..llm.schemas import GuardDecision
from ..sql_safety import static_guard
from ..state import AgentState


def schema_guard_node(state: AgentState) -> dict:
    sql = state.get("sql_query", "")

    # Layer 2: deterministic static parse — cheap, runs before any model call.
    ok, reason = static_guard(sql)
    if not ok:
        return {
            "guard_passed": False,
            "guard_feedback": reason,
            "retry_count": state.get("retry_count", 0) + 1,
        }

    # Layer 3: LLM guard — catches subtler intent, yields natural-language fix.
    decision = client.parse(
        prompts.render("guard.system"),
        prompts.render("guard.user", sql=sql),
        GuardDecision,
    )
    if not decision.is_safe:
        return {
            "guard_passed": False,
            "guard_feedback": decision.reason,
            "retry_count": state.get("retry_count", 0) + 1,
        }

    return {"guard_passed": True, "guard_feedback": ""}

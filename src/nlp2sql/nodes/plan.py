"""Node 4b: plan the query before generating SQL.

Separates *what to compute* (analytical reasoning) from *how to write it* (SQL
syntax). The planner classifies the analytical intent and fills the logical-plan
slots — measures, grain, dimensions, filters, derived calcs, fan-out mitigation —
from the question and schema. The generator then renders the plan into dialect
SQL, and the verifier checks the SQL against it.

This is the "classify & decompose" middle stage of the schema-link → plan →
generate → self-correct pipeline.
"""

from __future__ import annotations

from ..llm import client, prompts
from ..llm.schemas import QueryPlan
from ..state import AgentState


def plan_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    plan = client.parse(
        prompts.render("plan.system"),
        prompts.render("plan.user", question=question, schema=state.get("schema_context", "")),
        QueryPlan,
    )
    return {"query_plan": plan.model_dump()}

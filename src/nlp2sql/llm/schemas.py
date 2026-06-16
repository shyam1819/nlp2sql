"""Structured-output schemas for the nodes.

These are *code*, not prompt text — they define the shape the model must return
and are imported by nodes. Prompt wording lives in `prompts/` (see prompts.py).

NB (INV-8 / D-12): schemas must be valid under OpenAI strict mode — no
open-ended `dict`; model per-key data as a list of objects (see ColumnSelection).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RelevanceDecision(BaseModel):
    classification: Literal["on_topic", "follow_up", "out_of_scope"] = Field(
        description=(
            "on_topic: a new question answerable with a SQL query over the database. "
            "follow_up: refers to or builds on the previous turns or their results "
            "(verification, drill-down, 'does that add up?', 'why?', 'and for store 1?') "
            "— in scope even if, read alone, it doesn't mention the database. "
            "out_of_scope: unrelated to the database (greetings, math, other domains)."
        )
    )
    reason: str = Field(
        description="Brief justification; for out_of_scope, a polite user-facing refusal."
    )


class ClarificationDecision(BaseModel):
    needs_clarification: bool = Field(description="True if the question is too ambiguous to answer.")
    question: str = Field(default="", description="The single follow-up question to ask the user, if any.")


class TableSelection(BaseModel):
    tables: list[str] = Field(description="Exact table names required to answer the question.")


class TableColumns(BaseModel):
    table: str = Field(description="Table name.")
    columns: list[str] = Field(description="Columns of this table the query will touch.")


class ColumnSelection(BaseModel):
    selections: list[TableColumns] = Field(
        description="Per-table columns needed (for SELECT, JOIN, WHERE, GROUP BY, ORDER BY)."
    )


class GuardDecision(BaseModel):
    is_safe: bool = Field(description="True only if the query is a single, read-only SELECT.")
    reason: str = Field(description="If unsafe, what is wrong so the generator can fix it.")


class QueryPlan(BaseModel):
    """A dialect-agnostic logical plan for an analytical query.

    The planner fills these slots from the question + schema; the generator
    renders them into SQL; the verifier checks the SQL against them. Slots map
    to the analytical grammar (intent → measures/grain/dimensions/filters →
    derived → order). Concrete column/table references where possible.
    """

    intent: Literal[
        "lookup", "simple_aggregate", "grouped_aggregate", "ranking_topn",
        "time_series", "share_of_total", "period_comparison", "threshold",
        "distribution",
    ] = Field(description="The analytical archetype of the question.")
    measures: list[str] = Field(
        default_factory=list,
        description="What to aggregate, as expressions, e.g. 'SUM(payment.amount) AS revenue'. Empty for pure lookups.",
    )
    grain: str = Field(
        default="",
        description="What one row of the fact/base table represents, e.g. 'one row per payment'. The fan-out anchor.",
    )
    dimensions: list[str] = Field(
        default_factory=list, description="Columns to GROUP BY / break down by."
    )
    filters: list[str] = Field(
        default_factory=list, description="WHERE conditions (scope), e.g. \"film.rating = 'PG-13'\"."
    )
    time_grain: str = Field(
        default="", description="Time bucket + range if temporal, e.g. 'by month of payment_date in 2005'."
    )
    derived: list[str] = Field(
        default_factory=list,
        description="Window/comparative calcs: ranks, share-of-total, period-over-period.",
    )
    having: list[str] = Field(
        default_factory=list, description="Post-aggregate filters (HAVING)."
    )
    order_by: str = Field(default="", description="Ordering, e.g. 'revenue DESC'.")
    limit: str = Field(default="", description="Row limit, e.g. '5'; empty if none.")
    join_path: list[str] = Field(
        default_factory=list,
        description="Joins from fact to dimensions with keys, e.g. 'payment→rental on rental_id'.",
    )
    fan_out_risk: str = Field(
        default="none",
        description="Which joins could multiply a measure and the mitigation (pre-aggregate in a CTE / COUNT(DISTINCT)); 'none' if safe.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made, especially metric definitions, e.g. 'revenue := SUM(payment.amount)'.",
    )


class VerificationDecision(BaseModel):
    is_sound: bool = Field(
        description="True if the query correctly and faithfully answers the question, with no correctness problems."
    )
    issues: str = Field(
        default="",
        description="If not sound, the specific correctness problems (e.g. join fan-out, wrong grain, missing filter) and how to fix them.",
    )

"""Structured-output schemas for the nodes.

These are *code*, not prompt text — they define the shape the model must return
and are imported by nodes. Prompt wording lives in `prompts/` (see prompts.py).

NB (INV-8 / D-12): schemas must be valid under OpenAI strict mode — no
open-ended `dict`; model per-key data as a list of objects (see ColumnSelection).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelevanceDecision(BaseModel):
    is_relevant: bool = Field(description="True if the question can be answered from the database.")
    reason: str = Field(description="Short justification; if not relevant, a user-facing refusal.")


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

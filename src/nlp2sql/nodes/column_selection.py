"""Node 4: fetch schemas for the chosen tables and select the needed columns.

We render the full schema (cached) as context and store it for the generator,
along with the model's column shortlist.
"""

from __future__ import annotations

from ..db.introspect import render_schema
from ..llm import client
from ..llm.prompts import COLUMN_SELECTION_SYSTEM, ColumnSelection
from ..state import AgentState


def column_selection_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    tables = state["required_tables"]
    schema_context = render_schema(tables)

    selection = client.parse(
        COLUMN_SELECTION_SYSTEM,
        f"Schema:\n{schema_context}\n\nQuestion: {question}",
        ColumnSelection,
    )
    return {
        "selected_columns": selection.columns,
        "schema_context": schema_context,
    }

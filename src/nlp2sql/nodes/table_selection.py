"""Node 3: pick the minimal set of tables, using the cached catalog as context."""

from __future__ import annotations

from ..db.introspect import get_catalog
from ..llm import client
from ..llm.prompts import TABLE_SELECTION_SYSTEM, TableSelection
from ..state import AgentState


def table_selection_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    catalog = get_catalog()
    catalog_text = "\n".join(f"- {t}: {desc}" for t, desc in catalog.items())

    selection = client.parse(
        TABLE_SELECTION_SYSTEM,
        f"Catalog:\n{catalog_text}\n\nQuestion: {question}",
        TableSelection,
    )
    # Keep only valid table names; fall back to all tables if the model whiffs.
    tables = [t for t in selection.tables if t in catalog]
    if not tables:
        tables = list(catalog.keys())
    return {"required_tables": tables}

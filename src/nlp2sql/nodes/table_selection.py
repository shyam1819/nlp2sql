"""Node 3: pick the minimal set of tables, using the cached catalog as context."""

from __future__ import annotations

from ..db.introspect import get_catalog
from ..llm import client, prompts
from ..llm.schemas import TableSelection
from ..state import AgentState


def table_selection_node(state: AgentState) -> dict:
    question = state["rephrased_question"]
    catalog = get_catalog()

    # The template formats the catalog (loop) — the node just passes the dict.
    selection = client.parse(
        prompts.render("table_selection.system"),
        prompts.render("table_selection.user", catalog=catalog, question=question),
        TableSelection,
    )
    # Keep only valid table names; fall back to all tables if the model whiffs.
    tables = [t for t in selection.tables if t in catalog]
    if not tables:
        tables = list(catalog.keys())
    return {"required_tables": tables}

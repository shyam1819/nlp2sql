"""Assemble the LangGraph pipeline.

Flow (see README for the diagram):

    relevance ─not relevant─► ingest
        │ relevant
    clarification ─needs info─► ingest
        │ ok
    rephrase ─► table_selection ─► column_selection ─► sql_generation
        │                                                   ▲
        ▼                                       retry (≤ max)│
    schema_guard ─unsafe──────────────────────────────────┘
        │ safe                                              ▲
        ▼                                       retry (≤ max)│
    execute ─db error─────────────────────────────────────┘
        │ ok / budget exhausted
        ▼
    answer ─► ingest ─► END

The guard and execute loops share one retry counter (MAX_RETRIES).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from .config import get_settings
from .db.introspect import warm_cache
from .observability import setup_tracing
from .nodes.answer import answer_node
from .nodes.clarification import clarification_node
from .nodes.column_selection import column_selection_node
from .nodes.execute import execute_node
from .nodes.ingest import ingest_node
from .nodes.relevance import relevance_node
from .nodes.rephrase import rephrase_node
from .nodes.schema_guard import schema_guard_node
from .nodes.sql_generation import sql_generation_node
from .nodes.plan import plan_node
from .nodes.table_selection import table_selection_node
from .nodes.verify import verify_node
from .state import AgentState


# --- routing functions -------------------------------------------------------
def _after_relevance(state: AgentState) -> str:
    return "clarification" if state.get("is_relevant") else "ingest"


def _after_clarification(state: AgentState) -> str:
    return "ingest" if state.get("needs_clarification") else "rephrase"


def _after_guard(state: AgentState) -> str:
    if state.get("guard_passed"):
        return "verify"
    if state.get("retry_count", 0) <= get_settings().max_retries:
        return "sql_generation"
    return "answer"  # mechanical budget exhausted, no safe query


def _after_verify(state: AgentState) -> str:
    if state.get("verification_passed"):
        return "execute"
    if state.get("logic_retry_count", 0) <= get_settings().logic_retry_max:
        return "sql_generation"  # regenerate with the correctness feedback
    return "execute"  # semantic budget exhausted: run best-effort, answer caveats


def _after_execute(state: AgentState) -> str:
    if not state.get("execution_error"):
        return "answer"
    if state.get("retry_count", 0) > get_settings().max_retries:
        return "answer"  # mechanical budget exhausted, surface the db error
    # Schema-linking repair: a missing table/column means selection was wrong, so
    # re-select tables (full schema relink) rather than just re-prompting generation.
    err = state["execution_error"].lower()
    if "no such table" in err or "no such column" in err:
        return "table_selection"
    return "sql_generation"


def build_graph(checkpointer=None):
    """Compile the agent graph. Pass a checkpointer or use the default SqliteSaver."""
    setup_tracing()  # enable LangSmith if LANGSMITH_TRACING=true (no-op otherwise)
    warm_cache()  # load catalog + schemas once so runtime never hits SQLite for metadata

    g = StateGraph(AgentState)
    g.add_node("relevance", relevance_node)
    g.add_node("clarification", clarification_node)
    g.add_node("rephrase", rephrase_node)
    g.add_node("table_selection", table_selection_node)
    g.add_node("column_selection", column_selection_node)
    g.add_node("sql_generation", sql_generation_node)
    g.add_node("schema_guard", schema_guard_node)
    g.add_node("verify", verify_node)
    g.add_node("execute", execute_node)
    g.add_node("answer", answer_node)
    g.add_node("ingest", ingest_node)

    g.set_entry_point("relevance")
    g.add_conditional_edges("relevance", _after_relevance,
                            {"clarification": "clarification", "ingest": "ingest"})
    g.add_conditional_edges("clarification", _after_clarification,
                            {"rephrase": "rephrase", "ingest": "ingest"})
    g.add_edge("rephrase", "table_selection")
    g.add_edge("table_selection", "column_selection")
    # Plan the query before generating SQL (config-gated); otherwise go direct.
    if get_settings().enable_planning:
        g.add_node("plan", plan_node)
        g.add_edge("column_selection", "plan")
        g.add_edge("plan", "sql_generation")
    else:
        g.add_edge("column_selection", "sql_generation")
    g.add_edge("sql_generation", "schema_guard")
    g.add_conditional_edges("schema_guard", _after_guard,
                            {"verify": "verify", "sql_generation": "sql_generation", "answer": "answer"})
    g.add_conditional_edges("verify", _after_verify,
                            {"execute": "execute", "sql_generation": "sql_generation"})
    g.add_conditional_edges("execute", _after_execute,
                            {"answer": "answer", "sql_generation": "sql_generation",
                             "table_selection": "table_selection"})
    g.add_edge("answer", "ingest")
    g.add_edge("ingest", END)

    if checkpointer is None:
        path = get_settings().checkpoint_db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False so the saver is usable from a server worker.
        conn = sqlite3.connect(path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    return g.compile(checkpointer=checkpointer)

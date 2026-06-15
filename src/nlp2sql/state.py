"""The shared graph state.

A single TypedDict threads through every node. Each node reads what it needs
and returns a partial update; LangGraph merges updates into the running state.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # --- conversation ---
    # Full message history (HumanMessage/AIMessage). `add_messages` appends.
    messages: Annotated[list, add_messages]
    thread_id: str
    question: str  # the latest raw user question

    # --- Node 1: relevance + clarification ---
    is_relevant: bool
    refusal_message: str
    needs_clarification: bool
    clarification_message: str

    # --- Node 2: rephrase ---
    rephrased_question: str

    # --- Node 3: table selection ---
    required_tables: list[str]

    # --- Node 4: column selection ---
    # {table_name: [column, ...]} the generator is allowed/expected to use.
    selected_columns: dict[str, list[str]]
    schema_context: str  # rendered DDL/columns for the selected tables

    # --- Node 5: SQL generation ---
    sql_query: str

    # --- Node 6: schema guard ---
    guard_passed: bool
    guard_feedback: str  # fed back to Node 5 on a guarded retry

    # --- Node 7: execute ---
    query_result: list[dict[str, Any]]
    row_count: int
    execution_error: str  # fed back to Node 5 on an execution retry

    # Shared retry budget across Nodes 6 and 7.
    retry_count: int

    # --- Node 8: answer ---
    final_answer: str

    # Which terminal path produced this turn (for the ingest node / analytics).
    outcome: Literal["answered", "refused", "clarification", "failed"]

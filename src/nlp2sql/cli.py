"""Interactive REPL for the nlp2sql agent.

This is the framework-phase entry point; the eventual FastAPI service will call
the same `build_graph()` and `run_turn()` building blocks.

Usage:
    nlp2sql                 # start a chat (random thread id)
    nlp2sql --thread demo   # resume/continue a named conversation
"""

from __future__ import annotations

import argparse
import uuid

from langchain_core.messages import HumanMessage

from .graph import build_graph


def run_turn(graph, question: str, thread_id: str) -> dict:
    """Run one user turn through the graph and return the final state.

    The checkpointer persists state across turns on a thread (that's our
    memory), so every per-turn derived field must be reset here — otherwise a
    short-circuit turn (refusal/clarification) would inherit the previous
    turn's SQL/tables/results and log them. `messages` is intentionally NOT
    reset: the reducer appends to preserve history.
    """
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(
        {
            "question": question,
            "thread_id": thread_id,
            "messages": [HumanMessage(content=question)],
            # reset per-turn derived state
            "is_relevant": False,
            "refusal_message": "",
            "needs_clarification": False,
            "clarification_message": "",
            "rephrased_question": "",
            "required_tables": [],
            "selected_columns": {},
            "schema_context": "",
            "query_plan": {},
            "sql_query": "",
            "guard_passed": False,
            "guard_feedback": "",
            "verification_passed": None,
            "verification_feedback": "",
            "truncated": False,
            "query_result": None,
            "row_count": None,
            "execution_error": "",
            "retry_count": 0,
            "logic_retry_count": 0,
            "final_answer": "",
            "outcome": None,
        },
        config,
    )


def reply_text(state: dict) -> str:
    """Pick the user-facing message for whichever terminal path ran."""
    outcome = state.get("outcome")
    if outcome == "refused":
        return state.get("refusal_message", "I can't answer that.")
    if outcome == "clarification":
        return state.get("clarification_message", "Could you clarify?")
    return state.get("final_answer", "(no answer)")


def main() -> None:
    parser = argparse.ArgumentParser(description="nlp2sql interactive agent")
    parser.add_argument("--thread", default=None, help="Conversation thread id (for memory).")
    args = parser.parse_args()

    thread_id = args.thread or f"cli-{uuid.uuid4().hex[:8]}"
    graph = build_graph()

    print(f"nlp2sql — movie database agent. Thread: {thread_id}")
    print("Ask a question, or type 'exit' to quit.\n")

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit", ":q"}:
            break

        state = run_turn(graph, question, thread_id)
        print(f"\nagent> {reply_text(state)}\n")


if __name__ == "__main__":
    main()

"""Routing logic for the retry loops — pure functions, no LLM/DB needed."""

from nlp2sql.graph import _after_clarification, _after_execute, _after_guard, _after_relevance


def test_relevance_routing():
    assert _after_relevance({"is_relevant": True}) == "clarification"
    assert _after_relevance({"is_relevant": False}) == "ingest"


def test_clarification_routing():
    assert _after_clarification({"needs_clarification": True}) == "ingest"
    assert _after_clarification({"needs_clarification": False}) == "rephrase"


def test_guard_routing_within_budget(monkeypatch):
    assert _after_guard({"guard_passed": True}) == "execute"
    # unsafe but retries remain (<= max_retries default 2)
    assert _after_guard({"guard_passed": False, "retry_count": 1}) == "sql_generation"
    assert _after_guard({"guard_passed": False, "retry_count": 2}) == "sql_generation"
    # budget exhausted
    assert _after_guard({"guard_passed": False, "retry_count": 3}) == "answer"


def test_execute_routing():
    assert _after_execute({"execution_error": ""}) == "answer"
    assert _after_execute({"execution_error": "boom", "retry_count": 2}) == "sql_generation"
    assert _after_execute({"execution_error": "boom", "retry_count": 3}) == "answer"

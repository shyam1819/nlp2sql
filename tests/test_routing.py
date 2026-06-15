"""Routing logic for the retry loops — pure functions, no LLM/DB needed.

Boundaries are derived from the configured budgets so the tests don't depend on
the .env values (mechanical = max_retries, semantic = logic_retry_max).
"""

from nlp2sql.config import get_settings
from nlp2sql.graph import (
    _after_clarification,
    _after_execute,
    _after_guard,
    _after_relevance,
    _after_verify,
)

MAXR = get_settings().max_retries
LOGR = get_settings().logic_retry_max


def test_relevance_routing():
    assert _after_relevance({"is_relevant": True}) == "clarification"
    assert _after_relevance({"is_relevant": False}) == "ingest"


def test_clarification_routing():
    assert _after_clarification({"needs_clarification": True}) == "ingest"
    assert _after_clarification({"needs_clarification": False}) == "rephrase"


def test_guard_routing():
    # safe query now goes to verification, not straight to execute
    assert _after_guard({"guard_passed": True}) == "verify"
    # unsafe but mechanical retries remain
    assert _after_guard({"guard_passed": False, "retry_count": MAXR}) == "sql_generation"
    # mechanical budget exhausted
    assert _after_guard({"guard_passed": False, "retry_count": MAXR + 1}) == "answer"


def test_verify_routing():
    assert _after_verify({"verification_passed": True}) == "execute"
    # unsound but logic budget remains -> regenerate
    assert _after_verify({"verification_passed": False, "logic_retry_count": LOGR}) == "sql_generation"
    # logic budget exhausted -> run best-effort, answer caveats
    assert _after_verify({"verification_passed": False, "logic_retry_count": LOGR + 1}) == "execute"


def test_execute_routing():
    assert _after_execute({"execution_error": ""}) == "answer"
    # generic error within budget -> regenerate
    assert _after_execute({"execution_error": "syntax error", "retry_count": 1}) == "sql_generation"
    # missing table/column -> schema-linking repair (re-select tables)
    assert _after_execute({"execution_error": "no such column: foo", "retry_count": 1}) == "table_selection"
    assert _after_execute({"execution_error": "no such table: bar", "retry_count": 1}) == "table_selection"
    # mechanical budget exhausted -> give up regardless of error kind
    assert _after_execute({"execution_error": "no such table: bar", "retry_count": MAXR + 1}) == "answer"

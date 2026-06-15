"""Prompt loader — Jinja2 templates render, substitute, and emit no stray tags."""

import pytest

from nlp2sql.llm import prompts

# Every node's system + user template the graph loads.
PROMPT_NAMES = [
    "relevance.system", "relevance.user",
    "clarification.system", "clarification.user",
    "rephrase.system", "rephrase.user",
    "table_selection.system", "table_selection.user",
    "column_selection.system", "column_selection.user",
    "sql_generation.system", "sql_generation.user",
    "guard.system", "guard.user",
    "verify.system", "verify.user",
    "answer.system", "answer.user",
]

# A context superset covering every variable any template needs.
CONTEXT = dict(
    question="q",
    history="h",
    catalog={"film": "films", "actor": "actors"},
    schema="TABLE film(...)",
    columns={"film": ["title", "rating"]},
    sql="SELECT 1",
    dialect="sqlite",
    max_rows=1000,
    row_count=1,
    rows='[{"a": 1}]',
    guard_feedback="",
    verification_feedback="",
    execution_error="",
    previous_sql="",
)


def test_domain_is_substituted():
    out = prompts.render("relevance.system")
    assert "movie-rental database" in out
    assert "{{" not in out


def test_variable_substitution():
    out = prompts.render("guard.user", sql="SELECT 1")
    assert "SELECT 1" in out


def test_catalog_loop_renders_each_table():
    out = prompts.render("table_selection.user", catalog=CONTEXT["catalog"], question="q")
    assert "- film: films" in out and "- actor: actors" in out


def test_feedback_conditional_included_only_on_error():
    base = dict(schema="s", columns={"film": ["title"]}, question="q",
               guard_feedback="", verification_feedback="", execution_error="", previous_sql="")
    clean = prompts.render("sql_generation.user", **base)
    assert "failed to execute" not in clean

    errored = prompts.render("sql_generation.user", **{**base,
                            "execution_error": "boom", "previous_sql": "SELECT x"})
    assert "failed to execute: boom" in errored
    assert "Previous query was:" in errored


def test_values_with_braces_are_safe():
    out = prompts.render("answer.user", question="q", sql="select 1",
                        row_count=1, rows='[{"a": 1}]')
    assert '[{"a": 1}]' in out


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_no_unfilled_tokens_after_render(name):
    out = prompts.render(name, **CONTEXT)
    assert "{{" not in out and "{%" not in out, f"{name} left a tag: {out!r}"

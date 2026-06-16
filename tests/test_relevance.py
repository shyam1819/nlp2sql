"""Relevance node maps classification -> routing. LLM call is mocked."""

from nlp2sql.llm.schemas import RelevanceDecision
from nlp2sql.nodes import relevance


def _mock(monkeypatch, classification, reason=""):
    monkeypatch.setattr(
        relevance.client,
        "parse",
        lambda *a, **k: RelevanceDecision(classification=classification, reason=reason),
    )


def test_follow_up_is_in_scope(monkeypatch):
    _mock(monkeypatch, "follow_up")
    out = relevance.relevance_node({"question": "does that add up?", "messages": []})
    assert out["is_relevant"] is True
    assert "outcome" not in out  # not refused


def test_on_topic_is_in_scope(monkeypatch):
    _mock(monkeypatch, "on_topic")
    out = relevance.relevance_node({"question": "how many films?", "messages": []})
    assert out["is_relevant"] is True


def test_out_of_scope_is_refused(monkeypatch):
    _mock(monkeypatch, "out_of_scope", "I can only answer questions about the movie database.")
    out = relevance.relevance_node({"question": "what is the weather?", "messages": []})
    assert out["is_relevant"] is False
    assert out["outcome"] == "refused"
    assert "movie database" in out["refusal_message"]

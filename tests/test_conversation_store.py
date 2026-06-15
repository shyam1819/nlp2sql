from nlp2sql.persistence.conversations import ConversationStore


def test_record_and_query(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    store.record_turn("t1", {
        "question": "how many films?",
        "rephrased_question": "How many films are in the catalog?",
        "is_relevant": True,
        "outcome": "answered",
        "required_tables": ["film"],
        "sql_query": "select count(*) from film",
        "retry_count": 0,
        "row_count": 1,
        "final_answer": "There are 1000 films.",
    })
    rows = store.recent("t1")
    assert len(rows) == 1
    assert rows[0]["outcome"] == "answered"
    assert rows[0]["tables_used"] == '["film"]'
    assert rows[0]["final_answer"] == "There are 1000 films."


def test_refusal_answer_falls_back(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    store.record_turn("t2", {"outcome": "refused", "refusal_message": "Out of scope."})
    assert store.recent("t2")[0]["final_answer"] == "Out of scope."

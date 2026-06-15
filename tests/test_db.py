import sqlite3

import pytest

from nlp2sql.cache.memory import InMemoryCache
from nlp2sql.db.connection import ReadOnlyDB
from nlp2sql.db.introspect import get_catalog, get_table_schema, render_schema


def test_select_works():
    db = ReadOnlyDB()
    rows = db.execute_select("select title from film limit 3")
    assert len(rows) == 3
    assert "title" in rows[0]


def test_writes_are_blocked_at_connection():
    db = ReadOnlyDB()
    with pytest.raises(sqlite3.OperationalError):
        db.execute_select("delete from film")


def test_catalog_has_movie_tables():
    cache = InMemoryCache()
    catalog = get_catalog(cache)
    assert "film" in catalog and "actor" in catalog


def test_schema_is_cached():
    cache = InMemoryCache()
    s1 = get_table_schema("film", cache=cache)
    assert any(c["name"] == "title" for c in s1["columns"])
    # second call must come from cache (same object identity)
    s2 = get_table_schema("film", cache=cache)
    assert s1 is s2


def test_render_schema_includes_fk():
    text = render_schema(["film_actor"])
    assert "FK" in text and "film_id" in text

from nlp2sql.sql_safety import static_guard

SAFE = [
    "select * from film limit 5",
    "SELECT f.title FROM film f JOIN film_actor fa ON f.film_id = fa.film_id LIMIT 10",
    "select count(*) from rental",
    "select 1 union select 2",
]

UNSAFE = [
    "select a from t; drop table t",
    "delete from film",
    "update film set title='x'",
    "insert into film (title) values ('x')",
    "drop table film",
    "alter table film add column x int",
    "pragma table_info(film)",
    "attach database 'x.db' as y",
    "",
]


def test_safe_queries_pass():
    for sql in SAFE:
        ok, reason = static_guard(sql)
        assert ok, f"expected safe: {sql!r} -> {reason}"


def test_unsafe_queries_blocked():
    for sql in UNSAFE:
        ok, _ = static_guard(sql)
        assert not ok, f"expected unsafe: {sql!r}"

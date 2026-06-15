"""Table catalog + schema introspection, served through the cache.

Two things the agent needs as context:
  * a short description of every table (Node 3 picks which tables to use), and
  * the column-level schema for a chosen subset (Node 4 picks columns).

Both are static for Sakila, so we read them through the cache. `warm_cache()`
is called at startup so the introspection nodes never touch SQLite at runtime.
"""

from __future__ import annotations

from ..cache import Cache, get_cache
from .connection import ReadOnlyDB

CATALOG_KEY = "catalog:all"
_SCHEMA_KEY = "schema:{table}"

# Hand-written, one-line descriptions of the Sakila movie-rental schema.
# These are the *menu* the table-selection node reads from.
TABLE_DESCRIPTIONS: dict[str, str] = {
    "film": "Catalog of films: title, description, release_year, rental_rate, length, rating, language.",
    "film_text": "Full-text mirror of film title/description (search helper).",
    "actor": "Actors: first_name, last_name. Linked to films via film_actor.",
    "film_actor": "Many-to-many join between films and actors (film_id, actor_id).",
    "category": "Film genres/categories (e.g. Action, Comedy).",
    "film_category": "Many-to-many join between films and categories (film_id, category_id).",
    "language": "Languages a film can be in (name).",
    "inventory": "Physical copies of a film held at a store (inventory_id, film_id, store_id).",
    "rental": "Rental transactions: which inventory item was rented, by which customer, when, returned when.",
    "payment": "Payments made by customers for rentals: amount, payment_date, staff_id.",
    "customer": "Customers: first_name, last_name, email, address_id, active, create_date.",
    "staff": "Store staff members: name, email, store, active.",
    "store": "Rental stores: manager_staff_id, address_id.",
    "address": "Postal addresses (address, district, city_id, postal_code, phone).",
    "city": "Cities, linked to a country (city, country_id).",
    "country": "Countries (country name).",
}


def get_catalog(cache: Cache | None = None) -> dict[str, str]:
    """Return {table: description}, cached."""
    cache = cache or get_cache()
    cached = cache.get(CATALOG_KEY)
    if cached is not None:
        return cached
    cache.set(CATALOG_KEY, TABLE_DESCRIPTIONS)
    return TABLE_DESCRIPTIONS


def get_table_schema(table: str, *, db: ReadOnlyDB | None = None,
                     cache: Cache | None = None) -> dict:
    """Return {name, columns:[{name,type,pk,notnull}], foreign_keys:[...]} for a table, cached."""
    cache = cache or get_cache()
    key = _SCHEMA_KEY.format(table=table)
    cached = cache.get(key)
    if cached is not None:
        return cached

    db = db or ReadOnlyDB()
    # PRAGMA calls are read-only and run through the same read-only connection.
    con = db._connect()
    try:
        cols = [
            {
                "name": r["name"],
                "type": r["type"],
                "notnull": bool(r["notnull"]),
                "pk": bool(r["pk"]),
            }
            for r in con.execute(f"PRAGMA table_info('{table}')")
        ]
        fks = [
            {"column": r["from"], "references": f"{r['table']}.{r['to']}"}
            for r in con.execute(f"PRAGMA foreign_key_list('{table}')")
        ]
    finally:
        con.close()

    schema = {"name": table, "columns": cols, "foreign_keys": fks}
    cache.set(key, schema)
    return schema


def render_schema(tables: list[str], *, db: ReadOnlyDB | None = None,
                  cache: Cache | None = None) -> str:
    """Render the schema of `tables` as compact text for an LLM prompt."""
    db = db or ReadOnlyDB()
    blocks: list[str] = []
    for t in tables:
        schema = get_table_schema(t, db=db, cache=cache)
        lines = [f"TABLE {t} ({TABLE_DESCRIPTIONS.get(t, '')})"]
        for c in schema["columns"]:
            flags = []
            if c["pk"]:
                flags.append("PK")
            if c["notnull"]:
                flags.append("NOT NULL")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            lines.append(f"  - {c['name']} {c['type']}{suffix}")
        for fk in schema["foreign_keys"]:
            lines.append(f"  FK {fk['column']} -> {fk['references']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def warm_cache(*, db: ReadOnlyDB | None = None, cache: Cache | None = None) -> None:
    """Pre-load catalog + every table schema so runtime never hits SQLite for metadata."""
    cache = cache or get_cache()
    db = db or ReadOnlyDB()
    get_catalog(cache)
    for table in TABLE_DESCRIPTIONS:
        get_table_schema(table, db=db, cache=cache)

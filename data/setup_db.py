"""Download the Sakila SQLite sample database into ./data.

Sakila is a movie-rental schema (film, actor, category, rental, customer,
payment, ...) — ideal for exercising multi-table selection. The file is
static, so we download once and treat it as read-only thereafter.

Usage:
    python data/setup_db.py
"""

from __future__ import annotations

import sqlite3
import sys
import urllib.request
from pathlib import Path

SAKILA_URL = (
    "https://github.com/bradleygrant/sakila-sqlite3/raw/main/sakila_master.db"
)
DEST = Path(__file__).resolve().parent / "sakila.db"


def download() -> None:
    if DEST.exists():
        print(f"[setup_db] {DEST} already exists ({DEST.stat().st_size:,} bytes); skipping download.")
        return
    print(f"[setup_db] Downloading Sakila -> {DEST} ...")
    urllib.request.urlretrieve(SAKILA_URL, DEST)
    print(f"[setup_db] Done ({DEST.stat().st_size:,} bytes).")


def verify() -> None:
    con = sqlite3.connect(DEST)
    try:
        tables = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table' order by name"
        )]
    finally:
        con.close()
    print(f"[setup_db] {len(tables)} tables: {', '.join(tables)}")
    if "film" not in tables or "actor" not in tables:
        print("[setup_db] WARNING: expected Sakila tables not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download()
    verify()

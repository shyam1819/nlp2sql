# CLAUDE.md

## Architecture guardrail

**[PROJECT.md](PROJECT.md) is the architecture charter and source of truth.**

Before implementing any change in this repo:

1. Read the **Invariants (§4)** and **Decisions log (§5)** in `PROJECT.md`.
2. If the requested change contradicts an Invariant (`INV-n`) or Decision (`D-n`),
   **flag it explicitly** before writing code — name the ID, explain the conflict,
   and ask whether to (a) rework the change, or (b) deliberately revise the charter.
3. When a change legitimately supersedes a decision, update `PROJECT.md` in the
   same change: add a new `D-n`, mark the old one `Superseded by D-n` (never delete).
4. After topology changes, regenerate `assets/graph.png` via
   `python scripts/render_graph.py`.

Do not silently let code and `PROJECT.md` diverge.

## Project quick facts

- Python package under `src/nlp2sql/`; editable install (`pip install -e ".[dev]"`).
- Run the agent: `nlp2sql` (or `nlp2sql --thread <id>`). Tests: `pytest`.
- Seed DB: `python data/setup_db.py` → `data/sakila.db` (read-only at runtime).
- Secrets/config in `.env` (see `.env.example`).

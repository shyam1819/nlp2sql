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

## Where things live

- `graph.py` — pipeline wiring + retry routing. Nodes in `nodes/` (relevance,
  clarification, rephrase, table_selection, column_selection, sql_generation,
  schema_guard, **verify**, execute, answer, ingest).
- `prompts/*.j2` — all prompt text (Jinja2; edit without code changes, INV-12).
  Structural output models in `llm/schemas.py`. LLM access via `llm/client.py`
  (`init_chat_model`, provider-agnostic, D-13).
- `metadata/` — `SemanticMetadataProvider` for table/column descriptions; sidecar
  `sakila.yaml` today, warehouse/dbt adapters later (D-15).
- `db/` — read-only connection + cached introspection. `cache/` (Cache protocol),
  `persistence/` (conversation store), `observability.py` (LangSmith).

## Editing reminders

- Prompts → edit the `.j2` file (hot-reloads); never inline prompt strings (INV-12).
- Two retry budgets: `MAX_RETRIES` (mechanical) + `LOGIC_RETRY_MAX` (semantic, D-18).
- A safe + runnable query is not assumed correct — `verify` reviews it (INV-13).
- Governance/access limits must be enforced deterministically, not via prompt (INV-14).

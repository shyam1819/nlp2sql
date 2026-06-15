# Project Objective & Architecture Charter

> **Purpose of this file.** This is the source of truth for *what this project is*
> and *why it is built the way it is*. Before merging any change, check it against
> the **Invariants** and **Decisions** below. If a change contradicts one:
> either revise the change, or update this file deliberately (see
> [Change process](#change-process)) — never let code and charter silently diverge.

---

## 1. Objective

Build an **NLP-to-SQL agent service**: a user asks a natural-language question and
gets an answer derived from a database, safely and with conversational memory.

The project is delivered in phases:

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | **Agent framework** — a reusable LangGraph graph + CLI over a movie DB | ✅ in progress |
| 2 | **FastAPI service** wrapping the same graph | ⏳ planned |
| 3 | Pluggable DB connectors beyond the seed movie DB | ⏳ planned |

The movie database (Sakila) is a **starting substrate**, not the end goal — the
architecture must not hard-code assumptions that block other databases later.

---

## 2. Architecture overview

A LangGraph `StateGraph` of single-responsibility nodes, with two retry loops and
a single terminal ingest step. See `assets/graph.png` for the rendered graph.

```
relevance(1) → clarification(1b) → rephrase(2) → table_select(3) → column_select(4)
   → sql_generation(5) ⇄ schema_guard(6) ⇄ execute(7) → answer(8) → ingest → END
```

- **Relevance/clarification** short-circuit to `ingest` (refusal / follow-up).
- **Guard (6)** and **execute (7)** loop back to **generation (5)** sharing one
  bounded retry counter.
- **Every** path ends at `ingest`, which records the turn for audit.

**Layered concerns (kept independent):**

| Concern | Interface | Now | Later |
|---|---|---|---|
| Metadata cache (schemas/descriptions) | `cache.base.Cache` | in-memory | Redis |
| Conversation memory (resume threads) | LangGraph checkpointer | SQLite | Postgres |
| Conversation audit (one row/turn) | `persistence.ConversationStore` | SQLite | Postgres |
| LLM access | `llm.client` | OpenAI | swappable |
| Observability | `observability.setup_tracing` | LangSmith (opt-in) | — |

---

## 3. Key features

- **Conversational memory** — per-thread state via the checkpointer; the rephrase
  node resolves references ("...and just for store 1?") against history.
- **Defense-in-depth SQL safety** — three independent layers (see INV-2).
- **Self-correcting generation** — guard/execution feedback is fed back to the
  generator within a bounded retry budget.
- **Relevance gating & clarification** — out-of-scope questions are refused;
  ambiguous ones trigger a single follow-up.
- **Complete audit trail** — every turn (answered/refused/clarified/failed) is
  persisted with its SQL, tables, retries, and outcome.
- **Cached introspection** — table metadata is served from cache, warmed at startup.
- **Tracing** — opt-in LangSmith traces of every node, LLM call, and retry.

---

## 4. Invariants  *(non-negotiable; a change that breaks one needs explicit charter revision)*

- **INV-1 — Read-only data access.** No node may open the queried DB writably.
  Writes are blocked at the connection (`mode=ro`), not just by prompts.
- **INV-2 — Only single `SELECT` executes.** Enforced by three independent layers:
  (1) read-only connection, (2) static `sqlparse` guard, (3) LLM guard. Removing
  any layer weakens, not duplicates — keep all three.
- **INV-3 — Bounded, shared retry budget.** Generation↔guard↔execute loops share
  one counter capped at `MAX_RETRIES`. No unbounded loops.
- **INV-4 — Single terminal sink.** Every turn terminates through `ingest`; the
  audit log must never have gaps for refused/clarified/failed turns.
- **INV-5 — Cached metadata.** Schemas/descriptions are accessed through the
  `Cache` interface, never by direct SQLite calls at request time.
- **INV-6 — Memory ≠ audit.** The checkpointer (resume) and the conversation
  store (analytics) are separate; wiping one must not corrupt the other.
- **INV-7 — Depend on interfaces, not backends.** Cache, conversation store, and
  LLM are reached through their abstractions so backends swap via config.
- **INV-8 — Strict-mode-safe schemas.** Structured-output models must be valid
  under OpenAI strict mode — no open-ended `dict`; use list-of-objects.
- **INV-9 — Clean per-turn state.** All per-turn derived fields are reset each
  turn; only `messages` and `thread_id` persist. `query_result=None` means
  "not executed" (distinct from `[]` = executed, empty).
- **INV-10 — UI-agnostic core.** `build_graph()` knows nothing about CLI or HTTP;
  every front-end (CLI now, FastAPI later) consumes the same graph unchanged.
- **INV-11 — DB-substrate independence.** No node hard-codes Sakila specifics
  beyond the swappable catalog/introspection layer.
- **INV-12 — Prompts live in files, not code.** LLM prompt *text and
  presentation logic* live in `prompts/*.j2` (Jinja2) and are loaded via
  `llm.prompts.render`. Nodes must not inline prompt strings or build
  prompt-facing strings (lists/conditionals belong in the template); nodes pass
  raw data. Structural schemas stay in `llm/schemas.py`.

---

## 5. Decisions log  *(supersede, don't silently rewrite)*

| ID | Decision | Status | Rationale / alternatives |
|----|----------|--------|--------------------------|
| D-1 | **LangGraph** as the agent framework | Accepted | Native stateful nodes, conditional edges, retry loops, checkpointers. Alt: Google ADK (thinner loop/memory story). |
| D-2 | **Sakila (SQLite)** as the seed DB | Accepted | Canonical multi-table movie schema, single file, no server. Alt: IMDb/TMDB (flatter, heavier), Chinook (not movies). |
| D-3 | **OpenAI** as default LLM provider | Accepted | Project default. Reached only via `llm.client` (INV-7), now provider-agnostic per D-13. |
| D-4 | **SQLite checkpointer** for memory | Accepted | Survives restarts, no infra. → Postgres in Phase 2. |
| D-5 | **Cache abstraction**, in-memory now | Accepted | `Cache` protocol; Redis is a config swap. Redis deferred per request. |
| D-6 | **Separate conversation store** (SQLite) | Accepted | Audit/analytics distinct from checkpointing (INV-6). → Postgres later. |
| D-7 | **3-layer SQL safety** | Accepted | Connection wall + static parse + LLM guard (INV-2). |
| D-8 | **Shared retry counter, cap 2** | Accepted | One budget across guard+execute (INV-3). |
| D-9 | **Turn-based clarification** (not `interrupt()`) | Accepted | One HTTP request = one turn; resumes via memory. Simpler for Phase 2 API. Revisit if strict pause semantics are needed. |
| D-10 | **All paths route through `ingest`** | Accepted | Complete audit trail (INV-4). |
| D-11 | **LangSmith tracing, opt-in** | Accepted | Off by default; enabled via `.env`. |
| D-12 | **List-of-objects over dicts** in structured outputs | Accepted | OpenAI strict mode rejects open-ended dicts (INV-8). |
| D-13 | **LLM access via LangChain `init_chat_model`** (not the raw `openai` SDK) | Accepted | Provider swap becomes a config change (`LLM_PROVIDER`), realizing INV-7; LangSmith captures token usage natively (removes the `wrap_openai` patch). Structured outputs pinned to `with_structured_output(method="json_schema", strict=True)` to preserve INV-8/D-12. Formalizes the previously-undocumented raw-SDK choice. |
| D-14 | **Prompts externalized to `prompts/*.j2` (Jinja2)**, loaded by `llm.prompts.render` | Accepted | Prompt tuning needs no code change (INV-12). Jinja2 chosen over plain substitution so conditionals (retry feedback) and loops (catalog/column lists) live in templates, not nodes — nodes pass raw data. `auto_reload` hot-reload, `StrictUndefined` surfaces typos, `{{ domain }}` auto-injected. Override dir via `PROMPTS_DIR`. Schemas in `llm/schemas.py`. (Superseded the initial manual `{{var}}` loader.) |

---

## 6. Out of scope (for now)

- Write/DDL operations of any kind against the queried DB.
- Non-`SELECT` analytics (stored procedures, multi-statement scripts).
- Authentication / multi-tenant isolation (arrives with the FastAPI phase).
- Redis and Postgres backends (interfaces exist; implementations deferred).

---

## 7. Change process

1. **Before coding**, scan §4 and §5. Does the change contradict an INV or D?
2. **If it contradicts an Invariant** — stop. Either rework the change, or, if the
   invariant itself is wrong, revise §4 in the same PR with justification.
3. **If it supersedes a Decision** — add a new `D-n` row and mark the old one
   `Superseded by D-n`. Do not delete history.
4. **If it adds a new architectural choice** — record it as a new `D-n`.
5. Keep `assets/graph.png` in sync when topology changes
   (`python scripts/render_graph.py`).

> When in doubt, cite the ID you're touching (e.g. "relaxes D-8") in the commit/PR.

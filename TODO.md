# TODO

Open threads for the nlp2sql agent. Check each change against the charter
(`PROJECT.md` §4 Invariants / §5 Decisions) before implementing. Grouped by
status; mirrors the in-session task list.

---

## Completed

- **Relevance guard made history-aware** — follow-ups (verify / drill-down) stay
  in scope; out-of-scope still refused. (D-20)
- **Query-planning node before SQL generation** — typed `QueryPlan`; drives
  grain-first fan-out mitigation. (D-21)

---

## Active — perfecting the technical model

### A. Audit & adopt proven agentic design patterns  *(broad — design note first)*

Map the agent against proven agentic patterns, then fill the high-value gaps.
First deliverable: a short design note + a `PROJECT.md` decision; then implement
incrementally, each config-gated and off by default.

- **Already present** (don't redo): prompt chaining, routing (relevance/
  clarification), reflection / evaluator-optimizer (verify 6b + retries),
  human-in-the-loop (clarification), planning (Task #2).
- **Gaps to add, prioritized:**
  1. **Tool use / grounding** *(biggest analytics win)* — read-only tools to
     inspect the DB instead of guessing: distinct column values (resolve filter
     literals like `'Comedy'`, `'PG-13'`), sample rows, sanity COUNTs. Stops
     invented WHERE values. Stays within INV-1/INV-2/INV-14.
  2. **Self-consistency** — sample N candidate SQLs, execute, pick by result
     consensus / verifier score. Configurable N (default 1 = off).
  3. **Episodic / long-term memory** — persist successful question→SQL pairs;
     reuse as exemplars and as a repeat-question cache. Distinct from
     conversation memory (INV-6).
  4. **Decomposition / orchestrator** — split complex multi-part questions into
     sub-queries, solve, compose.

### B. Collect a concrete analytics dataset (demo + eval)  *(do before C)*

Sakila is fine for dev but small/OLTP-shaped. For analytics demo + evaluation we
need a realistic analytical dataset and a labeled question set:

1. **Analytics demo DB** — star/snowflake (fact + dimensions, time dimension, real
   volume). Candidates: **TPC-H / TPC-DS** (canonical analytical benchmarks,
   generatable via **DuckDB** at any scale — columnar/OLAP, supports our CTE/window
   SQL, aligns with the connector layer), Contoso Retail DW, or Olist e-commerce
   (Kaggle). Ship with a D-15 metadata sidecar.
2. **Eval set** — `question → gold SQL → expected result`. Adopt a benchmark
   (**BIRD** = most analytics/real-world; **Spider** = cross-domain standard) or
   hand-curate ~30–50 golden analytical questions across the archetypes (lookup,
   aggregate, top-N, time series, share-of-total, period-over-period, threshold,
   distribution), incl. fan-out traps, with verified SQL + results.

Decide in `PROJECT.md`: which demo DB + eval set, and DuckDB vs SQLite for eval.

### C. Evaluation framework (analytics correctness)  *(needs B)*

Automated harness to run the agent over the golden set and score it — so we
measure (not guess) whether planning/verify improve accuracy, and catch
regressions.

- **Execution accuracy** (primary): agent result set vs gold result set —
  order-insensitive, float-tolerant. Right metric since many SQLs are correct.
- **Component metrics**: table-selection precision/recall, verifier catch-rate &
  false-positive rate, retry counts (mechanical vs logic), truncation rate.
- **Cost/latency**: tokens + wall-time per question (LangSmith has tokens).
- **Per-archetype breakdown** to expose weak spots.
- Reuse `run_turn()` / `build_graph()`; emit a scored JSON + summary; keep an
  offline pytest-invokable subset; optionally wire LangSmith datasets/evaluators.

---

## Future add-ons  *(deferred until the core model is solid)*

### Few-shot exemplars + retrieval for table selection  *(scaling, not core correctness)*

`table_selection` does single-shot selection from a flat catalog — degrades on
large warehouse schemas. Add: (1) retrieval/schema-linking so only candidate
tables (similarity to the question) are presented; (2) few-shot known-good
question→SQL exemplars. Keep pluggable: off for small schemas, on for large.
(Deferred half of D-19.)

### Connector layer for warehouse execution (dialect)  *(large — own milestone)*

`SQL_DIALECT` (D-17) currently parameterizes only the prompt; execution is still
SQLite. Build a `Connector` interface (connect, execute_select, explain,
introspect, `get_column_descriptions` per D-15) with per-engine adapters
(Postgres / Snowflake / Databricks / BigQuery / DuckDB), selected by config. Must
preserve INV-1/INV-2 per engine. Where native-comment metadata adapters (D-15) and
the deterministic governance/policy gate (INV-14) plug in.

### Meta/catalog discoverability path  *(fit not yet clear)*

A deliberate path for meta questions ("what tables/data are available?", "what can
I ask?") answered directly from curated metadata (`get_catalog()` + D-15
descriptions + example questions), NO SQL. Extend the relevance classifier (D-20)
with a `meta` category → a describe node. Bonus: block `SELECT ... FROM
sqlite_master` in the guard. Revisit when discoverability/onboarding matters.

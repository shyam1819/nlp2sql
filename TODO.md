# TODO

Open threads for the nlp2sql agent. Check each change against the charter
(`PROJECT.md` §4 Invariants / §5 Decisions) before implementing.

## 1. Fix topic/relevance guard refusing genuine follow-ups  *(bug — do first)*

The relevance node ([nodes/relevance.py](src/nlp2sql/nodes/relevance.py)) refuses
legitimate follow-ups that reference prior results — e.g. *"Does this revenue add
up to the total revenue, verify that?"*

- **Root cause:** `relevance_node` is the only early node that does **not** receive
  conversation history (clarification + rephrase both use `format_history()`), so a
  verification/drill-down question with no DB nouns looks out-of-scope and is refused.
- **Fix:** pass history into the node; update `prompts/relevance.*.j2` to treat
  follow-ups about prior answers (verify, "does this add up", "why", "break that
  down") as in-scope when the thread is already on-topic. Keep refusing genuinely
  unrelated questions (weather, math).
- **Test:** a multi-turn thread where turn 2 is a verification follow-up must NOT be refused.

## 2. Add a query-planning node before SQL generation

Insert a planner between `column_selection` (4) and `sql_generation` (5) that emits
a **plan / pseudocode** (tables/joins, grain, aggregations, filters, grouping,
ordering, fan-out de-dup) — **not** SQL. `sql_generation` then translates the plan
into dialect SQL, focused purely on syntax.

- Separates "what to compute" from "how to write it" → better complex-query accuracy.
- Gives the **verify node (6b)** an explicit plan to check the SQL against (pairs
  well with the correctness pass we just built).
- New: `nodes/plan.py`, `prompts/plan.system.j2` + `plan.user.j2`, a `query_plan`
  state field; wire `column_selection → plan → sql_generation`; include the plan in
  `sql_generation.user.j2`. Record as a decision in `PROJECT.md`.

## 3. P3: few-shot exemplars + retrieval for table selection  *(deferred half of D-19)*

`table_selection` (3) does single-shot selection from a flat catalog — degrades on
large warehouse schemas. Add: (1) retrieval/schema-linking so only candidate tables
(similarity to the question) are presented; (2) few-shot known-good question→SQL
exemplars. Keep pluggable: off for small Sakila, on for large schemas. Record a decision.

## 4. Connector layer for warehouse execution (dialect)  *(large — own milestone)*

`SQL_DIALECT` (D-17) currently parameterizes only the prompt; execution is still
SQLite. Build a `Connector` interface (connect, execute_select, explain, introspect,
`get_column_descriptions` per D-15) with per-engine adapters (Postgres / Snowflake /
Databricks / BigQuery), selected by config. Must preserve INV-1/INV-2 per engine.
This is where native-comment metadata adapters (D-15) and the deterministic
governance/policy gate (INV-14) plug in.

## 5. Audit & adopt proven agentic design patterns  *(broad — design note first)*

Map the agent against proven agentic patterns, then fill the high-value gaps.
First deliverable: a short design note + a `PROJECT.md` decision mapping patterns
to the graph; then implement incrementally, each config-gated and off by default.

- **Already present** (don't redo): prompt chaining (node pipeline), routing
  (relevance/clarification), reflection / evaluator-optimizer (verify node 6b +
  retries), human-in-the-loop (clarification).
- **Overlaps:** planning = Task #2; RAG / schema-linking + exemplars = Task #3.
- **Gaps to add, prioritized:**
  1. **Tool use / grounding** *(biggest analytics win)* — read-only tools to
     inspect the DB instead of guessing: distinct column values (resolve filter
     literals like `'Comedy'`, `'PG-13'`), sample rows, sanity COUNTs. Stops
     invented WHERE values. Stays within INV-1/INV-2/INV-14.
  2. **Self-consistency** — sample N candidate SQLs, execute, pick by result
     consensus / verifier score. Configurable N (default 1 = off).
  3. **Episodic / long-term memory** — persist successful question→SQL pairs;
     reuse as exemplars (feeds #3) and as a repeat-question cache. Distinct from
     conversation memory (INV-6).
  4. **Decomposition / orchestrator** — split complex multi-part questions into
     sub-queries, solve, compose.

## 6. Collect a concrete analytics dataset (demo + eval)  *(do before #7)*

Sakila is fine for dev but small/OLTP-shaped. For analytics demo + evaluation we
need a realistic analytical dataset and a labeled question set:

1. **Analytics demo DB** — star/snowflake (fact + dimensions, time dimension, real
   volume). Candidates: **TPC-H / TPC-DS** (canonical analytical benchmarks,
   generatable via **DuckDB** at any scale — columnar/OLAP, supports our CTE/window
   SQL, aligns with the connector layer #4), Contoso Retail DW, or Olist e-commerce
   (Kaggle). Ship with a D-15 metadata sidecar.
2. **Eval set** — `question → gold SQL → expected result`. Adopt a benchmark
   (**BIRD** = most analytics/real-world; **Spider** = cross-domain standard) or
   hand-curate ~30–50 golden analytical questions across the archetypes (lookup,
   aggregate, top-N, time series, share-of-total, period-over-period, threshold,
   distribution), incl. fan-out traps, with verified SQL + results.

Decide in `PROJECT.md`: which demo DB + eval set, and DuckDB vs SQLite for eval.

## 7. Evaluation framework (analytics correctness)  *(needs #6)*

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

## Future add-ons

### Meta/catalog discoverability path  *(deferred — fit not yet clear)*

A deliberate path for meta questions ("what tables/data are available?", "what can
I ask?", "what do you know about customers?") answered directly from curated
metadata (`get_catalog()` + D-15 descriptions + example questions), NO SQL. Extend
the relevance classifier (D-20) with a `meta` category → a describe node. Bonus:
block `SELECT ... FROM sqlite_master` in the guard (currently leaks system schema).
Today meta questions are handled accidentally/inconsistently. Revisit when
discoverability/onboarding becomes a priority.

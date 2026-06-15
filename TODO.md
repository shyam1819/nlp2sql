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

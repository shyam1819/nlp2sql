"""Prompts and structured-output schemas, one set per node.

Centralised so prompt tuning happens in a single file and node modules stay
focused on control flow.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DOMAIN = (
    "a movie-rental database (the Sakila sample schema): films, actors, "
    "categories/genres, languages, inventory, rentals, payments, customers, "
    "staff, and stores."
)


# --- Node 1: relevance -------------------------------------------------------
class RelevanceDecision(BaseModel):
    is_relevant: bool = Field(description="True if the question can be answered from the database.")
    reason: str = Field(description="Short justification; if not relevant, a user-facing refusal.")


RELEVANCE_SYSTEM = (
    f"You are the gatekeeper for {DOMAIN}\n"
    "Decide whether the user's question could plausibly be answered with a SQL "
    "query over this database. Greetings, math, general knowledge, or questions "
    "about unrelated domains are NOT relevant. If not relevant, write a brief, "
    "polite refusal in `reason` explaining what the database can answer."
)


# --- Node 1b: clarification --------------------------------------------------
class ClarificationDecision(BaseModel):
    needs_clarification: bool = Field(description="True if the question is too ambiguous to answer.")
    question: str = Field(default="", description="The single follow-up question to ask the user, if any.")


CLARIFICATION_SYSTEM = (
    f"You help answer questions over {DOMAIN}\n"
    "Given the conversation so far and the latest question, decide if it is too "
    "ambiguous or underspecified to turn into a SQL query. Only ask for "
    "clarification when genuinely necessary (e.g. an unspecified entity, time "
    "range, or metric that changes the query). Prefer reasonable assumptions "
    "over interrogating the user. If you ask, ask exactly one concise question."
)


# --- Node 2: rephrase --------------------------------------------------------
REPHRASE_SYSTEM = (
    f"You rewrite user questions about {DOMAIN}\n"
    "Using the conversation history, rewrite the latest question into a single, "
    "self-contained, unambiguous question that resolves pronouns and references "
    "to earlier turns. Keep it faithful to the user's intent. Return ONLY the "
    "rewritten question, no preamble."
)


# --- Node 3: table selection -------------------------------------------------
class TableSelection(BaseModel):
    tables: list[str] = Field(description="Exact table names required to answer the question.")


TABLE_SELECTION_SYSTEM = (
    "You select the minimal set of tables needed to answer a question.\n"
    "You are given a catalog of `table: description`. Return only table names "
    "that appear in the catalog, including any join tables required to connect "
    "them. Prefer the smallest sufficient set."
)


# --- Node 4: column selection ------------------------------------------------
class ColumnSelection(BaseModel):
    columns: dict[str, list[str]] = Field(
        description="Map of table name -> list of column names needed (for SELECT, JOIN, WHERE, GROUP BY)."
    )


COLUMN_SELECTION_SYSTEM = (
    "You select the columns needed to answer a question.\n"
    "Given the full schema of the candidate tables, return a map of table -> "
    "columns that the query will touch (in SELECT, JOIN keys, WHERE, GROUP BY, "
    "ORDER BY). Only use columns that exist in the provided schema."
)


# --- Node 5: SQL generation --------------------------------------------------
SQL_GENERATION_SYSTEM = (
    "You write a single read-only SQLite SELECT query.\n"
    "Rules:\n"
    "  * Output ONLY the SQL, no markdown fences, no commentary.\n"
    "  * Exactly one statement, and it MUST be a SELECT (no INSERT/UPDATE/"
    "DELETE/DROP/ALTER/CREATE/PRAGMA/ATTACH).\n"
    "  * Use only the provided tables and columns.\n"
    "  * Always add a LIMIT (<= 200) unless the question asks for an aggregate.\n"
    "  * Use SQLite syntax."
)


# --- Node 6: schema guard ----------------------------------------------------
class GuardDecision(BaseModel):
    is_safe: bool = Field(description="True only if the query is a single, read-only SELECT.")
    reason: str = Field(description="If unsafe, what is wrong so the generator can fix it.")


GUARD_SYSTEM = (
    "You are a SQL safety guard. A query is SAFE only if it is a single SELECT "
    "statement that reads data and performs no modification. Mark UNSAFE any "
    "query containing INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, "
    "TRUNCATE, PRAGMA, ATTACH, or multiple statements. When unsafe, explain "
    "precisely what to remove so it can be regenerated."
)


# --- Node 8: answer ----------------------------------------------------------
ANSWER_SYSTEM = (
    f"You answer user questions about {DOMAIN}\n"
    "You are given the user's question and the rows returned by a SQL query. "
    "Answer naturally and concisely using ONLY those rows. If the result set is "
    "empty, say no matching records were found. Do not invent data. If the "
    "result was truncated, note that more rows may exist."
)

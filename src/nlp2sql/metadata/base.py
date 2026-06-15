"""Provider contract for semantic descriptions, and a composite that merges
several sources by priority.

A provider answers two questions for a table:
  * `table_description(table)`   -> a one-line description, or None
  * `column_descriptions(table)` -> {column: description} (may be partial/empty)

Adapters (file sidecar now; dbt/catalog/native-comment later) implement this so
the introspection layer never depends on where descriptions come from.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SemanticMetadataProvider(Protocol):
    def table_description(self, table: str) -> str | None: ...

    def column_descriptions(self, table: str) -> dict[str, str]: ...


class CompositeMetadataProvider:
    """Merge providers by priority: earlier providers win.

    For table descriptions, the first non-empty result is used. For columns,
    lower-priority maps are applied first and higher-priority ones override,
    so a curated source beats a generic one key-by-key.
    """

    def __init__(self, providers: list[SemanticMetadataProvider]) -> None:
        self.providers = providers

    def table_description(self, table: str) -> str | None:
        for provider in self.providers:
            description = provider.table_description(table)
            if description:
                return description
        return None

    def column_descriptions(self, table: str) -> dict[str, str]:
        merged: dict[str, str] = {}
        for provider in reversed(self.providers):  # low priority first
            merged.update(provider.column_descriptions(table))
        return merged

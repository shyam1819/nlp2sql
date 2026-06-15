"""File sidecar provider — descriptions in a YAML/JSON file alongside the app.

This is the right fit for databases without native column comments (SQLite), and
a useful override anywhere. Shape:

    film:
      description: "Catalog of films available to rent."
      columns:
        title: "Display title of the film."
        rental_rate: "Cost to rent the film for one rental_duration period (USD)."

Missing tables/columns simply yield no description (the schema still renders).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class SidecarMetadataProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = self._load(self.path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(text) or {}
        if path.suffix == ".json":
            return json.loads(text or "{}")
        raise ValueError(f"Unsupported sidecar format: {path.suffix!r}")

    def table_description(self, table: str) -> str | None:
        entry = self._data.get(table)
        if isinstance(entry, dict):
            return entry.get("description")
        return None

    def column_descriptions(self, table: str) -> dict[str, str]:
        entry = self._data.get(table)
        if isinstance(entry, dict):
            cols = entry.get("columns") or {}
            return {k: str(v) for k, v in cols.items()}
        return {}

"""Semantic metadata: column/table *descriptions* for the agent's schema context.

Descriptions are sourced through a `SemanticMetadataProvider`, not hard-wired to
DB introspection (D-15). Today the only adapter is a file sidecar (the natural
fit for SQLite, which has no native column comments). Warehouse engines that DO
expose comments natively — Snowflake / Databricks / BigQuery `COMMENT`, SQL
Server extended properties — plus dbt/catalog sources, slot in later as
additional adapters in the composite, highest business value first.
"""

from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from .base import CompositeMetadataProvider, SemanticMetadataProvider
from .sidecar import SidecarMetadataProvider

# Sidecar shipped for the Sakila/SQLite seed DB.
_PACKAGE_METADATA = Path(__file__).resolve().parent / "sakila.yaml"

_provider: SemanticMetadataProvider | None = None


def get_metadata_provider() -> SemanticMetadataProvider:
    """Process-wide provider. Composite so warehouse/catalog adapters add later."""
    global _provider
    if _provider is not None:
        return _provider

    configured = get_settings().metadata_path
    path = Path(configured) if configured else _PACKAGE_METADATA

    providers: list[SemanticMetadataProvider] = []
    if path.exists():
        providers.append(SidecarMetadataProvider(path))
    # Future, in priority order (highest business value first):
    #   providers.insert(0, CatalogMetadataProvider(...))   # dbt / Unity / Snowflake
    #   providers.append(NativeCommentProvider(connector))  # engine COMMENT / ext props

    _provider = CompositeMetadataProvider(providers)
    return _provider


__all__ = [
    "SemanticMetadataProvider",
    "CompositeMetadataProvider",
    "SidecarMetadataProvider",
    "get_metadata_provider",
]

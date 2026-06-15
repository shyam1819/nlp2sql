"""Semantic metadata provider — sidecar, composite priority, schema enrichment."""

from nlp2sql.cache.memory import InMemoryCache
from nlp2sql.db.introspect import render_schema
from nlp2sql.metadata import get_metadata_provider
from nlp2sql.metadata.base import CompositeMetadataProvider
from nlp2sql.metadata.sidecar import SidecarMetadataProvider


def test_sidecar_reads_descriptions():
    p = get_metadata_provider()
    assert "Payments" in (p.table_description("payment") or "")
    cols = p.column_descriptions("payment")
    assert "amount" in cols and "revenue" in cols["amount"].lower()


def test_missing_table_or_column_is_empty():
    p = get_metadata_provider()
    assert p.table_description("does_not_exist") is None
    assert p.column_descriptions("does_not_exist") == {}


def test_render_schema_includes_column_descriptions():
    text = render_schema(["payment"], cache=InMemoryCache())
    assert "amount DECIMAL" in text
    assert "— Payment amount" in text  # the description note


def test_render_schema_unknown_columns_have_no_note(tmp_path):
    # last_update has no sidecar entry: it must still render, just without a note.
    text = render_schema(["payment"], cache=InMemoryCache())
    assert "last_update TIMESTAMP" in text


def test_composite_priority(tmp_path):
    high = tmp_path / "high.yaml"
    low = tmp_path / "low.yaml"
    high.write_text("film:\n  columns:\n    title: HIGH\n")
    low.write_text("film:\n  description: low-desc\n  columns:\n    title: LOW\n    note: only-low\n")
    comp = CompositeMetadataProvider([
        SidecarMetadataProvider(high),  # higher priority first
        SidecarMetadataProvider(low),
    ])
    cols = comp.column_descriptions("film")
    assert cols["title"] == "HIGH"      # high overrides low
    assert cols["note"] == "only-low"   # low-only key preserved
    assert comp.table_description("film") == "low-desc"  # first non-empty wins

"""Conversation ingestion — a queryable record of every turn."""

from __future__ import annotations

from ..config import get_settings
from .conversations import ConversationStore

_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore(get_settings().conversation_db_path)
    return _store


__all__ = ["ConversationStore", "get_conversation_store"]

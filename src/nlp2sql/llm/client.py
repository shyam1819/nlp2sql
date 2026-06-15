"""Provider-agnostic LLM access for the nodes.

  * `parse(...)`    -> a typed pydantic object (structured routing/guard nodes)
  * `complete(...)` -> free text (rephrase, SQL generation, final answer)

We go through LangChain's `init_chat_model`, so adding another provider later is
a *config change* (`LLM_PROVIDER=anthropic`, set that provider's API key), not a
code change — nodes keep calling `parse`/`complete` unchanged. Because the model
is a LangChain chat model, LangSmith captures each call with token usage
automatically (no manual SDK wrapping needed).

Structured outputs use strict `json_schema` mode, which keeps the constraint
that response schemas contain no open-ended dicts (INV-8 / D-12).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..config import get_settings

T = TypeVar("T", bound=BaseModel)


@lru_cache
def _model() -> BaseChatModel:
    settings = get_settings()
    # Make the provider's key visible to the integration package via env.
    # (Other providers set their own *_API_KEY in .env; add them here as needed.)
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set; configure it in .env.")
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    return init_chat_model(
        settings.llm_model,
        model_provider=settings.llm_provider,
        temperature=settings.llm_temperature,
    )


def parse(system: str, user: str, schema: type[T]) -> T:
    """Structured output: returns an instance of `schema` (strict json_schema)."""
    structured = _model().with_structured_output(schema, method="json_schema", strict=True)
    return structured.invoke([SystemMessage(content=system), HumanMessage(content=user)])


def complete(system: str, user: str) -> str:
    """Free-text completion."""
    response = _model().invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = response.content
    return content.strip() if isinstance(content, str) else str(content).strip()

"""Thin OpenAI wrapper with two modes used by the nodes:

  * `parse(...)`    -> a typed pydantic object (structured routing/guard nodes)
  * `complete(...)` -> free text (rephrase, SQL generation, final answer)

Keeping this in one place means the model id and client construction live in a
single spot, and nodes depend on an interface rather than the SDK directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from ..config import get_settings

T = TypeVar("T", bound=BaseModel)


@lru_cache
def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; configure it in .env.")
    return OpenAI(api_key=settings.openai_api_key)


def parse(system: str, user: str, schema: type[T], *, temperature: float = 0.0) -> T:
    """Structured output: the model must return JSON matching `schema`."""
    completion = _client().beta.chat.completions.parse(
        model=get_settings().openai_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=schema,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:  # refusal or empty parse
        raise RuntimeError("Model returned no parsable structured output.")
    return parsed


def complete(system: str, user: str, *, temperature: float = 0.0) -> str:
    """Free-text completion."""
    completion = _client().chat.completions.create(
        model=get_settings().openai_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (completion.choices[0].message.content or "").strip()

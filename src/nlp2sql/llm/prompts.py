"""Prompt loader — prompt *text and presentation logic* live in Jinja2 templates
under `prompts/`, not in code.

Nodes call `render("<name>", **context)` to get a prompt string. Because the
templates are Jinja2, not only the wording but also conditionals (retry
feedback) and loops (catalog/column lists) live in the files — so prompt
behaviour can be tuned without a code change. `{{ domain }}` is injected into
every render from `fragments/domain.j2`.

Layout (default: the package's `prompts/` dir; override with PROMPTS_DIR):
    prompts/<node>.system.j2      system prompt for a node
    prompts/<node>.user.j2        user-message template for a node
    prompts/fragments/*.j2        shared snippets (e.g. domain)

The environment uses `auto_reload`, so editing a template takes effect on the
next render with no process restart. `StrictUndefined` surfaces a missing
variable as an error rather than silently emitting a blank.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..config import get_settings

_PACKAGE_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache
def _env() -> Environment:
    configured = get_settings().prompts_dir
    base = Path(configured) if configured else _PACKAGE_PROMPTS
    return Environment(
        loader=FileSystemLoader(str(base)),
        auto_reload=True,            # hot-reload templates on edit, no restart
        undefined=StrictUndefined,   # missing variables raise, not silently blank
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )


def _domain() -> str:
    return _env().get_template("fragments/domain.j2").render().strip()


def render(name: str, **context: object) -> str:
    """Render prompt template `name` (without the .j2 suffix) with `context`.

    `domain` is always available to the template; explicit context overrides it.
    """
    template = _env().get_template(f"{name}.j2")
    return template.render(domain=_domain(), **context).strip()

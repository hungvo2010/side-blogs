"""Versioned prompt loader — the single place that resolves a prompt by name
from ``prompts/<version>/<name>.txt`` and renders its ``{placeholders}``.

Versions live in folders under ``prompts/`` (e.g. ``prompts/v1/``,
``prompts/v2/``), mirroring the pipeline's phase structure:

    prompts/v1/
      brief/       section_generation, lsi_keywords, unique_angle
      draft/       outline, article_user, revision_system, revision_user
      factcheck/   claim_extraction, claim_verification
      seo/         meta_title, meta_description
      layouts/     block_selection, block_regenerate

Switching the whole pipeline to a new prompt set is a data-only change: drop
``prompts/v2/`` and set ``PROMPT_VERSION=v2`` (or pass ``version=`` per call).
No phase code needs editing.

Usage::

    from blog_automation.prompting import Prompts, render_prompt

    out = render_prompt("brief/section_generation",
                        keyword=kw, intent=it, difficulty=30, volume=6500,
                        competitor_h2s="...")
    raw = Prompts().get("draft/article_user")          # template, unfilled

Templates are ``str.format`` templates — keep literal JSON braces escaped as
``{{`` / ``}}`` (same as the old inline constants).
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

# prompts/ sits at the repo root: <repo>/src/blog_automation/prompting.py
# -> parents[0]=blog_automation, parents[1]=src, parents[2]=repo
PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts"
DEFAULT_VERSION = os.environ.get("PROMPT_VERSION", "v1")


class PromptError(FileNotFoundError):
    """A named prompt template could not be loaded."""


@functools.lru_cache(maxsize=256)
def _load(base: Path, version: str, rel: str) -> str:
    path = base / version / f"{rel}.txt"
    if not path.is_file():
        avail = ", ".join(
            sorted(
                str(p.relative_to(base / version))
                for p in (base / version).rglob("*.txt")
            )
        )
        raise PromptError(
            f"Prompt '{rel}' not found under {base / version}/. "
            f"Available in this version: {avail or '(none)'}"
        )
    return path.read_text(encoding="utf-8")


class Prompts:
    """Resolve and render versioned prompt templates.

    ``name`` is the path under ``prompts/<version>/`` (with or without the
    ``.txt`` suffix), e.g. ``"brief/section_generation"``. The active version
    is set per-instance (default from ``PROMPT_VERSION``) and can be overridden
    per call via ``version=``.
    """

    def __init__(
        self, base: Path = PROMPTS_ROOT, version: str = DEFAULT_VERSION
    ) -> None:
        self.base = Path(base)
        self.version = version

    def get(self, name: str, *, version: str | None = None) -> str:
        """Return the raw (unfilled) template for ``name``."""
        ver = version or self.version
        return _load(self.base, ver, name)

    def render(
        self, name: str, *, version: str | None = None, **variables: object
    ) -> str:
        """Load ``name`` (at ``version``) and fill its ``{placeholders}``."""
        return self.get(name, version=version).format(**variables)


# Shared instance + module-level convenience helper so phases just do:
#     from blog_automation.prompting import render_prompt
#     prompt = render_prompt("seo/meta_title", keyword=kw, ...)
prompts = Prompts()


def render_prompt(name: str, *, version: str | None = None, **variables: object) -> str:
    """Render a prompt template with the shared default-version loader."""
    return prompts.render(name, version=version, **variables)

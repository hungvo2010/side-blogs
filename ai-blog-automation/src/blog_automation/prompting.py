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

# --- Output-language pin ---------------------------------------------------
# No prompt ever stated which language to write in, so the model mirrored the
# input: the Vietnamese keyword "ca phe muoi" produced a fully Vietnamese
# article (title, body, meta) on an English site (SITE_LANG=en). Pin the
# publication language on EVERY rendered prompt instead of trusting the model.
LANGUAGE_NAMES = {
    "en": "English",
    "vi": "Vietnamese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "th": "Thai",
    "id": "Indonesian",
}


def language_name(lang: str | None = None) -> str:
    """Human-readable publication language, from ``lang`` or ``SITE_LANG``."""
    code = (lang or os.environ.get("SITE_LANG") or "en").strip().lower()
    code = code.split("-")[0].split("_")[0]
    return LANGUAGE_NAMES.get(code, code or "en")


def language_directive(lang: str | None = None) -> str:
    """One-line instruction that keeps every phase in the publication language."""
    name = language_name(lang)
    return (
        f"Language rule: write ALL output in {name} — the publication's language. "
        f"Never switch language to match the keyword, the sources or the locale. "
        f"Keep proper nouns and brand names in their original form."
    )


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
        """Load ``name`` (at ``version``) and fill its ``{placeholders}``.

        Every rendered prompt is prefixed with the publication-language rule so
        no phase can drift into the keyword's language (see ``language_directive``).
        """
        body = self.get(name, version=version).format(**variables)
        return f"{language_directive()}\n\n{body}"


# Shared instance + module-level convenience helper so phases just do:
#     from blog_automation.prompting import render_prompt
#     prompt = render_prompt("seo/meta_title", keyword=kw, ...)
prompts = Prompts()


def render_prompt(name: str, *, version: str | None = None, **variables: object) -> str:
    """Render a prompt template with the shared default-version loader."""
    return prompts.render(name, version=version, **variables)

"""Reusable layout components (block-based layouts) for the blog.

Concept
-------
A *layout component* is a small, self-contained, reusable piece of rendered
HTML. Any content (article, homepage, card, landing) is composed of these
components. Because each component is a plain Python renderer keyed by a
stable ``id``, the SAME component can be reused in many places, and any
authoring layer — including an LLM — can emit these components as structured
JSON blocks that ``render_blocks()`` turns into HTML.

Authoring
---------
Blocks can be authored two ways:

1. Frontmatter ``blocks:`` (JSON list) in a markdown file.
2. Inline directive inside markdown body (survives markdown as an HTML
   comment, then is replaced at build time):

       <!-- layout:comparison_table
            {"title":"Espresso vs Drip",
             "rows":[["Espresso","30s","strong"],["Drip","4m","mild"]]} -->

The registry (``COMPONENTS``) is the single source of truth. Every component
declares its data schema so both editors and AI know exactly what fields to
emit (see ``layout.md`` for the full human reference).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class LayoutComponent:
    id: str
    label: str
    description: str
    data_schema: dict
    render: Callable[[dict], str]
    reusable_in: list[str] = field(default_factory=lambda: ["article"])
    ai_generatable: bool = True


def _esc(v) -> str:
    return html.escape(str(v or ""), quote=True)


def _row(t: list | tuple) -> list[str]:
    return [_esc(x) for x in t]


# ── Individual renderers (each produces reusable, self-contained HTML) ──
def _r_hero(d: dict) -> str:
    return (
        f'<div class="layout-hero"><img src="{_esc(d.get("image"))}" '
        f'alt="{_esc(d.get("alt"))}"><p>{_esc(d.get("subtitle"))}</p></div>'
    )


def _r_image(d: dict) -> str:
    return (
        f'<figure class="layout-figure"><img src="{_esc(d.get("src"))}" '
        f'alt="{_esc(d.get("alt"))}"><figcaption>{_esc(d.get("caption"))}</figcaption></figure>'
    )


def _r_callout(d: dict) -> str:
    cls = _esc(d.get("tone") or "info")  # info|warn|tip|danger
    return (
        f'<div class="layout-callout {cls}"><p><strong>{_esc(d.get("label"))}</strong> '
        f"{_esc(d.get('text'))}</p></div>"
    )


def _r_steps(d: dict) -> str:
    lis = "".join(f"<li>{_esc(x)}</li>" for x in d.get("steps", []))
    return f'<ol class="layout-steps"><h3>{_esc(d.get("title"))}</h3>{lis}</ol>'


def _r_list(d: dict) -> str:
    tag = ["ul", "ol"][d.get("ordered", False)]
    lis = "".join(f"<li>{_esc(x)}</li>" for x in d.get("items", []))
    return f'<{tag} class="layout-list">{lis}</{tag}>'


def _r_pros_cons(d: dict) -> str:
    pros = "".join(f"<li>{_esc(x)}</li>" for x in d.get("pros", []))
    cons = "".join(f"<li>{_esc(x)}</li>" for x in d.get("cons", []))
    return (
        '<div class="layout-proscons"><div class="pros"><h4>Pros</h4>'
        f"<ul>{pros}</ul></div>"
        f'<div class="cons"><h4>Cons</h4><ul>{cons}</ul></div></div>'
    )


def _r_comparison(d: dict) -> str:
    head = "".join(f"<th>{_esc(x)}</th>" for x in d.get("headers", []))
    rows = "".join(
        "<tr>" + "".join(f"<td>{x}</td>" for x in _row(r)) + "</tr>"
        for r in d.get("rows", [])
    )
    return (
        f'<div class="layout-comparison"><h3>{_esc(d.get("title"))}</h3>'
        f'<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _r_recipe(d: dict) -> str:
    ings = "".join(f"<li>{_esc(x)}</li>" for x in d.get("ingredients", []))
    steps = "".join(f"<li>{_esc(x)}</li>" for x in d.get("steps", []))
    return (
        f'<div class="layout-recipe"><h3>{_esc(d.get("title"))}</h3>'
        f'<p class="meta">⏱ {_esc(d.get("time"))} · ☕ {_esc(d.get("yield"))}</p>'
        f"<h4>Ingredients</h4><ul>{ings}</ul><h4>Steps</h4><ol>{steps}</ol></div>"
    )


def _r_faq(d: dict) -> str:
    items = "".join(
        f"<details class=\"layout-faq-item\"><summary>{_esc(i.get('q'))}</summary>"
        f"<p>{_esc(i.get('a'))}</p></details>"
        for i in d.get("items", [])
    )
    return f"""<div class="layout-faq">{items}</div>"""


def _r_quote(d: dict) -> str:
    return (
        f'<blockquote class="layout-quote">{_esc(d.get("text"))}'
        f"<cite>{_esc(d.get('cite'))}</cite></blockquote>"
    )


def _r_cards(d: dict) -> str:
    cards = "".join(
        f'<div class="layout-card"><h4>{_esc(c.get("title"))}</h4>'
        f"<p>{_esc(c.get('text'))}</p></div>"
        for c in d.get("cards", [])
    )
    return f'<div class="layout-cards">{cards}</div>'


# ── Registry: 1 definition + 1 renderer per component ──────────────────
COMPONENTS: dict[str, LayoutComponent] = {
    "hero": LayoutComponent(
        id="hero",
        label="Hero",
        description="Banner header with image + subtitle.",
        data_schema={"image": "str", "alt": "str", "subtitle": "str"},
        render=_r_hero,
    ),
    "image": LayoutComponent(
        id="image",
        label="Image",
        description="Figure with caption.",
        data_schema={"src": "str", "alt": "str", "caption": "str"},
        render=_r_image,
        reusable_in=["article", "home", "landing"],
    ),
    "callout": LayoutComponent(
        id="callout",
        label="Callout / tip box",
        description="Highlighted note. tone = info|warn|tip|danger.",
        data_schema={"tone": "str", "label": "str", "text": "str"},
        render=_r_callout,
    ),
    "steps": LayoutComponent(
        id="steps",
        label="Step-by-step",
        description="Numbered how-to steps.",
        data_schema={"title": "str", "steps": "list[str]"},
        render=_r_steps,
    ),
    "list": LayoutComponent(
        id="list",
        label="List",
        description="Bullet/ordered list. ordered=true for numbered.",
        data_schema={"ordered": "bool", "items": "list[str]"},
        render=_r_list,
    ),
    "pros_cons": LayoutComponent(
        id="pros_cons",
        label="Pros & Cons",
        description="Two-column pros/cons block.",
        data_schema={"pros": "list[str]", "cons": "list[str]"},
        render=_r_pros_cons,
        reusable_in=["article", "comparison"],
    ),
    "comparison_table": LayoutComponent(
        id="comparison_table",
        label="Comparison table",
        description="Headers + rows table (e.g. product A vs B).",
        data_schema={"title": "str", "headers": "list[str]", "rows": "list[list]"},
        render=_r_comparison,
        reusable_in=["article", "comparison", "home"],
    ),
    "recipe": LayoutComponent(
        id="recipe",
        label="Recipe",
        description="Ingredients + time + yield + steps.",
        data_schema={
            "title": "str", "time": "str", "yield": "str",
            "ingredients": "list[str]", "steps": "list[str]",
        },
        render=_r_recipe,
    ),
    "faq": LayoutComponent(
        id="faq",
        label="FAQ",
        description="Accordion list of Q&A.",
        data_schema={"items": "list[{q:str, a:str}]"},
        render=_r_faq,
    ),
    "quote": LayoutComponent(
        id="quote",
        label="Quote",
        description="Blockquote with citation.",
        data_schema={"text": "str", "cite": "str"},
        render=_r_quote,
    ),
    "cards": LayoutComponent(
        id="cards",
        label="Cards grid",
        description="Grid of title+text cards.",
        data_schema={"cards": "list[{title:str, text:str}]"},
        render=_r_cards,
        reusable_in=["home", "landing", "article"],
    ),
}

# Clockwise: directive regex. Format:
#   <!-- layout:comparison_table {JSON} -->
#   <!-- layout:recipe
#       {JSON multiline}
#   -->
_BLOCK_RE = re.compile(r"<!--\s*layout:(\w+)\s*(.*?)-->", re.DOTALL)


def get_component(cid: str) -> LayoutComponent | None:
    return COMPONENTS.get(cid)


def render_block(block: dict) -> str:
    """Render a single block dict {type: <id>, ...data} into HTML."""
    cid = block.get("type")
    comp = COMPONENTS.get(cid)
    if not comp:
        raise ValueError(
            f"unknown layout component: {cid!r}. Known: {sorted(COMPONENTS)}"
        )
    return comp.render(block)


def render_blocks(blocks: list[dict]) -> str:
    """Render an ordered list of block dicts into one HTML string."""
    return "\n".join(render_block(b) for b in blocks)


def directives_from_markdown(md: str) -> "tuple[str, dict[str, str]]":
    """Extract inline block directives, returning (cleaned_md, {token: html}).

    Each directive ``<!-- layout:<id> {json} -->`` is replaced in the markdown
    by a placeholder ``@@BLK_<n>@@``. The caller later substitutes that token
    with the rendered HTML (so position is preserved in the article body).
    """
    tokens: dict[str, str] = {}
    rendered: dict[str, str] = {}

    def _sub(m: re.Match) -> str:
        cid = m.group(1)
        payload = (m.group(2) or "").strip()
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            data = {}
        data.setdefault("type", cid)
        token = f"@@BLK_{len(rendered)}@@"
        rendered[token] = render_block(data)
        return token

    cleaned = _BLOCK_RE.sub(_sub, md)
    tokens.update(rendered)
    return cleaned, tokens


def parse_frontmatter_blocks(fm_blocks: str | list | None) -> list[dict]:
    """Normalize a ``blocks`` value from YAML/JSON frontmatter into a list."""
    if not fm_blocks:
        return []
    if isinstance(fm_blocks, list):
        return fm_blocks
    if isinstance(fm_blocks, str):
        try:
            data = json.loads(fm_blocks)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return []
    return []


def substitute_tokens(html: str, tokens: dict[str, str]) -> str:
    for tok, val in tokens.items():
        html = html.replace(tok, val)
    return html

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
from typing import Any, Callable, Literal


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

# ── LangChain structured-output schemas (with_structured_output) ──────
try:  # pydantic ships with langchain_openai; fall back gracefully if absent
    from pydantic import BaseModel, Field  # type: ignore
except Exception:  # noqa: BLE001
    BaseModel = None  # type: ignore
    Field = None  # type: ignore

BLOCK_TYPES = Literal[
    "hero", "image", "callout", "steps", "list", "pros_cons",
    "comparison_table", "recipe", "faq", "quote", "cards",
]


def _make_schemas():  # build only when pydantic is available
    if BaseModel is None:
        return None, None

    class LayoutBlock(BaseModel):  # type: ignore
        type: BLOCK_TYPES
        data: dict[str, Any] = Field(
            default_factory=dict,
            description="The component's schema fields for this type.",
        )

    class LayoutBlocks(BaseModel):  # type: ignore
        blocks: list[LayoutBlock]

    return LayoutBlock, LayoutBlocks


BLOCK_SCHEMA, BLOCKS_SCHEMA = _make_schemas()


def _blocks_from_validated(resp) -> list[dict]:
    """Coerce a structured-output result into [{type, ...data}] dicts."""
    if isinstance(resp, list):
        items = resp
    else:
        items = getattr(resp, "blocks", None) or (
            resp.get("blocks") if isinstance(resp, dict) else None
        ) or []
    out = []
    for b in items:
        if isinstance(b, dict):
            d = b
        elif hasattr(b, "model_dump"):
            d = b.model_dump()
        else:
            continue
        blk = {"type": d.get("type")}
        data = d.get("data") if isinstance(d.get("data"), dict) else {}
        blk.update(data)
        out.append(blk)
    return out


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


# ── AI block generation + per-block regeneration ──────────────────────
def directive_matches(md: str) -> list[re.Match]:
    """All inline ``<!-- layout:<id> {json} -->`` matches, in order."""
    return list(_BLOCK_RE.finditer(md))


def parse_directives(md: str) -> list[dict]:
    """Parse all block dicts present in a markdown body, in order."""
    blocks: list[dict] = []
    for m in directive_matches(md):
        cid = m.group(1)
        payload = (m.group(2) or "").strip()
        try:
            data = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            data = {}
        data.setdefault("type", cid)
        blocks.append(data)
    return blocks


def replace_directive(md: str, idx: int, new_block: dict) -> str:
    """Replace the ``idx``-th inline directive's JSON with ``new_block``."""
    matches = directive_matches(md)
    if idx >= len(matches):
        raise IndexError(f"block index {idx} out of range (have {len(matches)})")
    m = matches[idx]
    cid = new_block.get("type", m.group(1))
    payload = json.dumps(
        {k: v for k, v in new_block.items() if k != "type"}, ensure_ascii=False
    )
    new_directive = f"<!-- layout:{cid} {payload} -->"
    return md[: m.start()] + new_directive + md[m.end():]


def blocks_to_directives(blocks: list[dict]) -> str:
    """Serialize a list of block dicts into inline ```<!-- layout:.. -->`` text."""
    out = []
    for b in blocks:
        cid = b.get("type")
        if cid not in COMPONENTS:
            continue
        payload = json.dumps(
            {k: v for k, v in b.items() if k != "type"}, ensure_ascii=False
        )
        out.append(f"<!-- layout:{cid} {payload} -->")
    return "\n\n".join(out)


def _component_catalog() -> str:
    return "\n".join(
        f"- {cid}: {COMPONENTS[cid].data_schema}"
        for cid in sorted(COMPONENTS)
        if COMPONENTS[cid].ai_generatable
    )


def generate_blocks(llm, title: str, keyword: str, content: str,
                     max_blocks: int = 4) -> list[dict]:
    """Ask the LLM to propose high-value layout blocks for an article.

    Returns only blocks whose ``type`` is a registered, AI-generatable component.
    ``llm`` is any object exposing ``extract_json(prompt, system_prompt=...)``
    (e.g. OpenRouterClient / deepseek-v4-flash).
    """
    prompt = (
        f"Article title: {title}\nKeyword: {keyword}\n\n"
        f"Article content (first 2500 chars):\n{content[:2500]}\n\n"
        "Choose 2-4 layout blocks that BEST enrich this article (a comparison "
        "table, recipe steps, FAQ, pros/cons, callout, etc.) that are relevant "
        "to the content. Available components + JSON schemas:\n"
        f"{_component_catalog()}\n\n"
        "Return ONLY a JSON object with a 'blocks' array. Provide up to "
        f"{max_blocks} blocks. Each block is an object with "
        "'type' (the component id) and 'data' (exactly that component's "
        "schema fields, relevant to the article). No other text."
    )
    if BLOCKS_SCHEMA is None:
        return []
    try:
        resp = llm.extract_json(
            prompt,
            system_prompt=(
                "You are a content layout engineer. Output valid JSON only "
                "matching the provided schema."
            ),
            schema=BLOCKS_SCHEMA,
            max_tokens=4000,
        )
    except Exception:
        return []
    blocks = [
        b for b in _blocks_from_validated(resp)
        if isinstance(b, dict) and b.get("type") in COMPONENTS
    ]
    return blocks[:max_blocks]


def regenerate_block(llm, md: str, idx: int, instruction: str) -> "tuple[str, dict]":
    """Regenerate a single block (index ``idx``) via the LLM, keep the rest.

    Returns (new_markdown, new_block_dict). Updates only the one directive;
    all other content is untouched.
    """
    blocks = parse_directives(md)
    if idx >= len(blocks):
        raise IndexError(f"block index {idx} out of range (have {len(blocks)})")
    old = blocks[idx]
    cid = old.get("type")
    comp = COMPONENTS.get(cid)
    schema = comp.data_schema if comp else {}
    prompt = (
        f"Regenerate the layout block type '{cid}' for a coffee blog article.\n"
        f"Current block data: {json.dumps(old, ensure_ascii=False)}\n"
        f"Required schema: {schema}\n"
        f"Instruction / what to improve: {instruction}\n"
        "Return ONLY a single JSON object: the NEW block, same type, using the "
        "schema fields, content faithful to the article."
    )
    if BLOCK_SCHEMA is None:
        raise RuntimeError("pydantic/structured-output unavailable for regeneration")
    new = llm.extract_json(
        prompt,
        system_prompt="You are a content layout editor. Output only the block object.",
        schema=BLOCK_SCHEMA,
        max_tokens=3000,
    )
    new_blocks = _blocks_from_validated(new)
    new = new_blocks[0] if new_blocks else {"type": cid}
    return replace_directive(md, idx, new), new

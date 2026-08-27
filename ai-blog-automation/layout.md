# Layout System — reusable, AI-generatable layout components

> Source of truth: `src/blog_automation/layouts.py` (registry `COMPONENTS`)
> Rendered by: `scripts/publish.py::build_article` (wired into every article build)

## Concept

A **layout component** is a small, self-contained, reusable piece of HTML.
Any page/article is composed of these components. Because each is a plain
renderer keyed by a stable `id`, the SAME component can be reused anywhere
(article, homepage, comparison page, landing) and — crucially — **an LLM can
emit them as structured JSON blocks** that the renderer turns into HTML. So
layout is no longer fixed to one template; it is *composed* per article.

- **Reusable in many places**: a component defined once renders identically
  everywhere it's used.
- **AI-generatable**: give the model the list of component ids + schemas; it
  outputs a JSON array of `{type, ...data}` and the build renders it.

## Authoring a block (2 ways)

### 1) Inline directive in the markdown body (recommended for AI)

```md
Intro paragraph...

<!-- layout:comparison_table
{"title":"Espresso vs Drip",
 "headers":["","Espresso","Drip"],
 "rows":[["Time","30s","4m"],["Boldness","High","Mild"]]}
-->

More prose...
```

The directive is an HTML comment, so it never shows as text; at build time
`layouts.directives_from_markdown` replaces it with the rendered HTML at the
exact same position.

### 2) Frontmatter `blocks:` (single-line JSON)

```yaml
---
title: My post
blocks: [{"type":"callout","tone":"tip","label":"Tip","text":"Use fresh water"}]
---
```

(`extract_frontmatter` is a simple line parser, so `blocks:` must be one line.)

## Component reference

| id | Label | data_schema | reusable_in |
|----|-------|-------------|-------------|
| `hero` | Hero banner | `image, alt, subtitle` | article |
| `image` | Figure w/ caption | `src, alt, caption` | article, home, landing |
| `callout` | Tip/alert box | `tone`(info\|warn\|tip\|danger), `label, text` | article |
| `steps` | Numbered how-to | `title, steps[]` | article |
| `list` | Bullet/numbered | `ordered(bool), items[]` | article |
| `pros_cons` | Pros & Cons | `pros[], cons[]` | article, comparison |
| `comparison_table` | Comparison table | `title, headers[], rows[][]` | article, comparison, home |
| `recipe` | Recipe card | `title, time, yield, ingredients[], steps[]` | article |
| `faq` | FAQ accordion | `items[{q,a}]` | article |
| `quote` | Blockquote | `text, cite` | article |
| `cards` | Cards grid | `cards[{title,text}]` | article, home, landing |

> CSS hooks: every component emits a `layout-*` class
> (`layout-comparison`, `layout-callout tip`, `layout-recipe`, ...). Style them
> once in the site CSS; components are markup-only.

## Renderer API (for scripts / AI pipeline)

```python
from blog_automation.layouts import (
    render_block,       # dict -> HTML
    render_blocks,      # list[dict] -> HTML
    directives_from_markdown,  # (cleaned_md, {token: html})
    substitute_tokens,  # html.replace tokens -> final HTML
    COMPONENTS,         # registry {id: LayoutComponent}
)
```

## Adding a new component

1. Write a `_r_<name>(data: dict) -> str` renderer.
2. Register it in `COMPONENTS` with `id`, `label`, `description`,
   `data_schema`, `reusable_in`.
3. Optionally add a `layout-<name>` CSS rule.
4. It becomes instantly usable by both markdown directives and the AI (which
   just needs the `id` + `data_schema`).

## AI integration note

To have the model generate layout: provide `sorted(COMPONENTS.keys())` +
each component's `data_schema`, and ask for a JSON array of
`{"type": "...", ...schema fields}`. Inline as `<!-- layout:<type> <json> -->`
or as frontmatter `blocks:`. The renderer validates schema only loosely
(missing keys are ignored / empty), so a partial block still renders safely.
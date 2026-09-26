#!/usr/bin/env python3
"""Publish markdown content as a static site via GitHub → Cloudflare Pages.

No database. No pipeline phases. No WordPress.  Just write markdown, run
this script, and it commits + pushes to the current repo.

Quick start::

    python scripts/publish.py                        # build + push all content/
    python scripts/publish.py post.md -t "Title"     # single post
    python scripts/publish.py --no-push              # build only, skip git
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

# Add src to path
_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

import markdown2

# ---------------------------------------------------------------------------
# Layout component CSS — styles the reusable `layout-*` blocks from layouts.py.
# Shared by both PAGE_TEMPLATE and INDEX_TEMPLATE via the `{layout_css}` slot.
# ---------------------------------------------------------------------------
LAYOUT_CSS = """\
.layout-hero img{width:100%;border-radius:16px;display:block}
.layout-hero p{color:var(--muted);font-size:1.05rem;margin:.5rem 0 0}
.layout-figure{margin:1.4rem 0}
.layout-figure img{max-width:100%;border-radius:14px}
.layout-figure figcaption{font-size:.85rem;color:var(--muted);text-align:center;margin-top:.5rem}
.layout-callout{border-left:4px solid var(--accent);background:#f7efe3;padding:14px 18px;border-radius:12px;margin:1.2rem 0}
.layout-callout.warn{border-color:#b8860b;background:#fbf3e0}
.layout-callout.danger{border-color:#b00020;background:#fbeeea}
.layout-callout.tip{border-color:#2e7d32;background:#eef6ee}
.layout-callout p{margin:0}
.layout-steps{background:#fbf7ef;border:1px solid #e6dccb;border-radius:12px;padding:16px 20px 16px 36px;margin:1.2rem 0}
.layout-steps li{margin:.35rem 0}
.layout-list{margin:1rem 0}
.layout-proscons{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:1.2rem 0}
.layout-proscons .pros,.layout-proscons .cons{border-radius:12px;padding:14px 16px}
.layout-proscons .pros{background:#eef6ee;border:1px solid #cfe6cf}
.layout-proscons .cons{background:#fbeeea;border:1px solid #ecd0cd}
.layout-proscons h4,.layout-proscons ul{margin:.2rem 0}
.layout-comparison{margin:1.4rem 0;border:1px solid #e6dccb;border-radius:12px;overflow:hidden}
.layout-comparison h3{padding:14px 16px;margin:0;background:#faf6ef;border-bottom:1px solid #e6dccb}
.layout-comparison table{margin:0;border:none}
.layout-comparison th{background:#faf6ef}
.layout-recipe{border:1px solid #e6dccb;border-radius:14px;padding:18px 20px;margin:1.4rem 0;background:#fbf7ef}
.layout-recipe h3,.layout-recipe h4{margin:.3rem 0}
.layout-recipe .meta{color:var(--muted);font-size:.9rem}
.layout-faq{margin:1.2rem 0}
.layout-faq details{border:1px solid #e6dccb;border-radius:10px;padding:12px 16px;margin:.5rem 0}
.layout-faq summary{cursor:pointer;font-weight:600}
.layout-faq-item p{margin:.5rem 0 0}
.layout-quote{border-left:4px solid var(--accent);padding-left:16px;color:#5b5240;font-style:italic;margin:1.2rem 0}
.layout-quote cite{display:block;font-style:normal;font-size:.85rem;color:var(--muted);margin-top:.4rem}
.layout-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:1.2rem 0}
.layout-card{border:1px solid #e6dccb;border-radius:12px;padding:16px;background:#fff}
.layout-card h4{margin:.2rem 0}
"""

# ---------------------------------------------------------------------------
# Shared site CSS — tokens, reset, nav, container, footer, a11y.
# Single source of truth for BOTH templates (PAGE_TEMPLATE + INDEX_TEMPLATE) via
# the `{site_css}` slot — before this existed the two templates duplicated the
# nav/container/footer rules and had DRIFTED (nav 1080px on articles vs 1360px
# on the homepage, `width:min(75%,…)` that broke the header on phones).
# Braces are literal here (substituted as a value, not re-formatted).
# Contrast (WCAG AA, verified): --muted #7a6a58 = 5.21 on #fff / 4.84 on --bg;
# --accent #96632b = 5.10 / 4.74. The old muted #8a7a6a (4.14/3.84) and accent
# #b07840 (3.75/3.48) both FAILED AA for body text.
# ---------------------------------------------------------------------------
SITE_CSS = """\
:root{--bg:#faf6ef;--surface:#fff;--ink:#3a2f28;--muted:#7a6a58;--accent:#96632b;--accent-soft:#e8dcc9;--line:#e6dccb;--serif:"Fraunces",Georgia,serif;--sans:"Inter",-apple-system,sans-serif;--wrap:1200px;--gut:20px}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%}
body{font-family:var(--sans);font-size:1rem;line-height:1.7;color:var(--ink);background:var(--bg);margin:0}
a{color:var(--accent)}
img{max-width:100%;height:auto}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
nav{background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
nav .inner{max-width:var(--wrap);margin:0 auto;padding:10px var(--gut);display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}
nav .brand{font-family:var(--serif);font-weight:700;font-size:1.25rem;line-height:1.15;color:var(--ink);text-decoration:none;white-space:nowrap}
nav .nav-links{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
nav .nav-links a{color:var(--muted);text-decoration:none;font-size:.92rem;font-weight:500;min-height:44px;display:inline-flex;align-items:center;padding:0 12px;border-radius:999px}
nav .nav-links a:hover{color:var(--accent);background:var(--accent-soft)}
.container{max-width:var(--wrap);margin:0 auto;padding:0 var(--gut)}
footer{color:var(--muted);font-size:.85rem;text-align:center;padding:36px 0;margin-top:24px;border-top:1px solid var(--line)}
footer .cols{max-width:var(--wrap);margin:16px auto 0;padding:0 var(--gut);display:flex;flex-wrap:wrap;gap:12px 18px;justify-content:center}
footer a{color:var(--muted)}footer a:hover{color:var(--accent)}
@media(max-width:480px){
  nav .inner{padding:8px var(--gut);gap:6px}
  nav .brand{font-size:1.05rem}
  nav .nav-links a{font-size:.85rem;padding:0 9px}
}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
"""

# ---------------------------------------------------------------------------
# Static pages generated by scripts/gen_pages.py — ONE list drives the footer of
# every page (blog + static) and the sitemap, so a link can never point at a page
# nobody generates (that mismatch is what produced the 200-but-homepage soft 404s).
# ---------------------------------------------------------------------------
STATIC_PAGES = [
    ("about", "About Us"),
    ("contributors", "Contributors"),
    ("contact", "Contact"),
    ("newsletter", "Newsletter"),
    ("pay-it-forward", "Pay It Forward"),
    ("sustainability", "Sustainability"),
    ("privacy", "Privacy"),
]
# Layout attributes (DB columns -> materialized frontmatter -> build).
#   page_layout : article | bento | page   (which template renders the page;
#                 only the generated homepage is `bento` today, `page` is used by
#                 gen_pages.py, so content pages are `article` and anything else
#                 is rejected loudly instead of rendering wrongly)
#   home_slot   : auto | hero | wide | small | text | list | none
#   home_weight : tie-break inside a slot, higher first
VALID_PAGE_LAYOUTS = ("article", "bento", "page")
VALID_HOME_SLOTS = ("auto", "hero", "wide", "small", "text", "list", "none")
SLOT_CAPACITY = {"hero": 1, "wide": 2}          # explicit overflow -> back to auto
AUTO_FILL_ORDER = (("hero", 1), ("wide", 2), ("small", 8), ("text", 2))   # newest first

FEATURED_EXTERNAL = (
    "https://sca.coffee/",
    "Specialty Coffee Association",
)


def footer_cols_html() -> str:
    """Footer link row: every static page + sitemap/RSS + one real external link."""
    links = "".join(f'<a href="/{slug}/">{label}</a>' for slug, label in STATIC_PAGES)
    links += '<a href="/sitemap.xml">Sitemap</a><a href="/rss.xml">RSS</a>'
    links += (
        f'<a href="{FEATURED_EXTERNAL[0]}" target="_blank" rel="noopener">'
        f"{FEATURED_EXTERNAL[1]}</a>"
    )
    return links


# ---------------------------------------------------------------------------
# HTML template — single article page, SEO-optimized
# ---------------------------------------------------------------------------
PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <meta name="author" content="{author}">
    <link rel="canonical" href="{canonical_url}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="{site_name}">
    <meta property="og:locale" content="{og_locale}">
    <meta property="article:published_time" content="{published_time}">
    {og_image}
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    {twitter_image}
    <script type="application/ld+json">{ld_json}</script>
    <link rel="alternate" type="application/rss+xml" title="{site_name} RSS" href="/rss.xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>{layout_css}</style>
    <style>{site_css}</style>
    <style>
        .article{{padding:48px 0 64px}}
        .hero{{margin:0 0 22px}}
        .hero img{{width:100%;aspect-ratio:16/10;max-height:560px;object-fit:cover;border-radius:18px;display:block}}
        .hero figcaption{{color:var(--muted);font-size:.82rem;margin-top:.5rem}}
        header{{margin-bottom:32px}}
        .kicker{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:12px}}
        h1{{font-family:var(--serif);font-weight:700;font-size:clamp(1.85rem,1.3rem + 2.2vw,2.5rem);line-height:1.12;margin:0 0 14px;color:var(--ink);letter-spacing:-.01em}}
        .deck{{font-size:clamp(1.05rem,.6vw + .9rem,1.25rem);line-height:1.55;color:var(--muted);max-width:680px;margin:0 0 22px}}
        .byline{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;color:var(--muted);font-size:.85rem;padding-bottom:22px;border-bottom:1px solid var(--line)}}
        .byline .avatar{{width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #e8dcc9}}
        .byline .by{{font-weight:600;color:var(--ink)}}
        .byline .dot{{width:3px;height:3px;border-radius:50%;background:#b8aa96;display:inline-block}}
        .tags{{margin-top:16px}}
        .tags span{{display:inline-block;padding:4px 12px;border-radius:999px;font-size:.72rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;background:var(--accent-soft);color:#7a5a34;margin-right:6px}}
        .content{{font-size:clamp(1rem,.35vw + .93rem,1.1rem);max-width:1000px;margin:0 auto}}
        .content p{{margin:1.15em 0}}
        .content>p:first-of-type::first-letter{{font-family:var(--serif);font-weight:700;font-size:3.6em;float:left;line-height:.82;padding:.06em .12em 0 0;color:var(--accent)}}
        .content h2{{font-family:var(--serif);font-size:1.7rem;font-weight:600;margin:2.4rem 0 .8rem;color:var(--ink)}}
        .content h3{{font-family:var(--serif);font-size:1.32rem;font-weight:600;margin:1.8rem 0 .6rem;color:var(--ink)}}
        .content a{{color:var(--accent);text-decoration:underline;text-underline-offset:2px}}
        .content img{{max-width:100%;height:auto;border-radius:14px;margin:1.2em 0}}
        .content pre{{background:#f4ede1;padding:18px;border-radius:12px;overflow-x:auto;font-size:.9rem;line-height:1.6}}
        .content code{{font-family:"SF Mono",Monaco,"Cascadia Code",monospace}}
        .content blockquote{{border-left:3px solid var(--accent);padding-left:18px;margin:1.4em 0;color:#5b5240;font-style:italic}}
        .content table{{width:100%;border-collapse:collapse;margin:1.4em 0}}
        .content th,.content td{{padding:10px 14px;border:1px solid var(--line)}}
        .content th{{background:var(--surface);font-weight:600}}
        .related{{margin-top:44px;padding-top:28px;border-top:1px solid var(--line)}}
        .related .label{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:14px}}
        .share{{margin-top:40px;padding-top:24px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
        .hashtags{{margin-top:34px;padding:18px 0;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px}}
        .hashtags span{{font-size:.85rem;font-weight:600;color:var(--accent)}}
        .hashtags span::before{{content:"#"}}
        .share .share-label{{color:var(--muted);font-size:.9rem;font-weight:600;margin-right:6px}}
        .share a,.share button{{display:inline-block;padding:8px 18px;border-radius:999px;font-size:.82rem;font-weight:600;background:var(--surface);color:var(--ink);text-decoration:none;border:1px solid var(--line);cursor:pointer;font-family:inherit}}
        .share a:hover,.share button:hover{{background:var(--accent);color:#fff;border-color:var(--accent)}}
        @media(max-width:640px){{
            h1{{font-size:clamp(1.65rem,1.25rem + 3vw,2.1rem)}}
            .deck{{font-size:1.02rem}}
            .content h2{{font-size:1.3rem}}
            .content h3{{font-size:1.15rem}}
            .hero img{{aspect-ratio:4/3;border-radius:14px}}
            .content>p:first-of-type::first-letter{{font-size:2.9em}}
        }}
    </style>
</head>
<body>
<nav><div class="inner">
    <a class="brand" href="/">{site_name}</a>
    <div class="nav-links"><a href="/">Home</a><a href="/sitemap.xml">Archive</a><a href="/rss.xml">RSS</a></div>
</div></nav>
<main class="container">
<article class="article">
    {hero_html}
    <header>
        <div class="kicker">{kicker}</div>
        <h1>{h1_title}</h1>
        <p class="deck">{description}</p>
        <div class="byline">
            <img class="avatar" src="{author_avatar}" alt="{author}" loading="lazy">
            <span class="by">By {author}</span>
            <span class="dot"></span>
            <span>{display_date}</span>
            <span class="dot"></span>
            <span>{word_count} words</span>
        </div>
        <div class="tags">{tags_html}</div>
    </header>
    <div class="content">{content_html}
    {hashtags_html}</div>
    <div class="related">
        <div class="label">Related topics</div>
        <div class="tags">{tags_html}</div>
    </div>
    <div class="share">
        <span class="share-label">Share this story</span>
        <a href="https://twitter.com/intent/tweet?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on X">X</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" rel="noopener" aria-label="Share on Facebook">Facebook</a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" rel="noopener" aria-label="Share on LinkedIn">LinkedIn</a>
        <a href="https://wa.me/?text={share_text}%20{share_url}" target="_blank" rel="noopener" aria-label="Share on WhatsApp">WhatsApp</a>
        <a href="https://t.me/share/url?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on Telegram">Telegram</a>
        <a href="mailto:?subject={share_text}&body={share_url}" aria-label="Share via email">Email</a>
        <button type="button" onclick="navigator.clipboard&&navigator.clipboard.writeText('{canonical_url}').then(()=>{{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy link',1500)}})">Copy link</button>
    </div>
</article>
</main>
<footer><p>&copy; 2026 {site_name}.</p>
<div class="cols">{footer_cols}</div>
</footer>
</body>
</html>
"""

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <meta name="google-site-verification" content="BWPdVOyPoQmHVqgfn8_PMBl7N6F0e5-q1CVNjHuMhOg" />
    <link rel="canonical" href="{site_url}/">
    <script type="application/ld+json">{index_ld_json}</script>
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{site_url}/">
    <link rel="alternate" type="application/rss+xml" title="{site_name} RSS" href="/rss.xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>{layout_css}</style>
    <style>{site_css}</style>
    <style>
        .container{{margin:34px auto 60px}}
        .intro{{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap;margin:0 0 18px}}
        .intro h1{{font-family:var(--serif);font-weight:700;font-size:clamp(1.7rem,1.15rem + 2.3vw,2.4rem);line-height:1.1;letter-spacing:-.02em;margin:0 0 8px;max-width:24ch}}
        .intro p{{color:var(--muted);margin:0;max-width:58ch}}
        .cta{{display:inline-flex;align-items:center;min-height:46px;padding:0 22px;border-radius:999px;background:var(--accent);color:#fff;font-weight:600;font-size:.92rem;white-space:nowrap}}
        .cta:hover{{background:#7d5223}}
        .filters{{display:flex;gap:8px;flex-wrap:wrap;padding:6px 0 20px}}
        .filters button{{min-height:40px;padding:0 15px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--muted);font-family:inherit;font-size:.86rem;font-weight:600;cursor:pointer;transition:border-color .18s,color .18s,background .18s}}
        .filters button:hover{{border-color:var(--accent);color:var(--accent)}}
        .filters button[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
        .bento{{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:206px;gap:16px}}
        .tile{{position:relative;display:block;border-radius:20px;overflow:hidden;background:var(--surface);border:1px solid var(--line);box-shadow:0 6px 22px rgba(58,47,40,.07);transition:transform .2s,box-shadow .2s}}
        .tile:hover{{transform:translateY(-4px);box-shadow:0 16px 34px rgba(58,47,40,.14)}}
        .tile img{{width:100%;height:100%;object-fit:cover;display:block}}
        .tile .cap{{position:absolute;left:0;right:0;bottom:0;padding:20px 18px 16px;color:#fff;background:linear-gradient(transparent,rgba(28,20,14,.88))}}
        .tile .cap .k{{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:#f0dcc0}}
        .tile .cap h2{{font-family:var(--serif);font-weight:600;font-size:1.18rem;line-height:1.26;margin:6px 0 0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
        .tile.big{{grid-column:span 2;grid-row:span 2}}
        .tile.big .cap h2{{font-size:clamp(1.35rem,2.1vw,1.85rem);-webkit-line-clamp:4}}
        .tile.wide{{grid-column:span 2}}
        .tile.flat{{display:flex;flex-direction:column;justify-content:center;gap:8px;padding:22px;background:var(--accent-soft);border-color:var(--accent-soft)}}
        .tile.flat h2{{font-family:var(--serif);font-size:1.15rem;line-height:1.25;margin:0}}
        .tile.flat p{{color:#6d4f2b;font-size:.9rem;margin:0}}
        .tile.flat code{{background:#fff;border-radius:8px;padding:6px 10px;font-size:.8rem;align-self:flex-start}}
        .tile.dark{{display:flex;flex-direction:column;justify-content:center;padding:22px;background:var(--ink);color:#f7f1e8;border-color:var(--ink)}}
        .tile.dark h2{{font-family:var(--serif);font-size:1.15rem;line-height:1.25;margin:0 0 6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
        .tile.dark p{{opacity:.82;font-size:.9rem;margin:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
        .tile.hide{{display:none}}
        .sec{{font-family:var(--serif);font-size:1.15rem;font-weight:600;margin:44px 0 16px;display:flex;align-items:center;gap:14px}}
        .sec:after{{content:"";flex:1;height:1px;background:var(--line)}}
        /* "More stories": grid (row-major, so reading order == chronology), one
           hairline per row, numbered for scanability. Titles are ink and NOT
           underlined until hover — a wall of underlined accent links read as a
           sitemap dump (the UA default underline + body link colour). */
        .morelist{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:0 44px}}
        .morelist li{{display:grid;grid-template-columns:32px 1fr;gap:12px;align-items:start;padding:14px 0;border-bottom:1px solid var(--line)}}
        .morelist .mn{{font-family:var(--serif);font-size:.95rem;line-height:1.4;color:#c3ad90;font-variant-numeric:tabular-nums;padding-top:1px}}
        .morelist li:hover .mn{{color:var(--accent)}}
        .morelist .mk{{display:block;font-size:.62rem;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:4px}}
        .morelist a{{font-family:var(--serif);font-weight:600;font-size:1.05rem;line-height:1.35;color:var(--ink);text-decoration:none;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
        .morelist a:hover{{color:var(--accent);text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}}
        .morelist .mmeta{{display:block;color:var(--muted);font-size:.76rem;margin-top:4px}}
        .moreall{{display:inline-flex;align-items:center;gap:8px;margin-top:22px;font-weight:600;font-size:.92rem;color:var(--accent);text-decoration:none;border-bottom:1px solid var(--accent-soft);padding-bottom:2px}}
        .moreall:hover{{border-bottom-color:var(--accent)}}
        @media(max-width:980px){{
            .bento{{grid-template-columns:repeat(2,1fr);grid-auto-rows:190px}}
            .tile.big{{grid-column:span 2;grid-row:span 1}}
        }}
        @media(max-width:700px){{
            .morelist{{grid-template-columns:1fr;gap:0}}
        }}
        @media(max-width:560px){{
            .bento{{grid-template-columns:1fr;grid-auto-rows:200px}}
            .tile.wide,.tile.big{{grid-column:span 1}}
            .tile.big .cap h2{{font-size:1.3rem}}
        }}
    </style>
</head>
<body>
<nav><div class="inner">
    <a class="brand" href="/">{site_name}</a>
    <div class="nav-links"><a href="/">Home</a><a href="/sitemap.xml">Archive</a><a href="/rss.xml">RSS</a></div>
</div></nav>
<main class="container">
    <section class="intro">
        <div>
            <h1>Latest posts and articles on coffee, brewing and the home barista</h1>
            <p>Fresh guides on brewing, espresso, Vietnamese coffee and honest gear reviews — {post_count} stories and counting.</p>
        </div>
        <a class="cta" href="/rss.xml">Follow by RSS →</a>
    </section>
    <div class="filters" id="filters" role="group" aria-label="Filter stories by topic">{filters_html}</div>
    <div class="bento" id="bento">{tiles_html}</div>
    <h2 class="sec" id="stories">More stories</h2>
    <ul class="morelist">{more_html}</ul>
</main>
<script>
(function(){{
  var bar=document.getElementById('filters'), grid=document.getElementById('bento');
  if(!bar||!grid) return;
  bar.addEventListener('click',function(e){{
    var b=e.target.closest('button'); if(!b) return;
    var f=b.dataset.topic, tiles=grid.querySelectorAll('.tile'), shown=0;
    bar.querySelectorAll('button').forEach(function(x){{x.setAttribute('aria-pressed', x===b ? 'true':'false');}});
    tiles.forEach(function(t){{
      var hit = f==='all' || t.dataset.topic===f;
      t.classList.toggle('hide', !hit); if(hit) shown++;
    }});
    grid.setAttribute('data-shown', shown);
  }});
}})();
</script>
<footer><p>&copy; 2026 {site_name}.</p>
<div class="cols">{footer_cols}</div>
</footer>
</body>
</html>"""

SITEMAP_TEMPLATE = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Load .env before DEFAULTS are computed: sourcing the file in a shell is
# fragile (one unparsable line silently drops every later variable), which is
# how the homepage ended up serving the fallback meta description instead of
# SITE_DESCRIPTION. Python-side loading always works.
try:  # pragma: no cover — optional dependency
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except Exception:  # noqa: BLE001
    pass

DEFAULTS = {
    "site_name": os.getenv("SITE_NAME", "The Daily Brew"),
    "site_url": os.getenv("SITE_URL", "https://dripper.top"),
    "author": os.getenv("SITE_AUTHOR", "Anonymous"),
    "description": os.getenv(
        "SITE_DESCRIPTION", "A blog about coffee, brewing, and the perfect cup."
    ),
    "lang": os.getenv("SITE_LANG", "en"),
    "dist_dir": "../public",  # at repo root — Cloudflare Pages serves from here
    "content_dir": "content",
}


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
AUTHOR_AVATARS = {
    # avatar tác giả (Unsplash portrait) — mỗi author 1 ảnh tròn
    "Tien Nguyen": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=tinysrgb&fit=crop&w=160&h=160",
}
_DEFAULT_AVATAR = (
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?"
    "crop=entropy&cs=tinysrgb&fit=crop&w=160&h=160"
)


def _avatar(author: str | None) -> str:
    """Return a circular avatar image URL for an author (Unsplash/Pexels)."""
    return AUTHOR_AVATARS.get((author or "").strip(), _DEFAULT_AVATAR)


def _byline_html(author: str | None) -> str:
    """Avatar + author name, adventure.com-style byline chip."""
    a = (author or "").strip() or "The Daily Brew"
    return (
        f'<span class="byline"><img class="avatar" src="{_avatar(author)}" '
        f'alt="{a}" loading="lazy"><span class="author-name">{a}</span></span>'
    )


def parse_tags(raw: Any) -> list[str]:
    """Parse a frontmatter `tags:` value into clean tags.

    Accepts the plain form (`a, b, c`) and the accidental list-literal form
    (`['a', 'b']`), and repairs the degenerate per-character list
    (`[, v, i, e, ...]`) that a bad join once wrote into a content file — that
    bug leaked single letters onto the homepage topic chips.
    """
    if isinstance(raw, (list, tuple)):
        s = ", ".join(str(x) for x in raw)
    else:
        s = str(raw or "")
    s = s.strip()
    if s.startswith("["):
        s = s[1:]
    if s.endswith("]"):
        s = s[:-1]
    parts = [x.strip().strip("'\"").strip() for x in s.split(",")]
    parts = [x for x in parts if x]
    if len(parts) > 8 and sum(1 for x in parts if len(x) <= 1) >= len(parts) - 2:
        # per-character garbage (a bad `", ".join(str(tags))` upstream): the original
        # word boundaries are already destroyed, so drop it instead of emitting letters
        return []
    return parts


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:80]


def extract_frontmatter(md_text: str) -> tuple[dict, str]:
    meta: dict[str, Any] = {}
    body = md_text
    if md_text.startswith("---"):
        parts = re.split(r"^---\s*$", md_text, maxsplit=2, flags=re.M)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].strip()
    return meta, body


def _guess_title(body: str) -> str | None:
    m = re.match(r"^# (.+)$", body.strip(), re.M)
    return m.group(1) if m else None


def auto_description(body: str, max_len: int = 160) -> str:
    for line in body.split("\n"):
        s = line.strip()
        if s and not s.startswith("#"):
            # line is ONLY an image -> skip (no text to describe)
            if re.match(r"!\[[^\]]*\]\([^)]*\)\s*$", s):
                continue
            # strip markdown links/images; the optional `!` kills
            # `![alt](url)` hero lines that would leak a literal `!`
            plain = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", s)
            plain = re.sub(r"[*_`]", "", plain)
            if len(plain) > 10:
                return plain[:max_len].rsplit(" ", 1)[0] + "…"
    return ""


def count_words(text: str) -> int:
    return len(text.split())


def _social_image(url: str) -> str:
    """Upgrade thumbnail URL to social-card size (1200px wide).

    Unsplash thumbnails are stored as w=200 in frontmatter — fine for the
    homepage, too small for og:image/twitter:image (social platforms need
    >= 300px, recommend 1200x630). Rewrite the query param to w=1200.
    """
    import re as _re

    if not url:
        return url
    return _re.sub(r"w=\d+", "w=1200", url)


def _hero_image(url: str) -> str:
    """Upgrade the article hero image to a sharp size for the wide layout.

    The article container is now min(94%,1360px) wide and the hero img is
    CSS-stretched (width:100%). Frontmatter stores w=200 thumbnails, so the
    hero rendered a tiny, blurry upscale. Request w=1600 so the large display
    stays crisp (matches a ~1.2x of the 1360px container for a sharp 2x DPR).
    """
    import re as _re

    if not url:
        return url
    return _re.sub(r"w=\d+", "w=1600", url)


def _hashtag_str(tags: list[str]) -> str:
    """Turn tag words into shareable hashtags, e.g. ['Hanoi Old Quarter'] ->
    '#HanoiOldQuarter'. Keeps alphanumerics only, PascalCase each word.
    """
    out = []
    for t in tags:
        cleaned = "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", t) if w)
        if cleaned:
            out.append("#" + cleaned)
    return " ".join(out)


def _hashtags_html(tags: list[str]) -> str:
    # _hashtag_str gives '#HanoiOldQuarter ...'; strip the '#' because the
    # CSS .hashtags span::before adds it (avoids '##Hanoi').
    s = _hashtag_str(tags).replace("#", " ")
    words = s.split()
    if not words:
        return ""
    return "<div class=\"hashtags\">" + "".join(f"<span>{w}</span>" for w in words) + "</div>"


def _known_slugs() -> set:
    root = Path(__file__).resolve().parent.parent
    cdir = root / "content"
    return {p.stem for p in cdir.glob("*.md")} if cdir.exists() else set()


def normalize_links(md: str, known_slugs: set) -> str:
    """Fix internal markdown links.

    - Real article slug -> absolute '/slug' (kills nested relative URLs).
    - Unknown / placeholder targets (article-slug, internal-link-*, fictional
      slugs like 'dial-in-espresso') -> unlink (turn into plain text) so we
      never ship broken or 404 links.
    - Absolute / http / anchor / mailto links are left untouched.
    """
    def _sub(m):
        text, target = m.group(1), m.group(2).strip()
        if target.startswith(("/", "http", "https", "#", "mailto:")):
            return m.group(0)
        if target in known_slugs:
            # trailing slash: the slashless URL 308s on Cloudflare Pages
            return f"[{text}](/{target}/)"
        return text

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _sub, md)


# Legacy citation form the drafting prompt used to ask for: `[Source: URL]` — a
# bracketed URL, NOT a markdown link. markdown2 runs without the autolink extra,
# so those refs shipped as dead text (85 refs across 26 pages, stray `]` visible).
_SOURCE_REF = re.compile(r"\[Source:\s*(https?://[^\s\]]+)\](?!\()", re.I)
# External anchors without an explicit target= (share buttons already set it).
_EXTERNAL_A = re.compile(r'<a href="(https?://[^"]+)"(?![^>]*\btarget=)')


def _readable_domain(url: str) -> str:
    """`https://www.ncausa.org/x` -> `ncausa.org` (anchor text for a citation)."""
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def linkify_source_refs(md: str) -> str:
    """Rewrite `[Source: URL]` into a real markdown link: `Source: [domain](URL)`.

    Leaves the already-correct `[Source: URL](URL)` form alone (negative lookahead
    on the opening paren) so double-linking can't happen.
    """
    def _sub(m):
        url = m.group(1).rstrip(".,;:")
        return f"Source: [{_readable_domain(url)}]({url})"

    return _SOURCE_REF.sub(_sub, md)


def externalize_links(html: str) -> str:
    """Open outbound content links in a new tab with rel=noopener.

    Applied to the rendered body only; same-site hrefs and anchors that already
    declare a target are left untouched.
    """
    def _sub(m):
        href = m.group(1)
        if "dripper.top" in href:
            return m.group(0)
        return f'<a href="{href}" target="_blank" rel="noopener">'

    return _EXTERNAL_A.sub(_sub, html)


def build_article(
    filepath: str,
    title: str | None = None,
    description: str | None = None,
    slug: str | None = None,
    tags: str | None = None,
    author: str | None = None,
    image: str | None = None,
) -> tuple[str, str, dict]:
    """Build a single article page from a markdown FILE path."""
    md_text = Path(filepath).read_text(encoding="utf-8")
    return build_article_from_text(
        md_text,
        title=title,
        description=description,
        slug=slug,
        tags=tags,
        author=author,
        image=image,
    )


def build_article_from_text(
    md_text: str,
    *,
    title: str | None = None,
    description: str | None = None,
    slug: str | None = None,
    tags: str | None = None,
    author: str | None = None,
    image: str | None = None,
    known_slugs: set | None = None,
) -> tuple[str, str, dict]:
    """Build a single article page from markdown TEXT (no filesystem).

    Used by the DB-driven build on hosts without durable disk (Streamlit
    Cloud). ``known_slugs`` overrides the on-disk content/ scan used to
    normalize internal links (pass the DB's published-slug set).
    """
    fm, body = extract_frontmatter(md_text)

    title = title or fm.get("title") or _guess_title(body) or "Untitled"
    slug = slug or fm.get("slug") or slugify(title or "untitled")
    description = description or fm.get("description") or auto_description(body)
    tags_list = parse_tags(tags if tags is not None else fm.get("tags", ""))
    author = author or fm.get("author") or DEFAULTS["author"]
    image = image or fm.get("image") or ""
    # featured: legacy boolean -> homepage hero (kept working; home_slot wins)
    featured = str(fm.get("featured", "")).lower() in ("1", "true", "yes", "y")

    # Layout attributes — defaults mirror the DB column defaults, so a page
    # materialized from a fresh DB row needs no frontmatter at all.
    page_layout = (fm.get("page_layout") or "article").strip().lower()
    if page_layout not in VALID_PAGE_LAYOUTS:
        print(f"⚠️  {slug}: unknown page_layout '{page_layout}' -> 'article'")
        page_layout = "article"
    home_slot = (fm.get("home_slot") or "auto").strip().lower()
    if home_slot not in VALID_HOME_SLOTS:
        print(f"⚠️  {slug}: unknown home_slot '{home_slot}' -> 'auto'")
        home_slot = "auto"
    try:
        home_weight = int(str(fm.get("home_weight") or 0).strip() or 0)
    except ValueError:
        home_weight = 0
    if featured and home_slot == "auto":
        home_slot = "hero"   # legacy flag still means "put it in the hero"

    # Use frontmatter date if present, otherwise fall back to now
    fm_date = fm.get("date")
    if fm_date:
        try:
            now = datetime.fromisoformat(fm_date)
        except ValueError:
            now = datetime.now(timezone.utc)
    else:
        now = datetime.now(timezone.utc)
    iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    display = now.strftime("%B %d, %Y")

    # Multi-layout components: inline directives + frontmatter `blocks`
    from blog_automation.layouts import (
        directives_from_markdown,
        parse_frontmatter_blocks,
        render_blocks,
        substitute_tokens,
    )

    body = normalize_links(
        body, known_slugs if known_slugs is not None else _known_slugs()
    )
    body = linkify_source_refs(body)
    body_clean, block_tokens = directives_from_markdown(body)
    html_body = markdown2.markdown(
        body_clean,
        extras=["fenced-code-blocks", "tables", "strike", "task_list", "header-ids"],
    )
    html_body = externalize_links(substitute_tokens(html_body, block_tokens))
    frontmatter_blocks = parse_frontmatter_blocks(fm.get("blocks"))
    if frontmatter_blocks:
        html_body += "\n" + render_blocks(frontmatter_blocks)
    wc = count_words(body)

    og_img = (
        f'<meta property="og:image" content="{_social_image(image)}">' if image else ""
    )
    tw_img = (
        f'<meta name="twitter:image" content="{_social_image(image)}">' if image else ""
    )
    tags_html = "".join(f"<span>{t}</span>" for t in tags_list)
    # NatGeo-style hero (top image) + section kicker (eyebrow)
    kicker = (tags_list[0].upper() if tags_list else DEFAULTS["site_name"].upper())
    hero_html = (
        f'<figure class="hero"><img src="{_hero_image(image)}" alt="{title}" loading="eager"></figure>'
        if image else ""
    )

    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": iso,
        "author": {"@type": "Person", "name": author},
    }
    if image:
        ld["image"] = _social_image(image)

    # Cloudflare Pages serves article pages ONLY at the trailing-slash URL
    # (it 308-redirects /slug -> /slug/). Canonical MUST point at the 200 URL,
    # otherwise Google flags every page as "Page with redirect".
    canonical = f"{DEFAULTS['site_url']}/{slug}/"

    html = PAGE_TEMPLATE.format(
        layout_css=LAYOUT_CSS,
        site_css=SITE_CSS,
        h1_title=title,
        footer_cols=footer_cols_html(),
        lang=DEFAULTS["lang"],
        title=f"{title} — {DEFAULTS['site_name']}",
        description=description,
        author=author,
        site_name=DEFAULTS["site_name"],
        canonical_url=canonical,
        share_url=quote(canonical, safe=""),
        share_text=quote(f"{title} {_hashtag_str(tags_list)}".strip(), safe=""),
        published_time=iso,
        iso_date=iso,
        display_date=display,
        word_count=wc,
        tags_html=tags_html,
        kicker=kicker,
        hero_html=hero_html,
        hashtags_html=_hashtags_html(tags_list),
        author_avatar=_avatar(author),
        og_image=og_img,
        twitter_image=tw_img,
        og_locale=DEFAULTS["lang"].replace("-", "_"),
        ld_json=json.dumps(ld, ensure_ascii=False),
        content_html=html_body,
    )

    return (
        slug,
        html,
        {
            "title": title,
            "slug": slug,
            "description": description,
            "tags": tags_list,
            "author": author,
            "image": image,
            "date": iso,
            "word_count": wc,
            "featured": featured,
            "page_layout": page_layout,
            "home_slot": home_slot,
            "home_weight": home_weight,
        },
    )


# ---------------------------------------------------------------------------
# Site-level files
# ---------------------------------------------------------------------------
# Homepage topic buckets — drive both the bento tiles' `data-topic` and the
# filter chips. First match wins, so list the most specific needles first.
TOPIC_DEFS = [
    ("espresso", "Espresso", ("espresso", "moka", "cortado", "latte", "americano", "crema", "sua da")),
    ("vietnamese", "Vietnamese", ("vietnamese", "phin", "cà phê", "ca phe", "egg coffee", "robusta", "hanoi")),
    ("brewing", "Brewing", ("pour over", "french press", "bloom", "grind", "ratio", "brew", "filter", "drip", "strong")),
    ("gear", "Beans & gear", ("best ", "review", "machine", "grinder", "beans", "brands", "budget", "descale", "clean")),
    ("culture", "Culture", ("culture", "travel", "food", "history", "hue", "pho")),
]


def topic_of(p: dict) -> str:
    """Bucket a post into one homepage topic (drives bento filters)."""
    hay = (p.get("title", "") + " " + " ".join(p.get("tags") or [])).lower()
    for key, _label, needles in TOPIC_DEFS:
        if any(n in hay for n in needles):
            return key
    return "brewing"


def _slot_sorted(items: list[dict]) -> list[dict]:
    """Explicit `home_weight` first, then newest — stable curation order.

    Both keys sort descending, so `reverse=True` gives weight-then-recency; an
    ISO date string sorts correctly as text.
    """
    return sorted(
        items,
        # slug as the last key makes ties (same date) deterministic across the
        # file-driven build and the DB-driven dashboard build
        key=lambda p: (
            int(p.get("home_weight") or 0),
            p.get("date") or "",
            p.get("slug") or "",
        ),
        reverse=True,
    )


def assign_home_slots(posts_meta: list[dict]) -> tuple[dict[str, list[dict]], list[str]]:
    """Group posts into homepage slots from their layout attributes.

    Explicit `home_slot` wins (validated against `SLOT_CAPACITY`; overflow and
    unknown values fall back to `auto` with a warning instead of silently
    reshuffling the page). Everything left on `auto` fills the remaining
    hero/wide/small capacity newest-first, and the remainder becomes the
    "More stories" list — so a page generated by the pipeline always lands
    somewhere sane without anyone curating it.
    """
    buckets: dict[str, list[dict]] = {s: [] for s in VALID_HOME_SLOTS if s != "auto"}
    warnings: list[str] = []
    auto: list[dict] = []

    for p in _slot_sorted(posts_meta):
        slot = (p.get("home_slot") or "auto").strip().lower()
        if slot in ("auto", ""):
            auto.append(p)
            continue
        if slot not in VALID_HOME_SLOTS:
            warnings.append(f"{p['slug']}: unknown home_slot '{slot}' -> auto")
            auto.append(p)
            continue
        cap = SLOT_CAPACITY.get(slot)
        if cap is not None and len(buckets[slot]) >= cap:
            warnings.append(
                f"{p['slug']}: home_slot '{slot}' is full (max {cap}) -> auto"
            )
            auto.append(p)
            continue
        buckets[slot].append(p)

    # Fill the visual slots with the newest unassigned posts that still have art
    pool = list(auto)
    for slot, n in AUTO_FILL_ORDER:
        have = len(buckets[slot])
        need = max(0, n - have)
        if not need:
            continue
        picked = [p for p in pool if p.get("image")][:need]
        if len(picked) < need:  # not enough images left — take text-only posts too
            picked += [p for p in pool if p not in picked][: need - len(picked)]
        for p in picked:
            buckets[slot].append(p)
            pool.remove(p)

    # everything else -> "More stories" (text list, still indexed/linked)
    buckets["list"] = sorted(pool + buckets["list"], key=lambda p: p.get("date") or "", reverse=True)
    buckets["none"] = buckets.get("none", [])
    for s in ("hero", "wide", "small", "text"):
        buckets[s] = _slot_sorted(buckets[s])
    return buckets, warnings


def build_index(posts_meta: list[dict]) -> str:
    """Homepage = bento grid (photo-led) + filter chips + compact 'More stories' list.

    The bento keeps imagery + scanning; the trailing list keeps the internal-link
    count (and crawl paths) that the old card grid provided.
    """
    from collections import Counter

    def _url(p, width):
        img = p.get("image") or ""
        if img:
            return re.sub(r"w=\d+", f"w={width}", img)
        return ""

    def _meta(p):
        wc = p.get("word_count") or 0
        read_min = max(1, round(wc / 200))
        return f"{p.get('date', '')[:10]} · {read_min} min read"

    def _kicker(p):
        tags = p.get("tags") or []
        return tags[0].title() if tags else "Coffee"

    def _tile(p, cls, width=800):
        topic = topic_of(p)
        alt = p["title"].replace('"', "&quot;")
        url = _url(p, width)
        if not url:  # no image -> text tile (still clickable)
            return (
                f'<a class="tile flat" href="/{p["slug"]}/" data-topic="{topic}">'
                f'<h2>{p["title"]}</h2><p>{_kicker(p)} · {_meta(p)}</p></a>'
            )
        kick = f'<div class="k">{_kicker(p)}</div>' if cls in ("big", "wide") else ""
        return (
            f'<a class="tile {cls}" href="/{p["slug"]}/" data-topic="{topic}">'
            f'<img src="{url}" alt="{alt}" loading="lazy" width="800" height="600">'
            f'<div class="cap">{kick}<h2>{p["title"]}</h2></div></a>'
        )

    def _dark(p):
        return (
            f'<a class="tile dark" href="/{p["slug"]}/" data-topic="{topic_of(p)}">'
            f'<div class="k" style="font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;'
            f'color:#f0dcc0;font-weight:700;margin-bottom:6px">{_kicker(p)}</div>'
            f'<h2>{p["title"]}</h2><p>{p.get("description", "")[:110]}…</p></a>'
        )

    slots, slot_warnings = assign_home_slots(posts_meta)
    for w in slot_warnings:
        print(f"⚠️  homepage slot: {w}")
    hero, wide, small, spotlight = slots["hero"], slots["wide"], slots["small"], slots["text"]
    more = slots["list"] + slots["none"]

    tiles = []
    tiles += [_tile(p, "big", 1200) for p in hero[:1]]
    tiles += [_tile(p, "wide") for p in wide]
    tiles += [_tile(p, "") for p in small[:3]]

    # Static recipe tile (real numbers), linked to the cold-brew guide when present
    cold = next((p for p in posts_meta if "cold-brew" in p["slug"] or "cold brew" in p["title"].lower()), None)
    if cold:
        tiles.append(
            f'<a class="tile flat" href="/{cold["slug"]}/" data-topic="brewing">'
            '<h2>Try the 1:4 cold brew ratio</h2>'
            '<p>Coarse grind, 16 hours in the fridge — smooth, never bitter.</p>'
            '<code>50 g coffee · 200 g water</code></a>'
        )

    tiles += [_tile(p, "") for p in small[3:]]
    tiles += [_dark(p) for p in spotlight]
    tiles.append(
        '<a class="tile flat" href="/rss.xml" data-topic="all">'
        '<h2>Every new guide, straight to your reader</h2>'
        '<p>No tracking, no popups — just the posts.</p><code>/rss.xml</code></a>'
    )

    # Filter chips from the same buckets the tiles use
    counts = Counter(topic_of(p) for p in posts_meta)
    labels = {k: lbl for k, lbl, _ in TOPIC_DEFS}
    filters_html = f'<button data-topic="all" aria-pressed="true">All ({len(posts_meta)})</button>'
    for key, n in counts.most_common():
        if n < 2:
            continue
        filters_html += f'<button data-topic="{key}" aria-pressed="false">{labels.get(key, key.title())} ({n})</button>'

    # Cap the list so the homepage stays scannable; the sitemap holds the rest
    # and stays the archive entry point.
    MORE_CAP = 18
    more_shown = more[:MORE_CAP]
    more_html = "".join(
        f'<li data-topic="{topic_of(p)}"><span class="mn">{i:02d}</span>'
        f'<div><span class="mk">{_kicker(p)}</span>'
        f'<a href="/{p["slug"]}/">{p["title"]}</a>'
        f'<span class="mmeta">{_meta(p)}</span></div></li>'
        for i, p in enumerate(more_shown, 1)
    )
    if len(more) > MORE_CAP:
        more_html += (
            '<li style="grid-column:1/-1;border-bottom:0;padding-top:6px">'
            f'<a class="moreall" href="/sitemap.xml">All {len(more) + len(more_shown)} '
            'stories in the archive →</a></li>'
        )

    index_ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": DEFAULTS["site_name"],
            "url": f"{DEFAULTS['site_url']}/",
            "description": DEFAULTS["description"],
            "inLanguage": DEFAULTS["lang"],
        },
        {
            "@context": "https://schema.org",
            "@type": "Blog",
            "name": DEFAULTS["site_name"],
            "url": f"{DEFAULTS['site_url']}/",
            "description": DEFAULTS["description"],
            "inLanguage": DEFAULTS["lang"],
            "author": {"@type": "Person", "name": DEFAULTS["author"]},
        },
    ]

    return INDEX_TEMPLATE.format(
        layout_css=LAYOUT_CSS,
        site_css=SITE_CSS,
        footer_cols=footer_cols_html(),
        lang=DEFAULTS["lang"],
        site_name=DEFAULTS["site_name"],
        title=f"{DEFAULTS['site_name']} — Latest Posts & Articles on Coffee, Brewing & Home Barista Tips",
        site_url=DEFAULTS["site_url"],
        description=DEFAULTS["description"],
        index_ld_json=json.dumps(index_ld, ensure_ascii=False),
        post_count=len(posts_meta),
        filters_html=filters_html,
        tiles_html="".join(tiles),
        more_html=more_html or '<li>No posts yet.</li>',
        hero_html="",
        topics_html="",
        post_items="",
        popular_html="",
        editors_html="",
    )


def build_sitemap(posts_meta: list[dict]) -> str:
    entries = [
        f"  <url><loc>{DEFAULTS['site_url']}/</loc><changefreq>daily</changefreq></url>"
    ]
    for slug, _label in STATIC_PAGES:
        entries.append(
            f"  <url><loc>{DEFAULTS['site_url']}/{slug}/</loc>"
            "<changefreq>monthly</changefreq><priority>0.4</priority></url>"
        )
    for p in posts_meta:
        entries.append(
            # trailing slash: slashless article URLs 308 on Cloudflare Pages
            f"  <url><loc>{DEFAULTS['site_url']}/{p['slug']}/</loc>"
            f"<lastmod>{p['date'][:10]}</lastmod></url>"
        )
    return SITEMAP_TEMPLATE.format(entries="\n".join(entries))


def build_rss(posts_meta: list[dict]) -> str:
    """Build RSS 2.0 feed from posts_meta."""
    from xml.sax.saxutils import escape

    site = DEFAULTS["site_name"]
    site_url = DEFAULTS["site_url"]
    desc = DEFAULTS["description"]

    items = []
    for p in posts_meta:
        items.append(
            "    <item>\n"
            f"      <title>{escape(p['title'])}</title>\n"
            f"      <link>{site_url}/{p['slug']}/</link>\n"
            f'      <guid isPermaLink="true">{site_url}/{p["slug"]}/</guid>\n'
            f"      <pubDate>{_rss_date(p['date'])}</pubDate>\n"
            f"      <description>{escape(p['description'])}</description>\n"
            + (
                f'      <enclosure url="{escape(p["image"])}" type="image/jpeg"/>\n'
                if p.get("image")
                else ""
            )
            + "    </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>\n"
        f"  <title>{escape(site)}</title>\n"
        f"  <link>{site_url}</link>\n"
        f"  <description>{escape(desc)}</description>\n"
        f'  <atom:link href="{site_url}/rss.xml" rel="self" type="application/rss+xml"/>\n'
        f"  <lastBuildDate>{_rss_date(posts_meta[0]['date']) if posts_meta else _rss_date('')}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n</channel>\n</rss>\n"
    )


def _rss_date(iso: str) -> str:
    """Convert ISO date (2026-08-08T08:02:15Z) to RFC-822 (Sat, 08 Aug 2026 08:02:15 GMT)."""
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().strftime("%a, %d %b %Y %H:%M:%S %z")
    return dt.astimezone().strftime("%a, %d %b %Y %H:%M:%S %z")


def load_meta_index(meta_file: Path) -> list[dict]:
    if meta_file.exists():
        return json.loads(meta_file.read_text())
    return []


def save_meta_index(meta_file: Path, posts: list[dict]) -> None:
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    meta_file.write_text(json.dumps(posts, ensure_ascii=False, indent=2))


def build_site(
    dist: Path, posts_meta: list[dict], new_slug: str, new_html: str
) -> None:
    import shutil

    dist.mkdir(parents=True, exist_ok=True)

    # Copy static assets (favicon, _redirects, etc.)
    _ROOT = Path(__file__).resolve().parent.parent
    favicon = _ROOT / "public" / "favicon.svg"
    if favicon.exists():
        shutil.copy2(favicon, dist / "favicon.svg")
    # NOTE: Cloudflare Pages does NOT support domain-level redirects in
    # _redirects (official docs: "Domain-level redirects ❌"). So www→apex
    # CANNOT be done with a rule like `https://www.x/* https://x/:splat 301`
    # — it is silently ignored. www→apex must be a ZONE-level Redirect Rule
    # (dash → dripper.top → Rules → Redirect Rules), or left to the canonical
    # tag (every www page already points its canonical at the apex, which GSC
    # reports as the benign "Alternate page with proper canonical tag").
    # Only same-host PATH redirects may live here.
    (dist / "_redirects").write_text(
        "# Path redirects only — domain-level (www→apex) redirects are NOT\n"
        "# supported by Cloudflare Pages. Use a zone Redirect Rule for those.\n",
        encoding="utf-8",
    )

    (dist / "index.html").write_text(build_index(posts_meta), encoding="utf-8")
    (dist / "sitemap.xml").write_text(build_sitemap(posts_meta), encoding="utf-8")
    (dist / "rss.xml").write_text(build_rss(posts_meta), encoding="utf-8")
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {DEFAULTS['site_url']}/sitemap.xml\n"
    )

    if new_slug:
        pd = dist / new_slug
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "index.html").write_text(new_html, encoding="utf-8")

    print(f"✅ Built {len(posts_meta)} posts → {dist}/")


# ---------------------------------------------------------------------------
# ─── Deploy ────────────────────────────────────────────────────────────
def _deploy(dist: Path) -> None:
    """Upload public/ to Cloudflare Pages.

    Prefers the wrangler CLI (local dev). Falls back to the Cloudflare Pages
    Direct Upload API (zip + upload) when wrangler is absent — which is the
    case on Streamlit Cloud, where only `requests` is available.
    """
    import shutil

    if shutil.which("wrangler"):
        project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
        subprocess.run(
            [
                "wrangler",
                "pages",
                "deploy",
                str(dist.resolve()),
                "--project-name",
                project,
                "--branch",
                "main",
                "--commit-dirty",
                "true",
            ],
            check=False,
        )
        print(f"🌍 Live: {DEFAULTS['site_url']}")
        return
    _deploy_via_api(dist)


def _deploy_via_api(dist: Path) -> None:
    """Cloudflare Pages Direct Upload API — no wrangler binary needed.

    Requires env: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_PROJECT_NAME (default side-blogs).
    """
    import tempfile
    import zipfile

    import requests

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
    if not token or not account:
        print("⚠️  No CLOUDFLARE_API_TOKEN/ACCOUNT_ID and no wrangler. Skipping deploy.")
        return

    api_base = f"https://api.cloudflare.com/client/v4/accounts/{account}/pages/projects"
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Zip dist/
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(dist):
                for fname in files:
                    full = Path(root) / fname
                    zf.write(full, full.relative_to(dist))
    finally:
        tmp.close()

    # 2. Request deployment upload URL
    r = requests.post(
        f"{api_base}/{project}/deployments",
        headers=headers,
        json={"branch": "main"},
        timeout=60,
    )
    r.raise_for_status()
    deployment = r.json()["result"]

    # 3. Upload zip
    with open(tmp.name, "rb") as f:
        r2 = requests.post(
            deployment["upload_url"],
            headers={"Content-Type": "application/zip"},
            data=f,
            timeout=300,
        )
    os.unlink(tmp.name)

    if r2.status_code not in (200, 201, 204):
        print(f"❌ Upload failed: {r2.status_code} {r2.text[:300]}")
        return
    print(f"📦 Deployed via API: deployment {deployment['id'][:8]}...")
    print(f"🌍 Live: {DEFAULTS['site_url']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Publish markdown → static site → GitHub push"
    )
    p.add_argument("file", nargs="?", help="Markdown file to publish")
    p.add_argument("-t", "--title", help="Post title")
    p.add_argument("-d", "--description", help="Meta description")
    p.add_argument("--slug", help="URL slug")
    p.add_argument("--tags", help="Comma-separated tags")
    p.add_argument("--author", help="Override author")
    p.add_argument("--image", help="OG image URL")
    p.add_argument("--no-push", action="store_true", help="Build only, skip git push")
    p.add_argument(
        "--allow-stale",
        action="store_true",
        help="Proceed with the build even if the DB sync fails. Dangerous: "
        "deploys whatever (possibly stale) content/ is on disk — wrong "
        "featured/hero and missing dashboard-published pages.",
    )
    return p.parse_args()


def main():
    args = parse_cli()
    dist = Path(DEFAULTS["dist_dir"])
    meta_file = dist / "posts.json"

    # ------------------------------------------------------------------
    # Batch mode: process all content/*.md
    # ------------------------------------------------------------------
    if not args.file:
        content_dir = Path(DEFAULTS["content_dir"])
        if not content_dir.exists():
            print(f"❌ No content dir at {content_dir}/")
            print("Usage: publish.py <file.md>    or drop .md files in content/")
            sys.exit(1)

        # DB is the single source of truth: materialize any PUBLISHED article
        # the DB has but content/ lacks (dashboard-approved pages), so a local
        # rebuild can never drop a live page. Same-slug files are overwritten
        # from the DB too (reverts local-stale images/content). pending_review
        # rows are NEVER materialized; legacy dup slugs are skipped.
        try:
            import reconcile_live

            reconcile_live.sync_published()
        except Exception as e:  # noqa: BLE001
            if not args.allow_stale:
                raise SystemExit(
                    f"❌ DB sync failed ({e.__class__.__name__}: {str(e)[:120]}).\n"
                    "   Refusing to build from stale content/ — it would deploy the "
                    "wrong featured/hero and drop dashboard-published pages.\n"
                    "   Fix DATABASE_URL / network, or pass --allow-stale to override."
                ) from e
            print(f"⚠️  DB materialize skipped ({e.__class__.__name__}: "
                  f"{str(e)[:80]}) — building from content/ only (--allow-stale)")

        posts_meta: list[dict] = []
        all_slugs: set[str] = set()
        post_htmls: dict[str, str] = {}

        for md_file in sorted(content_dir.glob("*.md")):
            print(f"📝 Processing {md_file.name}...")
            slug, html, meta = build_article(str(md_file))
            if slug in all_slugs:
                print(f"⚠️  Duplicate slug '{slug}', skipping {md_file.name}")
                continue
            all_slugs.add(slug)
            posts_meta.append(meta)
            post_htmls[slug] = html

        posts_meta.sort(key=lambda m: m["date"], reverse=True)
        save_meta_index(meta_file, posts_meta)
        build_site(dist, posts_meta, "", "")

        for slug, html in post_htmls.items():
            pd = dist / slug
            pd.mkdir(parents=True, exist_ok=True)
            (pd / "index.html").write_text(html, encoding="utf-8")

        if not args.no_push:
            print("📤 Uploading to Cloudflare Pages via wrangler...")
            _deploy(dist)
        return

    # ------------------------------------------------------------------
    # Single-post mode
    # ------------------------------------------------------------------
    slug, html, meta = build_article(
        args.file,
        title=args.title,
        description=args.description,
        slug=args.slug,
        tags=args.tags,
        author=args.author,
        image=args.image,
    )

    posts_meta = load_meta_index(meta_file)
    existing = {p["slug"]: i for i, p in enumerate(posts_meta)}
    if slug in existing:
        posts_meta[existing[slug]] = meta
    else:
        posts_meta.append(meta)
    posts_meta.sort(key=lambda m: m["date"], reverse=True)

    save_meta_index(meta_file, posts_meta)
    build_site(dist, posts_meta, slug, html)

    if not args.no_push:
        _deploy(dist)

    print(f"\n✨ Done! Preview: {dist}/{slug}/index.html")
    print(f"   Live: {DEFAULTS['site_url']}/{slug}")


if __name__ == "__main__":
    main()

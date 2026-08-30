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
from urllib.parse import quote

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
.layout-hero p{color:#8a7a6a;font-size:1.05rem;margin:.5rem 0 0}
.layout-figure{margin:1.4rem 0}
.layout-figure img{max-width:100%;border-radius:14px}
.layout-figure figcaption{font-size:.85rem;color:#8a7a6a;text-align:center;margin-top:.5rem}
.layout-callout{border-left:4px solid #b07840;background:#f7efe3;padding:14px 18px;border-radius:12px;margin:1.2rem 0}
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
.layout-recipe .meta{color:#8a7a6a;font-size:.9rem}
.layout-faq{margin:1.2rem 0}
.layout-faq details{border:1px solid #e6dccb;border-radius:10px;padding:12px 16px;margin:.5rem 0}
.layout-faq summary{cursor:pointer;font-weight:600}
.layout-faq-item p{margin:.5rem 0 0}
.layout-quote{border-left:4px solid #b07840;padding-left:16px;color:#5b5240;font-style:italic;margin:1.2rem 0}
.layout-quote cite{display:block;font-style:normal;font-size:.85rem;color:#8a7a6a;margin-top:.4rem}
.layout-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:1.2rem 0}
.layout-card{border:1px solid #e6dccb;border-radius:12px;padding:16px;background:#fff}
.layout-card h4{margin:.2rem 0}
"""

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
    <style>
        :root{{--bg:#faf6ef;--surface:#fff;--ink:#3a2f28;--muted:#8a7a6a;--accent:#b07840;--accent-soft:#e8dcc9;--line:#e6dccb;--serif:"Fraunces",Georgia,serif;--sans:"Inter",-apple-system,sans-serif}}
        *{{box-sizing:border-box}}
        html{{-webkit-font-smoothing:antialiased}}
        body{{font-family:var(--sans);line-height:1.75;color:var(--ink);background:var(--bg);margin:0}}
        a{{color:var(--accent)}}
        nav{{background:var(--surface);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:10}}
        nav .inner{{width:min(75%,1080px);margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
        nav .brand{{font-family:var(--serif);font-weight:700;font-size:1.3rem;color:var(--ink);text-decoration:none}}
        nav .nav-links a{{color:var(--muted);text-decoration:none;margin-left:20px;font-size:.92rem;font-weight:500}}
        nav .nav-links a:hover{{color:var(--accent)}}
        .container{{width:min(94%,1360px);margin:0 auto;padding:0 24px}}
        .article{{padding:48px 0 64px}}
        .hero{{margin:0 0 22px}}
        .hero img{{width:100%;height:auto;max-height:560px;object-fit:cover;border-radius:18px;display:block}}
        .hero figcaption{{color:#8a7a6a;font-size:.82rem;margin-top:.5rem}}
        header{{margin-bottom:32px}}
        .kicker{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:12px}}
        h1{{font-family:var(--serif);font-weight:700;font-size:2.5rem;line-height:1.12;margin:0 0 14px;color:var(--ink);letter-spacing:-.01em}}
        .deck{{font-size:1.25rem;line-height:1.55;color:#8a7a6a;max-width:680px;margin:0 0 22px}}
        .byline{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;color:#8a7a6a;font-size:.85rem;padding-bottom:22px;border-bottom:1px solid var(--line)}}
        .byline .avatar{{width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #e8dcc9}}
        .byline .by{{font-weight:600;color:var(--ink)}}
        .byline .dot{{width:3px;height:3px;border-radius:50%;background:#b8aa96;display:inline-block}}
        .tags{{margin-top:16px}}
        .tags span{{display:inline-block;padding:4px 12px;border-radius:999px;font-size:.72rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;background:var(--accent-soft);color:#7a5a34;margin-right:6px}}
        .content{{font-size:1.1rem;max-width:1000px;margin:0 auto}}
        .content p{{margin:1.15em 0}}
        .content>p:first-of-type::first-letter{{font-family:var(--serif);font-weight:700;font-size:3.6em;float:left;line-height:.82;padding:.06em .12em 0 0;color:var(--accent)}}
        .content h2{{font-family:var(--serif);font-size:1.7rem;font-weight:600;margin:2.4rem 0 .8rem;color:var(--ink)}}
        .content h3{{font-family:var(--serif);font-size:1.32rem;font-weight:600;margin:1.8rem 0 .6rem;color:var(--ink)}}
        .content a{{color:var(--accent);text-decoration:underline;text-underline-offset:2px}}
        .content img{{max-width:100%;height:auto;border-radius:14px;margin:1.2em 0}}
        .content pre{{background:#f4ede1;padding:18px;border-radius:12px;overflow-x:auto;font-size:.9rem;line-height:1.6}}
        .content code{{font-family:"SF Mono",Monaco,"Cascadia Code",monospace}}
        .content blockquote{{border-left:3px solid #b07840;padding-left:18px;margin:1.4em 0;color:#5b5240;font-style:italic}}
        .content table{{width:100%;border-collapse:collapse;margin:1.4em 0}}
        .content th,.content td{{padding:10px 14px;border:1px solid var(--line)}}
        .content th{{background:var(--surface);font-weight:600}}
        .related{{margin-top:44px;padding-top:28px;border-top:1px solid var(--line)}}
        .related .label{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:#b07840;font-weight:600;margin-bottom:14px}}
        .share{{margin-top:40px;padding-top:24px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
        .hashtags{{margin-top:34px;padding:18px 0;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px}}
        .hashtags span{{font-size:.85rem;font-weight:600;color:#b07840}}
        .hashtags span::before{{content:"#"}}
        .share .share-label{{color:#8a7a6a;font-size:.9rem;font-weight:600;margin-right:6px}}
        .share a,.share button{{display:inline-block;padding:8px 18px;border-radius:999px;font-size:.82rem;font-weight:600;background:var(--surface);color:var(--ink);text-decoration:none;border:1px solid var(--line);cursor:pointer;font-family:inherit}}
        .share a:hover,.share button:hover{{background:#b07840;color:#fff;border-color:#b07840}}
        footer{{text-align:center;color:#8a7a6a;font-size:.85rem;padding:42px 0;margin-top:24px;border-top:1px solid var(--line)}}
        footer .cols{{width:min(75%,1080px);margin:16px auto 0;padding:0 24px;display:flex;flex-wrap:wrap;gap:16px;justify-content:center}}
        footer a{{color:#8a7a6a}}footer a:hover{{color:#b07840}}
        @media(max-width:640px){{
            .container{{padding:0 18px}}
            h1{{font-size:1.8rem}}
            .deck{{font-size:1.12rem}}
            .content{{font-size:1rem}}
            .content h2{{font-size:1.3rem}}
            .content h3{{font-size:1.15rem}}
            .hero img{{max-height:none}}
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
        <h1>{title}</h1>
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
<div class="cols"><a href="/about">About Us</a><a href="/contributors">Contributors</a><a href="/contact">Contact</a><a href="/newsletter">Newsletter</a><a href="/pay-it-forward">Pay it Forward</a><a href="/sustainability">Sustainability</a><a href="/sitemap.xml">Sitemap</a><a href="/rss.xml">RSS</a></div>
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
    <link rel="canonical" href="{site_url}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{site_url}">
    <link rel="alternate" type="application/rss+xml" title="{site_name} RSS" href="/rss.xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>{layout_css}</style>
    <style>
        :root{{--bg:#faf6ef;--surface:#fff;--ink:#3a2f28;--muted:#8a7a6a;--accent:#b07840;--accent-soft:#e8dcc9;--line:#e6dccb;--serif:"Fraunces",Georgia,serif;--sans:"Inter",-apple-system,sans-serif}}
        *{{box-sizing:border-box}}
        body{{font-family:var(--sans);line-height:1.7;color:var(--ink);background:var(--bg);margin:0}}
        a{{color:var(--accent)}}
        nav{{background:var(--surface);border-bottom:1px solid var(--line);padding:14px 0;position:sticky;top:0;z-index:10}}
        nav .inner{{width:min(75%,1360px);margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
        nav .brand{{font-family:var(--serif);font-weight:700;font-size:1.3rem;color:var(--ink);text-decoration:none}}
        nav .nav-links a{{color:var(--muted);text-decoration:none;margin-left:20px;font-size:.92rem;font-weight:500}}
        nav .nav-links a:hover{{color:var(--accent)}}
        .container{{width:min(75%,1360px);margin:40px auto 60px;padding:0 24px}}
        .hero-mag{{position:relative;border-radius:20px;overflow:hidden;margin-bottom:44px;background:var(--surface);box-shadow:0 10px 30px rgba(58,47,40,.08)}}
        .hero-mag .hero-photo{{width:100%;height:420px;object-fit:cover;display:block}}
        .hero-mag .hero-body{{padding:32px 36px}}
        .hero-mag .hero-kicker{{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:10px}}
        .hero-mag h1{{font-family:var(--serif);font-weight:700;font-size:2.3rem;line-height:1.15;margin:0 0 12px}}
        .hero-mag h1 a{{color:var(--ink);text-decoration:none}}
        .hero-mag h1 a:hover{{color:var(--accent)}}
        .hero-mag p{{color:var(--muted);font-size:1.05rem;margin:0 0 18px;max-width:720px}}
        .hero-mag .meta{{color:var(--muted);font-size:.85rem;display:flex;gap:16px;flex-wrap:wrap;align-items:center}}
        .hero-mag .read-link{{font-weight:600;color:var(--accent);text-decoration:none}}
        .topics{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:40px}}
        .chip{{background:var(--accent-soft);color:#7a5a34;font-size:.8rem;font-weight:600;padding:6px 14px;border-radius:999px;letter-spacing:.02em}}
        .section-heading{{display:flex;align-items:center;gap:14px;margin:0 0 26px;font-family:var(--serif);font-size:1.1rem;color:var(--ink);font-weight:600}}
        .section-heading:after{{content:"";flex:1;height:1px;background:var(--line)}}
        .mag-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:28px;list-style:none;margin:0;padding:0}}
        .hero-mag .thumb-link img{{width:100%;height:420px;object-fit:cover;display:block;cursor:pointer}}
        .thumb-link{{display:block;cursor:pointer;text-decoration:none}}
        .thumb-link img{{width:100%;display:block}}
        .card .thumb{{height:210px;object-fit:cover}}
        .mini-list{{list-style:none;margin:0 0 46px;padding:0;max-width:840px}}
        .mini-item{{display:flex;gap:20px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}}
        .mini-item:last-child{{border-bottom:none}}
        .mini-item .mini-thumb{{width:180px;height:120px;flex-shrink:0;object-fit:cover;border-radius:14px;cursor:pointer}}
        .mini-item .mini-thumb.placeholder{{background:var(--accent-soft);display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.75rem}}
        .mini-item .mini-body{{min-width:0;flex:1}}
        .mini-item .mini-kicker{{font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600}}
        .mini-item h4{{margin:5px 0 8px}}
        .mini-item h4 a{{font-family:var(--serif);font-weight:600;font-size:1.25rem;line-height:1.3;color:var(--ink);text-decoration:none}}
        .mini-item h4 a:hover{{color:var(--accent)}}
        .mini-item .meta{{color:var(--muted);font-size:.85rem}}
        .avatar{{width:26px;height:26px;border-radius:50%;object-fit:cover;vertical-align:middle}}
        .byline{{display:inline-flex;align-items:center;gap:7px;margin-right:14px;vertical-align:middle}}
        .byline .author-name{{color:var(--ink);font-weight:600;font-size:.82rem;letter-spacing:.01em}}
        @media(max-width:640px){{.mini-item{{gap:14px}}.mini-item .mini-thumb{{width:104px;height:80px}}}}
        .card{{background:var(--surface);border-radius:16px;overflow:hidden;box-shadow:0 4px 16px rgba(58,47,40,.06);transition:transform .18s,box-shadow .18s;display:flex;flex-direction:column;border:1px solid var(--line);position:relative}}
        .card h3 a::after{{content:"";position:absolute;inset:0;z-index:1;cursor:pointer}}
        .card:hover{{transform:translateY(-5px);box-shadow:0 14px 32px rgba(58,47,40,.14)}}
        .card .thumb{{width:100%;height:210px;object-fit:cover;display:block}}
        .card .thumb.placeholder{{display:flex;align-items:center;justify-content:center;background:var(--accent-soft);color:var(--muted);font-size:.85rem}}
        .card .body{{flex:1;min-width:0;padding:20px 22px 24px;display:flex;flex-direction:column}}
        .card .kicker{{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:8px}}
        .card h3{{margin:0 0 10px}}
        .card h3 a{{font-family:var(--serif);font-weight:600;font-size:1.22rem;line-height:1.3;color:var(--ink);text-decoration:none}}
        .card h3 a:hover{{color:var(--accent)}}
        .card .desc{{color:var(--muted);font-size:.92rem;flex:1}}
        .card .meta{{color:var(--muted);font-size:.8rem;margin-top:16px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:12px;align-items:center}}
        footer{{text-align:center;color:var(--muted);font-size:.85rem;padding:36px 0}}
        footer .cols{{width:min(75%,1360px);margin:16px auto 0;padding:0 24px;display:flex;flex-wrap:wrap;gap:16px;justify-content:center}}
        footer a{{color:var(--muted)}}footer a:hover{{color:var(--accent)}}
        @media(max-width:640px){{
            .container{{padding:0 18px}}
            .hero-mag .hero-photo{{height:260px}}
            .hero-mag h1{{font-size:1.7rem}}
            .hero-mag .hero-body{{padding:24px 22px}}
            .mag-grid{{grid-template-columns:1fr}}
        }}
    </style>
</head>
<body>
<nav><div class="inner">
    <a class="brand" href="/">{site_name}</a>
    <div class="nav-links"><a href="/">Home</a><a href="/sitemap.xml">Archive</a><a href="/rss.xml">RSS</a></div>
</div></nav>
<main class="container">
    {hero_html}
    <div class="topics">{topics_html}</div>
    <h2 class="section-heading">Latest stories</h2>
    <ul class="mag-grid">{post_items}</ul>
    <h2 class="section-heading">Popular this Month</h2>
    <ul class="mini-list">{popular_html}</ul>
    <h2 class="section-heading">Editors Picks</h2>
    <ul class="mini-list">{editors_html}</ul>
</main>
<footer><p>&copy; 2026 {site_name}.</p>
<div class="cols"><a href="/about">About Us</a><a href="/contributors">Contributors</a><a href="/contact">Contact</a><a href="/newsletter">Newsletter</a><a href="/pay-it-forward">Pay it Forward</a><a href="/sustainability">Sustainability</a><a href="/sitemap.xml">Sitemap</a><a href="/rss.xml">RSS</a></div>
</footer>
</body>
</html>"""

SITEMAP_TEMPLATE = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULTS = {
    "site_name": os.getenv("SITE_NAME", "The Slow Drip"),
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
    a = (author or "").strip() or "The Slow Drip"
    return (
        f'<span class="byline"><img class="avatar" src="{_avatar(author)}" '
        f'alt="{a}" loading="lazy"><span class="author-name">{a}</span></span>'
    )


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
            plain = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", s)
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
            return f"[{text}](/{target})"
        return text

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _sub, md)


def build_article(
    filepath: str,
    title: str | None = None,
    description: str | None = None,
    slug: str | None = None,
    tags: str | None = None,
    author: str | None = None,
    image: str | None = None,
) -> tuple[str, str, dict]:
    md_text = Path(filepath).read_text(encoding="utf-8")
    fm, body = extract_frontmatter(md_text)

    title = title or fm.get("title") or _guess_title(body) or "Untitled"
    slug = slug or fm.get("slug") or slugify(title or "untitled")
    description = description or fm.get("description") or auto_description(body)
    tags_list = [
        t.strip() for t in (tags or fm.get("tags", "")).split(",") if t.strip()
    ]
    author = author or fm.get("author") or DEFAULTS["author"]
    image = image or fm.get("image") or ""

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

    body = normalize_links(body, _known_slugs())
    body_clean, block_tokens = directives_from_markdown(body)
    html_body = markdown2.markdown(
        body_clean,
        extras=["fenced-code-blocks", "tables", "strike", "task_list", "header-ids"],
    )
    html_body = substitute_tokens(html_body, block_tokens)
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

    canonical = f"{DEFAULTS['site_url']}/{slug}"

    html = PAGE_TEMPLATE.format(
        layout_css=LAYOUT_CSS,
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
        },
    )


# ---------------------------------------------------------------------------
# Site-level files
# ---------------------------------------------------------------------------
def build_index(posts_meta: list[dict]) -> str:
    from collections import Counter

    def _url(p, width):
        img = p.get("image") or ""
        if img:
            return re.sub(r"w=\d+", f"w={width}", img)
        return ""

    def _thumb(p, width, cls="thumb"):
        alt = p["title"].replace('"', "&quot;")
        url = _url(p, width)
        if url:
            return f'<img class="{cls}" src="{url}" alt="{alt}" loading="lazy">'
        return f'<div class="{cls} placeholder">No image</div>'

    def _meta(p):
        wc = p.get("word_count") or 0
        read_min = max(1, round(wc / 200))
        return f"{p.get('date', '')[:10]} · {read_min} min read"

    def _kicker(p):
        tags = p.get("tags") or []
        return tags[0].title() if tags else "Coffee"

    def _mini_item(p):
        alt = p["title"].replace('"', "&quot;")
        url = _url(p, 400)
        thumb = (
            f'<a class="mini-thumb-link" href="/{p["slug"]}">'
            f'<img class="mini-thumb" src="{url}" alt="{alt}" loading="lazy"></a>'
            if url
            else '<div class="mini-thumb placeholder">No image</div>'
        )
        return (
            f'<li class="mini-item">{thumb}<div class="mini-body">'
            f'<div class="mini-kicker">{_kicker(p)}</div>'
            f'<h4><a href="/{p["slug"]}">{p["title"]}</a></h4>'
            f'<div class="meta">{_byline_html(p.get("author"))}<span>{_meta(p)}</span></div></div></li>'
        )

    # Hero = newest post
    hero_html = ""
    if posts_meta:
        f = posts_meta[0]
        hero_html = (
            '<section class="hero-mag">'
            f'<a class="thumb-link" href="/{f["slug"]}">{_thumb(f, 1200)}</a>'
            '<div class="hero-body">'
            + f'<div class="hero-kicker">Featured · {_kicker(f)}</div>'
            + f'<h1><a href="/{f["slug"]}">{f["title"]}</a></h1>'
            + f'<p>{f["description"]}</p>'
            + f'<div class="meta">{_byline_html(f.get("author"))}<span>{_meta(f)}</span>'
            + f'<a class="read-link" href="/{f["slug"]}">Read the story →</a></div>'
            + "</div></section>"
        )

    rest = posts_meta[1:] if posts_meta else []

    # Topic chips
    tag_counts = Counter()
    for p in posts_meta:
        for t in (p.get("tags") or []):
            tag_counts[t.title()] += 1
    topics_html = "".join(
        f'<span class="chip">{t}</span>' for t, _ in tag_counts.most_common(8)
    )

    # Card grid for the rest
    items = []
    for p in rest:
        items.append(
            f'<li class="card"><a class="thumb-link" href="/{p["slug"]}">{_thumb(p, 800)}</a><div class="body">'
            f'<div class="kicker">{_kicker(p)}</div>'
            f'<h3><a href="/{p["slug"]}">{p["title"]}</a></h3>'
            f'<div class="desc">{p["description"]}</div>'
            f'<div class="meta">{_byline_html(p.get("author"))}<span>{_meta(p)}</span></div></div></li>'
        )

    # Popular this Month = top by word count (proxy for depth)
    popular = sorted(rest, key=lambda p: p.get("word_count") or 0, reverse=True)[:3]
    popular_html = "".join(_mini_item(p) for p in popular)

    # Editors Picks = culture/curated tags first, fill from remaining
    culture_tags = {"Vietnamese Coffee", "Coffee Culture", "Phin"}
    picked, seen = [], {p["slug"] for p in ([posts_meta[0]] + popular) if p}
    for p in rest:
        if any(t in culture_tags for t in (p.get("tags") or [])) and p["slug"] not in seen and len(picked) < 3:
            picked.append(p)
            seen.add(p["slug"])
    for p in rest:
        if p["slug"] not in seen and len(picked) < 3:
            picked.append(p)
    editors_html = "".join(_mini_item(p) for p in picked)

    return INDEX_TEMPLATE.format(
        layout_css=LAYOUT_CSS,
        lang=DEFAULTS["lang"],
        site_name=DEFAULTS["site_name"],
        title=f"{DEFAULTS['site_name']} — Latest Posts & Articles on Coffee, Brewing & Home Barista Tips",
        site_url=DEFAULTS["site_url"],
        description=DEFAULTS["description"],
        post_count=len(posts_meta),
        hero_html=hero_html,
        topics_html=topics_html,
        post_items="\n".join(items) if items else '<li class="card">No posts yet.</li>',
        popular_html=popular_html or '<li class="mini-item">No posts yet.</li>',
        editors_html=editors_html or '<li class="mini-item">No posts yet.</li>',
    )

def build_sitemap(posts_meta: list[dict]) -> str:
    entries = [
        f"  <url><loc>{DEFAULTS['site_url']}/</loc><changefreq>daily</changefreq></url>"
    ]
    for p in posts_meta:
        entries.append(
            f"  <url><loc>{DEFAULTS['site_url']}/{p['slug']}</loc>"
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
            f"      <link>{site_url}/{p['slug']}</link>\n"
            f'      <guid isPermaLink="true">{site_url}/{p["slug"]}</guid>\n'
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
    redirects = _ROOT / "public" / "_redirects"
    if redirects.exists():
        shutil.copy2(redirects, dist / "_redirects")

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

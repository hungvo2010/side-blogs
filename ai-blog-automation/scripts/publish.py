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
    <style>
        :root{{--primary:#1a73e8;--text:#1f2937;--muted:#6b7280;--bg:#fff;--code-bg:#f3f4f6}}
        *{{box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.7;color:var(--text);background:#f8fafc;margin:0;padding:0}}
        nav{{background:var(--bg);border-bottom:1px solid #e5e7eb;padding:12px 0}}
        nav .inner{{max-width:800px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;align-items:center}}
        nav a{{color:var(--primary);text-decoration:none;font-weight:600}}
        nav a:hover{{text-decoration:underline}}
        .container{{max-width:800px;margin:32px auto 60px;padding:40px;background:var(--bg);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
        header{{margin-bottom:32px;border-bottom:2px solid #e5e7eb;padding-bottom:20px}}
        h1{{font-size:2.2rem;line-height:1.25;margin-bottom:8px}}
        .meta{{color:var(--muted);font-size:.9rem}}
        .tags{{margin-top:8px}}
        .tags span{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.75rem;font-weight:500;background:#dbeafe;color:#1e40af;margin-right:6px}}
        .content{{font-size:1.1rem}}
        .content h2{{margin-top:2.2rem;font-size:1.5rem;color:#111827}}
        .content h3{{margin-top:1.6rem;font-size:1.25rem;color:#374151}}
        .content p{{margin:1em 0}}
        .content a{{color:var(--primary);text-decoration:underline}}
        .content img{{max-width:100%;height:auto;border-radius:6px;margin:1em 0}}
        .content pre{{background:var(--code-bg);padding:16px;border-radius:8px;overflow-x:auto;font-size:.9rem;line-height:1.5}}
        .content code{{font-family:"SF Mono",Monaco,"Cascadia Code",monospace}}
        .content blockquote{{border-left:4px solid var(--primary);padding-left:16px;margin:1em 0;color:#4b5563;font-style:italic}}
        .content table{{width:100%;border-collapse:collapse;margin:1em 0}}
        .content th,.content td{{padding:8px 12px;border:1px solid #e5e7eb}}
        .content th{{background:#f9fafb;font-weight:600}}
        footer{{margin-top:48px;padding-top:20px;border-top:1px solid #e5e7eb;text-align:center;color:var(--muted);font-size:.85rem}}
        footer a{{color:var(--primary)}}
        footer .cols{{max-width:800px;margin:0 auto;padding:0 20px;display:flex;flex-wrap:wrap;gap:32px;justify-content:space-between}}
        footer h4{{color:var(--text);margin-bottom:8px}}
        footer ul{{list-style:none;padding:0;margin:0}}
        footer li{{margin-bottom:4px}}
        .share{{margin-top:40px;padding-top:20px;border-top:1px solid #e5e7eb;display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
        .share .share-label{{color:var(--muted);font-size:.9rem;font-weight:600}}
        .share a,.share button{{display:inline-block;padding:6px 14px;border-radius:999px;font-size:.85rem;font-weight:500;background:#f3f4f6;color:var(--text);text-decoration:none;border:1px solid #e5e7eb;cursor:pointer;font-family:inherit}}
        .share a:hover,.share button:hover{{background:var(--primary);color:#fff;border-color:var(--primary)}}
        @media(max-width:640px){{
            .container{{padding:20px;margin:16px auto;border-radius:8px}}
            h1{{font-size:1.5rem}}
            .content{{font-size:1rem}}
            .content h2{{font-size:1.25rem}}
            .content h3{{font-size:1.1rem}}
            .content pre{{font-size:.8rem;padding:12px}}
            footer .cols{{flex-direction:column;gap:16px}}
        }}
    </style>
</head>
<body>
<nav><div class="inner"><a href="/">{site_name}</a><a href="/">← All posts</a></div></nav>
<article class="container">
    <header>
        <h1>{title}</h1>
        <div class="meta"><time datetime="{iso_date}">{display_date}</time> · {word_count} words</div>
        <div class="tags">{tags_html}</div>
    </header>
    <div class="content">{content_html}</div>
    <div class="share">
        <span class="share-label">Share this post:</span>
        <a href="https://twitter.com/intent/tweet?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on X">X</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" rel="noopener" aria-label="Share on Facebook">Facebook</a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" rel="noopener" aria-label="Share on LinkedIn">LinkedIn</a>
        <a href="https://wa.me/?text={share_text}%20{share_url}" target="_blank" rel="noopener" aria-label="Share on WhatsApp">WhatsApp</a>
        <a href="https://t.me/share/url?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on Telegram">Telegram</a>
        <a href="mailto:?subject={share_text}&body={share_url}" aria-label="Share via email">Email</a>
        <button type="button" onclick="navigator.clipboard&&navigator.clipboard.writeText('{canonical_url}').then(()=>{{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy link',1500)}})">Copy link</button>
    </div>
</article>
<footer><p>&copy; 2026 {site_name}.</p></footer>
</body>
</html>"""

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
    <style>
        :root{{--primary:#1a73e8;--text:#1f2937;--muted:#6b7280;--bg:#fff}}
        *{{box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.6;color:var(--text);background:#f8fafc;margin:0}}
        nav{{background:var(--bg);border-bottom:1px solid #e5e7eb;padding:12px 0}}
        nav .inner{{max-width:800px;margin:0 auto;padding:0 20px}}
        nav a{{color:var(--primary);text-decoration:none;font-weight:600}}
        .container{{max-width:800px;margin:40px auto 60px;padding:0 20px}}
        header{{margin-bottom:32px}}
        h1{{font-size:2rem}}
        .intro{{color:var(--muted);font-size:.95rem;margin-top:8px}}
        .posts{{list-style:none;padding:0}}
        .posts li{{background:var(--bg);padding:16px 20px;border-radius:10px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);transition:box-shadow .15s;display:flex;gap:16px;align-items:flex-start}}
        .posts li:hover{{box-shadow:0 4px 12px rgba(0,0,0,.1)}}
        .posts .thumb{{width:120px;height:90px;object-fit:cover;border-radius:8px;flex-shrink:0}}
        .posts .thumb.placeholder{{background:#e5e7eb;display:flex;align-items:center;justify-content:center;font-size:.7rem;color:var(--muted)}}
        .posts .post-body{{flex:1;min-width:0}}
        .posts a{{color:var(--text);text-decoration:none;font-size:1.15rem;font-weight:600}}
        .posts a:hover{{color:var(--primary)}}
        .posts .desc{{color:var(--muted);font-size:.9rem;margin-top:4px}}
        .posts .meta{{color:var(--muted);font-size:.8rem;margin-top:4px}}
        @media(max-width:640px){{.posts li{{flex-direction:column}}.posts .thumb{{width:100%;height:160px}}}}
        .share{{margin:32px 0;padding:20px 0;border-top:1px solid #e5e7eb;display:flex;flex-wrap:wrap;align-items:center;gap:8px}}
        .share .share-label{{color:var(--muted);font-size:.9rem;font-weight:600}}
        .share a,.share button{{display:inline-block;padding:6px 14px;border-radius:999px;font-size:.85rem;font-weight:500;background:#f3f4f6;color:var(--text);text-decoration:none;border:1px solid #e5e7eb;cursor:pointer;font-family:inherit}}
        .share a:hover,.share button:hover{{background:var(--primary);color:#fff;border-color:var(--primary)}}
        footer{{text-align:center;color:var(--muted);font-size:.85rem;padding:32px 0}}
        footer .cols{{max-width:800px;margin:0 auto;padding:0 20px;display:flex;flex-wrap:wrap;gap:16px;justify-content:center}}
        footer a{{color:var(--muted)}}footer a:hover{{color:var(--primary)}}
    </style>
</head>
<body>
<nav><div class="inner"><a href="/">{site_name}</a></div></nav>
<main class="container">
    <header><h1>{site_name} — Latest Posts &amp; Articles</h1><p>{description}</p><p class="intro">Welcome to {site_name}. Here you'll find the latest posts and articles about coffee, brewing, and the perfect cup.</p></header>
    <ul class="posts">{post_items}</ul>
    <div class="share">
        <span class="share-label">Share this blog:</span>
        <a href="https://twitter.com/intent/tweet?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on X">X</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" rel="noopener" aria-label="Share on Facebook">Facebook</a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" rel="noopener" aria-label="Share on LinkedIn">LinkedIn</a>
        <a href="https://wa.me/?text={share_text}%20{share_url}" target="_blank" rel="noopener" aria-label="Share on WhatsApp">WhatsApp</a>
        <a href="https://t.me/share/url?url={share_url}&text={share_text}" target="_blank" rel="noopener" aria-label="Share on Telegram">Telegram</a>
        <a href="mailto:?subject={share_text}&body={share_url}" aria-label="Share via email">Email</a>
        <button type="button" onclick="navigator.clipboard&&navigator.clipboard.writeText('{site_url}').then(()=>{{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy link',1500)}})\">Copy link</button>
    </div>
</main>
<footer><p>&copy; 2026 {site_name}.</p>
<div class="cols"><a href="/about">About</a><a href="/privacy">Privacy</a><a href="/sitemap.xml">Sitemap</a><a href="/rss.xml">RSS</a><a href="https://www.sca.coffee" target="_blank" rel="noopener">Specialty Coffee Association</a></div>
</footer>
</body>
</html>"""

SITEMAP_TEMPLATE = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>'

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULTS = {
    "site_name": os.getenv("SITE_NAME", "The Slow Drip"),
    "site_url": os.getenv("SITE_URL", "https://myblog.pages.dev"),
    "author": os.getenv("SITE_AUTHOR", "Anonymous"),
    "description": os.getenv("SITE_DESCRIPTION", "A blog about coffee, brewing, and the perfect cup."),
    "lang": os.getenv("SITE_LANG", "en"),
    "dist_dir": "../public",  # at repo root — Cloudflare Pages serves from here
    "content_dir": "content",
}


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
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
    tags_list = [t.strip() for t in (tags or fm.get("tags", "")).split(",") if t.strip()]
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

    html_body = markdown2.markdown(
        body, extras=["fenced-code-blocks", "tables", "strike", "task_list", "header-ids"]
    )
    wc = count_words(body)

    og_img = f'<meta property="og:image" content="{_social_image(image)}">' if image else ""
    tw_img = f'<meta name="twitter:image" content="{_social_image(image)}">' if image else ""
    tags_html = "".join(f"<span>{t}</span>" for t in tags_list)

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
        lang=DEFAULTS["lang"],
        title=f"{title} — {DEFAULTS['site_name']}",
        description=description,
        author=author,
        site_name=DEFAULTS["site_name"],
        canonical_url=canonical,
        share_url=quote(canonical, safe=""),
        share_text=quote(title, safe=""),
        published_time=iso,
        iso_date=iso,
        display_date=display,
        word_count=wc,
        tags_html=tags_html,
        og_image=og_img,
        twitter_image=tw_img,
        og_locale=DEFAULTS["lang"].replace("-", "_"),
        ld_json=json.dumps(ld, ensure_ascii=False),
        content_html=html_body,
    )

    return slug, html, {
        "title": title, "slug": slug, "description": description,
        "tags": tags_list, "author": author, "image": image,
        "date": iso, "word_count": wc,
    }


# ---------------------------------------------------------------------------
# Site-level files
# ---------------------------------------------------------------------------
def build_index(posts_meta: list[dict]) -> str:
    items = []
    for p in posts_meta:
        img = p.get("image") or ""
        if img:
            alt = p["title"].replace('"', "&quot;")
            thumb = f'<img class="thumb" src="{img}" alt="{alt}" loading="lazy">'
        else:
            thumb = '<div class="thumb placeholder">No image</div>'
        items.append(
            f'<li>{thumb}<div class="post-body">'
            f'<a href="/{p["slug"]}">{p["title"]}</a>'
            f'<div class="desc">{p["description"]}</div>'
            f'<div class="meta">{p["date"][:10]}</div></div></li>'
        )
    from urllib.parse import quote
    return INDEX_TEMPLATE.format(
        lang=DEFAULTS["lang"], site_name=DEFAULTS["site_name"],
        title=f"{DEFAULTS['site_name']} — Latest Posts & Articles on Coffee, Brewing & Home Barista Tips",
        site_url=DEFAULTS["site_url"],
        description=DEFAULTS["description"],
        share_url=quote(DEFAULTS["site_url"], safe=""),
        share_text=quote(DEFAULTS["site_name"]),
        post_items="\n".join(items) if items else "<li>No posts yet.</li>",
    )


def build_sitemap(posts_meta: list[dict]) -> str:
    entries = [f"  <url><loc>{DEFAULTS['site_url']}/</loc><changefreq>daily</changefreq></url>"]
    for p in posts_meta:
        entries.append(
            f'  <url><loc>{DEFAULTS["site_url"]}/{p["slug"]}</loc>'
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
            f"      <guid isPermaLink=\"true\">{site_url}/{p['slug']}</guid>\n"
            f"      <pubDate>{_rss_date(p['date'])}</pubDate>\n"
            f"      <description>{escape(p['description'])}</description>\n"
            + (f"      <enclosure url=\"{escape(p['image'])}\" type=\"image/jpeg\"/>\n" if p.get("image") else "")
            + "    </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>\n"
        f"  <title>{escape(site)}</title>\n"
        f"  <link>{site_url}</link>\n"
        f"  <description>{escape(desc)}</description>\n"
        f"  <atom:link href=\"{site_url}/rss.xml\" rel=\"self\" type=\"application/rss+xml\"/>\n"
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


def build_site(dist: Path, posts_meta: list[dict], new_slug: str, new_html: str) -> None:
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
    """Upload public/ to Cloudflare Pages via wrangler CLI. No git needed."""
    import shutil
    if not shutil.which("wrangler"):
        print("⚠️  wrangler not found. Skipping deploy.")
        return
    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
    subprocess.run(
        ["wrangler", "pages", "deploy", str(dist.resolve()),
         "--project-name", project, "--branch", "main", "--commit-dirty", "true"],
        check=False,
    )
    print(f"🌍 Live: {DEFAULTS['site_url']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Publish markdown → static site → GitHub push")
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

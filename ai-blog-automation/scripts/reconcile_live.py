#!/usr/bin/env python3
"""Reconcile local content/*.md against the live dripper.top site.

The live site is the single source of truth for what is deployed (Direct
Upload / Cloudflare Pages API — git push does NOT auto-deploy). This script
diffs the local ``content/*.md`` pages against the live sitemap and pushes any
content page that is missing from the live site.

Usage::

    python scripts/reconcile_live.py                      # dry-run: report diff only
    python scripts/reconcile_live.py --apply              # rebuild + Direct Upload (push missing)
    python scripts/reconcile_live.py --import-live-only   # save live-only pages as content/*.md
    python scripts/reconcile_live.py --apply --import-live-only  # preserve live-only, then deploy
    python scripts/reconcile_live.py --sync               # DB = source of truth: rewrite every
                                                          #   PUBLISHED article's content/*.md
                                                          #   from the DB (prevents local-stale
                                                          #   rebuilds reverting dashboard edits)
    python scripts/reconcile_live.py --sync --dry-run     # report without writing
    python scripts/reconcile_live.py --sync --apply       # sync + rebuild + deploy

Note on live-only pages: a full rebuild from ``content/`` builds pages ONLY
from ``content/*.md``. A page that is live but has no local ``content/<slug>.md``
(added via the dashboard API) would be silently DROPPED by the next deploy.
``--import-live-only`` fetches those pages and writes them back into
``content/`` so they survive rebuilds.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

import blog_automation.config  # noqa: F401  (loads .env)

from blog_automation.pipelines.phase_8_publish.publishing import (  # noqa: E402
    _CONTENT_DIR,
    _REPO_ROOT,
)

CONTENT_DIR = _REPO_ROOT / "ai-blog-automation" / _CONTENT_DIR

SITE_URL = os.environ.get("SITE_URL", "https://side-blogs.pages.dev").rstrip("/")

# Known bug artifacts (real article accidentally saved under a bogus slug) that
# should NOT be auto-pushed as their own URL until manually renamed/removed.
_ARTIFACT_SLUGS = {"x"}


def fetch_live_slugs() -> list[str]:
    """Return the set of post slugs currently live, from the sitemap."""
    import requests

    r = requests.get(f"{SITE_URL}/sitemap.xml", timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    slugs = []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in root.findall(".//s:loc", ns):
        url = (loc.text or "").strip()
        if url == f"{SITE_URL}/" or url == f"{SITE_URL}":
            continue
        # slugs in the sitemap carry a trailing slash (article pages only serve
        # at /slug/ on Cloudflare Pages) — strip it to compare with file stems
        slug = url.replace(f"{SITE_URL}/", "").rstrip("/")
        if slug:
            slugs.append(slug)
    return sorted(set(slugs))


def load_content_slugs() -> list[str]:
    return sorted(p.stem for p in CONTENT_DIR.glob("*.md"))


def import_live_only(slugs: list[str]) -> list[str]:
    """Export live-only pages from the DB into content/<slug>.md (lossless).

    The dashboard/API and this repo share the same database (DATABASE_URL), so
    the ORIGINAL markdown (``content_draft``) is available — we do not scrape
    rendered HTML. This guarantees the exact published content is preserved.
    """
    from blog_automation.models import Article, get_session

    imported = []
    for slug in slugs:
        out = CONTENT_DIR / f"{slug}.md"
        if out.exists():
            continue
        with get_session() as s:
            a = s.query(Article).filter_by(slug=slug).order_by(Article.id.desc()).first()
            if not a or not (a.content_draft or "").strip():
                print(f"  ⚠️  no content_draft in DB for {slug} — run the "
                      f"HTML-scrape fallback manually")
                continue
            title = a.title or slug
            keyword = a.keyword or ""
            tags = a.tags or ([keyword] if keyword else [])
            image = a.featured_image_url or ""
            published = a.published_date
            date_str = (
                published.strftime("%Y-%m-%d")
                if published
                else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )
        body = a.content_draft.strip()
        fm = f"---\ntitle: {title}\ndate: {date_str}\nslug: {slug}\n"
        if keyword:
            fm += f"keyword: {keyword}\n"
        if tags:
            fm += f"tags: {', '.join(str(t) for t in tags)}\n"
        fm += f"author: Tien Nguyen\n"
        if image:
            fm += f"image: {image}\n"
        fm += "---\n\n"
        out.write_text(fm + body + "\n", encoding="utf-8")
        imported.append(slug)
        print(f"  ✅ exported {slug}.md from DB ({len(body)} chars)")
    return imported


def _frontmatter_from_db(a, body: str, extra_keys: dict) -> str:
    """Build frontmatter with the DB as source of truth, preserving
    local-only keys (description, featured, blocks, ...) the DB has no column
    for, so hand-set flags survive a sync."""
    title = a.title or ""
    keyword = a.keyword or ""
    tags = a.tags or ([keyword] if keyword else [])
    image = a.featured_image_url or ""
    published = a.published_date or a.created_at
    date_str = (
        published.strftime("%Y-%m-%d")
        if published
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    fm = f"---\ntitle: {title}\ndate: {date_str}\nslug: {a.slug}\n"
    if keyword:
        fm += f"keyword: {keyword}\n"
    if tags:
        fm += f"tags: {', '.join(str(t) for t in tags)}\n"
    if extra_keys.get("author"):
        fm += f"author: {extra_keys['author']}\n"
    else:
        fm += "author: Tien Nguyen\n"
    if image:
        fm += f"image: {image}\n"
    for k in ("description", "featured", "blocks"):
        if extra_keys.get(k):
            fm += f"{k}: {extra_keys[k]}\n"
    fm += "---\n\n"
    return fm


def _body_without_frontmatter(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.S)
    return m.group(1).strip() if m else text.strip()


def sync_published(dry_run: bool = False) -> tuple[list[str], list[str]]:
    """DB is the SINGLE SOURCE OF TRUTH: rewrite every content/*.md for
    PUBLISHED articles from the DB row, so a local rebuild can never diverge
    from (or revert) what the dashboard/approve deployed.

    Only status='published' rows are materialized — a pending_review article
    MUST NOT land in content/ (a build would publish it unreviewed).

    Dup guard: legacy DB slugs (e.g. old date-suffixed slugs) that are NOT the
    slug a live article already uses are SKIPPED when the same title already
    has a content file under a different slug — otherwise every sync recreates
    the "2 bài đúp" bug for articles that historically moved to title-slugs.
    Rule per row:
      - content file exists for the DB slug  -> overwrite (DB truth, same URL)
      - no file + no same-title file         -> create (missing article,
                                                e.g. dashboard-approved)
      - no file + same-title file exists     -> skip (legacy slug, log it)
    Local-only frontmatter keys (description, featured, blocks) are preserved.
    Returns (written, unchanged).
    """
    from blog_automation.models import Article, get_session

    def _existing_titles() -> dict[str, str]:
        """map lower title -> slug for all current content files"""
        out: dict[str, str] = {}
        for f in CONTENT_DIR.glob("*.md"):
            m = re.match(r"^---\n(.*?)\n---\n", f.read_text(encoding="utf-8"), re.S)
            if not m:
                continue
            t = None
            for line in m.group(1).splitlines():
                if line.lower().startswith("title:"):
                    t = line.partition(":")[2].strip().lower()
                    break
            if t:
                out.setdefault(t, f.stem)
        return out

    existing_titles = _existing_titles()
    written, unchanged, skipped = [], [], []
    with get_session() as s:
        rows = (
            s.query(Article)
            .filter(Article.status == "published")
            .filter(Article.content_draft.isnot(None))
            .order_by(Article.id)
            .all()
        )
        for a in rows:
            slug = a.slug or ""
            if not slug or slug in _ARTIFACT_SLUGS:
                skipped.append(slug or "?")
                continue
            out = CONTENT_DIR / f"{slug}.md"
            title_key = (a.title or "").strip().lower()
            if not out.exists() and title_key and title_key in existing_titles:
                skipped.append(f"{slug} (dup of {existing_titles[title_key]})")
                continue
            extra: dict = {}
            if out.exists():
                txt = out.read_text(encoding="utf-8")
                m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
                if m:
                    for line in m.group(1).splitlines():
                        key, _, val = line.partition(":")
                        key = key.strip()
                        if key in (
                            "title", "date", "slug", "keyword",
                            "tags", "author", "image",
                        ):
                            continue
                        if val.strip():
                            extra[key] = val.strip()
            body = _body_without_frontmatter(a.content_draft or "")
            if not body:
                skipped.append(slug)
                continue
            new = _frontmatter_from_db(a, body, extra) + body + "\n"
            if out.exists() and out.read_text(encoding="utf-8") == new:
                unchanged.append(slug)
            else:
                if not dry_run:
                    out.write_text(new, encoding="utf-8")
                written.append(slug)
    print(f"  ✅ synced from DB ({len(written)}): {', '.join(written) if written else '-'}")
    if unchanged:
        print(f"  ⏸️  already in sync ({len(unchanged)})")
    if skipped:
        print(f"  🚫 skipped ({len(skipped)}): {', '.join(sorted(skipped))}")
    return written, unchanged


def main():
    import argparse

    p = argparse.ArgumentParser(description="Reconcile content/ vs live dripper.top")
    p.add_argument("--apply", action="store_true", help="Rebuild + Direct Upload (push missing)")
    p.add_argument("--import-live-only", action="store_true",
                   help="Save live-only pages into content/ so rebuilds don't drop them")
    p.add_argument("--sync", action="store_true",
                   help="Rewrite ALL published articles' content/*.md from the DB "
                        "(DB is the single source of truth; undoes local-stale reverts)")
    p.add_argument("--dry-run", action="store_true",
                   help="With --sync: report what would change without writing")
    args = p.parse_args()

    print(f"🌐 Live site: {SITE_URL}\n")
    live = set(fetch_live_slugs())
    content = set(load_content_slugs())

    to_push = content - live - _ARTIFACT_SLUGS
    already_live = content & live
    live_only = live - content
    artifacts = content & _ARTIFACT_SLUGS

    print(f"content/: {len(content)}   live: {len(live)}")
    print(f"\n✅ Already live ({len(already_live)}): ignored")
    for s in sorted(already_live):
        print(f"   - {s}")

    print(f"\n🟡 In content/ but NOT live — would push ({len(to_push)}):")
    for s in sorted(to_push):
        print(f"   + {s}")

    if artifacts:
        print(f"\n🚫 Artifact slugs skipped from auto-push ({sorted(artifacts)}): "
              f"rename/remove manually (looks like a bug slug, e.g. 'x.md')")

    print(f"\n🔴 Live but NO local content/*.md — would be DROPPED by next full "
          f"rebuild ({len(live_only)}):")
    for s in sorted(live_only):
        print(f"   ! {s}")
    if live_only:
        print("   → run with --import-live-only to save them into content/ first.")

    if not (args.apply or args.import_live_only or args.sync):
        print("\n(dry-run — pass --apply to deploy, --import-live-only to save live-only pages, or --sync to sync from DB)")
        return

    if args.import_live_only and live_only:
        print("\n⬇️  Importing live-only pages into content/…")
        import_live_only(sorted(live_only))

    if args.sync:
        print("\n🔄 Syncing published articles from the DB (DB = source of truth)…")
        sync_published(dry_run=args.dry_run)

    if not args.apply:
        return

    # Rebuild the full site from content/ (now includes imported live-only pages)
    # and deploy the rebuilt public/ to Cloudflare via Direct Upload.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import publish_cf

    print("\n🏗️  Building static site from content/…")
    publish_cf.build_site()
    print("📤 Direct Upload to Cloudflare Pages…")
    publish_cf.upload()
    print("✅ Done")


if __name__ == "__main__":
    main()

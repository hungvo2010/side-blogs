#!/usr/bin/env python3
"""One-time migration: make the DB's published set match the live site.

The site's canonical articles currently live in ``content/*.md`` (their file
stem / frontmatter ``slug`` is the live URL). The DB also holds older rows for
the same articles under legacy dated slugs, plus a few published-but-never-live
duplicates. That mismatch is why a DB-only build would drop live pages and add
stale ones.

What this does, per committed ``content/*.md`` (excluding the ``x`` artifact):

  * find the DB row for the same article — by canonical slug first, else by
    normalized title among published rows — and rewrite it in place: canonical
    slug, body, title, keyword, tags, image, description, date, featured;
  * create the row if none matches.

Then it archives (status -> ``archived``) every remaining ``published`` row
whose slug is neither canonical nor currently live. DB-only live pages (e.g. a
post published straight from the Review Queue) are preserved.

Usage::

    python scripts/db_migrate_canonical.py            # dry-run: print the plan
    python scripts/db_migrate_canonical.py --apply    # execute
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

import blog_automation.config  # noqa: F401,E402  (loads .env)

from blog_automation.models import Article, init_db  # noqa: E402
from blog_automation.models.base import create_session  # noqa: E402

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
ARTIFACT_SLUGS = {"x"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    body = text.strip()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"').strip("'")
        body = m.group(2).strip()
    return meta, body


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _tags(raw: str) -> list[str] | None:
    """Parse a frontmatter tags value, or None if it is char-split garbage.

    Some older exports wrote `[vietnamese coffee, ...]` as a string joined
    char-by-char (``tags: [, v, i, e, ...]``). Detect that and let the caller
    fall back to the DB row's already-correct tags.
    """
    parts = [t.strip() for t in (raw or "").split(",")]
    if parts and sum(1 for t in parts if len(t) <= 1) > len(parts) * 0.5:
        return None
    return [t for t in parts if t]


def _true(raw: str) -> bool:
    return str(raw).strip().lower() in ("1", "true", "yes", "y")


def _date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def load_canonical() -> list[dict]:
    articles: list[dict] = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.stem in ARTIFACT_SLUGS:
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        slug = meta.get("slug") or path.stem
        if slug in ARTIFACT_SLUGS:
            continue
        articles.append(
            {
                "slug": slug,
                "title": meta.get("title") or path.stem,
                "keyword": meta.get("keyword", ""),
                "description": meta.get("description", ""),
                "tags": _tags(meta.get("tags", "")),
                "image": meta.get("image", ""),
                "date": _date(meta.get("date")),
                "featured": _true(meta.get("featured", "")),
                "body": body,
            }
        )
    return articles


def fetch_live_slugs(site_url: str) -> set[str]:
    import requests

    r = requests.get(f"{site_url}/sitemap.xml", timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    slugs: set[str] = set()
    for loc in root.findall(".//s:loc", ns):
        url = (loc.text or "").strip()
        if url in (f"{site_url}/", site_url):
            continue
        slugs.add(url.replace(f"{site_url}/", "").rstrip("/"))
    return slugs


def _free_slug(session, row, conflict, taken: set[str]) -> None:
    """Rename an archived conflicting row so ``row`` can take its slug."""
    base = f"{conflict.slug}-dup-{conflict.id}"
    candidate = base
    n = 1
    while candidate in taken or session.query(Article).filter_by(slug=candidate).first():
        n += 1
        candidate = f"{base}-{n}"
    conflict.slug = candidate
    conflict.status = "archived"
    taken.add(candidate)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="execute (default: dry-run)")
    ap.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://dripper.top"),
        help="site whose sitemap defines what is currently live",
    )
    args = ap.parse_args()

    init_db()

    canonical = load_canonical()
    canon_slugs = {c["slug"] for c in canonical}
    live = fetch_live_slugs(args.site_url.rstrip("/"))

    print(f"canonical content files : {len(canonical)}")
    print(f"live sitemap slugs      : {len(live)}")
    print(f"live URLs with no canonical file: "
          f"{sorted(live - canon_slugs)}")
    print(f"canonical files not currently live: "
          f"{sorted(canon_slugs - live)}")
    print()

    s = create_session()
    try:
        all_rows = s.query(Article).all()
        by_slug: dict[str, Article] = {}
        for a in all_rows:
            by_slug.setdefault(a.slug, a)
        taken = set(by_slug)

        plan: list[str] = []
        touched: set[int] = set()

        for c in canonical:
            row = by_slug.get(c["slug"])
            action = "UPDATE"
            if row is None:
                candidates = [
                    a
                    for a in all_rows
                    if a.status == "published"
                    and _norm(a.title) == _norm(c["title"])
                    and (a.id or -1) not in touched
                ]
                candidates.sort(key=lambda a: a.id or 0)
                if candidates:
                    row = candidates[0]
                    action = f"RENAME {row.slug} -> {c['slug']}"
                else:
                    row = Article(
                        slug=c["slug"],
                        title=c["title"],
                        keyword=c["keyword"] or c["title"],
                        status="published",
                    )
                    s.add(row)
                    by_slug[c["slug"]] = row
                    taken.add(c["slug"])
                    action = "CREATE"

            if row.slug != c["slug"]:
                conflict = by_slug.get(c["slug"])
                if conflict is not None and conflict is not row:
                    plan.append(f"  archive conflicting slug {conflict.slug!r}")
                    _free_slug(s, row, conflict, taken)
                row.slug = c["slug"]
                by_slug[c["slug"]] = row

            row.title = c["title"][:255]
            row.keyword = (c["keyword"] or c["title"])[:255]
            row.content_draft = c["body"]
            row.meta_description = (c["description"] or "")[:170] or None
            # None means the file's tags were char-split garbage -> keep the
            # DB row's good tags (or fall back to the keyword for new rows).
            if c["tags"] is not None:
                row.tags = c["tags"] or row.tags
            elif not row.id:
                row.tags = [c["keyword"]] if c["keyword"] else None
            row.featured_image_url = (c["image"] or "")[:500] or None
            row.featured = c["featured"]
            row.status = "published"
            if c["date"]:
                row.published_date = c["date"]
            if row.id:
                touched.add(row.id)
            plan.append(f"  {action}: {c['slug']} ({len(c['body'])} chars)")

        # Archive leftover published rows that are neither canonical nor live.
        for a in all_rows:
            if a.status != "published":
                continue
            if a.slug in canon_slugs or a.slug in live:
                continue
            if (a.id or -1) in touched:
                continue
            a.status = "archived"
            plan.append(f"  ARCHIVE: {a.slug}")

        print("\n".join(plan))
        print(f"\nplan: {len(canonical)} canonical, "
              f"{len([p for p in plan if 'ARCHIVE' in p or 'archive' in p])} archived")

        if args.apply:
            s.commit()
            print("\n✅ applied.")
        else:
            s.rollback()
            print("\n(dry-run — pass --apply to execute)")
    finally:
        s.close()


if __name__ == "__main__":
    main()

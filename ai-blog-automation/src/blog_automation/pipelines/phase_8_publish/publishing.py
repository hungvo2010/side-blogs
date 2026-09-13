"""Cloudflare Pages publishing pipeline — no DB, no WordPress.

Takes article content (from any source — pipeline, manual, AI) and publishes
it as a static HTML page on Cloudflare Pages via the repo's ``public/`` dir.

Flow::

    content dict  →  markdown file  →  static HTML  →  git push  →  live
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from blog_automation.logging_config import get_logger

logger = get_logger(__name__)

# Repo-relative paths (from ai-blog-automation/)
_CONTENT_DIR = Path("content")
_DIST_DIR = Path("../public")  # at repo root — served by Cloudflare Pages
# publishing.py → phase_8_publish/ → pipelines/ → blog_automation/ → src/ → ai-blog-automation/ → side-blogs/
_REPO_ROOT = Path(__file__).resolve().parents[5]  # side-blogs/

# Bug-artifact slugs that must never become their own page.
_ARTIFACT_SLUGS = {"x"}

# Non-article static assets kept in the committed public/ checkout. These are
# read-only: the DB-driven build overlays the dynamic pages on top of them.
_STATIC_ROOT_FILES = ("favicon.svg", "_redirects", "apple-touch-icon.png")
_STATIC_DIRS = ("about", "privacy")


def delete_article_and_redeploy(slug: str) -> dict[str, Any]:
    """Rebuild the whole site from the DB and redeploy.

    The site is built purely from ``status='published'`` rows, so the caller
    MUST delete the row or move it off ``published`` first — then this drops
    the article's page and refreshes the homepage/sitemap. Works on hosts with
    no durable disk (Streamlit Cloud) because nothing is written to disk.

    Returns dict with ``slug`` and ``deploy_method``/``pushed``.
    """
    files = build_site_files_from_db()
    method, pushed = _deploy_to_cloudflare(files, title=slug)
    return {"slug": slug, "deploy_method": method, "pushed": pushed}


def publish_article(
    *,
    title: str,
    content: str,
    keyword: str = "",
    description: str = "",
    slug: str | None = None,
    tags: list[str] | None = None,
    author: str | None = None,
    image: str | None = None,
    auto_push: bool = True,
) -> dict[str, Any]:
    """Publish a single article to Cloudflare Pages.

    The whole site is rebuilt from the DB's published rows (plus this article,
    which may not be saved in the DB yet) and deployed via the Cloudflare Direct
    Upload API. Nothing is written to disk, so this works on Streamlit Cloud.

    Args:
        title: Article title (H1)
        content: Article body in **markdown**
        keyword: Primary keyword (for SEO meta)
        description: Meta description (auto-generated if empty)
        slug: URL slug (auto-generated from title if empty)
        tags: List of tags
        author: Author name
        image: OG image URL
        auto_push: If True, build + deploy to Cloudflare Pages

    Returns:
        Dict with ``slug``, ``url``, ``pushed`` and ``deploy_method``.
    """
    import re

    # ── Slug ──
    if not slug:
        slug = re.sub(r"[^\w\s-]", "", title.lower().strip())
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = slug.strip("-")[:80]
    if not slug:
        slug = "untitled"

    # ── Description ──
    if not description:
        # Pick first non-heading, non-image paragraph
        for line in content.split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and not re.match(
                r"!\[[^\]]*\]\([^)]*\)\s*$", s
            ):
                plain = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", s)
                plain = re.sub(r"[*_`]", "", plain)
                if len(plain) > 10:
                    description = plain[:157] + "…"
                    break
    if not description:
        description = title

    article = {
        "slug": slug,
        "title": title,
        "keyword": keyword,
        "description": description,
        "tags": tags or [],
        "author": author,
        "image": image or "",
        "featured": False,
        "date": None,
        "body": content,
    }

    # Rebuild from the DB's published rows + this (possibly unsaved) article.
    files = build_site_files_from_db(extra_articles=[article])

    site_url = os.environ.get("SITE_URL", "https://dripper.top")

    pushed = False
    deploy_method = "none"
    if auto_push:
        deploy_method, pushed = _deploy_to_cloudflare(files, title)

    return {
        "slug": slug,
        "url": f"{site_url}/{slug}",
        "pushed": pushed,
        "deploy_method": deploy_method,
        "title": title,
    }


def _load_publish_module():
    """Import scripts/publish.py in-process to reuse its templates/builders."""
    import importlib.util

    publish_script = _REPO_ROOT / "ai-blog-automation" / "scripts" / "publish.py"
    spec = importlib.util.spec_from_file_location("sideblog_publish", str(publish_script))
    pub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pub)
    pub.DEFAULTS.update(
        {
            "site_url": os.environ.get(
                "SITE_URL", pub.DEFAULTS.get("site_url", "https://dripper.top")
            ),
            "site_name": os.environ.get(
                "SITE_NAME", pub.DEFAULTS.get("site_name", "The Slow Drip")
            ),
        }
    )
    return pub


def _article_markdown(article: dict) -> str:
    """Render one article dict to frontmatter + body markdown (in memory)."""

    def _one_line(value: Any) -> str:
        return " ".join(str(value or "").split())

    title = _one_line(article.get("title")) or _one_line(article.get("keyword"))
    slug = article.get("slug") or ""
    date = article.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    fm = f"---\ntitle: {title or 'Untitled'}\ndate: {date}\nslug: {slug}\n"
    if article.get("description"):
        fm += f"description: {_one_line(article['description'])}\n"
    if article.get("keyword"):
        fm += f"keyword: {_one_line(article['keyword'])}\n"
    tags = [_one_line(t) for t in (article.get("tags") or []) if _one_line(t)]
    if tags:
        fm += f"tags: {', '.join(tags)}\n"
    fm += f"author: {_one_line(article.get('author')) or 'Tien Nguyen'}\n"
    if article.get("image"):
        fm += f"image: {_one_line(article['image'])}\n"
    if article.get("featured"):
        fm += "featured: true\n"
    fm += "---\n\n"
    return fm + (article.get("body") or "")


def _db_article_dict(a) -> dict:
    """Normalize an Article row into the dict ``_article_markdown`` expects."""
    published = a.published_date or a.created_at
    return {
        "slug": a.slug,
        "title": a.title,
        "keyword": a.keyword,
        "description": a.meta_description or "",
        "tags": a.tags or ([a.keyword] if a.keyword else []),
        "author": None,
        "image": a.featured_image_url or "",
        "featured": bool(a.featured),
        "date": published.strftime("%Y-%m-%d") if published else None,
        "body": a.content_draft or "",
    }


def _static_site_files() -> dict[str, bytes]:
    """Read the committed non-article static assets (read-only, no writes)."""
    public = _REPO_ROOT / "public"
    files: dict[str, bytes] = {}
    for name in _STATIC_ROOT_FILES:
        path = public / name
        if path.exists():
            files[f"/{name}"] = path.read_bytes()
    for dirname in _STATIC_DIRS:
        base = public / dirname
        if not base.exists():
            continue
        for root, _dirs, fnames in os.walk(base):
            for fname in fnames:
                full = Path(root) / fname
                rel = full.relative_to(public).as_posix()
                files[f"/{rel}"] = full.read_bytes()
    return files


def build_site_files_from_db(
    extra_articles: list[dict] | None = None,
) -> dict[str, bytes]:
    """Build the ENTIRE static site in memory from the DB (source of truth).

    Article pages come from ``Article`` rows with ``status='published'`` plus
    any ``extra_articles`` supplied by the caller (used for the article being
    approved, which is still ``pending_review`` at build time). Non-article
    static assets are read read-only from the committed ``public/`` checkout.
    Nothing is written to disk, so this is safe on diskless hosts.

    Returns a ``{"/path": bytes}`` map ready for the Cloudflare Direct Upload.
    """
    import json

    from blog_automation.models import Article, get_session

    pub = _load_publish_module()

    marks: dict[str, str] = {}
    with get_session() as session:
        rows = (
            session.query(Article)
            .filter(Article.status == "published")
            .filter(Article.content_draft.isnot(None))
            .order_by(Article.id)
            .all()
        )
        for a in rows:
            if not a.slug or a.slug in _ARTIFACT_SLUGS:
                continue
            if not (a.content_draft or "").strip():
                continue
            marks[a.slug] = _article_markdown(_db_article_dict(a))

    # Extra articles override same-slug DB rows (e.g. a fresh re-draft).
    for art in extra_articles or []:
        slug = art.get("slug")
        if slug and (art.get("body") or "").strip():
            marks[slug] = _article_markdown(art)

    known = set(marks)
    posts_meta: list[dict] = []
    post_htmls: dict[str, str] = {}
    for md_text in marks.values():
        slug, html, meta = pub.build_article_from_text(md_text, known_slugs=known)
        posts_meta.append(meta)
        post_htmls[slug] = html

    posts_meta.sort(key=lambda m: m["date"], reverse=True)

    files = _static_site_files()
    files["/index.html"] = pub.build_index(posts_meta).encode("utf-8")
    files["/sitemap.xml"] = pub.build_sitemap(posts_meta).encode("utf-8")
    files["/rss.xml"] = pub.build_rss(posts_meta).encode("utf-8")
    files["/robots.txt"] = (
        f"User-agent: *\nAllow: /\n\nSitemap: {pub.DEFAULTS['site_url']}/sitemap.xml\n"
    ).encode("utf-8")
    files["/posts.json"] = json.dumps(
        posts_meta, ensure_ascii=False, indent=2
    ).encode("utf-8")
    for slug, html in post_htmls.items():
        files[f"/{slug}/index.html"] = html.encode("utf-8")

    logger.info(
        "Built site from DB (in-memory)", posts=len(posts_meta), files=len(files)
    )
    return files


def _deploy_to_cloudflare(files: dict[str, bytes], title: str) -> tuple[str, bool]:
    """Deploy a built site to Cloudflare Pages using the best available method.

    Order of preference:
      1. Cloudflare Pages Direct Upload API (needs CLOUDFLARE_API_TOKEN +
         CLOUDFLARE_ACCOUNT_ID) — pure requests, works on Streamlit Cloud.
      2. wrangler CLI (on PATH, or via ``npx wrangler``) — needs ``wrangler login``.
      3. git push fallback — only stores source; may not trigger a Pages deploy.

    Returns (method, pushed).
    """
    import shutil

    # 1. Cloudflare Pages API (most reliable — no interactive auth, no CLI)
    if os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        try:
            return "cloudflare_api", _deploy_cloudflare_api(files)
        except Exception as e:
            logger.warning("Cloudflare API deploy failed, falling back", error=str(e)[:300])

    # 2. wrangler CLI (on PATH or via npx) — public/ was written to disk
    wrangler_cmd = None
    if shutil.which("wrangler"):
        wrangler_cmd = ["wrangler"]
    elif shutil.which("npx"):
        wrangler_cmd = ["npx", "--yes", "wrangler"]
    if wrangler_cmd is not None:
        dist = _REPO_ROOT / "public"
        if dist.exists() and any(dist.iterdir()):
            project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
            result = subprocess.run(
                [
                    *wrangler_cmd, "pages", "deploy", str(dist),
                    "--project-name", project,
                    "--branch", "main",
                    "--commit-dirty", "true",
                ],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                logger.info("Deployed to Cloudflare Pages via wrangler", project=project)
                return "wrangler", True
            logger.warning(
                "wrangler deploy failed, falling back to git push",
                stderr=result.stderr[:300],
            )
        else:
            logger.warning("public/ dir empty, nothing to deploy")
    else:
        logger.warning("wrangler CLI not found, falling back to git push")

    # 3. git push fallback (won't work on Streamlit Cloud — no git credentials)
    try:
        return "git_push", _deploy_git_push(title)
    except Exception as e:
        logger.warning("git push fallback failed", error=str(e)[:200])
        return "git_push", False


def _deploy_cloudflare_api(files: dict[str, bytes]) -> bool:
    """Upload a built site straight to Cloudflare Pages via Direct Upload API.

    Pure ``requests`` — no wrangler, no git, no disk dependency. Replicates the
    ``wrangler pages deploy`` upload flow:

      1. GET  /accounts/{account}/pages/projects/{project}/upload-token  → JWT
      2. POST /pages/assets/check-missing                                → hashes to upload
      3. POST /pages/assets/upload                                       → upload files (base64)
      4. POST /pages/assets/upsert-hashes                                → register hashes
      5. POST /accounts/{account}/pages/projects/{project}/deployments   → create deployment

    Requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID env vars.
    """
    import base64

    import blake3
    import requests

    token = os.environ["CLOUDFLARE_API_TOKEN"]
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")

    if not files:
        raise RuntimeError("No files to deploy")

    api = "https://api.cloudflare.com/client/v4"
    project_url = f"{api}/accounts/{account_id}/pages/projects/{project}"
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload JWT
    r = requests.get(f"{project_url}/upload-token", headers=headers, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare upload-token failed: {r.status_code} {r.text[:200]}")
    jwt = r.json()["result"]["jwt"]
    upload_headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    # Build manifest (path -> blake3 hash) + upload payload (base64).
    # The hash is blake3(base64(content) + file_extension), hex, 32 chars —
    # this is what wrangler computes and what the Pages asset store keys on.
    manifest: dict[str, str] = {}
    payload: list[dict] = []
    for path, data in sorted(files.items()):
        ext = Path(path).suffix[1:]  # extension without the dot ('' if none)
        h = blake3.blake3((base64.b64encode(data).decode() + ext).encode()).hexdigest()[:32]
        manifest[path] = h
        payload.append(
            {
                "key": h,
                "value": base64.b64encode(data).decode(),
                "metadata": {"contentType": _guess_content_type(path)},
                "base64": True,
            }
        )

    # 2. Only upload hashes Cloudflare doesn't already have
    try:
        r = requests.post(
            f"{api}/pages/assets/check-missing",
            headers=upload_headers,
            json={"hashes": list(manifest.values())},
            timeout=60,
        )
        r.raise_for_status()
        missing = set(r.json().get("result") or [])
    except Exception:
        missing = set()

    to_upload = [p for p in payload if p["key"] in missing] or payload

    # 3. Upload files
    r = requests.post(
        f"{api}/pages/assets/upload",
        headers=upload_headers,
        data=json.dumps(to_upload),
        timeout=300,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare upload failed: {r.status_code} {r.text[:300]}")
    result = r.json()
    if not result.get("success") or result.get("result", {}).get("unsuccessful_keys"):
        raise RuntimeError(f"Cloudflare upload reported errors: {r.text[:300]}")

    # 4. Register hashes
    try:
        requests.post(
            f"{api}/pages/assets/upsert-hashes",
            headers=upload_headers,
            json={"hashes": list(manifest.values())},
            timeout=60,
        )
    except Exception:
        pass

    # 5. Create deployment (multipart form-data, like wrangler)
    r = requests.post(
        f"{project_url}/deployments",
        headers=headers,
        files={
            "branch": (None, "main"),
            "manifest": (None, json.dumps(manifest), "application/json"),
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare deploy failed: {r.status_code} {r.text[:300]}")

    logger.info(
        "Deployed to Cloudflare Pages via API", project=project, files=len(files)
    )
    return True


def _guess_content_type(path: str) -> str:
    """Best-effort MIME guess for a public/-relative path."""
    suffix = Path(path).suffix.lower()
    return {
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".xml": "application/xml",
        ".txt": "text/plain",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".map": "application/json",
    }.get(suffix, "application/octet-stream")


def _deploy_git_push(title: str) -> bool:
    """Fallback: git push to trigger Cloudflare Pages build."""
    subprocess.run(
        ["git", "add", "public/", "ai-blog-automation/content/"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    )
    r = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=_REPO_ROOT,
        capture_output=True,
    )
    if r.returncode == 0:
        logger.info("No changes to push")
        return False

    subprocess.run(
        ["git", "commit", "-m", f"Publish: {title}"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    )
    logger.info("Pushed to git")
    return True

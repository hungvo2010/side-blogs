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

    This is the one-stop function — give it content, it handles everything
    from markdown generation to git push.

    Args:
        title: Article title (H1)
        content: Article body in **markdown**
        keyword: Primary keyword (for SEO meta)
        description: Meta description (auto-generated if empty)
        slug: URL slug (auto-generated from title if empty)
        tags: List of tags
        author: Author name
        image: OG image URL
        auto_push: If True, commit + push to git (Cloudflare auto-deploys)

    Returns:
        Dict with ``slug``, ``url``, ``html_path``, ``pushed``
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

    tags = tags or []
    author = author or "Tien Nguyen"

    # ── Build frontmatter markdown ──
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fm = f"---\ntitle: {title}\ndate: {now}\n"
    # Pin the slug in frontmatter so build_article produces the SAME URL
    # (otherwise it derives slugify(title), which keeps Vietnamese diacritics
    # and silently creates a second URL for the same article)
    fm += f"slug: {slug}\n"
    if description:
        fm += f"description: {description}\n"
    if keyword:
        fm += f"keyword: {keyword}\n"
    if tags:
        fm += f"tags: {', '.join(tags)}\n"
    if author:
        fm += f"author: {author}\n"
    if image:
        fm += f"image: {image}\n"
    fm += "---\n\n"

    md_content = fm + content

    # ── Write markdown to content/ ──
    content_dir = _REPO_ROOT / "ai-blog-automation" / _CONTENT_DIR
    content_dir.mkdir(parents=True, exist_ok=True)
    md_path = content_dir / f"{slug}.md"
    md_path.write_text(md_content, encoding="utf-8")

    logger.info("Markdown written", path=str(md_path))

    # ── Build the full static site in-process (no subprocess — works on
    #    Streamlit Cloud where there is no venv / npx / git) ──
    files = _build_site_files(slug=slug, md_content=md_content)

    site_url = os.environ.get("SITE_URL", "https://side-blogs.pages.dev")

    # ── Deploy: Cloudflare Pages API → wrangler → git push ──
    pushed = False
    deploy_method = "none"
    if auto_push:
        deploy_method, pushed = _deploy_to_cloudflare(files, title)

    # ── Determine live URL ──
    live_url = f"{site_url}/{slug}"

    return {
        "slug": slug,
        "url": live_url,
        "html_path": str(_DIST_DIR / slug / "index.html"),
        "md_path": str(md_path),
        "pushed": pushed,
        "deploy_method": deploy_method,
        "title": title,
    }


def _build_site_files(*, slug: str, md_content: str) -> dict[str, bytes]:
    """Build the complete static site in-process and return {path: bytes}.

    Renders the new article plus every existing post in ``content/`` using the
    same templates as ``scripts/publish.py`` (imported in-process — no
    subprocess). Also writes the outputs to ``content/`` and ``public/`` on
    disk so the repo and the git/wrangler fallback paths stay consistent.

    Returns a map of ``public/``-relative path → file bytes, ready for a
    Cloudflare Pages Direct Upload.
    """
    import importlib.util
    import json

    content_dir = _REPO_ROOT / "ai-blog-automation" / _CONTENT_DIR
    dist = _REPO_ROOT / "public"
    content_dir.mkdir(parents=True, exist_ok=True)
    dist.mkdir(parents=True, exist_ok=True)

    (content_dir / f"{slug}.md").write_text(md_content, encoding="utf-8")

    # Import scripts/publish.py in-process so we reuse the exact templates.
    publish_script = _REPO_ROOT / "ai-blog-automation" / "scripts" / "publish.py"
    spec = importlib.util.spec_from_file_location("sideblog_publish", str(publish_script))
    pub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pub)
    pub.DEFAULTS.update(
        {
            "site_url": os.environ.get(
                "SITE_URL", pub.DEFAULTS.get("site_url", "https://side-blogs.pages.dev")
            ),
            "site_name": os.environ.get(
                "SITE_NAME", pub.DEFAULTS.get("site_name", "The Slow Drip")
            ),
        }
    )

    posts_meta: list[dict] = []
    all_slugs: set[str] = set()
    post_htmls: dict[str, str] = {}
    for md_file in sorted(content_dir.glob("*.md")):
        s, html, meta = pub.build_article(str(md_file))
        if s in all_slugs:
            continue
        all_slugs.add(s)
        posts_meta.append(meta)
        post_htmls[s] = html

    posts_meta.sort(key=lambda m: m["date"], reverse=True)

    meta_file = dist / "posts.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    meta_file.write_text(json.dumps(posts_meta, ensure_ascii=False, indent=2))

    # Write site-level files + the new article page to public/ on disk.
    pub.build_site(dist, posts_meta, slug, post_htmls.get(slug, ""))
    for s, html in post_htmls.items():
        pd = dist / s
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "index.html").write_text(html, encoding="utf-8")

    logger.info("Built site in-process", posts=len(posts_meta), dist=str(dist))

    # Collect every file under public/ as {relative_path: bytes}.
    # Keys use a leading "/" — Cloudflare Pages manifest keys are absolute
    # paths (files without the slash aren't served).
    files: dict[str, bytes] = {}
    for root, _dirs, fnames in os.walk(dist):
        for fname in fnames:
            full = Path(root) / fname
            rel = str(full.relative_to(dist))
            files["/" + rel] = full.read_bytes()
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

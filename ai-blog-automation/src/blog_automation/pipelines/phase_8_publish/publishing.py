"""Cloudflare Pages publishing pipeline — no DB, no WordPress.

Takes article content (from any source — pipeline, manual, AI) and publishes
it as a static HTML page on Cloudflare Pages via the repo's ``public/`` dir.

Flow::

    content dict  →  markdown file  →  static HTML  →  git push  →  live
"""

from __future__ import annotations

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
# publishing.py -> phase_8_publish/ -> pipelines/ -> blog_automation/ -> src/
#   -> ai-blog-automation/ -> side-blogs/
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
        # Pick first non-heading paragraph
        for line in content.split("\n"):
            s = line.strip()
            if s and not s.startswith("#"):
                plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
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

    # ── Build static site via publish.py ──
    publish_script = _REPO_ROOT / "ai-blog-automation" / "scripts" / "publish.py"
    # Use venv python so markdown2 is available; on Streamlit Cloud there is
    # no .venv — fall back to the running interpreter (which has all deps
    # from requirements.txt).
    venv_python = str(_REPO_ROOT / "ai-blog-automation" / ".venv" / "bin" / "python")
    if not os.path.exists(venv_python):
        import sys as _sys

        venv_python = _sys.executable
    cmd = [venv_python, str(publish_script)]
    if not auto_push:
        cmd.append("--no-push")
    site_url = __import__("os").environ.get("SITE_URL", "https://side-blogs.pages.dev")

    # ── Build + deploy with retry loop ──
    # wrangler deploy can hang/timeout intermittently; retry the whole
    # build+deploy step until it succeeds (POST is already saved to content/).
    max_retries = int(__import__("os").environ.get("PUBLISH_RETRIES", "5"))
    attempt = 0
    result = None
    while attempt < max_retries:
        attempt += 1
        try:
            logger.info("Running publish.py", attempt=attempt, max_retries=max_retries)
            result = subprocess.run(
                cmd,
                cwd=_REPO_ROOT / "ai-blog-automation",
                capture_output=True,
                text=True,
                env={
                    **__import__("os").environ,
                    "PYTHONPATH": str(_REPO_ROOT / "ai-blog-automation" / "src"),
                    "SITE_URL": __import__("os").environ.get(
                        "SITE_URL", "https://side-blogs.pages.dev"
                    ),
                    "SITE_NAME": __import__("os").environ.get(
                        "SITE_NAME", "The Slow Drip"
                    ),
                },
                timeout=300,
            )
            if result.returncode == 0:
                break  # success
            logger.warning(
                "publish.py failed (attempt %s/%s)",
                attempt,
                max_retries,
                stderr=result.stderr[:300],
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "publish.py timed out (attempt %s/%s) — retrying",
                attempt,
                max_retries,
            )
        if attempt < max_retries:
            import time as _time

            _time.sleep(10 * attempt)  # 10s, 20s, 30s... backoff

    if result is None or result.returncode != 0:
        # Post is already saved in content/ — surface a clear error instead of
        # silently dropping the article from the build.
        raise RuntimeError(
            f"publish.py failed after {max_retries} attempts — "
            f"markdown saved at {md_path}, deploy not confirmed. "
            f"Last stderr: {(result.stderr[:300] if result else '')}"
        )

    # ── Deploy: Cloudflare Direct Upload (preferred) or Git push ──
    pushed = False
    if auto_push:
        cf_token = __import__("os").environ.get("CLOUDFLARE_API_TOKEN", "")
        if cf_token:
            pushed = _deploy_cloudflare(title)
        else:
            pushed = _deploy_git_push(title)

    # ── Determine live URL ──
    live_url = f"{site_url}/{slug}"

    return {
        "slug": slug,
        "url": live_url,
        "html_path": str(_DIST_DIR / slug / "index.html"),
        "md_path": str(md_path),
        "pushed": pushed,
        "title": title,
    }


def _deploy_cloudflare(title: str) -> bool:
    """Upload public/ to Cloudflare Pages via Direct Upload API (no wrangler needed).

    Falls back to wrangler CLI, then git push, if the API path is unavailable.
    """
    try:
        import tempfile
        import zipfile

        import requests  # noqa: PLC0415
    except ImportError:
        logger.warning("requests not available, falling back to wrangler")
        return _deploy_wrangler(title)

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not (token and acct):
        logger.warning(
            "CLOUDFLARE_API_TOKEN/ACCOUNT_ID missing, falling back to wrangler"
        )
        return _deploy_wrangler(title)

    dist = _REPO_ROOT / "public"
    if not dist.exists() or not list(dist.iterdir()):
        logger.warning("public/ dir empty, nothing to deploy")
        return False

    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
    api_base = f"https://api.cloudflare.com/client/v4/accounts/{acct}/pages/projects"
    headers = {"Authorization": f"Bearer {token}"}

    # Zip public/
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(dist):
                for fname in files:
                    full = Path(root) / fname
                    zf.write(full, full.relative_to(dist))
    finally:
        tmp.close()

    try:
        r = requests.post(
            f"{api_base}/{project}/deployments",
            headers=headers,
            json={"branch": "main"},
            timeout=120,
        )
        r.raise_for_status()
        deployment = r.json()["result"]
        with open(tmp.name, "rb") as f:
            r2 = requests.post(
                deployment["upload_url"],
                headers={"Content-Type": "application/zip"},
                data=f,
                timeout=300,
            )
        if r2.status_code not in (200, 201, 204):
            logger.warning(f"Cloudflare upload failed: {r2.status_code}")
            return False
        logger.info(
            "Deployed to Cloudflare Pages via Direct Upload API",
            project=project,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cloudflare API deploy failed, falling back to wrangler: {e}")
        return _deploy_wrangler(title)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _deploy_wrangler(title: str) -> bool:
    """Upload to Cloudflare Pages via wrangler CLI (fallback)."""
    import shutil

    # Check wrangler is available
    if not shutil.which("wrangler"):
        logger.warning("wrangler CLI not found, falling back to git push")
        return _deploy_git_push(title)

    dist = _REPO_ROOT / "public"
    if not dist.exists() or not list(dist.iterdir()):
        logger.warning("public/ dir empty, nothing to deploy")
        return False

    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
    result = subprocess.run(
        [
            "wrangler",
            "pages",
            "deploy",
            str(dist),
            "--project-name",
            project,
            "--branch",
            "main",
            "--commit-dirty",
            "true",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wrangler deploy failed: {result.stderr[:300]}")

    logger.info("Deployed to Cloudflare Pages via wrangler", project=project)
    return True


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

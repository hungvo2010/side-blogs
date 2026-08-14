"""Cloudflare Pages publishing pipeline — no DB, no WordPress.

Takes article content (from any source — pipeline, manual, AI) and publishes
it as a static HTML page on Cloudflare Pages via the repo's ``public/`` dir.

Flow::

    content dict  →  markdown file  →  static HTML  →  git push  →  live
"""

from __future__ import annotations

import subprocess
import sys
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

# Python interpreter to run scripts/publish.py (needs markdown2).
# Locally the app runs inside ai-blog-automation/.venv, so sys.executable is
# already the venv python. On Streamlit Cloud there is no venv — use the
# current interpreter, which has all requirements.txt packages installed.
def _python_executable() -> str:
    local_venv = _REPO_ROOT / "ai-blog-automation" / ".venv" / "bin" / "python"
    if local_venv.exists() and Path(sys.executable).resolve() != local_venv.resolve():
        return str(local_venv)
    return sys.executable


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
    # publish.py only builds here; deployment is handled below so we have a
    # single, predictable deploy path (Cloudflare API → wrangler → git push).
    publish_script = (
        _REPO_ROOT / "ai-blog-automation" / "scripts" / "publish.py"
    )
    # Use the current interpreter so it also works on Streamlit Cloud (no .venv).
    cmd = [_python_executable(), str(publish_script), "--no-push"]
    site_url = __import__("os").environ.get(
        "SITE_URL", "https://side-blogs.pages.dev"
    )

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
                    "PYTHONPATH": str(
                        _REPO_ROOT / "ai-blog-automation" / "src"
                    ),
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
                attempt, max_retries, stderr=result.stderr[:300],
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "publish.py timed out (attempt %s/%s) — retrying",
                attempt, max_retries,
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

    # ── Deploy: Cloudflare API → wrangler → git push ──
    pushed = False
    deploy_method = "none"
    if auto_push:
        deploy_method, pushed = _deploy_to_cloudflare(title)

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


def _deploy_to_cloudflare(title: str) -> tuple[str, bool]:
    """Deploy public/ to Cloudflare Pages using the best available method.

    Order of preference:
      1. Cloudflare Pages API (needs CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID) —
         no wrangler login required.
      2. wrangler CLI (on PATH, or via ``npx wrangler``) — needs ``wrangler login``.
      3. git push fallback — only stores source; may not trigger a Pages deploy.

    Returns (method, pushed).
    """
    import os
    import shutil

    # 1. Cloudflare Pages API (most reliable — no interactive auth)
    if os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        try:
            return "cloudflare_api", _deploy_cloudflare_api()
        except Exception as e:
            logger.warning("Cloudflare API deploy failed, falling back", error=str(e)[:200])

    # 2. wrangler CLI (on PATH or via npx)
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


def _deploy_cloudflare_api() -> bool:
    """Upload public/ straight to Cloudflare Pages via the REST API (no wrangler).

    Requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID env vars.
    """
    import os
    import tempfile
    import zipfile

    import requests

    token = os.environ["CLOUDFLARE_API_TOKEN"]
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    project = os.environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")

    dist = _REPO_ROOT / "public"
    if not dist.exists() or not any(dist.iterdir()):
        raise RuntimeError("public/ dir empty, nothing to deploy")

    headers = {"Authorization": f"Bearer {token}"}
    api_base = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/pages/projects"
    )

    # 1. Zip public/
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
        # 2. Create deployment → get upload URL
        r = requests.post(
            f"{api_base}/{project}/deployments",
            headers=headers,
            json={"branch": "main"},
            timeout=60,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Cloudflare API deploy failed: {r.status_code} {r.text[:300]}")
        deployment = r.json()["result"]

        # 3. Upload zip
        with open(tmp.name, "rb") as f:
            r2 = requests.post(
                deployment["upload_url"],
                headers={"Content-Type": "application/zip"},
                data=f,
                timeout=300,
            )
        if r2.status_code not in (200, 201, 204):
            raise RuntimeError(f"Cloudflare upload failed: {r2.status_code} {r2.text[:300]}")
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    logger.info("Deployed to Cloudflare Pages via API", project=project, deployment=deployment["id"])
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

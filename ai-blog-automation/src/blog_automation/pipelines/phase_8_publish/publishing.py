"""Cloudflare Pages publishing pipeline — no DB, no WordPress.

Takes article content (from any source — pipeline, manual, AI) and publishes
it as a static HTML page on Cloudflare Pages via the repo's ``public/`` dir.

Flow::

    content dict  →  markdown file  →  static HTML  →  git push  →  live
"""

from __future__ import annotations

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
    publish_script = (
        _REPO_ROOT / "ai-blog-automation" / "scripts" / "publish.py"
    )
    cmd = ["python3", str(publish_script)]
    if not auto_push:
        cmd.append("--no-push")
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
                "SITE_NAME", "Tien's Blog"
            ),
        },
        timeout=120,
    )

    if result.returncode != 0:
        logger.error("publish.py failed", stderr=result.stderr[:500])
        raise RuntimeError(f"publish.py failed: {result.stderr[:300]}")

    # ── Deploy: Cloudflare Direct Upload (preferred) or Git push ──
    pushed = False
    if auto_push:
        cf_token = __import__("os").environ.get("CLOUDFLARE_API_TOKEN", "")
        if cf_token:
            pushed = _deploy_cloudflare(title)
        else:
            pushed = _deploy_git_push(title)

    # ── Determine live URL ──
    site_url = __import__("os").environ.get(
        "SITE_URL", "https://side-blogs.pages.dev"
    )
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
    """Upload to Cloudflare Pages via wrangler CLI (reliable, no API issues)."""
    import shutil

    # Check wrangler is available
    if not shutil.which("wrangler"):
        logger.warning("wrangler CLI not found, falling back to git push")
        return _deploy_git_push(title)

    dist = _REPO_ROOT / "public"
    if not dist.exists() or not list(dist.iterdir()):
        logger.warning("public/ dir empty, nothing to deploy")
        return False

    project = __import__("os").environ.get("CLOUDFLARE_PROJECT_NAME", "side-blogs")
    result = subprocess.run(
        [
            "wrangler", "pages", "deploy", str(dist),
            "--project-name", project,
            "--branch", "main",
            "--commit-dirty", "true",
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

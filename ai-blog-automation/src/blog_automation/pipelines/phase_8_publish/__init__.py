"""Phase 8 — Cloudflare Pages publishing.

No DB. No WordPress. Output is static HTML in ``public/`` served by
Cloudflare Pages.
"""

from blog_automation.pipelines.phase_8_publish.publishing import (
    build_site_files_from_db,
    delete_article_and_redeploy,
    publish_article,
)

__all__ = [
    "publish_article",
    "delete_article_and_redeploy",
    "build_site_files_from_db",
]

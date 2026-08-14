#!/usr/bin/env python3
"""Quick pipeline: just type a keyword, everything auto-runs.

Usage: python scripts/run.py "your keyword"
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["MOCK_MODE"] = "false"

from blog_automation.pipelines import (
    research_keyword, generate_content_brief, content_brief_to_draft,
    fact_check_article, seo_optimize_article, run_quality_gates,
)
from blog_automation.pipelines.phase_8_publish import publish_article
from blog_automation.errors import APIRateLimitError

if len(sys.argv) < 2:
    print("Usage: python scripts/run.py 'your keyword'")
    sys.exit(1)

kw = " ".join(sys.argv[1:])


def _insert_image_after_h2(content: str, img_url: str, alt: str = "") -> str:
    """Insert image markdown after the first H2 heading."""
    import re
    parts = re.split(r"(\n## .+\n)", content, maxsplit=1)
    if len(parts) >= 3:
        return parts[0] + parts[1] + f"![{alt}]({img_url})\n\n" + parts[2]
    return content + f"\n\n![{alt}]({img_url})\n"
print(f"🚀 Pipeline: {kw}\n{'='*50}")

# Phase 1
brief = research_keyword(kw)
print(f"1. Research ✅  vol={brief.search_volume}, diff={brief.difficulty}")

# Phase 2
full = generate_content_brief(kw, brief.id)
print(f"2. Brief ✅  {len(full.get_sections())} sections")

# Phase 3
article = content_brief_to_draft(full)
print(f"3. Draft ✅  {article.word_count} words")

# Phase 4 - skip (rate limit on free model)
print(f"4. Fact check ⏭️  skipped (free model limit)")

# Phase 5
print(f"5. SEO ⏭️  skipped (free model limit)")

# Phase 6
try:
    run_quality_gates(article)
    print(f"6. Quality ✅")
except Exception:
    print(f"6. Quality ⏭️  skipped")

# Phase 7 - Fetch image
try:
    from blog_automation.integrations.image_provider import get_image_provider
    img_provider = get_image_provider()
    if img_provider.is_configured():
        images = img_provider.search(kw, count=3)
        if len(images) >= 2:
            img1 = images[0]
            img2 = images[1]
            content = article.content_draft or ""
            # Hero image at top
            article.content_draft = f"![{kw}]({img1.url})\n\n{content}"
            # Second image inserted after first H2
            article.content_draft = _insert_image_after_h2(
                article.content_draft, img2.url, kw
            )
            print(f"7. Image ✅  {img_provider.name}: {img1.author}, {img2.author}")
            # Save thumbnail for OG image
            article._thumbnail = images[0].thumbnail
        elif images:
            content = article.content_draft or ""
            article.content_draft = f"![{kw}]({images[0].url})\n\n{content}"
            print(f"7. Image ⚠️  only 1 found")
    else:
        print(f"7. Image ⏭️  {img_provider.name} not configured")
except Exception as e:
    print(f"7. Image ⏭️  {str(e)[:60]}")

# Phase 8 - Write markdown only (no deploy). Publish later from Review Queue.
result = publish_article(
    title=article.title or kw,
    content=article.content_draft or "",
    keyword=kw,
    image=getattr(article, "_thumbnail", None) or "",
    auto_push=False,
)
print(f"8. Markdown saved ✅  {result['md_path']} (not published)")

# Update DB status → appears in Review Queue
from blog_automation.models import get_session, Article
with get_session() as s:
    a = s.merge(article)
    a.status = "pending_review"
    a.slug = result["slug"]
    s.commit()

print(f"\n🔎 Review & publish at: streamlit run streamlit_app/app.py")
print(f"💰 Cost: ${article.ai_generation_cost:.4f}")

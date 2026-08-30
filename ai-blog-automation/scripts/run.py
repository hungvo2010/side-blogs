#!/usr/bin/env python3
"""Quick pipeline: just type a keyword, everything auto-runs.

Usage: python scripts/run.py "your keyword"
"""

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["MOCK_MODE"] = "false"

from blog_automation.pipelines import (
    content_brief_to_draft,
    generate_content_brief,
    research_keyword,
    run_quality_gates,
)

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


print(f"🚀 Pipeline: {kw}\n{'=' * 50}")

# Phase 1
brief = research_keyword(kw)
print(f"1. Research ✅  vol={brief.search_volume}, diff={brief.difficulty}")

# Phase 2
full = generate_content_brief(kw, brief.id)
print(f"2. Brief ✅  {len(full.get_sections())} sections")

# Phase 3
article = content_brief_to_draft(full)
print(f"3. Draft ✅  {article.word_count} words")

# Phase 3.5 - AI layout blocks (deepseek structured output) appended to draft
print("3.5 Blocks…")
try:
    from blog_automation.integrations.openrouter_client import OpenRouterClient
    from blog_automation.layouts import blocks_to_directives, generate_blocks

    _llm = OpenRouterClient()
    _blocks = generate_blocks(_llm, article.title, kw, article.content_draft or "")
    if _blocks:
        article.content_draft = (
            (article.content_draft or "").rstrip()
            + "\n\n" + blocks_to_directives(_blocks) + "\n"
        )
        print(f"3.5 Blocks ✅  {[b.get('type') for b in _blocks]}")
    else:
        print("3.5 Blocks ⏭️  none")
except Exception as e:
    print(f"3.5 Blocks ❗ {e!r}")
    traceback.print_exc()

# Persist article first so fact-check & SEO (which query by id) can find it
from blog_automation.models import get_session
with get_session() as s:
    s.add(article)
    s.commit()

# Phase 4 - Fact check (uses opencode/deepseek-v4-flash)
print("4. Fact check…")
try:
    from blog_automation.pipelines.phase_4_fact_check.fact_checking import (
        fact_check_article,
    )
    fact_check_article(article)
    print("4. Fact check ✅")
except Exception as e:
    print(f"4. Fact check ❗ {e!r}")
    traceback.print_exc()

# Phase 5 - SEO (uses opencode/deepseek-v4-flash)
print("5. SEO…")
try:
    from blog_automation.pipelines.phase_5_seo.seo_optimization import (
        seo_optimize_article,
    )
    article = seo_optimize_article(article)
    print(f"5. SEO ✅  score={getattr(article, 'seo_score', '?')}")
except Exception as e:
    print(f"5. SEO ❗ {e!r}")
    traceback.print_exc()

# Phase 6
try:
    run_quality_gates(article)
    print("6. Quality ✅")
except Exception as e:
    print(f"6. Quality ❗ {e!r}")
    traceback.print_exc()

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
            print("7. Image ⚠️  only 1 found")
    else:
        print(f"7. Image ⏭️  {img_provider.name} not configured")
except Exception as e:
    print(f"7. Image ❗ {e!r}")
    traceback.print_exc()

# Phase 8 - Send to review queue (NO auto-publish)
from blog_automation.models import get_session
from blog_automation.review.task_queue import create_review_task

with get_session() as s:
    a = s.merge(article)
    # Persist thumbnail so approve-from-dashboard keeps the OG image
    thumb = getattr(article, "_thumbnail", None)
    if thumb:
        a.featured_image_url = thumb
    # Persist main keywords (LSI from the brief) into tags so the dashboard
    # 🖼️ Images tab can find a replacement image by subject, not just the
    # primary keyword. Fall back to keyword if no LSI came through.
    try:
        lsi = full.get_lsi_keywords()
        if lsi:
            a.tags = [str(x) for x in lsi[:8]]
        elif not a.tags:
            a.tags = [kw]
    except Exception:
        if not a.tags:
            a.tags = [kw]
    a.status = "pending_review"
    s.commit()
    article_id = a.id

create_review_task(article, reviewer="Tien Nguyen", deadline_hours=24)
print(f"8. Review queue ✅  article_id={article_id} — chờ duyệt trên dashboard")
print(
    f"   → {os.environ.get('STREAMLIT_DASHBOARD_URL', 'https://reachnews.streamlit.app')} (Review Queue)"
)

print(f"\n🔎 Review & publish at: streamlit run streamlit_app/app.py")
print(f"💰 Cost: ${article.ai_generation_cost:.4f}")

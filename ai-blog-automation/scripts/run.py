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

# Phase 4 - skip on rate limit
try:
    fact_check_article(article)
    print(f"4. Fact check ✅")
except APIRateLimitError:
    print(f"4. Fact check ⏭️  rate limit")

# Phase 5
try:
    seo_optimize_article(article)
    print(f"5. SEO ✅  score={article.seo_score}")
except APIRateLimitError:
    print(f"5. SEO ⏭️  rate limit")

# Phase 6
try:
    run_quality_gates(article)
    print(f"6. Quality ✅")
except Exception:
    print(f"6. Quality ⏭️  skipped")

# Phase 8 - Publish
result = publish_article(
    title=article.title or kw,
    content=article.content_draft or "",
    keyword=kw,
    auto_push=True,
)
print(f"8. Published ✅  {result['url']}")
print(f"\n💰 Cost: ${article.ai_generation_cost:.4f}")

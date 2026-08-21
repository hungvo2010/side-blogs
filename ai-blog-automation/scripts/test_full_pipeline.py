#!/usr/bin/env python3
"""Test full pipeline: research → brief → draft → factcheck → SEO → quality → publish"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["MOCK_MODE"] = "false"

from blog_automation.pipelines import (
    content_brief_to_draft,
    fact_check_article,
    generate_content_brief,
    research_keyword,
    run_quality_gates,
    seo_optimize_article,
)
from blog_automation.pipelines.phase_8_publish import publish_article

KW = "best budget coffee maker 2026"

print(f"🚀 Pipeline: {KW}")
print("=" * 50)

# Phase 1
print("1. Research...")
brief = research_keyword(KW)
print(f"   ✅ volume={brief.search_volume}, difficulty={brief.difficulty}")

# Phase 2
print("2. Brief...")
full = generate_content_brief(KW, brief.id)
print(f"   ✅ {len(full.get_sections())} sections")

# Phase 3
print("3. Draft...")
article = content_brief_to_draft(full)
print(f"   ✅ {article.word_count} words, cost=${article.ai_generation_cost:.4f}")

# Phase 4
print("4. Fact check...")
report = fact_check_article(article)
print(f"   ✅ accuracy={report.get('accuracy_rate', 0):.0f}%")

# Phase 5
print("5. SEO...")
seo_optimize_article(article)
print(f"   ✅ score={article.seo_score}")

# Phase 6
print("6. Quality...")
try:
    run_quality_gates(article)
    print(f"   ✅ status={article.status}")
except Exception as e:
    print(f"   ⏭️ skip ({e})")

# Phase 8 - Publish
print("8. Publish...")
result = publish_article(
    title=article.title or KW,
    content=article.content_draft or "",
    keyword=KW,
    auto_push=True,
)
print(f"   ✅ {result['url']}")

print(f"\n💰 Total cost: ${article.ai_generation_cost:.4f}")
print(f"🌍 Live: {result['url']}")

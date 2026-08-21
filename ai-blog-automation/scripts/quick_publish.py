#!/usr/bin/env python3
"""Quick pipeline run for a single keyword"""

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


def run(kw):
    print(f"🚀 {kw}\n" + "=" * 50)
    brief = research_keyword(kw)
    print(f"1. ✅ Research: vol={brief.search_volume}, diff={brief.difficulty}")
    full = generate_content_brief(kw, brief.id)
    print(f"2. ✅ Brief: {len(full.get_sections())} sections")
    article = content_brief_to_draft(full)
    print(f"3. ✅ Draft: {article.word_count} words")
    fact_check_article(article)
    print("4. ✅ Fact check done")
    seo_optimize_article(article)
    print(f"5. ✅ SEO: score={article.seo_score}")
    run_quality_gates(article)
    print("6. ✅ Quality done")
    result = publish_article(
        title=article.title or kw,
        content=article.content_draft or "",
        keyword=kw,
        auto_push=True,
    )
    print(f"8. ✅ Published: {result['url']}\n")


run("robusta vs arabica coffee")
run("best vietnamese coffee beans")

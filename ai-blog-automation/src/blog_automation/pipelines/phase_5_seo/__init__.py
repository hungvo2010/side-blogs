"""Phase 5 — SEO Optimization.

Analyzes and optimizes articles for search engine visibility.
"""

from blog_automation.pipelines.phase_5_seo.seo_optimization import (
    analyze_content,
    generate_meta_description,
    generate_meta_title,
    seo_optimize_article,
)

__all__ = [
    "analyze_content",
    "generate_meta_title",
    "generate_meta_description",
    "seo_optimize_article",
]

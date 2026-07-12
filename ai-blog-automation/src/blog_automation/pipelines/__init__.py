"""Business logic pipelines, organized by the publish-a-blog flow.

The package is split into phase subpackages that mirror the end-to-end
article lifecycle:

    phase_1_research    -> keyword research (Ahrefs)
    phase_2_brief       -> content brief generation (OpenRouter)
    phase_3_draft       -> article drafting (OpenRouter)
    phase_4_fact_check  -> claim extraction & verification (OpenRouter)
    phase_5_seo         -> SEO optimization (RankMath + OpenRouter)
    phase_6_quality     -> quality gates (Copyscape, links, readability)
    phase_7_review      -> human-in-the-loop review (re-exports review pkg)
    phase_8_publish     -> WordPress publishing

The public API below re-exports every step so existing callers
(``from blog_automation.pipelines import research_keyword_full`` etc.)
keep working unchanged.
"""

from blog_automation.pipelines.phase_1_research import (
    get_next_keyword_from_calendar,
    research_keyword,
)
from blog_automation.pipelines.phase_2_brief import (
    generate_content_brief,
    research_keyword_full,
)
from blog_automation.pipelines.phase_3_draft import (
    content_brief_to_draft,
    generate_article_draft,
    generate_outline,
    revise_article_with_feedback,
    validate_draft_quality,
)
from blog_automation.pipelines.phase_4_fact_check import (
    extract_claims,
    fact_check_article,
    filter_checkworthy_claims,
    generate_fact_check_report,
    retrieve_evidence,
    verify_claim,
)
from blog_automation.pipelines.phase_5_seo import (
    analyze_content,
    generate_meta_description,
    generate_meta_title,
    seo_optimize_article,
)
from blog_automation.pipelines.phase_6_quality import (
    check_plagiarism,
    check_readability,
    run_quality_gates,
    validate_metadata,
    verify_links,
)
from blog_automation.pipelines.phase_7_review import (
    ReviewTask,
    assign_task,
    complete_review,
    create_review_task,
    get_pending_tasks,
    get_review_stats,
    get_reviewer_tasks,
    update_task_status,
)
from blog_automation.pipelines.phase_8_publish import (
    create_wordpress_post,
    format_markdown_to_html,
    prepare_images,
    publish_article,
    setup_analytics_tracking,
    store_acf_metadata,
)

__all__ = [
    # Phase 1 - Research
    "research_keyword",
    "get_next_keyword_from_calendar",
    # Phase 2 - Brief
    "generate_content_brief",
    "research_keyword_full",
    # Phase 3 - Draft
    "generate_outline",
    "generate_article_draft",
    "content_brief_to_draft",
    "validate_draft_quality",
    "revise_article_with_feedback",
    # Phase 4 - Fact-check
    "extract_claims",
    "filter_checkworthy_claims",
    "retrieve_evidence",
    "verify_claim",
    "generate_fact_check_report",
    "fact_check_article",
    # Phase 5 - SEO
    "analyze_content",
    "generate_meta_title",
    "generate_meta_description",
    "seo_optimize_article",
    # Phase 6 - Quality gates
    "check_plagiarism",
    "verify_links",
    "check_readability",
    "validate_metadata",
    "run_quality_gates",
    # Phase 7 - Human review
    "ReviewTask",
    "create_review_task",
    "get_pending_tasks",
    "get_reviewer_tasks",
    "assign_task",
    "update_task_status",
    "complete_review",
    "get_review_stats",
    # Phase 8 - Publish
    "format_markdown_to_html",
    "prepare_images",
    "create_wordpress_post",
    "store_acf_metadata",
    "setup_analytics_tracking",
    "publish_article",
]

"""Business logic pipelines package."""

from blog_automation.pipelines.keyword_research import (
    research_keyword,
    get_next_keyword_from_calendar,
)
from blog_automation.pipelines.brief_generation import (
    generate_content_brief,
    research_keyword_full,
)
from blog_automation.pipelines.drafting import (
    generate_outline,
    generate_article_draft,
    content_brief_to_draft,
    validate_draft_quality,
)
from blog_automation.pipelines.fact_checking import (
    extract_claims,
    filter_checkworthy_claims,
    retrieve_evidence,
    verify_claim,
    generate_fact_check_report,
    fact_check_article,
)
from blog_automation.pipelines.seo_optimization import (
    analyze_content,
    generate_meta_title,
    generate_meta_description,
    seo_optimize_article,
)
from blog_automation.pipelines.quality_gates import (
    check_plagiarism,
    verify_links,
    check_readability,
    validate_metadata,
    run_quality_gates,
)
from blog_automation.pipelines.publishing import (
    format_markdown_to_html,
    prepare_images,
    create_wordpress_post,
    store_acf_metadata,
    setup_analytics_tracking,
    publish_article,
)

__all__ = [
    # Keyword Research
    "research_keyword",
    "get_next_keyword_from_calendar",
    # Brief Generation
    "generate_content_brief",
    "research_keyword_full",
    # Drafting
    "generate_outline",
    "generate_article_draft",
    "content_brief_to_draft",
    "validate_draft_quality",
    # Fact Checking
    "extract_claims",
    "filter_checkworthy_claims",
    "retrieve_evidence",
    "verify_claim",
    "generate_fact_check_report",
    "fact_check_article",
    # SEO
    "analyze_content",
    "generate_meta_title",
    "generate_meta_description",
    "seo_optimize_article",
    # Quality Gates
    "check_plagiarism",
    "verify_links",
    "check_readability",
    "validate_metadata",
    "run_quality_gates",
    # Publishing
    "format_markdown_to_html",
    "prepare_images",
    "create_wordpress_post",
    "store_acf_metadata",
    "setup_analytics_tracking",
    "publish_article",
]

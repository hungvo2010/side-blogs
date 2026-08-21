"""SEO optimization pipeline.

Analyzes and optimizes articles for search engine visibility.
"""

from typing import Any

from blog_automation.errors import ProcessingError
from blog_automation.integrations.openrouter_client import OpenRouterClient
from blog_automation.integrations.rankmath_client import RankMathClient
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, ContentBrief, get_session

logger = get_logger(__name__)


# Prompts for SEO optimization
META_TITLE_PROMPT = """Generate an SEO-optimized meta title for this article.

Keyword: {keyword}
Article Title: {title}
Article Summary: {summary}

Requirements:
- 50-60 characters maximum
- Include the keyword in the first 5 words
- Make it compelling and click-worthy
- Use power words if appropriate

Return only the meta title, nothing else."""

META_DESCRIPTION_PROMPT = """Generate an SEO-optimized meta description for this article.

Keyword: {keyword}
Article Title: {title}
Article Summary: {summary}

Requirements:
- 150-160 characters maximum
- Include the keyword naturally
- Include a call-to-action
- Make it compelling to encourage clicks

Return only the meta description, nothing else."""


def analyze_content(article: Article) -> dict[str, Any]:
    """Analyze article content for SEO."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return {
            "score": 85,
            "metrics": {
                "word_count": article.word_count,
                "keyword_density": 1.2,
                "h2_count": 4,
                "internal_links": 2,
                "external_links": 3,
            },
            "issues": ["Add one more internal link"],
            "suggestions": ["Use keyword in first paragraph"],
        }

    logger.info("Analyzing content for SEO", article_id=article.id)

    rankmath = RankMathClient()

    content = article.content_final or article.content_draft or ""

    analysis = rankmath.analyze_content(
        content=content,
        keyword=article.keyword,
        title=article.title,
        meta_description=article.meta_description,
    )

    logger.info(
        "SEO analysis complete",
        article_id=article.id,
        score=analysis.get("score", 0),
    )

    return analysis


def analyze_competitors(
    keyword: str, brief: ContentBrief | None = None
) -> dict[str, Any]:
    """Analyze competitor content for SEO insights.

    Args:
        keyword: Target keyword
        brief: Optional content brief with competitor data

    Returns:
        Competitor analysis results
    """
    if brief and brief.competitor_data:
        return {
            "avg_word_count": brief.competitor_data.get("avg_word_count", 2000),
            "avg_domain_rating": brief.competitor_data.get("avg_domain_rating", 50),
            "top_pages": brief.competitor_data.get("competitors", []),
            "common_h2s": [],  # Would need to extract from competitor content
        }

    return {
        "avg_word_count": 2000,
        "avg_domain_rating": 50,
        "top_pages": [],
        "common_h2s": [],
    }


def generate_seo_recommendations(
    article: Article,
    analysis: dict[str, Any],
    brief: ContentBrief | None = None,
) -> list[str]:
    """Generate specific SEO recommendations.

    Args:
        article: Article to optimize
        analysis: SEO analysis results
        brief: Optional content brief

    Returns:
        List of recommendations
    """
    recommendations = []
    metrics = analysis.get("metrics", {})

    # Word count recommendations
    word_count = metrics.get("word_count", 0)
    target_count = brief.get_target_word_count() if brief else 2000

    if word_count < target_count:
        recommendations.append(
            f"Add {target_count - word_count} more words to reach optimal length"
        )

    # Keyword density
    density = metrics.get("keyword_density", 0)
    if density < 0.5:
        recommendations.append(
            f"Increase keyword density from {density:.1f}% to 0.5-1.5%"
        )
    elif density > 1.5:
        recommendations.append(
            f"Reduce keyword density from {density:.1f}% to avoid keyword stuffing"
        )

    # Heading structure
    h2_count = metrics.get("h2_count", 0)
    if h2_count < 3:
        recommendations.append(
            f"Add {3 - h2_count} more H2 headings for better structure"
        )

    # Internal links
    internal_links = metrics.get("internal_links", 0)
    if internal_links < 3:
        recommendations.append(
            f"Add {3 - internal_links} more internal links to related content"
        )

    # External links
    external_links = metrics.get("external_links", 0)
    if external_links < 3:
        recommendations.append(
            f"Add {3 - external_links} more external links to authoritative sources"
        )

    # Meta title
    if not article.meta_title:
        recommendations.append("Generate and add meta title")
    elif len(article.meta_title) > 60:
        recommendations.append(
            f"Shorten meta title from {len(article.meta_title)} to 60 characters"
        )

    # Meta description
    if not article.meta_description:
        recommendations.append("Generate and add meta description")
    elif len(article.meta_description) > 160:
        recommendations.append(
            f"Shorten meta description from {len(article.meta_description)} to 160 characters"
        )

    # Add issues from analysis
    for issue in analysis.get("issues", []):
        if issue not in recommendations:
            recommendations.append(issue)

    return recommendations


def generate_meta_title(
    keyword: str,
    title: str,
    content: str,
) -> str:
    """Generate SEO-optimized meta title."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return f"{title} | Expert Guide to {keyword}"

    llm = OpenRouterClient()

    # Create summary from first 500 chars
    summary = content[:500].replace("\n", " ").strip()

    prompt = META_TITLE_PROMPT.format(
        keyword=keyword,
        title=title,
        summary=summary,
    )

    response = llm.complete(prompt, temperature=0.7, max_tokens=100)
    meta_title = response.get("content", "").strip()

    # Ensure length constraint
    if len(meta_title) > 60:
        meta_title = meta_title[:57] + "..."

    return meta_title


def generate_meta_description(
    keyword: str,
    title: str,
    content: str,
) -> str:
    """Generate SEO-optimized meta description."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return f"Discover everything you need to know about {keyword}. Our expert guide covers the best tips, strategies, and insights for success."

    llm = OpenRouterClient()

    # Create summary from first 500 chars
    summary = content[:500].replace("\n", " ").strip()

    prompt = META_DESCRIPTION_PROMPT.format(
        keyword=keyword,
        title=title,
        summary=summary,
    )

    response = llm.complete(prompt, temperature=0.7, max_tokens=200)
    meta_desc = response.get("content", "").strip()

    # Ensure length constraint
    if len(meta_desc) > 160:
        meta_desc = meta_desc[:157] + "..."

    return meta_desc


def seo_optimize_article(article: Article) -> Article:
    """Complete SEO optimization pipeline.

    Args:
        article: Article to optimize

    Returns:
        Optimized article

    Raises:
        ProcessingError: If optimization fails
    """
    logger.info("Starting SEO optimization", article_id=article.id)

    try:
        with get_session() as session:
            # Get fresh article
            article = session.query(Article).get(article.id)
            if not article:
                raise ProcessingError(
                    message=f"Article {article.id} not found",
                    step="seo_optimization",
                )

            content = article.content_final or article.content_draft or ""

            # Get associated brief if exists
            brief = None
            brief_query = (
                session.query(ContentBrief)
                .filter(ContentBrief.article_id == article.id)
                .first()
            )
            if brief_query:
                brief = brief_query

            # Analyze content
            analysis = analyze_content(article)
            article.seo_analysis = analysis
            article.seo_score = analysis.get("score", 0)

            # Generate recommendations
            recommendations = generate_seo_recommendations(article, analysis, brief)

            # Generate meta title if missing
            if not article.meta_title:
                article.meta_title = generate_meta_title(
                    article.keyword,
                    article.title,
                    content,
                )
                logger.info(
                    "Generated meta title",
                    article_id=article.id,
                    meta_title=article.meta_title,
                )

            # Generate meta description if missing
            if not article.meta_description:
                article.meta_description = generate_meta_description(
                    article.keyword,
                    article.title,
                    content,
                )
                logger.info(
                    "Generated meta description",
                    article_id=article.id,
                )

            # Calculate keyword density
            article.calculate_keyword_density()

            # Update status
            if article.seo_score >= 70:
                article.status = "seo_review"
            else:
                article.status = "seo_needs_work"

            # Store recommendations in analysis
            article.seo_analysis["recommendations"] = recommendations

            session.commit()

            logger.info(
                "SEO optimization complete",
                article_id=article.id,
                score=article.seo_score,
                recommendations=len(recommendations),
            )

            return article

    except Exception as e:
        raise ProcessingError(
            message=f"SEO optimization failed: {str(e)}",
            step="seo_optimization",
            context={"article_id": article.id if article else None},
        ) from e

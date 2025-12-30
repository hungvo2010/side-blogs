"""Keyword research pipeline.

Fetches keyword data from Ahrefs and creates initial content briefs.
"""

from typing import Any

from blog_automation.errors import InvalidKeywordError, ProcessingError
from blog_automation.integrations.ahrefs_client import AhrefsClient
from blog_automation.logging_config import get_logger
from blog_automation.models import ContentBrief, ContentCalendar, get_session

logger = get_logger(__name__)


def research_keyword(
    keyword: str,
    article_id: int | None = None,
    country: str = "us",
) -> ContentBrief:
    """Research a keyword and create initial content brief.

    Args:
        keyword: Target keyword to research
        article_id: Optional article ID to link
        country: Country code for metrics

    Returns:
        ContentBrief with keyword research data

    Raises:
        InvalidKeywordError: If keyword is invalid
        ProcessingError: If research fails
    """
    logger.info("Starting keyword research", keyword=keyword)

    # Validate keyword
    if not keyword or not keyword.strip():
        raise InvalidKeywordError(
            message="Keyword cannot be empty",
            keyword=keyword,
        )

    keyword = keyword.strip().lower()

    try:
        # Initialize Ahrefs client
        ahrefs = AhrefsClient()

        # Get keyword metrics
        logger.info("Fetching keyword metrics", keyword=keyword)
        metrics = ahrefs.get_keyword_metrics(keyword, country)

        # Get SERP features
        logger.info("Analyzing SERP features", keyword=keyword)
        serp_features = ahrefs.serp_features(keyword, country)

        # Get top pages for competitor analysis
        logger.info("Analyzing competitors", keyword=keyword)
        top_pages = ahrefs.top_pages(keyword, country, limit=10)

        # Analyze competitors
        competitor_analysis = ahrefs.competitor_analysis(keyword, country)

        # Determine search intent
        intent = _determine_intent(keyword, serp_features)

        # Calculate recommended word count
        recommended_word_count = _recommend_word_count(
            metrics.get("difficulty", 50),
            competitor_analysis.get("avg_word_count", 2000),
        )

        # Create brief data structure
        brief_data = {
            "keyword": keyword,
            "search_volume": metrics.get("volume", 0),
            "difficulty": metrics.get("difficulty", 50),
            "intent": intent,
            "target_word_count": recommended_word_count,
            "competitor_analysis": {
                "avg_word_count": competitor_analysis.get("avg_word_count", 2000),
                "avg_domain_rating": competitor_analysis.get("avg_domain_rating", 50),
                "top_pages": [
                    {
                        "url": p.get("url"),
                        "title": p.get("title"),
                        "word_count": p.get("word_count"),
                    }
                    for p in top_pages[:5]
                ],
            },
            "serp_features": serp_features,
        }

        # Create ContentBrief
        with get_session() as session:
            brief = ContentBrief(
                keyword=keyword,
                search_volume=metrics.get("volume", 0),
                difficulty=metrics.get("difficulty", 50),
                intent=intent,
                brief_data=brief_data,
                serp_features=serp_features,
                competitor_data=competitor_analysis,
                article_id=article_id,
            )
            session.add(brief)
            session.commit()

            logger.info(
                "Keyword research complete",
                keyword=keyword,
                brief_id=brief.id,
                volume=metrics.get("volume", 0),
                difficulty=metrics.get("difficulty", 50),
            )

            return brief

    except InvalidKeywordError:
        raise
    except Exception as e:
        raise ProcessingError(
            message=f"Keyword research failed: {str(e)}",
            step="keyword_research",
            context={"keyword": keyword},
        ) from e


def get_next_keyword_from_calendar() -> dict[str, Any] | None:
    """Get the next planned keyword from content calendar.

    Returns:
        Dict with keyword and calendar entry, or None if none planned
    """
    with get_session() as session:
        entry = ContentCalendar.get_next_planned(session)

        if not entry:
            logger.info("No planned keywords in calendar")
            return None

        # Mark as in progress
        entry.mark_in_progress()
        session.commit()

        logger.info(
            "Retrieved keyword from calendar",
            keyword=entry.keyword,
            calendar_id=entry.id,
        )

        return {
            "keyword": entry.keyword,
            "calendar_id": entry.id,
            "title": entry.title,
            "pub_date": entry.pub_date.isoformat() if entry.pub_date else None,
        }


def _determine_intent(keyword: str, serp_features: dict) -> str:
    """Determine search intent from keyword and SERP features.

    Args:
        keyword: Target keyword
        serp_features: SERP feature data

    Returns:
        Intent classification
    """
    keyword_lower = keyword.lower()

    # Commercial intent signals
    commercial_words = ["best", "top", "review", "vs", "compare", "alternative"]
    if any(word in keyword_lower for word in commercial_words):
        return "commercial"

    # Transactional intent signals
    transactional_words = ["buy", "price", "cheap", "deal", "discount", "coupon"]
    if any(word in keyword_lower for word in transactional_words):
        return "transactional"

    # Navigational intent signals
    if serp_features.get("knowledge_panel"):
        return "navigational"

    # Default to informational
    return "informational"


def _recommend_word_count(difficulty: int, competitor_avg: int) -> int:
    """Recommend target word count based on difficulty and competition.

    Args:
        difficulty: Keyword difficulty (0-100)
        competitor_avg: Average competitor word count

    Returns:
        Recommended word count
    """
    # Base on competitor average
    base_count = max(competitor_avg, 1500)

    # Adjust for difficulty
    if difficulty >= 70:
        # High difficulty: aim for longer content
        return min(base_count + 500, 4000)
    elif difficulty >= 40:
        # Medium difficulty
        return min(base_count + 200, 3000)
    else:
        # Low difficulty
        return max(base_count, 1500)

"""Keyword research pipeline.

Fetches keyword data from the configured search provider (Ahrefs or Google
Custom Search) and runs opportunity scoring + backlink analysis.
"""

from typing import Any

from blog_automation.errors import InvalidKeywordError, ProcessingError
from blog_automation.logging_config import get_logger
from blog_automation.models import ContentBrief, ContentCalendar, get_session

logger = get_logger(__name__)


def research_keyword(
    keyword: str,
    article_id: int | None = None,
    country: str = "us",
) -> ContentBrief:
    """Research a keyword, score opportunity, and create initial content brief.

    Uses ``get_search_client()`` so it works with either Ahrefs or Google
    Custom Search depending on ``SEARCH_PROVIDER`` in .env.

    Args:
        keyword: Target keyword to research
        article_id: Optional article ID to link
        country: Country code for metrics

    Returns:
        ContentBrief with keyword research data + opportunity analysis

    Raises:
        InvalidKeywordError: If keyword is invalid
        ProcessingError: If research fails
    """
    logger.info("Starting keyword research", keyword=keyword)

    if not keyword or not keyword.strip():
        raise InvalidKeywordError(
            message="Keyword cannot be empty",
            keyword=keyword,
        )

    keyword = keyword.strip().lower()

    from blog_automation.config import get_settings

    settings = get_settings()

    if settings.mock_mode:
        logger.info("MOCK MODE: Using dummy keyword data")
        metrics = {"volume": 1200, "difficulty": 35}
        serp_features = {"featured_snippet": True, "knowledge_panel": False}
        top_pages = [
            {
                "url": "https://example.com/competitor1",
                "title": "Top Competitor Guide",
                "snippet": "A comprehensive guide from 2024.",
            }
        ]
        competitor_analysis = {"avg_word_count": 1800, "avg_domain_rating": 45}
    else:
        try:
            from blog_automation.integrations.search_factory import get_search_client

            client = get_search_client()
            logger.info(
                "Fetching keyword metrics via %s",
                type(client).__name__,
                keyword=keyword,
            )

            metrics = client.get_keyword_overview(keyword, country)
            serp_features = client.serp_features(keyword, country)
            top_pages = client.top_pages(keyword, country, limit=10)
            competitor_analysis = client.competitor_analysis(keyword, country)

        except Exception as e:
            logger.warning("Trends API failed, using OpenRouter", error=str(e)[:60])
            try:
                from blog_automation.integrations.openrouter_client import (
                    OpenRouterClient,
                )

                llm = OpenRouterClient()
                prompt = (
                    f"Research '{keyword}'. Estimate: search volume, "
                    f"difficulty (1-100), intent "
                    f"(informational/commercial/transactional), "
                    f"and top 3 competing URLs with titles."
                )
                system = (
                    "Output JSON: volume (int), difficulty (int), "
                    "intent (str), top_pages (list of {url, title})."
                )
                result = llm.extract_json(
                    prompt=prompt,
                    system_prompt=system,
                    max_tokens=300,
                )
                metrics = {
                    "volume": result.get("volume", 500),
                    "difficulty": result.get("difficulty", 50),
                }
                serp_features = {}
                top_pages = result.get("top_pages", [])
                competitor_analysis = {"avg_word_count": 1500}
            except Exception:
                logger.warning("OpenRouter research also failed, using defaults")
                metrics = {"volume": 500, "difficulty": 50}
                serp_features = {"featured_snippet": False}
                top_pages = []
                competitor_analysis = {"avg_word_count": 1500, "avg_domain_rating": 40}

    try:
        # ── Phase 1a: Determine intent + word count ──
        intent = _determine_intent(keyword, serp_features)

        recommended_word_count = _recommend_word_count(
            metrics.get("difficulty", 50),
            competitor_analysis.get("avg_word_count", 2000),
        )

        # ── Phase 1b: Opportunity scoring + backlink analysis ──
        from blog_automation.pipelines.phase_1_research.keyword_analyzer import (
            KeywordAnalyzer,
        )

        analyzer = KeywordAnalyzer()
        analysis = analyzer.analyze(
            {
                "keyword": keyword,
                "volume": metrics.get("volume", 0),
                "difficulty": metrics.get("difficulty", 50),
                "top_pages": top_pages,
            }
        )

        logger.info(
            "Keyword analysis",
            keyword=keyword,
            verdict=analysis.score.verdict,
            score=analysis.score.opportunity_score,
            backlinks=len(analysis.backlink_opportunities),
        )

        # ── Build brief data ──
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
                        "snippet": p.get("snippet"),
                    }
                    for p in top_pages[:5]
                ],
            },
            "serp_features": serp_features,
            # ── New: opportunity analysis ──
            "opportunity_analysis": {
                "verdict": analysis.score.verdict,
                "score": analysis.score.opportunity_score,
                "why": analysis.score.why,
                "summary": analysis.summary,
                "backlink_opportunities": [
                    {
                        "domain": b.domain,
                        "url": b.url,
                        "approach": b.approach,
                        "ease_score": b.ease_score,
                        "why": b.why,
                    }
                    for b in analysis.backlink_opportunities
                ],
            },
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
                opportunity_verdict=analysis.score.verdict,
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
